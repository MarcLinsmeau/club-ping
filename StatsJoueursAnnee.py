# StatsJoueursAnnee.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur principal de l'application de statistiques annuelles des joueurs (TCD par Année sans totaux)."""
    
    # --- ÉTAT DES SESSIONS & CALLBACKS DE FILTRES ---
    def reset_filtres(niveau):
        """Réinitialise en cascade les filtres descendants."""
        if niveau <= 1:
            st.session_state.clubs_choisis = []
        st.session_state.joueurs_choisis = []

    # Initialisation des variables de session indispensables aux contrôles tactiles
    for key, val in [("annee_choisie", None), ("clubs_choisis", []), ("joueurs_choisis", [])]:
        if key not in st.session_state:
            st.session_state[key] = val

    # --- INTERFACE UTILISATEUR : FILTRES ACTIFS ---
    st.subheader("🔍 Filtres de sélection (Multi-choix tactiles)")
    
    # Étape 1 : Choix de l'année
    st.write("**📅 1. Sélectionnez l'Année de recherche :**")
    st.segmented_control(
        "Année", options=utils.charger_annees(conn), key="annee_choisie", 
        selection_mode="single", on_change=reset_filtres, args=(1,), label_visibility="collapsed"
    )

    # Étape 2 : Choix des clubs (dépend de l'année sélectionnée)
    if st.session_state.annee_choisie:
        st.markdown("---")
        st.write("**🏢 2. Sélectionnez un ou plusieurs Clubs (Equipe 1) :**")
        st.segmented_control(
            "Clubs", options=utils.charger_clubs_par_annee(conn, st.session_state.annee_choisie), 
            key="clubs_choisis", selection_mode="multi", on_change=reset_filtres, args=(2,), label_visibility="collapsed"
        )

    # Étape 3 : Choix des joueurs (dépend de l'année et du club sélectionnés)
    if st.session_state.annee_choisie and st.session_state.clubs_choisis:
        st.markdown("---")
        st.write("**👤 3. Sélectionnez un ou plusieurs Joueurs (Joueur 1) :**")
        st.segmented_control(
            "Joueurs", options=utils.charger_joueurs_complet(conn, st.session_state.annee_choisie, st.session_state.clubs_choisis), 
            key="joueurs_choisis", selection_mode="multi", label_visibility="collapsed"
        )

    # --- SÉCURITÉ DE CONTRÔLE ET REQUÊTAGE ---
    st.markdown("---")
    if not st.session_state.annee_choisie:
        st.info("💡 En attente de vos critères : Veuillez cocher une **Année** pour commencer.")
    elif not st.session_state.clubs_choisis:
        st.info("💡 Étape suivante : Veuillez cocher au moins un **Club** pour charger les joueurs correspondants.")
    else:
        # Requête Supabase filtrée
        req = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie).in_("Equipe1", st.session_state.clubs_choisis)
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
                
            # --- 1. CONFIGURATION DU TCD SANS TOTAUX ---
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
                
                # Tri de l'index par Équipe puis par Joueur
                tcd_bilan = tcd_bilan.sort_index(level=["Equipe1", "Joueur1"])
                
                # Calcul des performances directes
                tcd_bilan["Taux Victoires"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match"]).fillna(0)) * 100
                tcd_bilan = tcd_bilan[["MatchNonFF", "Match", "VictoireJ1", "Taux Victoires", "PointsJ1"]]
                
                # Renommage des colonnes selon vos exigences
                tcd_bilan.columns =
