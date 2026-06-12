# StatsEquipe.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur principal : TCD croisé (Semaine en lignes, Joueurs en colonnes)."""
    
    # --- ÉTAT DES SESSIONS & CALLBACKS DE FILTRES ---
    def reset_filtres(niveau):
        if niveau <= 1:
            st.session_state.clubs_choisis = []
        st.session_state.divisions_choisies = None

    for key, val in [("annee_choisie", None), ("clubs_choisis", []), ("divisions_choisies", None)]:
        if key not in st.session_state:
            st.session_state[key] = val

    # --- INTERFACE UTILISATEUR ---
    st.subheader("🔍 Filtres de sélection (Multi-choix tactiles)")
    
    st.write("**📅 1. Sélectionnez l'Année :**")
    st.segmented_control(
        "Année", options=utils.charger_annees(conn), key="annee_choisie", 
        selection_mode="single", on_change=reset_filtres, args=(1,), label_visibility="collapsed"
    )

    if st.session_state.annee_choisie:
        st.markdown("---")
        st.write("**🏢 2. Sélectionnez les Clubs :**")
        st.segmented_control(
            "Clubs", options=utils.charger_clubs_par_annee(conn, st.session_state.annee_choisie), 
            key="clubs_choisis", selection_mode="multi", on_change=reset_filtres, args=(2,), label_visibility="collapsed"
        )

    if st.session_state.annee_choisie and st.session_state.clubs_choisis:
        st.markdown("---")
        st.write("**🏆 3. Sélectionnez une Division :**")
        # Sélection unique forcée
        st.segmented_control(
            "Divisions", options=utils.charger_equipes_complet(conn, st.session_state.annee_choisie, st.session_state.clubs_choisis), 
            key="divisions_choisies", selection_mode="single", label_visibility="collapsed"
        )

    # --- REQUÊTAGE ET TCD ---
    st.markdown("---")
    if not st.session_state.annee_choisie or not st.session_state.clubs_choisis:
        st.info("💡 Veuillez sélectionner une Année et au moins un Club.")
    elif not st.session_state.divisions_choisies:
        st.info("💡 Veuillez sélectionner une Division pour afficher les données.")
    else:
        req = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie).in_("Equipe1", st.session_state.clubs_choisis)
        
        # Filtre sur une seule division
        req = req.eq("Division", st.session_state.divisions_choisies)

        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé pour ces critères.")
        else:
            # Création du TCD : Semaine (lignes) / Joueur1 (colonnes)
            df_pivot = df_res.pivot_table(
                index="Semaine",
                columns="Joueur1",
                values="VictoireJ1",
                aggfunc="sum",
                fill_value=0
            )

            # Tri des semaines
            df_pivot = df_pivot.sort_index(key=lambda x: x.map(utils.parse_semaine))

            st.subheader(f"📋 Comparatif hebdomadaire - {st.session_state.divisions_choisies} ({len(df_res)} match(s))")
            
            # Affichage HTML avec alignement forcé
            html_table = (
                df_pivot.style.format("{:.0f}")
                .background_gradient(cmap="Blues", axis=None)
                .set_table_styles([
                    {
                        "selector": "th, td, th.row_heading, th.col_heading, td.data", 
                        "props": [
                            ("vertical-align", "top !important"), 
                            ("text-align", "left !important"), 
                            ("border", "1px solid #555555 !important"), 
                            ("padding", "8px !important")
                        ]
                    }
                ], overwrite=False)
                .to_html(escape=False)
            )
            st.write(html_table, unsafe_allow_html=True)
