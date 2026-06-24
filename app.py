import streamlit as st
import json
import os
import pandas as pd
import re
import unicodedata
from datetime import datetime
import pytz
import difflib

# --- ⚙️ CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Prono Tour de France", page_icon="🚴‍♂️", layout="wide")

FICHIER_PRONOS = "pronostics.json"
FICHIER_USERS = "utilisateurs.json"
FICHIER_COTES = "cotes.json"
FICHIER_PROFILS = "profils.json"
FICHIER_HORAIRES = "horaires.json"
FICHIER_POINTS = "points.json"
FICHIER_RESULTATS = "resultats.json"
FICHIER_VERROUS = "verrous.json" 
LIMITE_JOUEURS = 10

NOM_COURSES = ["Étape Test", "Classement Général"] + [f"Étape {i}" for i in range(1, 22)]

# --- 🚴‍♂️ CHARGEMENT DES FICHIERS ---
@st.cache_data
def charger_coureurs():
    if os.path.exists("coureurs.csv"):
        df = pd.read_csv("coureurs.csv")
        return df["Nom"].tolist(), dict(zip(df["Nom"], df["Lien"]))
    return ["--- Sélectionner un coureur ---"], {}

COUREURS, LIENS_COUREURS = charger_coureurs()

def charger_json(fichier, defaut=None):
    if os.path.exists(fichier):
        with open(fichier, "r", encoding="utf-8") as f:
            return json.load(f)
    return defaut if defaut is not None else {}

def sauvegarder_json(fichier, donnees):
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(donnees, f, indent=4, ensure_ascii=False)

def simplifier_texte(texte):
    texte = unicodedata.normalize('NFKD', str(texte)).encode('ASCII', 'ignore').decode('utf-8').lower()
    texte = re.sub(r'[^a-z0-9]', ' ', texte)
    texte = re.sub(r'\s+', ' ', texte).strip()
    return texte

def trouver_vrai_nom(nom_brut, liste_coureurs):
    nom_sim = simplifier_texte(nom_brut)
    if not nom_sim: return nom_brut
    
    for c in liste_coureurs:
        if c == "--- Sélectionner un coureur ---": continue
        if simplifier_texte(c) == nom_sim:
            return c
            
    mots_brut = set(nom_sim.split())
    meilleur_match = nom_brut
    meilleur_score = 0
    
    for c in liste_coureurs:
        if c == "--- Sélectionner un coureur ---": continue
        c_sim = simplifier_texte(c)
        mots_c = set(c_sim.split())
        score = len(mots_brut.intersection(mots_c))
        if score >= 2 and score > meilleur_score:
            meilleur_score = score
            meilleur_match = c
            
    if meilleur_score >= 2:
        return meilleur_match
        
    noms_simplifies = {simplifier_texte(c): c for c in liste_coureurs if c != "--- Sélectionner un coureur ---"}
    matches = difflib.get_close_matches(nom_sim, noms_simplifies.keys(), n=1, cutoff=0.6)
    if matches:
        return noms_simplifies[matches[0]]
        
    mot_le_plus_long = max(mots_brut, key=len)
    if len(mot_le_plus_long) >= 4:
        for c in liste_coureurs:
            if c == "--- Sélectionner un coureur ---": continue
            if mot_le_plus_long in simplifier_texte(c):
                return c

    return nom_brut

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
            if new_user in users_db: st.error("Identifiant pris.")
            elif len(new_user) < 3: st.error("Identifiant > 3 caractères.")
            elif len(users_db) >= LIMITE_JOUEURS + 1: st.error("Jeu complet !")
            else:
                users_db[new_user] = new_pass
                sauvegarder_json(FICHIER_USERS, users_db)
                st.success("Compte créé avec succès !")

