#!/usr/bin/env python3
"""Render checked inventory into the existing static galaxy gallery."""
from pathlib import Path
from html import escape
import csv,json,re
ROOT=Path(__file__).resolve().parents[1]

def links(g,compact=False):
 out=[]
 for band in g['bands']:
  if not band['available']:continue
  s=band['selected'];label=f"{band['band']} · {s['release']}"
  title=f"{band['band']}-band FITS, {s['release']}; {s['coverage_check']}; {s['valid_fraction']:.1%} footprint, {s['center_valid_fraction']:.1%} central coverage; {s['bytes']:,} bytes"
  out.append(f'<a class="fits-band" href="{escape(s["url"],quote=True)}" title="{escape(title,quote=True)}">{escape(label)}</a>')
 return ' '.join(out) or '<span class="fits-muted">No verified optical cutouts</span>'

def main():
 inv=json.loads((ROOT/'data/fits-inventory.json').read_text());gs=inv['galaxies'];byname={g['name'].lower():g for g in gs}
 index=(ROOT/'index.html').read_text()
 index=re.sub(r'<!-- FITS SUMMARY START -->.*?<!-- FITS SUMMARY END -->','',index,flags=re.S)
 index=re.sub(r'<!-- FITS CARD START -->.*?<!-- FITS CARD END -->','',index,flags=re.S)
 def card(m):
  g=byname[m.group(1)];n=g['available_count'];extra=f'<!-- FITS CARD START --><div class="fits-card"><a href="fits.html#{g["name"]}">{n} verified FITS band'+('s' if n!=1 else '')+'</a><div class="fits-band-list">'+links(g,True)+'</div></div><!-- FITS CARD END -->'
  return m.group(0).replace('</div>',extra+'</div>',1)
 index,count=re.subn(r'<div class="card" data-name="([^"]+)">.*?</div>',card,index,flags=re.S)
 assert count==len(gs)==96
 if 'fits.css' not in index:index=index.replace('</head>','<link rel="stylesheet" href="fits.css?v=1"></head>')
 total=sum(g['available_count'] for g in gs);unknown=sum(1 for g in gs for b in g['bands'] if not b['available'] and any(a['status']=='request_or_validation_error' for a in b['attempts']))
 summary=f'<!-- FITS SUMMARY START --><section class="fits-summary"><strong>{total} verified optical FITS band files across {len(gs)} galaxies</strong><p>DR9 preferred; DR10 and DR11 used for missing bands. Each link is one band, not one HDU. <a href="fits.html">Full FITS inventory, coverage and downloads</a></p></section><!-- FITS SUMMARY END -->'
 index=index.replace('<input id="q"',summary+'<input id="q"',1)
 (ROOT/'index.html').write_text(index)
 rows=[]
 for g in gs:
  notes=[]
  uncertain=[b['band'] for b in g['bands'] if not b['available'] and any(a['status']=='request_or_validation_error' for a in b['attempts'])]
  absent=[b['band'] for b in g['bands'] if not b['available'] and b['band'] not in uncertain]
  if absent:notes.append('No usable target coverage: '+', '.join(absent))
  if uncertain:notes.append('Unverified (service error): '+', '.join(uncertain))
  partial=[f"{b['band']} ({b['selected']['valid_fraction']:.1%})" for b in g['bands'] if b['available'] and b['selected']['partial_footprint']]
  if partial:notes.append('Partial footprint: '+', '.join(partial))
  central=[f"{b['band']} ({b['selected']['center_valid_fraction']:.1%})" for b in g['bands'] if b['available'] and b['selected'].get('central_coverage_warning',False)]
  if central:notes.append('Central masking/coverage <90%: '+', '.join(central))
  noivar=[b['band'] for b in g['bands'] if b['available'] and b['selected']['inverse_variance_hdu'] is None]
  if noivar:notes.append('Image only (no IVAR): '+', '.join(noivar))
  rows.append(f'<tr id="{g["name"]}" data-name="{g["name"].lower()}"><td><a href="{g["name"]}.html"><img loading="lazy" alt="{g["name"]} diagnostic preview" src="images/{g["name"]}/face_color.png"><span>{g["name"]}</span></a></td><td>{g["available_count"]}</td><td><div class="fits-band-list">{links(g)}</div></td><td>{g["size"]} × {g["size"]} pixels<br>{g["pixscale_arcsec"]:.6f}″/pixel<br>{g["field_width_arcsec"]:.1f}″ field<br><span class="fits-muted">{escape("; ".join(notes) or "Image + inverse variance")}</span></td></tr>')
 page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Verified FITS downloads | Spiral Galaxy Diagnostics</title><link rel="stylesheet" href="fits.css?v=1"></head><body class="fits-page"><main><a href="index.html">← Galaxy gallery</a><h1>Verified FITS downloads</h1>'''
 page+=f'<p class="fits-lead">{total} verified optical band files for {len(gs)} galaxies. Checked {escape(inv["checked_utc"])}.</p>'
 page+='''<p>One download per optical band. DR9 first, with checked DR10/DR11 fallback.</p><details class="fits-summary"><summary>What’s included and how coverage was checked</summary><p>Download links go directly to the official Legacy Surveys cutout service. We prefer DR9 for each g, r and z band, then try DR10 and DR11. The i band starts at DR10 because DR9 has no i-band images.</p><p>Counts mean distinct downloadable band cutouts. An image and its inverse-variance extension are not two bands; alternative releases are not double-counted.</p><p>These are newly retrieved, sky-centered survey cutouts at each galaxy’s saved native display scale. They cover a 512-pixel square and are not the deprojected pictures, fitted models or residual images shown on the site. Exact equivalence to the original input FITS has not been established.</p><p>Every listed file was downloaded and parsed. Band, release and WCS center were checked, and empty images were rejected. At least 50% of the central 16 × 16 pixels must be covered; central coverage below 90% is flagged. When the service supplies inverse variance, coverage requires it to be positive and finite. Coarser rebinned cutouts may omit inverse variance; for those, finite nonzero image pixels are only a coverage proxy. Partial edge coverage is flagged. These counts include the preferred coverage-qualified file per band. Valid FITS with lower central coverage, as well as empty responses and other attempted releases, remain in the full JSON audit with their URLs and measurements. Availability is not a scientific-quality guarantee.</p></details>'''
 page+=f'<p><a href="data/fits-inventory.json">Full JSON audit</a> · <a href="data/fits-inventory.csv">CSV inventory</a> · <a href="scripts/audit_fits.py">Repeatable audit script</a> · <a href="https://www.legacysurvey.org/dr11/description/">Survey documentation</a></p>'
 if unknown:page+=f'<p class="fits-warning">{unknown} band requests could not be conclusively verified. See the JSON audit for errors; these are excluded from counts.</p>'
 page+='''<label class="fits-search">Find a galaxy <input id="fits-search" type="search" placeholder="e.g. J004332" autocomplete="off"></label><p id="fits-result-count" aria-live="polite">96 galaxies</p><div class="fits-table-wrap"><table><thead><tr><th>Galaxy / diagnostic image</th><th>FITS bands</th><th>Download by band and release</th><th>Field and coverage</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div><p class="fits-muted">The public cutout service can be busy. If a download is rate-limited, wait before retrying. Files are generated by Legacy Surveys and are not stored as large binaries in this repository.</p></main><script>
