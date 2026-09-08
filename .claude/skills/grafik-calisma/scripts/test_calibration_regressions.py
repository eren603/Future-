#!/usr/bin/env python3
"""Bounded synthetic causal/calibration regressions; no market datasets."""
import unittest
from pathlib import Path
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
import kalibrasyon as kb
import setup_dogrulama as sd
import fvg_kalibre as fk
import backtest as bt


def frame(rows):
    return pd.DataFrame([dict(open=o,high=h,low=l,close=c) for o,h,l,c in rows])


def cycles(n=12,scale=1.):
    result=[]; prev=100.
    for i,m in enumerate(([1.]*10+[-1.]*7)*n):
        m*=scale; cl=prev+m
        result.append({'open':prev,'high':max(prev,cl)+.2,'low':min(prev,cl)-.1,
            'close':cl,'volume':100.+i%7,'open_time_ms':1700000000000+i*900000,
            'close_time_ms':1700000000000+(i+1)*900000-1,'closed':True})
        prev=cl
    return result


class Execution(unittest.TestCase):
    def test_close_entry_ignores_elapsed_wick(self):
        r=kb.walk_trade([100.5,100.1,100.1,100.1],[98.,99.9,99.9,99.9],[100.]*4,
            0,100.,99.,102.,3,True,o=[100.]*4,entry_mode='close')
        self.assertEqual(r,(0.,3,0.09999999999999432))
        benchmark=kb.permutation_pvalue([100.5,100.1,100.1,100.1],[98.,99.9,99.9,99.9],
            [100.]*4,[1.,np.nan,np.nan,np.nan],0.,['long']*10,1.,2.,3,n_perm=9,o=[100.]*4)
        self.assertIsNone(benchmark['p']); self.assertFalse(benchmark['valid_for_edge_permission'])
        self.assertEqual(benchmark['null_ortalama'],0.)

    def test_ambiguous_limit_high_does_not_credit_target(self):
        self.assertEqual(kb.walk_trade([103.],[99.5],[100.],0,100.,99.,102.,0,True,o=[103.])[0],0.)
        # The close after a fill can establish that a target was crossed.
        self.assertEqual(kb.walk_trade([103.],[99.5],[102.5],0,100.,99.,102.,0,True,o=[103.])[0],2.)

    def test_stop_precedence_and_lifetime_mae(self):
        r=kb.walk_trade([103.],[90.],[100.],0,100.,99.,102.,0,True,o=[100.])
        self.assertEqual(r,(-1.,0,1.))
        short=kb.walk_trade([110.],[97.],[100.],0,100.,101.,98.,0,False,o=[100.])
        self.assertEqual(short,(-1.,0,1.))

    def test_adverse_gap_uses_open(self):
        r=kb.walk_trade([100.1,95.],[99.9,94.],[100.,94.5],0,100.,99.,102.,1,True,
                        o=[100.,94.5],entry_mode='close')
        self.assertEqual(r,(-5.5,1,5.5))

    def test_incomplete_trade_horizon_not_admitted(self):
        self.assertIsNone(kb.walk_trade([101.],[99.5],[100.],0,100.,99.,102.,2,True))

    def test_cost_sign_and_overlapping_capacity(self):
        df=frame([(100.,100.05,99.99,100.04),(100.04,100.04,100.04,100.04)])
        order={'created_i':0,'deadline_i':0,'dir':'long','entry':100.,'sl':99.98,'tp':100.04,'atr':.02}
        rows=kb.execute_orders(df,[dict(order,id=i) for i in range(10)],max_bars=1,fees_bps=5.,slippage_bps=2.)
        self.assertEqual(len(rows),1)
        self.assertAlmostEqual(rows[0]['gross_R'],2.)
        self.assertLess(rows[0]['R'],-5.)  # actual entry+exit notionals charged
        free=kb.execute_orders(df,[order],max_bars=1,fees_bps=0.,slippage_bps=0.)
        self.assertAlmostEqual(free[0]['R'],2.)

    def test_earlier_fill_wins_not_earlier_submission_future_exit(self):
        df=frame([(110,110,109,109)]*6+[(109,109,105,106)]+[(106,106,104,105)]*2+[(105,105,99,100)]+[(100,100,99,100)]*3)
        slow={'id':'slow','created_i':1,'deadline_i':10,'dir':'long','entry':100.,'sl':90.,'tp':120.,'atr':1.}
        quick={'id':'quick','created_i':3,'deadline_i':8,'dir':'long','entry':105.,'sl':95.,'tp':125.,'atr':1.}
        rows=kb.execute_orders(df,[slow,quick],max_bars=4,fees_bps=0.,slippage_bps=0.)
        self.assertEqual(rows[0]['order_id'],'quick'); self.assertEqual(rows[0]['entry_i'],6)

    def test_calendar_blocks_cancel_pending_and_require_full_horizon(self):
        df=frame([(100,101,99.5,100)]*20)
        late={'id':'late','created_i':8,'deadline_i':12,'dir':'long','entry':100.,'sl':99.,'tp':102.,'atr':1.}
        next_block=dict(late,id='next',created_i=11,deadline_i=11)
        rows=kb.execute_orders(df,[late,next_block],max_bars=3,block_bars=10,fees_bps=0.,slippage_bps=0.)
        self.assertEqual([x['order_id'] for x in rows],['next'])
        self.assertEqual(rows[0]['entry_i'],11)

    def test_known_open_fill_cannot_be_erased_by_later_invalidation(self):
        df=frame([(100,101,99.5,100),(98,106,94,100)])
        order={'id':'open-fill','created_i':1,'deadline_i':1,'dir':'long',
               'entry':99.,'sl':95.,'tp':110.,'atr':1.,'invalidate_price':105.}
        rows=kb.execute_orders(df,[order],max_bars=0,fees_bps=0.,slippage_bps=0.)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['R'],-1.)
        self.assertEqual(rows[0]['exit'],95.)

    def test_gap_spans_excluded(self):
        df=frame([(100,101,99.5,100)]*5)
        order={'created_i':1,'deadline_i':1,'dir':'long','entry':100.,'sl':99.,'tp':102.,'atr':1.}
        self.assertEqual(kb.execute_orders(df,[order],max_bars=2,gaps=[2]),[])