# --- 🛠️ ESPACE ADMINISTRATEUR ---
def espace_admin():
    st.title("🛠️ Espace Administrateur")
    
    onglet_cotes, onglet_resultats, onglet_joueurs, onglet_verrou, onglet_ajust, onglet_suppr_prono = st.tabs([
        "📈 Cotes", "🏁 Résultats", "👥 Joueurs", "🔒 Verrous", "✏️ Points", "🗑️ Suppr. Prono"
    ])
    
    # --- ONGLET 1 : COTES ---
    with onglet_cotes:
        cible_cotes = st.selectbox("Pour quelle course ajouter des cotes ?", NOM_COURSES)
        texte_brut_cotes = st.text_area("Texte Winamax (Cotes)", height=250)
        
        if st.button(f"Enregistrer les cotes pour {cible_cotes}"):
            lignes = [ligne.strip() for ligne in texte_brut_cotes.split('\n') if ligne.strip()]
            dico_cotes = {}
            cotes_trouvees = 0
            for i in range(len(lignes) - 1):
                nom_potentiel = lignes[i]
                cote_potentielle = lignes[i+1]
                if nom_potentiel.startswith("Étape") or nom_potentiel.endswith("%") or re.match(r'^[0-9]+[.,]?[0-9]*$', nom_potentiel): continue
                if re.match(r'^[0-9]+([.,][0-9]+)?$', cote_potentielle):
                    cote_float = float(cote_potentielle.replace(',', '.'))
                    nom_propre = f"{nom_potentiel.split(',')[1].strip()} {nom_potentiel.split(',')[0].strip()}" if "," in nom_potentiel else nom_potentiel
                    nom_trouve = trouver_vrai_nom(nom_propre, COUREURS)
                    dico_cotes[nom_trouve] = cote_float
                    cotes_trouvees += 1
            
            if cotes_trouvees > 0:
                toutes_les_cotes = charger_json(FICHIER_COTES, {})
                toutes_les_cotes[cible_cotes] = dico_cotes
                sauvegarder_json(FICHIER_COTES, toutes_les_cotes)
                st.success(f"✅ {cotes_trouvees} cotes enregistrées !")
            else: st.warning("Aucune cote trouvée.")

    # --- ONGLET 2 : RÉSULTATS ET POINTS ---
    with onglet_resultats:
        st.info("Règle : 1x la cote si présent dans le Top 6 | 2x la cote si place exacte. Relancer le calcul écrase l'ancien score.")
        cible_resultats = st.selectbox("Pour quelle course calculer les points ?", NOM_COURSES, key="cible_res")
        
        # NOUVEAUTÉ : Option de Recalcul rapide
        tous_les_resultats = charger_json(FICHIER_RESULTATS, {})
        top6_existant = tous_les_resultats.get(cible_resultats, [])
        
        if top6_existant:
            st.success(f"📌 Un Top 6 officiel est déjà enregistré pour cette étape.")
            with st.expander("Voir le Top 6 enregistré"):
                st.write(top6_existant)
                
            if st.button(f"🔄 Recalculer les points de {cible_resultats}", use_container_width=True):
                toutes_les_cotes = charger_json(FICHIER_COTES, {})
                cotes_du_jour = toutes_les_cotes.get(cible_resultats, {})
                tous_les_pronos = charger_json(FICHIER_PRONOS, {})
                tous_les_points = charger_json(FICHIER_POINTS, {})
                
                bilan_etape = {}

                for joueur, pronos_joueur in tous_les_pronos.items():
                    prono_etape = pronos_joueur.get(cible_resultats, [])
                    points_joueur = 0.0
                    
                    for index_joueur, coureur in enumerate(prono_etape):
                        if coureur == "--- Sélectionner un coureur ---": continue
                        
                        if coureur in top6_existant:
                            cote = cotes_du_jour.get(coureur, 0.0)
                            index_officiel = top6_existant.index(coureur)
                            
                            if index_joueur == index_officiel:
                                points_joueur += (cote * 2)
                            else:
                                points_joueur += cote
                                
                    if joueur not in tous_les_points:
                        tous_les_points[joueur] = {}
                    tous_les_points[joueur][cible_resultats] = round(points_joueur, 2)
                    bilan_etape[joueur] = round(points_joueur, 2)
                
                sauvegarder_json(FICHIER_POINTS, tous_les_points)
                st.balloons()
                st.write("### 💰 Nouveau Bilan de l'étape :")
                st.json(bilan_etape)
                
        st.divider()
        st.write("### 🏁 Saisir un NOUVEAU classement")
        st.write("Colle directement le classement de ProCyclingStats ci-dessous :")
        texte_brut_resultats = st.text_area("Classement PCS", height=250)
        
        if st.button(f"Clôturer et distribuer les points pour {cible_resultats}"):
            texte_propre = texte_brut_resultats.replace('\xa0', ' ')
            lignes_res = [ligne.strip() for ligne in texte_propre.split('\n') if ligne.strip()]
            top6_officiel = []
            
            for ligne in lignes_res:
                if re.match(r'^\d+[\s\t\.\-]+', ligne):
                    nom_nettoye = re.sub(r'^\d+[\s\t\.\-]+', '', ligne).strip()
                    nom_nettoye = nom_nettoye.split('\t')[0].strip()
                    nom_trouve = trouver_vrai_nom(nom_nettoye, COUREURS)
                    
                    if nom_trouve in COUREURS and nom_trouve != "--- Sélectionner un coureur ---":
                        if nom_trouve not in top6_officiel:
                            top6_officiel.append(nom_trouve)
                
                if len(top6_officiel) == 6: 
                    break
            
            if len(top6_officiel) == 0:
                st.error("⚠️ Aucun coureur reconnu. Vérifie ton texte.")
            else:
                if len(top6_officiel) < 6:
                    st.warning(f"Attention, l'algorithme n'a reconnu que {len(top6_officiel)} coureurs. Calcul en cours quand même...")
                else:
                    st.success("✅ Top 6 officiel validé ! Calcul des points en cours...")
                
                tous_les_resultats[cible_resultats] = top6_officiel
                sauvegarder_json(FICHIER_RESULTATS, tous_les_resultats)
                
                toutes_les_cotes = charger_json(FICHIER_COTES, {})
                cotes_du_jour = toutes_les_cotes.get(cible_resultats, {})
                tous_les_pronos = charger_json(FICHIER_PRONOS, {})
                tous_les_points = charger_json(FICHIER_POINTS, {})
                
                bilan_etape = {}

                for joueur, pronos_joueur in tous_les_pronos.items():
                    prono_etape = pronos_joueur.get(cible_resultats, [])
                    points_joueur = 0.0
                    
                    for index_joueur, coureur in enumerate(prono_etape):
                        if coureur == "--- Sélectionner un coureur ---": continue
                        
                        if coureur in top6_officiel:
                            cote = cotes_du_jour.get(coureur, 0.0)
                            index_officiel = top6_officiel.index(coureur)
                            
                            if index_joueur == index_officiel:
                                points_joueur += (cote * 2)
                            else:
                                points_joueur += cote
                                
                    if joueur not in tous_les_points:
                        tous_les_points[joueur] = {}
                    tous_les_points[joueur][cible_resultats] = round(points_joueur, 2)
                    bilan_etape[joueur] = round(points_joueur, 2)
                
                sauvegarder_json(FICHIER_POINTS, tous_les_points)
                st.balloons()
                st.write("### 💰 Bilan de l'étape :")
                st.json(bilan_etape)

    # --- ONGLET 3 : JOUEURS ---
    with onglet_joueurs:
        st.subheader("Gérer les inscriptions")
        users_db = charger_json(FICHIER_USERS, {"admin": "admin"})
        for user_item in list(users_db.keys()):
            if user_item != "admin":
                col1, col2 = st.columns([3, 1])
                col1.write(f"👤 **{user_item}**")
                if col2.button("Supprimer", key=f"del_{user_item}"):
                    del users_db[user_item]
                    sauvegarder_json(FICHIER_USERS, users_db)
                    st.success(f"Joueur {user_item} supprimé !")
                    st.rerun()

    # --- ONGLET 4 : VERROUILLAGE MANUEL ---
    with onglet_verrou:
        st.subheader("Contrôle du Temps")
        st.write("Outre l'heure officielle, tu peux forcer le verrouillage ou l'ouverture d'une étape.")
        
        cible_verrou = st.selectbox("Sélectionne une étape :", NOM_COURSES, key="cible_verrou")
        tous_les_verrous = charger_json(FICHIER_VERROUS, {})
        etat_actuel = tous_les_verrous.get(cible_verrou, "auto")
        
        nouvel_etat = st.radio(
            "État de l'étape :", 
            ["Automatique (Basé sur l'heure)", "🔒 Forcer le Verrouillage", "🟢 Forcer l'Ouverture"],
            index=0 if etat_actuel == "auto" else (1 if etat_actuel == "locked" else 2)
        )
        
        if st.button("Sauvegarder l'état du verrou"):
            if "Automatique" in nouvel_etat: tous_les_verrous[cible_verrou] = "auto"
            elif "Verrouillage" in nouvel_etat: tous_les_verrous[cible_verrou] = "locked"
            else: tous_les_verrous[cible_verrou] = "unlocked"
            
            sauvegarder_json(FICHIER_VERROUS, tous_les_verrous)
            st.success("✅ État du verrou mis à jour !")

    # --- ONGLET 5 : AJUSTER LES POINTS MANUELLEMENT ---
    with onglet_ajust:
        st.subheader("Ajustement manuel des scores")
        tous_les_points = charger_json(FICHIER_POINTS, {})
        users_db = charger_json(FICHIER_USERS, {"admin": "admin"})
        joueurs_inscrits = [u for u in users_db.keys() if u != "admin"]
        
        if joueurs_inscrits:
            col_j, col_e = st.columns(2)
            with col_j:
                joueur_cible = st.selectbox("Joueur :", joueurs_inscrits)
            with col_e:
                etape_cible = st.selectbox("Étape :", NOM_COURSES, key="etape_ajust")
                
            pts_actuels = tous_les_points.get(joueur_cible, {}).get(etape_cible, 0.0)
            st.info(f"Le score actuel de **{joueur_cible}** pour cette course est de : **{pts_actuels} pts**")
            
            nouveaux_pts = st.number_input("Entrer le nouveau score :", value=float(pts_actuels), step=1.0)
            
            if st.button("💾 Appliquer ce nouveau score", use_container_width=True):
                if joueur_cible not in tous_les_points:
                    tous_les_points[joueur_cible] = {}
                tous_les_points[joueur_cible][etape_cible] = nouveaux_pts
                sauvegarder_json(FICHIER_POINTS, tous_les_points)
                st.success(f"✅ Le score de {joueur_cible} a été mis à jour à {nouveaux_pts} pts !")
        else:
            st.warning("Aucun joueur n'est inscrit pour le moment.")
            
    # --- ONGLET 6 : SUPPRIMER UN PRONO ---
    with onglet_suppr_prono:
        st.subheader("Supprimer le pronostic d'un joueur")
        st.write("Utile si un joueur a fait une erreur ou pour annuler un pari invalide.")
        tous_les_pronos = charger_json(FICHIER_PRONOS, {})
        users_db = charger_json(FICHIER_USERS, {"admin": "admin"})
        joueurs_inscrits = [u for u in users_db.keys() if u != "admin"]

        if joueurs_inscrits:
            col_jp, col_ep = st.columns(2)
            with col_jp:
                joueur_prono = st.selectbox("Sélectionne le Joueur :", joueurs_inscrits, key="del_prono_joueur")
            with col_ep:
                etape_prono = st.selectbox("Sélectionne l'Étape :", NOM_COURSES, key="del_prono_etape")

            prono_existant = tous_les_pronos.get(joueur_prono, {}).get(etape_prono)

            if prono_existant:
                st.info("Prono actuel trouvé pour ce joueur :")
                st.write(prono_existant)
                if st.button("🗑️ Supprimer définitivement ce pronostic", use_container_width=True):
                    del tous_les_pronos[joueur_prono][etape_prono]
                    sauvegarder_json(FICHIER_PRONOS, tous_les_pronos)
                    st.success(f"✅ Le pronostic de {joueur_prono} pour {etape_prono} a été supprimé !")
                    st.rerun()
            else:
                st.warning(f"Aucun pronostic enregistré par {joueur_prono} pour {etape_prono}.")
        else:
            st.warning("Aucun joueur n'est inscrit pour le moment.")

