import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Ping Club - Recherche", page_icon="🏓", layout="wide")
st.title("🏓 Recherche Avancée des Matchs")

try:
    # 1. Connexion à Supabase
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- FONCTIONS D'APPEL DES RPC (VALEURS UNIQUES EN CASCADE) ----
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
        # On récupère l'ensemble des joueurs appartenant à tous les clubs sélectionnés
        joueurs_globaux = set()
        for club in liste_clubs:
            res = conn.client.rpc("obtenir_joueurs_par_annee_et_club", {"annee_recherche": annee, "club_recherche": club}).execute()
            if res.data:
                for row in res.data:
                    joueurs_globaux.add(row["joueur"])
        return sorted(list(joueurs_globaux))


    # --- FONCTIONS DE CALLBACK (Nettoyage en cascade) ---
    def changement_annee():
        st.session_state.clubs_choisis = []
        st.session_state.joueurs_choisis = []

    def changement_club():
        st.session_state.joueurs_choisis = []


    # --- INITIALISATION DES VARIABLES DANS LE STATE ---
    if "annee_choisie" not in st.session_state:
        st.session_state.annee_choisie = None
    if "clubs_choisis" not in st.session_state:
        st.session_state.clubs_choisis = []
    if "joueurs_choisis" not in st.session_state:
        st.session_state.joueurs_choisis = []


    # --- INTERFACE ET FILTRES MULTI-SÉLECTION ---
    st.subheader("🔍 Filtres de sélection (Multi-choix tactiles)")

    # 1. FILTRE ANNÉE (Sélection unique pour cibler une saison)
    liste_annees = charger_annees()
    st.write("**📅 1. Sélectionnez l'Année de recherche :**")
    st.segmented_control(
        label="Année",
        options=list(liste_annees),
        key="annee_choisie",
        selection_mode="single",
        on_change=changement_annee,
        label_visibility="collapsed"
    )

    annee_valide = st.session_state.annee_choisie is not None

    # 2. FILTRE CLUB (Multi-sélection active)
    if annee_valide:
        st.markdown("---")
        liste_clubs = charger_clubs(st.session_state.annee_choisie)
        st.write("**🏢 2. Sélectionnez un ou plusieurs Clubs (Equipe 1) :**")
        st.segmented_control(
            label="Clubs",
            options=list(liste_clubs),
            key="clubs_choisis",
            selection_mode="multi",  # Multi-clubs activé
            on_change=changement_club,
            label_visibility="collapsed"
        )

    clubs_valides = annee_valide and len(st.session_state.clubs_choisis) > 0

    # 3. FILTRE JOUEUR (Multi-sélection active)
    if clubs_valides:
        st.markdown("---")
        liste_joueurs = charger_joueurs(st.session_state.annee_choisie, st.session_state.clubs_choisis)
        st.write("**👤 3. Sélectionnez un ou plusieurs Joueurs (Joueur 1) :**")
        st.segmented_control(
            label="Joueurs",
            options=list(liste_joueurs),
            key="joueurs_choisis",
            selection_mode="multi",  # Multi-joueurs activé
            label_visibility="collapsed"
        )


    # --- ENCLENCHEMENT DE LA REQUÊTE ET GENERATION TCD ---
    st.markdown("---")
    if not annee_valide:
        st.info("💡 En attente de vos critères : Veuillez cocher une **Année** pour commencer.")
    elif not clubs_valides:
        st.info("💡 Étape suivante : Veuillez cocher au moins un **Club** pour charger les joueurs correspondants.")
    else:
        # Construction de la requête avec les filtres cumulés .in_()
        requete = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie).in_("Equipe1", st.session_state.clubs_choisis)

        # Si des joueurs spécifiques sont cochés, on applique le filtre, sinon on prend tout le monde
        if st.session_state.joueurs_choisis:
            requete = requete.in_("Joueur1", st.session_state.joueurs_choisis)

        reponse = requete.limit(50000).execute()
        df_resultat = pd.DataFrame(reponse.data)

        if df_resultat.empty:
            st.warning("⚠️ Aucun record trouvé pour cette combinaison précise.")
        else:
            # Validation des colonnes requises pour le calcul
            colonnes_requises = ["MatchNonFF", "Match", "VictoireJ1", "PointsJ1"]
            if all(col in df_resultat.columns for col in colonnes_requises):
                
                # 1. Pivot de table initial
                tcd_base = df_resultat.pivot_table(
                    index=["Equipe1", "Joueur1", "ClassementJ1", "Division", "Semaine"], 
                    values=colonnes_requises,
                    aggfunc={
                        "MatchNonFF": "size",   
                        "Match": "size",    
                        "VictoireJ1": "sum",
                        "PointsJ1": "sum"
                    },
                    fill_value=0
                )

                if not tcd_base.empty:
                    tcd_base = tcd_base[colonnes_requises]
                    
                    # Normalisation du niveau "Semaine"
                    tcd_base.index = tcd_base.index.set_levels(tcd_base.index.levels[4].astype(str), level=4)
                    
                    # 2. Calcul des sous-totaux par joueur
                    totaux_joueurs = tcd_base.groupby(level=["Equipe1", "Joueur1"]).sum()
                    
                    totaux_joueurs["ClassementJ1"] = "Total Saison"
                    totaux_joueurs["Division"] = ""
                    totaux_joueurs["Semaine"] = ""
                    totaux_joueurs = totaux_joueurs.set_index(["ClassementJ1", "Division", "Semaine"], append=True)
                    
                    # 3. Fusion des données
                    tcd_bilan = pd.concat([tcd_base, totaux_joueurs])
                    
                    # 4. Tri personnalisé (Total placé au-dessus du détail en triant sur la colonne virtuelle / index)
                    tcd_bilan = tcd_bilan.sort_index(
                        level=["Equipe1", "Joueur1", "ClassementJ1"],
                        key=lambda x: x.map(lambda val: "0" if val == "Total Saison" else str(val)) if x.name == "ClassementJ1" else x
                    )
                    
                    # 5. Calcul des pourcentages et structuration finale
                    tcd_bilan["Taux Victoires"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match"]).fillna(0)) * 100
                    tcd_bilan = tcd_bilan[["MatchNonFF", "Match", "VictoireJ1", "Taux Victoires", "PointsJ1"]]
                    tcd_bilan.columns = ["Sélections", "Matchs Joués", "Matchs Gagnés", "% Victoires", "Points Gagnés"]

                    # --- STRATÉGIE DE MISE EN GRAS COMPLÈTE DES LIGNES ---
                    # Cette fonction cible les valeurs numériques de la ligne "Total Saison"
                    def styliser_ligne_total(row):
                        # On vérifie si "Total Saison" est présent dans le tuple de l'index (niveau 2 : ClassementJ1)
                        if "Total Saison" in row.name:
                            return ["font-weight: bold !important; background-color: #edf2f7 !important;"] * len(row)
                        return [""] * len(row)

                    # Affichage final stylisé
                    st.subheader(f"📋 Tableau de synthèse des performances ({len(df_resultat)} match(s) analysé(s))")
                    
                    tcd_style = tcd_bilan.style.format({
                        "Sélections": "{:,.0f}",
                        "Matchs Joués": "{:,.0f}",
                        "Matchs Gagnés": "{:,.0f}",
                        "% Victoires": "{:.1f}%",
                        "Points Gagnés J1": "{:+.0f}"
                    }).apply(
                        styliser_ligne_total, 
                        axis=1
                    ).background_gradient(
                        cmap="RdYlGn", 
                        subset=["% Victoires"],
                        vmin=0,
                        vmax=100,
                        axis=0                   
                    ).set_table_styles([
                        {"selector": "th, td, th.row_heading, th.col_heading, td.data, .blank", "props": [
                            ("vertical-align", "top !important"),
                            ("text-align", "left !important")
                        ]},
                        {"selector": "th, td, th.row_heading, th.col_heading, td.data", "props": [
                            ("border", "1px solid #555555 !important")
                        ]},
                        {"selector": "th, td", "props": [
                            ("padding", "8px !important")
                        ]},
                        # Cette règle CSS force désormais le gras également sur les en-têtes textuels (à gauche) de la ligne concernée
                        {"selector": "tr:has(th:contains('Total Saison')) th", "props": [
                            ("font-weight", "bold !important"),
                            ("background-color", "#edf2f7 !important")
                        ]}
                    ], overwrite=False)
                    
                    st.write(tcd_style.to_html(escape=False), unsafe_allow_html=True)
                    
                else:
                    st.info("Données insuffisantes pour générer ce tableau croisé.")
            else:
                st.error("Une ou plusieurs colonnes de calcul ('MatchNonFF', 'Match', 'VictoireJ1', 'PointsJ1') sont introuvables.")
                
except Exception as e:
    st.error("Une erreur technique est survenue lors de l'exécution de l'application.")
    st.exception(e)
