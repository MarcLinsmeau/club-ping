# StatsEquipe.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur : Tableau par Joueur et par Semaine."""
    
    # --- ÉTAT DES SESSIONS & FILTRES ---
    def reset_filtres(niveau):
        if niveau <= 1: st.session_state.clubs_choisis = []
        st.session_state.divisions_choisies = None

    for key, val in [("annee_choisie", None), ("clubs_choisis", []), ("divisions_choisies", None)]:
        if key not in st.session_state: st.session_state[key] = val

    # --- INTERFACE ---
    st.subheader("🔍 Filtres")
    st.write("**📅 1. Année :**")
    st.segmented_control("Année", options=utils.charger_annees(conn), key="annee_choisie", selection_mode="single", on_change=reset_filtres, args=(1,), label_visibility="collapsed")

    if st.session_state.annee_choisie:
        st.write("**🏢 2. Clubs :**")
        st.segmented_control("Clubs", options=utils.charger_clubs_par_annee(conn, st.session_state.annee_choisie), key="clubs_choisis", selection_mode="multi", on_change=reset_filtres, args=(2,), label_visibility="collapsed")

    if st.session_state.annee_choisie and st.session_state.clubs_choisis:
        st.write("**🏆 3. Division :**")
        st.segmented_control("Divisions", options=utils.charger_equipes_complet(conn, st.session_state.annee_choisie, st.session_state.clubs_choisis), key="divisions_choisies", selection_mode="single", label_visibility="collapsed")

    # --- REQUÊTAGE ET TCD ---
    st.markdown("---")
    if not st.session_state.annee_choisie or not st.session_state.clubs_choisis or not st.session_state.divisions_choisies:
        st.info("💡 Veuillez sélectionner une Année, un Club et une Division.")
    else:
        req = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie).in_("Equipe1", st.session_state.clubs_choisis).eq("Division", st.session_state.divisions_choisies)
        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé.")
        else:
            # Groupement par Joueur et par Semaine
            tcd = df_res.groupby(["Joueur1", "Semaine"]).agg(
                Sélections=("MatchNonFF", "size"),
                Matchs_Joués=("Match", "size"),
                Victoires=("VictoireJ1", "sum")
            )
            
            # Calcul du %
            tcd["% Victoire"] = (tcd["Victoires"] / tcd["Matchs_Joués"] * 100).fillna(0)
            
            # Tri des semaines dans l'index
            tcd = tcd.sort_index(level="Semaine", key=lambda x: x.map(utils.parse_semaine))

            st.subheader(f"📋 Performances par joueur ({st.session_state.divisions_choisies})")
            
            # Affichage HTML avec alignement forcé
            html_table = (
                tcd.style.format({"Sélections": "{:.0f}", "Matchs_Joués": "{:.0f}", "Victoires": "{:.0f}", "% Victoire": "{:.1f}%"})
                .background_gradient(cmap="RdYlGn", subset=["% Victoire"], vmin=0, vmax=100, axis=0)
                .set_table_styles([
                    {"selector": "th, td, th.row_heading, th.col_heading, td.data", 
                     "props": [("vertical-align", "top !important"), ("text-align", "left !important"), 
                               ("border", "1px solid #555555 !important"), ("padding", "8px !important")]}
                ], overwrite=False)
                .to_html(escape=False)
            )
            st.write(html_table, unsafe_allow_html=True)
