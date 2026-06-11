import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Ping Club", page_icon="🏓", layout="wide")
st.title("🏓 Consultation des Matchs du Club")

try:
    # 1. Connexion à Supabase
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- CHARGEMENT UNIQUE ET RAPIDE DES CRITÈRES VIA RPC ---
    @st.cache_data(ttl=600)
    def charger_filtres_uniques():
        reponse_rpc = conn.client.rpc("obtenir_filtres_uniques").execute()
        donnees = reponse_rpc.data
        
        annees = sorted([str(a) for a in donnees.get("annees", [])])
        clubs = sorted(donnees.get("clubs", []))
        joueurs = sorted(donnees.get("joueurs", []))
        
        return annees, clubs, joueurs

    liste_annees, liste_clubs, liste_joueurs = charger_filtres_uniques()

    # --- PRÉPARATION DES LISTES POUR LES DROPDOWNS ---
    options_annees = ["Toutes"] + liste_annees
    options_clubs = ["Tous les clubs"] + liste_clubs
    options_joueurs = ["Tous les joueurs"] + liste_joueurs

    # --- DÉFINITION DES VALEURS PAR DÉFAUT ---
    # 1. Pour l'année : on veut la plus récente (la dernière de la liste triée)
    if liste_annees:
        annee_par_defaut = liste_annees[-1]  # Prend la dernière année (ex: 2026)
        index_annee = options_annees.index(annee_par_defaut)
    else:
        index_annee = 0

    # 2. Pour le club ou le joueur (Optionnel)
    # Si tu veux imposer un club par défaut (ex: "Mon Club"), tu cherches son index :
    # index_club = options_clubs.index("Mon Club") if "Mon Club" in options_clubs else 0
    index_club = "AVENNES"  # Laisse sur "Tous les clubs" par défaut
    index_joueur = 0 # Laisse sur "Tous les joueurs" par défaut

    # --- ZONE DES FILTRES ---
    st.subheader("🔍 Critères de recherche")
    col1, col2, col3 = st.columns(3)

    with col1:
        # On applique 'index=index_annee' pour forcer la valeur par défaut
        annee_choisie = st.selectbox("Année :", options_annees, index=index_annee)
    with col2:
        club_choisi = st.selectbox("Club (Equipe 1) :", options_clubs, index=index_club)
    with col3:
        joueur_choisi = st.selectbox("Joueur (Joueur 1) :", options_joueurs, index=index_joueur)

    # --- CONSTRUIRE LA REQUÊTE SUPABASE SUR MESURE ---
    requete = conn.table("test").select("*")

    if annee_choisie != "Toutes":
        requete = requete.eq("Annee", annee_choisie)
    
    if club_choisi != "Tous les clubs":
        requete = requete.eq("Equipe1", club_choisi)
        
    if joueur_choisi != "Tous les joueurs":
        requete = requete.eq("Joueur1", joueur_choisi)

    # --- EXÉCUTION ET AFFICHAGE ---
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

        # --- SECTION TABLEAU CROISÉ DYNAMIQUE ---
        st.markdown("---")
        st.header("📊 Tableau Croisé Dynamique")
        
        element_colonne = st.selectbox("Afficher en colonnes du TCD :", ["Division", "Semaine"])

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
