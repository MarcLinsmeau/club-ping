# scraper.py
import re
import requests
from bs4 import BeautifulSoup


def scraper_match_table_tennis(url):
    """Télécharge une page de match FROTTBF via son URL et extrait

    toutes les données de manière reproductible.
    """
    # Simulateur de navigateur pour éviter le blocage par le serveur de la FROTTBF
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "fr,fr-FR;q=0.9,en;q=0.8",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {
                "erreur": f"Le site FROTTBF a répondu avec un code d'erreur : {response.status_code}",
                "matchs": [],
            }
    except Exception as e:
        return {
            "erreur": f"Impossible de se connecter au serveur FROTTBF : {str(e)}",
            "matchs": [],
        }

    soup = BeautifulSoup(response.content, "html.parser")

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
    annee = 2025  # Valeur par défaut
    input_date = soup.find("input", {"id": "matchdate"})
    if input_date and input_date.get("value"):
        match_annee = re.search(r"(\d{4})-\d{2}-\d{2}", input_date["value"])
        if match_annee:
            annee = int(match_annee.group(1))

    # --- 4. Extraction des Équipes ---
    equipe1, equipe2 = "", ""
    for h4 in soup.find_all("h4"):
        texte = h4.get_text(strip=True)
        if "Club Visité" in texte:
            nom_brut = texte.split(":")[-1].strip()
            equipe1 = re.sub(r"^\d+\s*-\s*", "", nom_brut)
        elif "Club Visiteur" in texte:
            nom_brut = texte.split(":")[-1].strip()
            equipe2 = re.sub(r"^\d+\s*-\s*", "", nom_brut)

    # --- 5. Cartographie des classements depuis les compositions ---
    dictionnaire_classements = {}
    inputs_joueurs = soup.find_all("input", {"id": re.compile(r"joueur\d+")})
    for inp in inputs_joueurs:
        valeur_joueur = inp.get("value", "")
        if valeur_joueur:
            match_infos = re.search(r"-\s*([^(]+)\s*\(([^)]+)\)", valeur_joueur)
            if match_infos:
                nom_complet = match_infos.group(1).strip()
                classement = match_infos.group(2).strip()
                dictionnaire_classements[nom_complet] = classement

    # --- 6. Extraction des 16 Matchs ---
    matchs_individuels = []
    table = soup.find("table")

    if table:
        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody else table.find_all("tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 8:
                try:
                    ordre = int(cols[0].get_text(strip=True))

                    # Extraction des noms (balises <span> dans votre HTML)
                    span_j1 = cols[1].find("span")
                    span_j2 = cols[5].find("span")

                    j1_nom = (
                        span_j1.get_text(strip=True)
                        if span_j1
                        else cols[1].get_text(strip=True)
                    )
                    j2_nom = (
                        span_j2.get_text(strip=True)
                        if span_j2
                        else cols[5].get_text(strip=True)
                    )

                    # Correspondance des classements
                    j1_classement = dictionnaire_classements.get(
                        j1_nom, "Non spécifié"
                    )
                    j2_classement = dictionnaire_classements.get(
                        j2_nom, "Non spécifié"
                    )

                    # Extraction des inputs de résultats (setresult)
                    input_set_j1 = cols[6].find("input")
                    input_set_j2 = cols[7].find("input")

                    sets_j1 = (
                        input_set_j1.get("value", "0") if input_set_j1 else "0"
                    )
                    sets_j2 = (
                        input_set_j2.get("value", "0") if input_set_j2 else "0"
                    )

                    # Conversion des scores de sets
                    sets_j1 = int(sets_j1) if sets_j1.isdigit() else sets_j1
                    sets_j2 = int(sets_j2) if sets_j2.isdigit() else sets_j2

                    matchs_individuels.append(
                        {
                            "numero_match": ordre,
                            "joueur_1": {"nom": j1_nom, "classement": j1_classement},
                            "joueur_2": {"nom": j2_nom, "classement": j2_classement},
                            "sets_joueur_1": sets_j1,
                            "sets_joueur_2": sets_j2,
                        }
                    )
                except Exception:
                    continue

    return {
        "annee": annee,
        "division": division,
        "semaine": semaine,
        "equipe_1": equipe1,
        "equipe_2": equipe2,
        "matchs": matchs_individuels,
    }
