"""Make the web version's page (site/index.html) from the laptop app's phone controller
(pages/phone.html). The page has the web version built in (getting ready, the sangat
screen, settings, playing a recording): it switches to it when local.js is loaded before
its own script, which then stands in for the laptop (talking to this phone's own speech
model and engine instead). So this only writes the version in and adds local.js.

usage: python make_index.py PHONE_HTML OUT_HTML VERSION VERSION_NAME   (build.py runs it)"""
import sys

SRC, OUT, VERSION, VERSION_NAME = sys.argv[1:5]
s = open(SRC, encoding="utf-8").read().replace("__VERSION_NAME__", VERSION_NAME).replace("__VERSION__", VERSION)
MARK = "<script>\n(() => {"
assert s.count(MARK) == 1, "phone.html: its script must start with: <script> (() => {"
s = s.replace(MARK, f'<script src="local.js?v={VERSION}"></script>\n' + MARK)
open(OUT, "w", encoding="utf-8").write(s)
print("wrote", OUT, len(s))
