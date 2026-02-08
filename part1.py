import json
import time
from urllib.parse import quote_plus
from seleniumbase import SB
from bs4 import BeautifulSoup
from config import SEARCH_WORD, MAX_ITEMS


def open_ebay_and_search(sb, page):
    encoded = quote_plus(SEARCH_WORD)
    url = f"https://www.ebay.com/sch/i.html?_nkw={encoded}&_sacat=0&_from=R40&_pgn={page}"
    sb.open(url)


def wait_for_results(sb, timeout=25):
    sb.wait_for_element_visible("ul.srp-results.srp-list.clearfix", timeout=timeout)


def extract_items_from_page(sb, seen):
    sb.wait_for_ready_state_complete(timeout=15)

    html = sb.get_page_source()
    soup = BeautifulSoup(html, "html.parser")

    results = []

    for li in soup.select("ul.srp-results.srp-list.clearfix li.s-card.s-card--horizontal"):
        listing_id = li.get("data-listingid") or ""
        if not listing_id or listing_id in seen:
            continue
        seen.add(listing_id)

        title_el = li.select_one(".s-card__title span.su-styled-text.primary")
        title = title_el.get_text(" ", strip=True) if title_el else ""

        link_el = li.select_one("a.s-card__link.image-treatment") or li.select_one("a.s-card__link")
        link = (link_el.get("href") or "").strip() if link_el else ""

        img_el = li.select_one("img.s-card__image")
        image = (img_el.get("src") or "").strip() if img_el else ""

        price_spans = [p.get_text(" ", strip=True) for p in li.select("span.s-card__price")]
        price = " ".join([p for p in price_spans if p])[:200]

        condition_el = li.select_one(".s-card__subtitle-row .s-card__subtitle span.su-styled-text.secondary")
        condition = condition_el.get_text(" ", strip=True) if condition_el else ""

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

    return results


def main():
    all_items = []
    seen = set()
    page = 1

    with SB(uc=True) as sb:
        while len(all_items) < MAX_ITEMS:
            print(f"\n📄 Loading page {page}...")
            open_ebay_and_search(sb, page)
            wait_for_results(sb)

            page_items = extract_items_from_page(sb, seen)

            if not page_items:
                print("⚠️ No items found on this page. Stopping.")
                break

            # Add items, but don’t exceed MAX_ITEMS
            remaining = MAX_ITEMS - len(all_items)
            all_items.extend(page_items[:remaining])

            print(f"✅ Page {page}: got {len(page_items)} new items | total: {len(all_items)}")

            page += 1
            time.sleep(1)  # small delay to reduce bot detection

    data = {
        "search": SEARCH_WORD,
        "count": len(all_items),
        "items": all_items
    }

    with open("JSON/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved {len(all_items)} items to JSON/data.json")


if __name__ == "__main__":
    main()
