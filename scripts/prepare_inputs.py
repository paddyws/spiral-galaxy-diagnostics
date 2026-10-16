#!/usr/bin/env python3
"""Derive the public galaxy list and sky footprint from existing display data."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
from urllib.parse import quote
import json,re,time
ROOT=Path(__file__).resolve().parents[1]
BASE='https://raw.githubusercontent.com/paddyws/spiral-galaxy-diagnostics/3cd12c19f8e8ea93f848b6d8f46efc32c49b5417/'
names=re.findall(r'data-name="([^"]+)"',(ROOT/'index.html').read_text())
names=[n[0].upper()+n[1:] for n in names]
assert len(names)==len(set(names))==96

def one(name):
 url=BASE+'geometry_views/'+quote(name+'.json')
 for attempt in range(3):
  try:
   data=json.loads(urlopen(Request(url,headers={'User-Agent':'spiral-galaxy-fits-inventory/1.0'}),timeout=60).read());break
  except Exception:
   if attempt==2:raise
   time.sleep(2**attempt)
 m=re.fullmatch(r'J(\d{2})(\d{2})(\d{2}\.\d+)([+-])(\d{2})(\d{2})(\d{2}\.\d+)',name)
 h,mn,s,sign,d,dm,ds=m.groups();ra=15*(int(h)+int(mn)/60+float(s)/3600);dec=(int(d)+int(dm)/60+float(ds)/3600)*(1 if sign=='+' else -1)
 outer=data.get('outer_boundary',{})
 rarc=outer.get('semimajor_arcsec');rpix=outer.get('semimajor_native_pixels')
 pixscale=round(rarc/rpix,6) if rarc and rpix else .63
 assert .1<pixscale<5
 print(name,pixscale,flush=True)
 return dict(name=name,ra_deg=round(ra,8),dec_deg=round(dec,8),coordinate_source='IAU name (J2000)',size=512,pixscale_arcsec=pixscale,field_width_arcsec=round(512*pixscale,6),outer_semimajor_arcsec=rarc,scale_source='saved outer-isophote arcsec/native-pixel ratio' if rarc and rpix else 'fallback 0.63 arcsec/pixel',geometry_source=url)
with ThreadPoolExecutor(max_workers=5) as pool:rows=list(pool.map(one,names))
(ROOT/'data/galaxies.json').write_text(json.dumps(rows,indent=2)+'\n')
