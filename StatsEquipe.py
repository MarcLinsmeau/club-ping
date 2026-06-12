# 1. Calcul agrégé
            df_g = df_res.groupby(["Semaine", "Joueur1"]).agg(
                Sélections=("MatchNonFF", "size"),
                Matchs_Joués=("Match", "size"),
                Victoires=("VictoireJ1", "sum"),
                Points=("PointsJ1", "sum")
            ).fillna(0)
            
            # 2. Récupération et TRI ALPHABÉTIQUE des joueurs
            joueurs = sorted(df_g.index.get_level_values("Joueur1").unique())
            
            df_list = []
            for joueur in joueurs:
                df_j = df_g.xs(joueur, level="Joueur1")[["Sélections", "Matchs_Joués", "Victoires", "Points"]]
                df_j.columns = pd.MultiIndex.from_product([[joueur], df_j.columns])
                df_list.append(df_j)
            
            # 3. Concaténation et tri de l'index (Semaines)
            df_pivot = pd.concat(df_list, axis=1).sort_index(key=lambda x: x.map(utils.parse_semaine))
