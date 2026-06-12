# StatsEquipe.py
import streamlit as st
import pandas as pd
import utils

def execution_app(conn):
    """Conteneur principal : TCD croisé (Semaine en lignes, Joueurs en colonnes)."""
    
    # ... (Gardez la gestion des sessions et des filtres identique) ...

    # --- REQUÊTAGE ET TCD ---
    st.markdown("---")
    if not st.session_state.annee_choisie or not st.session_state.clubs_choisis:
        st.info("💡 Veuillez sélectionner une Année et au moins un Club.")
    else:
        req = conn.table("test").select("*").eq("Annee", st.session_state.annee_choisie).in_("Equipe1", st.session_state.clubs_choisis)
        if st.session_state.divisions_choisies:
            req = req.in_("Division", st.session_state.divisions_choisies)

        df_res = pd.DataFrame(req.limit(50000).execute().data)

        if df_res.empty:
            st.warning("⚠️ Aucun record trouvé.")
        else:
            # Création du TCD : 
            # Index = Semaine (lignes)
            # Columns = Joueur1 (colonnes)
            # Values = Taux de Victoire
            
            # Calcul préalable pour avoir la donnée par joueur/semaine
            df_pivot = df_res.pivot_table(
                index="Semaine",
                columns="Joueur1",
                values="VictoireJ1",
                aggfunc="sum"
            )

            # Optionnel : Calculer le pourcentage si nécessaire
            # tcd_final = (df_pivot.div(total_matchs_par_joueur_semaine) * 100)

            st.subheader(f"📋 Comparatif hebdomadaire par joueur ({len(df_res)} match(s))")
            
            # Affichage HTML avec alignement forcé
            html_table = (
                df_pivot.style.format("{:.0f}") # Formatage simple pour les victoires
                .background_gradient(cmap="Blues", axis=0)
                .set_table_styles([
                    {
                        "selector": "th, td", 
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
