#!/usr/bin/env python3
"""FVG descriptive calibration followed by a frozen chronological evaluation.

Train-only level/stop/feature candidates remain useful when evidence is small.
Only later, net-cost, nonoverlapping time-block evidence can authorize a signal.
Lifetime estimates explicitly include unfilled complete-follow-up observations.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
import kalibrasyon as kb
import smc_tespit as st

class KalibreError(Exception):
    pass

VARSAYILAN={"seviyeler":[0.,.25,.5,.75,1.],"atr_period":14,"max_bars":20,
    "dolum_ufku":40,"devam_barlari":[5,10],"yapisal_tampon_atr":.10,
    "omur_quantile":.8,"tercil_dusuk":1/3,"tercil_yuksek":2/3,
    "fees_bps":5.,"slippage_bps":2.,"funding_bps_per_bar":0.,
    "train_fraction":.6,"train_end_i":None,"min_blocks":10,"block_bars":None,
    "assume_regular_bars":False,"seed":7}

def _frame(job: dict) -> pd.DataFrame:
    """Mumları yükler. Ham Binance kline dosyası verildiyse parser motorun
    KENDİsinden (karar_motoru.parse_klines) alınır — ikinci bir parser yazmak
    ikinci bir doğruluk kaynağı demektir."""
    if job.get("candles") is not None or job.get("input"):
        return st.load_frame(job)
    p = job.get("klines")
    if not p:
        raise KalibreError("'candles', 'input' ya da 'klines' gerekli")
    kok = Path(__file__).resolve().parents[4]   # scripts→skill→skills→.claude→depo
    motor = kok / "engine"
    if str(motor) not in sys.path:
        sys.path.insert(0, str(motor))
    import karar_motoru as km  # noqa: PLC0415

    bars = km.parse_klines(str(Path(p).expanduser()))
    return st.load_frame({**job, "candles": [{"open": b.o, "high": b.h, "low": b.l,
                                       "close": b.c, "volume": b.v, "open_time_ms": b.t} for b in bars]})


def fvg_ozellikleri(df: pd.DataFrame, atr: np.ndarray, mitigasyon_ref: float) -> list:
    """Her FVG için ölçek-BAĞIMSIZ nitelikler. Bölge tanımı smc_tespit.find_fvgs'ten
    İTHAL edilir (kopyalanmaz) — iki yerde iki tanım = sessiz sapma."""
    h = df["high"].to_numpy(); l = df["low"].to_numpy()
    o = df["open"].to_numpy(); c = df["close"].to_numpy()
    v = df["volume"].to_numpy() if "volume" in df.columns else np.full(len(df), np.nan)
    kayit = []
    for f in st.find_fvgs(df, mitigasyon_ref):
        i = int(f["i"])          # 3. mum (bölgenin kapandığı bar)
        d = i - 1                # DISPLACEMENT mumu = ORTA mum (3. değil!)
        a = float(atr[i]) if np.isfinite(atr[i]) and atr[i] > 0 else np.nan
        genislik = float(f["high"] - f["low"])
        govde = abs(float(c[d] - o[d]))
        menzil = float(h[d] - l[d])
        pencere = v[max(0, d - 20):d]
        vz = np.nan
        if pencere.size >= 5 and np.isfinite(pencere).all() and pencere.std() > 0:
            vz = float((v[d] - pencere.mean()) / pencere.std())
        kayit.append({
            "i": i, "tip": f["type"], "low": float(f["low"]), "high": float(f["high"]),
            "genislik": genislik,
            "genislik_atr": genislik / a if np.isfinite(a) else np.nan,
            "govde_atr": govde / a if np.isfinite(a) else np.nan,
            "govde_menzil": govde / menzil if menzil > 0 else np.nan,
            "hacim_z": vz,
            "atr": a,
        })
    return kayit


def _dolum_bari(h,l,rec,seviye,ufuk):
    if not 0<=float(seviye)<=1: raise KalibreError('mitigation level must be in [0,1]')
    i=int(rec['i']); lo=float(rec['low']); hi=float(rec['high'])
    price=hi-(hi-lo)*seviye if rec['tip']=='bull' else lo+(hi-lo)*seviye
    for j in range(i+1,min(i+int(ufuk),len(h)-1)+1):
        if l[j]<=price if rec['tip']=='bull' else h[j]>=price:
            return j,price
    return None,None


def _devam(c,j,esik,is_long,k):
    if j+k>=len(c): return None
    return bool(c[j+k]>esik if is_long else c[j+k]<esik)


def seviye_taramasi(df,atr,kayit,p):
    """Fill probabilities use only complete formation->horizon cohorts.

    Recently formed events are reported as censored, never failed fills.
    Remaining nonfills are included in the lifetime CDF denominator.
    """
    h,l,c=(df[k].to_numpy() for k in ('high','low','close')); result=[]
    for sv in p['seviyeler']:
        fills=[]; lags=[]; censored=0; complete=0
        continuation={k:[] for k in p['devam_barlari']}
        for rec in kayit:
            if not np.isfinite(rec['atr']) or rec['atr']<=0: continue
            if rec['i']+int(p['dolum_ufku'])>=len(df):
                censored+=1; continue
            complete+=1; j,price=_dolum_bari(h,l,rec,sv,p['dolum_ufku'])
            if j is None: continue
            fills.append((rec,j,price)); lags.append(j-rec['i'])
            for k in continuation:
                d=_devam(c,j,price,rec['tip']=='bull',k)
                if d is not None: continuation[k].append(d)
        q=float(p['omur_quantile']); rank=int(np.ceil(q*complete))
        lifetime=float(sorted(lags)[rank-1]) if rank>0 and rank<=len(lags) else None
        result.append({'seviye':float(sv),'n_fvg':complete,'n_censored':censored,'n_dolan':len(fills),
            'mitigasyon_orani':len(fills)/complete if complete else None,
            'medyan_bar':float(np.median(lags)) if lags else None,
            'lifetime_quantile_bar':lifetime,'lifetime_quantile':q,
            'lifetime_scope':'all complete-follow-up FVGs; None means not reached within horizon',
            'yon_devami':{f'{k}_bar':{'n':len(v),'oran':float(np.mean(v)) if v else None,
                'scope':'descriptive overlapping events; not independent Bernoulli evidence'} for k,v in continuation.items()},
            'dolum_ornekleri':fills})
    return result


def _make_orders(kayit,seviye,kural,mult,rr,p,*,start=0,end=None,filters=None):
    orders=[]
    for rec in kayit:
        i=int(rec['i']); a=float(rec['atr'])
        if i<start or not np.isfinite(a) or a<=0: continue
        if filters and any(not np.isfinite(rec.get(key,np.nan)) or rec[key]<threshold for key,threshold in filters.items()):
            continue
        ready=i+1
        if end is not None and i+int(p['dolum_ufku'])+int(p['max_bars'])>end: continue
        long=rec['tip']=='bull'
        entry=rec['high']-(rec['high']-rec['low'])*seviye if long else rec['low']+(rec['high']-rec['low'])*seviye
        sl=entry-mult*a if long else entry+mult*a
        if kural=='yapisal': sl=rec['low']-p['yapisal_tampon_atr']*a if long else rec['high']+p['yapisal_tampon_atr']*a
        risk=abs(entry-sl); tp=entry+rr*risk if long else entry-rr*risk
        if risk<=0 or min(entry,sl,tp)<=0: continue
        orders.append({'id':i,'created_i':ready,'deadline_i':i+int(p['dolum_ufku']),
            'dir':'long' if long else 'short','entry':float(entry),'sl':float(sl),'tp':float(tp),'atr':a})
    return orders


def _run(df,orders,p,*,start=0,end=None,gaps=(),block_bars=None):
    return kb.execute_orders(df,orders,start=start,end=end,max_bars=int(p['max_bars']),
        fees_bps=float(p['fees_bps']),slippage_bps=float(p['slippage_bps']),
        funding_bps_per_bar=float(p.get('funding_bps_per_bar',0.)),gaps=gaps,block_bars=block_bars)


def _stats(rows):
    rs=np.array([x['R'] for x in rows],dtype=float)
    return {'n':len(rows),'kazanma_orani':float(np.mean(rs>0)) if len(rs) else None,
        'ortalama_r':float(rs.mean()) if len(rs) else None,
        'brut_ortalama_r':float(np.mean([x['gross_R'] for x in rows])) if rows else None,
        'maliyet_toplam_r':sum(x['cost_R'] for x in rows),
        'bootstrap_ci':kb.bootstrap_ci(rs,block_size=max(1,int(np.sqrt(len(rs))))) if len(rs) else None,
        'ci_scope':'descriptive ordered-trade moving-block CI; authorization uses calendar blocks',
        'dirs':[x['dir'] for x in rows],
        'kazanan_mae_atr':[x['mae_atr'] for x in rows if x['R']>0],
        'trades':rows}


def _islemler(df,atr,dolumlar,stop_kural,atr_mult,tp_rr,p):
    """Compatibility helper: filled observations use the same cost/capacity engine.

    ATR is fixed at formation (rec.atr), known before the first eligible fill.
    Its result is explicitly descriptive; overlapping entries compete for one
    position instead of inflating an IID sample count.
    """
    orders=[]
    for rec,j,price in dolumlar:
        a=float(rec['atr']); long=rec['tip']=='bull'
        sl=price-atr_mult*a if long else price+atr_mult*a
        if stop_kural=='yapisal': sl=rec['low']-p['yapisal_tampon_atr']*a if long else rec['high']+p['yapisal_tampon_atr']*a
        risk=abs(price-sl)
        orders.append({'id':rec['i'],'created_i':j,'deadline_i':j,'dir':'long' if long else 'short',
            'entry':price,'sl':sl,'tp':price+(1 if long else -1)*tp_rr*risk,'atr':a})
    return _stats(_run(df,orders,{**VARSAYILAN,**p}))


def tercil_testi(rows,anahtar,*,alpha=None):
    """Train-only feature suggestion, never 'filter proven'.

    Caller supplies capacity-controlled trade rows. Quantile ties are made
    disjoint; feature multiplicity is accounted for by caller's alpha budget.
    The combined selected rule must still be frozen and evaluated later.
    """
    valid=[x for x in rows if np.isfinite(x.get(anahtar,np.nan)) and np.isfinite(x['r'])]
    n=len(valid); minimum=kb.KONVANSIYON['n_taban']
    if n<3*minimum: return {'sonuc':'VERİ YOK','n':n,'onerilen_esik':None}
    vals=np.array([x[anahtar] for x in valid]); rs=np.array([x['r'] for x in valid])
    lo,hi=np.quantile(vals,[1/3,2/3]); alt=rs[vals<=lo]; ust=rs[(vals>=hi)&(vals>lo)]
    if min(len(alt),len(ust))<minimum: return {'sonuc':'VERİ YOK','n':n,'onerilen_esik':None}
    alpha=kb.KONVANSIYON['alpha']/3 if alpha is None else alpha
    ca=kb.bootstrap_ci(alt,alpha=alpha,block_size=max(1,int(np.sqrt(len(alt)))))
    cu=kb.bootstrap_ci(ust,alpha=alpha,block_size=max(1,int(np.sqrt(len(ust)))))
    suggested=cu[0]>max(0.,ca[1])
    return {'sonuc':'EĞİTİM FİLTRE ADAYI' if suggested else 'AYRIM YOK — filtre uygulanmaz',
        'n':n,'onerilen_esik':float(hi) if suggested else None,'esik_q33':float(lo),'esik_q67':float(hi),
        'alt_tercil':{'n':len(alt),'ci':ca},'ust_tercil':{'n':len(ust),'ci':cu},
        'evidence_scope':'training suggestion only; combined policy needs heldout evaluation'}


def kalibre(job):
    p={**VARSAYILAN,**(job.get('params') or {})}
    if not p['seviyeler'] or any(not 0<=float(x)<=1 for x in p['seviyeler']): raise KalibreError('levels must be a nonempty [0,1] list')
    if min(int(p[k]) for k in ('max_bars','dolum_ufku','min_blocks'))<1: raise KalibreError('positive horizons required')
    frac=float(p['train_fraction'])
    if not .2<=frac<=.8: raise KalibreError('train_fraction must be in [0.2,0.8]')
    if not 0<float(p['omur_quantile'])<=1: raise KalibreError('lifetime quantile must be in (0,1]')
    df=_frame(job); n=len(df)
    split=int(p['train_end_i'])+1 if p.get('train_end_i') is not None else int(n*frac)
    if not 3<=split<=n-3: raise KalibreError('training boundary must leave both periods at least 3 bars')
    atr=st.wilder_atr(df,int(p['atr_period'])).to_numpy()
    axis=kb.time_axis(df,p['assume_regular_bars']); gaps=axis['gaps']
    train_df=df.iloc[:split].copy()
    train_rec=fvg_ozellikleri(train_df,atr[:split],st.FVG_MITIGASYON)
    all_rec=fvg_ozellikleri(df,atr,st.FVG_MITIGASYON)
    tarama=seviye_taramasi(train_df,atr[:split],train_rec,p)
    candidates=[]
    for level in tarama:
        level.pop('dolum_ornekleri',None); level['islem']={}
        for rule in ('atr','yapisal'):
            initial=_run(df,_make_orders(train_rec,level['seviye'],rule,1.,2.,p,end=split-1),p,end=split-1,gaps=gaps)
            mult=kb.mae_atr_mult([x['mae_atr'] for x in initial if x['R']>0])
            rr=kb.dinamik_min_rr(sum(x['R']>0 for x in initial),len(initial))
            target=float(rr['candidate_rr']) if initial else 2.
            fitted=_run(df,_make_orders(train_rec,level['seviye'],rule,mult['atr_mult'],target,p,end=split-1),p,end=split-1,gaps=gaps)
            stats=_stats(fitted); stats.pop('trades'); stats.pop('dirs'); stats.pop('kazanan_mae_atr')
            stats.update(atr_mult=mult,min_rr=rr,frozen_tp_rr=target)
            level['islem'][rule]=stats
            if len(fitted)>=kb.KONVANSIYON['n_taban']:
                # Ranking is openly train-only fitting, not corrected significance.
                candidates.append((stats['bootstrap_ci'][0],stats['ortalama_r'],level['seviye'],rule,mult['atr_mult'],target))
    if candidates:
        chosen=max(candidates); _,_,sv,rule,mult,target=chosen
        fit_status='EĞİTİMDE KALİBRE EDİLDİ'
    else:
        sv,rule,mult,target=st.FVG_MITIGASYON,'atr',1.,2.
        fit_status='KALİBRE EDİLEMEDİ (fail-closed)'
    training=_run(df,_make_orders(train_rec,sv,rule,mult,target,p,end=split-1),p,end=split-1,gaps=gaps)
    by_id={r['i']:r for r in train_rec}
    samples=[{**by_id[t['order_id']],'r':t['R']} for t in training]
    features=('genislik_atr','govde_atr','govde_menzil')
    feature_results={k:tercil_testi(samples,k) for k in features}
    filters={k:r['onerilen_esik'] for k,r in feature_results.items() if r.get('onerilen_esik') is not None}
    baseline_training_orders=_make_orders(train_rec,sv,rule,mult,target,p,end=split-1,filters=filters)
    baseline_policy=kb.freeze_baseline_policy(df,baseline_training_orders,train_end=split-1)
    eval_rec=[r for r in all_rec if r['i']>=split]
    orders=_make_orders(eval_rec,sv,rule,mult,target,p,start=split,end=n-1,filters=filters)
    block=int(p['block_bars'] or max(4*int(p['max_bars']),int(p['dolum_ufku'])+int(p['max_bars'])))
    if block<2*int(p['max_bars']): raise KalibreError('block_bars must cover two max_bars horizons')
    actual=_run(df,orders,p,start=split,gaps=gaps,block_bars=block)
    reference=kb.matched_baseline(df,baseline_policy,atr,start=split,end=n-1,fees_bps=p['fees_bps'],slippage_bps=p['slippage_bps'],
        max_bars=int(p['max_bars']),funding_bps_per_bar=p['funding_bps_per_bar'],seed=int(p['seed']),gaps=gaps,block_bars=block)
    evidence=kb.evaluate_blocks(actual,reference,start=split,end=n-1,block_bars=block,
        min_blocks=max(kb.KONVANSIYON['n_taban'],int(p['min_blocks'])),seed=int(p['seed']),axis_valid=axis['valid'])
    if not candidates: evidence.update(supported=False,adequate=False,status='insufficient_training_evidence')
    evidence.update(train_end_i=split-1,evaluation_start_i=split,evaluation_end_i=n-1,parameters_frozen=True,
        time_axis=axis,baseline_policy={k:v for k,v in baseline_policy.items() if k!='templates'},training_trades=len(training),heldout_trades=len(actual),baseline_trades=len(reference),
        split_source='explicit_train_end_i' if p.get('train_end_i') is not None else 'predeclared_fraction_of_input',repeated_retuning_adjusted=False)
    life=next((s for s in tarama if s['seviye']==sv),None)
    if life is None:
        life=seviye_taramasi(train_df,atr[:split],train_rec,{**p,'seviyeler':[sv]})[0]
    lifetime={'bar':life['lifetime_quantile_bar'],'quantile':p['omur_quantile'],
        'scope':'all training FVGs with complete follow-up; not just fills',
        'not_reached_within_horizon':life['lifetime_quantile_bar'] is None,
        'conditional_filled_median_bar':life['medyan_bar'],'n_complete':life['n_fvg'],'n_censored':life['n_censored'],
        'dolum_ufku_bar':p['dolum_ufku']}
    if job.get('tf_dakika') and lifetime['bar'] is not None: lifetime['saat']=lifetime['bar']*float(job['tf_dakika'])/60
    return {'sonuc':fit_status,'n_fvg':len(all_rec),'bar_sayisi':n,'seviye_taramasi':tarama,
        'secilen_mitigasyon':{'seviye':sv,'stop_kurali':rule,'atr_mult':mult,'tp_rr':target,
            'kaynak':'Train-only candidate ranking; no selection on later evaluation',
            'coklu_test':{'method':'train-only selection; one frozen combined policy evaluated once'}},
        'filtre_kanitlari':feature_results,'selected_training_filters':filters,'omur':lifetime,
        'onerilen_params':{'fvg_mitigasyon':sv},'confluence_thresholds':{'atr_mult':float(mult),'min_rr':float(target)},
        'thresholds_kaynak':'training-only FVG candidate; frozen later evaluation',
        'sinyal_izni':bool(evidence['supported']),'validated_edge':bool(evidence['supported']),
        'evidence_status':evidence['status'],'evaluation':evidence,
        'heldout_net':_stats(actual),'baseline_net':_stats(reference),
        'hizalama_kisiti':'FVG mitigation and entry level must change together; suggestions are not automatically applied.',
        'varsayimlar':kb.varsayim_defteri([f"fees={p['fees_bps']}bps/slippage={p['slippage_bps']}bps per side; funding={p['funding_bps_per_bar']}bps/bar",
            f"train_fraction={frac}; block_bars={block}; features alpha budget={kb.KONVANSIYON['alpha']/3}"]),
        'not':'Descriptive calibration is useful but cannot grant permission without adequate later net evidence.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--job',required=True)
    args=ap.parse_args(); job=json.loads(Path(args.job).expanduser().read_text())
    print(json.dumps(kalibre(job),ensure_ascii=False,indent=2)); return 0

if __name__=='__main__': sys.exit(main())
