import os
import csv
from difflib import get_close_matches

LGU_FILE = os.path.join("data", "ph_lgu_centroids.csv")

# GLOBAL LOOKUP TABLE
LGUS = {}  # (PROVINCE, MUNICIPALITY) -> (lat, lng)

def normalize(s):
    return str(s).strip().upper().replace("CITY OF ", "").replace(".", "")

def load_lgu_file():
    """Load all LGUs from CSV into LGUS dictionary."""
    if not os.path.exists(LGU_FILE):
        print("ERROR: LGU file not found:", LGU_FILE)
        return

    with open(LGU_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prov = normalize(row["province"])
            muni = normalize(row["municipality"])
            lat = float(row["lat"])
            lng = float(row["lng"])
            LGUS[(prov, muni)] = (lat, lng)

# Load on import
load_lgu_file()


def get_coords(area, unit):
    """
    Return ACCURATE coordinates from ph_lgu_centroids.csv
    area = province (may contain area codes)
    unit = municipality (real name)
    """

    # 🔥 ALWAYS RELOAD to ensure updates take effect
    load_lgu_file()

    # Normalize inputs
    area_clean = normalize(area)
    unit_clean = normalize(unit)

    # If area contains numbers (e.g., BATANGAS 1), strip them
    tokens = area_clean.split()
    area_name = tokens[0]

    # 1. Exact match
    key = (area_name, unit_clean)
    if key in LGUS:
        return *LGUS[key], "exact"

    # 2. Fuzzy match municipality within same province
    prov_munis = [m for (p, m) in LGUS.keys() if p == area_name]
    match = get_close_matches(unit_clean, prov_munis, n=1, cutoff=0.80)
    if match:
        m = match[0]
        return *LGUS[(area_name, m)], "fuzzy_province"

    # 3. Fuzzy match anywhere in PH
    all_munis = [m for (_, m) in LGUS.keys()]
    match = get_close_matches(unit_clean, all_munis, n=1, cutoff=0.80)
    if match:
        m = match[0]
        for (p, mm) in LGUS.keys():
            if mm == m:
                return *LGUS[(p, mm)], "fuzzy_global"

    # 4. No match found
    return None, None, "not_found"

