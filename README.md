# Spiral Galaxy Diagnostics

Interactive visualizations for 96 isolated galaxies. The original native and estimated deprojected views share saved arm coordinates. These are algorithmic candidate arm tracks, not ground-truth physical arms.

Methods include residual Track-V2, SpArcFiRe, Fourier components, radial peak-and-graph tracking, and curved Gabor variants. Local pitch angles are estimated from deprojected tracks; large pitch ranges indicate variation and/or possible overfitting.

Only presentation assets and per-galaxy display geometry are published. Raw FITS images, full scientific working arrays, personal paths, credentials, and retired SINDy/eigengap experiments are not included.

## Verified optical FITS downloads

Open [the FITS inventory](fits.html) or use the band links on the gallery and
individual diagnostic pages. The checked inventory covers the Legacy Surveys
optical g, r, i and z bands for all 96 galaxies. We select DR9 when usable, then
fall back to DR10 or DR11 per band. DR9 has no i band. For DR10 we explicitly use
its southern DECam layer so northern DR9 data are not relabeled as DR10.

Each count is one downloadable single-band cutout, not a count of HDUs, raw
exposures or releases. Links point to the official cutout service. Full FITS
binaries are downloaded for verification but are not committed to this site.

### Footprint and verification

The cutouts are 512-pixel squares, centered on coordinates parsed from the IAU
J2000 galaxy names. Their pixel scales are inferred from each saved display
geometry's outer-isophote arcseconds/native-pixel ratio. This retains the
per-galaxy display scale instead of using a small fixed 0.262 arcsec/pixel field
that could crop larger galaxies. Newly fetched cutouts are not guaranteed to be
the exact original inputs. They are not deprojected PNGs, models or residuals.

Every listed response was downloaded and parsed as FITS. We check the requested
band, release, shape and WCS center, reject empty images, and require coverage
in at least 50% of the central 16×16 pixels. Central coverage below 90% is
flagged rather than concealing otherwise available files. Positive finite inverse variance
is used when supplied; the service can omit inverse variance in coarser rebinned
cutouts, in which case finite nonzero image pixels are a weaker coverage proxy.
Edge coverage and omitted inverse variance are recorded. Availability does not
establish adequate depth, calibration, photometric suitability or image quality.
A request error is recorded as unverified, not proof that survey data do not exist.
The full JSON retains every attempted release, including downloadable FITS that
do not meet the central-coverage threshold. Such files are not selected or added
to the coverage-qualified band counts. The CSV includes per-band status, release,
download URL, central/field coverage and inverse-variance availability.

### Reproduce the audit

Requirements: Python 3.10+, NumPy and Astropy. Install with
`python -m pip install -r requirements-fits.txt`, then run:

```
python scripts/audit_fits.py --workers 2
python scripts/build_fits_pages.py
```

The source list and scales are saved in `data/galaxies.json`; `scripts/prepare_inputs.py`
can reproduce them from the original public site commit. The audit caches FITS in
`fits_cache/`, retries transient failures with backoff, throttles requests, and
writes `data/fits-inventory.json`. To force a fresh network retrieval, use
`--recheck`. An interrupted run can continue from `data/audit-progress.json` with
`--resume`; only use this with the same input list and parameters. The build also writes a CSV and updates the static gallery counts.

Official references: [DR9](https://www.legacysurvey.org/dr9/description/),
[DR10](https://www.legacysurvey.org/dr10/description/),
[DR11](https://www.legacysurvey.org/dr11/description/), and
[viewer cutout formats](https://www.legacysurvey.org/viewer/urls/).

Validation tests: `python -m unittest discover -s tests -v`. These include empty,
constant and corrupt FITS responses, absent/zero inverse variance, wrong bands,
wrong releases, incorrect WCS centers and field scales, and release preference.
After an audit, `python scripts/validate_fits_inventory.py` cross-checks all selected
cached files, their SHA-256 hashes, counts, links, and the generated HTML/CSV.
`python scripts/recheck_cached_fits.py` re-evaluates every saved attempt from its
cached pixels without making new network requests; rebuild the pages afterwards.
