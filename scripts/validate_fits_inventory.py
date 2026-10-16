#!/usr/bin/env python3
"""Cross-check the published inventory against the downloaded FITS and HTML."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse,parse_qs
from collections import Counter
import csv,hashlib,json,sys
from audit_fits import assess
ROOT=Path(__file__).resolve().parents[1]
class Links(HTMLParser):
 def __init__(self):super().__init__();self.bands=[];self.cards=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);classes=a.get('class','').split()
  if tag=='a' and 'fits-band' in classes:self.bands.append(a['href'])
  if tag=='div' and 'fits-card' in classes:self.cards+=1

def main():
 inv=json.loads((ROOT/'data/fits-inventory.json').read_text());rows=inv['galaxies'];source=json.loads((ROOT/'data/galaxies.json').read_text());assert len(rows)==96;assert {x['name'] for x in rows}=={x['name'] for x in source}
 expected=[];release=Counter();counts=Counter();ivar=0;partial=0;unverified=[];no_coverage=[];selected_bytes=0
 for g in rows:
  assert [b['band'] for b in g['bands']]==list('griz')
  good=[b for b in g['bands'] if b['available']];assert g['available_count']==len(good);assert g['available_bands']==[b['band'] for b in good];counts[len(good)]+=1
  assert not g['outer_semimajor_arcsec'] or 2*g['outer_semimajor_arcsec']<g['field_width_arcsec']
  for b in g['bands']:
   if not b['available']:
    assert b['selected'] is None
    (unverified if any(a['status']=='request_or_validation_error' for a in b['attempts']) else no_coverage).append([g['name'],b['band']]);continue
   s=b['selected'];p=ROOT/'fits_cache'/s['download_filename'];blob=p.read_bytes();assert len(blob)==s['bytes'];assert hashlib.sha256(blob).hexdigest()==s['sha256'];check=assess(blob,g,b['band'],s['release']);assert check['status']=='available';assert check['valid_fraction']==s['valid_fraction'];assert check['inverse_variance_hdu']==s['inverse_variance_hdu']
   url=urlparse(s['url']);q=parse_qs(url.query);assert url.scheme=='https' and url.netloc=='www.legacysurvey.org';assert q['bands']==[b['band']];assert int(q['size'][0])==g['size'];assert abs(float(q['pixscale'][0])-g['pixscale_arcsec'])<1e-8
   expected.append(s['url']);release[s['release']]+=1;ivar+=s['inverse_variance_hdu'] is not None;partial+=s['partial_footprint'];selected_bytes+=len(blob)
 for name in ['index.html','fits.html']:
  h=Links();h.feed((ROOT/name).read_text());assert Counter(h.bands)==Counter(expected),(name,len(h.bands),len(expected))
  if name=='index.html':assert h.cards==96
 csvrows=list(csv.DictReader((ROOT/'data/fits-inventory.csv').open()));assert len(csvrows)==96
 for r,g in zip(csvrows,rows):assert r['galaxy']==g['name'] and int(r['available_fits_bands'])==g['available_count']
 for g in rows:assert (ROOT/(g['name']+'_model.html')).read_text().count('src="fits-links.js?v=1"')==1
 result=dict(galaxies=len(rows),verified_band_files=len(expected),bands_per_galaxy=dict(counts),releases=dict(release),with_inverse_variance=ivar,image_only=len(expected)-ivar,partial_footprint_files=partial,selected_bytes=selected_bytes,unverified=unverified,no_usable_coverage=no_coverage,all_selected_files_reparsed_and_sha256_matched=True,html_csv_json_counts_agree=True)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
