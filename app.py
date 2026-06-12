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
            
            # Réorganisation des colonnes d'affichage selon ton schéma SQL
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


            # --- SECTION TABLEAU CROISÉ DYNAMIQUE (TCD) SANS AUCUN DEFILEMENT ---
            st.markdown("---")
            st.header("📊 Tableau Croisé Dynamique : Bilan des Joueurs")
            st.write("Ce tableau récapitule les statistiques complètes. Il s'affiche en entier sans barre de défilement.")

            # Ajout sécurisé de 'PointsJ1' dans la validation des colonnes de base
            colonnes_requises = ["MatchNonFF", "Match", "VictoireJ1", "PointsJ1"]
            if all(col in df_resultat.columns for col in colonnes_requises):
                
                # 1. Pivot de table initial (Inclusion de PointsJ1)
                tcd_base = df_resultat.pivot_table(
                    index=["Equipe1", "Joueur1", "ClassementJ1", "Division", "Semaine"], 
                    values=["MatchNonFF", "Match", "VictoireJ1", "PointsJ1"],
                    aggfunc={
                        "MatchNonFF": "size",   
                        "Match": "size",    
                        "VictoireJ1": "sum",
                        "PointsJ1": "sum" # Ajout du calcul de la somme des points de classement gagnés/perdus
                    },
                    fill_value=0
                )

                if not tcd_base.empty:
                    # Reconstruction ordonnée et explicite de nos colonnes de travail
                    colonnes_existantes = ["MatchNonFF", "Match", "VictoireJ1", "PointsJ1"]
                    tcd_base = tcd_base[colonnes_existantes]
                    
                    # Normalisation propre du niveau "Semaine" en chaînes de caractères
                    tcd_base.index = tcd_base.index.set_levels(tcd_base.index.levels[4].astype(str), level=4)
                    
                    # 2. CALCUL DES SOUS-TOTAUX PAR JOUEUR (La somme s'applique automatiquement sur PointsJ1)
                    totaux_joueurs = tcd_base.groupby(level=["Equipe1", "Joueur1"]).sum()
                    
                    # Remplissage des dimensions d'index pour insérer proprement la ligne de totalisation
                    totaux_joueurs["ClassementJ1"] = "TOTAL JOUEUR"
                    totaux_joueurs["Division"] = "TOTAL JOUEUR"
                    totaux_joueurs["Semaine"] = "TOTAL JOUEUR"
                    
                    totaux_joueurs = totaux_joueurs.set_index(["ClassementJ1", "Division", "Semaine"], append=True)
                    
                    # 3. FUSION DE LA BASE ET DES TOTAUX JOUEURS
                    tcd_bilan = pd.concat([tcd_base, totaux_joueurs])
                    
                    # 4. TRI PERSONNALISÉ POUR PROPULSER LE TOTAL AU-DESSUS DU DÉTAIL
                    tcd_bilan = tcd_bilan.sort_index(
                        level=["Equipe1", "Joueur1", "Semaine"],
                        key=lambda x: x.map(lambda val: "0" if val == "TOTAL JOUEUR" else str(val)) if x.name == "Semaine" else x
                    )
                    
                    # 5. CALCULS DES POURCENTAGES & RENOMMAGE DES COLONNES DES 4 METRICS
                    tcd_bilan["Taux Victoires"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match"]).fillna(0)) * 100
                    
                    # Réorganisation finale des colonnes pour l'affichage visuel
                    tcd_bilan = tcd_bilan[["MatchNonFF", "Match", "VictoireJ1", "Taux Victoires", "PointsJ1"]]
                    tcd_bilan.columns = ["Sélections", "Matchs Joués", "Matchs Gagnés", "% Victoires", "Points Gagnés J1"]

                    # Affichage final de la performance
                    st.subheader("📋 Tableau de synthèse des performances")
                    
                    # Application des styles CSS (Alignements haut/gauche, bordures serrées, surbrillance du gras)
                    tcd_style = tcd_bilan.style.format({
                        "Sélections": "{:,.0f}",
                        "Matchs Joués": "{:,.0f}",
                        "Matchs Gagnés": "{:,.0f}",
                        "% Victoires": "{:.1f}%",
                        "Points Gagnés J1": "{:+.0f}" # Formatage signé (+12 ou -7) pour l'évolution des points tennis de table
                    }).background_gradient(
                        cmap="RdYlGn", 
                        subset=["% Victoires"],
                        vmin=0,
                        vmax=100,
                        axis=0
                    ).set_table_styles([
                        # Alignement parfait sur l'intégralité des cellules générées
                        {"selector": "th, td, th.row_heading, th.col_heading, td.data, .blank", "props": [
                            ("vertical-align", "top !important"),
                            ("text-align", "left !important")
                        ]},
                        # Forçage global du quadrillage sombre
                        {"selector": "th, td, th.row_heading, th.col_heading, td.data", "props": [
                            ("border", "1px solid #555555 !important")
                        ]},
                        # Marges intérieures
                        {"selector": "th, td", "props": [
                            ("padding", "8px !important")
                        ]},
                        # Style en gras appliqué aux lignes de totaux par joueur
                        {"selector": "tr:has(th:contains('TOTAL')), tr:has(td:contains('TOTAL'))", "props": [
                            ("font-weight", "bold !important"),
                            ("background-color", "#edf2f7 !important")
                        ]}
                    ], overwrite=False)
                    
                    # Rendu final HTML propre sans défilement
                    st.write(tcd_style.to_html(escape=False), unsafe_allow_html=True)
                    
                else:
                    st.info("Données insuffisantes pour générer ce tableau croisé.")
            else:
                st.error("Une ou plusieurs colonnes de calcul ('MatchNonFF', 'Match', 'VictoireJ1', 'PointsJ1') sont introuvables.")
                
except Exception as e:
    st.error("Une erreur technique est survenue lors de l'exécution de l'application.")
    st.exception(e)