# --- 🎮 INTERFACE JOUEUR ---
def main_app():
    if st.session_state.username == "admin":
        if st.sidebar.button("Se déconnecter"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
        espace_admin()
        return

    st.sidebar.title(f"💛 Salut {st.session_state.username} !")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
        
    st.sidebar.divider()
    
    menu_choix = st.sidebar.radio("Navigation :", ["📝 Faire un prono", "🏆 Classement des Joueurs"])
    
    if menu_choix == "🏆 Classement des Joueurs":
        st.title("🏆 Classement Général")
        st.write("Voici le classement de tous les joueurs de la ligue !")
        
        tous_les_points = charger_json(FICHIER_POINTS, {})
        classement = []
        
        for joueur, etapes in tous_les_points.items():
            total = sum(etapes.values())
            classement.append({"Joueur": joueur, "Points": round(total, 2)})
            
        if not classement:
            st.info("Aucun point n'a encore été distribué. Le classement est vide !")
        else:
            df_class = pd.DataFrame(classement).sort_values(by="Points", ascending=False).reset_index(drop=True)
            df_class.index = df_class.index + 1
            st.dataframe(df_class, use_container_width=True, column_config={
                "Joueur": st.column_config.TextColumn("👤 Manager"),
                "Points": st.column_config.NumberColumn("💯 Total des Points", format="%.2f pts")
            })

    else:
        st.sidebar.header("🗺️ Étapes")
        course_choisie = st.sidebar.radio("Sélectionne ton étape :", NOM_COURSES)
        
        with st.sidebar.expander("📚 Chercher une fiche PCS"):
            recherche = st.selectbox("Coureur :", COUREURS, key="recherche_pcs", label_visibility="collapsed")
            if recherche != "--- Sélectionner un coureur ---" and LIENS_COUREURS.get(recherche, ""):
                st.link_button(f"📊 Voir la fiche", LIENS_COUREURS.get(recherche))

        st.title(f"🏁 {course_choisie}")
        
        fuseau_paris = pytz.timezone("Europe/Paris")
        maintenant = datetime.now(fuseau_paris)
        
        horaires = charger_json(FICHIER_HORAIRES, {})
        limite_str = horaires.get(course_choisie, "2026-07-04 12:00") 
        
        try:
            limite_dt = fuseau_paris.localize(datetime.strptime(limite_str, "%Y-%m-%d %H:%M"))
            etape_verrouillee_auto = maintenant >= limite_dt
        except Exception:
            etape_verrouillee_auto = False

        tous_les_verrous = charger_json(FICHIER_VERROUS, {})
        etat_manuel = tous_les_verrous.get(course_choisie, "auto")
        
        etape_verrouillee = False
        message_verrou = ""
        
        if etat_manuel == "locked":
            etape_verrouillee = True
            message_verrou = "🔒 **Pronostics fermés !** (Verrouillage forcé)."
        elif etat_manuel == "unlocked":
            etape_verrouillee = False
        else:
            etape_verrouillee = etape_verrouillee_auto
            if etape_verrouillee:
                message_verrou = f"🔒 **Pronostics fermés !** Cette étape a commencé le {limite_dt.strftime('%d/%m à %H:%M')}."

        if etape_verrouillee:
            st.error(message_verrou)
            
            tous_les_resultats = charger_json(FICHIER_RESULTATS, {})
            if course_choisie in tous_les_resultats:
                st.success("🏁 L'étape est clôturée ! Voici le bilan.")
                top6_off = tous_les_resultats[course_choisie]
                
                col_res, col_pts = st.columns(2)
                with col_res:
                    st.subheader("Classement Officiel")
                    df_off = pd.DataFrame({"Coureur": top6_off})
                    df_off.index = range(1, len(top6_off) + 1)
                    st.dataframe(df_off, use_container_width=True)
                    
                with col_pts:
                    st.subheader("Points gagnés sur l'étape")
                    tous_les_points = charger_json(FICHIER_POINTS, {})
                    pts_etape = [{"Manager": j, "Points": pts.get(course_choisie, 0)} for j, pts in tous_les_points.items() if course_choisie in pts]
                    if pts_etape:
                        df_pts = pd.DataFrame(pts_etape).sort_values(by="Points", ascending=False).reset_index(drop=True)
                        df_pts.index = df_pts.index + 1
                        st.dataframe(df_pts, use_container_width=True)
            
            st.subheader("👀 Pronostics des managers")
            tous_les_pronos = charger_json(FICHIER_PRONOS, {})
            df_pronos = {}
            for j, pronos_j in tous_les_pronos.items():
                prono_list = pronos_j.get(course_choisie, [])
                if len(prono_list) == 6:
                    df_pronos[j] = prono_list
            if df_pronos:
                df_all_bets = pd.DataFrame(df_pronos)
                df_all_bets.index = range(1, 7)
                st.dataframe(df_all_bets, use_container_width=True)
                
        else:
            if etat_manuel == "unlocked":
                st.success("🟢 **Pronostics ouverts !** (Ouverture forcée).")
            else:
                st.info(f"⏳ Tu as jusqu'au **{limite_dt.strftime('%d/%m/%Y à %H:%M')}** pour valider ou modifier ton prono.")

        tous_les_profils = charger_json(FICHIER_PROFILS, {})
        url_profil = tous_les_profils.get(course_choisie, "")
        if url_profil:
            st.image(url_profil, use_container_width=True)

        st.divider()
        st.subheader("Ton Top 6")

        toutes_les_cotes = charger_json(FICHIER_COTES, {})
        cotes_du_jour = toutes_les_cotes.get(course_choisie, {})
        tous_les_pronos = charger_json(FICHIER_PRONOS, {})
        user = st.session_state.username
        if user not in tous_les_pronos: tous_les_pronos[user] = {}
        prono_actuel = tous_les_pronos[user].get(course_choisie, ["--- Sélectionner un coureur ---"] * 6)

        options_formatees = ["--- Sélectionner un coureur ---"]
        mapping_inverse = {"--- Sélectionner un coureur ---": "--- Sélectionner un coureur ---"}
        
        coureurs_tries = sorted([c for c in COUREURS if c != "--- Sélectionner un coureur ---"], key=lambda x: cotes_du_jour.get(x, 9999))

        for c in coureurs_tries:
            cote = cotes_du_jour.get(c)
            texte = f"{c} | Cote: {cote}" if cote else c 
            options_formatees.append(texte)
            mapping_inverse[texte] = c

        with st.form("formulaire_prono"):
            col1, col2 = st.columns(2)
            nouveau_prono_noms_purs = []
            
            for i in range(6):
                col_actuelle = col1 if i < 3 else col2
                nom_pur_precedent = prono_actuel[i] if i < len(prono_actuel) else "--- Sélectionner un coureur ---"
                
                texte_defaut = "--- Sélectionner un coureur ---"
                for texte_formate, nom_pur in mapping_inverse.items():
                    if nom_pur == nom_pur_precedent:
                        texte_defaut = texte_formate
                        break
                        
                index_defaut = options_formatees.index(texte_defaut) if texte_defaut in options_formatees else 0
                
                with col_actuelle:
                    choix_formate = st.selectbox(
                        f"🏆 Position {i+1}", 
                        options=options_formatees, 
                        index=index_defaut, 
                        key=f"pos_{i}",
                        disabled=etape_verrouillee
                    )
                    nouveau_prono_noms_purs.append(mapping_inverse[choix_formate])
            
            st.write("") 
            soumis = st.form_submit_button("Sauvegarder ce Top 6", use_container_width=True, disabled=etape_verrouillee)
            
            if soumis:
                vrais_choix = [c for c in nouveau_prono_noms_purs if c != "--- Sélectionner un coureur ---"]
                if len(vrais_choix) != len(set(vrais_choix)):
                    st.error("⚠️ Erreur : Tu as sélectionné plusieurs fois le même coureur !")
                elif len(vrais_choix) != 6:
                    st.warning(f"Tu n'as sélectionné que {len(vrais_choix)} coureurs sur 6. (C'est enregistré, mais complète vite !)")
                    tous_les_pronos[user][course_choisie] = nouveau_prono_noms_purs
                    sauvegarder_json(FICHIER_PRONOS, tous_les_pronos)
                else:
                    tous_les_pronos[user][course_choisie] = nouveau_prono_noms_purs
                    sauvegarder_json(FICHIER_PRONOS, tous_les_pronos)
                    st.success(f"✅ Ton pronostic est parfaitement enregistré !")
                    st.balloons()

if not st.session_state.logged_in:
    ecran_accueil()
else:
    main_app()
