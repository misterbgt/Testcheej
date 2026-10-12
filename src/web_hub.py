"""The console's hub for the web version (runs in Pyodide, in a browser worker).

It does for the iPhone page what console_app.py does for the laptop app: keeps the
settings, the history and the screen messages, carries out the commands, runs the
search, and decides when the words heard get a full check or a quick one. The sound is
turned into words in the browser (asr-worker.js); the engine (engine/, engine_ext/) is
the same as the laptop app's. Every method returns the messages for the page as JSON,
exactly as the laptop app sends them over its websocket.
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from engine_ext.console_session import ConsoleSession, Resources
from engine_ext.search import GurbaniSearch

log = logging.getLogger("web")

APP_VERSION = "web-2026-10-12a"
VERSION_NAME = "ਅ੧"
HOP_S = {"kirtan": 5.0, "paath": 3.0, "akv": 3.0}     # as console_app.py: seconds between full checks
QUICK_HOP_S = 1.5                                   # quick checks for words of another line
RECENT_AFTER_S = 12.0                               # kirtan: the last 10 s decide the line once there is enough sound
HISTORY_AFTER_S = 15
MSG_TEXTS_KEPT = MSG_IMAGES_KEPT = 8
IMAGE_NAME = re.compile(r"[0-9a-f]{16}\.(png|jpg|gif)")

# as console_app.py (the overlay and casting settings are kept so the pages work unchanged)
DEFAULT_SETTINGS = {"en": True, "tr": False, "prev": False, "next": True, "predict": True, "phone": True,
                    "notice": True, "learn": True,
                    "fs_g": 100, "fs_prev": 100, "fs_next": 100, "fs_en": 100, "fs_tr": 100, "fs_all": 100,
                    "ov_pos": "top-middle", "ov_width": 80, "ov_bg": "#0F1A30", "ov_gc": "#FFFFFF",
                    "ov_tc": "#F2D9A6", "ov_op": 0, "ov_gs": 100, "ov_ts": 100, "ov_en": True,
                    "bani_length": "long"}
SIZE_LIMITS = {"fs_all": (40, 100), "ov_op": (0, 100), "ov_width": (30, 100)}
CHOICES = {"ov_pos": ("top-left", "top-middle", "top-right", "bottom-left", "bottom-middle", "bottom-right"),
           "bani_length": ("short", "medium", "long", "extra long")}


def bani_menu(res):
    """The banis in the order they are listed: each one's lengths together, shortest first."""
    out, done = [], set()
    for b in res.banis.values():
        if b["id"] in done:
            continue
        for v in res.variants(b["id"]):
            out.append(res.banis[v])
            done.add(v)
    return out


