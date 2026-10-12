#!/bin/bash
# Rebuild the web version's files in site/: the Python bundle (app.zip) and the page.
set -e
cd /home/claude/webapp
rm -rf py/engine py/engine_ext py/data; mkdir -p py/engine py/engine_ext py/data
W=/home/claude/w
cp $W/engine/__init__.py $W/engine/asr.py $W/engine/config.py $W/engine/corpus.py $W/engine/event_types.py $W/engine/matcher.py $W/engine/matcher_state.py $W/engine/protocols.py py/engine/
cp $W/engine_ext/*.py py/engine_ext/
for f in sggs_corpus.json sggs_extra.json other_corpus.json banis.json shabad_meta.json sggs_angs.json sggs_order.json; do cp $W/data/$f py/data/; done
(cd py && rm -f ../site/app.zip && zip -q -9 -r ../site/app.zip engine engine_ext rapidfuzz aiohttp.py web_hub.py data -x "*/__pycache__/*")
python3 make_index.py
cp $W/logo64.png $W/logo.png site/
ls -la site
