import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Ping Club - Matchs", page_icon="🏓", layout="wide")
st.title("🏓 Historique et Détails des Matchs")

try:
    # 1. Connexion à Supabase
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- ÉTAPE 1 : RÉCUPÉRER LES ANNÉES SANS TOUT TÉLÉCHARGER ---
    @st.cache_data(ttl=600)
    def obtenir_annees_uniques():
        reponse_annees = conn.table("test").select("Annee").execute()
        df_annees = pd.DataFrame(reponse_annees.data)
        if not df_annees.empty:
            return sorted(list(df_annees["Annee"].astype(str).unique()))
        return []

    liste_annees = obtenir_annees_uniques()

    # --- ZONE DES FILTRES ---
    st.subheader("🔍 Filtrer les matchs")
    
    # On crée 3 colonnes pour nos filtres principaux
    f_col1, f_col2, f_col3 = st.columns(3)

    with f_col1:
        if liste_annees:
            annee_choisie = st.selectbox("1. Sélectionnez une Année :", liste_annees)
        else:
            annee_choisie = None
            st.warning("Aucune année trouvée.")

    # --- ÉTAPE 2 : CHARGEMENT DU SOUS-ENSEMBLE DE L'ANNÉE ---
    if annee_choisie:
        # On télécharge UNIQUEMENT les matchs de l'année sélectionnée (Adieu le timeout !)
        reponse_base = conn.table("test").select("*").eq("Annee", annee_choisie).execute()
        df_annee = pd.DataFrame(reponse_base.data)

        if df_annee.empty:
            st.info(f"Aucun match trouvé pour l'année {annee_choisie}.")
        else:
            
            with f_col2:
                # Liste unique des Clubs (Equipe1) pour cette année spécifique
                liste_clubs = ["Tous les clubs"] + sorted(list(df_annee["Equipe1"].dropna().unique()))
                club_choisi = st.selectbox("2. Filtrer par Club (Equipe 1) :", liste_clubs)

            with f_col3:
                # Liste unique des Joueurs (Joueur1) pour cette année spécifique
                liste_joueurs = ["Tous les joueurs"] + sorted(list(df_annee["Joueur1"].dropna().unique()))
                joueur_choisi = st.selectbox("3. Filtrer par Joueur (Joueur 1) :", liste_joueurs)

            # --- APPLICATION DES FILTRES EN LOCAL ---
            df_filtre = df_annee.copy()

            # Filtre Club (Equipe1)
            if club_choisi != "Tous les clubs":
                df_filtre = df_filtre[df_filtre["Equipe1"] == club_choisi]

            # Filtre Joueur (Joueur1)
            if joueur_choisi != "Tous les joueurs":
                df_filtre = df_filtre[df_filtre["Joueur1"] == joueur_choisi]

            # --- AFFICHAGE DU TABLEAU DES MATCHS ---
            st.subheader(f"📊 Résultats ({len(df_filtre)} match(s) affiché(s))")
            
            colonnes_affichage = [
                "id", "Annee", "Division", "Semaine", "Match", 
                "Equipe1", "Joueur1", "ClassementJ1", "Resultat1.1",
                "Resultat2.1", "ClassementJ2", "Joueur2", "Equipe2"
            ]
            st.dataframe(df_filtre[colonnes_affichage], use_container_width=True, hide_index=True)

            # --- SECTION TABLEAU CROISÉ DYNAMIQUE (TCD) ---
            st.markdown("---")
            st.header("📊 Tableau Croisé Dynamique (Joueur 1 uniquement)")
            st.write("Analyse croisée basée sur votre sélection ci-dessus.")

            col_tcd1, col_tcd2 = st.columns(2)
            with col_tcd1:
                element_colonne = st.selectbox(
                    "Que voulez-vous afficher en colonnes ?",
                    ["Division", "Semaine"]
                )
            with col_tcd2:
                type_calcul = st.selectbox(
                    "Quelle statistique calculer ?",
                    ["Nombre de matchs joués", "Total des sets marqués (Resultat1)"]
                )

            # Calcul du TCD
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

            # Affichage du TCD
            st.subheader(f"📋 Tableau : Joueur 1 (Lignes) vs {element_colonne} (Colonnes)")
            if not tcd_joueur1.empty:
                st.dataframe(
                    tcd_joueur1.style.background_gradient(cmap="Blues"), 
                    use_container_width=True
                )
            else:
                st.info("Pas assez de données pour générer le tableau croisé avec ces filtres.")

except Exception as e:
    st.error("Une erreur est survenue lors du chargement des données.")
    st.exception(e)
