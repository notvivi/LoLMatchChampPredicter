import requests
import time
import csv

API_KEY = "RGAPI_Code"
REGION = "eun1"
ROUTING = "europe"
TARGET_MATCHES = 1000
OUTPUT_FILE = "../data/lol_data_emerald.csv"
HEADERS = {"X-Riot-Token": API_KEY}


def get_data(url):
    """
    Gets data from Riot API with GET request.
    :param url: API endpoint URL.
    :return: JSON response if successful, else None if the request failed.
    """
    while True:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            wait = int(response.headers.get("Retry-After", 10))
            time.sleep(wait)
        else:
            return None

def get_emerald_puuids(target_count=600):
    """
    Gets PUUIDs of players in the Emerald division.
    :param target_count:target_count (int): The number of unique PUUIDs to collect.
    :return:list: A list of PUUID strings.
    """
    puuids = []
    for division in ["I", "II", "III", "IV"]:
        page = 1
        while len(puuids) < target_count:
            url = (f"https://{REGION}.api.riotgames.com/lol/league-exp/v4/entries"
                   f"/RANKED_SOLO_5x5/EMERALD/{division}?page={page}")
            entries = get_data(url)
            if not entries:
                break
            for e in entries:
                if e.get("puuid"):
                    puuids.append(e["puuid"])
            if len(entries) < 205:
                break
            page += 1
            time.sleep(1.2)
        if len(puuids) >= target_count:
            break
    return puuids[:target_count]

def collect():
    """
Orchestrates the data collection process:
    1. Fetches PUUIDs.
    2. Gathers Match IDs for those players.
    3. Scrapes detailed match info (champions, roles, win/loss).
    4. Saves results to a CSV file.
    """
    puuids = get_emerald_puuids(target_count=600)

    match_ids = set()
    for puuid in puuids:
        if len(match_ids) >= TARGET_MATCHES:
            break
        url = (f"https://{ROUTING}.api.riotgames.com/lol/match/v5/matches"
               f"/by-puuid/{puuid}/ids?start=0&count=20&type=ranked")
        ids = get_data(url)
        if ids:
            match_ids.update(ids)
        time.sleep(1.2)

    final_data = []
    for i, mid in enumerate(list(match_ids)[:TARGET_MATCHES], 1):
        url = f"https://{ROUTING}.api.riotgames.com/lol/match/v5/matches/{mid}"
        m = get_data(url)
        if not m or "info" not in m:
            continue
        for p in m["info"]["participants"]:
            allies = [str(cp["championId"]) for cp in m["info"]["participants"]
                      if cp["teamId"] == p["teamId"] and cp != p]
            enemies = [str(cp["championId"]) for cp in m["info"]["participants"]
                       if cp["teamId"] != p["teamId"]]
            final_data.append({
                "role": p.get("teamPosition", "UNKNOWN"),
                "championId": p["championId"],
                "win": 1 if p["win"] else 0,
                "allies": ",".join(allies),
                "enemies": ",".join(enemies),
            })
        time.sleep(1.2)

    if final_data:
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=final_data[0].keys())
            writer.writeheader()
            writer.writerows(final_data)

if __name__ == "__main__":
    collect()