import os
import json
import re
import requests
import pandas as pd

# --- CONFIGURATION ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRIuRASQ_HlQiLMfa2SPx8jCt65vBzCq_ZMwTPAQLMg4v8W6luoIhimr5TDnLPNqhTieMRweKAS7fhJ/pub?gid=337005601&single=true&output=csv"

# Absolute Path Project Anchoring
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DATA_OUTPUT_PATH = os.path.join(REPO_ROOT, "data", "games.json")
IMAGE_DIR_PATH = os.path.join(REPO_ROOT, "static", "images", "games")

# Read your GamesDB Token securely from your environment
GAMESDB_API_KEY = os.environ.get("GAMESDB_API_KEY")

def slugify(text):
    """Converts game titles into clean, filesystem-safe strings."""
    text = str(text).lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    return re.sub(r'[\s-]+', '-', text)


def get_best_match_game(games):
    """Given a list of game entries from TheGamesDB, determine the best match based on region priority."""
    if not games:
        return None
    
    # Priority order: North America > Europe > Japan > others
    for region_id in [1, 2, 4]:
        for game in games:
            if game.get("region_id") == region_id:
                return game
    
    # Fallback to first result if no priority regions found
    return games[0]

def fetch_gamesdb_game(game_title, system):
    """
    Queries TheGamesDB API v1.1 search endpoint using fuzzy title match + platform filtering.
    Parses out the structural boxart asset path.
    """
    if not GAMESDB_API_KEY:
        print("   ⚠️ GAMESDB_API_KEY missing from environment properties.")
        return None

    # TheGamesDB maps platforms to exact ID integers.
    # Covers everything from classic handhelds to your Switch & Switch 2 logs
    platform_id_map = {
        "nes": 7, "snes": 6, "n64": 3, "gameboy": 4, "gbc": 41, "gba": 5, "ds": 8, "3ds": 4912,
        "switch": 4971, "switch2": 5021, # Switch 2 maps seamlessly into the Switch ecosystem
        "genesis": 18, "megadrive": 18, "sms": 35, "ps1": 10, "ps2": 11, "psp": 13, "vita": 39, "pc": 1
    }
    
    clean_system = system.lower().replace(" ", "").strip()
    platform_id = platform_id_map.get(clean_system)

    # Search Endpoint URL
    search_url = "https://api.thegamesdb.net/v1.1/Games/ByGameName"
    params = {
        "apikey": GAMESDB_API_KEY,
        "name": game_title,
        "fields": "images",
        "include": "boxart"
    }
    if platform_id:
        params["filter[platform]"] = platform_id
        params["filter[region]"] = "1"

    try:
        response = requests.get(search_url, params=params, timeout=12)
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        # Pull down the base image delivery URL directory structure from the configuration metadata node
        base_img_url = data.get("include", {}).get("boxart", {}).get("base_url", {}).get("thumb", "")
        games = data.get("data", {}).get("games", [])
        print(games)
        if not games:
            return None


        game = get_best_match_game(games)

        boxart_data = data.get("include", {}).get("boxart", {}).get("data", {}).get(str(game.get("id")), [])
        print(boxart_data)
        for art in boxart_data:
            # We want the front side artwork configuration block
            if art.get("type") == "boxart" and art.get("side") == "front":
                filename = art.get("filename")
                if filename:
                    game["boxart"] = f"{base_img_url}{filename}"


        print(game)
        # The first item returned is the closest search match
        return game
        
    except Exception as e:
        print(f"   ⚠️ TheGamesDB query exception: {e}")
        return None

def get_gamesdb_entry(title, system):
    game_data = fetch_gamesdb_game(title, system)
    
    if game_data:
        boxart_url = game_data.get("boxart")
        return boxart_url
    return None


def main():
    if not GAMESDB_API_KEY:
        print("❌ Error: Missing GAMESDB_API_KEY variable setup. Please export it in your shell profile.")
        return

    print("🚀 Fetching latest game configurations from Google Sheets...")
    try:
        df = pd.read_csv(SHEET_CSV_URL)
    except Exception as e:
        print(f"❌ Error downloading spreadsheet: {e}")
        return

    os.makedirs(os.path.dirname(DATA_OUTPUT_PATH), exist_ok=True)
    os.makedirs(IMAGE_DIR_PATH, exist_ok=True)

    games_list = []

    for _, row in df.iterrows():
        if pd.isna(row['Title']):
            continue

        title = str(row['Title']).strip()
        system = str(row['System']).strip()
        
        # Default placeholder setup; dynamically assigned based on network responses
        image_filename = f"{slugify(title)}.jpg" 
        local_image_path = os.path.join(IMAGE_DIR_PATH, image_filename)

        # Scrape missing graphics assets seamlessly
        if not os.path.exists(local_image_path) and not os.path.exists(local_image_path.replace(".jpg", ".png")):
            print(f"🔍 Searching TheGamesDB for: {title} ({system})...")
            img_url = get_gamesdb_entry(title, system)
            
            if img_url:
                try:
                    response = requests.get(img_url, timeout=10)
                    if response.status_code == 200:
                        content_type = response.headers.get('Content-Type', '')
                        ext = ".png" if "png" in content_type else ".jpg"
                        
                        image_filename = f"{slugify(title)}{ext}"
                        local_image_path = os.path.join(IMAGE_DIR_PATH, image_filename)
                        
                        with open(local_image_path, 'wb') as handler:
                            handler.write(response.content)
                        print(f"   ✅ Box Art downloaded: static/images/games/{image_filename}")
                    else:
                        print(f"   ⚠️ Asset mapping down (Status {response.status_code})")
                except Exception as e:
                    print(f"   ⚠️ Image sync failed: {e}")
            else:
                print(f"   ⚠️ No front cover located for '{title}'")

        # Confirm exact file properties mapping for ultimate Hugo rendering loops
        final_ext = ".png" if os.path.exists(local_image_path.replace(".jpg", ".png")) else ".jpg"
        
        game_entry = {
            "title": title,
            "system": system,
            "completionType": str(row.get('Completion Type', '')),
            "date": str(row.get('Date', '')),
            "timeToBeat": str(row.get('Time to Beat', '')),
            "cheats": str(row.get('Cheats', '')).lower() in ['yes', 'true'],
            "rating": float(row.get('Rating', 0)) if not pd.isna(row.get('Rating')) else 0,
            "notes": str(row.get('Notes', '')),
            "image": f"images/games/{slugify(title)}{final_ext}"
        }
        games_list.append(game_entry)

    with open(DATA_OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(games_list, f, indent=4, ensure_ascii=False)
        
    print(f"\n🎉 Sync Complete! Updated cards compiled cleanly into data/games.json!")

if __name__ == "__main__":
    main()