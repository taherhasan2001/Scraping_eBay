import json
import time
from seleniumbase import SB
from bs4 import BeautifulSoup
from config import CHECK_EVERY, SEARCH_WORD, MAX_ITEMS




def open_ebay_and_search(sb):
    encoded = quote_plus(SEARCH_WORD)
    url = f"https://www.ebay.com/sch/i.html?_nkw={encoded}&_sacat=0&_from=R40&_trksid=m570.l1313"
    sb.open(url)



def wait_for_results(sb, timeout=25):
    sb.wait_for_element_visible("ul.srp-results.srp-list.clearfix", timeout=timeout)



from urllib.parse import quote_plus

def extract_items(sb):
    sb.refresh()
    sb.wait_for_ready_state_complete(timeout=15)

    html = sb.get_page_source()
    soup = BeautifulSoup(html, "html.parser")

    results = []
    seen = set()

    # ✅ Based on your snippet
    for li in soup.select("ul.srp-results.srp-list.clearfix li.s-card.s-card--horizontal"):
        listing_id = li.get("data-listingid") or ""
        if not listing_id or listing_id in seen:
            continue
        seen.add(listing_id)

        # Title
        title_el = li.select_one(".s-card__title span.su-styled-text.primary")
        title = title_el.get_text(" ", strip=True) if title_el else ""

        # Link (image link is usually best)
        link_el = li.select_one("a.s-card__link.image-treatment") or li.select_one("a.s-card__link")
        link = (link_el.get("href") or "").strip() if link_el else ""

        # Image
        img_el = li.select_one("img.s-card__image")
        image = (img_el.get("src") or "").strip() if img_el else ""

        # Price (may be range: "$299.00 to $529.00")
        price_spans = [p.get_text(" ", strip=True) for p in li.select("span.s-card__price")]
        price = " ".join([p for p in price_spans if p])[:200]

        # Condition (ex: Brand New)
        condition_el = li.select_one(".s-card__subtitle-row .s-card__subtitle span.su-styled-text.secondary")
        condition = condition_el.get_text(" ", strip=True) if condition_el else ""

        # Skip junk
        if not title:
            continue

        results.append({
            "id": listing_id,
            "title": title,
            "price": price,
            "condition": condition,
            "link": link,
            "image": image,
        })

        if len(results) >= MAX_ITEMS:
            break

    return {
        "search": SEARCH_WORD,
        "count": len(results),
        "items": results
    }


def main():
    old_data = None

    with SB(uc=True) as sb:
        open_ebay_and_search(sb)
        wait_for_results(sb)
        print("✅ Results loaded")

        while True:
            try:
                data = extract_items(sb)

                if old_data is None or data != old_data:
                    print("💾 Changes detected — writing data.json")
                    with open("JSON/data.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    old_data = data
                else:
                    print("✅ No changes")

            except Exception as e:
                print("⚠️ Error:", e)
            if CHECK_EVERY :
                time.sleep(CHECK_EVERY)
            else:
                break
if __name__ == "__main__":
    main()
