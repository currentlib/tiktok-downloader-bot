import os
from PIL import Image, ImageDraw, ImageFont

# --- Configuration ---
SCALE_FACTOR = 3  # High resolution (3x)

# Base dimensions
BASE_AVATAR_SIZE = 42
BASE_FONT_SIZE_USER = 16
BASE_FONT_SIZE_MSG = 16
BASE_PADDING_BUBBLE = 10
BASE_GAP_AVATAR_BUBBLE = 10
BASE_MARGIN = 15
BASE_BUBBLE_RADIUS = 12
BASE_MAX_TEXT_WIDTH = 280

# Colors
BUBBLE_COLOR = "#2b5278"
TEXT_USER_COLOR = "#64b5f6"
TEXT_MSG_COLOR = "#ffffff"

# Scaled Dimensions
AVATAR_SIZE = int(BASE_AVATAR_SIZE * SCALE_FACTOR)
FONT_SIZE_USER = int(BASE_FONT_SIZE_USER * SCALE_FACTOR)
FONT_SIZE_MSG = int(BASE_FONT_SIZE_MSG * SCALE_FACTOR)
PADDING_BUBBLE = int(BASE_PADDING_BUBBLE * SCALE_FACTOR)
GAP_AVATAR_BUBBLE = int(BASE_GAP_AVATAR_BUBBLE * SCALE_FACTOR)
MARGIN = int(BASE_MARGIN * SCALE_FACTOR)
BUBBLE_RADIUS = int(BASE_BUBBLE_RADIUS * SCALE_FACTOR)
TEXT_GAP_Y = int(4 * SCALE_FACTOR)
MAX_TEXT_WIDTH_PX = int(BASE_MAX_TEXT_WIDTH * SCALE_FACTOR)

# Helper: Circular Avatar
def process_avatar(image_path, size):
    try:
        img = Image.open(image_path).convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, size, size), fill=255)
        output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        output.paste(img, (0, 0), mask=mask)
        return output
    except Exception:
        # Grey placeholder
        placeholder = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(placeholder)
        draw.ellipse((0, 0, size, size), fill="#cccccc")
        return placeholder

# Helper: Wrap Text (Handles explicit newlines \n)
def wrap_text(text, font, max_width_px, draw_obj):
    # 1. Split by existing newlines (paragraphs)
    paragraphs = text.split('\n')
    all_lines = []

    for paragraph in paragraphs:
        # If paragraph is empty (double newline), add an empty line
        if not paragraph:
            all_lines.append("")
            continue

        words = paragraph.split(' ')
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw_obj.textbbox((0, 0), test_line, font=font)
            text_w = bbox[2] - bbox[0]

            if text_w <= max_width_px:
                current_line.append(word)
            else:
                if current_line:
                    all_lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Single word is too long, force split it
                    all_lines.append(word)
                    current_line = []
        
        if current_line:
            all_lines.append(' '.join(current_line))
            
    return all_lines

def generate_telegram_message(username, message, image_input_path, image_output_path):
    # 1. Load Fonts
    try:
        font_user = ImageFont.truetype("arialbd.ttf", FONT_SIZE_USER)
        font_msg = ImageFont.truetype("arial.ttf", FONT_SIZE_MSG)
    except IOError:
        font_user = ImageFont.load_default()
        font_msg = ImageFont.load_default()

    dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))

    # 2. Calculate Line Heights using Metrics (Stable Height)
    # This prevents the bubble from being too short if text has no descenders (like "mmm")
    # or failing if text is tall (like "Ag").
    
    # Username Height
    ascent_u, descent_u = font_user.getmetrics()
    user_line_h = ascent_u + descent_u + int(2 * SCALE_FACTOR) # small buffer

    # Message Line Height
    ascent_m, descent_m = font_msg.getmetrics()
    msg_line_h = ascent_m + descent_m + int(2 * SCALE_FACTOR)

    # 3. Process Content
    # Wrap message (Now handles \n properly)
    wrapped_lines = wrap_text(message, font_msg, MAX_TEXT_WIDTH_PX, dummy_draw)
    
    # Calculate widths to size the bubble
    user_bbox = dummy_draw.textbbox((0,0), username, font=font_user)
    user_w = user_bbox[2] - user_bbox[0]
    
    max_msg_w = 0
    for line in wrapped_lines:
        bbox = dummy_draw.textbbox((0,0), line, font=font_msg)
        w = bbox[2] - bbox[0]
        if w > max_msg_w: max_msg_w = w

    # 4. Calculate Geometry
    bubble_w = max(user_w, max_msg_w) + (PADDING_BUBBLE * 2)
    
    # Height = Padding + UserLine + Gap + (Lines * MsgLine) + Padding
    msg_block_h = len(wrapped_lines) * msg_line_h
    bubble_h = PADDING_BUBBLE + user_line_h + TEXT_GAP_Y + msg_block_h + PADDING_BUBBLE

    # Canvas Size
    total_w = MARGIN + AVATAR_SIZE + GAP_AVATAR_BUBBLE + bubble_w + MARGIN
    content_h = max(AVATAR_SIZE, bubble_h)
    total_h = MARGIN + content_h + MARGIN

    # 5. Draw
    canvas = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Avatar
    avatar_img = process_avatar(image_input_path, AVATAR_SIZE)
    avatar_y = MARGIN + content_h - AVATAR_SIZE
    canvas.paste(avatar_img, (MARGIN, avatar_y), mask=avatar_img)

    # Bubble
    bubble_x = MARGIN + AVATAR_SIZE + GAP_AVATAR_BUBBLE
    bubble_y = MARGIN + content_h - bubble_h
    draw.rounded_rectangle(
        (bubble_x, bubble_y, bubble_x + bubble_w, bubble_y + bubble_h),
        radius=BUBBLE_RADIUS, fill=BUBBLE_COLOR
    )

    # Text Rendering
    text_x = bubble_x + PADDING_BUBBLE
    # Start drawing exactly at the padding offset
    current_y = bubble_y + PADDING_BUBBLE

    # Draw Username
    draw.text((text_x, current_y), username, font=font_user, fill=TEXT_USER_COLOR)
    current_y += user_line_h + TEXT_GAP_Y

    # Draw Message Lines
    for line in wrapped_lines:
        draw.text((text_x, current_y), line, font=font_msg, fill=TEXT_MSG_COLOR)
        current_y += msg_line_h

    # Save
    if not image_output_path.lower().endswith(".png"):
        image_output_path += ".png"
    canvas.save(image_output_path, "PNG")
    return image_output_path

# --- Test ---
if __name__ == "__main__":
    # Create test avatar
    if not os.path.exists("test_avatar.jpg"):
        Image.new('RGB', (100,100), 'orange').save("test_avatar.jpg")

    # TEST CASE: Input with explicit newline
    msg = "TITLE\ntest"
    
    generate_telegram_message("Панікер", msg, "test_avatar.jpg", "fixed_output.png")
    print("Done. Check fixed_output.png")