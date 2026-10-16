#!/usr/bin/env python3
"""Verify/download Legacy Surveys optical FITS, preferring DR9 then DR10/DR11.

Install: python -m pip install numpy astropy
Run from repository: python scripts/audit_fits.py --workers 4
Files are cached in fits_cache/ (ignored by git). Each linked file contains one
band's IMAGE and, where supplied, INVVAR HDUs; HDUs and repeated releases are not extra bands.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
from datetime import datetime,timezone
import argparse,hashlib,io,json,time,threading
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
ROOT=Path(__file__).resolve().parents[1]
BANDS='griz'
REQUEST_LOCK=threading.Lock()
LAST_REQUEST=[0.0]
def throttle():
 with REQUEST_LOCK:
  wait=max(0,2.0-(time.monotonic()-LAST_REQUEST[0]))
  if wait:time.sleep(wait)
  LAST_REQUEST[0]=time.monotonic()
DOCS=['https://www.legacysurvey.org/dr9/description/','https://www.legacysurvey.org/dr10/description/','https://www.legacysurvey.org/dr11/description/','https://www.legacysurvey.org/viewer/urls/']
def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def candidates(band):
 if band!='i':yield 'DR9','ls-dr9'
 yield 'DR10','ls-dr10-south'
 yield 'DR11','ls-dr11-south' if band=='i' else 'ls-dr11'
def assess(blob,row,band,release):
 if not blob.startswith(b'SIMPLE'):raise ValueError('Response is not FITS')
 with fits.open(io.BytesIO(blob),memmap=False) as hdus:
  hdus.verify('exception')
  image_hdus=[(i,h) for i,h in enumerate(hdus) if h.header.get('IMAGETYP','').strip()=='IMAGE']
  ivar_hdus=[(i,h) for i,h in enumerate(hdus) if h.header.get('IMAGETYP','').strip()=='INVVAR']
  if len(image_hdus)!=1 or len(ivar_hdus)>1:raise ValueError('Expected one IMAGE and at most one INVVAR HDU')
  image_idx,im=image_hdus[0];ivar_idx,iv=ivar_hdus[0] if ivar_hdus else (None,None)
  a=np.asarray(im.data);v=np.asarray(iv.data) if iv is not None else np.ones_like(a)
  if a.shape != (row['size'],row['size']) or v.shape!=a.shape:raise ValueError('Unexpected image/ivar shape')
  for h in ([im,iv] if iv is not None else [im]):
   if h.header.get('BANDS','').strip()!=band:raise ValueError('Requested band does not match FITS header')
   if h.header.get('VERSION','').strip().split('-')[0]!=release:raise ValueError('Requested release does not match FITS header')
  w=WCS(im.header).celestial
  xx,yy=w.world_to_pixel_values(row['ra_deg'],row['dec_deg'])
  actual_scale=float(np.sqrt(abs(np.linalg.det(w.pixel_scale_matrix)))*3600)
  if not np.isclose(actual_scale,row['pixscale_arcsec'],rtol=1e-5):raise ValueError('WCS pixel scale differs from requested field')
  if max(abs(xx-(row['size']-1)/2),abs(yy-(row['size']-1)/2))>1:raise ValueError('WCS target is not centered')
  valid=np.isfinite(a)&np.isfinite(v)&(v>0)
  if iv is None:valid &= (a!=0)
  c=row['size']//2; center=valid[c-8:c+8,c-8:c+8]
  usable=bool(valid.any() and np.any(a[valid]!=0) and np.ptp(a[valid])>0 and center.mean()>=.5)
  return dict(status='available' if usable else 'no_usable_target_coverage',valid_fraction=round(float(valid.mean()),6),center_valid_fraction=round(float(center.mean()),6),nonzero_valid_pixels=int(np.count_nonzero(a[valid])),finite_image_fraction=round(float(np.isfinite(a).mean()),6),image_hdu=image_idx,inverse_variance_hdu=ivar_idx,hdu_count=len(hdus),coverage_check='positive inverse variance' if iv is not None else 'finite nonzero image pixels (coverage proxy; rebinned service response omits inverse variance)',shape=list(a.shape),header_release=im.header.get('VERSION'),header_bands=im.header.get('BANDS'),target_pixel=[float(xx),float(yy)],unit=im.header.get('BUNIT'),partial_footprint=bool(valid.mean()<.99),central_coverage_warning=bool(center.mean()<.9))
def one(row,band,cache,recheck=False):
 attempts=[]
 for release,layer in candidates(band):
  params=dict(ra=f"{row['ra_deg']:.8f}",dec=f"{row['dec_deg']:.8f}",layer=layer,bands=band,pixscale=row['pixscale_arcsec'],size=row['size'],invvar='')
  url='https://www.legacysurvey.org/viewer/fits-cutout?'+urlencode(params)
  fn=f"{row['name']}_{release.lower()}_{band}.fits";path=cache/fn
  item=dict(release=release,layer=layer,url=url,checked_utc=now())
  try:
   cached=False
   if path.exists() and not recheck:
    try:
     blob=path.read_bytes();result=assess(blob,row,band,release);cached=True
    except Exception:
     path.replace(path.with_suffix('.invalid'))
   if not cached:
    for trial in range(3):
     try:
      throttle()
      with urlopen(Request(url,headers={'User-Agent':'spiral-galaxy-fits-inventory/1.0 (public astronomy research)'}),timeout=100) as response:blob=response.read(12_000_000)
      if not blob.startswith(b'SIMPLE'):raise ValueError('Response is not FITS')
      result=assess(blob,row,band,release)
      temporary=path.with_suffix('.part');temporary.write_bytes(blob);temporary.replace(path);break
     except Exception as e:
      if trial==2 or isinstance(e,HTTPError) and e.code in (400,404):raise
      if isinstance(e,HTTPError) and e.code==429:
       try:cooldown=max(20,float(e.headers.get('Retry-After',20)))
       except (ValueError,TypeError):cooldown=20
       with REQUEST_LOCK:LAST_REQUEST[0]=max(LAST_REQUEST[0],time.monotonic()+cooldown)
       time.sleep(cooldown)
      else:time.sleep(2**(trial+1))
   result=assess(blob,row,band,release)
   item.update(result,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),download_filename=fn)
  except Exception as e:item.update(status='request_or_validation_error',error=f'{type(e).__name__}: {e}')
  attempts.append(item)
  if item['status']=='available':
   out=dict(band=band,available=True,selected=item,attempts=attempts)
   print(row['name'],band,release,'coverage',item['valid_fraction'],flush=True);return out
 out=dict(band=band,available=False,selected=None,attempts=attempts)
 print(row['name'],band,'UNAVAILABLE',[(a['release'],a['status']) for a in attempts],flush=True);return out

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workers',type=int,default=2);p.add_argument('--cache',type=Path,default=ROOT/'fits_cache');p.add_argument('--recheck',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--limit',type=int);args=p.parse_args()
 if not 1<=args.workers<=4:p.error('Use 1–4 workers to avoid overloading the public service')
 args.cache.mkdir(parents=True,exist_ok=True)
 rows=json.loads((ROOT/'data/galaxies.json').read_text())
 if args.limit:rows=rows[:args.limit]
 results={r['name']:{} for r in rows};started=now()
 if args.resume and (ROOT/'data/audit-progress.json').exists():
  previous=json.loads((ROOT/'data/audit-progress.json').read_text())
  for name in results:results[name]=previous.get(name,{})
 with ThreadPoolExecutor(max_workers=args.workers) as pool:
  futures={pool.submit(one,r,b,args.cache,args.recheck):(r['name'],b) for r in rows for b in BANDS if b not in results[r['name']]}
  for f in as_completed(futures):
   name,band=futures[f];results[name][band]=f.result()
   (ROOT/'data/audit-progress.json').write_text(json.dumps(results,indent=2)+'\n')
 galaxies=[]
 for r in rows:
  bands=[results[r['name']][b] for b in BANDS];available=[b['band'] for b in bands if b['available']]
  galaxies.append(dict(**r,available_count=len(available),available_bands=available,bands=bands))
 output=dict(schema_version=1,started_utc=started,checked_utc=now(),source_commit='3cd12c19f8e8ea93f848b6d8f46efc32c49b5417',scope='Legacy Surveys optical coadd cutouts in g, r, i, z; one file per available band; IMAGE and optional INVVAR are HDUs, not separate bands',preference='DR9 first for g/r/z; DR10-south then DR11 fallback. DR9 has no i band; i starts at DR10-south, then DR11-south.',availability_rule='FITS parses; requested band/release and centered WCS match; nonzero finite IMAGE pixels; positive finite INVVAR when supplied by the service (otherwise nonzero image coverage proxy); >=50% of central 16×16 pixels covered. Edge coverage is reported separately.',original_image_equivalence_verified=False,cutout_note='New sky-centered survey cutouts at the native display pixel scale inferred from saved geometry. They are not the transformed PNGs, fitted models, residual maps, or guaranteed original inputs.',sources=DOCS,galaxies=galaxies)
 (ROOT/'data/fits-inventory.json').write_text(json.dumps(output,indent=2)+'\n')
 print('DONE',len(galaxies),'galaxies',sum(g['available_count'] for g in galaxies),'band files',flush=True)
if __name__=='__main__':main()
