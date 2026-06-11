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

            # Vérification de la présence des colonnes requises pour le calcul
            colonnes_requises = ["MatchNonFF", "Match Joué", "VictoireJ1"]
            if all(col in df_resultat.columns for col in colonnes_requises):
                
                # Pivot de table initial AVEC les marges de totaux activées (margins=True)
                tcd_bilan = df_resultat.pivot_table(
                    index=["Equipe1", "Joueur1", "ClassementJ1", "Division", "Semaine"], 
                    values=["MatchNonFF", "Match Joué", "VictoireJ1"],
                    aggfunc={
                        "MatchNonFF": "size",   # Compte les sélections (lignes)
                        "Match Joué": "sum",    # Somme des matchs joués
                        "VictoireJ1": "sum"     # Somme des victoires
                    },
                    fill_value=0,
                    margins=True,               # Active la ligne de TOTAL global automatique
                    margins_name="TOTAL"        # Renomme la ligne "All" par "TOTAL"
                )

                if not tcd_bilan.empty:
                    # Reconstruction sécurisée pour l'ordre initial des colonnes
                    colonnes_existantes = [c for c in ["MatchNonFF", "Match Joué", "VictoireJ1"] if c in tcd_bilan.columns]
                    tcd_bilan = tcd_bilan[colonnes_existantes]
                    
                    # Recalcul dynamique et propre du pourcentage de victoires (y compris pour la ligne TOTAL)
                    tcd_bilan["Taux Victoires"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match Joué"]).fillna(0)) * 100

                    # Application des noms propres pour les en-têtes du tableau
                    tcd_bilan.columns = [
                        "Sélections", 
                        "Matchs Joués", 
                        "Matchs Gagnés", 
                        "% Victoires"
                    ]

                    # Tri des valeurs en excluant la ligne globale 'TOTAL' pour qu'elle reste tout en bas
                    if "TOTAL" in tcd_bilan.index.get_level_values(0):
                        ligne_total = tcd_bilan.xs("TOTAL", level=0, drop_level=False)
                        tcd_sans_total = tcd_bilan.drop("TOTAL", level=0)
                        tcd_sans_total = tcd_sans_total.sort_values(by=["Equipe1", "Joueur1", "Semaine"], ascending=True)
                        tcd_bilan = pd.concat([tcd_sans_total, ligne_total])
                    else:
                        tcd_bilan = tcd_bilan.sort_values(by=["Equipe1", "Joueur1", "Semaine"], ascending=True)

                    # Affichage final de la matrice de performance
                    st.subheader("📋 Tableau de synthèse des performances")
                    
                    # Application du style Pandas (dégradé unique sur % Victoires)
                    tcd_style = tcd_bilan.style.format({
                        "Sélections": "{:,.0f}",
                        "Matchs Joués": "{:,.0f}",
                        "Matchs Gagnés": "{:,.0f}",
                        "% Victoires": "{:.1f}%"
                    }).background_gradient(
                        cmap="RdYlGn", 
                        subset=["% Victoires"],
                        vmin=0,
                        vmax=100,
                        axis=0
                    ).set_table_styles([
                        # Ciblage complet de toutes les cellules standards
                        {"selector": "th, td, th.row_heading, th.col_heading, td.data, .blank", "props": [
                            ("vertical-align", "top !important"),
                            ("text-align", "left !important")
                        ]},
                        # Forçage du quadrillage foncé
                        {"selector": "th, td, th.row_heading, th.col_heading, td.data", "props": [
                            ("border", "1px solid #555555 !important")
                        ]},
                        # Marges de confort
                        {"selector": "th, td", "props": [
                            ("padding", "8px !important")
                        ]},
                        # --- INJECTION CSS POUR LE STYLE EN GRAS DE LA LIGNE TOTAL ---
                        # On repère l'élément contenant le texte 'TOTAL' et on met toute sa ligne en gras
                        {"selector": "tr:has(th:contains('TOTAL')), tr:has(td:contains('TOTAL'))", "props": [
                            ("font-weight", "bold !important"),
                            ("background-color", "#f0f2f6 !important") # Légère teinte grise pour détacher le bloc
                        ]}
                    ], overwrite=False)
                    
                    # Rendu HTML propre forcé sans défilement
                    st.write(tcd_style.to_html(escape=False), unsafe_allow_html=True)
                    
                else:
                    st.info("Données insuffisantes pour générer ce tableau croisé.")
            else:
                st.error("Une ou plusieurs colonnes de calcul ('MatchNonFF', 'Match Joué', 'VictoireJ1') sont introuvables.")
                
except Exception as e:
    st.error("Une erreur technique est survenue lors de l'exécution de l'application.")
    st.exception(e)
