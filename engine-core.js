// Starts the Python engine (the laptop app's engine/ and engine_ext/, with web_hub.py)
// in Pyodide. Shared by engine-worker.js (the page) and the tests (Node).
(function (root) {
  async function startEngine({ loadPyodide, indexURL, rfjs, rfWasm, appZip, settings, texts, say }) {
    say = say || (() => {});
    say("Starting Python");
    const py = await loadPyodide({ indexURL });
    say("Loading numpy");
    await py.loadPackage("numpy");
    say("Loading the word matching");
    await rfjs.load(rfWasm);
    py.registerJsModule("rfjs", rfjs);
    say("Unpacking the Gurbani data");
    py.unpackArchive(appZip, "zip", { extractDir: "/app" });
    py.runPython(`
import sys, logging
sys.path.insert(0, "/app")
logging.basicConfig(level=logging.WARNING)
`);
    say("Loading Gurbani (about half a minute)");
    py.globals.set("SETTINGS_JSON", JSON.stringify(settings || {}));
    py.globals.set("TEXTS_JSON", JSON.stringify(texts || []));
    py.runPython(`
import os, shutil
from web_hub import WebHub
hub = WebHub("/app", SETTINGS_JSON, TEXTS_JSON)
shutil.rmtree("/app/data", ignore_errors=True)      # loaded: free the memory the files took
`);
    const hub = py.globals.get("hub");
    const loadS = hub.load_s;
    return {
      py, loadS,
      hello: () => JSON.parse(hub.hello()),
      audio: (t, t20, t10, t45) => JSON.parse(hub.audio(t, t20, t10, t45)),
      command: (c) => JSON.parse(hub.command(JSON.stringify(c))),
      settings: () => JSON.parse(py.runPython("import json; json.dumps(hub.settings)")),
      texts: () => JSON.parse(py.runPython("import json; json.dumps(hub.recent_texts)")),
    };
  }
  root.startEngine = startEngine;
  if (typeof module !== "undefined") module.exports = { startEngine };
})(typeof self !== "undefined" ? self : globalThis);
