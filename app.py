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
    def charger_joueurs(annee, club):
        res = conn.client.rpc("obtenir_joueurs_par_annee_et_club", {"annee_recherche": annee, "club_recherche": club}).execute()
        return [row["joueur"] for row in res.data] if res.data else []


    # --- FONCTIONS DE CALLBACK (Réinitialisation propre lors des changements) ---
    def changement_annee():
        # Si on change d'année, on remet le club et le joueur à zéro
        st.session_state.club_choisi = "--- Choisir un club ---"
        st.session_state.joueur_choisi = "Tous les joueurs"

    def changement_club():
        # Si on change de club, on remet le joueur à zéro
        st.session_state.joueur_choisi = "Tous les joueurs"


    # --- INITIALISATION DES VARIABLES DANS LE STATE ---
    if "annee_choisie" not in st.session_state:
        st.session_state.annee_choisie = "--- Choisir une année ---"
    if "club_choisi" not in st.session_state:
        st.session_state.club_choisi = "--- Choisir un club ---"
    if "joueur_choisi" not in st.session_state:
        st.session_state.joueur_choisi = "Tous les joueurs"


    # --- INTERFACE ET FILTRES EN CASCADE ---
    st.subheader("🔍 Filtres de sélection")
    col1, col2, col3 = st.columns(3)

    # 1. FILTRE ANNÉE
    liste_annees = charger_annees()
    options_annees = ["--- Choisir une année ---"] + list(liste_annees)
    
    with col1:
        st.selectbox(
            "📅 1. Année :",
            options=options_annees,
            key="annee_choisie",
            on_change=changement_annee
        )

    annee_valide = st.session_state.annee_choisie != "--- Choisir une année ---"

    # 2. FILTRE CLUB
    with col2:
        if annee_valide:
            liste_clubs = charger_clubs(st.session_state.annee_choisie)
            options_clubs = ["--- Choisir un club ---"] + list(liste_clubs)
            
            st.selectbox(
                "🏢 2. Club (Equipe 1) :",
                options=options_clubs,
                key="club_choisi",
                on_change=changement_club
            )
        else:
            st.selectbox("🏢 2. Club (Equipe 1) :", ["Veuillez d'abord choisir une année"], disabled=True)

    club_valide = annee_valide and st.session_state.club_choisi != "--- Choisir un club ---" and st.session_state.club_choisi != "Veuillez d'abord choisir une année"

    # 3. FILTRE JOUEUR
    with col3:
        if club_valide:
            liste_joueurs = charger_joueurs(st.session_state.annee_choisie, st.session_state.club_choisi)
            options_joueurs = ["Tous les joueurs"] + list(liste_joueurs)
            
            st.selectbox(
                "👤 3. Joueur (Joueur 1) :",
                options=options_joueurs,
                key="joueur_choisi"
            )
        else:
            st.selectbox("👤 3. Joueur (Joueur 1) :", ["Veuillez d'abord choisir un club"], disabled=True)


    # --- ASTUCE CSS ANTI-CLAVIER IPHONE ---
    # On applique l'astuce sur les 3 boîtes en même temps pour bloquer la saisie de texte
    st.markdown(
        """
        <style>
            .stSelectbox div[data-baseweb="select"] input {
                inputmode: none !important;
                pointer-events: none !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )


    # --- ENCLENCHEMENT DE LA REQUÊTE ET GENERATION TCD ---
    if not annee_valide:
        st.info("💡 En attente de vos critères : Veuillez sélectionner une **Année** pour commencer.")
    elif not club_valide:
        st.info("💡 Étape suivante : Veuillez sélectionner un **Club** pour charger les matchs correspondants.")
    else:
        # Exécution de la requête avec les bonnes variables stabilisées
        requete = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie).eq("Equipe1", st.session_state.club_choisi)

        if st.session_state.joueur_choisi != "Tous les joueurs":
            requete = requete.eq("Joueur1", st.session_state.joueur_choisi)

        reponse = requete.limit(5000).execute()
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
                    
                    totaux_joueurs["ClassementJ1"] = "TOTAL JOUEUR"
                    totaux_joueurs["Division"] = "TOTAL JOUEUR"
                    totaux_joueurs["Semaine"] = "TOTAL JOUEUR"
                    totaux_joueurs = totaux_joueurs.set_index(["ClassementJ1", "Division", "Semaine"], append=True)
                    
                    # 3. Fusion des données
                    tcd_bilan = pd.concat([tcd_base, totaux_joueurs])
                    
                    # 4. Tri personnalisé (Total placé au-dessus du détail)
                    tcd_bilan = tcd_bilan.sort_index(
                        level=["Equipe1", "Joueur1", "Semaine"],
                        key=lambda x: x.map(lambda val: "0" if val == "TOTAL JOUEUR" else str(val)) if x.name == "Semaine" else x
                    )
                    
                    # 5. Calcul des pourcentages et structuration finale
                    tcd_bilan["Taux Victoires"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match"]).fillna(0)) * 100
                    tcd_bilan = tcd_bilan[["MatchNonFF", "Match", "VictoireJ1", "Taux Victoires", "PointsJ1"]]
                    tcd_bilan.columns = ["Sélections", "Matchs Joués", "Matchs Gagnés", "% Victoires", "Points Gagnés J1"]

                    # Affichage final stylisé
                    st.subheader(f"📋 Tableau de synthèse des performances ({len(df_resultat)} match(s) analysé(s))")
                    
                    tcd_style = tcd_bilan.style.format({
                        "Sélections": "{:,.0f}",
                        "Matchs Joués": "{:,.0f}",
                        "Matchs Gagnés": "{:,.0f}",
                        "% Victoires": "{:.1f}%",
                        "Points Gagnés J1": "{:+.0f}"
                    }).background_gradient(
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
                        {"selector": "tr:has(th:contains('TOTAL')), tr:has(td:contains('TOTAL'))", "props": [
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
    st.exception(e)import streamlit as st
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
    def charger_joueurs(annee, club):
        res = conn.client.rpc("obtenir_joueurs_par_annee_et_club", {"annee_recherche": annee, "club_recherche": club}).execute()
        return [row["joueur"] for row in res.data] if res.data else []


    # --- FONCTIONS DE CALLBACK (Réinitialisation propre lors des changements) ---
    def changement_annee():
        # Si on change d'année, on remet le club et le joueur à zéro
        st.session_state.club_choisi = "--- Choisir un club ---"
        st.session_state.joueur_choisi = "Tous les joueurs"

    def changement_club():
        # Si on change de club, on remet le joueur à zéro
        st.session_state.joueur_choisi = "Tous les joueurs"


    # --- INITIALISATION DES VARIABLES DANS LE STATE ---
    if "annee_choisie" not in st.session_state:
        st.session_state.annee_choisie = "--- Choisir une année ---"
    if "club_choisi" not in st.session_state:
        st.session_state.club_choisi = "--- Choisir un club ---"
    if "joueur_choisi" not in st.session_state:
        st.session_state.joueur_choisi = "Tous les joueurs"


    # --- INTERFACE ET FILTRES EN CASCADE ---
    st.subheader("🔍 Filtres de sélection")
    col1, col2, col3 = st.columns(3)

    # 1. FILTRE ANNÉE
    liste_annees = charger_annees()
    options_annees = ["--- Choisir une année ---"] + list(liste_annees)
    
    with col1:
        st.selectbox(
            "📅 1. Année :",
            options=options_annees,
            key="annee_choisie",
            on_change=changement_annee
        )

    annee_valide = st.session_state.annee_choisie != "--- Choisir une année ---"

    # 2. FILTRE CLUB
    with col2:
        if annee_valide:
            liste_clubs = charger_clubs(st.session_state.annee_choisie)
            options_clubs = ["--- Choisir un club ---"] + list(liste_clubs)
            
            st.selectbox(
                "🏢 2. Club (Equipe 1) :",
                options=options_clubs,
                key="club_choisi",
                on_change=changement_club
            )
        else:
            st.selectbox("🏢 2. Club (Equipe 1) :", ["Veuillez d'abord choisir une année"], disabled=True)

    club_valide = annee_valide and st.session_state.club_choisi != "--- Choisir un club ---" and st.session_state.club_choisi != "Veuillez d'abord choisir une année"

    # 3. FILTRE JOUEUR
    with col3:
        if club_valide:
            liste_joueurs = charger_joueurs(st.session_state.annee_choisie, st.session_state.club_choisi)
            options_joueurs = ["Tous les joueurs"] + list(liste_joueurs)
            
            st.selectbox(
                "👤 3. Joueur (Joueur 1) :",
                options=options_joueurs,
                key="joueur_choisi"
            )
        else:
            st.selectbox("👤 3. Joueur (Joueur 1) :", ["Veuillez d'abord choisir un club"], disabled=True)


    # --- ASTUCE CSS ANTI-CLAVIER IPHONE
