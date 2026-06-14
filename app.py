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

# Définition des modes disponibles
modes_disponibles = {
    "StatsJoueursSemaine": "Stats Joueurs Hebdo",
    "StatsJoueursAnnee": "Stats Joueurs Année",
    "StatsJoueursAdversaire": "Stats Joueurs vs Adversaire",
    "StatsEquipe": "Stats Équipe"
}

# --- NAVIGATION VIA SIDEBAR ---
st.sidebar.title("Navigation")
mode_courant = st.query_params.get("mode", "StatsJoueursSemaine")

# Sélection du mode
nouveau_mode = st.sidebar.selectbox(
    "Choisir une vue :",
    options=list(modes_disponibles.keys()),
    format_func=lambda x: modes_disponibles[x],
    index=list(modes_disponibles.keys()).index(mode_courant) if mode_courant in modes_disponibles else 0
)

# Mise à jour de l'URL si le mode change
if nouveau_mode != mode_courant:
    st.query_params["mode"] = nouveau_mode
    st.rerun()

st.title(f"🏓 {modes_disponibles.get(nouveau_mode, 'Recherche')}")

try:
    # Initialisation unique de la connexion
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- ROUTAGE ET AIGUILLAGE DES SOUS-APPS ---
    if nouveau_mode == "StatsJoueursSemaine":
        from StatsJoueursSemaine import execution_app
        execution_app(conn)
        
    elif nouveau_mode == "StatsJoueursAnnee":
        from StatsJoueursAnnee import execution_app
        execution_app(conn)
    
    elif nouveau_mode == "StatsJoueursAdversaire":
        from StatsJoueursAdversaire import execution_app
        execution_app(conn)

    elif nouveau_mode == "StatsEquipe":
        # Ici, vous pouvez ajouter le paramètre optionnel si nécessaire
        from StatsEquipe import execution_app
        execution_app(conn)  
    
    else:
        st.error(f"Le mode demandé '{nouveau_mode}' est introuvable.")

except Exception as e:
    st.error("Une erreur technique globale est survenue.")
    st.exception(e)
