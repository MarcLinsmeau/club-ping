# StatsEquipe.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur : Semaine, Equipe2 en index, Joueurs en colonnes (Entiers)."""
    
    # --- ÉTAT DES SESSIONS & INTERFACE ---
    for key, val in [("annee_choisie", None), ("club_choisi", None), ("division_choisie", None)]:
        if key not in st.session_state: st.session_state[key] = val

    def reset_suivant(niveau):
        if niveau <= 1: st.session_state.club_choisi = None
        if niveau <= 2: st.session_state.division_choisie = None

    st.subheader("🔍 Filtres de sélection")
    st.segmented_control("Année", options=utils.charger_annees(conn), key="annee_choisie", selection_mode="single", on_change=reset_suivant, args=(1,), label_visibility="collapsed")
    if st.session_state.annee_choisie:
        st.segmented_control("Club", options=utils.charger_clubs_par_annee(conn, st.session_state.annee_choisie), key="club_choisi", selection_mode="single", on_change=reset_suivant, args=(2,), label_visibility="collapsed")
    if st.session_state.annee_choisie and st.session_state.club_choisi:
        st.segmented_control("Division", options=utils.charger_equipes_complet(conn, st.session_state.annee_choisie, [st.session_state.club_choisi]), key="division_choisie", selection_mode="single", label_visibility="collapsed")

    # --- REQUÊTAGE ET TCD ---
    if not (st.session_state.annee_choisie and st.session_state.club_choisi and st.session_state.division_choisie):
        st.info("💡 Veuillez sélectionner une Année, un Club et une Division.")
    else:
        req = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie).eq("Equipe1", st.session_state.club_choisi).eq("Division", st.session_state.division_choisie)
        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé.")
        else:
            # 1. Calcul agrégé (Equipe1 retiré de l'index)
            df_g = df_res.groupby(["Semaine", "Equipe2", "Joueur1"]).agg(
                Sélect=("MatchNonFF", "size"),
                Joués=("Match", "size"),
                Vict=("VictoireJ1", "sum"),
                Points=("PointsJ1", "sum")
            ).fillna(0)
            
            # 2. Tri joueurs
            joueurs = sorted(df_g.index.get_level_values("Joueur1").unique())
            
            # 3. Construction + conversion en Int64
            df_list = []
            for joueur in joueurs:
                df_j = df_g.xs(joueur, level="Joueur1")[["Sélect", "Joués", "Vict", "Points"]].astype('Int64')
                df_j.columns = pd.MultiIndex.from_product([[joueur], df_j.columns])
                df_list.append(df_j)
            
            df_pivot = pd.concat(df_list, axis=1).fillna(0).astype('Int64')
            df_pivot = df_pivot.sort_index(level="Semaine", key=lambda x: x.map(utils.parse_semaine))

            # 4. Total (Index ajusté avec 2 niveaux : Semaine, Equipe2)
            total_row = pd.DataFrame(df_pivot.sum()).T.astype('Int64')
            total_row.index = pd.MultiIndex.from_tuples([("Total", "")], names=["Semaine", "Equipe2"])
            df_pivot = pd.concat([df_pivot, total_row])

            # 5. Affichage avec style
            st.subheader(f"📋 Synthèse hebdomadaire ({len(df_res)} match(s))")
            st_style = df_pivot.style.set_properties(**{'border': '1px solid #d3d3d3'}) \
                                     .set_table_styles([{'selector': 'th', 'props': [('border', '1px solid #d3d3d3')]}])
            
            st.dataframe(st_style, use_container_width=True, height=(len(df_pivot) + 1) * 35)
