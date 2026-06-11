import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Ping Club - Recherche", page_icon="🏓", layout="wide")
st.title("🏓 Recherche Avancée des Matchs")

try:
    # 1. Connexion à Supabase
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- FONCTIONS D'APPEL DES RPC (VALEURS UNIQUES EN CASCADE) ---
    @st.cache_data(ttl=300)
    def charger_annees():
        """Récupère toutes les années uniques disponibles"""
        res = conn.client.rpc("obtenir_annees_uniques").execute()
        return [str(row["annee"]) for row in res.data] if res.data else []

    @st.cache_data(ttl=300)
    def charger_clubs(annee):
        """Récupère les clubs uniques pour une année donnée"""
        res = conn.client.rpc("obtenir_clubs_par_annee", {"annee_recherche": annee}).execute()
        return [row["club"] for row in res.data] if res.data else []

    @st.cache_data(ttl=300)
    def charger_joueurs(annee, club):
        """Récupère les joueurs uniques pour une année et un club donnés"""
        res = conn.client.rpc("obtenir_joueurs_par_annee_et_club", {"annee_recherche": annee, "club_recherche": club}).execute()
        return [row["joueur"] for row in res.data] if res.data else []


    # --- INTERFACE ET FILTRES ---
    st.subheader("🔍 Filtres de sélection")
    col1, col2, col3 = st.columns(3)

    # 1. Filtre Année (Toujours actif et obligatoire pour éviter le timeout)
    liste_annees = charger_annees()
    with col1:
        if liste_annees:
            annee_choisie = st.selectbox("Année :", liste_annees, index=0)
        else:
            st.error("Aucune donnée trouvée dans la base.")
            st.stop()

    # 2. Filtre Club (Chargé dynamiquement selon l'année choisie)
    liste_clubs = charger_clubs(annee_choisie)
    options_clubs = ["Tous les clubs"] + liste_clubs
    with col2:
        club_choisi = st.selectbox("Club (Equipe 1) :", options_clubs, index=0)

    # 3. Filtre Joueur (Chargé dynamiquement en cascade)
    with col3:
        if club_choisi != "Tous les clubs":
            # Si un club est choisi, on récupère uniquement ses joueurs via la fonction RPC
            liste_joueurs = charger_joueurs(annee_choisie, club_choisi)
            options_joueurs = ["Tous les joueurs"] + liste_joueurs
            joueur_choisi = st.selectbox("Joueur (Joueur 1) :", options_joueurs, index=0)
        else:
            # Si "Tous les clubs" est sélectionné, on permet de chercher le joueur par texte libre
            # car récupérer la liste globale de TOUS les joueurs de l'année serait trop lourd
            joueur_choisi = st.text_input("Rechercher un joueur (Texte libre) :", value="")

    # --- CONSTRUCTION DE LA REQUÊTE FINALE SUR LA TABLE "TEST" ---
    # On commence par filtrer par l'année sélectionnée (Filtre de base ultra-performant)
    requete = conn.table("test").select("*").eq("Annee", annee_choisie)

    # Si un club spécifique est sélectionné
    if club_choisi != "Tous les clubs":
        requete = requete.eq("Equipe1", club_choisi)
        # Si un joueur spécifique de ce club est sélectionné
        if joueur_choisi != "Tous les joueurs":
            requete = requete.eq("Joueur1", joueur_choisi)
            
    # Si "Tous les clubs" est sélectionné mais que l'utilisateur a écrit un nom de joueur
    elif club_choisi == "Tous les clubs" and joueur_choisi.strip() != "":
        # Recherche insensible à la casse sur la colonne Joueur1
        requete = requete.ilike("Joueur1", f"%{joueur_choisi}%")

    # --- EXÉCUTION ET AFFICHAGE DES RECORDS ---
    # Limite de sécurité à 5000 lignes pour l'affichage de l'année complète
    reponse = requete.limit(5000).execute()
    df_resultat = pd.DataFrame(reponse.data)

    if df_resultat.empty:
        st.info("Aucun record trouvé pour cette combinaison de filtres.")
    else:
        st.subheader(f"📋 Records trouvés ({len(df_resultat)} match(s))")
        
        # Ordre d'affichage logique de tes colonnes (nouvelle structure incluse)
        colonnes_ordonnees = [
            "Annee", "Division", "Semaine", "Match", 
            "Equipe1", "Joueur1", "ClassementJ1", 
            "Resultat1.1", "Resultat1.2", "Resultat2.1", "Resultat2.2", 
            "ClassementJ2", "Joueur2", "Equipe2", "MatchNonFF"
        ]
        
        # Sécurité pour n'afficher que les colonnes réellement détectées
        colonnes_visibles = [col for col in colonnes_ordonnees if col in df_resultat.columns]
        
        # Affichage du tableau principal
        st.dataframe(df_resultat[colonnes_visibles], use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Une erreur technique est survenue.")
    st.exception(e)
