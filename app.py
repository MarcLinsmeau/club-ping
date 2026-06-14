# app.py
import streamlit as st
from ScrapPage import scraper_match_table_tennis

# Config de la page
st.set_page_config(
    page_title="Scraper Tennis de Table FROTTBF", page_icon="🏓", layout="centered"
)

st.title("🏓 Extraction de Feuille de Match FROTTBF")
st.write(
    "Entrez l'URL d'une feuille de match pour extraire instantanément toutes ses données."
)

# Champ URL
url_defaut = "https://www.frottbf.org/voirfeuille.php?semaine=2&match=9908"
url_saisie = st.text_input("URL de la feuille de match :", value=url_defaut)

if st.button("Analyser la rencontre", type="primary"):
    with st.spinner("Connexion et extraction des données en cours..."):
        # On passe directement l'URL saisie à la fonction
        donnees = scraper_match_table_tennis(url_saisie)

    # Traitement des résultats
    if "erreur" in donnees:
        st.error(donnees["erreur"])

    elif not donnees["matchs"]:
        st.error(
            "⚠️ Aucun tableau de match n'a pu être trouvé. Le site bloque peut-être l'application ou l'URL est incorrecte."
        )

    else:
        st.success("🎉 Données extraites avec succès !")
        st.write(donnees)

        
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
