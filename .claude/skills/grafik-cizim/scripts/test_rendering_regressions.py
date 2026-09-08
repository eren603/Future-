"""Renderer contracts; deterministic fixtures, no market retrieval or forecast tests."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import math
import re
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import cizim as C
import araclar as A
import otomatik_cizim as O
import veri_sozlesmesi as V
import plan_sozlesmesi as P
from tuval import Tuval,ema,rsi


def candles(n=40,values=None):
    values=values or [100+i*.1+math.sin(i/3) for i in range(n)]
    return [dict(open=v,high=v+1,low=v-1,close=v,volume=10,
                 time=1699999200000+i*900000,close_time=1699999200000+(i+1)*900000-1,closed=True)
            for i,v in enumerate(values)]


class RenderingRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='chart-regressions-')
        self.base=Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def job(self,rows=None,**extra):
        rows=rows or candles()
        value={'veri':{'mumlar':rows},'cutoff':rows[-1]['close_time'],
               'timeframe':'15m','price_unit':'USDT','volume_unit':'BTC',
               'cikti':str(self.base/'chart.svg')}
        value.update(extra);return value
    def render(self,job):
        report=C.uygula(job,self.base)
        return report,Path(report['cikti']).read_text()
    def test_cutoff_filters_future_and_open_without_changing_c0_history(self):
        rows=candles(45);cut=rows[39]['close_time'];rows[38]['closed']=False
        job=self.job(rows,cutoff=cut,c0=cut,as_of=cut)
        result,_,audit=V.load(job,self.base,C.KOK)
        self.assertEqual(len(result),39)
        self.assertEqual(result[-1]['source_i'],39)
        self.assertEqual(audit['time_contract']['excluded'],{'open':1,'future':5})
        self.assertLessEqual(result[-1]['close_time_ms'],cut)
    def test_cutoff_alias_conflicts_and_unknown_alias_rejected(self):
        for extra in ({'c0':candles()[-1]['close_time']-1},{'cutoff_typo':0}):
            with self.assertRaises(ValueError):V.load(self.job(**extra),self.base,C.KOK)
    def test_cutoff_requires_close_time_or_explicit_duration(self):
        rows=candles();job=self.job(rows)
        for row in rows:row.pop('close_time')
        job.pop('timeframe')
        with self.assertRaises(ValueError):V.load(job,self.base,C.KOK)
        job['timeframe']='15m'
        self.assertEqual(len(V.load(job,self.base,C.KOK)[0]),40)
    def test_inline_and_file_epoch_seconds_agree(self):
        rows=candles()
        for row in rows:row['time']/=1000;row['close_time']/=1000
        job=self.job(rows)
        inline=V.load(job,self.base,C.KOK)[0]
        path=self.base/'rows.json';path.write_text(json.dumps(rows))
        file_job=dict(job,veri={'kline':str(path)})
        self.assertEqual(inline,V.load(file_job,self.base,C.KOK)[0])
        self.assertEqual(inline[0]['time'],1699999200000)
    def test_missing_volume_is_flagged_not_a_measured_zero(self):
        rows=candles()
        for row in rows:row.pop('volume')
        report,_=self.render(self.job(rows,paneller=[{'tip':'hacim'}]))
        self.assertEqual(report['manifest']['time_contract']['missing_volume_rows'],40)
        self.assertTrue(any('hacim eksik' in warning for warning in report['uyarilar']))
    def test_duplicate_and_invalid_rows_rejected_not_silently_removed(self):
        rows=candles();rows[1]['time']=rows[0]['time']
        with self.assertRaises(ValueError):V.load(self.job(rows),self.base,C.KOK)
        rows=candles();rows[3]['high']=0
        with self.assertRaises(ValueError):V.load(self.job(rows),self.base,C.KOK)
    def test_future_tail_does_not_change_normalized_hash(self):
        rows=candles(50);cut=rows[39]['close_time']
        first=V.load(self.job(rows[:40],cutoff=cut),self.base,C.KOK)[2]
        second=V.load(self.job(rows,cutoff=cut),self.base,C.KOK)[2]
        self.assertEqual(first['normalized_sha256'],second['normalized_sha256'])
    def test_viewport_preserves_indicator_history_and_ema200(self):
        rows=candles(240)
        report,_=self.render(self.job(rows,son_bar=160,cizimler=[{'arac':'ema','period':200}]))
        self.assertEqual(report['bar_sayisi'],160)
        self.assertEqual(report['cizim_sayisi'],1)
        history=V.load(self.job(rows),self.base,C.KOK)[0]
        t=Tuval(history[-160:],history=history,display_start=80)
        self.assertAlmostEqual(A._ma_seri(t,{'period':50})[-1],ema([c['close'] for c in history],50)[-1])
        self.assertEqual(report['manifest']['history_rows'],240)
    def test_automatic_uses_detector_swing_params(self):
        rows=candles(140)
        specs,report=O.uret(rows,{'params':{'left':100,'right':100},'fib':False,'panel':False})
        self.assertFalse(any(s['arac'] in ('metin','trend_cizgisi') for s in specs))
    def test_missing_atr_is_reported_without_crash(self):
        report,svg=self.render(self.job(candles(40),otomatik={'params':{'atr_period':200}}))
        self.assertIn('bilgi_paneli',report['araclar'])
        self.assertIn('VERİ YOK',svg)
    def test_invalid_log_values_rejected(self):
        rows=candles();rows[0].update(open=-1,low=-2,high=1,close=0)
        with self.assertRaises(ValueError):self.render(self.job(rows,log_olcek=True))
        report,_=self.render(self.job(log_olcek=True,cizimler=[{'arac':'yatay_cizgi','fiyat':-5}]))
        self.assertEqual(report['cizim_sayisi'],0)
        self.assertTrue(report['atlanan_cizimler'])
    def test_log_regression_passes_through_calculated_midpoint(self):
        t=Tuval(candles(values=[100,200,300,400]),log_olcek=True,sag_bosluk_bar=2)
        spec={'bar_baslangic':0,'bar_bitis':3}
        t.rezerve(A.regresyon_kanali_fiyat(t,spec));t.hazirla()
        root=ET.fromstring('<g>'+A.regresyon_kanali_ciz(t,spec)+'</g>')
        points=[tuple(map(float,p.split(','))) for p in root.find('polyline').attrib['points'].split()]
        point=min(points,key=lambda p:abs(p[0]-t.x(1.5)))
        self.assertAlmostEqual(t.fiyat_y(point[1]),250,delta=.1)
    def test_projection_is_reserved_and_keeps_actual_values(self):
        t=Tuval(candles(values=[100,110,120,130]),sag_bosluk_bar=10)
        spec={'bar_baslangic':0,'bar_bitis':3,'ileri_bar':10}
        levels=A.regresyon_kanali_fiyat(t,spec)
        self.assertIn(230,levels)
        t.rezerve(levels);t.hazirla()
        self.assertLess(t.y(230),t.ana_alt);self.assertGreater(t.y(230),t.ana_ust)
    def test_fib_channel_level_one_passes_third_anchor(self):
        t=Tuval(candles(values=list(range(100,201,10))))
        spec={'p1':{'bar':0,'fiyat':100},'p2':{'bar':10,'fiyat':200},
              'p3':{'bar':5,'fiyat':130},'seviyeler':[0,1]}
        t.rezerve(A.fib_kanal_fiyat(t,spec));t.hazirla()
        root=ET.fromstring('<g>'+A.fib_kanal_ciz(t,spec)+'</g>');line=root.findall('line')[1]
        x1,y1,x2,y2=[float(line.get(k)) for k in ('x1','y1','x2','y2')]
        y=y1+(y2-y1)*(t.x(5)-x1)/(x2-x1)
        self.assertAlmostEqual(t.fiyat_y(y),130,delta=.1)
    def test_path_honors_distinct_timestamps(self):
        rows=candles();t=Tuval(rows);t.hazirla()
        svg=A.yol_ciz(t,{'noktalar':[{'zaman':rows[0]['time'],'fiyat':100},{'zaman':rows[-1]['time'],'fiyat':105}]})
        points=ET.fromstring(svg).get('points').split()
        self.assertNotEqual(points[0].split(',')[0],points[-1].split(',')[0])
    def test_warnings_after_render_and_actual_counts(self):
        report,_=self.render(self.job(paneller=[{'tip':'unknown-panel'}],cizimler=[{'arac':'ma','period':999},{'arac':'yatay_cizgi','fiyat':102}]))
        self.assertEqual(report['istenen_cizim_sayisi'],2)
        self.assertEqual(report['cizim_sayisi'],1)
        self.assertEqual(len(report['atlanan_cizimler']),1)
        self.assertTrue(any('unknown-panel' in w for w in report['uyarilar']))
    def test_manifest_hashes_match_exact_svg(self):
        report,svg=self.render(self.job())
        self.assertEqual(report['manifest']['output_sha256'],hashlib.sha256(svg.encode()).hexdigest())
        self.assertEqual(json.loads(Path(report['manifest_path']).read_text())['manifest'],report['manifest'])
        self.assertIn('USDT',svg);self.assertIn('UTC',svg)
    def test_invalid_geometry_and_blocked_plan_never_render_positions(self):
        for position in ({'arac':'long_pozisyon','giris':100,'stop':105,'hedef':90},
                         {'arac':'long_pozisyon','giris':100,'stop':95,'hedef':110,'plan_metadata':{'EMIR':'EMİR YOK'}}):
            report,_=self.render(self.job(cizimler=[position]))
            self.assertEqual(report['cizim_sayisi'],0)
            self.assertTrue(report['atlanan_cizimler'])
    def test_unproven_R99_cannot_be_labeled_audited(self):
        report,svg=self.render(self.job(cizimler=[{'arac':'long_pozisyon','giris':100,'stop':95,'hedef':110,'R':99}]))
        self.assertEqual(report['cizim_sayisi'],0);self.assertNotIn('R 99',svg)
    def test_legacy_position_is_visible_draft_with_computed_raw_R(self):
        job=self.job(cizimler=[{'arac':'long_pozisyon','giris':100,'stop':95,'hedef':110,'r_etiketi':'R 99 audited'}]);job.pop('cutoff')
        report,svg=self.render(job)
        self.assertEqual(report['cizim_sayisi'],1)
        self.assertFalse(report['decision_verified']);self.assertIn('TASLAK',svg)
        self.assertIn('denetimsiz',svg);self.assertNotIn('R 99 audited',svg)
    def test_confirmed_position_requires_same_c0_and_direction(self):
        position={'arac':'long_pozisyon','giris':100,'stop':95,'hedef':110}
        job=self.job(cizimler=[position]);source=V.load(job,self.base,C.KOK)[2]['normalized_sha256']
        job['final_decision']={'status':'confirmed','direction':'long','cutoff_ms':job['cutoff'],
                               'input_sha256':source,'geometry':{'entry':100,'stop':95,'target':110}}
        report,_=self.render(job);self.assertTrue(report['decision_verified'])
        job['final_decision']['cutoff_ms']-=1
        self.assertEqual(self.render(job)[0]['cizim_sayisi'],0)
    def test_confirmed_shifted_geometry_or_wrong_source_is_rejected(self):
        job=self.job(cizimler=[{'arac':'long_pozisyon','giris':200,'stop':195,'hedef':210}])
        source=V.load(job,self.base,C.KOK)[2]['normalized_sha256']
        job['final_decision']={'status':'confirmed','direction':'long','cutoff_ms':job['cutoff'],
                               'input_sha256':source,'geometry':{'entry':100,'stop':95,'target':110}}
        self.assertEqual(self.render(job)[0]['cizim_sayisi'],0)
        job['cizimler'][0].update(giris=100,stop=95,hedef=110)
        job['final_decision']['input_sha256']='wrong source'
        self.assertEqual(self.render(job)[0]['cizim_sayisi'],0)
        job['final_decision'].pop('input_sha256')
        self.assertEqual(self.render(job)[0]['cizim_sayisi'],0)
    def test_tiny_price_geometry_mismatch_is_not_hidden_by_absolute_tolerance(self):
        job=self.job(cizimler=[{'arac':'long_pozisyon','giris':2.05e-9,'stop':1e-9,'hedef':3e-9}])
        source=V.load(job,self.base,C.KOK)[2]['normalized_sha256']
        job['final_decision']={'status':'confirmed','direction':'long','cutoff_ms':job['cutoff'],
                               'input_sha256':source,'geometry':{'entry':2e-9,'stop':1e-9,'target':3e-9}}
        self.assertEqual(self.render(job)[0]['cizim_sayisi'],0)
        job['cizimler'][0]['giris']=2e-9
        self.assertTrue(self.render(job)[0]['decision_verified'])
    def test_contradictory_primary_plan_levels_are_not_ignored(self):
        position={'arac':'long_pozisyon','giris':200,'stop':195,'hedef':210,
                  'plan_metadata':{'birincil':{'yon':'long','giris':100,'stop':95,'hedef':110}}}
        report,_=self.render(self.job(cizimler=[position]))
        self.assertEqual(report['cizim_sayisi'],0)
        self.assertFalse(report['decision_verified'])
    def test_conditional_zone_requires_explicit_policy_and_preserves_case(self):
        job=self.job(cizimler=[{'arac':'long_pozisyon','giris':101,'stop':95,'hedef':110}])
        source=V.load(job,self.base,C.KOK)[2]['normalized_sha256'];job['case_sha256']='a'*64
        job['final_decision']={'status':'conditional','direction':'long','cutoff_ms':job['cutoff'],
                               'input_sha256':source,'case_sha256':'a'*64,
                               'geometry':{'entry_zone':[100,102],'entry_policy':'midpoint',
                                           'stop':95,'targets':[110,120],'target_index':0}}
        report,svg=self.render(job)
        self.assertEqual(report['cizim_sayisi'],1);self.assertFalse(report['decision_verified'])
        self.assertTrue(report['manifest']['position_evidence'][0]['geometry_bound'])
        self.assertTrue(report['manifest']['position_evidence'][0]['source_bound'])
        self.assertIn('KOŞULLU',svg)
        job['final_decision']['geometry'].pop('entry_policy')
        self.assertEqual(self.render(job)[0]['cizim_sayisi'],0)
        job['final_decision']['geometry']['entry_policy']='midpoint'
        job['case_sha256']='b'*64
        self.assertEqual(self.render(job)[0]['cizim_sayisi'],0)
    def test_conditional_cutoff_alias_conflict_is_rejected(self):
        job=self.job(cizimler=[{'arac':'long_pozisyon','giris':100,'stop':95,'hedef':110}])
        job['final_decision']={'status':'conditional','direction':'long','cutoff_ms':job['cutoff'],'as_of':job['cutoff']-1}
        self.assertEqual(self.render(job)[0]['cizim_sayisi'],0)
    def test_inkscape_fallback_is_bounded_and_checks_output(self):
        svg_path=self.base/'input.svg';svg_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        def success(args,**kwargs):
            self.assertEqual(kwargs['timeout'],30)
            self.assertFalse(kwargs['check'])
            self.assertNotIn('shell',kwargs)
            output=next(arg.split('=',1)[1] for arg in args if arg.startswith('--export-filename='))
            Path(output).write_bytes(b'\x89PNG\r\n\x1a\nfixture')
            return SimpleNamespace(returncode=0,stderr='')
        with patch.dict(sys.modules,{'cairosvg':None}),patch.object(C.shutil,'which',return_value='/usr/bin/inkscape'),patch.object(C.subprocess,'run',side_effect=success):
            png,engine=C._export_png(svg_path.read_text(),svg_path,1000)
            self.assertTrue(png.exists());self.assertEqual(engine,'inkscape')
        with patch.object(C.shutil,'which',return_value='/usr/bin/inkscape'),patch.object(C.subprocess,'run',return_value=SimpleNamespace(returncode=1,stderr='invalid SVG')):
            with self.assertRaisesRegex(RuntimeError,'invalid SVG'):
                C._inkscape_png(svg_path,self.base/'missing.png',1000)
        with patch.object(C.shutil,'which',return_value='/usr/bin/inkscape'),patch.object(C.subprocess,'run',return_value=SimpleNamespace(returncode=0,stderr='')):
            with self.assertRaisesRegex(RuntimeError,'üretmedi'):
                C._inkscape_png(svg_path,self.base/'missing.png',1000)
    def test_invalid_svg_is_not_hidden_by_png_fallback(self):
        with patch.object(C,'_inkscape_png') as exporter:
            with self.assertRaises(ET.ParseError):
                C._export_png('<svg broken',self.base/'broken.svg',1000)
            exporter.assert_not_called()
    def test_provenance_bound_net_R_is_recomputed_separately(self):
        job=self.job();_,_,manifest=V.load(job,self.base,C.KOK)
        audit={'input_sha256':manifest['normalized_sha256'],'cutoff':job['cutoff'],'direction':'long',
               'entry':100,'stop':95,'target':110,'method':'net_of_costs','win_cost_price':1,'loss_cost_price':1,'R':1.5}
        job['cizimler']=[{'arac':'long_pozisyon','giris':100,'stop':95,'hedef':110,'rr_audit':audit,'R':1.5}]
        report,svg=self.render(job)
        self.assertIn('R ham 2.00',svg);self.assertIn('R net 1.50',svg)
        self.assertEqual(report['manifest']['position_evidence'][0]['stop'],95)
        audit['input_sha256']='bad'
        self.assertEqual(self.render(job)[0]['cizim_sayisi'],0)
    def test_footer_has_reserved_row_below_time_axis_with_and_without_panels(self):
        for panels in ([],[{'tip':'rsi','period':14}]):
            rows=candles()
            t=Tuval(rows,yukseklik=600,dipnot='FOOTER EVIDENCE TEXT',paneller=panels)
            svg=t.render();root=ET.fromstring(svg)
            texts=root.findall('.//{http://www.w3.org/2000/svg}text')
            footer=next(text for text in texts if text.text=='FOOTER EVIDENCE TEXT')
            utc=next(text for text in texts if text.text=='UTC')
            time_labels=[text for text in texts if text.text and 'Kas' in text.text]
            self.assertTrue(time_labels)
            self.assertGreaterEqual(float(footer.get('y'))-float(utc.get('y')),26)
            self.assertTrue(all(float(text.get('y'))==float(utc.get('y')) for text in time_labels))
            self.assertLessEqual(max([t.ana_alt]+[bottom for _,bottom in t.panel_kutu]),float(utc.get('y'))-14)
            plain=Tuval(rows,yukseklik=600,paneller=panels);plain.hazirla()
            self.assertEqual(plain.time_axis_y,592)
            self.assertEqual(plain.ALT,26)
            self.assertEqual(t.ALT,52)
    def test_flat_RSI_is_neutral_and_graphics_are_clipped(self):
        self.assertEqual(rsi([100]*30)[-1],50)
        report,svg=self.render(self.job(cizimler=[{'arac':'long_pozisyon','giris':100,'stop':99.99,'hedef':100.01}]))
        self.assertIn('<clipPath',svg);self.assertIn('clip-path=',svg)
        self.assertEqual(len(ET.fromstring(svg).findall('.//{http://www.w3.org/2000/svg}text'))>0,True)


if __name__=='__main__':
    unittest.main(verbosity=2)
