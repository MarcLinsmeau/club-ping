# StatsEquipe.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur principal : TCD analytique avec index complet, trié et aligné."""
    
    # --- ÉTAT DES SESSIONS & CALLBACKS DE FILTRES ---
    def reset_filtres(niveau):
        if niveau <= 1:
            st.session_state.clubs_choisis = []
        st.session_state.joueurs_choisis = []

    for key, val in [("annee_choisie", None), ("clubs_choisis", []), ("joueurs_choisis", [])]:
        if key not in st.session_state:
            st.session_state[key] = val

    # --- INTERFACE UTILISATEUR ---
    st.subheader("🔍 Filtres de sélection (Multi-choix tactiles)")
    
    st.write("**📅 1. Sélectionnez l'Année :**")
    st.segmented_control(
        "Année", options=utils.charger_annees(conn), key="annee_choisie", 
        selection_mode="single", on_change=reset_filtres, args=(1,), label_visibility="collapsed"
    )

    if st.session_state.annee_choisie:
        st.markdown("---")
        st.write("**🏢 2. Sélectionnez les Clubs :**")
        st.segmented_control(
            "Clubs", options=utils.charger_clubs_par_annee(conn, st.session_state.annee_choisie), 
            key="clubs_choisis", selection_mode="multi", on_change=reset_filtres, args=(2,), label_visibility="collapsed"
        )

    if st.session_state.annee_choisie and st.session_state.clubs_choisis:
        st.markdown("---")
        st.write("**👤 3. Sélectionnez les Joueurs :**")
        st.segmented_control(
            "Joueurs", options=utils.charger_joueurs_complet(conn, st.session_state.annee_choisie, st.session_state.clubs_choisis), 
            key="joueurs_choisis", selection_mode="multi", label_visibility="collapsed"
        )

    # --- REQUÊTAGE ET TCD ---
    st.markdown("---")
    if not st.session_state.annee_choisie or not st.session_state.clubs_choisis:
        st.info("💡 Veuillez sélectionner une Année et au moins un Club.")
    else:
        req = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie).in_("Equipe1", st.session_state.clubs_choisis)
        if st.session_state.joueurs_choisis:
            req = req.in_("Joueur1", st.session_state.joueurs_choisis)

        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé pour ces critères.")
        else:
            # Création du TCD avec index complet
            tcd_bilan = df_res.pivot_table(
                index=["Equipe1", "Joueur1", "Annee", "ClassementJ1", "ClassementJ2"], 
                values=["Match", "VictoireJ1"], 
                aggfunc={"Match": "size", "VictoireJ1": "sum"}, 
                fill_value=0
            )

            # Calcul des indicateurs
            tcd_bilan["% Victoire"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match"]).fillna(0)) * 100
            tcd_bilan.columns = ["Matchs Joués", "Victoires", "% Victoire"]

            # Tri par Joueur puis par Année
            tcd_bilan = tcd_bilan.reset_index()
            tcd_bilan = tcd_bilan.sort_values(by=["Joueur1", "Annee"])
            tcd_bilan = tcd_bilan.set_index(["Equipe1", "Joueur1", "Annee", "ClassementJ1", "ClassementJ2"])

            st.subheader(f"📋 Synthèse ({len(df_res)} match(s) analysé(s))")
            
            # Affichage HTML avec alignement forcé en haut à gauche
            html_table = (
                tcd_bilan.style.format({"Matchs Joués": "{:,.0f}", "Victoires": "{:,.0f}", "% Victoire": "{:.1f}%"})
                .background_gradient(cmap="RdYlGn", subset=["% Victoire"], vmin=0, vmax=100, axis=0)
                .set_table_styles([
                    {
                        "selector": "th, td, th.row_heading, th.col_heading, td.data", 
                        "props": [
                            ("vertical-align", "top !important"), 
                            ("text-align", "left !important"), 
                            ("border", "1px solid #555555 !important"), 
                            ("padding", "8px !important")
                        ]
                    }
                ], overwrite=False)
                .to_html(escape=False)
            )
            st.write(html_table, unsafe_allow_html=True)
