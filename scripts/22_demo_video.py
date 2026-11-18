# records the demo video: drives the running demo in a browser, adds captions, narrates with windows speech, muxes an mp4
import json
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np

OUT = Path(r"D:\Capstone\demo_video")
APP = "http://localhost:8501/"
API = "http://127.0.0.1:8077/docs"
W, H = 1600, 900
VOICE = "Microsoft Zira Desktop"
TITLE = "Pattern-Mining-Driven Cache Admission and Routing for Multi-Provider LLM Gateways"
FIGS = Path(__file__).resolve().parent.parent / "results" / "figures" / "report"
TEAM = "Arnav Gupta · Saugata Kumar Jana · Avishkar Maitra · Arpita Suresh Kulkarni · Guide: Dr. Sandipan Maiti"

# each scene: on-screen caption, spoken narration, and the minimum seconds it stays on screen
SCENES = [
    ("title", "", "This is a demonstration of our capstone project: a behavior-aware cache admission engine for "
                  "large language model gateways. Everything shown runs on the real held-out data and the frozen models.", 6),
    ("architecture", "How it works: every request is matched against cached ones, then judged by its behavior — "
                     "dialogue act, mined patterns and learned rules.",
     "Here is how it works. Online, each request is embedded and matched against the three most similar cached requests. "
     "We then describe both turns by their behavior: the dialogue act, the behavioral state mined from past sessions, and "
     "a learned rule about how often such a reuse was safe. A LightGBM verifier turns this into an expected benefit, and "
     "the answer is served only if it clears a threshold. Offline, patterns and rules are re-mined every day from past "
     "traffic only.", 10),
    ("findings_top", "Finding: a similarity cache answers 56.3% of near-identical requests wrongly — 75.7% when the request "
                     "depends on the conversation, 37.1% when it is self-contained.",
     "First, the finding behind the project. When a new request is almost identical to a cached one, a standard similarity "
     "cache would still serve a wrong answer 56 percent of the time. For follow-ups, corrections and continuations it is "
     "wrong about 76 percent of the time, against 37 percent for self-contained requests.", 8),
    ("findings_chart", "Similarity is necessary but not sufficient: among near-identical requests, the role of the turn decides.",
     "In this chart, each group is a similarity band and each colour is the type of turn. Even at the highest similarity, "
     "follow-ups and corrections are mostly wrong. Behavior, not similarity, decides whether reuse is safe.", 7),
    ("replay_play", "Replay of the held-out week: every request goes through three policies, each with its own cache.",
     "Now the replay. We stream the held-out week through three policies side by side: a fixed similarity threshold like "
     "GPTCache, a learned verifier that knows each turn's dialogue act, and our version with mined behavioral patterns. "
     "The counters show the share of requests served from cache and how many of those were wrong.", 24),
    ("replay_mid", "Red = a wrong cached answer. Here the per-turn model serves wrong answers that the pattern-aware policy refuses.",
     "Red cells are wrong cached answers. At this point the per-turn model served wrong answers that the pattern-aware "
     "policy refused, because the mined patterns flag these situations as unsafe.", 8),
    ("replay_end", "End of the week: 0.02% vs 4.62% vs 4.49% of requests served at ≤10% wrong answers — about 240× the standard cache.",
     "At the end of the week, the fixed threshold has served only 0.02 percent of requests, while the behavior-aware "
     "policies serve about 4.5 percent at the same error level. That is roughly 240 times more, and these are exactly the "
     "numbers in our report.", 9),
    ("rules", "Mined rules make every decision explainable: reuse from a correction chain was never acceptable; "
              "fresh question to fresh question is the safest.",
     "These are some of the behavioral rules the system mined. Answering a fresh question with an answer that came out of a "
     "chain of corrections was never acceptable. Follow-ups reused from other follow-ups were acceptable only two to three "
     "percent of the time, while fresh question to fresh question is the safest reuse. A similarity score cannot express "
     "any of this.", 8),
    ("inspect_blocked", "Why was this blocked? The texts are identical (similarity 1.0), but the cached answer came from "
                        "another user's follow-up chain.",
     "The inspector explains individual decisions. Here the new request and the cached one are word for word identical. "
     "But the cached answer was produced as a follow-up inside someone else's conversation.", 8),
    ("inspect_rule", "Mined rule: this kind of reuse was acceptable only 4% of the time. The judge agrees. P3 served it; P4 refused.",
     "Our mined rule says this kind of reuse was acceptable only four percent of the time in the past, and the judge "
     "confirms it would be wrong. The per-turn model served it; the pattern-aware policy blocked it.", 8),
    ("inspect_served", "And when reuse is safe, the system serves it — fewer model calls, same answer quality.",
     "And when reuse is safe, the pattern-aware policy serves it, saving a model call without hurting answer quality.", 6),
    ("operating", "Operators choose their error budget: behavior-aware admission leads at every level.",
     "Gateway operators can choose how many wrong answers they tolerate. At five, ten or twenty percent, the behavior-aware "
     "policies serve far more than similarity thresholds.", 10),
    ("live", "Live service: a repeated fresh question is served from cache; “make it shorter” is a follow-up and is blocked.",
     "Finally, the live engine with three thousand real cached entries. A repeated fresh question is served from cache. "
     "Make it shorter is recognised as a follow-up and blocked, even though similar text exists in the cache. And another "
     "common fresh question is again served instantly.", 14),
    ("api", "A real REST service: POST /admit before a model call, POST /record after — 43 ms per decision on a laptop CPU.",
     "The same engine runs as a REST service with OpenAPI documentation. A gateway calls admit before forwarding a request "
     "and record after the model answers. Each decision takes about 43 milliseconds on a laptop.", 7),
    ("savings", "Projected savings over a standard semantic cache at the same ≤10% error: up to ₹1.95 crore a year at "
                "100M requests a month.",
     "What is this worth? Per million requests, our method avoids about forty-four thousand seven hundred model calls, "
     "against about one hundred and ninety for a standard cache at the same error rate. At the price we actually paid per "
     "call, that is about one point nine five lakh rupees a year for a startup with a million requests a month, and about "
     "one point nine five crore rupees a year for an enterprise at one hundred million.", 9),
    ("end", "", "Behavior, not similarity, decides whether a cached answer is safe. Our system serves about 240 times more "
                "requests than a standard cache at the same error rate, and stops wrong reuse on corrections. Thank you.", 7),
]


