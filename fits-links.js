/* Adds the audited FITS inventory to existing saved-geometry galaxy pages. */
(() => {
  'use strict';
  if (document.getElementById('fits-downloads')) return;
  const name = decodeURIComponent(location.pathname.split('/').pop() || '').replace(/(?:_model)?\.html$/, '');
  if (!/^J\d/.test(name)) return;
  if (!document.querySelector('link[href^="fits.css"]')) {
    const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = 'fits.css?v=1'; document.head.append(css);
  }
  const box = document.createElement('section'); box.id = 'fits-downloads'; box.className = 'fits-downloads standalone';
  const heading = document.createElement('h2'); heading.textContent = 'Survey FITS downloads'; box.append(heading);
  const info = document.createElement('p'); info.textContent = 'Loading checked band availability…'; box.append(info);
  const host = document.querySelector('header.standalone') || document.querySelector('h1');
  if (host) host.after(box); else (document.getElementById('app') || document.body).prepend(box);
  const inventory = document.createElement('a'); inventory.href = 'fits.html#' + encodeURIComponent(name); inventory.textContent = 'Full inventory and coverage details';
  const foot = document.createElement('p'); foot.append(inventory); box.append(foot);
  fetch('data/fits-inventory.json').then(r => {if (!r.ok) throw new Error('HTTP ' + r.status); return r.json();}).then(data => {
    const g = data.galaxies.find(x => x.name === name); if (!g) throw new Error('Galaxy missing from inventory');
    info.textContent = `${g.available_count} verified FITS band${g.available_count === 1 ? '' : 's'}: ${g.available_bands.join(', ') || 'none'}. DR9 preferred, with DR10/DR11 fallback.`;
    const list = document.createElement('div'); list.className = 'fits-band-list';
    for (const b of g.bands) {
      if (!b.available) continue;
      const s = b.selected, a = document.createElement('a'); a.className = 'fits-band'; a.href = s.url;
      a.textContent = `${b.band} · ${s.release} FITS`;
      a.title = `${s.coverage_check}; ${(100*s.valid_fraction).toFixed(1)}% footprint, ${(100*s.center_valid_fraction).toFixed(1)}% central coverage; ${s.bytes.toLocaleString()} bytes`;
      list.append(a);
    }
    info.after(list);
    const note = document.createElement('p'); note.className = 'fits-muted';
    const noivar = g.bands.filter(b => b.available && b.selected.inverse_variance_hdu === null).map(b => b.band);
    note.textContent = `New ${g.size} × ${g.size} sky-centered cutouts; ${g.pixscale_arcsec.toFixed(6)}″/pixel, ${g.field_width_arcsec.toFixed(1)}″ field. Each file is one band. Exact original-input equivalence is unverified; these are not deprojected images or fitted models.` + (noivar.length ? ` Image-only response, without inverse variance: ${noivar.join(', ')}.` : ' Each file includes image and inverse variance.');
    const central = g.bands.filter(b => b.available && b.selected.central_coverage_warning).map(b => `${b.band} (${(100*b.selected.center_valid_fraction).toFixed(1)}%)`);
    if (central.length) note.textContent += ' Central masking/coverage below 90%: ' + central.join(', ') + '.';
    const partial = g.bands.filter(b => b.available && b.selected.partial_footprint).map(b => `${b.band} (${(100*b.selected.valid_fraction).toFixed(1)}%)`);
    if (partial.length) note.textContent += ' Partial field coverage: ' + partial.join(', ') + '.';
    const missing = g.bands.filter(b => !b.available).map(b => {
      const uncertain = b.attempts.some(a => a.status === 'request_or_validation_error');
      return `${b.band}: ${uncertain ? 'unverified (survey service error)' : 'no usable coverage in checked releases'}`;
    });
    if (missing.length) note.textContent += ' ' + missing.join('; ') + '.';
    list.after(note);
  }).catch(() => {info.textContent = 'Band availability could not be loaded. Open the full inventory below.';});
})();
