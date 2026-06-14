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

# app.py
from ScrapPage import scraper_match_table_tennis
import streamlit as st

url_cible = "https://www.frottbf.org/voirfeuille.php?semaine=2&match=9908"

resultat = scraper_match_table_tennis(url_cible)

if "erreur" in resultat:
    st.error(f"Erreur de scraping : {resultat['erreur']}")
elif not resultat["matchs"]:
    st.warning(
        "La page a été chargée mais aucun match n'a pu être extrait. Le site bloque peut-être la requête."
    )
else:
    st.success(f"Match : {resultat['equipe_1']} vs {resultat['equipe_2']}")

    # On ne demande le match 0 QUE si la liste n'est pas vide
    m1 = resultat["matchs"][0]
    st.write(
        f"Match 1 : {m1['joueur_1']['nom']} vs {m1['joueur_2']['nom']} ({m1['sets_joueur_1']}-{m1['sets_joueur_2']})"
    )
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
