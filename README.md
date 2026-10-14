# Gurbani Audio Searcher (web)

The iPhone / web version of Gurbani Audio Searcher (beta testing). Open it in Safari:

**https://misterbgt.github.io/Testcheej/**

It listens with the phone's microphone and shows the shabad or bani being sung or read,
like the laptop app, with no laptop. Everything runs on the phone: the speech model and the
laptop app's own engine run inside the page, and nothing it hears is sent anywhere.

## Using it

1. Open the address above in Safari, on Wi-Fi. The first time, it downloads about 200 MB
   (mostly the speech model, which is then kept on the phone). Getting ready takes about
   half a minute after that.
2. Tap **Listen** (bottom right) and allow the microphone. Keep the page open and the phone
   unlocked; place it near the speakers.
3. Choose Kirtan, Paath or Akhand (Akhand or Sehaj Paath) at the top; in Kirtan,
   **Asa Ki Vaar** follows the Vaar in the order it is sung.
4. Previous, Pause, Next and Listen are along the bottom, with the Now, Search, History
   and Message tabs. The menu (the three lines, top right) has **Sangat screen** (the
   current line full screen, for mirroring to a TV), **Show on a TV** (how to mirror),
   **Settings**, **Play a recording** (try it with an audio file instead of the
   microphone) and **Start over**.

While it is listening and has not yet found the shabad, the logo grows and shrinks with the
sound, so you can see it is hearing; once a shabad is on the screen it stays still
(Settings → Sound turns this off).

Tip: Share → Add to Home Screen gives it its own icon.

## What is here

Version ਅ੫ (build 2026-10-14b), the same as the laptop app.

- `index.html`: the page: the laptop app's phone controller, which has the web version built in
  (`src/make_index.py` adds `local.js` to it).
- `local.js`: connects the page to the two workers below instead of the laptop.
- `asr-worker.js`: the speech model (onnxruntime-web 1.18, the build without shared memory), loaded from Karanbir Singh's
  Hugging Face page and kept in the phone's cache.
- `engine-worker.js`, `engine-core.js`, `app.zip`: the laptop app's Python engine
  (`engine/`, `engine_ext/`, and `app/core.py`, the part of the app the web version
  shares with it), `src/web_hub.py` and the Gurbani data, run with Pyodide.
- `rf.wasm`, `rfjs.js`: rapidfuzz's C++ scorers compiled to WebAssembly
  (`src/rfwasm.cpp`, built by `src/build_rf.sh`), for the engine's word matching (`src/rapidfuzz/`).
- `vocab.json`: the speech model's word pieces.

Everything here is built by `src/build.py` from the app's source (its `web/` folder).

## Credits and licence

Built on the kirtan-captioning project and speech model by Karanbir Singh
(https://github.com/karanbirsingh/kirtan-captioning, CC BY-NC-SA 4.0); the model is loaded
from https://huggingface.co/karansea/indicconformer-stt-pa-ctc-shabad-preview and is not
copied here. Gurbani text from the Shabad OS database. Uses Pyodide, onnxruntime-web and
rapidfuzz (MIT). This web version follows the same terms: non-commercial, share-alike.
