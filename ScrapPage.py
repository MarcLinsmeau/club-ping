# scraper.py
import re
from bs4 import BeautifulSoup


def scraper_match_table_tennis_html(html_content):
    """Analyse le contenu HTML brut d'une feuille de match FROTTBF et en extrait

    toutes les informations requises de manière reproductible.
    """
    soup = BeautifulSoup(html_content, "html.parser")

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

    # --- 5. Cartographie des joueurs et de leurs classements ---
    # On crée un dictionnaire pour lier les noms des joueurs à leurs classements
    # car le grand tableau du bas contient uniquement les noms de famille et prénoms.
    dictionnaire_classements = {}

    # Parcourir tous les inputs de type texte contenant les fiches des joueurs
    inputs_joueurs = soup.find_all("input", {"id": re.compile(r"joueur\d+")})
    for inp in inputs_joueurs:
        valeur_joueur = inp.get("value", "")  # Ex: "24986 - GRANDJEAN Virginie (E1)"
        if valeur_joueur:
            # Extraction du Nom Prénom et du Classement
            match_infos = re.search(r"-\s*([^(]+)\s*\(([^)]+)\)", valeur_joueur)
            if match_infos:
                nom_complet = match_infos.group(1).strip()  # GRANDJEAN Virginie
                classement = match_infos.group(2).strip()  # E1
                dictionnaire_classements[nom_complet] = classement

    # --- 6. Extraction des Matchs depuis le Tableau ---
    matchs_individuels = []
    table = soup.find("table")

    if table:
        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody else table.find_all("tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 8:
                try:
                    # Numéro d'ordre du match
                    ordre = int(cols[0].get_text(strip=True))

                    # Extraction des noms de joueurs (balises <span>)
                    j1_nom = cols[1].find("span").get_text(strip=True)
                    j2_nom = cols[5].find("span").get_text(strip=True)

                    # Récupération des classements associés via notre dictionnaire créé à l'étape 5
                    j1_classement = dictionnaire_classements.get(j1_nom, "Non spécifié")
                    j2_classement = dictionnaire_classements.get(j2_nom, "Non spécifié")

                    # Extraction des sets gagnés dans les attributs 'value' des inputs
                    input_set_j1 = cols[6].find("input")
                    input_set_j2 = cols[7].find("input")

                    sets_j1 = input_set_j1.get("value", "0") if input_set_j1 else "0"
                    sets_j2 = input_set_j2.get("value", "0") if input_set_j2 else "0"

                    # Conversion sécurisée en entier (gestion du cas "WO")
                    sets_j1 = int(sets_j1) if sets_j1.isdigit() else sets_j1
                    sets_j2 = int(sets_j2) if sets_j2.isdigit() else sets_j2

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
                except (ValueError, IndexError, AttributeError):
                    continue

    return {
        "annee": annee,
        "division": division,
        "semaine": semaine,
        "equipe_1": equipe1,
        "equipe_2": equipe2,
        "matchs": matchs_individuels
    }
