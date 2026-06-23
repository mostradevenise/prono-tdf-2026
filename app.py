import streamlit as st
import json
import os
import pandas as pd
import re
import unicodedata

# --- ⚙️ CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Prono Tour de France", page_icon="🚴‍♂️", layout="wide")

FICHIER_PRONOS = "pronostics.json"
FICHIER_USERS = "utilisateurs.json"
FICHIER_COTES = "cotes.json"
FICHIER_PROFILS = "profils.json" # NOUVEAU FICHIER
LIMITE_JOUEURS = 10

# --- 📅 BASE DE DONNÉES DES ÉTAPES ---
INFO_ETAPES = {
    "Classement Général": "Fin du Tour",
    "Étape 1": "Sam. 4 Juillet",
    "Étape 2": "Dim. 5 Juillet",
    "Étape 3": "Lun. 6 Juillet",
    "Étape 4": "Mar. 7 Juillet",
    "Étape 5": "Mer. 8 Juillet",
    "Étape 6": "Jeu. 9 Juillet",
    "Étape 7": "Ven. 10 Juillet",
    "Étape 8": "Sam. 11 Juillet",
    "Étape 9": "Dim. 12 Juillet",
    "Étape 10": "Mar. 14 Juillet",
    "Étape 11": "Mer. 15 Juillet",
    "Étape 12": "Jeu. 16 Juillet",
    "Étape 13": "Ven. 17 Juillet",
    "Étape 14": "Sam. 18 Juillet",
    "Étape 15": "Dim. 19 Juillet",
    "Étape 16": "Mar. 21 Juillet",
    "Étape 17": "Mer. 22 Juillet",
    "Étape 18": "Jeu. 23 Juillet",
    "Étape 19": "Ven. 24 Juillet",
    "Étape 20": "Sam. 25 Juillet",
    "Étape 21": "Dim. 26 Juillet"
}

# --- 🚴‍♂️ CHARGEMENT DES COUREURS ---
@st.cache_data
def charger_coureurs():
    if os.path.exists("coureurs.csv"):
        df = pd.read_csv("coureurs.csv")
        dict_liens = dict(zip(df["Nom"], df["Lien"]))
        return df["Nom"].tolist(), dict_liens
    return ["--- Sélectionner un coureur ---"], {}

COUREURS, LIENS_COUREURS = charger_coureurs()

# --- 💾 FONCTIONS UTILITAIRES ---
def charger_json(fichier, defaut=None):
    if os.path.exists(fichier):
        with open(fichier, "r", encoding="utf-8") as f:
            return json.load(f)
    return defaut if defaut is not None else {}

def sauvegarder_json(fichier, donnees):
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(donnees, f, indent=4, ensure_ascii=False)

def simplifier_texte(texte):
    texte = unicodedata.normalize('NFKD', texte).encode('ASCII', 'ignore').decode('utf-8').lower()
    return re.sub(r'[^a-z0-9\s]', '', texte)

def trouver_vrai_nom(nom_wina, coureurs_pcs):
    nom_wina_sim = simplifier_texte(nom_wina)
    mots_wina = set(nom_wina_sim.split())
    meilleur_match = nom_wina
    meilleur_score = 0
    
    for coureur in coureurs_pcs:
        if coureur == "--- Sélectionner un coureur ---": continue
        nom_pcs_sim = simplifier_texte(coureur)
        if nom_pcs_sim == nom_wina_sim: return coureur
        
        mots_pcs = set(nom_pcs_sim.split())
        mots_communs = mots_wina.intersection(mots_pcs)
        score = len(mots_communs)
        if score > meilleur_score and score >= 1:
            meilleur_score = score
            meilleur_match = coureur
    return meilleur_match