# speaks every narration line to a wav file with the built-in windows voice; returns each clip's length in seconds
def narrate(folder: Path) -> list[float]:
    folder.mkdir(parents=True, exist_ok=True)
    jobs = [{"text": s[2], "path": str(folder / f"{i:02d}.wav")} for i, s in enumerate(SCENES)]
    (folder / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
    ps = (f"Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$s.SelectVoice('{VOICE}'); $s.Rate = 0; "
          f"foreach ($j in (Get-Content -Raw -Encoding UTF8 '{folder / 'jobs.json'}' | ConvertFrom-Json)) "
          "{ $s.SetOutputToWaveFile($j.path); $s.Speak($j.text) }; $s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    lengths = []
    for j in jobs:
        with wave.open(j["path"]) as w:
            lengths.append(w.getnframes() / w.getframerate())
    return lengths


# full-screen title or closing card drawn over the page
def card(page, heading: str, lines: list[str]):
    html = "".join(f"<div style='font-size:24px;margin-top:18px;opacity:.9'>{l}</div>" for l in lines)
    page.evaluate("""([h, body]) => {
        let d = document.getElementById('demo-card') || document.createElement('div');
        d.id = 'demo-card';
        d.style.cssText = 'position:fixed;inset:0;z-index:1000000;background:#572314;color:#fff;display:flex;'
            + 'flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:80px;'
            + 'font-family:Segoe UI,Arial,sans-serif';
        d.innerHTML = `<div style='font-size:44px;font-weight:700;line-height:1.25'>${h}</div>${body}`;
        document.body.appendChild(d);
    }""", [heading, html])


# full-screen slide with a heading and one figure from the results, used for explanation scenes
def figure_slide(page, heading: str, path: Path):
    import base64

    data = base64.b64encode(path.read_bytes()).decode()
    page.set_content(f"""<html><body style='margin:0;background:#fff;font-family:Segoe UI,Arial,sans-serif'>
        <div style='padding:26px 40px 0;font-size:34px;font-weight:700;color:#572314'>{heading}</div>
        <div style='display:flex;justify-content:center;align-items:center;height:{H - 200}px'>
        <img src='data:image/png;base64,{data}' style='max-width:{W - 120}px;max-height:{H - 220}px'></div></body></html>""")


# full-screen slide with the projected savings table, read from the results
def savings_slide(page):
    import pandas as pd

    sv = pd.read_csv(Path(__file__).resolve().parent.parent / "results" / "savings_projection.csv")
    sv = sv[sv["wrong_reuse_level"] == 10]

    def inr(v):
        return f"₹{v / 1e7:.2f} crore" if v >= 1e7 else (f"₹{v / 1e5:.2f} lakh" if v >= 1e5 else f"₹{v:,.0f}")

    cell = "<td style='padding:14px;border-bottom:1px solid #ddd;text-align:center'>"
    rows = ""
    for n, label in [(1_000_000, "Startup · 1M requests/month"), (10_000_000, "Mid-size · 10M requests/month"),
                     (100_000_000, "Enterprise · 100M requests/month")]:
        pr = sv[(sv["requests_per_month"] == n) & sv["tier"].str.startswith("premium")].iloc[0]
        bu = sv[(sv["requests_per_month"] == n) & sv["tier"].str.startswith("budget")].iloc[0]
        rows += (f"<tr>{cell}{label}</td>{cell}{pr['calls_avoided_month']:,.0f}</td>{cell}{inr(pr['saving_inr_year'])}</td>"
                 f"{cell}{inr(bu['saving_inr_year'])}</td></tr>")
    page.set_content(f"""<html><body style='margin:0;background:#fff;font-family:Segoe UI,Arial,sans-serif;color:#1a1a1a'>
        <div style='padding:30px 50px 10px;font-size:34px;font-weight:700;color:#572314'>Projected savings vs a standard semantic cache</div>
        <div style='padding:0 50px;font-size:20px;color:#555'>Same ≤10% wrong-answer level · hit rates measured on the held-out week · real gateway prices</div>
        <table style='margin:40px 50px;border-collapse:collapse;font-size:26px;width:{W - 100}px'>
        <tr style='background:#572314;color:#fff'><th style='padding:14px'>User scale</th><th>Extra calls avoided / month</th>
        <th>Premium model / year</th><th>Budget model / year</th></tr>{rows}</table></body></html>""")


# caption bar at the bottom of the screen (empty text removes it)
def caption(page, text: str):
    page.evaluate("""(t) => {
        let d = document.getElementById('demo-cap');
        if (!t) { if (d) d.remove(); return; }
        if (!d) { d = document.createElement('div'); d.id = 'demo-cap'; document.body.appendChild(d); }
        d.style.cssText = 'position:fixed;left:50%;bottom:28px;transform:translateX(-50%);max-width:82%;z-index:999999;'
            + 'background:rgba(20,20,20,.86);color:#fff;font:600 24px/1.35 Segoe UI,Arial,sans-serif;padding:16px 26px;'
            + 'border-radius:12px;box-shadow:0 6px 24px rgba(0,0,0,.25);text-align:center';
        d.textContent = t;
    }""", text)


# waits until streamlit has finished rerunning the page
def settle(page, extra=1.0):
    page.wait_for_selector('[data-testid="stApp"][data-test-script-state="notRunning"]', timeout=900000)
    time.sleep(extra)


# opens a demo page and waits for it to render
def open_app(page, query: str):
    page.goto(APP + query)
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=900000)
    settle(page, 1.5)


# scrolls the streamlit main area smoothly by a number of pixels
def scroll(page, pixels: int, steps: int = 12):
    page.mouse.move(W * 0.62, H * 0.5)
    for _ in range(steps):
        page.mouse.wheel(0, pixels / steps)
        time.sleep(0.06)


# types one request into the live page and waits for its decision
def ask(page, text: str, n: int):
    box = page.get_by_label("Request")
    box.click()
    box.fill("")
    page.keyboard.type(text, delay=45)
    box.press("Enter")
    settle(page, 0.4)
    page.get_by_role("button", name="Send").click()
    page.wait_for_function(f"document.body.innerText.split('Latency').length > {n}", timeout=120000)
    settle(page, 0.5)


# loads the live engine once before recording so the video never waits on model loading
def warm_up(browser):
    page = browser.new_page()
    open_app(page, "?page=Live%20admission")
    page.get_by_label("Request").wait_for(timeout=900000)
    page.close()


# plays every scene in order, holding each for its narration, and returns when each one started
def record(browser, lengths: list[float]) -> tuple[Path, list[float]]:
    ctx = browser.new_context(viewport={"width": W, "height": H}, record_video_dir=str(OUT / "raw"),
                              record_video_size={"width": W, "height": H})
    page = ctx.new_page()
    t0 = time.monotonic()
    starts = []

    def hold(i, since):
        rest = max(lengths[i] + 0.8, SCENES[i][3]) - (time.monotonic() - since)
        if rest > 0:
            time.sleep(rest)

    for i, (name, cap, _, _) in enumerate(SCENES):
        if name == "title":
            page.set_content("<html><body style='margin:0;background:#572314'></body></html>")
            card(page, TITLE, ["Final Review Demo", TEAM])
        elif name == "architecture":
            figure_slide(page, "How the admission engine works", FIGS / "block_diagram.png")
        elif name == "rules":
            figure_slide(page, "Mined behavioral rules: when is reuse acceptable?", FIGS / "rules_bar.png")
        elif name == "savings":
            savings_slide(page)
        elif name == "findings_top":
            open_app(page, "?page=Findings")
        elif name == "replay_play":
            open_app(page, "?page=Replay&step=60")
        elif name == "replay_mid":
            open_app(page, "?page=Replay&step=452")
            scroll(page, 380)
        elif name == "replay_end":
            open_app(page, "?page=Replay&step=2424")
        elif name == "inspect_blocked":
            open_app(page, "?page=Inspect%20a%20decision&filter=0&pick=0")
        elif name == "inspect_served":
            open_app(page, "?page=Inspect%20a%20decision&filter=1&pick=3")
        elif name == "operating":
            open_app(page, "?page=Operating%20point&target=5")
        elif name == "live":
            open_app(page, "?page=Live%20admission")
        elif name == "api":
            page.goto(API)
            page.wait_for_selector(".opblock", timeout=60000)
            page.click("text=/admit")
            time.sleep(1)
        elif name == "end":
            card(page, "Behavior, not similarity, decides safe reuse",
                 ["~240× more requests served than a standard semantic cache at the same error",
                  "Wrong reuse on corrections: 66.7% → 0% · 43 ms per decision",
                  "github.com/arnnnavvvvv/llm-cache-pattern-mining"])
        caption(page, cap)
        since = time.monotonic()
        starts.append(since - t0)
        if name == "findings_chart":
            scroll(page, 520)
        elif name == "replay_play":
            page.get_by_text("Play", exact=True).click()
            time.sleep(max(lengths[i], SCENES[i][3]) - 1)
            page.goto("about:blank")
            open_app(page, "?page=Replay&step=1300")
            caption(page, cap)
        elif name == "replay_end":
            time.sleep(4)
            scroll(page, 700)
        elif name == "inspect_blocked":
            time.sleep(3)
            scroll(page, 250)
        elif name == "inspect_served":
            scroll(page, 300)
        elif name == "operating":
            time.sleep(3)
            for target in (10, 20):
                open_app(page, f"?page=Operating%20point&target={target}")
                caption(page, cap)
                time.sleep(2.5)
        elif name == "live":
            for n, q in enumerate(["Can you make some ASCII-art please?", "make it shorter",
                                   "Where can I use chatgpt 4 for free"], start=1):
                ask(page, q, n)
                caption(page, cap)
                time.sleep(1.5)
        if name != "inspect_rule":
            hold(i, since)
        else:
            scroll(page, 450)
            hold(i, since)
    video = Path(page.video.path())
    ctx.close()
    return video, starts


# lays every narration clip on one silent track at the second its scene started
def mix(folder: Path, starts: list[float], total: float) -> Path:
    rate, track = None, None
    for i, s in enumerate(starts):
        with wave.open(str(folder / f"{i:02d}.wav")) as w:
            rate = rate or w.getframerate()
            if track is None:
                track = np.zeros(int((total + 2) * rate), dtype=np.int16)
            clip = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        a = int((s + 0.3) * rate)
        b = min(len(track), a + len(clip))
        track[a:b] = clip[: b - a]
    out = folder / "narration.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(track.tobytes())
    return out


# encodes the recording to mp4, once with narration and once captions-only
def encode(video: Path, narration: Path):
    import imageio_ffmpeg

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    common = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "22", "-r", "25"]
    subprocess.run([ff, "-y", "-i", str(video), "-i", str(narration), *common, "-c:a", "aac", "-b:a", "128k",
                    "-shortest", str(OUT / "demo_narrated.mp4")], check=True, capture_output=True)
    subprocess.run([ff, "-y", "-i", str(video), *common, "-an", str(OUT / "demo_captions_only.mp4")], check=True,
                   capture_output=True)


# runs the whole recording
def main():
    # playwright keeps its video encoder on d:, since c: has no space
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", r"D:\Capstone\.cache\ms-playwright")
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    lengths = narrate(OUT / "audio")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        warm_up(browser)
        video, starts = record(browser, lengths)
        browser.close()
    total = starts[-1] + max(lengths[-1], SCENES[-1][3]) + 1
    encode(video, mix(OUT / "audio", starts, total))
    (OUT / "scene_starts.json").write_text(json.dumps(dict(zip([s[0] for s in SCENES], starts)), indent=1))
    print("done", round(total), "s ->", OUT)


if __name__ == "__main__":
    main()
