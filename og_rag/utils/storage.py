"""
utils/storage.py — Farmer profile + crop registry storage
──────────────────────────────────────────────────────────
FIXES:
  - save_profile() now also writes to data/user_profiles.json so new users
    appear in that file (was only writing to data/profiles/<uid>.json)
  - get_profile() checks data/profiles/ first, falls back to user_profiles.json
  - is_new_user() checks data/profiles/<uid>.json (correct, unchanged)
"""

import os
import json
import logging
from typing import Optional

log = logging.getLogger(__name__)

PROFILES_DIR        = os.path.join("data", "profiles")
REGISTRY_PATH       = os.path.join("data", "farmers_registry.json")
USER_PROFILES_PATH  = os.path.join("data", "user_profiles.json")  # FIX: sync target

os.makedirs(PROFILES_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# PROFILE HELPERS
# ═══════════════════════════════════════════════════════════════

def _profile_path(user_id: int) -> str:
    return os.path.join(PROFILES_DIR, f"{user_id}.json")


def is_new_user(user_id: int) -> bool:
    """Returns True if no profile file exists for this user yet."""
    return not os.path.exists(_profile_path(user_id))


def get_profile(user_id: int) -> Optional[dict]:
    """
    Read profile from data/profiles/<uid>.json.
    Falls back to data/user_profiles.json for migrating legacy users.
    """
    path = _profile_path(user_id)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error("get_profile failed for %s: %s", user_id, e)

    # FIX: fallback — check legacy user_profiles.json
    if os.path.exists(USER_PROFILES_PATH):
        try:
            with open(USER_PROFILES_PATH, encoding="utf-8") as f:
                all_profiles = json.load(f)
            profile = all_profiles.get(str(user_id))
            if profile:
                # Migrate: write to correct per-user file
                save_profile(user_id, profile)
                log.info("Migrated user %s from user_profiles.json to profiles/", user_id)
                return profile
        except Exception as e:
            log.warning("user_profiles.json fallback failed for %s: %s", user_id, e)

    return None


def save_profile(user_id: int, profile: dict) -> None:
    """
    Save profile to data/profiles/<uid>.json AND sync to data/user_profiles.json.
    FIX: user_profiles.json was never updated, so new users never appeared in it.
    """
    # ── 1. Save per-user file (primary storage) ───────────────────
    path = _profile_path(user_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        log.info("Profile saved: user=%s", user_id)
    except Exception as e:
        log.error("save_profile failed for %s: %s", user_id, e)
        return

    # ── 2. FIX: sync to user_profiles.json ───────────────────────
    try:
        all_profiles: dict = {}
        if os.path.exists(USER_PROFILES_PATH):
            try:
                with open(USER_PROFILES_PATH, encoding="utf-8") as f:
                    all_profiles = json.load(f)
            except Exception:
                all_profiles = {}

        all_profiles[str(user_id)] = profile

        with open(USER_PROFILES_PATH, "w", encoding="utf-8") as f:
            json.dump(all_profiles, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning("user_profiles.json sync failed for %s: %s", user_id, e)


def update_profile(user_id: int, **kwargs) -> None:
    """Partially update a profile — only the keys passed as kwargs."""
    profile = get_profile(user_id) or {}
    profile.update(kwargs)
    save_profile(user_id, profile)


def get_all_profiles() -> dict:
    """Returns {user_id_str: profile_dict} for every farmer profile on disk."""
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


def _save_registry(data: dict) -> None:
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def register_farmer_crop(
    user_id:  int,
    username: str,
    name:     str,
    crop:     str,
    district: str,
    village:  str = "",
) -> None:
    registry = _load_registry()
    crop_key = crop.lower().strip()

    if crop_key not in registry:
        registry[crop_key] = []

    # Remove old entry for this user first
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
    crop:            str,
    exclude_user_id: int  = None,
    village:         str  = "",
    district:        str  = "",
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
