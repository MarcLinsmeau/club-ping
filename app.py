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
    # On n'affiche rien tant que les critères minimaux (Année et Club) ne sont pas cochés
    if not annee_valide:
        st.info("💡 En attente de vos critères : Veuillez sélectionner une **Année** pour commencer.")
    elif not club_valide:
        st.info("💡 Étape suivante : Veuillez sélectionner un **Club** pour charger les matchs correspondants.")
    else:
        # Si Année et Club sont valides, on prépare la requête finale
        requete = conn.table("test").select("*").eq("Annee", annee_choisie).eq("Equipe1", club_choisi)

        # Si un joueur spécifique est demandé (et qu'on a pas laissé "Tous les joueurs")
        if joueur_choisi != "Tous les joueurs":
            requete = requete.eq("Joueur1", joueur_choisi)

        # Exécution (Sécurité limitée à 5000 lignes, mais ici avec Année + Club ce sera très léger)
        reponse = requete.limit(5000).execute()
        df_resultat = pd.DataFrame(reponse.data)

        if df_resultat.empty:
            st.warning("⚠️ Aucun record trouvé pour cette combinaison précise.")
        else:
            st.subheader(f"📋 Records trouvés ({len(df_resultat)} match(s))")
            
            # Structure d'affichage des colonnes
            colonnes_ordonnees = [
                "Annee", "Division", "Semaine", "Match", 
                "Equipe1", "Joueur1", "ClassementJ1", 
                "Resultat1.1", "Resultat1.2", "Resultat2.1", "Resultat2.2", 
                "ClassementJ2", "Joueur2", "Equipe2", "MatchNonFF"
            ]
            colonnes_visibles = [col for col in colonnes_ordonnees if col in df_resultat.columns]
            
            # Affichage final
            st.dataframe(df_resultat[colonnes_visibles], use_container_width=True, hide_index=True)

# --- SECTION TABLEAU CROISÉ DYNAMIQUE : COMPTAGE DES MATCHS ---
        st.markdown("---")
        st.header("📊 Tableau Croisé Dynamique : Volume de Matchs")
        st.write("Ce tableau croise les Équipes et les Joueurs (en lignes) avec les Années et les Semaines (en colonnes).")

        # 1. Construction du TCD multi-index
        # 'index=[...]' crée les sous-groupements en lignes (Équipe > Joueur)
        # 'columns=[...]' crée les sous-groupements en colonnes (Année > Semaine)
        tcd_comptage = df_resultat.pivot_table(
            index=["Equipe1", "Joueur1", "Annee", "Semaine"],
            columns=["Match Joué"],
            aggfunc="size",  # 'size' compte le nombre de lignes (matchs joués)
            fill_value=0     # Remplace les cases vides (où le joueur n'a pas joué) par un 0
        )

        # 2. Affichage du TCD
        if not tcd_comptage.empty:
            st.subheader("📋 Matrice d'activité (Nombre de matchs)")
            
            # Affichage avec un joli dégradé bleu pour repérer les joueurs les plus actifs
            st.dataframe(
                tcd_comptage.style.background_gradient(cmap="Blues", axis=None), 
                use_container_width=True
            )
        else:
            st.info("Données insuffisantes pour générer ce tableau croisé.")

except Exception as e:
    st.error("Une erreur technique est survenue.")
    st.exception(e)
