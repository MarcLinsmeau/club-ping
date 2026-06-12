# StatsEquipe.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur : Semaine, Joueurs et Totaux avec quadrillage accentué."""
    
    # ... (partie filtres identique au code précédent) ...
    # --- ÉTAT DES SESSIONS & INTERFACE ---
    # (Je raccourcis cette partie pour la lisibilité, gardez votre version)
    # ... 

    # --- REQUÊTAGE ET TCD ---
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
            # Agrégation et pivot
            df_g = df_res.groupby(["Semaine", "Joueur1"]).agg(
                Sélections=("MatchNonFF", "size"),
                Matchs_Joués=("Match", "size"),
                Victoires=("VictoireJ1", "sum"),
                Points=("PointsJ1", "sum")
            ).fillna(0)
            
            joueurs = sorted(df_g.index.get_level_values("Joueur1").unique())
            df_list = []
            for joueur in joueurs:
                df_j = df_g.xs(joueur, level="Joueur1")[["Sélections", "Matchs_Joués", "Victoires", "Points"]]
                df_j.columns = pd.MultiIndex.from_product([[joueur], df_j.columns])
                df_list.append(df_j)
            
            df_pivot = pd.concat(df_list, axis=1).fillna(0).sort_index(key=lambda x: x.map(utils.parse_semaine))
            
            # Total
            total_row = pd.DataFrame(df_pivot.sum()).T
            total_row.index = ["Total"]
            df_pivot = pd.concat([df_pivot, total_row])

            # Affichage avec style CSS pour le quadrillage
            st.subheader(f"📋 Synthèse hebdomadaire ({len(df_res)} match(s))")
            
            # Application du style pour le quadrillage
            st_style = df_pivot.style.set_properties(**{'border': '1px solid #d3d3d3'}) \
                                     .set_table_styles([{'selector': 'th', 'props': [('border', '1px solid #d3d3d3')]}] )

            hauteur_calc = (len(df_pivot) + 1) * 35 
            st.dataframe(st_style, use_container_width=True, height=hauteur_calc)
