import requests
from bs4 import BeautifulSoup
import json
import re

print("⏳ Début du scraping sur L'Équipe...")

URL = "https://www.lequipe.fr/Cyclisme-sur-route/Actualites/Le-parcours-complet-et-le-profil-des-etapes-du-tour-de-france-2026/1685331"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

try:
    reponse = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(reponse.text, "html.parser")
    
    profils_extraits = {}
    
    # On cherche toutes les images de la page
    for img in soup.find_all("img"):
        alt_texte = img.get("alt", "").lower()
        lien_img = img.get("src", "")
        
        # Si le texte alternatif parle d'un profil d'étape (ex: "profil de la 2e étape")
        if "profil" in alt_texte and "étape" in alt_texte and lien_img:
            # On cherche le numéro de l'étape dans la phrase
            match = re.search(r'(\d+)(e|re|er|ème)\s+étape', alt_texte)
            if match:
                numero = match.group(1)
                nom_etape = f"Étape {numero}"
                profils_extraits[nom_etape] = lien_img
                print(f"✅ Trouvé : {nom_etape}")

    # Sauvegarde dans un fichier JSON
    with open("profils.json", "w", encoding="utf-8") as f:
        json.dump(profils_extraits, f, indent=4, ensure_ascii=False)

    print(f"📁 Fichier 'profils.json' créé avec succès avec {len(profils_extraits)} profils !")

except Exception as e:
    print(f"❌ Erreur lors du scraping : {e}")
