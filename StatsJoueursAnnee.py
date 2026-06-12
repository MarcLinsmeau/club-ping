# StatsJoueursAnnee.py
import streamlit as st
import pandas as pd
import utils  # Conservé au cas où d'autres fonctions du module resteraient requises

def execution_app(conn):
    """Conteneur principal de l'application de statistiques annuelles des joueurs (TCD par Année)."""
    
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
                
            # --- 1. CONFIGURATION DU NOUVEL INDEX SUR LE TCD ---
            # Index demandé : Equipe1, Joueur1, Annee, ClassementJ1
            tcd_base = df_res.pivot_table(
                index=["Equipe1", "Joueur1", "Annee", "ClassementJ1"], 
                values=colonnes_requises, 
                aggfunc={"MatchNonFF": "size", "Match": "size", "VictoireJ1": "sum", "PointsJ1": "sum"}, 
                fill_value=0
            ).reindex(columns=colonnes_requises)

            if tcd_base.empty:
                st.info("Données insuffisantes pour générer ce tableau croisé.")
            else:
                # Forçage du format String sur le niveau de l'index 'Annee' pour éviter les formats numériques
                tcd_base.index = tcd_base.index.set_levels(tcd_base.index.levels[2].astype(str), level=2)

                # --- 2. CALCUL DU RESUMÉ & CALCULS DES LIGNES TOTAL ---
                # Génération des sous-totaux par bloc de joueurs
                totaux = tcd_base.groupby(level=["Equipe1", "Joueur1"]).sum()
                
                # Alignement de l'index des totaux sur la nouvelle structure (4 niveaux)
                totaux["Annee"], totaux["ClassementJ1"] = "Total Saison", ""
                totaux = totaux.set_index(["Annee", "ClassementJ1"], append=True)
                
                # Fusion et tri alphabétique des index
                tcd_bilan = pd.concat([tcd_base, totaux]).sort_index(level=["Equipe1", "Joueur1"])
                
                # Calculs des ratios de performance
                tcd_bilan["Taux Victoires"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match"]).fillna(0)) * 100
                tcd_bilan = tcd_bilan[["MatchNonFF", "Match", "VictoireJ1", "Taux Victoires", "PointsJ1"]]
                
                # Renommage des colonnes selon vos exigences
                tcd_bilan.columns = ["Sélections", "Matchs Joués", "Matchs Gagnés", "% Victoires", "Points Gagnés J1"]

                # Règle CSS personnalisée pour mettre en valeur les lignes de totaux
                def injection_style_ligne(row):
                    return ["font-weight: bold !important;" + (" background-color: #edf2f7 !important;" if c != "% Victoires" else "") if "Total Saison" in row.name else "" for c in row.index]

                st.subheader(f"📋 Tableau de synthèse des performances ({len(df_res)} match(s) analysé(s))")
                
                # Génération HTML de la table avec son dégradé conditionnel
                html_table = (
                    tcd_bilan.style.format({"Sélections": "{:,.0f}", "Matchs Joués": "{:,.0f}", "Matchs Gagnés": "{:,.0f}", "% Victoires": "{:.1f}%", "Points Gagnés J1": "{:+.0f}"})
                    .background_gradient(cmap="RdYlGn", subset=["% Victoires"], vmin=0, vmax=100, axis=0)
                    .apply(injection_style_ligne, axis=1)
                    .set_table_styles([
                        {"selector": "th, td, th.row_heading, th.col_heading, td.data, .blank", "props": [("vertical-align", "top !important"), ("text-align", "left !important"), ("border", "1px solid #555555 !important"), ("padding", "8px !important")]},
                        {"selector": "tr:has(th:contains('Total Saison')) th", "props": [("font-weight", "bold !important"), ("background-color", "#edf2f7 !important")]}
                    ], overwrite=False)
                    .to_html(escape=False)
                )
                
                # Rendu du tableau final épuré
                st.write(html_table, unsafe_allow_html=True)
