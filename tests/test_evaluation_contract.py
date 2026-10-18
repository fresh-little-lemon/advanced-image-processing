import copy
import itertools
import json
import unittest
from pathlib import Path
import numpy as np
from reliable_focus.evaluation_contract import (
    digest, validate_manifest, validate_manifest_bundle, validate_run_record,
    validate_ablation, paired_uint8_inputs, SCHEMA_VERSION, PROTOCOL_ID,
)
from reliable_focus.metric_contract import score_rgb, REC709
from reliable_focus.metrics import psnr, edge_preservation_local
from reliable_focus.core import decode_srgb, encode_srgb
from reliable_focus.diagnostic import DiagnosticConfig, energy_fuse
from reliable_focus.residual_floor import estimate_floor
from reliable_focus.crossfit_floor import estimate_crossfit

ROOT = Path(__file__).resolve().parents[1]


def scene(scene_id="fixture", split="validation", group="fixture-group"):
    return {"scene_id": scene_id, "split": split, "group_id": group,
            "files": [{"role": role, "path": f"{scene_id}/{role}.png",
                       "sha256": digest([scene_id, role]), "height": 16, "width": 16,
                       "bytes": 100, "mode": "RGB"} for role in ("A", "B", "GT")]}


def run_fixture():
    s = scene()
    a = np.full((16,16,3), .25)
    b = np.full_like(a, .5)
    case = {"case_id": "fixture-0", "scene_id": s["scene_id"], "split": s["split"],
            "group_id": s["group_id"], "seed": 11, "noise_a_255": 0, "noise_b_255": 5,
            "shape": [16,16,3], "input_order": ["A", "B"],
            "input_sha256": {"A": digest("a"), "B": digest("b")}}
    run = {"schema_version": SCHEMA_VERSION, "protocol_id": PROTOCOL_ID,
           "evidence_level": "synthetic_contract_only", "manifest_sha256": digest([s]),
           "protocol_sha256": digest("fixture-protocol"),
           "code": {"base_commit": "a"*40, "source_sha256": {"fixture.py": digest("code")}},
           "model": {"kind": "non_learned", "artifact_sha256": None,
                     "configs": {"average": {"weight_a": .5}, "other": {"weight_a": .5}}},
           "runtime": {"engine": "python", "version": "fixture", "dependencies": {},
                       "execution_label": "python_execution"}, "cases": [case], "results": []}
    for method in run["model"]["configs"]:
        run["results"].append({"case_id": case["case_id"], "method_id": method,
            "seed": 11, "input_sha256": dict(case["input_sha256"]), "status": "ok",
            "output_shape": [16,16,3], "output_sha256": digest("output"),
            "metrics": score_rgb(reference=a, output=b, color_domain="linear_rgb")})
    for key in ("code", "model", "runtime"):
        run[key+"_sha256"] = digest(run[key])
    return s, run


