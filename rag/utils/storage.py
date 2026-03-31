"""
utils/storage.py
────────────────
Handles all read/write operations for:
  - user_profiles.json   (farmer onboarding data)
  - farmer_network.json  (crop-wise farmer registry)
"""

import json
import os
import logging
from typing import Optional

log = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────
_ROOT              = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_PROFILES_PATH = os.path.join(_ROOT, "data", "user_profiles.json")
FARMER_NETWORK_PATH = os.path.join(_ROOT, "data", "farmer_network.json")


# ── Internal helpers ──────────────────────────────────────────────

def _load(path: str) -> dict:
    """Load a JSON file. Returns empty dict if missing or corrupt."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.error("Failed to load %s: %s", path, e)
        return {}


def _save(path: str, data: dict) -> bool:
    """Save dict to JSON file. Returns True on success."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        log.error("Failed to save %s: %s", path, e)
        return False


# ═══════════════════════════════════════════════════════════════
# USER PROFILE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def is_new_user(user_id: int) -> bool:
    """Returns True if user has NOT completed onboarding."""
    profiles = _load(USER_PROFILES_PATH)
    profile  = profiles.get(str(user_id), {})
    return not profile.get("onboarded", False)


def get_profile(user_id: int) -> Optional[dict]:
    """
    Get a farmer's full profile.
    Returns None if user doesn't exist.
    """
    profiles = _load(USER_PROFILES_PATH)
    return profiles.get(str(user_id))


def save_profile(user_id: int, profile: dict) -> bool:
    """
    Save a complete profile for a user.
    Overwrites any existing profile for that user_id.
    """
    profiles = _load(USER_PROFILES_PATH)
    profiles[str(user_id)] = profile
    log.info("Profile saved for user=%s", user_id)
    return _save(USER_PROFILES_PATH, profiles)


def update_profile(user_id: int, **kwargs) -> bool:
    """
    Update specific fields of an existing profile.
    Example: update_profile(123, digest_time="08:00", crop="wheat")
    """
    profiles = _load(USER_PROFILES_PATH)
    uid      = str(user_id)

    if uid not in profiles:
        log.warning("update_profile called for unknown user=%s", user_id)
        profiles[uid] = {}

    profiles[uid].update(kwargs)
    log.info("Profile updated for user=%s fields=%s", user_id, list(kwargs.keys()))
    return _save(USER_PROFILES_PATH, profiles)


def get_all_profiles() -> dict:
    """Returns all user profiles. Used by scheduler."""
    return _load(USER_PROFILES_PATH)


def delete_profile(user_id: int) -> bool:
    """Delete a user's profile (e.g. if they send /delete)."""
    profiles = _load(USER_PROFILES_PATH)
    uid      = str(user_id)
    if uid in profiles:
        del profiles[uid]
        log.info("Profile deleted for user=%s", user_id)
        return _save(USER_PROFILES_PATH, profiles)
    return False


# ═══════════════════════════════════════════════════════════════
# FARMER NETWORK FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def register_farmer_crop(
    user_id: int,
    username: str,
    name: str,
    crop: str,
    district: str
) -> bool:
    """
    Register a farmer in the crop network.
    Called during onboarding so farmers can find each other.
    """
    network = _load(FARMER_NETWORK_PATH)
    uid     = str(user_id)

    network[uid] = {
        "user_id":  uid,
        "username": username,
        "name":     name,
        "crop":     crop.lower().strip(),
        "district": district,
    }
    log.info("Farmer registered in network: user=%s crop=%s district=%s",
             user_id, crop, district)
    return _save(FARMER_NETWORK_PATH, network)


def find_farmers_by_crop(crop: str, exclude_user_id: int = None) -> list[dict]:
    """
    Find all farmers growing the same crop.
    Excludes the requesting farmer from results.

    Returns list of dicts with: user_id, username, name, crop, district
    """
    network = _load(FARMER_NETWORK_PATH)
    crop    = crop.lower().strip()
    results = []

    for uid, farmer in network.items():
        # Skip self
        if exclude_user_id and uid == str(exclude_user_id):
            continue
        # Match crop (partial match supported e.g. "paddy" matches "paddy rice")
        if crop in farmer.get("crop", "").lower():
            results.append(farmer)

    log.info("Found %d farmers for crop='%s'", len(results), crop)
    return results


def update_farmer_network(user_id: int, **kwargs) -> bool:
    """Update specific fields in the farmer network entry."""
    network = _load(FARMER_NETWORK_PATH)
    uid     = str(user_id)
    if uid in network:
        network[uid].update(kwargs)
        return _save(FARMER_NETWORK_PATH, network)
    return False