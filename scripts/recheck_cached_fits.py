#!/usr/bin/env python3
"""Reconcile all saved audit attempts with their cached pixels, without requests."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
from audit_fits import assess
ROOT=Path(__file__).resolve().parents[1]
def main():
 path=ROOT/'data/fits-inventory.json';inv=json.loads(path.read_text());checked=datetime.now(timezone.utc).isoformat(timespec='seconds')
 for g in inv['galaxies']:
  for b in g['bands']:
   for attempt in b['attempts']:
    fn=attempt.get('download_filename')
    if not fn:continue
    p=ROOT/'fits_cache'/fn
    if not p.exists():continue
    blob=p.read_bytes()
    try:
     result=assess(blob,g,b['band'],attempt['release']);attempt.update(result,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),pixels_rechecked_utc=checked);attempt.pop('error',None)
    except Exception as e:attempt.update(status='request_or_validation_error',error=f'{type(e).__name__}: {e}')
   b['selected']=next((a for a in b['attempts'] if a['status']=='available'),None);b['available']=b['selected'] is not None
  g['available_bands']=[b['band'] for b in g['bands'] if b['available']];g['available_count']=len(g['available_bands'])
 inv['started_utc']=min([inv['started_utc']]+[a['checked_utc'] for g in inv['galaxies'] for b in g['bands'] for a in b['attempts']])
 inv['checked_utc']=checked
 inv['availability_rule']='FITS parses; requested band/release, shape, WCS center and pixel scale match; finite, nonconstant, nonzero IMAGE data; positive finite INVVAR where supplied (otherwise nonzero image coverage proxy). At least 50% of central 16×16 pixels covered. Central coverage below 90% and field coverage below 99% are explicitly flagged; all attempted FITS provenance is retained.'
 path.write_text(json.dumps(inv,indent=2)+'\n')
 print('Rechecked',len(inv['galaxies']),'galaxies;',sum(g['available_count'] for g in inv['galaxies']),'coverage-qualified band files')
if __name__=='__main__':main()
