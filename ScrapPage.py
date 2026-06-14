# scraper.py
import re
import requests
from bs4 import BeautifulSoup


def scraper_match_table_tennis(url):
    """Extrait les données d'une feuille de match de tennis de table FROTTBF à partir de son URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {
                "erreur": f"Impossible d'accéder à la page (Status: {response.status_code})"
            }
    except Exception as e:
        return {"erreur": f"Erreur de connexion : {str(e)}"}

    soup = BeautifulSoup(response.content, "html.parser")

    # Extraction Division
    h1_text = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
    division = h1_text.replace("Rencontre de division", "").strip()

    # Extraction Semaine
    semaine = ""
    semaine_text = soup.find(string=re.compile(r"Semaine\s+\d+"))
    if semaine_text:
        match_semaine = re.search(r"Semaine\s+(\d+)", semaine_text)
        if match_semaine:
            semaine = int(match_semaine.group(1))

    # Extraction Année
    annee = 2025
    date_label = soup.find(string=re.compile(r"Date du match"))
    if date_label:
        parent_text = date_label.parent.get_text()
        match_annee = re.search(r"(\d{4})-\d{2}-\d{2}", parent_text)
        if match_annee:
            annee = int(match_annee.group(1))

    # Extraction Équipes
    equipe1, equipe2 = "", ""
    for h4 in soup.find_all("h4"):
        texte = h4.get_text(strip=True)
        if "Club Visité" in texte:
            nom_brut = texte.split(":")[-1].strip()
            equipe1 = re.sub(r"^\d+\s*-\s*", "", nom_brut)
        elif "Club Visiteur" in texte:
            nom_brut = texte.split(":")[-1].strip()
            equipe2 = re.sub(r"^\d+\s*-\s*", "", nom_brut)

    # Extraction des Matchs
    matchs_individuels = []
    table = soup.find("table")

    if table:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 9:
                try:
                    ordre = int(cols[0].get_text(strip=True))

                    # Joueur 1
                    j1_brut = cols[1].get_text(strip=True)
                    j1_classement = ""
                    match_c1 = re.search(r"\((.*?)\)", j1_brut)
                    if match_c1:
                        j1_classement = match_c1.group(1)
                        j1_nom = re.sub(r"\(.*?\)", "", j1_brut).strip()
                    else:
                        j1_nom = j1_brut

                    # Joueur 2
                    j2_brut = cols[5].get_text(strip=True)
                    j2_classement = ""
                    match_c2 = re.search(r"\((.*?)\)", j2_brut)
                    if match_c2:
                        j2_classement = match_c2.group(1)
                        j2_nom = re.sub(r"\(.*?\)", "", j2_brut).strip()
                    else:
                        j2_nom = j2_brut

                    # Sets
                    sets_j1 = int(cols[-2].get_text(strip=True))
                    sets_j2 = int(cols[-1].get_text(strip=True))

                    matchs_individuels.append(
                        {
                            "numero_match": ordre,
                            "joueur_1": {"nom": j1_nom, "classement": j1_classement or "Non spécifié"},
                            "joueur_2": {"nom": j2_nom, "classement": j2_classement or "Non spécifié"},
                            "sets_joueur_1": sets_j1,
                            "sets_joueur_2": sets_j2,
                        }
                    )
                except ValueError:
                    continue

    return {
        "annee": annee,
        "division": division,
        "semaine": semaine,
        "equipe_1": equipe1,
        "equipe_2": equipe2,
        "matchs": matchs_individuels,
    }