class WebHub:
    def __init__(self, repo: str, settings_json: str = "{}", texts_json: str = "[]"):
        t0 = time.time()
        self.res = Resources(Path(repo))
        self.search = GurbaniSearch(self.res.corpus, self.res.meta, self.res.banis, self.res.phrase.first_line)
        self.settings = dict(DEFAULT_SETTINGS)
        try:
            self._apply_settings(json.loads(settings_json or "{}"))
        except ValueError:
            pass
        try:
            self.recent_texts = [t for t in json.loads(texts_json or "[]") if isinstance(t, str)][:MSG_TEXTS_KEPT]
        except ValueError:
            self.recent_texts = []
        self.recent_images: list[str] = []
        self.screen_msg = None
        self.history: list[dict] = []
        self._on_screen = (None, 0.0)
        self.last_track = self.last_state = None
        self.sess = self._new_session()
        self.last_main = self.last_quick = -1e9
        self.load_s = time.time() - t0

    # ------------------------------------------------------------------ session
    def _new_session(self) -> ConsoleSession:
        sess = ConsoleSession(self.res, mode="kirtan")
        self._configure(sess)
        return sess

    def _configure(self, sess):
        sess.predict_enabled = bool(self.settings.get("predict", True))
        sess.bani_length = self.settings.get("bani_length", "long")
        sess._teacher().enabled = bool(self.settings.get("learn", True))

    def _out(self, msgs) -> str:
        msgs = list(msgs or [])
        for m in msgs:
            if m["type"] == "track":
                self.last_track = m
            elif m["type"] == "state":
                self.last_state = m
        if any(m["type"] == "state" and self._note_history(m) for m in list(msgs)):
            msgs.append(self.history_msg())
        return json.dumps(msgs, ensure_ascii=False)

    # ------------------------------------------------------------------ messages
    def hello(self) -> str:
        banis = [{"id": b["id"], "name": b["name"], "name_gurmukhi": b["name_gurmukhi"]} for b in bani_menu(self.res)]
        msgs = [{"type": "hello", "banis": banis, "version": APP_VERSION, "version_name": VERSION_NAME},
                {"type": "settings", "settings": self.settings}, self.history_msg(), self.screen_msg_msg()]
        if self.last_track:
            msgs.append(self.last_track)
        msgs += self.sess._emit()
        return self._out(msgs)

    def history_msg(self):
        return {"type": "history", "items": self.history[:100]}

    def screen_msg_msg(self):
        return {"type": "screen_msg", "msg": self.screen_msg, "recent_images": self.recent_images,
                "recent_texts": self.recent_texts}

    def _note_history(self, st) -> bool:
        """As console_app.py: the shabad (or bani) on screen goes into the history once
        it has stayed a while, or at once if it was picked."""
        tid = st.get("track_id")
        if not tid or (st.get("pos") is None and st.get("last_pos") is None):
            return False
        now = time.time()
        if self._on_screen[0] != tid:
            self._on_screen = (tid, now)
        if self.history and self.history[0]["key"] == tid:
            return False
        settled = (now - self._on_screen[1] >= HISTORY_AFTER_S
                   and st.get("status") in ("following", "held_simran", "held_quiet", "held_user"))
        if not (settled or st.get("confidence") == "manual"):
            return False
        tr = self.last_track["track"] if self.last_track and self.last_track["track"]["id"] == tid else None
        if not tr:
            return False
        e = {"key": tid, "kind": tr["kind"], "sid": tr.get("sid"), "bani_id": tr.get("bani_id"),
             "title": tr.get("title", ""), "where": tr.get("subtitle", ""), "time": time.strftime("%H:%M"),
             "mode": st.get("mode")}
        if tr["kind"] == "bani":
            e["where"] = ("Kirtan: " if st.get("mode") == "kirtan" else "Paath: ") + (tr.get("subtitle") or "")
        elif tr["kind"] == "granth":
            e["kind"] = "shabad"
            e["where"] = "Akhand / Sehaj Paath, " + (tr.get("subtitle") or "")
        self.history.insert(0, e)
        del self.history[200:]
        return True

    # ------------------------------------------------------------------ sound
    def audio(self, t: float, t20: str, t10: str, t45: str) -> str:
        """New words heard up to t seconds: the last 20, 10 and 4.5 seconds of them.
        A full check every few seconds (as the laptop app), a quick one in between."""
        sess = self.sess
        msgs = list(sess.tick(t) or [])
        akv = sess.mode == "kirtan" and sess.akv is not None and not sess.akv_paused
        hop = HOP_S["akv"] if akv else HOP_S.get(sess.mode, 5.0)
        if t - self.last_main >= hop and t >= 4.0:
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
    def command(self, cjson: str) -> str:
        c = json.loads(cjson)
        sess, cmd = self.sess, c.get("cmd")
        msgs: list = []
        if cmd == "hold":
            msgs = sess.hold(bool(c.get("on", True)))
        elif cmd == "step":
            msgs = sess.step(int(c.get("delta", 1)))
        elif cmd == "goto":
            msgs = sess.goto(int(c.get("pos", 0)))
        elif cmd == "confirm":
            msgs = sess.confirm(int(c["sid"]))
        elif cmd == "reset":
            self.last_main = self.last_quick = -1e9
            msgs = sess.reset()
        elif cmd == "mode":
            bid, sehaj = c.get("bani_id"), c.get("sehaj")
            msgs = sess.set_mode(c.get("mode", "kirtan"), int(bid) if bid not in (None, "") else None,
                                 None if sehaj is None else bool(sehaj))
        elif cmd == "accept_suggestion":
            msgs = sess.accept_suggestion()
        elif cmd == "akv":
            n = c.get("n")
            msgs = sess.akv_command(str(c.get("action", "")), int(n) if str(n).isdigit() else None)
        elif cmd == "back":
            msgs = sess.back(c.get("sid"))
        elif cmd == "show":
            bid, pos = c.get("bani_id"), c.get("pos")
            msgs = sess.show(int(c.get("sid") or 0), None if pos is None else int(pos),
                             int(bid) if bid not in (None, "") else None)
        elif cmd == "screen_msg":
            msgs = self._screen_msg(c)
        elif cmd == "settings":
            self._apply_settings(c)
            self._configure(sess)
            msgs = [{"type": "settings", "settings": self.settings}]
        elif cmd == "hello":                        # a page (re)connected: everything it needs
            return self.hello()
        elif cmd == "search":
            q, mode = str(c.get("q", ""))[:80], str(c.get("mode", "auto"))
            msgs = [{"type": "search_results", "id": c.get("id"), "q": q, **self.search.search(q, mode)}]
        return self._out(msgs)

    def _apply_settings(self, c: dict):
        for k, default in DEFAULT_SETTINGS.items():
            if k not in c:
                continue
            if isinstance(default, bool):
                self.settings[k] = bool(c[k])
            elif isinstance(default, str):
                v = str(c[k])
                if v in CHOICES.get(k, ()) or (k not in CHOICES and re.fullmatch(r"#[0-9A-Fa-f]{6}", v)):
                    self.settings[k] = v
            else:
                lo, hi = SIZE_LIMITS.get(k, (50, 200))
                try:
                    self.settings[k] = max(lo, min(hi, int(round(float(c[k])))))
                except (TypeError, ValueError):
                    pass

    def _screen_msg(self, c) -> list:
        """ਵਾਹਿਗੁਰੂ, a message or a picture instead of the Gurbani (pictures stay in the
        page; only their names come here)."""
        kind = c.get("kind")
        where = {"screens": bool(c.get("screens", True)), "overlay": bool(c.get("overlay", True))}
        if kind == "vaheguru":
            self.screen_msg = {"kind": "vaheguru", "text": "ਵਾਹਿਗੁਰੂ", **where}
        elif kind == "text":
            text = " ".join(str(c.get("text", "")).split())[:200]
            if not text:
                return []
            self.screen_msg = {"kind": "text", "text": text, **where}
            self.recent_texts = ([text] + [t for t in self.recent_texts if t != text])[:MSG_TEXTS_KEPT]
        elif kind == "image":
            name = str(c.get("image", ""))
            if not IMAGE_NAME.fullmatch(name):
                return []
            self.recent_images = ([name] + [n for n in self.recent_images if n != name])[:MSG_IMAGES_KEPT]
            self.screen_msg = {"kind": "image", "image": "/message-image/" + name, **where}
        elif kind == "forget_image":
            name = str(c.get("image", ""))
            self.recent_images = [n for n in self.recent_images if n != name]
            if self.screen_msg and self.screen_msg.get("image") == "/message-image/" + name:
                self.screen_msg = None
        else:
            self.screen_msg = None
        return [self.screen_msg_msg()]
