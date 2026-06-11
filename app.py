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

    # 1. FILTRE ANNÉE
    liste_annees = charger_annees()
    options_annees = ["--- Choisir une année ---"] + liste_annees

    with col1:
        annee_choisie = st.selectbox("1. Année :", options_annees, index=0)

    annee_valide = annee_choisie != "--- Choisir une année ---"

    # 2. FILTRE CLUB
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

    club_valide = annee_valide and club_choisi != "--- Choisir un club ---" and club_choisi != "Veuillez d'abord choisir une année"

    # 3. FILTRE JOUEUR
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
            
            colonnes_ordonnees = [
                "id", "Annee", "Division", "Semaine", "Match", 
                "Equipe1", "Joueur1", "ClassementJ1", "ClassJ1New", "PointsJ1",
                "Resultat1.1", "Resultat1.2", "Resultat2.1", "Resultat2.2", 
                "ClassementJ2", "ClassJ2New", "Joueur2", "Equipe2", 
                "VictoireJ1", "VictoireJ2", "Match Joué", "MatchNonFF"
            ]
            colonnes_visibles = [col for col in colonnes_ordonnees if col in df_resultat.columns]
            
            st.dataframe(df_resultat[colonnes_visibles], use_container_width=True, hide_index=True)


            # --- SECTION TABLEAU CROISÉ DYNAMIQUE (TCD) REVISITÉ ---
            st.markdown("---")
            st.header("📊 Tableau Croisé Dynamique : Bilan des Joueurs")
            st.write("Ce tableau récapitule les statistiques complètes (trié par équipe, joueur et semaine).")

            colonnes_requises = ["MatchNonFF", "Match Joué", "VictoireJ1"]
            if all(col in df_resultat.columns for col in colonnes_requises):
                
                # 1. Création du Pivot de table initial
                tcd_bilan = df_resultat.pivot_table(
                    index=["Equipe1", "Joueur1", "ClassementJ1", "Division", "Semaine"], 
                    values=["MatchNonFF", "Match Joué", "VictoireJ1"],
                    aggfunc={
                        "MatchNonFF": "size",   
                        "Match Joué": "sum",    
                        "VictoireJ1": "sum"     
                    },
                    fill_value=0
                )

                if not tcd_bilan.empty:
                    colonnes_existantes = [c for c in ["MatchNonFF", "Match Joué", "VictoireJ1"] if c in tcd_bilan.columns]
                    tcd_bilan = tcd_bilan[colonnes_existantes]
                    
                    # 2. Calcul propre du Taux (valeur brute pour appliquer nos couleurs plus tard)
                    tcd_bilan["Taux Brut"] = (tcd_bilan["VictoireJ1"].div(tcd_bilan["Match Joué"]).fillna(0)) * 100

                    # 3. Tri du tableau par Équipe, Joueur puis Semaine
                    tcd_bilan = tcd_bilan.sort_values(by=["Equipe1", "Joueur1", "Semaine"], ascending=True)

                    # 4. Fonction Python pour injecter les couleurs directement dans les cellules HTML
                    def générer_ligne_html(row_index, row_data):
                        # Détermination de la couleur selon le pourcentage
                        taux = row_data["Taux Brut"]
                        if taux >= 75:
                            bg_color, text_color = "#006837", "#f1f1f1"  # Vert foncé sportif
                        elif taux >= 40:
                            bg_color, text_color = "#feffbe", "#000000"  # Jaune / Orange clair
                        else:
                            bg_color, text_color = "#a50026", "#f1f1f1"  # Rouge échec

                        # Construction des cellules HTML standards
                        html_cells = f"""
                        <td style='vertical-align: top !important; text-align: right;'>{int(row_data['MatchNonFF'])}</td>
                        <td style='vertical-align: top !important; text-align: right;'>{int(row_data['Match Joué'])}</td>
                        <td style='vertical-align: top !important; text-align: right;'>{int(row_data['VictoireJ1'])}</td>
                        <td style='vertical-align: top !important; text-align: right; background-color: {bg_color} !important; color: {text_color} !important; font-weight: bold;'>{taux:.1f}%</td>
                        """
                        return html_cells

                    # 5. Construction manuelle du tableau HTML complet pour un contrôle absolu
                    # On réinitialise l'index pour manipuler les colonnes facilement
                    df_html = tcd_bilan.reset_index()
                    
                    html_table = """
                    <style>
                    .tcd-custom { border-collapse: collapse !important; width: 100%; font-family: sans-serif; }
                    .tcd-custom th { background-color: #2b2b2b; color: white; padding: 10px; border: 1px solid #555555 !important; text-align: left; }
                    .tcd-custom td { padding: 8px; border: 1px solid #555555 !important; }
                    </style>
                    <table class='tcd-custom'>
                        <thead>
                            <tr>
                                <th>Équipe 1</th>
                                <th>Joueur 1</th>
                                <th>Classement</th>
                                <th>Division</th>
                                <th>Semaine</th>
                                <th style='text-align: right;'>Sélections</th>
                                <th style='text-align: right;'>Matchs Joués</th>
                                <th style='text-align: right;'>Matchs Gagnés</th>
                                <th style='text-align: right;'>% Victoires</th>
                            </tr>
                        </thead>
                        <tbody>
                    """

                    # Remplissage des lignes
                    for idx, row in df_html.iterrows():
                        html_table += "<tr>"
                        html_table += f"<td style='vertical-align: top !important;'>{row['Equipe1']}</td>"
                        html_table += f"<td style='vertical-align: top !important;'>{row['Joueur1']}</td>"
                        html_table += f"<td style='vertical-align: top !important;'>{row['ClassementJ1']}</td>"
                        html_table += f"<td style='vertical-align: top !important;'>{row['Division']}</td>"
                        html_table += f"<td style='vertical-align: top !important;'>{row['Semaine']}</td>"
                        html_table += générer_ligne_html(idx, row)
                        html_table += "</tr>"

                    html_table += "</tbody></table>"

                    # 6. Rendu final propre
                    st.subheader("📋 Tableau de synthèse des performances")
                    st.write(html_table, unsafe_allow_html=True)
                    
                else:
                    st.info("Données insuffisantes pour générer ce tableau croisé.")
            else:
                st.error("Une ou plusieurs colonnes de calcul ('MatchNonFF', 'Match Joué', 'VictoireJ1') sont introuvables.")
                
except Exception as e:
    st.error("Une erreur technique est survenue lors de l'exécution de l'application.")
    st.exception(e)
