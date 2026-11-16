"""UI tour — plays a short scripted game and screenshots every screen.

Usage (from the repo root, needs fastapi, uvicorn and httpx installed):

    python tools/ui_tour.py OUT_DIR                  # desktop, all screens
    python tools/ui_tour.py OUT_DIR --mobile         # 390px wide as well
    python tools/ui_tour.py OUT_DIR --only battle,shop

Writes OUT_DIR/<screen>.png (and <screen>.mobile.png) plus the HTML that was
captured. Prints one line per screen. Sessions live in a temp dir, so the
real web/sessions folder is not touched.

Screens: home, race, class, details, summary, location, location-large,
shop, shop-quests, inventory, travel, journal, saves, event, event-result,
battle, battle-hit (damage numbers mid-animation), victory, defeat.

The browser is headless Chrome through flatpak (override with --chrome "cmd").
"""

import argparse
import json
import random
import shlex
import socket
import subprocess
import sys
import tempfile
import threading
import time
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

import uvicorn  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import web.game_session as gs  # noqa: E402
from web.app import app  # noqa: E402

DEFAULT_CHROME = "flatpak run --filesystem={out} com.google.Chrome"
SIZES = {"": (1280, 1500), ".mobile": (390, 1500)}


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve_static(port):
    """Chrome loads CSS/JS/images from a real server; pages come from TestClient."""
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise RuntimeError("static server did not start")


