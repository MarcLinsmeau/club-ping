# app.py
import streamlit as st
from ScrapPage import lister_urls_matchs_division, scraper_match_table_tennis

# Config de la page
st.set_page_config(
    page_title="Scraper FROTTBF", page_icon="🏓", layout="centered"
)

st.title("🏓 Outil d'extraction Tennis de Table FROTTBF")

# Création de deux onglets pour structurer l'application
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
            st.error("⚠️ Aucun match trouvé. Vérifiez l'URL.")
        else:
            st.success("🎉 Match extrait avec succès !")
            st.metric("Division", donnees["division"])
            st.subheader(f"🏆 {donnees['equipe_1']} 🆚 {donnees['equipe_2']}")

            # Affichage rapide sous forme de tableau
            st.write("### 📊 Détails des 16 matchs")
            st.dataframe(donnees["matchs"])


# --- ONGLET 2 : SCAN DE TOUTE LA DIVISION (SANS MICROPAUSE) ---
with onglet2:
    st.subheader("Extraction de tous les liens d'une division")
    url_div_defaut = "https://www.frottbf.org/resultat.php?division=140"
    url_saisie_div = st.text_input(
        "Entrez l'URL de la division :", value=url_div_defaut, key="div_url"
    )

    if st.button("Lancer le scan de la division", type="primary"):
        with st.spinner("Lecture du calendrier de la division en cours..."):
            liens_decouverts = lister_urls_matchs_division(url_saisie_div)

        if not liens_decouverts:
            st.error(
                "⚠️ Aucun lien de match trouvé. La page est peut-être inaccessible ou la division est invalide."
            )
        else:
            st.success(
                f"🔥 Récupération terminée ! **{len(liens_decouverts)}** liens de feuilles de matchs uniques ont été extraits."
            )

            # Option d'affichage ou de traitement en masse direct
            st.write("### 🔗 Liste complète des URLs récoltées")
            st.write(liens_decouverts)

            # Exemple d'extraction immédiate en chaîne (sans aucune pause)
            st.markdown("---")
            st.write("### ⚙️ Lancement de l'extraction globale en continu...")

            tous_les_matchs_scrapes = []
            barre_progression = st.progress(0)

            # Traitement de masse à pleine vitesse
            for index, lien in enumerate(liens_decouverts):
                resultat_m = scraper_match_table_tennis(lien)
                if "erreur" not in resultat_m:
                    tous_les_matchs_scrapes.append(resultat_m)

                # Mise à jour graphique de la barre de progression
                barre_progression.progress((index + 1) / len(liens_decouverts))

            st.success(
                f"✅ Extraction en masse terminée ! **{len(tous_les_matchs_scrapes)}** feuilles de matchs ont été entièrement téléchargées et décodées."
            )

            # Aperçu des données de la division globale compilées
            if tous_les_matchs_scrapes:
                st.write("Exemple de la première rencontre compilée :")
                st.json(tous_les_matchs_scrapes[0])
