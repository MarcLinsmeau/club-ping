# StatsEquipe.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur : Semaine, Equipe1, Equipe2 en index, Joueurs en colonnes."""
    
    # --- ÉTAT DES SESSIONS ---
    for key, val in [("annee_choisie", None), ("club_choisi", None), ("division_choisie", None)]:
        if key not in st.session_state:
            st.session_state[key] = val

    def reset_suivant(niveau):
        if niveau <= 1: st.session_state.club_choisi = None
        if niveau <= 2: st.session_state.division_choisie = None

    # --- INTERFACE ---
    st.subheader("🔍 Filtres de sélection")
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
            # 1. Calcul agrégé avec les nouveaux index
            df_g = df_res.groupby(["Semaine", "Equipe1", "Equipe2", "Joueur1"]).agg(
                Sélections=("MatchNonFF", "size"),
                Matchs_Joués=("Match", "size"),
                Victoires=("VictoireJ1", "sum"),
                Points=("PointsJ1", "sum")
            ).fillna(0)
            
            # 2. Tri des joueurs
            joueurs = sorted(df_g.index.get_level_values("Joueur1").unique())
            
            # 3. Construction du tableau
            df_list = []
            for joueur in joueurs:
                # On extrait les données pour ce joueur spécifique
                df_j = df_g.xs(joueur, level="Joueur1")[["Sélections", "Matchs_Joués", "Victoires", "Points"]]
                # On prépare les colonnes multi-indexées
                df_j.columns = pd.MultiIndex.from_product([[joueur], df_j.columns])
                df_list.append(df_j)
            
            # Concaténation horizontale
            df_pivot = pd.concat(df_list, axis=1).fillna(0)
            
            # Tri des index (Semaine d'abord, puis Equipes)
            df_pivot = df_pivot.sort_index(level="Semaine", key=lambda x: x.map(utils.parse_semaine))

            # 4. Ajout de la ligne TOTAL (en bas du tableau)
            total_row = pd.DataFrame(df_pivot.sum()).T
            total_row.index = pd.MultiIndex.from_tuples([("Total", "", "")], names=["Semaine", "Equipe1", "Equipe2"])
            df_pivot = pd.concat([df_pivot, total_row])

            st.subheader(f"📋 Synthèse hebdomadaire ({len(df_res)} match(s))")
            
            # 5. Affichage avec style quadrillé
            st_style = df_pivot.style.set_properties(**{'border': '1px solid #d3d3d3'}) \
                                     .set_table_styles([{'selector': 'th', 'props': [('border', '1px solid #d3d3d3')]}])

            hauteur_calc = (len(df_pivot) + 1) * 35 
            st.dataframe(st_style, use_container_width=True, height=hauteur_calc)
