import requests
from bs4 import BeautifulSoup
import pandas as pd

print("⏳ Début du scraping sur ProCyclingStats...")

# URL de la startlist du Tour de France 2026
URL = "https://www.procyclingstats.com/race/tour-de-france/2026/startlist"

# On simule un navigateur classique pour ne pas être bloqué immédiatement
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    reponse = requests.get(URL, headers=HEADERS)
    reponse.raise_for_status() # Vérifie si la page a bien répondu
    
    soup = BeautifulSoup(reponse.text, "html.parser")
    
    coureurs_data = []
    
    # Astuce : sur PCS, les liens des coureurs contiennent "rider/"
    for lien in soup.find_all("a"):
        href = lien.get("href", "")
        # On filtre pour ne garder que les vrais liens de coureurs
        if href.startswith("rider/") and not href == "rider/":
            nom = lien.text.strip()
            # On ignore les liens vides ou les images
            if nom and len(nom) > 2:
                lien_complet = f"https://www.procyclingstats.com/{href}"
                coureurs_data.append({
                    "Nom": nom,
                    "Lien": lien_complet
                })
    
    # PCS affiche parfois des doublons dans le code HTML, on nettoie ça
    df = pd.DataFrame(coureurs_data).drop_duplicates(subset=['Nom'])
    
    # On ajoute la ligne "Sélection par défaut" tout en haut
    df_defaut = pd.DataFrame([{"Nom": "--- Sélectionner un coureur ---", "Lien": ""}])
    df_final = pd.concat([df_defaut, df], ignore_index=True)
    
    # Sauvegarde en CSV
    df_final.to_csv("coureurs.csv", index=False, encoding="utf-8")
    
    print(f"✅ Scraping terminé ! {len(df_final) - 1} coureurs récupérés avec leurs liens.")
    print("📁 Le fichier 'coureurs.csv' a été créé.")

except Exception as e:
    print(f"❌ Erreur lors du scraping : {e}")
