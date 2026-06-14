# app.py
import streamlit as st
from scraper import lister_urls_matchs_division, scraper_match_table_tennis

st.set_page_config(
    page_title="Scraper FROTTBF", page_icon="🏓", layout="centered"
)
st.title("🏓 Outil d'extraction Tennis de Table FROTTBF")

onglet1, onglet2 = st.tabs(
    ["📄 Analyser un match", "🗂️ Scanner une division complète"]
)

# --- ONGLET 1 : UN SEUL MATCH ---
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
            st.error("⚠️ Aucun match trouvé.")
        else:
            st.success("🎉 Match extrait avec succès !")
            st.metric("Division", donnees["division"])
            st.subheader(f"🏆 {donnees['equipe_1']} 🆚 {donnees['equipe_2']}")

            # Tableau épuré des 16 rencontres individuelles
            st.write("### 📊 Détails des 16 matchs")
            
            # Formate proprement pour un affichage minimaliste
            lignes_minimales = []
            for m in donnees["matchs"]:
                lignes_minimales.append({
                    "N°": m["numero_match"],
                    "Joueur 1": f"{m['joueur_1']['nom']} ({m['joueur_1']['classement']})",
                    "Score": f"{m['sets_joueur_1']} - {m['sets_joueur_2']}",
                    "Joueur 2": f"{m['joueur_2']['nom']} ({m['joueur_2']['classement']})"
                })
            st.table(lignes_minimales)


# --- ONGLET 2 : TOUTE LA DIVISION ---
with onglet2:
    st.subheader("Extraction globale d'une division")
    url_div_defaut = "https://www.frottbf.org/resultat.php?division=140"
    url_saisie_div = st.text_input(
        "Entrez l'URL de la division :", value=url_div_defaut, key="div_url"
    )

    if st.button("Lancer le scan de la division", type="primary"):
        with st.spinner("Lecture du calendrier de la division..."):
            liens_decouverts = lister_urls_matchs_division(url_saisie_div)

        if not liens_decouverts:
            st.error("⚠️ Aucun match trouvé.")
        else:
            st.success(f"🔥 **{len(liens_decouverts)}** rencontres détectées.")

            tous_les_matchs_scrapes = []
            barre_progression = st.progress(0)
            status_text = st.empty()

            # Extraction en masse sans pause
            for index, lien in enumerate(liens_decouverts):
                status_text.text(f"Analyse rencontre {index+1}/{len(liens_decouverts)}...")
                resultat_m = scraper_match_table_tennis(lien)
                if "erreur" not in resultat_m:
                    tous_les_matchs_scrapes.append(resultat_m)
                barre_progression.progress((index + 1) / len(liens_decouverts))

            status_text.empty()
            barre_progression.empty()
            st.success("✅ Extraction globale terminée !")

            # --- AFFICHAGE MINIMALISTE DE TOUTES LES RENCONTRES ---
            st.write("### 📅 Liste récapitulative des rencontres")
            
            recap_rencontres = []
            for renc in tous_les_matchs_scrapes:
                # Calcule le score global de la rencontre (ex: 10 - 6)
                score_equipe1 = sum(1 for m in renc["matchs"] if m["sets_joueur_1"] > m["sets_joueur_2"])
                score_equipe2 = sum(1 for m in renc["matchs"] if m["sets_joueur_2"] > m["sets_joueur_1"])
                
                recap_rencontres.append({
                    "Semaine": f"Sem {renc['semaine']}",
                    "Équipe Visité": renc["equipe_1"],
                    "Score Global": f"{score_equipe1} - {score_equipe2}",
                    "Équipe Visiteur": renc["equipe_2"]
                })
            
            # Affichage sous forme de tableau épuré, idéal à lire
            st.dataframe(recap_rencontres, use_container_width=True)
