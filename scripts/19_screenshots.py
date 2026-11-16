# captures the demo pages as report screenshots from a running demo server (streamlit run demo/app.py)
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gwcache import config

BASE = "http://localhost:8501/"
SHOTS = [
    ("demo_replay_start", "?page=Replay&step=200", None),
    ("demo_replay_mid", "?page=Replay&step=452", None),
    ("demo_replay_end", "?page=Replay&step=2424", None),
    ("demo_inspect_blocked", "?page=Inspect%20a%20decision&filter=0&pick=0", None),
    ("demo_inspect_served", "?page=Inspect%20a%20decision&filter=1&pick=3", None),
    ("demo_operating_5", "?page=Operating%20point&target=5", None),
    ("demo_operating_10", "?page=Operating%20point&target=10", None),
    ("demo_findings", "?page=Findings", None),
    ("demo_live", "?page=Live%20admission", ["Can you make some ASCII-art please?", "make it shorter", "Where can I use chatgpt 4 for free"]),
]


# waits until streamlit has finished running the script for the current page
def settle(page, extra: float = 2.0):
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=120000)
    page.wait_for_selector('[data-testid="stApp"][data-test-script-state="notRunning"]', timeout=900000)
    time.sleep(extra)


# opens each page in edge, types live requests where given, and saves a full-page png
def main():
    from playwright.sync_api import sync_playwright

    out = config.path("figures") / "demo"
    out.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 950}, device_scale_factor=1.5)
        for name, query, typed in SHOTS:
            if only and name not in only:
                continue
            page.goto(BASE + query)
            settle(page, 3.0)
            for n, text in enumerate(typed or [], start=1):
                box = page.get_by_label("Request")
                box.wait_for(timeout=900000)
                box.fill(text)
                box.press("Enter")
                settle(page, 1.0)
                page.get_by_role("button", name="Send").click()
                page.wait_for_function(f"document.body.innerText.split('Latency').length > {n}", timeout=120000)
                settle(page, 1.0)
            height = page.evaluate("document.querySelector('[data-testid=\"stMain\"]').scrollHeight")
            page.set_viewport_size({"width": 1500, "height": int(min(max(height, 950), 4000))})
            settle(page, 1.5)
            page.screenshot(path=str(out / f"{name}.png"))
            page.set_viewport_size({"width": 1500, "height": 950})
            print("saved", name)
        browser.close()


if __name__ == "__main__":
    main()
