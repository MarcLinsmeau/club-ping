import streamlit as st
import pandas as pd
import altair as alt
from st_supabase_connection import SupabaseConnection

# --- IMPORTATION DE VOS FONCTIONS CENTRALISÉES ---
import utils 

mode = st.query_params.get("mode", "StatsJoueursSemaine")
st.set_page_config(page_title="Ping-Point - Recherche", page_icon="🏓", layout="wide")
st.title(f"🏓 Recherche Avancée des Statistiques - {mode}")

try:
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- ÉTAT DES SESSIONS & CALLBACKS ---
    def reset_filtres(niveau):
        if niveau <= 1:
            st.session_state.clubs_choisis = []
        st.session_state.joueurs_choisis = []

    for key, val in [("annee_choisie", None), ("clubs_choisis", []), ("joueurs_choisis", [])]:
        if key not in st.session_state:
            st.session_state[key] = val

    # --- INTERFACE UTILISATEUR (Appels via le module utils) ---
    st.subheader("🔍 Filtres de sélection")
    
    # Remplacement par utils.nom_fonction(conn)
    st.write("**📅 1. Sélectionnez l'Année de recherche :**")
    st.segmented_control("Année", options=utils.charger_annees(conn), key="annee_choisie", selection_mode="single", on_change=reset_filtres, args=(1,), label_visibility="collapsed")

    if st.session_state.annee_choisie:
        st.markdown("---")
        st.write("**🏢 2. Sélectionnez un ou plusieurs Clubs :**")
        st.segmented_control("Clubs", options=utils.charger_clubs(conn, st.session_state.annee_choisie), key="clubs_choisis", selection_mode="multi", on_change=reset_filtres, args=(2,), label_visibility="collapsed")

    if st.session_state.annee_choisie and st.session_state.clubs_choisis:
        st.markdown("---")
        st.write("**👤 3. Sélectionnez un ou plusieurs Joueurs :**")
        st.segmented_control("Joueurs", options=utils.charger_joueurs(conn, st.session_state.annee_choisie, st.session_state.clubs_choisis), key="joueurs_choisis", selection_mode="multi", label_visibility="collapsed")

    # --- REQUÊTE PRINCIPALE & TRAITEMENT ---
    st.markdown("---")
    if not st.session_state.annee_choisie:
        st.info("💡 En attente d'une année...")
    elif not st.session_state.clubs_choisis:
        st.info("💡 En attente d'un club...")
    else:
        req = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie).in_("Equipe1", st.session_state.clubs_choisis)
        if st.session_state.joueurs_choisis:
            req = req.in_("Joueur1", st.session_state.joueurs_choisis)

        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé.")
        else:
            colonnes_requises = ["MatchNonFF", "Match", "VictoireJ1", "PointsJ1"]
            if not all(c in df_res.columns for c in colonnes_requises):
                st.error("Colonnes manquantes.")
                st.stop()
                
            tcd_base = df_res.pivot_table(index=["Equipe1", "Joueur1", "ClassementJ1", "Division", "Semaine"], values=colonnes_requises, aggfunc={"MatchNonFF": "size", "Match": "size", "VictoireJ1": "sum", "PointsJ1": "sum"}, fill_value=0).reindex(columns=colonnes_requises)

            if tcd_base.empty:
                st.info("Données insuffisantes.")
            else:
                tcd_base.index = tcd_base.index.set_levels(tcd_base.index.levels[4].astype(str), level=4)

                # --- ZONE GRAPHES (Utilisation de utils.parse_semaine) ---
                if len(st.session_state.joueurs_choisis) == 1:
                    st.subheader(f"📊 Analyse Graphique — {st.session_state.joueurs_choisis[0]}")
                    
                    df_graph = tcd_base.reset_index()
                    df_graph["semaine_num"] = df_graph["Semaine"].map(utils.parse_semaine)
                    df_graph = df_graph.sort_values(by="semaine_num")
                    df_graph["Points Cumulés"] = df_graph["PointsJ1"].cumsum()
                    
                    chart_base = alt.Chart(df_graph).encode(x=alt.X("Semaine:N", sort=alt.SortField(field="semaine_num", order="ascending")))
                    barres = chart_base.mark_bar(color="#22c55e").encode(y=alt.Y("PointsJ1:Q"))
                    labels_pos = chart_base.mark_text(dy=-10, align="center", fontWeight="bold").transform_filter("datum.PointsJ1 >= 0").encode(y="PointsJ1:Q", text=alt.Text("PointsJ1:Q", format="+d"))
                    labels_neg = chart_base.mark_text(dy=10, align="center", fontWeight="bold").transform_filter("datum.PointsJ1 < 0").encode(y="PointsJ1:Q", text=alt.Text("PointsJ1:Q", format="+d"))
                    st.altair_chart(barres + labels_pos + labels_neg, use_container_width=True)
                    
                    chart_cumul = alt.Chart(df_graph).encode(x=alt.X("Semaine:N", sort=alt.SortField(field="semaine_num", order="ascending")), y="Points Cumulés:Q")
                    courbe = chart_cumul.mark_line(color="#3b82f6", strokeWidth=3)
                    points = chart_cumul.mark_circle(color="#3b82f6", size=60)
                    labels_cumul = chart_cumul.mark_text(dy=-12, align="center", fontWeight="bold").encode(text=alt.Text("Points Cumulés:Q", format="d"))
                    st.altair_chart(courbe + points + labels_cumul, use_container_width=True)
                    st.markdown("---")

                # --- CALCUL DU BILAN (Utilisation de utils.parse_semaine) ---
                totaux = tcd_base.groupby(level=["Equipe1", "Joueur1"]).sum()
                totaux["ClassementJ1"], totaux["Division"], totaux["Semaine"] = "Total Saison", "", ""
                totaux = totaux.set_index(["ClassementJ1", "Division", "Semaine"], append=True)
                
                tcd_bilan = pd.concat([tcd_base, totaux]).sort_index(level=["Equipe1", "Joueur1", "Semaine"], key=lambda x: x.map(utils.parse_semaine) if x.name == "Semaine" else x)
                tcd_bilan["Taux Victoires"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match"]).fillna(0)) * 100
                tcd_bilan = tcd_bilan[["MatchNonFF", "Match", "VictoireJ1", "Taux Victoires", "PointsJ1"]]
                tcd_bilan.columns = ["Sélections", "Matchs Joués", "Matchs Gagnés", "% Victoires", "Points Gagnés J1"]

                def injection_style_ligne(row):
                    return ["font-weight: bold !important;" + (" background-color: #edf2f7 !important;" if c != "% Victoires" else "") if "Total Saison" in row.name else "" for c in row.index]

                st.subheader(f"📋 Tableau de synthèse")
                html_table = (
                    tcd_bilan.style.format({"Sélections": "{:,.0f}", "Matchs Joués": "{:,.0f}", "Matchs Gagnés": "{:,.0f}", "% Victoires": "{:.1f}%", "Points Gagnés J1": "{:+.0f}"})
                    .background_gradient(cmap="RdYlGn", subset=["% Victoires"], vmin=0, vmax=100, axis=0)
                    .apply(injection_style_ligne, axis=1)
                    .set_table_styles([
                        {"selector": "th, td, th.row_heading, th.col_heading, td.data, .blank", "props": [("vertical-align", "top !important"), ("text-align", "left !important"), ("border", "1px solid #555555 !important"), ("padding", "8px !important")]},
                        {"selector": "tr:has(th:contains('Total Saison')) th", "props": [("font-weight", "bold !important"), ("background-color", "#edf2f7 !important")]}
                    ], overwrite=False).to_html(escape=False)
                )
                st.write(html_table, unsafe_allow_html=True)
                
except Exception as e:
    st.error("Erreur technique.")
    st.exception(e)
