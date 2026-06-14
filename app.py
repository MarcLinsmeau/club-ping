# app.py
import os
import sys
import streamlit as st

# --- SÉCURITÉ LINUX : CHEMINS DE RECHERCHE PYTHON ---
chemin_app = os.path.dirname(os.path.abspath(__file__))
if chemin_app not in sys.path:
    sys.path.insert(0, chemin_app)

from st_supabase_connection import SupabaseConnection

# --- CONFIGURATION DE L'APPLICATION ---
st.set_page_config(page_title="Ping-Point - Recherche", page_icon="🏓", layout="wide")

# Détection dynamique de l'application cible via les paramètres d'URL
# Par défaut, si aucun mode n'est spécifié, on charge "StatsJoueursSemaine"
mode = st.query_params.get("mode", "StatsJoueursSemaine")
st.title(f"🏓 Recherche Avancée des Statistiques - {mode}")

# On importe la fonction spécifique depuis le fichier scraper.py
from ScrapPage import scraper_match_table_tennis

# L'URL reçue par votre application
url_cible = "https://www.frottbf.org/voirfeuille.php?semaine=2&match=9908"

# Appel de la fonction externe
resultat = scraper_match_table_tennis(url_cible)

# Utilisation des données dans votre application
if "erreur" not in resultat:
    print(f"Données récupérées pour la division : {resultat['division']}")
    print(f"Match : {resultat['equipe_1']} vs {resultat['equipe_2']}")
    print(f"Nombre de matchs individuels extraits : {len(resultat['matchs'])}")
    
    # Exemple pour voir le premier match
    print("\nFocus sur le Match 1 :")
    m1 = resultat['matchs'][0]
    print(f"{m1['joueur_1']['nom']} vs {m1['joueur_2']['nom']} -> Score : {m1['sets_joueur_1']}-{m1['sets_joueur_2']}")
else:
    print(f"Une erreur est survenue : {resultat['erreur']}")

try:
    # Initialisation unique de la connexion pour tout l'écosystème d'applications
    conn = st.connection("supabase", type=SupabaseConnection)

   # --- ROUTAGE ET AIGUILLAGE DES SOUS-APPS ---
    if mode == "StatsJoueursSemaine":
        from StatsJoueursSemaine import execution_app
        execution_app(conn)
        
    elif mode == "StatsJoueursAnnee":
        from StatsJoueursAnnee import execution_app
        execution_app(conn)
    
    elif mode == "StatsJoueursAdversaire":
        from StatsJoueursAdversaire import execution_app
        execution_app(conn)

    elif mode == "StatsEquipe":
        from StatsEquipe import execution_app
        execution_app(conn)  
    
    else:
        st.error(f"Le mode demandé '{mode}' est introuvable ou non configuré.")

except Exception as e:
    st.error("Une erreur technique globale est survenue lors du chargement de la page.")
    st.exception(e)
