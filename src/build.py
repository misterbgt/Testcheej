"""Build the web version (the iPhone page) into web/site/, ready to publish as it is
(GitHub Pages: copy site/ to the top of the repository).

    python web/build.py

  files/      the page's own files: local.js (the stand-in for the laptop), the two
              workers (speech model; engine), rfjs.js and rf.wasm (word matching,
              built from rf/ by rf/build_rf.sh), vocab.json (the speech model's word pieces)
  py/         Python that runs in the browser beside the engine: web_hub.py, and stand-ins
              for rapidfuzz (the same C++ scorers, through rf.wasm) and aiohttp (unused)
  make_index.py  index.html from the laptop app's phone page (pages/phone.html)

site/app.zip holds the engine (engine/, engine_ext/), app/core.py (shared with the laptop
app), py/ and the Gurbani data. The version (app/__init__.py) goes into every file name
the page asks for, so a phone never mixes old and new files.
"""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

WEB = Path(__file__).resolve().parent
REPO = WEB.parent
SITE = WEB / "site"
sys.path.insert(0, str(REPO))
from app import VERSION, VERSION_NAME  # noqa: E402

ENGINE = ["__init__.py", "asr.py", "config.py", "corpus.py", "event_types.py", "matcher.py", "matcher_state.py",
          "protocols.py"]                    # the speech parts (engine/_internal) run in asr-worker.js instead
DATA = ["sggs_corpus.json", "sggs_extra.json", "other_corpus.json", "banis.json", "shabad_meta.json",
        "sggs_angs.json", "sggs_order.json"]


def app_zip(out: Path):
    files = [(REPO / "engine" / f, f"engine/{f}") for f in ENGINE]
    files += [(p, f"engine_ext/{p.name}") for p in sorted((REPO / "engine_ext").glob("*.py"))]
    files += [(REPO / "app" / f, f"app/{f}") for f in ("__init__.py", "core.py")]
    files += [(p, p.relative_to(WEB / "py").as_posix()) for p in sorted((WEB / "py").rglob("*.py"))
              if "__pycache__" not in p.parts]
    files += [(REPO / "data" / f, f"data/{f}") for f in DATA]
    out.unlink(missing_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for src, name in files:
            z.write(src, name)
    return len(files)


def main():
    SITE.mkdir(exist_ok=True)
    for p in sorted((WEB / "files").iterdir()):
        if p.name == "local.js":
            (SITE / p.name).write_text(p.read_text(encoding="utf-8").replace("__VERSION__", VERSION), encoding="utf-8")
        else:
            shutil.copyfile(p, SITE / p.name)
    subprocess.run([sys.executable, str(WEB / "make_index.py"), str(REPO / "pages" / "phone.html"),
                    str(SITE / "index.html"), VERSION, VERSION_NAME], check=True)
    n = app_zip(SITE / "app.zip")
    for name in ("logo.png", "logo64.png"):
        shutil.copyfile(REPO / "pages" / name, SITE / name)
    print(f"web version {VERSION_NAME} ({VERSION}) in {SITE}: app.zip has {n} files")
    for p in sorted(SITE.iterdir()):
        print(f"  {p.name:18s} {p.stat().st_size:>10,d}")


if __name__ == "__main__":
    main()