class Calibration(unittest.TestCase):
    def test_uncapped_wilson_requirement(self):
        r=kb.dinamik_min_rr(1,30)
        self.assertAlmostEqual(r['required_rr'],168.24947014259698)
        self.assertEqual(r['min_rr'],r['required_rr']); self.assertEqual(r['candidate_rr'],5.)
        self.assertFalse(r['feasible']); self.assertFalse(r['net_break_even_guarantee'])
        self.assertIsNone(kb.dinamik_min_rr(0,0)['required_rr'])

    def test_pre_entry_atr_is_frozen(self):
        p=dict(sd.DEFAULTS,freeze=1,scan=5,wait=5,max_bars=1,fees_bps=0.,slippage_bps=0.)
        base=frame([(99,100,98,99),(99,99,98,98.5),(98.5,99,93,94),(94,94,93.9,94)])
        other=base.copy(); other.loc[2,'low']=80.
        events=[{'i':0,'direction':'bull','impulse_start':90.}]
        a=sd.st.wilder_atr(base,1).to_numpy(); b=sd.st.wilder_atr(other,1).to_numpy()
        qa=sd._orders(base,events,a,p,1.); qb=sd._orders(other,events,b,p,1.)
        self.assertEqual(qa,qb); self.assertEqual(qa[0]['sl'],89.)

    def test_train_parameters_and_numeric_bridge_ignore_later_prices(self):
        bars=cycles(); cutoff=int(len(bars)*.6); changed=[dict(x) for x in bars]
        for i in range(cutoff,len(changed)):
            for key in ('open','high','low','close'): changed[i][key]*=1.2
        a=sd.simulate({'candles':bars,'params':{'mc_runs':2}})
        b=sd.simulate({'candles':changed,'params':{'mc_runs':2}})
        self.assertEqual(a['confluence_thresholds'],b['confluence_thresholds'])
        self.assertEqual(a['kalibrasyon'],b['kalibrasyon'])
        self.assertEqual(a['evaluation']['baseline_policy'],b['evaluation']['baseline_policy'])
        self.assertTrue(all(isinstance(v,float) for v in a['confluence_thresholds'].values()))
        self.assertEqual(a['evaluation']['train_end_i'],cutoff-1)
        self.assertEqual(a['evaluation']['evaluation_start_i'],cutoff)
        self.assertTrue(all(t['created_i']>=cutoff and t['entry_i']>=cutoff for t in a['islemler_son10']))
        self.assertFalse(a['sinyal_izni'])  # intentionally small holdout

    def test_explicit_training_boundary_stays_fixed_when_data_are_appended(self):
        bars=cycles(12)
        params={'train_end_i':100,'mc_runs':0}
        a=sd.simulate({'candles':bars[:170],'params':params})
        b=sd.simulate({'candles':bars,'params':params})
        self.assertEqual(a['kalibrasyon'],b['kalibrasyon'])
        self.assertEqual(a['evaluation']['train_end_i'],100)
        self.assertEqual(b['evaluation']['train_end_i'],100)

    def test_holdout_gate_can_accept_and_reject_scoped_evidence(self):
        actual=[{'entry_i':b*10+1,'exit_i':b*10+2,'max_exit_i':b*10+3,'R':2.} for b in range(12)]
        base=[dict(x,R=.1) for x in actual]
        good=kb.evaluate_blocks(actual,base,start=0,end=119,block_bars=10)
        self.assertTrue(good['supported']); self.assertEqual(good['n_blocks'],12)
        bad=kb.evaluate_blocks(actual,[dict(x,R=3.) for x in base],start=0,end=119,block_bars=10)
        self.assertFalse(bad['supported'])
        missing=kb.evaluate_blocks(actual,base,start=0,end=119,block_bars=10,axis_valid=False)
        self.assertFalse(missing['supported'])

    def test_block_boundary_purge_uses_maximum_not_realized_horizon(self):
        rows=[{'entry_i':8,'exit_i':8,'max_exit_i':12,'R':5.}]
        r=kb.evaluate_blocks(rows,rows,start=0,end=19,block_bars=10)
        self.assertEqual(r['n_trades_used'],0)

    def test_matched_baseline_uses_identical_executor(self):
        df=frame([(100,101,99.5,100.5)]*50); atr=np.ones(50)
        q={'id':1,'created_i':1,'deadline_i':3,'dir':'long','entry':100.5,'sl':99.,'tp':103.5,'atr':1.}
        policy=kb.freeze_baseline_policy(df,[dict(q,created_i=i,deadline_i=i+2) for i in range(1,10)],train_end=9)
        rows=kb.matched_baseline(df,policy,atr,start=10,end=49,fees_bps=5.,slippage_bps=2.,max_bars=3)
        self.assertGreater(len(rows),1)
        self.assertAlmostEqual(rows[0]['cost_R'],.0014*100.5/1.5)
        self.assertEqual(rows[0]['max_exit_i']-rows[0]['entry_i'],3)

    def test_baseline_is_frozen_from_training_and_early_orders_ignore_late_holdout(self):
        df=pd.DataFrame(cycles(8)); changed=df.copy(); cut=90
        for key in ('open','high','low','close'): changed.loc[cut:,key]*=1.2
        atr=sd.st.wilder_atr(df,3).to_numpy(); later_atr=sd.st.wilder_atr(changed,3).to_numpy()
        train_orders=[]
        for i in range(14,31,2):
            previous=df['close'].iloc[i-1]; a=atr[i-1]
            train_orders.append({'created_i':i,'deadline_i':i+5,'dir':'long','entry':previous-a,
                'sl':previous-2*a,'tp':previous+a,'atr':a})
        policy=kb.freeze_baseline_policy(df,train_orders,train_end=39)
        first=kb.baseline_orders(df,policy,atr,start=40,end=len(df)-1,seed=7)
        second=kb.baseline_orders(changed,policy,later_atr,start=40,end=len(df)-1,seed=7)
        earlier=[q for q in first if q['created_i']<=cut]
        self.assertTrue(earlier)
        self.assertEqual(earlier,[q for q in second if q['created_i']<=cut])
        short=kb.baseline_orders(df.iloc[:110],policy,atr[:110],start=40,end=109,seed=7)
        self.assertEqual(short,[q for q in first if q['created_i']<=109])
        self.assertEqual(policy['training_submission_count'],9)

    def test_censored_fvg_is_not_failed_fill_and_lifetime_counts_nonfills(self):
        df=frame([(100,101,99,100)]*20)
        old={'i':0,'tip':'bull','low':99.,'high':101.,'atr':1.}
        new=dict(old,i=19)
        p=dict(fk.VARSAYILAN,seviyeler=[.5],dolum_ufku=10)
        r=fk.seviye_taramasi(df,np.ones(20),[old,new],p)[0]
        self.assertEqual((r['n_fvg'],r['n_censored'],r['mitigasyon_orani']),(1,1,1.))
        unfilled=dict(old,low=90.,high=92.)
        r=fk.seviye_taramasi(df,np.ones(20),[old,unfilled],p)[0]
        self.assertIsNone(r['lifetime_quantile_bar'])
        self.assertEqual(r['mitigasyon_orani'],.5)

    def test_fvg_fits_prefix_and_preserves_usable_candidate(self):
        bars=cycles(10); cutoff=int(len(bars)*.6); changed=[dict(x) for x in bars]
        for i in range(cutoff,len(changed)):
            for key in ('open','high','low','close'): changed[i][key]*=1.1
        p={'dolum_ufku':8,'max_bars':4,'seviyeler':[.5]}
        a=fk.kalibre({'candles':bars,'params':p}); b=fk.kalibre({'candles':changed,'params':p})
        self.assertEqual(a['secilen_mitigasyon'],b['secilen_mitigasyon'])
        self.assertEqual(a['evaluation']['baseline_policy'],b['evaluation']['baseline_policy'])
        self.assertEqual(a['omur'],b['omur']); self.assertEqual(a['filtre_kanitlari'],b['filtre_kanitlari'])
        self.assertIsInstance(a['confluence_thresholds']['min_rr'],float)
        self.assertFalse(a['sinyal_izni'])

    def test_order_risk_invariant_and_initial_loss(self):
        mc=bt.monte_carlo([-.1],20,7)
        self.assertEqual(mc['max_dd_p50'],-.1)
        self.assertEqual(mc['fixed_terminal_return'],-.1)
        self.assertIsNone(mc['prob_profit'])
        mc=bt.monte_carlo([.1,-.05,.02],20,7)
        self.assertEqual(mc['final_return_p5'],mc['final_return_p95'])
        self.assertFalse(mc['valid_for_future_profit_probability'])

if __name__=='__main__': unittest.main(verbosity=2)
