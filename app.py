# app.py
import streamlit as st
from ScrapPage import scraper_match_table_tennis

# Configuration de la page Streamlit
st.set_page_config(page_title="Scraper Tennis de Table FROTTBF", page_icon="🏓", layout="centered")

st.title("🏓 Extraction de Feuille de Match FROTTBF")
st.write("Entrez l'URL d'une feuille de match pour extraire instantanément toutes ses données.")

# Champ de saisie pour l'URL (avec l'URL exemple par défaut)
url_defaut = "https://www.frottbf.org/voirfeuille.php?semaine=2&match=9908"
url_saisie = st.text_input("URL de la feuille de match :", value=url_defaut)

if st.button("Analyser la rencontre", type="primary"):
    with st.spinner("Extraction des données en cours depuis le site de la FROTTBF..."):
        # Appel de la fonction située dans scraper.py
        donnees = scraper_match_table_tennis_html(url_saisie)
        
    # --- Gestion et affichage des résultats ---
    if "erreur" in donnees:
        st.error(donnees["erreur"])
        
    elif not donnees["matchs"]:
        st.warning("⚠️ La page a été contactée avec succès, mais aucun tableau de match n'a pu être trouvé. Vérifiez que l'URL est correcte.")
        
    else:
        st.success("🎉 Données extraites avec succès !")
        
        # Affichage des métadonnées globales
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Année / Saison", donnees["annee"])
        with col2:
            st.metric("Division", donnees["division"])
        with col3:
            st.metric("Semaine", donnees["semaine"])
            
        st.markdown("---")
        st.subheader(f"🏆 {donnees['equipe_1']} 🆚 {donnees['equipe_2']}")
        st.write(f"Nombre de matchs individuels détectés : **{len(donnees['matchs'])}**")
        
        # Affichage détaillé des 16 matchs individuels
        st.write("### 📊 Détails des matchs individuels")
        
        for m in donnees["matchs"]:
            # On crée un petit bandeau extensible (expander) pour chaque match individuel
            titre_match = f"Match {m['numero_match']} : {m['joueur_1']['nom']} vs {m['joueur_2']['nom']} ({m['sets_joueur_1']} - {m['sets_joueur_2']})"
            
            with st.expander(titre_match):
                c_j1, c_vs, c_j2 = st.columns([4, 2, 4])
                with c_j1:
                    st.markdown(f"**Joueur 1 (Visité) :** \n{m['joueur_1']['nom']}")
                    st.caption(f"Classement : {m['joueur_1']['classement']}")
                    st.markdown(f"Sets gagnés : `{m['sets_joueur_1']}`")
                with c_vs:
                    st.markdown("<h3 style='text-align: center; color: gray;'>VS</h3>", unsafe_allow_html=True)
                with c_j2:
                    st.markdown(f"**Joueur 2 (Visiteur) :** \n{m['joueur_2']['nom']}")
                    st.caption(f"Classement : {m['joueur_2']['classement']}")
                    st.markdown(f"Sets gagnés : `{m['sets_joueur_2']}`")
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
