# StatsEquipe.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur : Synthèse hebdomadaire avec filtres et affichage conditionnel propre."""
    
    # --- ÉTAT DES SESSIONS ---
    for key, val in [("annee_choisie", None), ("club_choisi", None), ("division_choisie", None)]:
        if key not in st.session_state: st.session_state[key] = val

    def reset_suivant(niveau):
        if niveau <= 1: st.session_state.club_choisi = None
        if niveau <= 2: st.session_state.division_choisie = None

    # --- INTERFACE ---
    st.subheader("🔍 Filtres de sélection")
    
    # 1. Année
    st.write("**📅 1. Année :**")
    st.segmented_control("Année", options=utils.charger_annees(conn), key="annee_choisie", 
                         selection_mode="single", on_change=reset_suivant, args=(1,), label_visibility="collapsed")

    # 2. Club (S'affiche uniquement si une année est sélectionnée)
    if st.session_state.annee_choisie:
        st.markdown("---")
        st.write("**🏢 2. Club :**")
        st.segmented_control("Club", options=utils.charger_clubs_par_annee(conn, st.session_state.annee_choisie), 
                             key="club_choisi", selection_mode="single", on_change=reset_suivant, args=(2,), label_visibility="collapsed")

    # 3. Division (S'affiche uniquement si un club est sélectionné)
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
            df_g = df_res.groupby(["Semaine", "Equipe2", "Joueur1"]).agg(
                Sélect=("MatchNonFF", "size"),
                Joués=("Match", "size"),
                Vict=("VictoireJ1", "sum"),
                Points=("PointsJ1", "sum")
            )
            
            # 2. Construction du tableau
            joueurs = sorted(df_g.index.get_level_values("Joueur1").unique())
            df_list = []
            for joueur in joueurs:
                df_j = df_g.xs(joueur, level="Joueur1")[["Sélect", "Joués", "Vict", "Points"]]
                df_j.columns = pd.MultiIndex.from_product([[joueur], df_j.columns])
                df_list.append(df_j)
            
            df_pivot = pd.concat(df_list, axis=1).fillna(0)
            df_pivot = df_pivot.sort_index(level="Semaine", key=lambda x: x.map(utils.parse_semaine))

            # 3. Conversion entier + suppression des zéros
            df_pivot = df_pivot.astype(int).replace(0, "")
            
            # 4. Total
            total_row = pd.DataFrame(df_pivot.replace("", 0).sum()).T.astype(int)
            total_row.index = pd.MultiIndex.from_tuples([("Total", "")], names=["Semaine", "Equipe2"])
            df_pivot = pd.concat([df_pivot, total_row])

            # 5. Affichage final
            st.subheader(f"📋 Synthèse hebdomadaire ({len(df_res)} match(s))")
            
            st_style = df_pivot.style.set_properties(**{'border': '1px solid #d3d3d3', 'text-align': 'center'}) \
                                     .set_table_styles([{'selector': 'th', 'props': [('border', '1px solid #d3d3d3')]}])
            
            hauteur_calc = (len(df_pivot) + 1) * 38
            
            st.dataframe(
                st_style, 
                use_container_width=True, 
                height=hauteur_calc
            )
