# scraper.py
import re
import requests
from bs4 import BeautifulSoup


def scraper_match_table_tennis(url):
    """Télécharge une page de match FROTTBF via son URL et extrait

    toutes les données de manière reproductible (y compris le score global).
    """
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
    annee = None
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

    # --- 6. Extraction des Matchs et du Score Global ---
    matchs_individuels = []
    score_global_equipe_1 = 0
    score_global_equipe_2 = 0
    
    table = soup.find("table")

    if table:
        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody else table.find_all("tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 8:
                # Véritable ligne de match individuel (commence par un numéro de 1 à 16)
                texte_ordre = cols[0].get_text(strip=True)
                if texte_ordre.isdigit():
                    try:
                        ordre = int(texte_ordre)

                        span_j1 = cols[1].find("span")
                        span_j2 = cols[5].find("span")

                        j1_nom = span_j1.get_text(strip=True) if span_j1 else cols[1].get_text(strip=True)
                        j2_nom = span_j2.get_text(strip=True) if span_j2 else cols[5].get_text(strip=True)

                        j1_classement = dictionnaire_classements.get(j1_nom, "Non spécifié")
                        j2_classement = dictionnaire_classements.get(j2_nom, "Non spécifié")

                        input_set_j1 = cols[6].find("input")
                        input_set_j2 = cols[7].find("input")

                        sets_j1 = input_set_j1.get("value", "0") if input_set_j1 else "0"
                        sets_j2 = input_set_j2.get("value", "0") if input_set_j2 else "0"

                        sets_j1 = int(sets_j1) if sets_j1.isdigit() else sets_j1
                        sets_j2 = int(sets_j2) if sets_j2.isdigit() else sets_j2

                        matchs_individuels.append({
                            "numero_match": ordre,
                            "joueur_1": {"nom": j1_nom, "classement": j1_classement},
                            "joueur_2": {"nom": j2_nom, "classement": j2_classement},
                            "sets_joueur_1": sets_j1,
                            "sets_joueur_2": sets_j2,
                        })
                    except Exception:
                        continue
                
                # Cas particulier : détection de la ligne de total (ex: "Résultat : 9 7")
                elif "résultat" in texte_ordre.lower() or "total" in texte_ordre.lower():
                    try:
                        # Les scores finaux se trouvent dans les mêmes colonnes d'input (indices 6 et 7)
                        inp_res1 = cols[6].find("input")
                        inp_res2 = cols[7].find("input")
                        
                        if inp_res1 and inp_res2:
                            score_global_equipe_1 = int(inp_res1.get("value", "0"))
                            score_global_equipe_2 = int(inp_res2.get("value", "0"))
                    except Exception:
                        pass

        # Sécurité : Si le score global est resté à 0-0 (ex: ligne de total absente ou structurée différemment),
        # on le calcule de manière robuste à partir des victoires de sets récoltées.
        if score_global_equipe_1 == 0 and score_global_equipe_2 == 0:
            for m in matchs_individuels:
                s1, s2 = m["sets_joueur_1"], m["sets_joueur_2"]
                if isinstance(s1, int) and isinstance(s2, int):
                    if s1 > s2:
                        score_global_equipe_1 += 1
                    elif s2 > s1:
                        score_global_equipe_2 += 1

    return {
        "annee": annee,
        "division": division,
        "semaine": semaine,
        "equipe_1": equipe1,
        "equipe_2": equipe2,
        "score_global_equipe_1": score_global_equipe_1,
        "score_global_equipe_2": score_global_equipe_2,
        "matchs": matchs_individuels,
    }


def lister_urls_matchs_division(url_division):
    """Scanne la page calendrier d'une division FROTTBF et extrait tous les

    liens de feuilles de match.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    urls_matchs = []

    try:
        response = requests.get(url_division, headers=headers, timeout=15)
        if response.status_code != 200:
            return []
    except Exception:
        return []

    soup = BeautifulSoup(response.content, "html.parser")

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "voirfeuille.php" in href:
            if href.startswith("voirfeuille.php") or href.startswith("/voirfeuille.php"):
                url_complete = "https://www.frottbf.org/" + href.lstrip("/")
            else:
                url_complete = href

            if url_complete not in urls_matchs:
                urls_matchs.append(url_complete)

    return urls_matchs
