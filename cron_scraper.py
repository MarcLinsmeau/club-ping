# cron_scraper.py
from scraper import lister_urls_matchs_division, scraper_match_table_tennis

def execution_automatique():
    print("🚀 Démarrage du scraper automatique...")
    url_division = "https://www.frottbf.org/resultat.php?division=140"
    
    # 1. Récupération de tous les liens
    liens = lister_urls_matchs_division(url_division)
    print(f"📋 {len(liens)} matchs trouvés au calendrier.")
    
    # 2. Boucle d'extraction
    tous_les_matchs = []
    for index, lien in enumerate(liens):
        donnees = scraper_match_table_tennis(lien)
        if "erreur" not in donnees:
            print(f"[{index+1}/{len(liens)}] Match extrait : {donnees['equipe_1']} vs {donnees['equipe_2']}")
            tous_les_matchs.append(donnees)
            
    # 3. Destination Base de données
    print(f"💾 Fin du traitement. {len(tous_les_matchs)} matchs prêts pour la DB.")
    # C'est ici qu'on ajoutera les 3 lignes pour envoyer 'tous_les_matchs' vers votre DB.

if __name__ == "__main__":
    execution_automatique()
