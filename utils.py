# utils.py
import re
import streamlit as st

# --- FONCTIONS DE DONNÉES COPIÉES DE VOTRE CODE ---

def charger_annees(conn):
  @st.cache_data(ttl=300)
    #"""Récupère la liste de toutes les années uniques disponibles en base."""
    res = conn.client.rpc("obtenir_annees_uniques").execute()
    return [str(row["annee"]) for row in (res.data or [])]

def charger_clubs(conn):
  @st.cache_data(ttl=300)
    #"""Récupère la liste de tous les club uniques disponibles en base."""
    res = conn.client.rpc("obtenir_clubs_uniques").execute()
    return [row["club"] for row in (res.data or [])]

def charger_clubs(conn, annee):
  @st.cache_data(ttl=300)
    #"""Récupère les clubs ayant participé à une année spécifique."""
    res = conn.client.rpc("obtenir_clubs_par_annee", {"annee_recherche": annee}).execute()
    return [row["club"] for row in (res.data or [])]

def charger_joueurs(conn, liste_clubs):
  @st.cache_data(ttl=300)
    #"""Extrait et trie la liste des joueurs selon les clubs."""
    res = conn.table("test").select("Joueur1").in_("Equipe1", liste_clubs).execute()
    return sorted(list({row["Joueur1"] for row in (res.data or []) if row.get("Joueur1")}))

def charger_joueurs(conn, annee, liste_clubs):
  @st.cache_data(ttl=300)
    #"""Extrait et trie la liste des joueurs selon l'année et les clubs."""
    res = conn.table("test").select("Joueur1").eq("Annee", annee).in_("Equipe1", liste_clubs).execute()
    return sorted(list({row["Joueur1"] for row in (res.data or []) if row.get("Joueur1")}))

def parse_semaine(val):
    #"""Extrait le numéro de semaine pour le tri chronologique."""
    digits = re.findall(r'\d+', str(val))
    return int(digits[0]) if digits else (-1 if val == "" else 0)
