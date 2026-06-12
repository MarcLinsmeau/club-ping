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


    # --- ASTUCE CSS ANTI-CLAVIER IPHONE