class MetricContractTests(unittest.TestCase):
    def test_psnr_known_values_and_exact_match(self):
        a = np.zeros((16,16,3))
        self.assertEqual(psnr(a, np.ones_like(a)), 0.)
        self.assertAlmostEqual(psnr(a, a+.1), 20., places=12)
        self.assertTrue(np.isposinf(psnr(a,a)))

    def test_psnr_rejects_uint8_broadcast_nan_inf_range_empty(self):
        a = np.zeros((16,16,3))
        for b in (a.astype(np.uint8), a[:,:1], a+np.nan, a+np.inf, a-1e-8, a+1.01,
                  np.zeros((0,16,3)), np.zeros((16,16,4))):
            with self.subTest(shape=b.shape, dtype=b.dtype):
                with self.assertRaises(ValueError): psnr(a,b)

    def test_float64_historical_valid_formula_unchanged(self):
        rng = np.random.default_rng(502)
        for _ in range(30):
            a,b = rng.random((2,17,19,3))
            expected = float(-10*np.log10(float(np.mean((a-b)**2))))
            self.assertEqual(psnr(a,b), expected)

    def test_float32_uses_float64_arithmetic(self):
        a = np.linspace(.1,.9,16*16*3,dtype=np.float32).reshape(16,16,3)
        b = (a+.001).astype(np.float32)
        expected = -10*np.log10(np.mean((a.astype(np.float64)-b.astype(np.float64))**2))
        self.assertEqual(psnr(a,b), expected)

    def test_ssim_exact_match_is_one_and_json_safe(self):
        a = np.random.default_rng(17).random((18,21,3))
        score = score_rgb(reference=a, output=a, color_domain="linear_rgb")
        self.assertEqual(score["ssim_y_rec709_local"],1.)
        self.assertIsNone(score["psnr_rgb"])
        self.assertEqual(score["psnr_status"],"positive_infinity")
        self.assertEqual(score["ssim_valid_centers"],8*11)
        json.dumps(score, allow_nan=False)

    def test_ssim_constants_match_analytic_formula(self):
        a=np.full((18,19,3),.3); b=np.full_like(a,.6)
        got=score_rgb(reference=a,output=b,color_domain="linear_rgb")["ssim_y_rec709_local"]
        expected=(2*.3*.6+.01**2)/(.3**2+.6**2+.01**2)
        self.assertAlmostEqual(got,expected,places=11)

    def test_ssim_matches_independent_direct_window_formula(self):
        rng=np.random.default_rng(36)
        a,b=rng.random((2,14,16,3))
        ya,yb=a@REC709,b@REC709
        w=np.array([[np.exp(-(i*i+j*j)/(2*1.5**2)) for j in range(-5,6)] for i in range(-5,6)])
        w/=w.sum(); values=[]
        for i in range(4):
            for j in range(6):
                x,y=ya[i:i+11,j:j+11],yb[i:i+11,j:j+11]
                ux,uy=np.sum(x*w),np.sum(y*w)
                vx,vy=np.sum((x-ux)**2*w),np.sum((y-uy)**2*w)
                cov=np.sum((x-ux)*(y-uy)*w)
                values.append((2*ux*uy+.0001)*(2*cov+.0009)/((ux*ux+uy*uy+.0001)*(vx+vy+.0009)))
        got=score_rgb(reference=a,output=b,color_domain="linear_rgb")
        self.assertAlmostEqual(got["ssim_y_rec709_local"],np.mean(values),places=12)

    def test_crop_and_mask_apply_identically(self):
        a=np.full((24,24,3),.4);b=a.copy();b[0]=0
        full=score_rgb(reference=a,output=b,color_domain="linear_rgb")
        cropped=score_rgb(reference=a,output=b,color_domain="linear_rgb",crop_border=1)
        self.assertEqual(full["psnr_status"],"finite")
        self.assertEqual(cropped["psnr_status"],"positive_infinity")
        mask=np.ones((24,24),bool);mask[0]=False
        masked=score_rgb(reference=a,output=b,color_domain="linear_rgb",valid_mask=mask)
        self.assertEqual(masked["ssim_y_rec709_local"],1.)
        self.assertEqual(masked["ssim_valid_centers"],13*14)
        self.assertEqual(masked["valid_pixels"],23*24)

    def test_invalid_domain_crop_mask_and_small_ssim_fail_closed(self):
        a=np.full((16,16,3),.4)
        for kw in ({"color_domain":"RGB"},{"crop_border":True},{"crop_border":3},
                   {"valid_mask":np.ones((16,16),np.uint8)}, {"valid_mask":np.zeros((16,16),bool)},
                   {"valid_mask":np.eye(16,dtype=bool)}):
            with self.subTest(kw=list(kw)):
                with self.assertRaises(ValueError): score_rgb(reference=a,output=a,**({"color_domain":"linear_rgb"}|kw))
        with self.assertRaises(TypeError): score_rgb(a,a,"linear_rgb")

    def test_color_domains_are_explicit_and_not_interchanged(self):
        a=np.full((16,16,3),.4);b=np.full_like(a,.5)
        srgb=score_rgb(reference=a,output=b,color_domain="srgb_encoded_rgb")
        linear=score_rgb(reference=decode_srgb(a),output=decode_srgb(b),color_domain="linear_rgb")
        self.assertNotEqual(srgb["psnr_rgb"],linear["psnr_rgb"])
        self.assertEqual(srgb["color_domain"],"srgb_encoded_rgb")

    def test_existing_local_q_flat_is_explicitly_undefined(self):
        a=np.full((16,16,3),.4)
        self.assertTrue(np.isnan(edge_preservation_local(a,a,a)))
        # This preserves q_local's historical definition; never rename it official Q_AB/F.


class DatasetAndNoiseTests(unittest.TestCase):
    def test_real_manifest_bundle_has_26_94_13_disjoint_groups(self):
        folder=ROOT/'data/manifests'
        master=json.loads((folder/'manifest_v1.json').read_text())
        splits={s:json.loads((folder/f'{s}_v1.json').read_text()) for s in ('validation','test','external_test','exploration')}
        report=validate_manifest_bundle(master,splits)
        self.assertEqual(report['splits'],{'validation':26,'test':94,'external_test':13})
        self.assertEqual(report['groups'],133)

    def test_reject_scene_group_file_and_role_leakage(self):
        a=scene();b=scene('second','test','second-group')
        for mutation in ('scene','group','hash','path','role','shape'):
            x,y=copy.deepcopy(a),copy.deepcopy(b)
            if mutation=='scene': y['scene_id']=x['scene_id']
            if mutation=='group': y['group_id']=x['group_id']
            if mutation=='hash': y['files'][0]['sha256']=x['files'][0]['sha256']
            if mutation=='path': y['files'][0]['path']=x['files'][0]['path']
            if mutation=='role': y['files'][1]['role']='A'
            if mutation=='shape': y['files'][1]['width']=17
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):validate_manifest([x,y])

    def test_split_manifest_cannot_silently_drop_scene(self):
        with self.assertRaises(ValueError): validate_manifest_bundle([scene()],{'validation':[]})

    def test_noise_matches_existing_pilot_draw_order_exactly(self):
        a,b=np.random.default_rng(91).random((2,16,16,3))
        for na,nb in ((0,0),(0,5),(5,0),(5,5)):
            rng=np.random.default_rng(11);expected=[]
            for source,sigma in ((a,na),(b,nb)):
                x=np.clip(decode_srgb(source)+rng.normal(0,sigma/255,source.shape),0,1)
                expected.append(np.floor(np.clip(encode_srgb(x),0,1)*255+.5).astype(np.uint8))
            actual=paired_uint8_inputs(a,b,noise_a_255=na,noise_b_255=nb,seed=11)
            for x,y in zip(actual,expected):np.testing.assert_array_equal(x,y)

    def test_paired_noise_repeatability_and_input_immutability(self):
        a=np.full((32,32,3),.5);before=a.copy()
        x=paired_uint8_inputs(a,a,noise_a_255=5,noise_b_255=5,seed=23)
        y=paired_uint8_inputs(a,a,noise_a_255=5,noise_b_255=5,seed=23)
        for i in range(2):np.testing.assert_array_equal(x[i],y[i])
        self.assertFalse(np.array_equal(*x));np.testing.assert_array_equal(a,before)


