import os
from PIL import Image, ImageDraw, ImageFont

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_DIR = os.path.join(_ROOT, "data", "journey_images")
os.makedirs(IMAGE_DIR, exist_ok=True)

def generate_tomorrow_requirements_image(crop: str, day: int, stage_name: str, tasks: list, fertilizer: dict = None) -> str:
    """
    Generate an image dynamically listing out tomorrow's requirements.
    """
    filename = os.path.join(IMAGE_DIR, f"req_{crop}_{day}.png")
    
    # Create background
    width, height = 700, 500
    img = Image.new("RGB", (width, height), color="#F4FAEC")
    draw = ImageDraw.Draw(img)

    # Fonts
    try:
        font_large = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
        font_medium = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
        font_bold = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
    except IOError:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_bold = ImageFont.load_default()

    # Draw Banner
    draw.rectangle([(0, 0), (width, 80)], fill="#2E7D32")
    draw.text((30, 20), f"🌱 Tomorrow's Requirements ({crop.title()} - Day {day})", font=font_large, fill="white")

    # Draw Content
    y_text = 100
    draw.text((30, y_text), "Get these items ready for tomorrow:", font=font_bold, fill="#1B5E20")
    y_text += 40

    items_to_buy = []
    
    # Always add something
    items_to_buy.append("✅ Inspection Tools / Proper Attire")
    
    if fertilizer and fertilizer.get("product"):
        items_to_buy.append(f"✅ FERTILIZER: {fertilizer['product']}")
        items_to_buy.append(f"    - Dose: {fertilizer.get('dose', 'See routine')}")

    # Process tasks to extract potential sprays/chemicals
    for task in tasks:
        if "spray" in task.lower() or "apply" in task.lower():
            items_to_buy.append("✅ REQUIRED: " + task[:70] + "...")
            
    if len(items_to_buy) == 1:
        items_to_buy.append("No special chemicals or fertilizers needed.")
        items_to_buy.append("Just your standard farming tools! 🚜")

    for item in items_to_buy:
        draw.text((40, y_text), item, font=font_medium, fill="#333333")
        y_text += 35

    # Footer
    draw.rectangle([(0, height - 40), (width, height)], fill="#E8F5E9")
    draw.text((width//2 - 100, height - 30), "Agrithm Crop Journey 🌿", font=font_medium, fill="#2E7D32")

    img.save(filename)
    return filename
