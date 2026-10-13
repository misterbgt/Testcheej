"""The console's hub for the web version (runs in Pyodide, in a browser worker).

It does for the iPhone page what app/hub.py does for the laptop app, with the same
shared part (app/core.py: settings, history, screen messages, the sewadar's commands):
it runs the search and decides when the words heard get a full check or a quick one.
The sound is turned into words in the browser (asr-worker.js); the engine (engine/,
engine_ext/) is the same as the laptop app's. Every method returns the messages for the
page as JSON, exactly as the laptop app sends them over its websocket. Pictures and the
recent messages stay in the page; only their names come here.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from app import VERSION, VERSION_NAME
from app.core import HOP_S, MSG_IMAGES_KEPT, MSG_TEXTS_KEPT, QUICK_HOP_S, HubCore  # noqa: F401
from engine_ext.console_session import Resources
from engine_ext.search import GurbaniSearch

APP_VERSION = "web-" + VERSION
RECENT_AFTER_S = 12.0                               # kirtan: the last 10 s decide the line once there is enough sound


class WebHub(HubCore):
    def __init__(self, repo: str, settings_json: str = "{}", texts_json: str = "[]"):
        t0 = time.time()
        super().__init__()
        self.res = Resources(Path(repo))
        self.search = GurbaniSearch(self.res.corpus, self.res.meta, self.res.banis, self.res.phrase.first_line)
        try:
            self.apply_settings(json.loads(settings_json or "{}"))
        except ValueError:
            pass
        try:
            self.recent_texts = [t for t in json.loads(texts_json or "[]") if isinstance(t, str)][:MSG_TEXTS_KEPT]
        except ValueError:
            self.recent_texts = []
        self.recent_images: list[str] = []
        self.sess = self.new_session()
        self.last_main = self.last_quick = -1e9
        self.load_s = time.time() - t0

    def _out(self, msgs) -> str:
        msgs = list(msgs or [])
        if self.take(msgs):
            msgs.append(self.history_msg())
        return json.dumps(msgs, ensure_ascii=False)

    # ------------------------------------------------------------------ messages
    def hello(self) -> str:
        msgs = [{"type": "hello", "banis": self.banis(), "version": APP_VERSION, "version_name": VERSION_NAME},
                {"type": "settings", "settings": self.settings}, self.history_msg(), self.screen_msg_msg()]
        if self.last_track:
            msgs.append(self.last_track)
        msgs += self.sess._emit()
        return self._out(msgs)

    def screen_msg_msg(self):
        return {"type": "screen_msg", "msg": self.screen_msg, "recent_images": self.recent_images,
                "recent_texts": self.recent_texts}

    def remember_text(self, text):
        self.recent_texts = ([text] + [t for t in self.recent_texts if t != text])[:MSG_TEXTS_KEPT]

    def image_used(self, name):
        self.recent_images = ([name] + [n for n in self.recent_images if n != name])[:MSG_IMAGES_KEPT]

    def forget_image(self, name):
        self.recent_images = [n for n in self.recent_images if n != name]

    # ------------------------------------------------------------------ sound
    def audio(self, t: float, t20: str, t10: str, t45: str) -> str:
        """New words heard up to t seconds: the last 20, 10 and 4.5 seconds of them.
        A full check every few seconds (as the laptop app), a quick one in between."""
        sess = self.sess
        msgs = list(sess.tick(t) or [])
        if t - self.last_main >= self.hop() and t >= 4.0:
            self.last_main = self.last_quick = t
            if sess.mode == "kirtan":
                msgs += sess.process(t20, t, recent=t10 if t > RECENT_AFTER_S else None)
            else:
                msgs += sess.process(t10, t)
        elif sess.track and sess.wants_quick() and t - self.last_quick >= QUICK_HOP_S - 0.2 and t >= 4.5:
            self.last_quick = t
            msgs += sess.quick_line(t45, t) or []
        return self._out(msgs)

    # ------------------------------------------------------------------ commands
    def on_reset(self):
        self.last_main = self.last_quick = -1e9

    def command(self, cjson: str) -> str:
        c = json.loads(cjson)
        cmd = c.get("cmd")
        if cmd == "hello":                        # a page (re)connected: everything it needs
            return self.hello()
        if cmd == "search":
            q, mode = str(c.get("q", ""))[:80], str(c.get("mode", "auto"))
            return self._out([{"type": "search_results", "id": c.get("id"), "q": q, **self.search.search(q, mode)}])
        return self._out(super().command(c))
