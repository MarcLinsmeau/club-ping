import streamlit as st
import pandas as pd
import altair as alt
import re
from st_supabase_connection import SupabaseConnection

# 1. Récupérer le paramètre 'mode' depuis l'URL (ex: https://monapp.streamlit.app/?mode=ping)
# Si aucun paramètre n'est fourni, on définit un mode par défaut
mode = st.query_params.get("mode", "Marc")

# Configuration initiale de la page
st.set_page_config(page_title="Ping Club - Recherche", page_icon="🏓", layout="wide")
st.title(f"🏓 Recherche Avancée des Matchs - {mode}")

try:
    # 1. Connexion à Supabase
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- REQUÊTES DATA (RPC ET TABLES) ---
    @st.cache_data(ttl=300)
    def charger_annees():
        res = conn.client.rpc("obtenir_annees_uniques").execute()
        return [str(row["annee"]) for row in res.data] if res.data else []

    @st.cache_data(ttl=300)
    def charger_clubs(annee):
        res = conn.client.rpc("obtenir_clubs_par_annee", {"annee_recherche": annee}).execute()
        return [row["club"] for row in res.data] if res.data else []

    @st.cache_data(ttl=300)
    def charger_joueurs(annee, liste_clubs):
        res = conn.table("test").select("Joueur1").eq("Annee", annee).in_("Equipe1", liste_clubs).execute()
        return sorted(list({row["Joueur1"] for row in res.data if row.get("Joueur1")})) if res.data else []

    # --- CALLBACKS ET ETAT DE SESSIONS ---
    def reset_filtres(niveau):
        if niveau <= 1:
            st.session_state.clubs_choisis = []
        st.session_state.joueurs_choisis = []

    for key, val in [("annee_choisie", None), ("clubs_choisis", []), ("joueurs_choisis", [])]:
        if key not in st.session_state:
            st.session_state[key] = val

    # --- INTERFACE UTILISATEUR (FILTRES TACTILES) ---
    st.subheader("🔍 Filtres de sélection (Multi-choix tactiles)")

    st.write("**📅 1. Sélectionnez l'Année de recherche :**")
    st.segmented_control(
        "Année", options=charger_annees(), key="annee_choisie", 
        selection_mode="single", on_change=reset_filtres, args=(1,), label_visibility="collapsed"
    )

    if st.session_state.annee_choisie:
        st.markdown("---")
        st.write("**🏢 2. Sélectionnez un ou plusieurs Clubs (Equipe 1) :**")
        st.segmented_control(
            "Clubs", options=charger_clubs(st.session_state.annee_choisie), key="clubs_choisis", 
            selection_mode="multi", on_change=reset_filtres, args=(2,), label_visibility="collapsed"
        )

    if st.session_state.annee_choisie and st.session_state.clubs_choisis:
        st.markdown("---")
        st.write("**👤 3. Sélectionnez un ou plusieurs Joueurs (Joueur 1) :**")
        st.segmented_control(
            "Joueurs", options=charger_joueurs(st.session_state.annee_choisie, st.session_state.clubs_choisis), 
            key="joueurs_choisis", selection_mode="multi", label_visibility="collapsed"
        )

    # --- CONTROLE LOGIQUE ET REQUÊTE PRINCIPALE ---
    st.markdown("---")
    if not st.session_state.annee_choisie:
        st.info("💡 En attente de vos critères : Veuillez cocher une **Année** pour commencer.")
    elif not st.session_state.clubs_choisis:
        st.info("💡 Étape suivante : Veuillez cocher au moins un **Club** pour charger les joueurs correspondants.")
    else:
        req = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie).in_("Equipe1", st.session_state.clubs_choisis)
        if st.session_state.joueurs_choisis:
            req = req.in_("Joueur1", st.session_state.joueurs_choisis)

        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé pour cette combinaison précise.")
        else:
            colonnes_requises = ["MatchNonFF", "Match", "VictoireJ1", "PointsJ1"]
            if not all(c in df_res.columns for c in colonnes_requises):
                st.error("Une ou plusieurs colonnes de calcul ('MatchNonFF', 'Match', 'VictoireJ1', 'PointsJ1') sont introuvables.")
                st.stop()
                
            # 1. Pivot de Table initial
            tcd_base = df_res.pivot_table(
                index=["Equipe1", "Joueur1", "ClassementJ1", "Division", "Semaine"], 
                values=colonnes_requises, 
                aggfunc={"MatchNonFF": "size", "Match": "size", "VictoireJ1": "sum", "PointsJ1": "sum"}, 
                fill_value=0
            ).reindex(columns=colonnes_requises)

            if tcd_base.empty:
                st.info("Données insuffisantes pour générer ce tableau croisé.")
            else:
                tcd_base.index = tcd_base.index.set_levels(tcd_base.index.levels[4].astype(str), level=4)
                
                # Extraction numérique des semaines
                def parse_semaine(val):
                    if val == "": return -1
                    digits = re.findall(r'\d+', str(val))
                    return int(digits[0]) if digits else 0

                # --- BLOC GRAPHES IMMUNISÉ CONTRE L'ERREUR SCHEMA DY ---
                if len(st.session_state.joueurs_choisis) == 1:
                    st.subheader(f"📊 Analyse Graphique — {st.session_state.joueurs_choisis[0]}")
                    
                    df_graph = tcd_base.reset_index()
                    df_graph["semaine_num"] = df_graph["Semaine"].map(parse_semaine)
                    df_graph = df_graph.sort_values(by="semaine_num")
                    df_graph["Points Cumulés"] = df_graph["PointsJ1"].cumsum()
                    
                    # Graphique 1 : Histogramme de base
                    st.write("**Points gagnés / perdus par semaine**")
                    chart_base = alt.Chart(df_graph).encode(
                        x=alt.X("Semaine:N", sort=alt.SortField(field="semaine_num", order="ascending"))
                    )
                    
                    barres = chart_base.mark_bar(color="#22c55e").encode(y=alt.Y("PointsJ1:Q"))
                    
                    # SOLUTION STRUCTURÉE : Deux calques de texte séparés avec des dy (float) fixes et autorisés
                    labels_positifs = chart_base.mark_text(
                        dy=-10, align="center", fontWeight="bold"
                    ).transform_filter(
                        "datum.PointsJ1 >= 0"
                    ).encode(
                        y=alt.Y("PointsJ1:Q"), text=alt.Text("PointsJ1:Q", format="+d")
                    )
                    
                    labels_negatifs = chart_base.mark_text(
                        dy=10, align="center", fontWeight="bold"
                    ).transform_filter(
                        "datum.PointsJ1 < 0"
                    ).encode(
                        y=alt.Y("PointsJ1:Q"), text=alt.Text("PointsJ1:Q", format="+d")
                    )
                    
                    st.altair_chart(barres + labels_positifs + labels_negatifs, use_container_width=True)
                    st.write("") 
                    
                    # Graphique 2 : Courbe de tendance cumulative
                    st.write("**Évolution du cumul sur la saison**")
                    chart_cumul_base = alt.Chart(df_graph).encode(
                        x=alt.X("Semaine:N", sort=alt.SortField(field="semaine_num", order="ascending")),
                        y=alt.Y("Points Cumulés:Q")
                    )
                    
                    courbe = chart_cumul_base.mark_line(color="#3b82f6", strokeWidth=3)
                    points = chart_cumul_base.mark_circle(color="#3b82f6", size=60)
                    labels_courbe = chart_cumul_base.mark_text(dy=-12, align="center", fontWeight="bold").encode(
                        text=alt.Text("Points Cumulés:Q", format="d")
                    )
                    
                    st.altair_chart(courbe + points + labels_courbe, use_container_width=True)
                    st.markdown("---")

                # 2. Sous-totaux par joueur
                totaux = tcd_base.groupby(level=["Equipe1", "Joueur1"]).sum()
                totaux["ClassementJ1"], totaux["Division"], totaux["Semaine"] = "Total Saison", "", ""
                totaux = totaux.set_index(["ClassementJ1", "Division", "Semaine"], append=True)
                
                # 3. Fusion et Tri Chronologique
                tcd_bilan = pd.concat([tcd_base, totaux]).sort_index(
                    level=["Equipe1", "Joueur1", "Semaine"],
                    key=lambda x: x.map(parse_semaine) if x.name == "Semaine" else x
                )
                
                # 4. Métriques calculées et renommage final
                tcd_bilan["Taux Victoires"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match"]).fillna(0)) * 100
                tcd_bilan = tcd_bilan[["MatchNonFF", "Match", "VictoireJ1", "Taux Victoires", "PointsJ1"]]
                tcd_bilan.columns = ["Sélections", "Matchs Joués", "Matchs Gagnés", "% Victoires", "Points Gagnés J1"]

                # 5. Injection de Styles CSS
                def injection_style_ligne(row):
                    is_total = "Total Saison" in row.name
                    return ["font-weight: bold !important;" + (" background-color: #edf2f7 !important;" if c != "% Victoires" else "") if is_total else "" for c in row.index]

                st.subheader(f"📋 Tableau de synthèse des performances ({len(df_res)} match(s) analysé(s))")
                
                html_table = (
                    tcd_bilan.style.format({
                        "Sélections": "{:,.0f}", "Matchs Joués": "{:,.0f}", "Matchs Gagnés": "{:,.0f}",
                        "% Victoires": "{:.1f}%", "Points Gagnés J1": "{:+.0f}"
                    })
                    .background_gradient(cmap="RdYlGn", subset=["% Victoires"], vmin=0, vmax=100, axis=0)
                    .apply(injection_style_ligne, axis=1)
                    .set_table_styles([
                        {"selector": "th, td, th.row_heading, th.col_heading, td.data, .blank", "props": [("vertical-align", "top !important"), ("text-align", "left !important"), ("border", "1px solid #555555 !important"), ("padding", "8px !important")]},
                        {"selector": "tr:has(th:contains('Total Saison')) th", "props": [("font-weight", "bold !important"), ("background-color", "#edf2f7 !important")]}
                    ], overwrite=False)
                    .to_html(escape=False)
                )
                st.write(html_table, unsafe_allow_html=True)
                
except Exception as e:
    st.error("Une erreur technique est survenue lors de l'exécution de l'application.")
    st.exception(e)
