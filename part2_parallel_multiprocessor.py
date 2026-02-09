import os, tempfile, time, json
from multiprocessing import Process
from seleniumbase import SB
from bs4 import BeautifulSoup
import json
import glob

INPUT_PATTERN = "JSON/partial_*.json"     # matches partial_P1.json, partial_P2.json ...
OUTPUT_FILE = "JSON/merged_output.json"



INPUT_FILE = "JSON/data.json"
SLEEP_BETWEEN_ITEMS = 2

def merge_partials():
    merged_items = []

    partial_files = sorted(glob.glob(INPUT_PATTERN))
    if not partial_files:
        print("No partial files found!")
        return

    for file in partial_files:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data.get("items", [])
        merged_items.extend(items)
        print(f"Loaded {len(items)} items from {file}")

    # Save merged result
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"items": merged_items}, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Merged {len(merged_items)} total items into: {OUTPUT_FILE}")

def extract_description(sb) -> str:
    sb.wait_for_ready_state_complete(timeout=15)
    if sb.is_element_present("iframe#desc_ifr"):
        try:
            sb.switch_to_frame("desc_ifr")
            txt = sb.get_text("body").strip()
            sb.switch_to_default_content()
            return txt
        except Exception:
            try: sb.switch_to_default_content()
            except Exception: pass
    html = sb.get_page_source()
    soup = BeautifulSoup(html, "html.parser")
    c = soup.select_one("div[data-testid='x-item-description']")
    return c.get_text(" ", strip=True) if c else ""

def worker(name: str, start: int, end: int, debug_port: int):
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data["items"][start:end]

    profile_dir = os.path.join(tempfile.gettempdir(), f"sb_profile_{name}")
    os.makedirs(profile_dir, exist_ok=True)

    # ✅ unique debugging port per process
    chrome_args = [f"--remote-debugging-port={debug_port}"]

    with SB(uc=True, user_data_dir=profile_dir, chromium_arg=chrome_args) as sb:
        for idx, item in enumerate(items, start=start+1):
            link = (item.get("link") or "").strip()
            if not link:
                continue
            try:
                print(f"[{name}] [{idx}] open")
                sb.open(link)
                time.sleep(1)
                item["description"] = extract_description(sb)
                print(f"[{name}] [{idx}] done len={len(item['description'] or '')}")
            except Exception as e:
                print(f"[{name}] [{idx}] error {e}")
                item["description"] = ""

            time.sleep(SLEEP_BETWEEN_ITEMS)

    out = f"JSON/partial_{name}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"items": items}, f, ensure_ascii=False, indent=2)

from multiprocessing import cpu_count

MAX_WORKERS = 4      # set what you want ( 4 worked fine with me)
BASE_PORT = 9222

if __name__ == "__main__":
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    n = len(data["items"])
    workers = min(MAX_WORKERS, cpu_count(), n)

    # split n items into `workers` nearly-equal chunks
    base = n // workers
    rem = n % workers

    processes = []
    start = 0

    for i in range(workers):
        size = base + (1 if i < rem else 0)
        end = start + size

        name = f"P{i+1}"
        port = BASE_PORT + i

        p = Process(target=worker, args=(name, start, end, port))
        p.start()
        processes.append(p)

        start = end

    for p in processes:
        p.join()

    print("done")
    merge_partials()
