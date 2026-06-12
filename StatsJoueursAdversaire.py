# NomDeVotreNouvelleSousApp.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur principal de la nouvelle sous-app (Trié par Joueur puis par Année)."""
    
    # --- ÉTAT DES SESSIONS & CALLBACKS DE FILTRES ---
    def reset_filtres():
        """Réinitialise le filtre descendant des joueurs lorsque les clubs changent."""
        st.session_state.joueurs_choisis = []

    # Initialisation des variables de session indispensables
    for key, val in [("clubs_choisis", []), ("joueurs_choisis", [])]:
        if key not in st.session_state:
            st.session_state[key] = val

    # --- INTERFACE UTILISATEUR : FILTRES ACTIFS ---
    st.subheader("🔍 Filtres de sélection (Multi-choix tactiles)")
    
    # Étape 1 : Choix des clubs parmi TOUS les clubs de la base
    st.write("**🏢 1. Sélectionnez un ou plusieurs Clubs (Equipe 1) :**")
    st.segmented_control(
        "Clubs", options=utils.charger_clubs_uniques(conn), 
        key="clubs_choisis", selection_mode="multi", on_change=reset_filtres, label_visibility="collapsed"
    )

    # Étape 2 : Choix des joueurs (dépend uniquement des clubs sélectionnés)
    if st.session_state.clubs_choisis:
        st.markdown("---")
        st.write("**👤 2. Sélectionnez un ou plusieurs Joueurs (Joueur 1) :**")
        st.segmented_control(
            "Joueurs", options=utils.charger_joueurs_par_clubs(conn, st.session_state.clubs_choisis), 
            key="joueurs_choisis", selection_mode="multi", label_visibility="collapsed"
        )

    # --- SÉCURITÉ DE CONTRÔLE ET REQUÊTAGE ---
    st.markdown("---")
    if not st.session_state.clubs_choisis:
        st.info("💡 En attente de vos critères : Veuillez cocher au moins un **Club** pour commencer.")
    else:
        # Requête Supabase globale
        req = conn.table("test").select("*").in_("Equipe1", st.session_state.clubs_choisis)
        if st.session_state.joueurs_choisis:
            req = req.in_("Joueur1", st.session_state.joueurs_choisis)

        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé pour cette combinaison précise.")
        else:
            colonnes_requises = ["Match", "VictoireJ1", "ClassementJ2"]
            if not all(c in df_res.columns for c in colonnes_requises):
                st.error("Une ou plusieurs colonnes de calcul indispensables (Match, VictoireJ1, ClassementJ2) sont introuvables.")
                st.stop()
                
            # --- CONFIGURATION DU TCD : JOUEUR ET ANNÉE EN PREMIER ---
            # Index réordonné : Joueur1 en premier, suivi de Annee
            tcd_bilan = df_res.pivot_table(
                index=["Joueur1", "Annee", "Equipe1", "ClassementJ1", "ClassementJ2"], 
                values=["Match", "VictoireJ1"], 
                aggfunc={"Match": "size", "VictoireJ1": "sum"}, 
                fill_value=0
            )

            if tcd_bilan.empty:
                st.info("Données insuffisantes pour générer ce tableau croisé.")
            else:
                # Forçage du format String sur le niveau de l'index 'Annee' (situé à la position 1 désormais)
                tcd_bilan.index = tcd_bilan.index.set_levels(tcd_bilan.index.levels[1].astype(str), level=1)
                
                # --- APPLICATION DU TRI ---
                # Tri avec priorité absolue au Joueur puis à l'Année
                tcd_bilan = tcd_bilan.sort_index(level=["Joueur1", "Annee"])
                
                # Calcul du % de Victoires
                tcd_bilan["Taux Victoires"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match"]).fillna(0)) * 100
                
                # Réorganisation finale des colonnes de données
                tcd_bilan = tcd_bilan[["Match", "VictoireJ1", "Taux Victoires"]]
                tcd_bilan.columns = ["Matchs Joués", "Victoires", "% Victoire"]

                st.subheader(f"📋 Tableau de synthèse analytique ({len(df_res)} match(s) analysé(s))")
                
                # Génération du rendu HTML propre
                html_table = (
                    tcd_bilan.style.format({"Matchs Joués": "{:,.0f}", "Victoires": "{:,.0f}", "% Victoire": "{:.1f}%"})
                    .background_gradient(cmap="RdYlGn", subset=["% Victoire"], vmin=0, vmax=100, axis=0)
                    .set_table_styles([
                        {"selector": "th, td, th.row_heading, th.col_heading, td.data, .blank", "props": [("vertical-align", "top !important"), ("text-align", "left !important"), ("border", "1px solid #555555 !important"), ("padding", "8px !important")]}
                    ], overwrite=False)
                    .to_html(escape=False)
                )
                
                st.write(html_table, unsafe_allow_html=True)
