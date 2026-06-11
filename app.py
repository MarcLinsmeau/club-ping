import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Ping Club", page_icon="🏓")
st.title("🏓 Statistiques de notre Club de Ping")

try:
    # Connexion à ta base Supabase (va lire les Secrets de l'Étape 4)
    conn = st.connection("supabase", type=SupabaseConnection)

    # Récupération des données
    reponse = conn.table("stats_ping").select("*").execute()
    df = pd.DataFrame(reponse.data)

    # Affichage du tableau
    st.subheader("🏆 Classement Général")
    st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Connexion en cours... Configure les Secrets sur Streamlit (Étape 4).")
