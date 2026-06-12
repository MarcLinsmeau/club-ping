# app.py
import os
import sys
import streamlit as st

# --- SÉCURITÉ LINUX : CHEMINS DE RECHERCHE PYTHON ---
# Assure que le dossier courant contenant 'utils.py' est prioritaire lors de l'import
chemin_app = os.path.dirname(os.path.abspath(__file__))
if chemin_app not in sys.path:
    sys.path.insert(0, chemin_app)

import pandas as pd
import altair as alt
from st_supabase_connection import SupabaseConnection

# Importation de votre module de fonctions partagées
import utils 

# --- CONFIGURATION DE L'APPLICATION ---
mode = st.query_params.get("mode", "StatsJoueursSemaine")
st.set_page_config(page_title="Ping-Point", page_icon="🏓", layout="wide")
st.title(f"🏓 Recherche Avancée des Statistiques - {mode}")

try:
    # Connexion à l'instance Supabase via le gestionnaire natif
    conn = st.connection("supabase", type=SupabaseConnection)

    StatsJoueursSemaine.StatsJoueursSemaine(conn)
                
except Exception as e:
    st.error("Une erreur technique globale est survenue lors du chargement de la page.")
    st.exception(e)
