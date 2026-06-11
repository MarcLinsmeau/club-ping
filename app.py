# --- SECTION TABLEAU CROISÉ DYNAMIQUE (TCD) : SÉLECTIONS & MATCHS ---
            st.markdown("---")
            st.header("📊 Tableau Croisé Dynamique : Bilan des Joueurs")
            st.write("Ce tableau récapitule le nombre de sélections (lignes), de matchs joués et de matchs gagnés.")

            # On vérifie que les colonnes nécessaires existent bien dans le DataFrame
            colonnes_requises = ["MatchNonFF", "Match Joué", "VictoireJ1"]
            if all(col in df_resultat.columns for col in colonnes_requises):
                
                # Construction du TCD avec un dictionnaire de fonctions d'agrégation (aggfunc)
                tcd_bilan = df_resultat.pivot_table(
                    index=["Equipe1", "Joueur1", "ClassementJ1", "Division", "Semaine"], 
                    values=["MatchNonFF", "Match Joué", "VictoireJ1"],
                    aggfunc={
                        "MatchNonFF": "size",   # 'size' compte le nombre de lignes (le nombre de sélections)
                        "Match Joué": "sum",    # 'sum' fait la somme des matchs réellement joués
                        "VictoireJ1": "sum"     # 'sum' fait la somme des victoires
                    },
                    fill_value=0
                )

                # Réorganisation des colonnes pour une lecture naturelle
                tcd_bilan = tcd_bilan[["MatchNonFF", "Match Joué", "VictoireJ1"]]
                
                # Renommer proprement les en-têtes de colonnes
                tcd_bilan.columns = ["Sélections (Taille)", "Matchs Joués (Somme)", "Matchs Gagnés (Somme)"]

                # Affichage final de la matrice de performance
                if not tcd_bilan.empty:
                    st.subheader("📋 Tableau de synthèse des performances")
                    st.dataframe(
                        tcd_bilan.style.background_gradient(cmap="YlGnBu", axis=0), 
                        use_container_width=True
                    )
                else:
                    st.info("Données insuffisantes pour générer ce tableau croisé.")
            else:
                st.error("Une ou plusieurs colonnes de calcul ('MatchNonFF', 'Match Joué', 'VictoireJ1') sont introuvables.")
