"""rapidfuzz for the web version: the same C++ scorers (rapidfuzz-cpp, compiled to
WebAssembly, rf.wasm + rfjs.js) called from Pyodide. Only what the engine uses:
fuzz.ratio, fuzz.partial_ratio, process.extract and process.cdist."""
__version__ = "3.14.1-web"
from . import fuzz, process  # noqa: F401
