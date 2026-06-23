import json
from bs4 import BeautifulSoup
import re

print("⏳ Création du fichier horaires à partir de tes données locales...")

# On lit directement le fichier que tu as créé (pas de requêtes internet !)
with open("donnees_brutes_pcs.json", "r", encoding="utf-8") as f:
    donnees = json.load(f)

horaires_etapes = {}
mois_dict = {
    "january": "01", "february": "02", "march": "03", "april": "04", 
    "may": "05", "june": "06", "july": "07", "august": "08", 
    "september": "09", "october": "10", "november": "11", "december": "12"
}

for nom_etape, html in donnees.items():
    if not nom_etape.startswith("Étape"):
        continue
        
    soup = BeautifulSoup(html, "html.parser")
    heure_depart = "12:00"
    date_formattee = f"2026-07-04 {heure_depart}"
    
    # 1. Extraction de l'heure (lambda permet d'ignorer les espaces cachés)
    for div in soup.find_all("div", class_=lambda c: c and "title" in c):
        if "Start time" in div.text:
            div_valeur = div.find_next_sibling("div", class_=lambda c: c and "value" in c)
            if div_valeur:
                match = re.search(r'\d{1,2}:\d{2}', div_valeur.text)
                if match: 
                    heure_depart = match.group()
            break
            
    # 2. Extraction de la Date
    for div in soup.find_all("div", class_=lambda c: c and "title" in c):
        if "Date" in div.text:
            div_valeur = div.find_next_sibling("div", class_=lambda c: c and "value" in c)
            if div_valeur:
                match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(202[0-9])', div_valeur.text, re.IGNORECASE)
                if match:
                    jour = match.group(1).zfill(2)
                    mois = mois_dict.get(match.group(2).lower(), "07")
                    annee = match.group(3)
                    date_formattee = f"{annee}-{mois}-{jour} {heure_depart}"
            break

    horaires_etapes[nom_etape] = date_formattee
    print(f"✅ {nom_etape} -> {date_formattee}")

# Le Classement Général se verrouille en même temps que la 1ère étape
horaires_etapes["Classement Général"] = horaires_etapes.get("Étape 1", "2026-07-04 12:00")

# Sauvegarde finale
with open("horaires.json", "w", encoding="utf-8") as f:
    json.dump(horaires_etapes, f, indent=4)

print("\n📁 Fichier 'horaires.json' généré avec succès !")