# --- 🔐 INITIALISATION ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# --- 🏠 ACCUEIL ---
def ecran_accueil():
    st.title("🚴‍♂️ Prono Tour de France")
    users_db = charger_json(FICHIER_USERS, {"admin": "admin"})
    onglet_connexion, onglet_inscription = st.tabs(["Se connecter", "S'inscrire"])
    
    with onglet_connexion:
        username = st.text_input("Identifiant", key="log_user")
        password = st.text_input("Mot de passe", type="password", key="log_pass")
        if st.button("Se connecter"):
            if username in users_db and users_db[username] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect.")
                
    with onglet_inscription:
        new_user = st.text_input("Choisis un Identifiant", key="reg_user")
        new_pass = st.text_input("Choisis un Mot de passe", type="password", key="reg_pass")
        if st.button("Créer mon compte"):
            nombre_joueurs_actuels = len(users_db) - 1 if "admin" in users_db else len(users_db)
            if new_user in users_db:
                st.error("Cet identifiant est déjà pris.")
            elif len(new_user) < 3 or len(new_pass) < 3:
                st.error("Identifiant et mot de passe > 3 caractères.")
            elif nombre_joueurs_actuels >= LIMITE_JOUEURS:
                st.error("Le jeu est complet ! (10/10)")
            else:
                users_db[new_user] = new_pass
                sauvegarder_json(FICHIER_USERS, users_db)
                st.success("Compte créé avec succès !")

# --- 🛠️ ESPACE ADMINISTRATEUR ---
def espace_admin():
    st.title("🛠️ Espace Administrateur")
    
    cible_selectionnee = st.selectbox("Pour quelle course ajouter des cotes ?", list(INFO_ETAPES.keys()))
    
    st.info(f"Colle le texte Winamax pour : **{cible_selectionnee}**")
    texte_brut = st.text_area("Texte Winamax", height=300)
    
    if st.button(f"Extraire pour {cible_selectionnee}"):
        lignes = [ligne.strip() for ligne in texte_brut.split('\n') if ligne.strip()]
        dico_cotes = {}
        cotes_trouvees = 0
        
        for i in range(len(lignes) - 1):
            nom_potentiel = lignes[i]
            cote_potentielle = lignes[i+1]
            if nom_potentiel.startswith("Étape") or nom_potentiel.endswith("%") or re.match(r'^[0-9]+[.,]?[0-9]*$', nom_potentiel):
                continue
            if re.match(r'^[0-9]+([.,][0-9]+)?$', cote_potentielle):
                cote_float = float(cote_potentielle.replace(',', '.'))
                if "," in nom_potentiel:
                    parts = nom_potentiel.split(",")
                    nom_propre = f"{parts[1].strip()} {parts[0].strip()}"
                else:
                    nom_propre = nom_potentiel
                
                nom_trouve = trouver_vrai_nom(nom_propre, COUREURS)
                dico_cotes[nom_trouve] = cote_float
                cotes_trouvees += 1
        
        if cotes_trouvees > 0:
            toutes_les_cotes = charger_json(FICHIER_COTES, {})
            toutes_les_cotes[cible_selectionnee] = dico_cotes
            sauvegarder_json(FICHIER_COTES, toutes_les_cotes)
            st.success(f"✅ {cotes_trouvees} cotes enregistrées !")
            st.json(dico_cotes)
        else:
            st.warning("Aucune cote trouvée.")

