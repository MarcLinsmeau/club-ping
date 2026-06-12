# StatsEquipe.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur : TCD avec Joueurs en lignes et Semaines en colonnes."""
    
    # --- ÉTAT DES SESSIONS & CALLBACKS ---
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
            # 1. Calcul par Joueur et par Semaine
            tcd = df_res.groupby(["Joueur1", "Semaine"]).agg(
                Sélections=("MatchNonFF", "size"),
                Matchs_Joués=("Match", "size"),
                Victoires=("VictoireJ1", "sum")
            )
            tcd["% Victoire"] = (tcd["Victoires"] / tcd["Matchs_Joués"] * 100).fillna(0)
            
            # 2. Inversion : Joueurs en index, Semaines en colonnes (avec les 4 indicateurs en sous-index)
            # On utilise stack() pour mettre les indicateurs en colonnes, puis unstack() pour les semaines
            df_pivot = tcd.unstack(level="Semaine")
            
            # Tri des colonnes Semaines chronologiquement
            df_pivot = df_pivot.sort_index(axis=1, level="Semaine", key=lambda x: x.map(utils.parse_semaine))

            st.subheader(f"📋 Synthèse par Joueur ({len(df_res)} match(s))")
            
            # 3. Affichage HTML
            html_table = (
                df_pivot.style.format("{:.0f}")
                .format({c: "{:.1f}%" for c in df_pivot.columns if c[0] == "% Victoire"})
                .background_gradient(cmap="Blues", subset=pd.IndexSlice[:, pd.IndexSlice["Victoires", :]], axis=None)
                .set_table_styles([
                    {"selector": "th, td, th.row_heading, th.col_heading, td.data", 
                     "props": [("vertical-align", "top !important"), ("text-align", "left !important"), 
                               ("border", "1px solid #555555 !important"), ("padding", "8px !important")]}
                ], overwrite=False)
                .to_html(escape=False)
            )
            st.write(html_table, unsafe_allow_html=True)
