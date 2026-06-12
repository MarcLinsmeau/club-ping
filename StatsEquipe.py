# StatsEquipe.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur : Semaine (index), Joueurs (colonnes), 4 métriques, avec 0 pour les vides."""
    
    # --- ÉTAT DES SESSIONS ---
    for key, val in [("annee_choisie", None), ("club_choisi", None), ("division_choisie", None)]:
        if key not in st.session_state:
            st.session_state[key] = val

    # --- CALLBACKS ---
    def reset_suivant(niveau):
        if niveau <= 1: st.session_state.club_choisi = None
        if niveau <= 2: st.session_state.division_choisie = None

    # --- INTERFACE ---
    st.subheader("🔍 Filtres de sélection (Unique)")
    
    st.write("**📅 1. Année :**")
    st.segmented_control("Année", options=utils.charger_annees(conn), key="annee_choisie", 
                        selection_mode="single", on_change=reset_suivant, args=(1,), label_visibility="collapsed")

    if st.session_state.annee_choisie:
        st.markdown("---")
        st.write("**🏢 2. Club :**")
        st.segmented_control("Club", options=utils.charger_clubs_par_annee(conn, st.session_state.annee_choisie), 
                            key="club_choisi", selection_mode="single", on_change=reset_suivant, args=(2,), label_visibility="collapsed")

    if st.session_state.annee_choisie and st.session_state.club_choisi:
        st.markdown("---")
        st.write("**🏆 3. Division :**")
        st.segmented_control("Division", options=utils.charger_equipes_complet(conn, st.session_state.annee_choisie, [st.session_state.club_choisi]), 
                            key="division_choisie", selection_mode="single", label_visibility="collapsed")

    # --- REQUÊTAGE ET TCD ---
    st.markdown("---")
    if not (st.session_state.annee_choisie and st.session_state.club_choisi and st.session_state.division_choisie):
        st.info("💡 Veuillez sélectionner une Année, un Club et une Division.")
    else:
        req = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie)\
                                       .eq("Equipe1", st.session_state.club_choisi)\
                                       .eq("Division", st.session_state.division_choisie)

        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé.")
        else:
            # 1. Calcul agrégé
            df_g = df_res.groupby(["Semaine", "Joueur1"]).agg(
                Sélections=("MatchNonFF", "size"),
                Matchs_Joués=("Match", "size"),
                Victoires=("VictoireJ1", "sum"),
                Points=("PointsJ1", "sum")
            ).fillna(0)
            
            # 2. Récupération et TRI ALPHABÉTIQUE des joueurs
            joueurs = sorted(df_g.index.get_level_values("Joueur1").unique())
            
            # 3. Construction du tableau avec ordre forcé des métriques
            df_list = []
            for joueur in joueurs:
                df_j = df_g.xs(joueur, level="Joueur1")[["Sélections", "Matchs_Joués", "Victoires", "Points"]]
                df_j.columns = pd.MultiIndex.from_product([[joueur], df_j.columns])
                df_list.append(df_j)
            
            # 4. Concaténation, remplacement des vides par 0, et tri chronologique
            df_pivot = pd.concat(df_list, axis=1).fillna(0).sort_index(key=lambda x: x.map(utils.parse_semaine))

            st.subheader(f"📋 Synthèse hebdomadaire ({len(df_res)} match(s))")
            
            # 5. Affichage final
            st.dataframe(df_pivot, use_container_width=True)
