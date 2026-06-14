import re
import requests
from bs4 import BeautifulSoup


def scraper_match_table_tennis(url):
    """Extrait les données d'une feuille de match de tennis de table FROTTBF à partir de son URL.

    :param url: (str) L'URL de la page du match.
    :return: (dict) Un dictionnaire contenant l'année, la division, la semaine,
             les équipes et la liste des 16 matchs individuels.
    """
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

    # 1. Extraction de la Division
    h1_text = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
    division = h1_text.replace("Rencontre de division", "").strip()

    # 2. Extraction de la Semaine
    semaine = ""
    semaine_text = soup.find(string=re.compile(r"Semaine\s+\d+"))
    if semaine_text:
        match_semaine = re.search(r"Semaine\s+(\d+)", semaine_text)
        if match_semaine:
            semaine = int(match_semaine.group(1))

    # 3. Extraction de l'Année (Depuis la date du match si disponible, sinon par défaut)
    annee = 2025  # Valeur par défaut demandée
    date_label = soup.find(string=re.compile(r"Date du match"))
    if date_label:
        # Souvent la date est dans le texte ou l'élément suivant
        parent_text = date_label.parent.get_text()
        match_annee = re.search(r"(\d{4})-\d{2}-\d{2}", parent_text)
        if match_annee:
            annee = int(match_annee.group(1))

    # 4. Extraction des Équipes (en enlevant les numéros de matricules)
    equipe1 = ""
    equipe2 = ""
    for h4 in soup.find_all("h4"):
        texte = h4.get_text(strip=True)
        if "Club Visité" in texte:
            nom_brut = texte.split(":")[-1].strip()
            equipe1 = re.sub(r"^\d+\s*-\s*", "", nom_brut)  # Retire "234 - "
        elif "Club Visiteur" in texte:
            nom_brut = texte.split(":")[-1].strip()
            equipe2 = re.sub(r"^\d+\s*-\s*", "", nom_brut)  # Retire "94 - "

    # 5. Extraction des 16 Matchs Individuels
    matchs_individuels = []
    table = soup.find("table")

    if table:
        # On parcourt toutes les lignes en ignorant la ligne d'en-tête (th)
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            # Une ligne de match valide sur la FROTTBF contient au moins 9 colonnes
            if len(cols) >= 9:
                try:
                    # Ordre / Numéro du match
                    ordre = int(cols[0].get_text(strip=True))

                    # --- JOUEUR 1 (Club Visité) ---
                    j1_brut = cols[1].get_text(strip=True)
                    # Extraction du classement entre parenthèses ex: "GRANDJEAN Virginie (E1)"
                    j1_classement = ""
                    match_c1 = re.search(r"\((.*?)\)", j1_brut)
                    if match_c1:
                        j1_classement = match_c1.group(1)
                        j1_nom = re.sub(r"\(.*?\)", "", j1_brut).strip()
                    else:
                        j1_nom = j1_brut

                    # --- JOUEUR 2 (Club Visiteur) ---
                    # Dans la structure de la table : cols[5] contient le nom du visiteur
                    j2_brut = cols[5].get_text(strip=True)
                    j2_classement = ""
                    match_c2 = re.search(r"\((.*?)\)", j2_brut)
                    if match_c2:
                        j2_classement = match_c2.group(1)
                        j2_nom = re.sub(r"\(.*?\)", "", j2_brut).strip()
                    else:
                        j2_nom = j2_brut

                    # --- SETS GAGNÉS ---
                    # Les deux dernières colonnes de la ligne contiennent les sets totaux
                    sets_j1 = int(cols[-2].get_text(strip=True))
                    sets_j2 = int(cols[-1].get_text(strip=True))

                    # Ajout du match à la liste
                    matchs_individuels.append(
                        {
                            "numero_match": ordre,
                            "joueur_1": {
                                "nom": j1_nom,
                                "classement": j1_classement
                                if j1_classement
                                else "Non spécifié",
                            },
                            "joueur_2": {
                                "nom": j2_nom,
                                "classement": j2_classement
                                if j2_classement
                                else "Non spécifié",
                            },
                            "sets_joueur_1": sets_j1,
                            "sets_joueur_2": sets_j2,
                        }
                    )
                except ValueError:
                    # Ignore les lignes qui ne contiennent pas de données numériques valides (ex: en-têtes secondaires)
                    continue

    # Retourne le dictionnaire final structuré
    return {
        "annee": annee,
        "division": division,
        "semaine": semaine,
        "equipe_1": equipe1,
        "equipe_2": equipe2,
        "matchs": matchs_individuels,
    }
