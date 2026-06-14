# app.py
import streamlit as st
from ScrapPage import lister_urls_matchs_division, scraper_match_table_tennis

# Configuration globale de la page Streamlit
st.set_page_config(
    page_title="Scraper FROTTBF", page_icon="🏓", layout="centered"
)
st.title("🏓 Outil d'extraction Tennis de Table FROTTBF")

# Création des deux onglets principaux
onglet1, onglet2 = st.tabs(
    ["📄 Analyser un match", "🗂️ Scanner une division complète"]
)


# --- ONGLET 1 : ANALYSE D'UN SEUL MATCH ---
with onglet1:
    st.subheader("Extraction d'une feuille de match unique")
    url_match_defaut = (
        "https://www.frottbf.org/voirfeuille.php?semaine=2&match=9908"
    )
    url_saisie_match = st.text_input(
        "Entrez l'URL du match :", value=url_match_defaut, key="match_url"
    )

    if st.button("Analyser ce match", type="primary"):
        with st.spinner("Extraction en cours..."):
            donnees = scraper_match_table_tennis(url_saisie_match)

        if "erreur" in donnees:
            st.error(donnees["erreur"])
        elif not donnees["matchs"]:
            st.error("⚠️ Aucun match trouvé dans la page.")
        else:
            st.success("🎉 Données du match extraites avec succès !")
            
            # Métadonnées et score final
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Division", donnees["division"])
                st.metric("Semaine du calendrier", donnees["semaine"])
            with col2:
                score_final_formate = f"{donnees['score_global_equipe_1']} - {donnees['score_global_equipe_2']}"
                st.metric("Score de la rencontre", score_final_formate)

            st.subheader(f"🏆 {donnees['equipe_1']} 🆚 {donnees['equipe_2']}")

            # Tableau minimaliste et propre des 16 matchs individuels
            st.write("### 📊 Détails des 16 matchs individuels")
            lignes_minimales = []
            for m in donnees["matchs"]:
                lignes_minimales.append({
                    "N°": m["numero_match"],
                    "Joueur 1 (Club Visité)": f"{m['joueur_1']['nom']} ({m['joueur_1']['classement']})",
                    "Score Sets": f"{m['sets_joueur_1']} - {m['sets_joueur_2']}",
                    "Joueur 2 (Club Visiteur)": f"{m['joueur_2']['nom']} ({m['joueur_2']['classement']})"
                })
            st.table(lignes_minimales)


# --- ONGLET 2 : SCAN DE TOUTE LA DIVISION ---
with onglet2:
    st.subheader("Extraction globale d'une division complète")
    url_div_defaut = "https://www.frottbf.org/resultat.php?division=140"
    url_saisie_div = st.text_input(
        "Entrez l'URL de la division :", value=url_div_defaut, key="div_url"
    )

    if st.button("Lancer le scan de la division", type="primary"):
        with st.spinner("Lecture du calendrier de la division..."):
            liens_decouverts = lister_urls_matchs_division(url_saisie_div)

        if not liens_decouverts:
            st.error("⚠️ Aucun lien de match trouvé sur cette page de division.")
        else:
            st.success(f"🔥 **{len(liens_decouverts)}** rencontres détectées au calendrier.")

            tous_les_matchs_scrapes = []
            barre_progression = st.progress(0)
            status_text = st.empty()

            # Extraction en masse à pleine vitesse (sans micropause)
            for index, lien in enumerate(liens_decouverts):
                status_text.text(f"Analyse rencontre {index+1}/{len(liens_decouverts)}...")
                resultat_m = scraper_match_table_tennis(lien)
                
                if "erreur" not in resultat_m:
                    tous_les_matchs_scrapes.append(resultat_m)
                    
                barre_progression.progress((index + 1) / len(liens_decouverts))

            # Nettoyage des éléments de chargement
            status_text.empty()
            barre_progression.empty()
            st.success("✅ Extraction de la division terminée avec succès !")

            # --- AFFICHAGE MINIMALISTE DE TOUTES LES RENCONTRES ---
            st.write("### 📅 Liste récapitulative des rencontres de la saison")
            
            recap_rencontres = []
            for renc in tous_les_matchs_scrapes:
                # Utilisation directe des nouvelles variables de score global calculées par le scraper
                score_visit = renc.get("score_global_equipe_1", 0)
                score_visiteur = renc.get("score_global_equipe_2", 0)
                
                recap_rencontres.append({
                    "Semaine": f"Semaine {renc.get('semaine', '?')}",
                    "Équipe Visité": renc.get("equipe_1", "Inconnue"),
                    "Score Global": f"{score_visit} - {score_visiteur}",
                    "Équipe Visiteur": renc.get("equipe_2", "Inconnue")
                })
            
            # Affichage dans un tableau Streamlit dynamique, triable et scannable
            st.dataframe(recap_rencontres, use_container_width=True)