class AblationTests(unittest.TestCase):
    def configs(self):
        return [dict(estimator=e,subtract_mean=m,normalize_variance=v,window=7,kappa=4.,
                     epsilon_variance=1e-8,fallback_quantization=False)
                for e,m,v in itertools.product(('same_sample','crossfit'),(False,True),(False,True))]

    def test_eight_cells_have_identical_backbone(self):
        self.assertEqual(validate_ablation(self.configs())['cells'],8)
        cfg=self.configs();cfg[-1]['window']=9
        with self.assertRaises(ValueError):validate_ablation(cfg)
        cfg=self.configs();cfg[-1]=cfg[0]
        with self.assertRaises(ValueError):validate_ablation(cfg)

    def test_both_corrections_off_ignore_estimator_choice(self):
        a,b=np.random.default_rng(8).uniform(.1,.9,(2,48,48,3))
        same=estimate_floor(a,b)[0];cross=estimate_crossfit(a,b)[0]
        cfg=DiagnosticConfig(sigma_mode='oracle_known',subtract_mean=False,
                             normalize_variance=False,fallback_quantization=False)
        np.testing.assert_array_equal(energy_fuse(a,b,cfg,same)[0],energy_fuse(a,b,cfg,cross)[0])


class ResultSchemaTests(unittest.TestCase):
    def validate(self,s,r):return validate_run_record(r,scenes=[s],manifest_sha256=digest([s]))

    def test_valid_record_and_failure_retained_in_denominator(self):
        s,r=run_fixture();self.assertEqual(self.validate(s,r)['rows'],2)
        r['results'][0].update(status='failed',metrics=None,failure_reason='synthetic injected timeout')
        self.assertEqual(self.validate(s,r)['failed'],1)

    def test_reject_corrupt_pairing_metadata_and_missing_rows(self):
        for mutation in ('seed','input_order','input_hash','method_input_hash','shape','missing','duplicate',
                         'nan','color','range','crop','model_hash','code_hash','runtime_hash','matlab_relabel',
                         'formal_claim','split','missing_config'):
            s,r=run_fixture();row=r['results'][0]
            if mutation=='seed':row['seed']=23
            if mutation=='input_order':r['cases'][0]['input_order']=['B','A']
            if mutation=='input_hash':r['cases'][0]['input_sha256']['A']='bad'
            if mutation=='method_input_hash':row['input_sha256']['A']=digest('different')
            if mutation=='shape':row['output_shape']=[1,16,3]
            if mutation=='missing':r['results'].pop()
            if mutation=='duplicate':r['results'].append(copy.deepcopy(row))
            if mutation=='nan':row['metrics']['psnr_rgb']=float('nan')
            if mutation=='color':row['metrics']['color_domain']='srgb_encoded_rgb'
            if mutation=='range':row['metrics']['data_range']=255
            if mutation=='crop':row['metrics']['crop_border']=1
            if mutation in ('model_hash','code_hash','runtime_hash'):r[mutation.replace('_hash','_sha256')]='0'*64
            if mutation=='matlab_relabel':
                r['runtime'].update(engine='octave',execution_label='matlab_execution')
                r['runtime_sha256']=digest(r['runtime'])
            if mutation=='formal_claim':r['evidence_level']='formal_verified'
            if mutation=='split':r['cases'][0]['split']='test'
            if mutation=='missing_config':
                r['model']['configs']['other']={};r['model_sha256']=digest(r['model'])
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):self.validate(s,r)

    def test_clean_seeds_cannot_inflate_sample_count(self):
        s,r=run_fixture();r['cases'][0]['noise_b_255']=0
        c=copy.deepcopy(r['cases'][0]);c['case_id']='repeat';c['seed']=23;r['cases'].append(c)
        with self.assertRaisesRegex(ValueError,'Clean conditions'):self.validate(s,r)

    def test_holdout_rejected_without_loading_any_images(self):
        s,r=run_fixture();s['split']='test';r['manifest_sha256']=digest([s]);r['cases'][0]['split']='test'
        with self.assertRaisesRegex(ValueError,'Held-out'):self.validate(s,r)


if __name__=='__main__':unittest.main()
