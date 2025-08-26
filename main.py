import os
import json
from collections import defaultdict
from datetime import datetime

from PIL import Image
import pytesseract
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from ollama import Client  # Ollama client for local LLMs

# ------------- CONFIG -------------
user_name = "NickoLaygo"  # user name for PDF filename
images_folder = "screenshots"  # folder with your screenshots
images_per_page = 3  # number of images per page per date
page_width = 297  # A4 landscape width (mm)
page_height = 210  # A4 landscape height (mm)
margin = 10
ollama_model = "mistral:latest"
# ----------------------------------

# Make sure tesseract is reachable (adjust path if needed)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Initialize Ollama client
client = Client()


# --- Helpers ---
def safe_text(text: str) -> str:
    """Replace problematic unicode with safe equivalents and force latin-1 fallback for fpdf."""
    if text is None:
        return ""
    replacements = {
        "—": "-",
        "–": "-",
        """: '"',
        """: '"',
        "'": "'",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    # encode to latin-1 with replacement to avoid FPDF errors (it will strip unsupported chars)
    return text.encode("latin-1", "replace").decode("latin-1")


def extract_date_from_filename(filename):
    """Extract YYYY-MM-DD from your filename format Screenshot_YYYY-MM-DD-HH-..."""
    try:
        parts = filename.split("_")[1]  # "2025-08-24-18-30-16-438"
        date = "-".join(parts.split("-")[:3])  # "2025-08-24"
        return date
    except Exception:
        return "Unknown"


def ocr_text_from_image(img_path):
    """Run OCR and return raw text."""
    try:
        img = Image.open(img_path)
        txt = pytesseract.image_to_string(img)
        return txt.strip()
    except Exception as e:
        return f"[OCR error: {e}]"


def call_mistral_for_page_and_summary(ocr_text_combined):
    """
    Ask mistral:latest to (1) find page/source name from OCR text and
    (2) produce a concise summary that STARTS with 'This post is'.
    Expect JSON output: {"page_name": "...", "summary": "..."}
    """
    if not ocr_text_combined.strip():
        return "Unknown", "This post is not available due to missing context."

    prompt = (
        "You will be given OCR text from a Facebook screenshot. Look for the name of the Facebook page, group, or person who ORIGINALLY POSTED this content. "
        "Return a JSON object with keys: page_name and summary.\n\n"
        "1) page_name: Find who originally posted this (the main poster, not commenters). Look for:\n"
        "   - Facebook page names (like 'One Batangas', 'MMDA', 'GMA News')\n"
        "   - Facebook group names (like 'Batangas Buy and Sell', 'Calamba Updates')\n"
        "   - Individual person's name who made the original post\n"
        "   IGNORE: commenters, people who liked/reacted, sponsored content labels, timestamps, and UI elements.\n"
        "   The poster's name is usually at the TOP of the post, before the main content.\n"
        "   Return 'Unknown' only if you truly cannot find the original poster.\n\n"
        "2) summary: Write a concise summary (MAX 3 sentences) that MUST START with 'This post is' and describe:\n"
        "   - What the original post is about (main content)\n"
        "   - General sentiment/views of commenters if there are comments (e.g., 'supportive', 'mixed reactions', 'critical')\n"
        "   Focus on substance, not technical details. Keep it brief and readable.\n\n"
        "Return ONLY valid JSON. OCR TEXT:\n\n" + ocr_text_combined
    )

    try:
        response = client.chat(
            model=ollama_model, messages=[{"role": "user", "content": prompt}]
        )

        # Fixed: Properly extract content from Ollama response
        raw_content = ""
        if hasattr(response, "message") and hasattr(response.message, "content"):
            # If response has message.content attribute
            raw_content = response.message.content
        elif isinstance(response, dict) and "message" in response:
            # If response is dict with message key
            if isinstance(response["message"], dict):
                raw_content = response["message"].get("content", "")
            elif hasattr(response["message"], "content"):
                raw_content = response["message"].content
        else:
            # Fallback - convert to string and hope for the best
            raw_content = str(response)

        if not raw_content:
            return "Unknown", "This post is not available due to empty response."

        # Try to extract JSON from the response
        json_text = None
        raw_content = raw_content.strip()

        if raw_content.startswith("{") and raw_content.endswith("}"):
            json_text = raw_content
        else:
            # find first { and last } to extract JSON
            first = raw_content.find("{")
            last = raw_content.rfind("}")
            if first != -1 and last != -1 and last > first:
                json_text = raw_content[first : last + 1]

        if json_text:
            try:
                data = json.loads(json_text)
                page_name = data.get("page_name", "Unknown") or "Unknown"
                summary = data.get("summary", "") or ""

                # Ensure summary starts with "This post is"
                if summary and not summary.lower().startswith("this post is"):
                    summary = "This post is " + summary
                elif not summary:
                    summary = "This post is about the content shown in the screenshots."

                return (page_name.strip(), summary.strip())
            except json.JSONDecodeError:
                # JSON parsing failed, fall back to text processing
                pass

        # Fallback: if JSON parsing fails, try to extract meaningful info from raw text
        lines = [ln.strip() for ln in raw_content.splitlines() if ln.strip()]

        # Look for obvious page indicators in the text
        page_name = "Unknown"
        for line in lines:
            # Look for Facebook-specific indicators
            if any(
                keyword in line.lower()
                for keyword in [
                    "posted by",
                    "shared by",
                    "page:",
                    "group:",
                    "from:",
                    "source:",
                    "admin",
                    "moderator",
                    "official",
                    "verified",
                ]
            ):
                # Extract the part after common indicators
                for indicator in [
                    "posted by",
                    "shared by",
                    "page:",
                    "group:",
                    "from:",
                    "source:",
                ]:
                    if indicator in line.lower():
                        potential_page = line.lower().split(indicator, 1)[1].strip()
                        if len(potential_page) > 3 and len(potential_page) < 50:
                            page_name = potential_page.title()  # Capitalize properly
                            break
                if page_name != "Unknown":
                    break

        # If still unknown, try to find page names from common Facebook patterns in OCR
        if page_name == "Unknown" and ocr_text_combined:
            ocr_lines = ocr_text_combined.splitlines()
            # Look for lines that might be the original poster (usually at the top)
            for line in ocr_lines[:3]:  # Check first 3 lines only for poster name
                line = line.strip()
                # Skip very short or very long lines, and common UI elements
                if (
                    3 < len(line) < 50
                    and not any(
                        skip in line.lower()
                        for skip in [
                            "like",
                            "comment",
                            "share",
                            "follow",
                            "sponsored",
                            "mins",
                            "hrs",
                            "days",
                            "ago",
                            "just now",
                            "yesterday",
                            "replied",
                            "reacted",
                            "tagged",
                            "wrote:",
                            "said:",
                            "view",
                            "replies",
                            "see more",
                            "translate",
                            "edited",
                        ]
                    )
                    and
                    # Avoid lines that look like comments or reactions
                    not line.endswith("·")  # FB timestamp separator
                    and not any(
                        char in line for char in ["👍", "❤️", "😂", "😮", "😢", "😡"]
                    )  # reactions
                    and not line.lower().startswith(("reply", "comment", "see all"))
                ):
                    page_name = line
                    break

        # Create a simple summary from the OCR text itself
        # Take first meaningful sentence from OCR text if available
        if ocr_text_combined.strip():
            ocr_lines = [
                ln.strip()
                for ln in ocr_text_combined.splitlines()
                if len(ln.strip()) > 10
            ]
            if ocr_lines:
                first_content = ocr_lines[0][:200]  # First substantial line, truncated
                summary = f"This post is about: {first_content}"
            else:
                summary = "This post is shown in the screenshot but content could not be determined."
        else:
            summary = "This post is shown in the screenshot but no text was detected."

        return page_name, summary

    except Exception as e:
        # If model call completely fails, return fallback
        return (
            "Unknown",
            f"This post is shown in the screenshot (analysis failed: {str(e)[:100]}).",
        )


# --- Group images by date ---
images_by_date = defaultdict(list)
for file in os.listdir(images_folder):
    if file.lower().endswith((".png", ".jpg", ".jpeg")):
        date = extract_date_from_filename(file)
        file_path = os.path.join(images_folder, file)
        images_by_date[date].append(file_path)

# Sort file lists for deterministic order
for k in images_by_date:
    images_by_date[k].sort()

# --- Determine date range for filename ---
all_dates = sorted(images_by_date.keys())
if all_dates:
    start_date = datetime.strptime(all_dates[0], "%Y-%m-%d")
    end_date = datetime.strptime(all_dates[-1], "%Y-%m-%d")

    # Format dates as "Month Day"
    start_formatted = start_date.strftime("%B %d")
    end_formatted = end_date.strftime("%B %d")

    # Create filename
    if start_formatted == end_formatted:
        # Same date
        output_pdf = f"{user_name} - {start_formatted}.pdf"
    else:
        # Date range
        output_pdf = f"{user_name} - {start_formatted} - {end_formatted}.pdf"
else:
    # Fallback if no dates found
    output_pdf = f"{user_name} - Screenshots.pdf"

# --- Create PDF (landscape A4) ---
pdf = FPDF(orientation="L", unit="mm", format="A4")
pdf.set_auto_page_break(auto=False)
pdf.set_font("helvetica", size=12)

# layout constants
top_margin = margin
title_height = 12 + 4  # approx
reserved_context = 40  # reserved vertical space for context area at bottom
max_img_area_height = (
    page_height - top_margin - title_height - reserved_context - 10
)  # safety margin

from fpdf.enums import XPos, YPos  # deprecation-safe cell movement

for date, files in sorted(images_by_date.items()):
    # chunk per images_per_page
    for i in range(0, len(files), images_per_page):
        chunk = files[i : i + images_per_page]
        part_num = (i // images_per_page) + 1

        # --- OCR for this chunk (per-image) ---
        ocr_texts = []
        for img_path in chunk:
            ocr_texts.append(ocr_text_from_image(img_path))
        combined_ocr_text = "\n\n".join(ocr_texts)

        # --- Ask model for page_name and summary (for this chunk) ---
        page_name_raw, summary_raw = call_mistral_for_page_and_summary(
            combined_ocr_text
        )

        page_name = safe_text(page_name_raw)
        summary = safe_text(summary_raw)

        # Enforce summary starting phrase "This post is"
        if not summary.lower().startswith("this post is"):
            # gently rewrite via the model to ensure the exact phrase if possible
            rewrite_prompt = (
                "Rewrite the following paragraph so it STARTS with 'This post is' "
                "and includes both the main post content AND general commenter sentiment if present. "
                "Keep it to exactly 3 sentences maximum:\n\n" + summary_raw
            )
            try:
                resp2 = client.chat(
                    model=ollama_model,
                    messages=[{"role": "user", "content": rewrite_prompt}],
                )

                # Fixed: Properly extract content from rewrite response too
                rewrite_content = ""
                if hasattr(resp2, "message") and hasattr(resp2.message, "content"):
                    rewrite_content = resp2.message.content
                elif isinstance(resp2, dict) and "message" in resp2:
                    if isinstance(resp2["message"], dict):
                        rewrite_content = resp2["message"].get("content", "")
                    elif hasattr(resp2["message"], "content"):
                        rewrite_content = resp2["message"].content

                if rewrite_content:
                    candidate_line = rewrite_content.strip().splitlines()[0].strip()
                    if candidate_line and candidate_line.lower().startswith(
                        "this post is"
                    ):
                        summary = safe_text(candidate_line)
                    else:
                        summary = safe_text("This post is " + summary_raw[:300])
                else:
                    summary = safe_text("This post is " + summary_raw[:300])
            except Exception:
                # fallback naive prefix
                summary = safe_text(
                    "This post is "
                    + (summary_raw or "about the content shown in the screenshots.")
                )
        # final safety
        summary = safe_text(summary)

        # --- Compose title text ---
        title = f"Date: {date}"
        if part_num > 1:
            title += f" - Part {part_num}"

        # --- Add PDF page and layout images ---
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(
            0, 12, safe_text(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C"
        )
        # small gap
        pdf.ln(4)

        # Compute image widths and heights while preserving aspect ratio
        available_width = page_width - 2 * margin
        spacing = 5
        num_imgs = len(chunk)
        # compute target width per image (initial)
        target_w = (available_width - (spacing * (num_imgs - 1))) / num_imgs

        # calculate natural heights for each image at that width (using pixel aspect ratio)
        natural_heights = []
        pil_images = []
        for img_path in chunk:
            try:
                im = Image.open(img_path)
                pil_images.append((img_path, im.width, im.height))
                natural_h = target_w * (im.height / im.width)
                natural_heights.append(natural_h)
            except Exception:
                pil_images.append((img_path, None, None))
                natural_heights.append(target_w * 0.75)

        # if any natural height exceeds max_img_area_height, scale all down
        max_natural_h = max(natural_heights) if natural_heights else 0
        scale_factor = 1.0
        if max_natural_h > max_img_area_height:
            scale_factor = max_img_area_height / max_natural_h

        final_w = target_w * scale_factor
        final_heights = [h * scale_factor for h in natural_heights]

        # center the row horizontally
        total_row_width = final_w * num_imgs + spacing * (num_imgs - 1)
        start_x = (page_width - total_row_width) / 2

        img_y = top_margin + title_height

        x = start_x
        for idx, (img_path, w_px, h_px) in enumerate(pil_images):
            h_mm = final_heights[idx]
            # draw image
            try:
                pdf.image(img_path, x=x, y=img_y, w=final_w, h=h_mm)
            except Exception:
                # fallback: draw without explicit size
                try:
                    pdf.image(img_path, x=x, y=img_y)
                except Exception:
                    pass
            x += final_w + spacing

        # --- Add page name and summary below images ---
        pdf.set_y(img_y + max(final_heights) + 8)
        pdf.set_font("helvetica", "B", 12)
        # show page name (if unknown, skip or show Unknown)
        if page_name and page_name.lower() != "unknown":
            pdf.cell(
                0,
                8,
                safe_text(f"Page: {page_name}"),
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
                align="L",
            )
        else:
            pdf.cell(
                0,
                8,
                safe_text("Page: Unknown"),
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
                align="L",
            )

        pdf.set_font("helvetica", "", 11)
        # summary label + text (wrap automatically using multi_cell)
        pdf.multi_cell(
            0, 7, safe_text(f"Context: {summary}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )

# Save PDF
pdf.output(output_pdf)
print(f"✅ PDF saved as {output_pdf}")
