# StatsEquipe.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur : Semaine et Indicateurs en index, Joueurs en colonnes (Stable)."""
    
    # --- ÉTAT DES SESSIONS ---
    def reset_filtres(niveau):
        if niveau <= 1: st.session_state.clubs_choisis = []
        st.session_state.divisions_choisies = []

    for key, val in [("annee_choisie", None), ("clubs_choisis", []), ("divisions_choisies", [])]:
        if key not in st.session_state: st.session_state[key] = val

    # --- INTERFACE ---
    st.subheader("🔍 Filtres de sélection")
    st.write("**📅 1. Année :**")
    st.segmented_control("Année", options=utils.charger_annees(conn), key="annee_choisie", 
                        selection_mode="single", on_change=reset_filtres, args=(1,), label_visibility="collapsed")

    if st.session_state.annee_choisie:
        st.write("**🏢 2. Clubs :**")
        st.segmented_control("Clubs", options=utils.charger_clubs_par_annee(conn, st.session_state.annee_choisie), 
                            key="clubs_choisis", selection_mode="multi", on_change=reset_filtres, args=(2,), label_visibility="collapsed")

    if st.session_state.annee_choisie and st.session_state.clubs_choisis:
        st.write("**🏆 3. Divisions :**")
        st.segmented_control("Divisions", options=utils.charger_equipes_complet(conn, st.session_state.annee_choisie, st.session_state.clubs_choisis), 
                            key="divisions_choisies", selection_mode="multi", label_visibility="collapsed")

    # --- REQUÊTAGE ET TCD ---
    st.markdown("---")
    if not st.session_state.annee_choisie or not st.session_state.clubs_choisis or not st.session_state.divisions_choisies:
        st.info("💡 Veuillez sélectionner une Année, un Club et au moins une Division.")
    else:
        req = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie).in_("Equipe1", st.session_state.clubs_choisis).in_("Division", st.session_state.divisions_choisies)
        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé.")
        else:
            # 1. Calcul agrégé
            df_g = df_res.groupby(["Semaine", "Joueur1"]).agg(
                Sélections=("MatchNonFF", "size"),
                Matchs_Joués=("Match", "size"),
                Victoires=("VictoireJ1", "sum")
            )
            df_g["% Victoire"] = (df_g["Victoires"] / df_g["Matchs_Joués"] * 100).fillna(0)
            
            # 2. Transposition
            df_pivot = df_g.stack().unstack(level="Joueur1")
            df_pivot = df_pivot.sort_index(key=lambda x: x.map(utils.parse_semaine))

            # 3. Formatage manuel des données pour éviter les bugs de style
            def appliquer_format(val, row_name):
                if row_name == "% Victoire":
                    return f"{val:.1f}%"
                return f"{int(val)}"

            df_display = df_pivot.copy()
            for idx in df_display.index:
                semaine, indicateur = idx
                df_display.loc[idx] = [appliquer_format(val, indicateur) for val in df_pivot.loc[idx]]

            st.subheader(f"📋 Synthèse hebdomadaire ({len(df_res)} match(s))")
            
            # 4. Affichage simple et robuste
            st.dataframe(df_display, use_container_width=True)
