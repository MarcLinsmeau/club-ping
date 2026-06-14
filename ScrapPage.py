# Exemple de modification pour la boucle d'affichage dans app.py
recap_rencontres = []
for renc in tous_les_matchs_scrapes:
    eq1_nom = renc.get("equipe_1", "Inconnue")
    eq2_nom = renc.get("equipe_2", "Inconnue")

    # Si l'équipe est forfait, on ajoute une mention claire à côté de son nom
    if renc.get("forfait_equipe_1"):
        eq1_nom += " (FORFAIT)"
    if renc.get("forfait_equipe_2"):
        eq2_nom += " (FORFAIT)"

    recap_rencontres.append(
        {
            "Semaine": f"Semaine {renc.get('semaine', '?')}",
            "Équipe Visité": eq1_nom,
            "Score Global": f"{renc.get('score_global_equipe_1', 0)} - {renc.get('score_global_equipe_2', 0)}",
            "Équipe Visiteur": eq2_nom,
        }
    )
