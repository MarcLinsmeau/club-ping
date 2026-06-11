import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Ping Club", page_icon="🏓", layout="wide")
st.title("🏓 Consultation des Matchs du Club")

try:
    # 1. Connexion à Supabase
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- CHARGEMENT DES FILTRES VIA RPC (Uuuultra rapide, pas de doublons reçus) ---
    @st.cache_data(ttl=600)
    def charger_filtres_uniques():
        # On appelle la fonction SQL qu'on a créée sur Supabase
        reponse_rpc = conn.rpc("obtenir_filtres_uniques").execute()
        donnees = reponse_rpc.data
        
        # On extrait les listes uniques calculées par la base de données
        annees = sorted([str(a) for a in donnees.get("annees", [])])
        clubs = sorted(donnees.get("clubs", []))
        joueurs = sorted(donnees.get("joueurs", []))
        
        return annees, clubs, joueurs

    # Récupération des 3 listes uniques d'un coup
    liste_annees, liste_clubs, liste_joueurs = charger_filtres_uniques()
    # --- ZONE DES FILTRES ---
    st.subheader("🔍 Critères de recherche")
    col1, col2, col3 = st.columns(3)

    with col1:
        annee_choisie = st.selectbox("Année :", ["Toutes"] + [str(a) for a in liste_annees])
    with col2:
        club_choisi = st.selectbox("Club (Equipe 1) :", ["Tous les clubs"] + liste_clubs)
    with col3:
        joueur_choisi = st.selectbox("Joueur (Joueur 1) :", ["Tous les joueurs"] + liste_joueurs)

    # --- CONSTRUIRE LA REQUÊTE SUPABASE SUR MESURE ---
    # C'est l'astuce : on prépare la requête en fonction des choix de l'utilisateur
    requete = conn.table("test").select("*")

    if annee_choisie != "Toutes":
        requete = requete.eq("Annee", annee_choisie)
    
    if club_choisi != "Tous les clubs":
        requete = requete.eq("Equipe1", club_choisi)
        
    if joueur_choisi != "Tous les joueurs":
        requete = requete.eq("Joueur1", joueur_choisi)

    # --- EXÉCUTION ET AFFICHAGE ---
    # On limite à 5000 lignes max pour l'affichage de sécurité si aucun filtre n'est mis
    reponse = requete.limit(5000).execute()
    df_filtre = pd.DataFrame(reponse.data)

    if df_filtre.empty:
        st.info("Aucun match ne correspond à cette combinaison de filtres.")
    else:
        st.subheader(f"📊 Résultats ({len(df_filtre)} match(s) trouvé(s))")
        
        colonnes_affichage = [
            "id", "Annee", "Division", "Semaine", "Match", 
            "Equipe1", "Joueur1", "ClassementJ1", "Resultat1.1",
            "Resultat2.1", "ClassementJ2", "Joueur2", "Equipe2"
        ]
        st.dataframe(df_filtre[colonnes_affichage], use_container_width=True, hide_index=True)

        # --- SECTION TABLEAU CROISÉ DYNAMIQUE (TCD) ---
        st.markdown("---")
        st.header("📊 Tableau Croisé Dynamique")
        
        element_colonne = st.selectbox("Afficher en colonnes du TCD :", ["Division", "Semaine"])

        # Calcul rapide du TCD sur les données affichées
        tcd_joueur1 = df_filtre.pivot_table(
            index="Joueur1", 
            columns=element_colonne, 
            aggfunc="size", 
            fill_value=0
        )

        if not tcd_joueur1.empty:
            st.dataframe(tcd_joueur1.style.background_gradient(cmap="Blues"), use_container_width=True)

except Exception as e:
    st.error("Une erreur est survenue lors du chargement.")
    st.exception(e)
