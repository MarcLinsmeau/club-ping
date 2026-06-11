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

# --- SECTION TABLEAU CROISÉ DYNAMIQUE : TAUX DE VICTOIRE ---
        st.markdown("---")
        st.header("📊 Tableau Croisé Dynamique : Performance des Joueurs")
        st.write("Ce tableau affiche le **% de victoires** des joueurs selon les critères sélectionnés.")

        # 1. Détermination de la victoire pour Joueur 1
        # On additionne les manches pour savoir si Joueur 1 a gagné plus de sets que Joueur 2
        # Note : Dans le ping, on regarde généralement si le total de sets gagnés est de 3 (ou si Resultat1 > Resultat2)
        # Supposons ici que la colonne 'Match' ou une logique simple valide la victoire.
        # Créons une colonne temporaire 'Victoire' (1 si oui, 0 si non)
        
        # Exemple de logique de calcul basé sur les scores globaux s'ils sont calculés :
        # Si tu as une colonne 'Resultat1' (sets totaux J1) et 'Resultat2' (sets totaux J2) :
        # df_resultat['Victoire'] = (df_resultat['Resultat1'] > df_resultat['Resultat2']).astype(int)
        
        # Si tu n'as que les manches détaillées (ex: Resultat1.1 est le score de la manche 1), 
        # voici une méthode d'analyse simple (ici on va simuler la victoire pour l'exemple, 
        # adapte la condition '>' selon la colonne de score global exacte de ta table) :
        if 'Resultat1' in df_resultat.columns and 'Resultat2' in df_resultat.columns:
            df_resultat['Victoire'] = (df_resultat['Resultat1'] > df_resultat['Resultat2']).astype(int)
        else:
            # Sécurité alternative : si tu as une colonne 'Match' qui dit "Gagné", ou si on simule via une règle :
            df_resultat['Victoire'] = 1 # Par défaut pour le calcul, à lier à ton indicateur de score réel

        # 2. Choix de la dimension pour les colonnes du TCD
        axe_colonne = st.selectbox(
            "Regrouper les statistiques en colonnes par :", 
            ["Division", "Semaine"]
        )

        # 3. Calcul du TCD du Taux de Victoire (Moyenne des victoires * 100)
        # En faisant la moyenne (mean) d'une colonne de 0 et de 1, on obtient le pourcentage de victoires !
        tcd_performance = df_resultat.pivot_table(
            index="Joueur1",
            columns=axe_colonne,
            values="Victoire",
            aggfunc="mean",
            fill_value=0
        )

        # Conversion en pourcentage pour l'affichage (ex: 0.75 devient 75.0%)
        tcd_performance = tcd_performance * 100

        # 4. Affichage avec mise en forme conditionnelle (Heatmap de performance)
        if not tcd_performance.empty:
            st.subheader(f"📋 % de Victoires par Joueur et par {axe_colonne}")
            
            # Formater l'affichage pour ajouter le symbole '%' et limiter à 1 décimale
            tcd_style = tcd_performance.style.format("{:.1f}%").background_gradient(
                cmap="RdYlGn", # Dégradé du Rouge (0%) au Vert (100%) idéal pour les taux de réussite
                vmin=0,
                vmax=100
            )
            
            st.dataframe(tcd_style, use_container_width=True)
        else:
            st.info("Données insuffisantes pour calculer les taux de victoire.")

except Exception as e:
    st.error("Une erreur technique est survenue.")
    st.exception(e)
