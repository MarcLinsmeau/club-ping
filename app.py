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

# --- SECTION TABLEAU CROISÉ DYNAMIQUE (TCD) POUR JOUEUR 1 ---
        st.markdown("---") # Une ligne de séparation visuelle
        st.header("📊 Tableau Croisé Dynamique (Joueur 1 uniquement)")
        st.write("Analysez les statistiques des joueurs lorsqu'ils sont positionnés en Joueur 1.")

        # 1. Choix de la colonne pour le TCD
        col_tcd1, col_tcd2 = st.columns(2)
        with col_tcd1:
            element_colonne = st.selectbox(
                "Que voulez-vous afficher en colonnes ?",
                ["Division", "Annee", "Semaine"]
            )
        with col_tcd2:
            type_calcul = st.selectbox(
                "Quelle statistique calculer ?",
                ["Nombre de matchs joués", "Total des sets marqués (Resultat1)"]
            )

        # 2. Calcul du TCD via Pandas
        if type_calcul == "Nombre de matchs joués":
            # On compte le nombre de matchs (lignes) pour chaque Joueur1 selon l'élément choisi
            tcd_joueur1 = df_filtre.pivot_table(
                index="Joueur1", 
                columns=element_colonne, 
                aggfunc="size", 
                fill_value=0
            )
        else:
            # On fait la somme des sets marqués (Resultat1) par chaque Joueur1
            tcd_joueur1 = df_filtre.pivot_table(
                index="Joueur1", 
                columns=element_colonne, 
                values="Resultat1",
                aggfunc="sum", 
                fill_value=0
            )

        # 3. Affichage du TCD style Excel
        st.subheader(f"📋 Tableau : Joueur 1 (Lignes) vs {element_colonne} (Colonnes)")
        
        if not tcd_joueur1.empty:
            # Affichage avec un joli dégradé bleu pour repérer les grosses valeurs
            st.dataframe(
                tcd_joueur1.style.background_gradient(cmap="Blues"), 
                use_container_width=True
            )
        else:
            st.info("Pas assez de données pour générer le tableau croisé.")

except Exception as e:
    st.error("Une erreur est survenue lors du chargement des données.")
    st.exception(e)
