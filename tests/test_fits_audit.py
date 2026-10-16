import io,sys,unittest
from pathlib import Path
import numpy as np
from astropy.io import fits
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_fits import assess,candidates
ROW=dict(size=32,ra_deg=10,dec_deg=14,pixscale_arcsec=.63)
def blob(image=None,ivar=True,band='g',release='DR9'):
 if image is None:image=np.arange(1024,dtype='f4').reshape(32,32)+1
 header=fits.Header(dict(IMAGETYP='IMAGE',BANDS=band,VERSION=release,CTYPE1='RA---TAN',CTYPE2='DEC--TAN',CRVAL1=10,CRVAL2=14,CRPIX1=16.5,CRPIX2=16.5,CD1_1=-.63/3600,CD1_2=0,CD2_1=0,CD2_2=.63/3600))
 h=[fits.PrimaryHDU(image,header)]
 if ivar:
  hh=header.copy();hh['IMAGETYP']='INVVAR';h.append(fits.ImageHDU(np.ones_like(image),hh))
 b=io.BytesIO();fits.HDUList(h).writeto(b);return b.getvalue()
class TestAudit(unittest.TestCase):
 def test_image_and_ivar_count_one_band(self):
  r=assess(blob(),ROW,'g','DR9');self.assertEqual(r['status'],'available');self.assertEqual(r['hdu_count'],2)
 def test_rebinned_image_without_ivar(self):
  r=assess(blob(ivar=False),ROW,'g','DR9');self.assertEqual(r['status'],'available');self.assertIsNone(r['inverse_variance_hdu'])
 def test_zero_placeholder_rejected(self):self.assertEqual(assess(blob(image=np.zeros((32,32))),ROW,'g','DR9')['status'],'no_usable_target_coverage')
 def test_nan_rejected(self):self.assertEqual(assess(blob(image=np.full((32,32),np.nan)),ROW,'g','DR9')['status'],'no_usable_target_coverage')
 def test_no_center_rejected(self):
  a=np.ones((32,32));a[8:24,8:24]=0
  self.assertEqual(assess(blob(image=a,ivar=False),ROW,'g','DR9')['status'],'no_usable_target_coverage')
 def test_partial_center_available_with_warning(self):
  with fits.open(io.BytesIO(blob())) as h:
   h[1].data[8:10,8:24]=0;b=io.BytesIO();h.writeto(b)
  r=assess(b.getvalue(),ROW,'g','DR9');self.assertEqual(r['status'],'available');self.assertTrue(r['central_coverage_warning']);self.assertEqual(r['center_valid_fraction'],.875)
 def test_below_half_center_kept_but_not_selected(self):
  with fits.open(io.BytesIO(blob())) as h:
   h[1].data[8:17,8:24]=0;b=io.BytesIO();h.writeto(b)
  r=assess(b.getvalue(),ROW,'g','DR9');self.assertEqual(r['status'],'no_usable_target_coverage');self.assertEqual(r['center_valid_fraction'],.4375);self.assertGreater(r['valid_fraction'],0)
 def test_wrong_band_rejected(self):
  with self.assertRaises(ValueError):assess(blob(band='r'),ROW,'g','DR9')
 def test_wrong_release_rejected(self):
  with self.assertRaises(ValueError):assess(blob(release='DR11'),ROW,'g','DR9')
 def test_regional_version(self):self.assertEqual(assess(blob(release='DR10-south'),ROW,'g','DR10')['status'],'available')
 def test_constant_placeholder_rejected(self):self.assertEqual(assess(blob(image=np.ones((32,32))),ROW,'g','DR9')['status'],'no_usable_target_coverage')
 def test_wrong_pixel_scale_rejected(self):
  with self.assertRaises(ValueError):assess(blob(),dict(ROW,pixscale_arcsec=.262),'g','DR9')
 def test_wrong_wcs_center_rejected(self):
  with self.assertRaises(ValueError):assess(blob(),dict(ROW,ra_deg=11),'g','DR9')
 def test_zero_inverse_variance_rejected(self):
  with fits.open(io.BytesIO(blob())) as h:
   h[1].data[:]=0;b=io.BytesIO();h.writeto(b)
  self.assertEqual(assess(b.getvalue(),ROW,'g','DR9')['status'],'no_usable_target_coverage')
 def test_corrupt_fits_rejected(self):
  with self.assertRaises(Exception):assess(blob()[:3000],ROW,'g','DR9')
 def test_preference(self):self.assertEqual([x[0] for x in candidates('g')],['DR9','DR10','DR11']);self.assertEqual([x[0] for x in candidates('i')],['DR10','DR11'])
if __name__=='__main__':unittest.main()
