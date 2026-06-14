# scraper.py
import re
import streamlit as st
import requests
from bs4 import BeautifulSoup

def scraper_match_table_tennis(url):
    """
    Extrait dynamiquement les données d'une feuille de match FROTTBF.
    Gère les blocages de serveurs en simulant un navigateur humain.
    """
    # Configuration de faux en-têtes de navigateur (Headers) pour éviter le blocage sur Streamlit Cloud
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.frottbf.org/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {
                "erreur": f"Le site FROTTBF a répondu avec un code d'erreur : {response.status_code}",
                "matchs": []
            }        
    except Exception as e:
        return {
            "erreur": f"Impossible de se connecter au serveur : {str(e)}",
            "matchs": []
        }

    soup = BeautifulSoup(response.content, "html.parser")
    st.write(soup)

    # --- 1. Extraction de la Division ---
    h1_text = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
    division = h1_text.replace("Rencontre de division", "").strip()

    # --- 2. Extraction de la Semaine ---
    semaine = None
    semaine_text = soup.find(string=re.compile(r"Semaine\s+\d+"))
    if semaine_text:
        match_semaine = re.search(r"Semaine\s+(\d+)", semaine_text)
        if match_semaine:
            semaine = int(match_semaine.group(1))

    # --- 3. Extraction de l'Année ---
    annee = 2025  # Année par défaut demandée
    date_label = soup.find(string=re.compile(r"Date du match"))
    if date_label:
        parent_text = date_label.parent.get_text()
        match_annee = re.search(r"(\d{4})-\d{2}-\d{2}", parent_text)
        if match_annee:
            annee = int(match_annee.group(1))

    # --- 4. Extraction des Équipes ---
    equipe1, equipe2 = "", ""
    for h4 in soup.find_all("h4"):
        texte = h4.get_text(strip=True)
        if "Club Visité" in texte:
            nom_brut = texte.split(":")[-1].strip()
            equipe1 = re.sub(r"^\d+\s*-\s*", "", nom_brut)  # Retire le matricule "234 - "
        elif "Club Visiteur" in texte:
            nom_brut = texte.split(":")[-1].strip()
            equipe2 = re.sub(r"^\d+\s*-\s*", "", nom_brut)  # Retire le matricule "94 - "

    # --- 5. Extraction des 16 Matchs Individuels ---
    matchs_individuels = []
    table = soup.find("table")

    if table:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            # Une ligne valide sur la FROTTBF contient au moins 9 colonnes de données
            if len(cols) >= 9:
                try:
                    ordre = int(cols[0].get_text(strip=True))

                    # Joueur 1 (Visité) et son classement
                    j1_brut = cols[1].get_text(strip=True)
                    j1_classement = "Non spécifié"
                    match_c1 = re.search(r"\((.*?)\)", j1_brut)
                    if match_c1:
                        j1_classement = match_c1.group(1)
                        j1_nom = re.sub(r"\(.*?\)", "", j1_brut).strip()
                    else:
                        j1_nom = j1_brut

                    # Joueur 2 (Visiteur) et son classement
                    j2_brut = cols[5].get_text(strip=True)
                    j2_classement = "Non spécifié"
                    match_c2 = re.search(r"\((.*?)\)", j2_brut)
                    if match_c2:
                        j2_classement = match_c2.group(1)
                        j2_nom = re.sub(r"\(.*?\)", "", j2_brut).strip()
                    else:
                        j2_nom = j2_brut

                    # Nombre de sets gagnés (deux dernières colonnes du tableau)
                    sets_j1 = int(cols[-2].get_text(strip=True))
                    sets_j2 = int(cols[-1].get_text(strip=True))

                    matchs_individuels.append({
                        "numero_match": ordre,
                        "joueur_1": {
                            "nom": j1_nom,
                            "classement": j1_classement
                        },
                        "joueur_2": {
                            "nom": j2_nom,
                            "classement": j2_classement
                        },
                        "sets_joueur_1": sets_j1,
                        "sets_joueur_2": sets_j2
                    })
                except (ValueError, IndexError):
                    # Ignore proprement les lignes d'en-tête intermédiaires ou corrompues
                    continue

    return {
        "annee": annee,
        "division": division,
        "semaine": semaine,
        "equipe_1": equipe1,
        "equipe_2": equipe2,
        "matchs": matchs_individuels
    }
