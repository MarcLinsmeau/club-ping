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
            
            # Gestion des noms avec mention Forfait éventuelle
            nom_eq1 = donnees['equipe_1'] + " (FORFAIT)" if donnees.get('forfait_equipe_1') else donnees['equipe_1']
            nom_eq2 = donnees['equipe_2'] + " (FORFAIT)" if donnees.get('forfait_equipe_2') else donnees['equipe_2']

            # Métadonnées et score final
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Division", donnees["division"])
                st.metric("Semaine du calendrier", donnees["semaine"])
            with col2:
                score_final_formate = f"{donnees['score_global_equipe_1']} - {donnees['score_global_equipe_2']}"
                st.metric("Score de la rencontre", score_final_formate)

            st.subheader(f"🏆 {nom_eq1} 🆚 {nom_eq2}")

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
    st.subheader("Extraction globale d'une
