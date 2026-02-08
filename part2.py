import json
import time
from bs4 import BeautifulSoup
from seleniumbase import SB
from config import SEARCH_WORD
INPUT_FILE = "JSON/data.json"

# Safety: avoid hammering eBay
SLEEP_BETWEEN_ITEMS = 2


def load_data(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_description(sb) -> str:
    """
    Tries multiple ways:
    1) iframe#desc_ifr (common on eBay)
    2) HTML fallbacks from page source
    Returns a cleaned string (may be empty if not found).
    """
    sb.wait_for_ready_state_complete(timeout=15)

    # 1) iframe description (most common)
    if sb.is_element_present("iframe#desc_ifr"):
        try:
            sb.switch_to_frame("desc_ifr")
            # Sometimes it's in body text
            desc_text = sb.get_text("body").strip()
            sb.switch_to_default_content()
            if desc_text:
                return desc_text
        except Exception:
            try:
                sb.switch_to_default_content()
            except Exception:
                pass

    # 2) Fallback: parse page source for any visible description areas
    html = sb.get_page_source()
    soup = BeautifulSoup(html, "html.parser")

    # Some pages expose a short description near item specifics or overview
    candidates = [
        soup.select_one("#desc_div"),
        soup.select_one("#viTabs_0_is"),  # sometimes item specifics / description tab area
        soup.select_one("div[data-testid='x-item-description']"),
        soup.select_one("div[data-testid='x-item-condition']"),
    ]

    for c in candidates:
        if c:
            text = c.get_text(" ", strip=True)
            if text and len(text) > 40:
                return text

    return ""


def enrich_items():
    data = load_data(INPUT_FILE)

    items = data.get("items", [])
    if not isinstance(items, list) or not items:
        print("No items found in data.json")
        return

    with SB(uc=True) as sb:
        for i, item in enumerate(items, start=1):
            link = (item.get("link") or "").strip()
            title = item.get("title", "")

            if not link:
                print(f"[{i}/{len(items)}] Skipping (no link): {title}")
                continue

            # Skip if already enriched
            if item.get("description"):
                print(f"[{i}/{len(items)}] Already has description: {title}")
                continue

            try:
                print(f"[{i}/{len(items)}] Opening: {title}")
                sb.open(link)

                # Some eBay pages show overlays; waiting a bit helps
                sb.wait_for_ready_state_complete(timeout=15)
                time.sleep(1)

                desc = extract_description(sb)
                item["description"] = desc

                if desc:
                    print(f"   ✅ Description length: {len(desc)}")
                else:
                    print("   ⚠️ No description found (maybe blocked/empty/iframe different)")

            except Exception as e:
                print(f"   ❌ Error: {e}")
                item["description"] = ""

            time.sleep(SLEEP_BETWEEN_ITEMS)
    OUTPUT_FILE ='JSON/'
    for word in SEARCH_WORD.split(' '):
        OUTPUT_FILE += word + "_"
    OUTPUT_FILE += 'eBay.json'
    save_data(OUTPUT_FILE, data)
    print(f"\nDone. Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    enrich_items()
