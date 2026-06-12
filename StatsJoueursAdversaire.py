# StatsJoueursAdversaire.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur principal : TCD analytique, trié par Joueur et par Année, sans totaux."""
    
    # --- ÉTAT DES SESSIONS & CALLBACKS DE FILTRES ---
    def reset_filtres():
        """Réinitialise le filtre descendant des joueurs lorsque les clubs changent."""
        st.session_state.joueurs_choisis = []

    # Initialisation des variables de session
    for key, val in [("clubs_choisis", []), ("joueurs_choisis", [])]:
        if key not in st.session_state:
            st.session_state[key] = val

    # --- INTERFACE UTILISATEUR : FILTRES ACTIFS ---
    st.subheader("🔍 Filtres de sélection")
    
    st.write("**🏢 1. Sélectionnez un ou plusieurs Clubs :**")
    st.segmented_control(
        "Clubs", options=utils.charger_clubs_uniques(conn), 
        key="clubs_choisis", selection_mode="multi", on_change=reset_filtres, label_visibility="collapsed"
    )

    if st.session_state.clubs_choisis:
        st.markdown("---")
        st.write("**👤 2. Sélectionnez un ou plusieurs Joueurs :**")
        st.segmented_control(
            "Joueurs", options=utils.charger_joueurs_par_clubs(conn, st.session_state.clubs_choisis), 
            key="joueurs_choisis", selection_mode="multi", label_visibility="collapsed"
        )

    # --- SÉCURITÉ DE CONTRÔLE ET REQUÊTAGE ---
    st.markdown("---")
    if not st.session_state.clubs_choisis:
        st.info("💡 Veuillez cocher au moins un **Club** pour commencer.")
    else:
        # Requête Supabase
        req = conn.table("test").select("*").in_("Equipe1", st.session_state.clubs_choisis)
        if st.session_state.joueurs_choisis:
            req = req.in_("Joueur1", st.session_state.joueurs_choisis)

        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé.")
        else:
            # --- CONFIGURATION DU TCD ---
            # Index demandé : Equipe1, Joueur1, Annee, ClassementJ1, ClassementJ2
            tcd_bilan = df_res.pivot_table(
                index=["Equipe1", "Joueur1", "Annee", "ClassementJ1", "ClassementJ2"], 
                values=["Match", "VictoireJ1"], 
                aggfunc={"Match": "size", "VictoireJ1": "sum"}, 
                fill_value=0
            )

            # Forçage année en string pour l'affichage
            tcd_bilan.index = tcd_bilan.index.set_levels(tcd_bilan.index.levels[2].astype(str), level=2)
            
            # Tri par Joueur puis par Année
            tcd_bilan = tcd_bilan.reset_index()
            tcd_bilan = tcd_bilan.sort_values(by=["Joueur1", "Annee"])
            tcd_bilan = tcd_bilan.set_index(["Equipe1", "Joueur1", "Annee", "ClassementJ1", "ClassementJ2"])
            
            # Calcul du % Victoire
            tcd_bilan["% Victoire"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match"]).fillna(0)) * 100
            
            # Sélection et renommage des colonnes
            tcd_bilan = tcd_bilan[["Match", "VictoireJ1", "% Victoire"]]
            tcd_bilan.columns = ["Matchs Joués", "Victoires", "% Victoire"]

            st.subheader(f"📋 Synthèse ({len(df_res)} match(s))")
            
            # Rendu HTML
            html_table = (
                tcd_bilan.style.format({"Matchs Joués": "{:,.0f}", "Victoires": "{:,.0f}", "% Victoire": "{:.1f}%"})
                .background_gradient(cmap="RdYlGn", subset=["% Victoire"], vmin=0, vmax=100, axis=0)
                .set_table_styles([
                    {"selector": "th, td", "props": [("border", "1px solid #555555"), ("padding", "8px")]}
                ], overwrite=False)
                .to_html(escape=False)
            )
            st.write(html_table, unsafe_allow_html=True)
