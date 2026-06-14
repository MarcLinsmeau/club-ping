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

url_test = "https://www.frottbf.org/voirfeuille.php?semaine=2&match=9908"

# Appel de la fonction
donnees_rencontre = scraper_match_table_tennis(url_test)

# Exemple d'utilisation du résultat (ici un affichage propre)
if "erreur" not in donnees_rencontre:
    print(f"--- {donnees_rencontre['equipe_1']} VS {donnees_rencontre['equipe_2']} ---")
    print(f"Saison : {donnees_rencontre['annee']} | Division : {donnees_rencontre['division']} | Semaine : {donnees_rencontre['semaine']}\n")
    
    # Affichage du premier match pour vérifier
    premier_match = donnees_rencontre["matchs"][0]
    print(f"Match n°{premier_match['numero_match']} :")
    print(f"  Joueur 1 : {premier_match['joueur_1']['nom']} ({premier_match['joueur_1']['classement']}) -> Sets : {premier_match['sets_joueur_1']}")
    print(f"  Joueur 2 : {premier_match['joueur_2']['nom']} ({premier_match['joueur_2']['classement']}) -> Sets : {premier_match['sets_joueur_2']}")
else:
    print(donnees_rencontre["erreur"])

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
