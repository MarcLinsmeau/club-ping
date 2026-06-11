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


    # --- INTERFACE ET FILTRES EN CASCADE STRICTE ---
    st.subheader("🔍 Filtres de sélection")
    col1, col2, col3 = st.columns(3)

    # 1. FILTRE ANNÉE (Toujours actif au démarrage)
    liste_annees = charger_annees()
    options_annees = ["--- Choisir une année ---"] + liste_annees

    with col1:
        annee_choisie = st.selectbox("1. Année :", options_annees, index=0)

    # Détermination du statut du filtre Club
    annee_valide = annee_choisie != "--- Choisir une année ---"

    # 2. FILTRE CLUB (Verrouillé tant qu'une année n'est pas choisie)
    if annee_valide:
        liste_clubs = charger_clubs(annee_choisie)
        options_clubs = ["--- Choisir un club ---"] + liste_clubs
        desactiver_club = False
    else:
        options_clubs = ["Veuillez d'abord choisir une année"]
        desactiver_club = True

    with col2:
        club_choisi = st.selectbox(
            "2. Club (Equipe 1) :", 
            options_clubs, 
            index=0, 
            disabled=desactiver_club
        )

    # Détermination du statut du filtre Joueur
    club_valide = annee_valide and club_choisi != "--- Choisir un club ---" and club_choisi != "Veuillez d'abord choisir une année"

    # 3. FILTRE JOUEUR (Verrouillé tant qu'un club n'est pas choisi)
    if club_valide:
        liste_joueurs = charger_joueurs(annee_choisie, club_choisi)
        options_joueurs = ["Tous les joueurs"] + liste_joueurs
        desactiver_joueur = False
    else:
        options_joueurs = ["Veuillez d'abord choisir un club"]
        desactiver_joueur = True

    with col3:
        joueur_choisi = st.selectbox(
            "3. Joueur (Joueur 1) :", 
            options_joueurs, 
            index=0, 
            disabled=desactiver_joueur
        )


    # --- ENCLENCHEMENT DE LA REQUÊTE ET AFFICHAGE ---
    if not annee_valide:
        st.info("💡 En attente de vos critères : Veuillez sélectionner une **Année** pour commencer.")
    elif not club_valide:
        st.info("💡 Étape suivante : Veuillez sélectionner un **Club** pour charger les matchs correspondants.")
    else:
        requete = conn.table("test").select("*").eq("Annee", annee_choisie).eq("Equipe1", club_choisi)

        if joueur_choisi != "Tous les joueurs":
            requete = requete.eq("Joueur1", joueur_choisi)

        reponse = requete.limit(5000).execute()
        df_resultat = pd.DataFrame(reponse.data)

        if df_resultat.empty:
            st.warning("⚠️ Aucun record trouvé pour cette combinaison précise.")
        else:
            st.subheader(f"📋 Records trouvés ({len(df_resultat)} match(s))")
            
            # Réorganisation des colonnes d'affichage avec toutes tes nouvelles variables SQL
            colonnes_ordonnees = [
                "id", "Annee", "Division", "Semaine", "Match", 
                "Equipe1", "Joueur1", "ClassementJ1", "ClassJ1New", "PointsJ1",
                "Resultat1.1", "Resultat1.2", "Resultat2.1", "Resultat2.2", 
                "ClassementJ2", "ClassJ2New", "Joueur2", "Equipe2", 
                "VictoireJ1", "VictoireJ2", "Match Joué", "MatchNonFF"
            ]
            colonnes_visibles = [col for col in colonnes_ordonnees if col in df_resultat.columns]
            
            # Affichage du tableau de données brutes
            st.dataframe(df_resultat[colonnes_visibles], use_container_width=True, hide_index=True)


           # --- SECTION TABLEAU CROISÉ DYNAMIQUE (TCD) RE-STRUCTURÉ ---
            st.markdown("---")
            st.header("📊 Tableau Croisé Dynamique : Analyse des Victoires")
            st.write("Ce tableau affiche le total des victoires par Équipe, Joueur, Classement et Division.")

            # On vérifie que la colonne "VictoireJ1" est bien présente dans le DataFrame
            if "VictoireJ1" in df_resultat.columns:
                
                # Construction du TCD avec tes nouvelles dimensions en lignes
                tcd_performance = df_resultat.pivot_table(
                    index=["Equipe1", "Joueur1", "ClassementJ1", "Division"], # Toutes tes dimensions en lignes
                    values=["Match Joué", "VictoireJ1"],                                      # La métrique à analyser
                    aggfunc="sum",                                            # On fait la somme des victoires
                    fill_value=0
                )

                # Optionnel : On renomme la colonne pour que ce soit plus joli à l'affichage
                tcd_performance.columns = ["Total Victoires"]

                # Affichage du TCD
                if not tcd_performance.empty:
                    st.subheader("📋 Matrice des performances (Somme des Victoires)")
                    
                    # On utilise un dégradé Vert ("Greens") car on parle de victoires !
                    st.dataframe(
                        tcd_performance.style.background_gradient(cmap="Greens", axis=0), 
                        use_container_width=True
                    )
                else:
                    st.info("Données insuffisantes pour générer ce tableau croisé.")
            else:
                st.error("La colonne 'VictoireJ1' n'a pas été trouvée dans les données de Supabase.")
except Exception as e:
    st.error("Une erreur technique est survenue.")
    st.exception(e)
