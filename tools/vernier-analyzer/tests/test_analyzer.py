import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import vernier
import synthetic
import numpy as np
from PIL import Image


class AnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=vernier.load_original()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='vernier-fixture-')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.addCleanup(self.m.plt.close,'all')

    def fixture(self,shift=4,portrait=False):
        p=self.root/'invented.png';synthetic.image(shift,portrait).save(p);return p

    def cli(self,*args):
        r=subprocess.run([sys.executable,'-B',str(ROOT/'vernier.py'),*map(str,args)],cwd=self.root,capture_output=True,text=True,timeout=90)
        return r,json.loads(r.stdout)

    def test_original_four_files_and_duplicate_revision_bytes(self):
        b=json.loads((ROOT/'BASELINE.json').read_bytes())
        self.assertEqual(len(b['source_sha256']),4)
        for name,pin in b['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),pin)
        self.assertEqual((ROOT/'original/Vern_Analyze_v2.py').read_bytes(),(ROOT/'original/Vern_Analyze_v3b.py').read_bytes())

    def test_original_verification_outputs_are_checked(self):
        r=subprocess.run([sys.executable,'-B',str(ROOT/'original/verify_patch.py')],cwd=self.root,capture_output=True,text=True,timeout=60)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(r.stdout.splitlines(),['syntax_ok True','help_rc 0','has_rev3b_gate True','has_qc_summary True'])
        self.assertEqual(r.stderr,'')

    def test_zero_offset_oracle(self):
        v=vernier.analyze(self.fixture(0));self.assertAlmostEqual(v['results']['delta_verniers'],0,places=9)
        self.assertEqual(v['results']['delta_sem_verniers'],0)

    def test_signed_shift_and_unit_oracles(self):
        p=self.root/'shift.png'
        for shift in (-8,-4,4,8):
            with self.subTest(shift=shift):
                synthetic.image(shift).save(p);v=vernier.analyze(p);n=v['results']
                self.assertAlmostEqual(n['delta_verniers'],shift/40,delta=.002)
                self.assertAlmostEqual(n['delta_um'],shift/4,delta=.02)
                # Preserve legacy length-vs-last-index scale, and document it.
                self.assertAlmostEqual(n['delta_orig_px'],shift*640/639,delta=.10)
                self.assertFalse(v['quality_approved']);self.assertFalse(v['calibration_verified'])

    def test_portrait_own_sampling_windows(self):
        v=vernier.analyze(self.fixture(4,True))
        self.assertEqual(v['orientation'],'portrait')
        self.assertAlmostEqual(v['results']['delta_verniers'],.1,delta=.002)
        self.assertEqual(v['dimensions'],[100,640])

    def test_original_main_numeric_parity(self):
        p=self.fixture();expected=vernier.analyze(p)['results']
        output=io.StringIO()
        with patch.object(self.m,'select_png_file',return_value=str(p)),contextlib.redirect_stdout(output):
            actual=self.m.main(['--no-display'])
        value,error=map(float,output.getvalue().split())
        self.assertAlmostEqual(value,expected['delta_verniers'],places=6)
        self.assertAlmostEqual(error,expected['delta_sem_verniers'],places=6)
        self.assertAlmostEqual(actual,expected['delta_verniers'],places=12)

    def test_extrema_subpixel_and_insufficient_points(self):
        x=np.arange(11,dtype=float);s=(x-4.25)**2
        self.assertAlmostEqual(self.m.refine_extremum_quadratic(s,4,'min'),4.25,places=10)
        self.assertEqual(self.m.refine_extremum_quadratic(np.array([2.]),0,'min'),0)
        self.assertIsNone(self.m.ordinary_least_squares_line(np.array([1]),np.array([2])))
        self.assertTrue(math.isnan(self.m.robust_median(np.array([math.nan]))))

    def test_robust_fit_rejects_invented_outlier(self):
        x=np.arange(11,dtype=float);y=10*x+100;y[5]+=70
        r=self.m.robust_fit_known_centers(x,y)
        self.assertAlmostEqual(r['slope_um_per_interp'],10,places=10)
        self.assertFalse(r['inlier_mask'][5]);self.assertEqual(r['n_inliers'],10)

    def test_quality_gate_and_empty_candidate_boundaries(self):
        gray=np.asarray(synthetic.image(),dtype=float)
        a,b,q=self.m.rev3b_build_sampling_groups(gray,'landscape',list(range(20,40,2)),list(range(60,80,2)))
        self.assertFalse(q['group_a']['fallback_used']);self.assertFalse(q['group_b']['fallback_used'])
        self.assertGreaterEqual(len(a),8);self.assertLessEqual(len(b),14)
        self.assertEqual(self.m.rev3b_expand_sampling_indices([-2,0,2],3),[0,1,2])
        self.assertEqual(self.m.rev3b_gate_indices(gray,'landscape',[]),([],{'candidates':0,'kept':0}))

    def test_fallback_ranking_is_preserved_but_flagged(self):
        gray=np.full((100,640),180.,dtype=float)
        kept,q=self.m.rev3b_gate_indices(gray,'landscape',list(range(16,43)))
        self.assertTrue(q['fallback_used']);self.assertEqual(len(kept),8)
        self.assertFalse(any(row['keep'] for row in q['scored']))
        # Force a strict gate without modifying source bytes. The CLI must
        # expose the original fallback even when the numerical result is finite.
        p=self.fixture();m=vernier.load_original();m.REV3B_MIN_VALID_LINES=100
        with patch.object(vernier,'load_original',return_value=m):v=vernier.analyze(p)
        self.assertTrue(v['fallback_used']);self.assertIn('QC_FALLBACK_RETAINED_FAILED_LINES',v['notes'])

    def test_blank_and_too_small_images_refused(self):
        p=self.root/'bad.png';Image.new('L',(640,100),180).save(p)
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT_PATTERN'):vernier.analyze(p)
        Image.new('L',(10,10),180).save(p)
        with self.assertRaisesRegex(ValueError,'SAMPLING_GROUPS_UNAVAILABLE'):vernier.analyze(p)

    def test_malformed_non_png_and_pixel_limits(self):
        p=self.root/'bad.png';p.write_bytes(b'not an image')
        with self.assertRaises(OSError):vernier.analyze(p)
        Image.new('RGB',(100,100)).save(p,format='JPEG')
        with self.assertRaisesRegex(ValueError,'SINGLE_PNG_REQUIRED'):vernier.analyze(p)
        Image.new('L',(2001,2000)).save(p,format='PNG')
        with self.assertRaisesRegex(ValueError,'IMAGE_DIMENSIONS_REFUSED'):vernier.analyze(p)

    def test_cli_copied_runtime_arbitrary_working_directory(self):
        p=self.fixture();before=hashlib.sha256(p.read_bytes()).hexdigest()
        r,v=self.cli(p)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stderr,'')
        self.assertEqual(v['status'],'RESULT_REQUIRES_REVIEW')
        self.assertAlmostEqual(v['results']['delta_verniers'],.1,delta=.002)
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),before)
        self.assertEqual(v['plots'],[])

    def test_cli_errors_exit_two_and_no_input_path_disclosure(self):
        p=self.root/'invented-private-name.png';r,v=self.cli(p)
        self.assertEqual(r.returncode,2);self.assertEqual(v,{'status':'ERROR','code':'PATH_UNAVAILABLE'})
        self.assertNotIn(str(self.root),r.stdout+r.stderr)

    def test_plot_rendering_and_no_overwrite(self):
        p=self.fixture();out=self.root/'plots';v=vernier.analyze(p,out)
        self.assertEqual(len(v['plots']),6)
        pins={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in v['plots']}
        for name in v['plots']:
            with Image.open(out/name) as im:self.assertEqual(im.format,'PNG');self.assertGreater(im.width,100)
        with self.assertRaisesRegex(ValueError,'PLOT_DESTINATION_EXISTS'):vernier.analyze(p,out)
        self.assertEqual(pins,{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in pins})

    def test_symlink_refused_when_available_and_no_silent_skip(self):
        p=self.fixture();link=self.root/'link.png'
        # Windows may deny creation to ordinary accounts. Always exercise the
        # reparse attribute refusal, then additionally exercise native symlinks.
        original_lstat=Path.lstat
        def fake_lstat(item,*a,**k):
            if item==p:
                class Reparse:st_mode=0o100644;st_file_attributes=0x400
                return Reparse()
            return original_lstat(item,*a,**k)
        with patch.object(Path,'lstat',fake_lstat),self.assertRaisesRegex(ValueError,'LINK_PATH_REFUSED'):vernier.ordinary(p)
        try:link.symlink_to(p)
        except OSError:return
        with self.assertRaisesRegex(ValueError,'LINK_PATH_REFUSED'):vernier.analyze(link)

    def test_fixture_generator_exclusive_and_expected_records(self):
        out=self.root/'fixtures';v=synthetic.generate(out)
        self.assertEqual(v['images'],5)
        expected=json.loads((out/'EXPECTED.json').read_bytes())
        for row in expected['cases']:
            result=vernier.analyze(out/row['file'])['results']
            self.assertAlmostEqual(result['delta_verniers'],row['expected_verniers'],delta=row['absolute_tolerance_verniers'])
        with self.assertRaises(FileExistsError):synthetic.generate(out)


if __name__=='__main__':unittest.main()
