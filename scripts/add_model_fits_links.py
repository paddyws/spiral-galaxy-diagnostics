#!/usr/bin/env python3
"""Add the same audited source-band panel to existing model diagnostic pages."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
import json,time
ROOT=Path(__file__).resolve().parents[1]
BASE='https://raw.githubusercontent.com/paddyws/spiral-galaxy-diagnostics/3cd12c19f8e8ea93f848b6d8f46efc32c49b5417/'
def one(row):
 name=row['name']+'_model.html';path=ROOT/name
 if path.exists():s=path.read_text()
 else:
  for trial in range(3):
   try:s=urlopen(Request(BASE+quote(name),headers={'User-Agent':'spiral-galaxy-fits-inventory/1.0'}),timeout=60).read().decode();break
   except Exception:
    if trial==2:raise
    time.sleep(2**trial)
 if 'src="fits-links.js' not in s:s=s.replace('</body>','<script src="fits-links.js?v=1"></script></body>')
 assert s.count('src="fits-links.js')==1
 path.write_text(s);return name
if __name__=='__main__':
 rows=json.loads((ROOT/'data/galaxies.json').read_text())
 with ThreadPoolExecutor(max_workers=4) as p:names=list(p.map(one,rows))
 print('Prepared',len(names),'model-page FITS panels')
