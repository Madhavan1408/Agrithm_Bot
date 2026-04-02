"""
utils/storage.py — Farmer profile + crop registry storage
──────────────────────────────────────────────────────────
All data stored as JSON files under data/
  data/profiles/<user_id>.json   — individual farmer profiles
  data/farmers_registry.json     — crop → list of farmers index

FIXED:
  - Added get_all_profiles() — was missing, caused scheduler crash
"""

import os
import json
import logging
from typing import Optional

log = logging.getLogger(__name__)

PROFILES_DIR  = os.path.join("data", "profiles")
REGISTRY_PATH = os.path.join("data", "farmers_registry.json")

os.makedirs(PROFILES_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# PROFILE HELPERS
# ═══════════════════════════════════════════════════════════════

def _profile_path(user_id: int) -> str:
    return os.path.join(PROFILES_DIR, f"{user_id}.json")


def is_new_user(user_id: int) -> bool:
    return not os.path.exists(_profile_path(user_id))


def get_profile(user_id: int) -> Optional[dict]:
    path = _profile_path(user_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error("get_profile failed for %s: %s", user_id, e)
        return None


def save_profile(user_id: int, profile: dict):
    path = _profile_path(user_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        log.info("Profile saved: user=%s", user_id)
    except Exception as e:
        log.error("save_profile failed for %s: %s", user_id, e)


def update_profile(user_id: int, **kwargs):
    """Partially update a profile — only the keys passed as kwargs."""
    profile = get_profile(user_id) or {}
    profile.update(kwargs)
    save_profile(user_id, profile)


def get_all_profiles() -> dict:
    """
    ADDED: Returns {user_id_str: profile_dict} for every farmer profile on disk.
    Used by scheduler to find who needs a digest sent.
    """
    profiles = {}
    if not os.path.exists(PROFILES_DIR):
        return profiles
    for fname in os.listdir(PROFILES_DIR):
        if not fname.endswith(".json"):
            continue
        uid   = fname.replace(".json", "")
        fpath = os.path.join(PROFILES_DIR, fname)
        try:
            with open(fpath, encoding="utf-8") as f:
                profiles[uid] = json.load(f)
        except Exception as e:
            log.warning("Could not read profile %s: %s", fname, e)
    return profiles


# ═══════════════════════════════════════════════════════════════
# FARMERS REGISTRY  (crop index)
# ═══════════════════════════════════════════════════════════════

def _load_registry() -> dict:
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_registry(data: dict):
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def register_farmer_crop(
    user_id: int,
    username: str,
    name: str,
    crop: str,
    district: str,
    village: str = "",
):
    registry = _load_registry()
    crop_key = crop.lower().strip()

    if crop_key not in registry:
        registry[crop_key] = []

    registry[crop_key] = [
        f for f in registry[crop_key] if f.get("user_id") != user_id
    ]
    registry[crop_key].append({
        "user_id":  user_id,
        "username": username,
        "name":     name,
        "crop":     crop_key,
        "district": district,
        "village":  village,
    })
    _save_registry(registry)
    log.info("Registered farmer: user=%s crop=%s district=%s village=%s",
             user_id, crop_key, district, village)


def find_farmers_by_crop(
    crop: str,
    exclude_user_id: int = None,
    village: str = "",
    district: str = "",
) -> list:
    registry    = _load_registry()
    crop_key    = crop.lower().strip()
    all_farmers = registry.get(crop_key, [])

    candidates = [
        f for f in all_farmers
        if f.get("user_id") != exclude_user_id
    ]
    if not candidates:
        return []

    if village:
        village_lower = village.lower().strip()
        village_match = [
            f for f in candidates
            if f.get("village", "").lower().strip() == village_lower
        ]
        if village_match:
            return village_match

    if district:
        district_lower = district.lower().strip()
        district_match = [
            f for f in candidates
            if f.get("district", "").lower().strip() == district_lower
        ]
        if district_match:
            return district_match

    return candidates