"""
bot_patch.py  —  exact changes needed in bot.py
Run this script from your project root to apply the patch automatically.
"""

import re, sys, os

BOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.py")


PATCHES = [

    # ── PATCH A: disease_rag_answer — resolve system prompt properly ──────
    {
        "name": "A — disease_rag_answer: pass resolved system to Ollama",
        "old": """\
async def disease_rag_answer(
    description: str,
    profile: dict,
    image_b64: str | None = None,
) -> str:
    rag_context = _build_disease_rag_context(description)
    farmer_ctx  = build_farmer_context(profile)

    if rag_context:
        prompt = (
            f"{farmer_ctx}"
            f"Farmer's disease description: \\"{description}\\"\\n\\n"
            f"{rag_context}\\n\\n"
            f"Using the knowledge above as reference, diagnose the crop problem "
            f"and give practical, field-ready remedies. "
            f"Do not mention 'database' or 'knowledge base' in your answer."
        )
    else:
        prompt = (
            f"{farmer_ctx}"
            f"Farmer says: \\"{description}\\"\\n"
            f"Diagnose the crop problem and give practical remedies."
        )

    if image_b64:
        return await query_ollama_vision_async(prompt, image_b64)
    return await query_ollama_async(prompt)""",

        "new": """\
async def disease_rag_answer(
    description: str,
    profile: dict,
    image_b64: str | None = None,
) -> str:
    rag_context = _build_disease_rag_context(description)
    farmer_ctx  = build_farmer_context(profile)      # already contains lang instruction

    # Resolve the system prompt — farmer context carries the language directive
    # in the *prompt*, so the system string just needs the placeholder stripped.
    resolved_system = FARMING_SYSTEM_PROMPT.replace("{lang_instruction}", "")

    if rag_context:
        prompt = (
            f"{farmer_ctx}"
            f"Farmer's disease description: \\"{description}\\"\\n\\n"
            f"{rag_context}\\n\\n"
            f"Using the knowledge above as reference, diagnose the crop problem "
            f"and give practical, field-ready remedies. "
            f"Do not mention 'database' or 'knowledge base' in your answer."
        )
    else:
        prompt = (
            f"{farmer_ctx}"
            f"Farmer says: \\"{description}\\"\\n"
            f"Diagnose the crop problem and give practical remedies."
        )

    if image_b64:
        return await query_ollama_vision_async(prompt, image_b64, system=resolved_system)
    return await query_ollama_async(prompt, system=resolved_system)""",
    },

    # ── PATCH B1: handle_crop_status — pass lang to build_daily_card ──────
    {
        "name": "B1 — handle_crop_status: pass lang= to build_daily_card",
        "old":  "        md, tts = build_daily_card(journey, name, ollama_tip=ai_tip)\n\n    await update.message.reply_text(\n        md,\n        parse_mode=ParseMode.MARKDOWN,\n        reply_markup=_journey_action_keyboard(),\n    )",
        "new":  "        md, tts = build_daily_card(journey, name, ollama_tip=ai_tip, lang=lang)\n\n    await update.message.reply_text(\n        md,\n        parse_mode=ParseMode.MARKDOWN,\n        reply_markup=_journey_action_keyboard(),\n    )",
    },

    # ── PATCH B2: journey_callback "journey_now" — pass lang ──────────────
    # The journey_now block has its own local build_daily_card call
    {
        "name": "B2 — journey_callback journey_now: pass lang= to build_daily_card",
        "old":  "        md, tts = build_daily_card(journey, name, ollama_tip=ai_tip)\n        await query.message.reply_text(",
        "new":  "        md, tts = build_daily_card(journey, name, ollama_tip=ai_tip, lang=lang)\n        await query.message.reply_text(",
    },

    # ── PATCH B3: _fire_journey_card — pass lang ──────────────────────────
    {
        "name": "B3 — _fire_journey_card: pass lang= to build_daily_card",
        "old":  "        md, tts_text = build_daily_card(journey, name, ollama_tip=ai_tip)",
        "new":  "        md, tts_text = build_daily_card(journey, name, ollama_tip=ai_tip, lang=lang)",
    },

    # ── PATCH C: journey_callback "journey_confirm_" — pass lang ──────────
    {
        "name": "C — journey_callback journey_confirm: pass lang= to build_journey_start_message",
        "old":  "        msg = build_journey_start_message(journey, name)",
        "new":  "        msg = build_journey_start_message(journey, name, lang=lang)",
    },
]


def apply_patches(path: str, patches: list[dict]) -> None:
    with open(path, encoding="utf-8") as f:
        src = f.read()

    for p in patches:
        old = p["old"]
        new = p["new"]
        if old not in src:
            print(f"  ⚠️  PATCH '{p['name']}' — old string NOT FOUND (already applied or mismatch)")
            continue
        src = src.replace(old, new, 1)
        print(f"  ✅  PATCH '{p['name']}' — applied")

    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"\n✅ bot.py patched successfully.")


def apply_crop_schedule(project_root: str) -> None:
    """Copy the fixed crop_schedule into utils/."""
    import shutil
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crop_schedule_fixed.py")
    dst = os.path.join(project_root, "utils", "crop_schedule.py")
    if not os.path.exists(src):
        print(f"  ⚠️  crop_schedule_fixed.py not found at {src}")
        return
    shutil.copy2(src, dst)
    print(f"  ✅  utils/crop_schedule.py replaced with multilingual version")


if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))
    bot_py = os.path.join(project_root, "bot.py")

    if not os.path.exists(bot_py):
        print(f"ERROR: bot.py not found at {bot_py}")
        print("Run this script from your Agrithm project root.")
        sys.exit(1)

    print("=== Agrithm Language & Disease Fix — Patch Applicator ===\n")

    # Step 1: Replace crop_schedule.py
    print("Step 1 — Replacing utils/crop_schedule.py ...")
    apply_crop_schedule(project_root)

    # Step 2: Patch bot.py
    print("\nStep 2 — Patching bot.py ...")
    apply_patches(bot_py, PATCHES)

    print("\n=== Done. Restart the bot with: python bot.py ===")