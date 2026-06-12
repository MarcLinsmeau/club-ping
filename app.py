import streamlit as st
import pandas as pd
import altair as alt
import re
from st_supabase_connection import SupabaseConnection

# --- CONFIGURATION DE L'APPLICATION ---
# Récupération du mode via l'URL (permet de basculer dynamiquement la configuration)
mode = st.query_params.get("mode", "StatsJoueursSemaine")

st.set_page_config(page_title="Ping-Point - Recherche", page_icon="🏓", layout="wide")
st.title(f"🏓 Recherche Avancée des Statistiques - {mode}")

try:
    # Initialisation de la connexion native à Supabase
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- FONCTIONS DE DONNÉES (RPC & TABLES) AVEC MISE EN CACHE ---
    @st.cache_data(ttl=300)
    def charger_annees():
        """Récupère la liste de toutes les années uniques disponibles en base."""
        res = conn.client.rpc("obtenir_annees_uniques").execute()
        return [str(row["annee"]) for row in (res.data or [])]

    @st.cache_data(ttl=300)
    def charger_clubs(annee):
        """Récupère les clubs ayant participé à une année spécifique."""
        res = conn.client.rpc("obtenir_clubs_par_annee", {"annee_recherche": annee}).execute()
        return [row["club"] for row in (res.data or [])]

    @st.cache_data(ttl=300)
    def charger_joueurs(annee, liste_clubs):
        """Extrait et trie la liste des joueurs (Joueur1) selon l'année et les clubs sélectionnés."""
        res = conn.table("test").select("Joueur1").eq("Annee", annee).in_("Equipe1", liste_clubs).execute()
        return sorted(list({row["Joueur1"] for row in (res.data or []) if row.get("Joueur1")}))

    # --- GESTION DE L'ÉTAT DE SESSION (SESSION STATE) & CALLBACKS ---
    def reset_filtres(niveau):
        """Réinitialise en cascade les filtres enfants lors de la modification d'un filtre parent."""
        if niveau <= 1:
            st.session_state.clubs_choisis = []
        st.session_state.joueurs_choisis = []

    # Initialisation des variables d'état si elles n'existent pas encore
    for key, val in [("annee_choisie", None), ("clubs_choisis", []), ("joueurs_choisis", [])]:
        if key not in st.session_state:
            st.session_state[key] = val

    # --- INTERFACE UTILISATEUR : FILTRES TACTILES ---
    st.subheader("🔍 Filtres de sélection (Multi-choix tactiles)")
    
    # Filtre 1 : Sélection obligatoire de l'année
    st.write("**📅 1. Sélectionnez l'Année de recherche :**")
    st.segmented_control("Année", options=charger_annees(), key="annee_choisie", selection_mode="single", on_change=reset_filtres, args=(1,), label_visibility="collapsed")

    # Filtre 2 : Sélection des clubs (accessible uniquement si l'année est cochée)
    if st.session_state.annee_choisie:
        st.markdown("---")
        st.write("**🏢 2. Sélectionnez un ou plusieurs Clubs (Equipe 1) :**")
        st.segmented_control("Clubs", options=charger_clubs(st.session_state.annee_choisie), key="clubs_choisis", selection_mode="multi", on_change=reset_filtres, args=(2,), label_visibility="collapsed")

    # Filtre 3 : Sélection des joueurs (accessible si l'année et au moins un club sont cochés)
    if st.session_state.annee_choisie and st.session_state.clubs_choisis:
        st.markdown("---")
        st.write("**👤 3. Sélectionnez un ou plusieurs Joueurs (Joueur 1) :**")
        st.segmented_control("Joueurs", options=charger_joueurs(st.session_state.annee_choisie, st.session_state.clubs_choisis), key="joueurs_choisis", selection_mode="multi", label_visibility="collapsed")

    # --- LOGIQUE DE CONTRÔLE ET REQUÊTAGE PRINCIPAL ---
    st.markdown("---")
    if not st.session_state.annee_choisie:
        st.info("💡 En attente de vos critères : Veuillez cocher une **Année** pour commencer.")
    elif not st.session_state.clubs_choisis:
        st.info("💡 Étape suivante : Veuillez cocher au moins un **Club** pour charger les joueurs correspondants.")
    else:
        # Construction de la requête principale filtrée par Année et Clubs
        req = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie).in_("Equipe1", st.session_state.clubs_choisis)
        
        # Application du filtre optionnel sur les joueurs si spécifié
        if st.session_state.joueurs_choisis:
            req = req.in_("Joueur1", st.session_state.joueurs_choisis)

        # Chargement des données brutes (limite de sécurité à 50 000 lignes)
        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé pour cette combinaison précise.")
        else:
            # Clause de garde : Vérification de la présence des colonnes indispensables pour les calculs
            colonnes_requises = ["MatchNonFF", "Match", "VictoireJ1", "PointsJ1"]
            if not all(c in df_res.columns for c in colonnes_requises):
                st.error("Une ou plusieurs colonnes de calcul sont introuvables.")
                st.stop()
                
            # --- 1. CONSTRUCTION DU TABLEAU CROISÉ DYNAMIQUE (TCD) DE BASE ---
            tcd_base = df_res.pivot_table(
                index=["Equipe1", "Joueur1", "ClassementJ1", "Division", "Semaine"], 
                values=colonnes_requises, 
                aggfunc={"MatchNonFF": "size", "Match": "size", "VictoireJ1": "sum", "PointsJ1": "sum"}, 
                fill_value=0
            ).reindex(columns=colonnes_requises)

            if tcd_base.empty:
                st.info("Données insuffisantes pour générer ce tableau croisé.")
            else:
                # Normalisation du type de l'index 'Semaine' en chaîne de caractères
                tcd_base.index = tcd_base.index.set_levels(tcd_base.index.levels[4].astype(str), level=4)
                
                # Fonction lambda optimisée pour extraire le numéro de semaine à des fins de tri chronologique
                parse_semaine = lambda val: int(re.findall(r'\d+', str(val))[0]) if re.findall(r'\d+', str(val)) else ( -1 if val == "" else 0 )

                # --- 2. MODULE DE RENDU DES GRAPHES (MODE MONO-JOUEUR) ---
                if len(st.session_state.joueurs_choisis) == 1:
                    st.subheader(f"📊 Analyse Graphique — {st.session_state.joueurs_choisis[0]}")
                    
                    # Préparation et tri du jeu de données pour les graphiques temporels
                    df_graph = tcd_base.reset_index()
                    df_graph["semaine_num"] = df_graph["Semaine"].map(parse_semaine)
                    df_graph = df_graph.sort_values(by="semaine_num")
                    df_graph["Points Cumulés"] = df_graph["PointsJ1"].cumsum()
                    
                    # Graphique 1 : Histogramme hebdomadaire des points gagnés / perdus
                    st.write("**Points gagnés / perdus par semaine**")
                    chart_base = alt.Chart(df_graph).encode(x=alt.X("Semaine:N", sort=alt.SortField(field="semaine_num", order="ascending")))
                    barres = chart_base.mark_bar(color="#22c55e").encode(y=alt.Y("PointsJ1:Q"))
                    
                    # Superposition des étiquettes textuelles (gestion dy stricte pour compatibilité Altair Schema)
                    labels_pos = chart_base.mark_text(dy=-10, align="center", fontWeight="bold").transform_filter("datum.PointsJ1 >= 0").encode(y="PointsJ1:Q", text=alt.Text("PointsJ1:Q", format="+d"))
                    labels_neg = chart_base.mark_text(dy=10, align="center", fontWeight="bold").transform_filter("datum.PointsJ1 < 0").encode(y="PointsJ1:Q", text=alt.Text("PointsJ1:Q", format="+d"))
                    
                    st.altair_chart(barres + labels_pos + labels_neg, use_container_width=True)
                    
                    # Graphique 2 : Courbe d'évolution cumulative au fil de la saison
                    st.write("**Évolution du cumul sur la saison**")
                    chart_cumul = alt.Chart(df_graph).encode(x=alt.X("Semaine:N", sort=alt.SortField(field="semaine_num", order="ascending")), y="Points Cumulés:Q")
                    courbe = chart_cumul.mark_line(color="#3b82f6", strokeWidth=3)
                    points = chart_cumul.mark_circle(color="#3b82f6", size=60)
                    labels_cumul = chart_cumul.mark_text(dy=-12, align="center", fontWeight="bold").encode(text=alt.Text("Points Cumulés:Q", format="d"))
                    
                    st.altair_chart(courbe + points + labels_cumul, use_container_width=True)
                    st.markdown("---")

                # --- 3. CALCUL DES SOUS-TOTAUX ET DU BILAN FINAL ---
                # Génération de la ligne agrégée de résumé pour la saison
                totaux = tcd_base.groupby(level=["Equipe1", "Joueur1"]).sum()
                totaux["ClassementJ1"], totaux["Division"], totaux["Semaine"] = "Total Saison", "", ""
                totaux = totaux.set_index(["ClassementJ1", "Division", "Semaine"], append=True)
                
                # Fusion des lignes de détails avec la ligne de total et tri par chronologie de semaine
                tcd_bilan = pd.concat([tcd_base, totaux]).sort_index(level=["Equipe1", "Joueur1", "Semaine"], key=lambda x: x.map(parse_semaine) if x.name == "Semaine" else x)
                
                # Calcul des KPI finaux et renommage des en-têtes du tableau
                tcd_bilan["Taux Victoires"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match"]).fillna(0)) * 100
                tcd_bilan = tcd_bilan[["MatchNonFF", "Match", "VictoireJ1", "Taux Victoires", "PointsJ1"]]
                tcd_bilan.columns = ["Sélections", "Matchs Joués", "Matchs Gagnés", "% Victoires", "Points Gagnés J1"]

                # --- 4. FORMATTAGE CSS ET INJECTION DU RENDU HTML ---
                def injection_style_ligne(row):
                    """Stylise spécifiquement la ligne 'Total Saison' en appliquant un fond gris et du texte en gras."""
                    return ["font-weight: bold !important;" + (" background-color: #edf2f7 !important;" if c != "% Victoires" else "") if "Total Saison" in row.name else "" for c in row.index]

                st.subheader(f"📋 Tableau de synthèse des performances ({len(df_res)} match(s) analysé(s))")
                
                # Construction et configuration du Styler Pandas vers du HTML brut
                html_table = (
                    tcd_bilan.style.format({"Sélections": "{:,.0f}", "Matchs Joués": "{:,.0f}", "Matchs Gagnés": "{:,.0f}", "% Victoires": "{:.1f}%", "Points Gagnés J1": "{:+.0f}"})
                    .background_gradient(cmap="RdYlGn", subset=["% Victoires"], vmin=0, vmax=100, axis=0)
                    .apply(injection_style_ligne, axis=1)
                    .set_table_styles([
                        {"selector": "th, td, th.row_heading, th.col_heading, td.data, .blank", "props": [("vertical-align", "top !important"), ("text-align", "left !important"), ("border", "1px solid #555555 !important"), ("padding", "8px !important")]},
                        {"selector": "tr:has(th:contains('Total Saison')) th", "props": [("font-weight", "bold !important"), ("background-color", "#edf2f7 !important")]}
                    ], overwrite=False)
                    .to_html(escape=False)
                )
                
                # Rendu du tableau personnalisé (unsafe_allow_html requis pour interpréter le CSS du Styler)
                st.write(html_table, unsafe_allow_html=True)
                
except Exception as e:
    st.error("Une erreur technique est survenue lors de l'exécution de l'application.")
    st.exception(e)
