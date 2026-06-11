import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Ping Club - Matchs", page_icon="🏓", layout="wide")
st.title("🏓 Historique et Détails des Matchs")

try:
    # 1. Connexion à Supabase
    conn = st.connection("supabase", type=SupabaseConnection)

    # 2. Récupération de toutes les lignes de la table 'test'
    reponse = conn.table("test").select("*").execute()
    df = pd.DataFrame(reponse.data)

    if df.empty:
        st.info("La table 'test' est connectée mais elle ne contient pas encore de données. Ajoute des lignes dans Supabase !")
    else:
        # --- ZONE DES FILTRES ---
        st.subheader("🔍 Filtrer les matchs")
        col1, col2 = st.columns(2)

        with col1:
            # Filtre par Année (récupère automatiquement les années présentes)
            liste_annees = ["Toutes"] + sorted(list(df["Annee"].astype(str).unique()))
            annee_choisie = st.selectbox("Année :", liste_annees)

        with col2:
            # Barre de recherche pour trouver un joueur
            recherche_joueur = st.text_input("Rechercher un joueur (Nom) :")

        # --- APPLICATION DES FILTRES ---
        df_filtre = df.copy()

        # Application filtre Année
        if annee_choisie != "Toutes":
            df_filtre = df_filtre[df_filtre["Annee"].astype(str) == annee_choisie]

        # Application filtre Joueur (cherche si le nom est dans Joueur1 OU Joueur2)
        if recherche_joueur:
            condition_j1 = df_filtre["Joueur1"].str.contains(recherche_joueur, case=False, na=False)
            condition_j2 = df_filtre["Joueur2"].str.contains(recherche_joueur, case=False, na=False)
            df_filtre = df_filtre[condition_j1 | condition_j2]

        # --- AFFICHAGE DU TABLEAU ---
        st.subheader(f"📊 Liste des matchs ({len(df_filtre)} match(s) trouvé(s))")
        
        # On choisit l'ordre des colonnes pour que ce soit joli à l'écran
        colonnes_affichage = [
            "id", "Annee", "Division", "Semaine", "Match", 
            "Equipe1", "Joueur1", "ClassementJ1", "Resultat1",
            "Resultat2", "ClassementJ2", "Joueur2", "Equipe2"
        ]
        
        # On affiche le tableau avec les colonnes bien ordonnées
        st.dataframe(df_filtre[colonnes_affichage], use_container_width=True, hide_index=True)

# --- SECTION TABLEAU CROISÉ DYNAMIQUE (TCD) ---
        st.markdown("---") # Une ligne de séparation visuelle
        st.header("📊 Analyse Croisée des Matchs (TCD)")
        st.write("Ce tableau croisé montre le nombre de matchs joués entre les joueurs.")

        # 1. Configuration du TCD par l'utilisateur
        col_tcd1, col_tcd2 = st.columns(2)
        with col_tcd1:
            option_donnee = st.selectbox(
                "Quelle donnée afficher dans les cases ?",
                ["Nombre de matchs joués", "Total des sets marqués par Joueur 1"]
            )
        with col_tcd2:
            Couleur_tcd = st.selectbox("Couleur du tableau :", ["Bleu", "Vert", "Pourpre"])

        # Correspondance des couleurs pour le style Excel
        choix_cmap = {"Bleu": "Blues", "Vert": "Greens", "Pourpre": "Purples"}

        # 2. Calcul du TCD via Pandas selon le choix
        if option_donnee == "Nombre de matchs joués":
            # On crée le TCD en comptant le nombre de lignes (de matchs) pour chaque joueur
            tcd_df = df_filtre.pivot_table(
                index="Joueur1", 
                columns="Joueur2", 
                aggfunc="size", # 'size' compte les lignes
                fill_value=0
            )
        else:
            # On crée le TCD en faisant la somme de la colonne 'Resultat1'
            tcd_df = df_filtre.pivot_table(
                index="Joueur1", 
                columns="Joueur2", 
                values="Resultat1",
                aggfunc="sum", # 'sum' fait le total
                fill_value=0
            )

        # 3. Affichage du TCD avec un style "Heatmap" (dégradé de couleur)
        st.subheader("📋 Matrice Joueur 1 (Lignes) vs Joueur 2 (Colonnes)")
        
        if not tcd_df.empty:
            # On applique une couleur de fond dynamique comme sur Excel
            st.dataframe(
                tcd_df.style.background_gradient(cmap=choix_cmap[Couleur_tcd]), 
                use_container_width=True
            )
        else:
            st.info("Pas assez de données pour générer le tableau croisé.")

except Exception as e:
    st.error("Une erreur est survenue lors du chargement des données.")
    st.exception(e)
