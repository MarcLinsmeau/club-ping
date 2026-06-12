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


    # --- INITIALISATION DU STATE (Mémoire de l'application) ---
    if "annee" not in st.session_state:
        st.session_state.annee = "--- Choisir une année ---"
    if "club" not in st.session_state:
        st.session_state.club = "--- Choisir un club ---"
    if "joueur" not in st.session_state:
        st.session_state.joueur = "Tous les joueurs"

    # --- PANNEL DE CONFIGURATION DES FILTRES ---
    st.subheader("🔍 Filtres de sélection")
    
    # Étape 1 : Choisir l'année en premier pour charger le reste
    liste_annees = charger_annees()
    annee_selectionnee = st.selectbox(
        "📅 Étape 1 : Choisir une Année",
        options=["--- Choisir une année ---"] + list(liste_annees),
        key="annee_select"
    )
    
    if annee_selectionnee != "--- Choisir une année ---":
        st.session_state.annee = annee_selectionnee
        
        # Formulaire global pour le Club et le Joueur (Évite les rafraîchissements partiels gênants)
        with st.form("formulaire_filtres"):
            st.write("### 🎛️ Ajuster les filtres de recherche")
            
            # Chargement des clubs pour l'année choisie
            liste_clubs = charger_clubs(st.session_state.annee)
            club_index = 0
            if st.session_state.club in liste_clubs:
                club_index = liste_clubs.index(st.session_state.club) + 1
                
            club_choisi = st.radio(
                "🏢 Étape 2 : Sélectionner le Club (Equipe 1)",
                options=["--- Choisir un club ---"] + list(liste_clubs),
                index=club_index
            )
            
            # Chargement dynamique des joueurs si un club est coché
            if club_choisi != "--- Choisir un club ---":
                liste_joueurs = charger_joueurs(st.session_state.annee, club_choisi)
                joueur_index = 0
                if st.session_state.joueur in liste_joueurs:
                    joueur_index = liste_joueurs.index(st.session_state.joueur) + 1
                    
                joueur_choisi = st.radio(
                    "👤 Étape 3 : Sélectionner le Joueur (Joueur 1)",
                    options=["Tous les joueurs"] + list(liste_joueurs),
                    index=joueur_index
                )
            else:
                st.info("Sélectionnez un club pour voir apparaître la liste des joueurs.")
                joueur_choisi = "Tous les joueurs"
            
            # Bouton de soumission unique : Ferme virtuellement les choix et applique les données
            bouton_valider = st.form_submit_button("⚡ Appliquer les filtres et calculer", use_container_width=True)
            
            if bouton_valider:
                st.session_state.club = club_choisi
                st.session_state.joueur = joueur_choisi
                st.rerun()

    # --- ASTUCE CSS CONTRE LE CLAVIER IPHONE ---
    st.markdown("<style>.stSelectbox div[data-baseweb=\"select\"] input {inputmode: none !important; pointer-events: none !important;}</style>", unsafe_allow_html=True)

    # --- ENCLENCHEMENT DE LA REQUÊTE ET GENERATION TCD ---
    annee_valide = st.session_state.annee != "--- Choisir une année ---"
    club_valide = st.session_state.club != "--- Choisir un club ---"

    if not annee_valide:
        st.info("💡 En attente de vos critères : Veuillez sélectionner une **Année** ci-dessus.")
    elif not club_valide:
        st.info("💡 Étape suivante : Veuillez valider un **Club** dans le formulaire pour lancer l'analyse.")
    else:
        # Affichage du rappel des filtres actifs en haut du tableau
        st.success(f"🎯 **Filtres actifs** 📅 {st.session_state.annee} 🏢 {st.session_state.club} 👤 {st.session_state.joueur}")

        requete = conn.table("test").select("*").eq("Annee", st.session_state.annee).eq("Equipe1", st.session_state.club)

        if st.session_state.joueur != "Tous les joueurs":
            requete = requete.eq("Joueur1", st.session_state.joueur)

        reponse = requete.limit(5000).execute()
        df_resultat = pd.DataFrame(reponse.data)

        if df_resultat.empty:
            st.warning("⚠️ Aucun record trouvé pour cette combinaison précise.")
        else:
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
                    tcd_base.index = tcd_base.index.set_levels(tcd_base.index.levels[4].astype(str), level=4)
                    
                    # 2. Calcul des sous-totaux par joueur
                    totaux_joueurs = tcd_base.groupby(level=["Equipe1", "Joueur1"]).sum()
                    
                    totaux_joueurs["ClassementJ1"] = "TOTAL JOUEUR"
                    totaux_joueurs["Division"] = "TOTAL JOUEUR"
                    totaux_joueurs["Semaine"] = "TOTAL JOUEUR"
                    totaux_joueurs = totaux_joueurs.set_index(["ClassementJ1", "Division", "Semaine"], append=True)
                    
                    # 3. Fusion des données
                    tcd_bilan = pd.concat([tcd_base, totaux_joueurs])
                    
                    # 4. Tri personnalisé
                    tcd_bilan = tcd_bilan.sort_index(
                        level=["Equipe1", "Joueur1", "Semaine"],
                        key=lambda x: x.map(lambda val: "0" if val == "TOTAL JOUEUR" else str(val)) if x.name == "Semaine" else x
                    )
                    
                    # 5. Calcul des pourcentages et colonnes
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
                st.error("Une ou plusieurs colonnes de calcul sont introuvables dans la base de données.")
                
except Exception as e:
    st.error("Une erreur technique est survenue lors de l'exécution de l'application.")
    st.exception(e)
