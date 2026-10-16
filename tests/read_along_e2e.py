"""End-to-end test for the Read Along player on the built site, in headless Chromium.

Builds the site, serves it locally and plays a real note. ElevenLabs is simulated:
every request to api.elevenlabs.io is answered with silent audio plus exact
per-character timings, so the test needs no API key and costs no credits.

Setup (once):
    pip install playwright && playwright install chromium

Run from the repo root (after `python3 quiz/build_web.py`, which mkdocs needs):
    python3 tests/read_along_e2e.py      # exits 0 when every check passes
"""
import base64
import functools
import http.server
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import threading
import wave

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTE = "ml/concepts/normalisation/"  # maths right after the first ##, then a code block
HUB = "ml/"
CHARS_PER_SEC = 60  # speaking rate of the fake voice (fast, so the test stays quick)
CORS = {"Access-Control-Allow-Origin": "*"}

results = []


def check(cond, label):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + label)


def silent_wav(seconds):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(8000)
        w.writeframes(b"\x80" * int(8000 * seconds))
    return base64.b64encode(buf.getvalue()).decode()


class FakeElevenLabs:
    """Answers the endpoints the player calls and records every text it was asked to speak."""

    def __init__(self):
        self.texts = []

    def __call__(self, route, request):
        url = request.url
        if url.endswith("/v1/voices"):
            body = {"voices": [{"voice_id": "v_test", "name": "Test", "labels": {}}]}
            return route.fulfill(status=200, content_type="application/json", headers=CORS, body=json.dumps(body))
        if url.endswith("/v1/user/subscription"):
            body = {"character_count": 0, "character_limit": 10000}
            return route.fulfill(status=200, content_type="application/json", headers=CORS, body=json.dumps(body))
        if "/with-timestamps" in url:
            text = json.loads(request.post_data)["text"]
            self.texts.append(text)
            dur = max(0.3, len(text) / CHARS_PER_SEC)
            starts = [i * dur / len(text) for i in range(len(text))]
            body = {"audio_base64": silent_wav(dur), "alignment": {"character_start_times_seconds": starts}}
            return route.fulfill(status=200, content_type="application/json", headers=CORS, body=json.dumps(body))
        return route.fulfill(status=404, headers=CORS, body="")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(directory):
    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}/"


def open_page(browser, base, path, width=1200):
    page = browser.new_page(viewport={"width": width, "height": 800})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    fake = FakeElevenLabs()
    page.route("https://api.elevenlabs.io/**", fake)
    page.add_init_script("try{localStorage.setItem('readalong.elKey','sk_test')}catch(e){}")
    page.goto(base + path)
    page.wait_for_function("document.querySelector('.katex')", timeout=10000)
    return page, fake, errors


def status(page):
    return page.text_content('[data-ra="status"]') or ""


def play_until_paused(page):
    """Press Play and wait for the next "Pause at blocks" stop; return what it paused at."""
    page.click('[data-ra="play"]')
    page.wait_for_function("document.querySelector('[data-ra=status]').textContent.startsWith('Paused at')",
                           timeout=20000)
    return status(page)


def test_desktop(browser, base):
    print("\n# Desktop")
    hub = browser.new_page()
    hub.goto(base + HUB)
    check(hub.locator(".ra-listen").count() == 0, "section hubs get no Listen button")
    hub.close()

    page, fake, errors = open_page(browser, base, NOTE)
    check(page.locator(".ra-listen").count() == 1, "a content page gets one Listen button")
    check(page.locator(".ra-player").count() == 0, "the player is not built until it is opened")

    page.keyboard.press("Space")
    page.wait_for_timeout(300)
    check(not fake.texts, "Space does nothing while the player is closed")

    page.click(".ra-listen")
    check(page.is_visible(".ra-player"), "Listen opens the player bar")
    check("sentences" in status(page) and "credits" in status(page), "the player shows the sentence count and cost")
    check(page.is_hidden('[data-ra="settings"]'), "settings stay closed when a key is already saved")

    page.check('[data-ra="pauseBlocks"]')
    first_stop = play_until_paused(page)
    spoken = " ".join(fake.texts)
    check(spoken.startswith("Normalisation Layers"), "reading starts at the page title")
    check("Feature scaling" in spoken, "list items are read")
    check("feature-scaling" not in spoken.lower() and "#" not in spoken, "no link targets or markup are read")
    at_first_formula = page.evaluate("document.querySelector('div.arithmatex').classList.contains('stop-here')")
    check(first_stop.startswith("Paused at a formula") and at_first_formula,
          "Pause at blocks stops at the first display formula")

    stops = [first_stop]
    while not stops[-1].startswith("Paused at a code block") and len(stops) < 5:
        stops.append(play_until_paused(page))
    check(stops[-1].startswith("Paused at a code block"), "it goes on to stop before the code block")
    spoken = " ".join(fake.texts)
    check("square root of" in spoken and "epsilon" in spoken, "KaTeX formulas are spoken from their TeX source")
    check("LayerNorm" not in spoken, "code blocks are not read")
    check(page.evaluate("document.querySelector('article').classList.contains('active')"),
          "the article is in reading mode")

    page.click('[data-ra="close"]')
    check(page.is_hidden(".ra-player"), "Close hides the player")
    check(not page.evaluate("document.querySelector('article').classList.contains('active')"),
          "closing clears the highlight")
    check(not errors, "no script errors" + (f": {errors}" if errors else ""))
    page.close()


def test_mobile(browser, base):
    print("\n# Mobile (collapsed sections)")
    page, fake, errors = open_page(browser, base, NOTE, width=420)
    hidden_before = page.locator(".collapsible-section[hidden]").count()
    check(hidden_before > 1, "sections start collapsed on a phone")
    page.click(".ra-listen")
    page.evaluate("""() => { const s = document.querySelector('[data-ra=scrub]');
        s.value = Math.floor(s.max * 0.6); s.dispatchEvent(new Event('change')); }""")
    page.click('[data-ra="play"]')
    page.wait_for_function("CSS.highlights.get('tts-word').size > 0", timeout=20000)
    in_hidden = page.evaluate("""() => {
        const r = CSS.highlights.get('tts-sentence').values().next().value;
        const n = r.startContainer.nodeType === 1 ? r.startContainer : r.startContainer.parentElement;
        return !!n.closest('[hidden]'); }""")
    check(not in_hidden, "the section being read is opened")
    opened = page.locator('h2.is-collapsible[aria-expanded="true"]').count()
    check(opened >= 1, "its heading shows as expanded")
    check(page.locator(".collapsible-section[hidden]").count() < hidden_before, "only reading opened it")
    page.click('[data-ra="close"]')
    check(not errors, "no script errors" + (f": {errors}" if errors else ""))
    page.close()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["mkdocs", "build", "--strict", "--quiet", "--site-dir", tmp], cwd=ROOT, check=True)
        server, base = serve(tmp)
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
            for test in (test_desktop, test_mobile):
                try:
                    test(browser, base)
                except Exception as e:  # a crashed test counts as a failure, the rest still run
                    check(False, f"{test.__name__} crashed: {e}")
            browser.close()
        server.shutdown()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
