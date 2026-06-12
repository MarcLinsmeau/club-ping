# StatsJoueursAnnee.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur principal de l'application de statistiques annuelles des joueurs (Toutes années confondues)."""
    
    # --- ÉTAT DES SESSIONS & CALLBACKS DE FILTRES ---
    def reset_filtres():
        """Réinitialise le filtre descendant des joueurs lorsque les clubs changent."""
        st.session_state.joueurs_choisis = []

    # Initialisation des variables de session indispensables (sans la clé annee_choisie)
    for key, val in [("clubs_choisis", []), ("joueurs_choisis", [])]:
        if key not in st.session_state:
            st.session_state[key] = val

    # --- INTERFACE UTILISATEUR : FILTRES ACTIFS ---
    st.subheader("🔍 Filtres de sélection (Multi-choix tactiles)")
    
    # Nouvelle Étape 1 : Choix des clubs parmi TOUS les clubs de la base
    st.write("**🏢 1. Sélectionnez un ou plusieurs Clubs (Equipe 1) :**")
    st.segmented_control(
        "Clubs", options=utils.charger_clubs_uniques(conn), 
        key="clubs_choisis", selection_mode="multi", on_change=reset_filtres, label_visibility="collapsed"
    )

    # Nouvelle Étape 2 : Choix des joueurs (dépend uniquement des clubs sélectionnés, toutes années confondues)
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
        # Requête Supabase globale : on filtre uniquement sur les clubs et optionnellement les joueurs
        req = conn.table("test").select("*").in_("Equipe1", st.session_state.clubs_choisis)
        if st.session_state.joueurs_choisis:
            req = req.in_("Joueur1", st.session_state.joueurs_choisis)

        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé pour cette combinaison précise.")
        else:
            colonnes_requises = ["MatchNonFF", "Match", "VictoireJ1", "PointsJ1"]
            if not all(c in df_res.columns for c in colonnes_requises):
                st.error("Une ou plusieurs colonnes de calcul indispensables sont introuvables en base de données.")
                st.stop()
                
            # --- CONFIGURATION DU TCD SANS FILTRE D'ANNÉE ---
            tcd_bilan = df_res.pivot_table(
                index=["Equipe1", "Joueur1", "Annee", "ClassementJ1"], 
                values=colonnes_requises, 
                aggfunc={"MatchNonFF": "size", "Match": "size", "VictoireJ1": "sum", "PointsJ1": "sum"}, 
                fill_value=0
            ).reindex(columns=colonnes_requises)

            if tcd_bilan.empty:
                st.info("Données insuffisantes pour générer ce tableau croisé.")
            else:
                # Forçage du format String sur le niveau de l'index 'Annee'
                tcd_bilan.index = tcd_bilan.index.set_levels(tcd_bilan.index.levels[2].astype(str), level=2)
                
                # Tri de l'index par Équipe, Joueur, puis Année chronologique
                tcd_bilan = tcd_bilan.sort_index(level=["Equipe1", "Joueur1", "Annee"])
                
                # Calcul des performances
                tcd_bilan["Taux Victoires"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match"]).fillna(0)) * 100
                tcd_bilan = tcd_bilan[["MatchNonFF", "Match", "VictoireJ1", "Taux Victoires", "PointsJ1"]]
                
                # Renommage des colonnes
                tcd_bilan.columns = ["Sélections", "Matchs Joués", "Matchs Gagnés", "% Victoires", "Points Gagnés J1"]

                st.subheader(f"📋 Tableau de synthèse multi-saisons ({len(df_res)} match(s) analysé(s))")
                
                # Génération HTML propre
                html_table = (
                    tcd_bilan.style.format({"Sélections": "{:,.0f}", "Matchs Joués": "{:,.0f}", "Matchs Gagnés": "{:,.0f}", "% Victoires": "{:.1f}%", "Points Gagnés J1": "{:+.0f}"})
                    .background_gradient(cmap="RdYlGn", subset=["% Victoires"], vmin=0, vmax=100, axis=0)
                    .set_table_styles([
                        {"selector": "th, td, th.row_heading, th.col_heading, td.data, .blank", "props": [("vertical-align", "top !important"), ("text-align", "left !important"), ("border", "1px solid #555555 !important"), ("padding", "8px !important")]}
                    ], overwrite=False)
                    .to_html(escape=False)
                )
                
                st.write(html_table, unsafe_allow_html=True)