const search=document.getElementById('fits-search');search.addEventListener('input',()=>{let n=0;for(const row of document.querySelectorAll('tbody tr')){row.hidden=!row.dataset.name.includes(search.value.toLowerCase().trim());if(!row.hidden)n++;}document.getElementById('fits-result-count').textContent=n+' galaxies';});
</script></body></html>'''
 (ROOT/'fits.html').write_text(page)
 with (ROOT/'data/fits-inventory.csv').open('w',newline='') as f:
  cols=['galaxy','available_fits_bands','bands','ra_deg','dec_deg','size_pixels','pixscale_arcsec','field_width_arcsec']+[x for b in 'griz' for x in [b+'_status',b+'_release',b+'_url',b+'_coverage_fraction',b+'_central_coverage_fraction',b+'_inverse_variance_included']]
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
  for g in gs:
   r=dict(galaxy=g['name'],available_fits_bands=g['available_count'],bands=' '.join(g['available_bands']),ra_deg=g['ra_deg'],dec_deg=g['dec_deg'],size_pixels=g['size'],pixscale_arcsec=g['pixscale_arcsec'],field_width_arcsec=g['field_width_arcsec'])
   for b in g['bands']:
    r[b['band']+'_status']='coverage-qualified download' if b['available'] else ('unverified: request or validation error' if any(a['status']=='request_or_validation_error' for a in b['attempts']) else 'no usable target coverage in checked releases')
    if b['available']:
     s=b['selected'];r.update({b['band']+'_release':s['release'],b['band']+'_url':s['url'],b['band']+'_coverage_fraction':s['valid_fraction'],b['band']+'_central_coverage_fraction':s['center_valid_fraction'],b['band']+'_inverse_variance_included':s['inverse_variance_hdu'] is not None})
   w.writerow(r)
 print('Rendered',len(gs),'galaxies;',total,'band files;',unknown,'unresolved bands')
if __name__=='__main__':main()