# --- 🎮 INTERFACE JOUEUR ---
def main_app():
    if st.session_state.username == "admin":
        if st.sidebar.button("Se déconnecter"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
        espace_admin()
        return

    # --- PANNEAU LATÉRAL ---
    st.sidebar.title(f"💛 Salut {st.session_state.username} !")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
        
    st.sidebar.divider()
    st.sidebar.header("🗺️ Étapes")
    
    options_radio = [f"{etape} ({date})" for etape, date in INFO_ETAPES.items()]
    choix_sidebar = st.sidebar.radio("Sélectionne ton étape :", options_radio)
    
    course_choisie = choix_sidebar.split(" (")[0]
    
    with st.sidebar.expander("📚 Chercher une fiche PCS"):
        recherche = st.selectbox("Coureur :", COUREURS, key="recherche_pcs", label_visibility="collapsed")
        if recherche != "--- Sélectionner un coureur ---" and LIENS_COUREURS.get(recherche, ""):
            st.link_button(f"📊 Voir la fiche", LIENS_COUREURS.get(recherche))

    # --- ZONE PRINCIPALE ---
    st.title(f"🏁 {course_choisie}")
    
    # Affichage instantané du profil depuis L'Équipe
    tous_les_profils = charger_json(FICHIER_PROFILS, {})
    url_profil = tous_les_profils.get(course_choisie, "")
    
    if url_profil:
        st.image(url_profil, use_container_width=True)
    elif course_choisie.startswith("Étape"):
        st.info("Le profil de cette étape n'a pas encore été récupéré (lance le script de scraping L'Équipe).")

    st.divider()
    st.subheader("Fais ton Top 10")

    toutes_les_cotes = charger_json(FICHIER_COTES, {})
    cotes_du_jour = toutes_les_cotes.get(course_choisie, {})
    tous_les_pronos = charger_json(FICHIER_PRONOS, {})
    user = st.session_state.username
    if user not in tous_les_pronos: tous_les_pronos[user] = {}
    prono_actuel = tous_les_pronos[user].get(course_choisie, ["--- Sélectionner un coureur ---"] * 10)

    options_formatees = ["--- Sélectionner un coureur ---"]
    mapping_inverse = {"--- Sélectionner un coureur ---": "--- Sélectionner un coureur ---"}
    
    coureurs_valides = [c for c in COUREURS if c != "--- Sélectionner un coureur ---"]
    coureurs_tries = sorted(coureurs_valides, key=lambda x: cotes_du_jour.get(x, 9999))

    for c in coureurs_tries:
        cote = cotes_du_jour.get(c)
        if cote:
            texte = f"{c} | Cote: {cote}"
        else:
            texte = c 
        options_formatees.append(texte)
        mapping_inverse[texte] = c

    with st.form("formulaire_prono"):
        col1, col2 = st.columns(2)
        nouveau_prono_noms_purs = []
        
        for i in range(10):
            col_actuelle = col1 if i < 5 else col2
            nom_pur_precedent = prono_actuel[i] if i < len(prono_actuel) else "--- Sélectionner un coureur ---"
            
            texte_defaut = "--- Sélectionner un coureur ---"
            for texte_formate, nom_pur in mapping_inverse.items():
                if nom_pur == nom_pur_precedent:
                    texte_defaut = texte_formate
                    break
                    
            index_defaut = options_formatees.index(texte_defaut) if texte_defaut in options_formatees else 0
            
            with col_actuelle:
                choix_formate = st.selectbox(f"🏆 Position {i+1}", options=options_formatees, index=index_defaut, key=f"pos_{i}")
                nouveau_prono_noms_purs.append(mapping_inverse[choix_formate])
        
        st.write("") 
        soumis = st.form_submit_button("Sauvegarder ce Top 10", use_container_width=True)
        
        if soumis:
            vrais_choix = [c for c in nouveau_prono_noms_purs if c != "--- Sélectionner un coureur ---"]
            if len(vrais_choix) != len(set(vrais_choix)):
                st.error("⚠️ Erreur : Tu as sélectionné plusieurs fois le même coureur !")
            elif len(vrais_choix) != 10:
                st.warning(f"Tu n'as sélectionné que {len(vrais_choix)} coureurs sur 10. (C'est enregistré, mais n'oublie pas de compléter !)")
                tous_les_pronos[user][course_choisie] = nouveau_prono_noms_purs
                sauvegarder_json(FICHIER_PRONOS, tous_les_pronos)
            else:
                tous_les_pronos[user][course_choisie] = nouveau_prono_noms_purs
                sauvegarder_json(FICHIER_PRONOS, tous_les_pronos)
                st.success(f"✅ Ton pronostic complet est enregistré !")
                st.balloons()

if not st.session_state.logged_in:
    ecran_accueil()
else:
    main_app()
