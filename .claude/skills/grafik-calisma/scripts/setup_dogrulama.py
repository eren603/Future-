#!/usr/bin/env python3
"""Golden-zone calibration: chronological train -> freeze -> later evaluation.

The historical evaluation is scoped evidence under declared execution and
block assumptions. It is never labelled proven edge. Useful fitted thresholds
are reported even when the later period is too small to authorize a signal.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import numpy as np

_HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(_HERE))
import smc_tespit as st
import kalibrasyon as kb
sys.path.insert(0,str(_HERE.parents[1]/'backtest-motoru'/'scripts'))
import backtest as bt

GZ_LO,GZ_HI=.618,.786
DEFAULTS={"left":2,"right":2,"atr_period":14,"scan":30,"freeze":3,"wait":40,
          "atr_mult":1.,"tp_rr":1.5,"max_bars":60,"fees_bps":5.,"slippage_bps":2.,
          "funding_bps_per_bar":0.,"risk_frac":.01,"min_trades":None,"mc_runs":1000,
          "seed":7,"direction":"auto","kalibrasyon":True,"train_fraction":.6,"train_end_i":None,
          "min_blocks":10,"block_bars":None,"assume_regular_bars":False}


def _orders(df,events,atr,p,atr_mult,*,start=0,end=None):
    """Resting orders use only confirmed event/freeze history and prior ATR.

    All orders are constructed before portfolio execution, so an earlier
    submitted slow-fill order cannot reserve capacity based on its future exit.
    """
    end=len(df)-1 if end is None else int(end)
    h,l=(df[k].to_numpy(dtype=float) for k in ('high','low'))
    result=[]
    for ev in events:
        b=int(ev['i']); d=ev['direction']; long=d=='bull'
        if b<start or b>end or ev.get('impulse_start') is None: continue
        if p['direction'] in ('long','short') and p['direction']!=('long' if long else 'short'): continue
        s=float(ev['impulse_start']); e_i=b; ext=float(h[b] if long else l[b]); frozen=None
        for i in range(b+1,min(b+int(p['scan']),end)+1):
            v=float(h[i] if long else l[i])
            if v>ext if long else v<ext:
                ext=v; e_i=i
            elif i-e_i>=int(p['freeze']):
                frozen=i; break
        if frozen is None or frozen+1>end: continue
        ready=frozen+1; a=float(atr[ready-1])
        if not np.isfinite(a) or a<=0: continue
        span=ext-s if long else s-ext
        if span<=0: continue
        entry=ext-GZ_LO*span if long else ext+GZ_LO*span
        sl=s-atr_mult*a if long else s+atr_mult*a
        risk=abs(entry-sl); tp=entry+float(p['tp_rr'])*risk if long else entry-float(p['tp_rr'])*risk
        if min(entry,sl,tp)<=0: continue
        result.append({"id":b,"created_i":ready,"deadline_i":e_i+int(p['wait']),
                       "dir":"long" if long else "short","entry":entry,"sl":sl,"tp":tp,
                       "atr":a,"invalidate_price":ext})
    return result


def _sim_pass(df,events,atr_arr,p,atr_mult,*,start=0,end=None,return_orders=False,gaps=(),block_bars=None):
    orders=_orders(df,events,atr_arr,p,atr_mult,start=start,end=end)
    rows=kb.execute_orders(df,orders,start=start,end=end,fees_bps=float(p['fees_bps']),
                           slippage_bps=float(p['slippage_bps']),max_bars=int(p['max_bars']),
                           funding_bps_per_bar=float(p.get('funding_bps_per_bar',0.)),gaps=gaps,block_bars=block_bars)
    return (rows,orders) if return_orders else rows


def _summary(rows):
    if not rows: return {"n":0,"net_mean_R":None,"gross_mean_R":None}
    rs=np.array([r['R'] for r in rows]); gross=np.array([r['gross_R'] for r in rows])
    return {"n":len(rows),"net_mean_R":float(rs.mean()),"gross_mean_R":float(gross.mean()),
            "win_rate":float((rs>0).mean()),"total_cost_R":sum(r['cost_R'] for r in rows)}


def simulate(job):
    p={**DEFAULTS,**(job.get('params') or {})}
    frac=float(p['train_fraction'])
    if not .2<=frac<=.8: raise ValueError('train_fraction must be in [0.2,0.8]')
    if min(int(p[k]) for k in ('scan','freeze','wait','max_bars','min_blocks'))<1:
        raise ValueError('positive horizons and block count required')
    df=st.load_frame(job); n=len(df)
    split=int(p['train_end_i'])+1 if p.get('train_end_i') is not None else int(n*frac)
    if not 3<=split<=n-3: raise ValueError('training boundary must leave both periods at least 3 bars')
    axis=kb.time_axis(df,p['assume_regular_bars']); gaps=axis['gaps']
    atr=st.wilder_atr(df,int(p['atr_period'])).to_numpy()
    # Training events themselves are detected on the prefix, not a full-series view.
    train_df=df.iloc[:split].copy()
    th,tl=st.find_swings(train_df,int(p['left']),int(p['right']))
    _,train_events=st.structure_events(train_df,th,tl,int(p['right']))
    highs,lows=st.find_swings(df,int(p['left']),int(p['right']))
    trend,events=st.structure_events(df,highs,lows,int(p['right']))
    wide=_sim_pass(df,train_events,atr,p,kb.KONVANSIYON['atr_mult_sinir'][1],end=split-1,gaps=gaps)
    mae=kb.mae_atr_mult([t['mae_atr'] for t in wide if t['R']>0])
    mult=float(mae['atr_mult']) if p['kalibrasyon'] else float(p['atr_mult'])
    preliminary=_sim_pass(df,train_events,atr,p,mult,end=split-1,gaps=gaps)
    rr=kb.dinamik_min_rr(sum(t['R']>0 for t in preliminary),len(preliminary))
    # Train-only target adaptation, then freeze; never publish a clamped requirement.
    fitted_rr=float(rr['candidate_rr']) if p['kalibrasyon'] and preliminary else float(p['tp_rr'])
    frozen={**p,'tp_rr':fitted_rr}
    training,training_orders=_sim_pass(df,train_events,atr,frozen,mult,end=split-1,gaps=gaps,return_orders=True)
    baseline_policy=kb.freeze_baseline_policy(df,training_orders,train_end=split-1)
    block=int(p['block_bars'] or max(4*int(p['max_bars']),int(p['wait'])+int(p['max_bars'])))
    if block<2*int(p['max_bars']): raise ValueError('block_bars must cover at least two max_bars horizons')
    heldout,orders=_sim_pass(df,events,atr,frozen,mult,start=split,return_orders=True,gaps=gaps,block_bars=block)
    reference=kb.matched_baseline(df,baseline_policy,atr,start=split,end=n-1,
        fees_bps=float(p['fees_bps']),slippage_bps=float(p['slippage_bps']),max_bars=int(p['max_bars']),
        funding_bps_per_bar=float(p['funding_bps_per_bar']),seed=int(p['seed']),gaps=gaps,block_bars=block)
    evidence=kb.evaluate_blocks(heldout,reference,start=split,end=n-1,block_bars=block,
        min_blocks=max(kb.KONVANSIYON['n_taban'],int(p['min_blocks'])),
        min_trades=max(kb.KONVANSIYON['n_taban'],int(p['min_trades'] or 0)),seed=int(p['seed']),axis_valid=axis['valid'])
    # An empty/too-small fitted cohort cannot support a learned-policy claim.
    if p['kalibrasyon'] and len(training)<kb.KONVANSIYON['n_taban']:
        evidence.update(supported=False,adequate=False,status='insufficient_training_evidence')
    evidence.update(train_start_i=0,train_end_i=split-1,evaluation_start_i=split,evaluation_end_i=n-1,
                    parameters_frozen=True,training=_summary(training),heldout=_summary(heldout),
                    baseline=_summary(reference),time_axis=axis,
                    benchmark='train_frozen_random_timing_same_limit_execution_costs_capacity',
                    baseline_policy={k:v for k,v in baseline_policy.items() if k!='templates'},
                    split_source=('explicit_train_end_i' if p.get('train_end_i') is not None else 'predeclared_fraction_of_input'),
                    repeated_retuning_adjusted=False)
    supported=bool(evidence['supported']); summary=_summary(heldout)
    rs=[t['R'] for t in heldout]
    return {"SONUC":"AYRILMIŞ DÖNEMDE DESTEK VAR" if supported else "KANIT YETERSİZ — KOŞULLU ANALİZ",
            "sinyal_izni":supported,"validated_edge":supported,"evidence_status":evidence['status'],
            "gerekce":"Net getiri ve eşleştirilmiş referans farkı ayrılmış zaman bloklarıyla değerlendirildi; yalnız bu tarihsel dönem için.",
            "trend":trend,"olay_sayisi":len(events),"islem_sayisi":len(heldout),
            "beklenti_R":summary['net_mean_R'],"brut_beklenti_R":summary['gross_mean_R'],
            "kullanilan_atr_mult":mult,"evaluation":evidence,
            "kalibrasyon":{"atr_mult_kalibre":mae,"onerilen_min_rr":rr,
                            "fit_source":"training_only","frozen_tp_rr":fitted_rr},
            "confluence_thresholds":{"atr_mult":mult,"min_rr":fitted_rr},
            "thresholds_kaynak":"chronological training; frozen evaluated target candidate (not break-even guarantee)",
            "esik_kaynagi":"eğitim verisi; ayrılmış dönemde sabit" if p['kalibrasyon'] else "statik varsayım; ayrılmış dönem",
            "monte_carlo":bt.monte_carlo([r*float(p['risk_frac']) for r in rs],int(p['mc_runs']),int(p['seed'])),
            "islemler_son10":heldout[-10:],
            "varsayimlar":kb.varsayim_defteri([f"train_fraction={frac}; block_bars={block}",
                f"fees={p['fees_bps']}bps/slippage={p['slippage_bps']}bps per side; funding={p['funding_bps_per_bar']}bps/bar",
                "Training MAE upper bound can include ambiguous pre-target excursion; no unobserved intrabar path is claimed."]),
            "not":"Ayrılmış tarihsel dönem desteği gelecekte başarı garantisi değildir. Koşullu grafik seviyeleri ayrıca kullanılabilir."}


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--job',required=True)
    args=ap.parse_args(); job=json.loads(Path(args.job).expanduser().read_text())
    print(json.dumps(simulate(job),ensure_ascii=False,indent=2)); return 0

if __name__=='__main__': sys.exit(main())
