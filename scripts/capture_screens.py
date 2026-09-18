#!/usr/bin/env python3
"""Capture the README screenshots from a running local app.

    services/api/.venv/bin/python scripts/capture_screens.py

Needs the API on 8010 and the web dev server on 5173, and `pip install playwright`.
It drives the installed Edge (channel="msedge"), so there is no browser download.

Every shot is a real signed-in session against the real API - the same tokens the app
issues - rather than a mock, so what lands in docs/images is what a visitor actually sees.
The collaborative shot opens two browser contexts, because one player cannot demonstrate
two cursors.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

API = "http://localhost:8010"
WEB = "http://localhost:5173"
# The plan-update draft is captured against the deployment, because only there does the
# instance role reach Bedrock: a laptop with expired keys would label a real feature
# "offline rules" in the README.
LIVE = "https://d1fai7rdy6j53g.cloudfront.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "images"
VIEWPORT = {"width": 1280, "height": 860}


def login(username: str, password: str, api: str = API) -> dict:
    request = urllib.request.Request(
        f"{api}/auth/login", method="POST",
        data=json.dumps({"username": username, "password": password}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        d = json.load(response)
    return {"role": d["role"], "userId": d["user_id"], "name": d["display_name"],
            "token": d["token"], "refreshToken": d.get("refresh_token")}


def open_as(browser, session: dict, path: str, wait_for: str | None = None, settle: float = 2.0,
            base: str = WEB):
    """A fresh context per signer-in, so two learners never share one localStorage."""
    context = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
    page = context.new_page()
    page.goto(base, wait_until="domcontentloaded")
    page.evaluate("s => localStorage.setItem('alp.session', JSON.stringify(s))", session)
    page.goto(f"{base}{path}", wait_until="networkidle")
    if wait_for:
        page.wait_for_selector(wait_for, timeout=20000)
    time.sleep(settle)
    return context, page


MAX_WIDTH = 1600  # wider than GitHub renders a README image, and a quarter of the bytes


def shot(page, name: str, selector: str | None = None) -> None:
    """Capture at 2x, then down-sample to a size a repository should carry."""
    OUT.mkdir(parents=True, exist_ok=True)
    raw = OUT / f"{name}.raw.png"
    target = page.locator(selector) if selector else page
    target.screenshot(path=str(raw))

    from PIL import Image
    image = Image.open(raw).convert("RGB")
    if image.width > MAX_WIDTH:
        image = image.resize((MAX_WIDTH, round(image.height * MAX_WIDTH / image.width)),
                             Image.LANCZOS)
    final = OUT / f"{name}.jpg"
    image.save(final, "JPEG", quality=86, optimize=True, progressive=True)
    raw.unlink()
    print(f"[  ok  ] docs/images/{name}.jpg  {image.width}x{image.height}  "
          f"{final.stat().st_size // 1024}KB")


def main() -> int:
    sam = login("sam", "otter123")
    mia = login("mia", "otter123")
    rivera = login("rivera", "teach123")
    jordan = login("jordan", "family123")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)

        # 1. The landing page, signed out.
        context = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page = context.new_page()
        page.goto(WEB, wait_until="networkidle")
        time.sleep(2.5)
        shot(page, "landing")
        context.close()

        # 2. The practice path.
        context, page = open_as(browser, sam, "/student", ".path-layout")
        shot(page, "student-path")
        context.close()

        # 3. A quiz question: read-aloud, Capy, chunked passage.
        context, page = open_as(browser, sam, "/student/quest/main_idea", ".choices")
        shot(page, "student-quiz")
        context.close()

        # 4. Globe Trotters with two learners in the room and a teammate's cursor live.
        sam_ctx, sam_page = open_as(browser, sam,
                                    "/student/games/globe-trotters/group-activity-globe-01",
                                    ".globe-map", settle=3)
        mia_ctx, mia_page = open_as(browser, mia,
                                    "/student/games/globe-trotters/group-activity-globe-01",
                                    ".globe-map", settle=3)
        # Mia's pointer drifts over the Atlantic; Sam's screen should draw it.
        box = mia_page.locator(".globe-map").bounding_box()
        if box:
            mia_page.mouse.move(box["x"] + box["width"] * 0.36, box["y"] + box["height"] * 0.45)
            time.sleep(0.4)
            mia_page.mouse.move(box["x"] + box["width"] * 0.38, box["y"] + box["height"] * 0.48)
        time.sleep(2)
        # Frame the team bar (who is here now) together with the board.
        sam_page.evaluate("document.querySelector('.team-bar')?.scrollIntoView({block:'start'})")
        time.sleep(1)
        shot(sam_page, "game-globe")
        mia_ctx.close()
        sam_ctx.close()

        # 5. The teacher's learner page with a live AI plan-update draft, from the deployment.
        live_rivera = login("rivera", "teach123", api=f"{LIVE}/api")
        context, page = open_as(browser, live_rivera, "/teacher/learners/student-01",
                                ".plan-doc", base=LIVE)
        page.get_by_role("button", name="Ask Dori for a plan update idea").click()
        page.wait_for_selector(".plan-ai-draft", timeout=60000)
        time.sleep(2)
        shot(page, "teacher-plan", ".plan-ai-draft")
        context.close()

        # 6. The teacher's class roster.
        context, page = open_as(browser, rivera, "/teacher", ".learner-grid")
        shot(page, "teacher-class")
        context.close()

        # 7. The family view.
        context, page = open_as(browser, jordan, "/parent", ".profile-head", settle=3)
        shot(page, "family")
        context.close()

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
