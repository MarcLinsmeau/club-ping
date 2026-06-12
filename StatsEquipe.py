# StatsEquipe.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur : Semaine, Equipe2 en index, Joueurs en colonnes."""
    
    # --- ÉTAT DES SESSIONS ---
    for key, val in [("annee_choisie", None), ("club_choisi", None), ("division_choisie", None)]:
        if key not in st.session_state: st.session_state[key] = val

    def reset_suivant(niveau):
        if niveau <= 1: st.session_state.club_choisi = None
        if niveau <= 2: st.session_state.division_choisie = None

    # --- INTERFACE ---
    st.subheader("🔍 Filtres de sélection")
    st.segmented_control("Année", options=utils.charger_annees(conn), key="annee_choisie", selection_mode="single", on_change=reset_suivant, args=(1,), label_visibility="collapsed")
    if st.session_state.annee_choisie:
        st.segmented_control("Club", options=utils.charger_clubs_par_annee(conn, st.session_state.annee_choisie), key="club_choisi", selection_mode="single", on_change=reset_suivant, args=(2,), label_visibility="collapsed")
    if st.session_state.annee_choisie and st.session_state.club_choisi:
        st.segmented_control("Division", options=utils.charger_equipes_complet(conn, st.session_state.annee_choisie, [st.session_state.club_choisi]), key="division_choisie", selection_mode="single", label_visibility="collapsed")

    # --- REQUÊTAGE ET TCD ---
    if not (st.session_state.annee_choisie and st.session_state.club_choisi and st.session_state.division_choisie):
        st.info("💡 Veuillez sélectionner une Année, un Club et une Division.")
    else:
        req = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie).eq("Equipe1", st.session_state.club_choisi).eq("Division", st.session_state.division_choisie)
        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé.")
        else:
            # 1. Calcul agrégé (Equipe1 retiré de l'index)