class Tour:
    def __init__(self, out, port, chrome, mobile, only):
        self.out, self.port, self.chrome = out, port, chrome
        self.sizes = SIZES if mobile else {"": SIZES[""]}
        self.only = only
        self.sessions = Path(tempfile.mkdtemp(prefix="ui_tour_"))
        gs.SESSIONS_DIR = self.sessions
        self.client = TestClient(app)

    # -- session file helpers -------------------------------------------------
    def edit(self, fn):
        path = next(self.sessions.glob("*.json"))
        data = json.loads(path.read_text())
        fn(data)
        path.write_text(json.dumps(data))

    @staticmethod
    def _where(pred):
        """First (act number, location name, area id) whose area matches pred."""
        for act in gs.get_campaign()["acts"]:
            for loc in act["locations"]:
                for area in loc["areas"]:
                    if pred(area):
                        return act["number"], loc["name"], area["id"]
        raise LookupError("no matching area")

    # -- capture --------------------------------------------------------------
    def shot(self, name, url, head="", budget=4000):
        """Capture `url`. `head` is extra markup for <head>; `budget` is how long the page runs (ms)."""
        if self.only and name not in self.only:
            return
        resp = self.client.get(url)
        html = resp.text.replace(
            "<head>", f'<head><base href="http://127.0.0.1:{self.port}/">{head}', 1)
        page = self.out / f"{name}.html"
        page.write_text(html)
        for suffix, (w, h) in self.sizes.items():
            png = self.out / f"{name}{suffix}.png"
            cmd = shlex.split(self.chrome.format(out=self.out)) + [
                "--headless", "--hide-scrollbars", f"--virtual-time-budget={budget}",
                f"--window-size={w},{h}", f"--screenshot={png}", f"file://{page}"]
            subprocess.run(cmd, capture_output=True, timeout=90)
            status = "ok" if png.exists() else "FAILED"
            print(f"{name}{suffix}: {status} ({resp.status_code} {resp.url.path})")

    # -- script ---------------------------------------------------------------
    def run(self, class_name):
        c = self.client
        self.shot("home", "/")
        self.shot("race", "/character/new")
        c.post("/character/race", data={"race": "Human"})
        self.shot("class", "/character/class")
        c.post("/character/class", data={"class_name": class_name})
        self.shot("details", "/character/details")
        c.post("/character/create", data={
            "name": "Aldric", "weapon": "Longsword", "armor": "Chain Mail",
            "portrait": "/static/images/player_fighter.png"})
        self.shot("summary", "/character/summary")

        def kit(data):
            ch = data["character"]
            potion = {"name": "Healing Potion", "description": "", "type": "potion", "healing_amount": 20}
            ch["inventory"] += [potion, dict(potion), dict(potion),
                                {"name": "Greatsword", "type": "weapon"}, {"name": "Dagger", "type": "weapon"},
                                {"name": "Leather", "type": "armor"}]
            ch["gold"] = 180
            ch["level"] = 4          # unspent ASI points show the nav badge
            ch["current_hit_points"] = max(1, int(ch["max_hit_points"] * 0.6))
        self.edit(kit)

        self.shot("location", "/game")
        town = self._where(lambda a: True)
        self.edit(lambda d: d.update(area_id=self._where(lambda a: "shop" in str(a.get("special", "")))[2]))
        self.edit(lambda d: d.update(act_num=3, location_name="The Convergence", area_id="courtyard"))
        self.shot("location-large", "/game")
        self.edit(lambda d: d.update(act_num=town[0], location_name=town[1]))
        self.shot("shop", "/shop")
        self.shot("shop-quests", "/shop?tab=quests")
        self.shot("inventory", "/inventory")
        self.shot("travel", "/game/travel")
        self.shot("journal", "/game/journal")
        self.edit(lambda d: d.update(area_id=town[2]))
        c.post("/saves/save")
        self.shot("saves", "/saves")

        # Event: explore somewhere without monsters until one fires
        for _ in range(40):
            r = c.post("/game/explore")
            if r.url.path == "/game/event":
                break
            if r.url.path.startswith("/battle"):
                self.edit(lambda d: d["battle"].update(is_active=False))
        self.shot("event", "/game/event")
        r = c.get("/game/event")
        if "event-choice" in r.text:
            import re
            m = re.search(r'name="choice"[^>]*value="([^"]+)"', r.text)
            if m:
                c.post("/game/event/choose", data={"choice": m.group(1)})
                self.shot("event-result", "/game/event")
                c.post("/game/event/continue")
        self.edit(lambda d: (d.update(pending_event=None, event_result=None),
                             d["battle"].update(is_active=False)))

        # Battle: move to the first area with monsters
        wilds = self._where(lambda a: a.get("monster_types"))
        self.edit(lambda d: d.update(act_num=wilds[0], location_name=wilds[1], area_id=wilds[2]))
        c.get("/battle/start")
        self.edit(lambda d: d["battle"]["monster"].update(
            hp=max(d["battle"]["monster"]["max_hp"], 40), max_hp=max(d["battle"]["monster"]["max_hp"], 40)))
        c.post("/battle/attack")
        c.post("/battle/defend")
        self.shot("battle", "/battle")
        # Pretend the previous render had more HP on both sides, to show the hit feedback
        # Registered before main.js, so it runs first on DOMContentLoaded
        seed = ("<script>document.addEventListener('DOMContentLoaded',function(){"
                "var q=function(s){return document.querySelector(s)},r=q('.battle-arena');"
                "sessionStorage.setItem('battleHp',JSON.stringify({key:r.dataset.battleKey,round:1,"
                "player:+q('[data-combatant=player]').dataset.hp+3,"
                "monster:+q('[data-combatant=monster]').dataset.hp+9}))})</script>")
        self.shot("battle-hit", "/battle", head=seed, budget=450)

        self.edit(lambda d: d["battle"]["monster"].update(hp=1))
        for _ in range(30):
            # No redirect following: the victory page shows its rewards only once
            r = c.post("/battle/attack", follow_redirects=False)
            if r.headers.get("location", "").rstrip("/") != "/battle":
                break
        self.shot("victory", "/battle/victory")

        c.get("/game")
        c.get("/battle/start")
        self.edit(lambda d: (d["character"].update(current_hit_points=1),
                             d["battle"]["monster"].update(hp=500, max_hp=500, str_mod=10, proficiency=20)))
        for _ in range(40):
            if c.post("/battle/defend").url.path != "/battle":
                break
        self.shot("defeat", "/battle/defeat")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("out", type=Path, help="directory for PNG and HTML output")
    p.add_argument("--mobile", action="store_true", help="also capture at 390px width")
    p.add_argument("--only", default="", help="comma-separated screen names")
    p.add_argument("--class", dest="class_name", default="Fighter")
    p.add_argument("--chrome", default=DEFAULT_CHROME, help="browser command; {out} is the output dir")
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    random.seed(args.seed)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    port = _free_port()
    _serve_static(port)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    Tour(out, port, args.chrome, args.mobile, only).run(args.class_name)


if __name__ == "__main__":
    main()
