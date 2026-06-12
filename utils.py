# utils.py
import re
import streamlit as st

# --- FONCTIONS DE DONNÉES AVEC MISE EN CACHE ---

@st.cache_data(ttl=300)
def charger_annees(conn):
    """Récupère la liste de toutes les années uniques disponibles en base."""
    res = conn.client.rpc("obtenir_annees_uniques").execute()
    return [str(row["annee"]) for row in (res.data or [])]

@st.cache_data(ttl=300)
def charger_clubs_uniques(conn):
    """Récupère la liste de tous les clubs uniques (sans filtre d'année)."""
    res = conn.client.rpc("obtenir_clubs_uniques").execute()
    return [row["club"] for row in (res.data or [])]

@st.cache_data(ttl=300)
def charger_clubs_par_annee(conn, annee):
    """Récupère les clubs ayant participé à une année spécifique."""
    res = conn.client.rpc("obtenir_clubs_par_annee", {"annee_recherche": annee}).execute()
    return [row["club"] for row in (res.data or [])]

@st.cache_data(ttl=300)
def charger_joueurs_par_clubs(conn, liste_clubs):
    """Extrait et trie la liste des joueurs selon une liste de clubs."""
    res = conn.table("test").select("Joueur1").in_("Equipe1", liste_clubs).execute()
    return sorted(list({row["Joueur1"] for row in (res.data or []) if row.get("Joueur1")}))

@st.cache_data(ttl=300)
def charger_joueurs_complet(conn, annee, liste_clubs):
    """Extrait et trie la liste des joueurs selon l'année et les clubs."""
    res = conn.table("test").select("Joueur1").eq("Annee", annee).in_("Equipe1", liste_clubs).execute()
    return sorted(list({row["Joueur1"] for row in (res.data or []) if row.get("Joueur1")}))

# --- FONCTION UTILITAIRE DE PARSING ---

def parse_semaine(val):
    """Extrait le numéro de semaine pour le tri chronologique."""
    digits = re.findall(r'\d+', str(val))
    return int(digits[0]) if digits else (-1 if val == "" else 0)
