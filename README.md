# Gurbani Audio Searcher (web)

The iPhone / web version of Gurbani Audio Searcher (beta testing). Open it in Safari:

**https://misterbgt.github.io/testcheej/**

It listens with the phone's microphone and shows the shabad or bani being sung or read,
like the laptop app, with no laptop. Everything runs on the phone: the speech model and the
laptop app's own engine run inside the page, and nothing it hears is sent anywhere.

## Using it

1. Open the address above in Safari, on Wi-Fi. The first time, it downloads about 200 MB
   (mostly the speech model, which is then kept on the phone). Getting ready takes about
   half a minute after that.
2. Tap **Start listening** and allow the microphone. Keep the page open and the phone
   unlocked; place it near the speakers.
3. **Sangat screen** shows the current line full screen (for screen mirroring to a TV).
4. Kirtan / Paath, Akhand / Sehaj Paath, Asa Ki Vaar, Search, History and the ਵਾਹਿਗੁਰੂ /
   message / picture screen work as on the laptop app's phone controller.
5. **Play a recording** tries it with an audio file instead of the microphone.

Tip: Share → Add to Home Screen gives it its own icon.

## What is here

- `index.html`: the page (the laptop app's phone controller, made by `src/make_index.py`).
- `local.js`: connects the page to the two workers below instead of the laptop.
- `asr-worker.js`: the speech model (onnxruntime-web), loaded from Karanbir Singh's
  Hugging Face page and kept in the phone's cache.
- `engine-worker.js`, `engine-core.js`, `app.zip`: the laptop app's Python engine
  (`engine/`, `engine_ext/`, `src/web_hub.py`) and Gurbani data, run with Pyodide.
- `rf.wasm`, `rfjs.js`: rapidfuzz's C++ scorers compiled to WebAssembly
  (`src/rfwasm.cpp`), for the engine's word matching (`src/rapidfuzz/`).
- `vocab.json`: the speech model's word pieces.

## Credits and licence

Built on the kirtan-captioning project and speech model by Karanbir Singh
(https://github.com/karanbirsingh/kirtan-captioning, CC BY-NC-SA 4.0); the model is loaded
from https://huggingface.co/karansea/indicconformer-stt-pa-ctc-shabad-preview and is not
copied here. Gurbani text from the Shabad OS database. Uses Pyodide, onnxruntime-web and
rapidfuzz (MIT). This web version follows the same terms: non-commercial, share-alike.
