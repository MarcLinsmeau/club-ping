import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Ping Club", page_icon="🏓")
st.title("🏓 Statistiques de notre Club de Ping")

try:
    # 1. Connexion à Supabase
    conn = st.connection("supabase", type=SupabaseConnection)

    # 2. Récupération de toutes les données
    reponse = conn.table("test").select("*").execute()
    df = pd.DataFrame(reponse.data)

    # --- ZONE DE FILTRE ---
    st.subheader("🔍 Filtrer les statistiques")

    # On crée une liste propre avec "Tous les joueurs" + le nom de chaque joueur unique
    liste_joueurs = ["Tous les joueurs"] + sorted(list(df["Joueur1"].unique()))
    
    # On affiche la liste déroulante (le filtre)
    joueur_selectionne = st.selectbox("Sélectionnez un joueur :", liste_joueurs)

    # On applique le filtre sur le tableau selon le choix de l'utilisateur
    if joueur_selectionne != "Tous les joueurs":
        # On ne garde que la ligne où le champ 'joueur' correspond au choix
        df_filtre = df[df["Joueur1"] == joueur_selectionne]
    else:
        # Sinon, on garde tout le tableau
        df_filtre = df

    # --- AFFICHAGE ---
    st.subheader("🏆 Classement")
    # On affiche le tableau filtré
    st.dataframe(df_filtre, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Une erreur est survenue lors de la connexion.")
    st.exception(e)
