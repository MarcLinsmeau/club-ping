import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Ping Club - Matchs", page_icon="🏓", layout="wide")
st.title("🏓 Historique et Détails des Matchs v2")

try:
    # 1. Connexion à Supabase
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- ÉTAPE UNIQUE POUR LES GRANDES BASES : RÉCUPÉRER LES ANNÉES SANS TOUT TÉLÉCHARGER ---
    # On demande à Supabase de ne nous renvoyer QUE la colonne "Annee" distincte
    # Cela évite le timeout car la réponse est ultra-légère.
    @st.cache_data(ttl=600)  # On garde en mémoire 10 min pour que ce soit instantané
    def obtenir_annees_uniques():
        reponse_annees = conn.table("test").select("Annee").execute()
        df_annees = pd.DataFrame(reponse_annees.data)
        if not df_annees.empty:
            return sorted(list(df_annees["Annee"].astype(str).unique()))
        return []

    liste_annees = obtenir_annees_uniques()

    # --- ZONE DES FILTRES PRINCIPAUX ---
    st.subheader("🔍 Filtrer les matchs")
    col1, col2 = st.columns(2)

    with col1:
        if liste_annees:
            annee_choisie = st.selectbox("Sélectionnez une Année (Obligatoire pour éviter le timeout) :", liste_annees)
        else:
            annee_choisie = None
            st.warning("Aucune année trouvée dans la base.")

    with col2:
        # Barre de recherche pour trouver un joueur
        recherche_joueur = st.text_input("Rechercher un joueur (Nom) dans cette année :")

    # --- ÉTAPE 2 : TÉLÉCHARGEMENT FILTRÉ À LA SOURCE ---
    if annee_choisie:
        # Crucial : On ajoute .eq("Annee", annee_choisie) pour que Supabase fasse le tri LUI-MÊME
        reponse = conn.table("test").select("*").eq("Annee", annee_choisie).execute()
        df_filtre = pd.DataFrame(reponse.data)

        if df_filtre.empty:
            st.info(f"Aucun match trouvé pour l'année {annee_choisie}.")
        else:
            # Application du filtre textuel du joueur en local sur le sous-ensemble de l'année
            if recherche_joueur:
                condition_j1 = df_filtre["Joueur1"].str.contains(recherche_joueur, case=False, na=False)
                condition_j2 = df_filtre["Joueur2"].str.contains(recherche_joueur, case=False, na=False)
                df_filtre = df_filtre[condition_j1 | condition_j2]

            # --- AFFICHAGE DU TABLEAU DES MATCHS ---
            st.subheader(f"📊 Liste des matchs de l'année {annee_choisie} ({len(df_filtre)} match(s) affiché(s))")
            
            colonnes_affichage = [
                "id", "Annee", "Division", "Semaine", "Match", 
                "Equipe1", "Joueur1", "ClassementJ1", "Resultat1.1",
                "Resultat2.1", "ClassementJ2", "Joueur2", "Equipe2"
            ]
            st.dataframe(df_filtre[colonnes_affichage], use_container_width=True, hide_index=True)

            # --- SECTION TABLEAU CROISÉ DYNAMIQUE (TCD) POUR JOUEUR 1 ---
            st.markdown("---")
            st.header("📊 Tableau Croisé Dynamique (Joueur 1 uniquement)")
            st.write(f"Analyse croisée basée uniquement sur l'année {annee_choisie}.")

            col_tcd1, col_tcd2 = st.columns(2)
            with col_tcd1:
                element_colonne = st.selectbox(
                    "Que voulez-vous afficher en colonnes ?",
                    ["Division", "Semaine"] # Enlevé 'Annee' car elle est déjà fixée par le filtre principal
                )
            with col_tcd2:
                type_calcul = st.selectbox(
                    "Quelle statistique calculer ?",
                    ["Nombre de matchs joués", "Total des sets marqués (Resultat1)"]
                )

            # Calcul du TCD via Pandas
            if type_calcul == "Nombre de matchs joués":
                tcd_joueur1 = df_filtre.pivot_table(
                    index="Joueur1", 
                    columns=element_colonne, 
                    aggfunc="size", 
                    fill_value=0
                )
            else:
                tcd_joueur1 = df_filtre.pivot_table(
                    index="Joueur1", 
                    columns=element_colonne, 
                    values="Resultat1",
                    aggfunc="sum", 
                    fill_value=0
                )

            # Affichage du TCD style Excel
            st.subheader(f"📋 Tableau : Joueur 1 (Lignes) vs {element_colonne} (Colonnes)")
            if not tcd_joueur1.empty:
                st.dataframe(
                    tcd_joueur1.style.background_gradient(cmap="Blues"), 
                    use_container_width=True
                )
            else:
                st.info("Pas assez de données pour générer le tableau croisé.")

except Exception as e:
    st.error("Une erreur est survenue lors du chargement des données.")
    st.exception(e)
