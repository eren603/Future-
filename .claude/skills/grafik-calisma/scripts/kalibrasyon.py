#!/usr/bin/env python3
"""Causal execution and chronological calibration helpers.

A fitted parameter is a descriptive estimate, not proof of edge. Inference is
restricted to a later frozen-policy period and labelled with its block-sampling
assumptions. Random-entry comparisons are benchmarks, never permutation tests.
"""
from __future__ import annotations
import numpy as np

KONVANSIYON = {"alpha": .05, "ci_guven": .95, "n_taban": 10, "n_boot": 1000,
               "n_perm": 200, "wilson_z": 1.96, "rr_sinir": (1., 5.),
               "atr_mult_sinir": (.5, 3.), "mae_quantile": .9}


def varsayim_defteri(ekstra=None):
    return ["Eşikler yalnız eğitim bölümünde öğrenilir; sonraki dönem içinde sabittir.",
            "Blok bootstrap: bloklar arası yaklaşık bağımsızlık varsayılır; garanti değildir.",
            f"alpha={KONVANSIYON['alpha']}; en az {KONVANSIYON['n_taban']} değerlendirme bloğu (tasarım tabanı)",
            f"ATR aday sınırı={KONVANSIYON['atr_mult_sinir']}; kazanan MAE q={KONVANSIYON['mae_quantile']}",
            "Wilson dönüşümü ikili/brüt ödeme varsayımıdır; net başabaş garantisi değildir.",
            "OHLC içi belirsizlik: stop önce; intrabar limit girişinde önceki tepe/dip TP sayılmaz.",
            "Limit fiyatı açılışta iyileşse de model iyileşme kredisi vermez; gap stop açılıştan çıkar."] + list(ekstra or [])


def wilson_lo(wins, n, z=None):
    if n <= 0:
        return 0.
    if not 0 <= wins <= n:
        raise ValueError("wins must be within [0,n]")
    z = KONVANSIYON['wilson_z'] if z is None else float(z)
    p = wins/n
    return float(max(0., (p+z*z/(2*n)-z*np.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)))


def bootstrap_ci(rs, n_boot=None, seed=7, alpha=None, block_size=1):
    """Moving-block mean CI. block_size=1 is explicit IID; callers use time blocks."""
    rs = np.asarray(rs, dtype=float)
    if not rs.size:
        return None
    if not np.isfinite(rs).all():
        raise ValueError("nonfinite bootstrap observations")
    n_boot = KONVANSIYON['n_boot'] if n_boot is None else int(n_boot)
    alpha = KONVANSIYON['alpha'] if alpha is None else float(alpha)
    if n_boot < 1 or not 0 < alpha < 1:
        raise ValueError("invalid bootstrap configuration")
    size = max(1, min(int(block_size), len(rs)))
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(rs), size=(n_boot, int(np.ceil(len(rs)/size))))
    idx = (starts[..., None]+np.arange(size)) % len(rs)
    means = rs[idx.reshape(n_boot, -1)[:, :len(rs)]].mean(axis=1)
    return [float(x) for x in np.quantile(means, [alpha/2, 1-alpha/2])]


def dinamik_min_rr(wins, n):
    """Unclamped binary-payoff heuristic plus a separately labelled usable candidate."""
    lower, upper = KONVANSIYON['rr_sinir']
    wl = wilson_lo(wins, n)
    required = (1-wl)/wl if wl > 0 else None
    feasible = required is not None and required <= upper
    return {"min_rr": required, "required_rr": required,
            "candidate_rr": float(min(upper, max(lower, required))) if required is not None else upper,
            "feasible": bool(feasible), "wr_wilson_lo": wl,
            "kaynak": "İkili/brüt ödeme varsayımı; candidate_rr tasarım adayıdır, kırpılmış gereksinim değildir.",
            "net_break_even_guarantee": False}


def mae_atr_mult(mae_atr_list):
    arr = np.asarray([x for x in mae_atr_list if np.isfinite(x) and x >= 0], dtype=float)
    if not len(arr):
        return {"atr_mult": 1., "n": 0, "kaynak": "MAE yok; açık tasarım varsayımı"}
    q = float(np.quantile(arr, KONVANSIYON['mae_quantile']))
    return {"atr_mult": float(np.clip(q, *KONVANSIYON['atr_mult_sinir'])),
            "mae_q": q, "n": len(arr), "kaynak": "Yalnız eğitim kazananlarının MAE üst sınırı"}


def walk_trade(h, l, c, entry_i, entry, sl, tp, max_bars, is_long, *,
               o=None, entry_mode='limit', require_full_horizon=True):
    """Return (gross R, exit_i, conservative MAE while open).

    close: entry occurs after entry_i OHLC. limit: a resting limit fills in
    entry_i; its earlier favorable extreme cannot credit a target. If the open
    is supplied, a marketable limit at the open can use subsequent full OHLC.
    Missing opens never invent favorable gap execution. A stop crossing is
    filled at its level except an adverse open beyond it, filled at that open.
    MAE ends at the stop/exit, never the candle's later adverse extreme.
    """
    h,l,c = map(lambda a: np.asarray(a,dtype=float), (h,l,c))
    if o is not None:
        o = np.asarray(o,dtype=float)
    n = len(c); i=int(entry_i); horizon=int(max_bars)
    if entry_mode not in ('limit','close') or horizon < 0 or not 0 <= i < n:
        raise ValueError("invalid entry/horizon")
    sign=1. if is_long else -1.
    risk=sign*(entry-sl)
    if not all(np.isfinite(x) for x in (entry,sl,tp)) or risk <= 0 or sign*(tp-entry) <= 0:
        return None
    end=i+horizon
    if end >= n and require_full_horizon:
        return None
    end=min(end,n-1)
    worst=entry
    def adverse(price):
        nonlocal worst
        worst=min(worst,price) if is_long else max(worst,price)
    def finish(price,k):
        return float(sign*(price-entry)/risk), int(k), float(max(0.,sign*(entry-worst)))
    start=i+1 if entry_mode=='close' else i
    for k in range(start,end+1):
        intrabar_entry = k==i and entry_mode=='limit'
        opened = None if o is None else float(o[k])
        at_open = intrabar_entry and opened is not None and (opened <= entry if is_long else opened >= entry)
        if intrabar_entry and not (l[k] <= entry if is_long else h[k] >= entry):
            return None
        # Once filled, adverse opening gaps execute at the first available open.
        if opened is not None and (not intrabar_entry or at_open):
            if opened <= sl if is_long else opened >= sl:
                adverse(opened)
                return finish(opened,k)
            if not intrabar_entry and (opened >= tp if is_long else opened <= tp):
                return finish(tp,k)  # no favorable gap improvement credit
        if l[k] <= sl if is_long else h[k] >= sl:
            adverse(sl)
            return finish(sl,k)
        hit_tp = h[k] >= tp if is_long else l[k] <= tp
        # The close is after a limit fill; the favorable wick may precede it.
        safe_tp = not intrabar_entry or at_open or (c[k] >= tp if is_long else c[k] <= tp)
        if hit_tp and safe_tp:
            # With no stop crossing, this is an upper bound on MAE before TP.
            adverse(l[k] if is_long else h[k])
            return finish(tp,k)
        adverse(l[k] if is_long else h[k])
    return finish(float(c[end]),end)


def time_axis(df, assume_regular=False):
    """Validate spacing when timestamps exist; synthetic index-only input is explicit."""
    key=next((k for k in ('open_time_ms','timestamp','time','t') if k in df),None)
    if key is None:
        return {"valid": bool(assume_regular), "source": "explicit_regular_bar_assumption" if assume_regular else "timestamps_missing", "gaps": []}
    try:
        ts=np.asarray(df[key],dtype=float)
        dif=np.diff(ts)
        if len(dif)==0 or not np.isfinite(ts).all() or np.any(dif<=0):
            return {"valid":False,"source":key,"gaps":[],"reason":"invalid chronological timestamps"}
        step=float(np.median(dif))
        gaps=(np.flatnonzero(np.abs(dif-step)>max(1e-6,step*.01))+1).tolist()
        return {"valid":not gaps,"source":key,"step":step,"gaps":gaps}
    except (ValueError,TypeError):
        return {"valid":False,"source":key,"gaps":[],"reason":"timestamp normalization required"}


def execute_orders(df, orders, *, start=0, end=None, fees_bps=5., slippage_bps=2.,
                   max_bars=20, funding_bps_per_bar=0., gaps=(), block_bars=None):
    """One portfolio position; pending orders compete by first fill, not future exit.

    Orders carry prices fixed from information available at created_i, plus
    deadline_i and optional invalidate_price. A complete potential follow-up
    is required before any order can fill. Gaps invalidate that observation.
    """
    end=len(df)-1 if end is None else int(end)
    if block_bars is not None:
        end=start+((end-start+1)//int(block_bars))*int(block_bars)-1
    if min(fees_bps,slippage_bps,funding_bps_per_bar) < 0:
        raise ValueError("costs must be nonnegative")
    h,l,c,o=(df[k].to_numpy(dtype=float) for k in ('high','low','close','open'))
    active=[]; by_start={}
    for idx,raw in enumerate(orders):
        q=dict(raw,id=raw.get('id',idx))
        created=int(q['created_i'])
        if created >= start and created <= end:
            by_start.setdefault(created,[]).append(q)
    trades=[]; busy=-1
    for j in range(start,end+1):
        if block_bars is not None and (j-start)%int(block_bars)==0:
            active=[]; busy=-1
        block_end=end if block_bars is None else min(end,start+((j-start)//int(block_bars)+1)*int(block_bars)-1)
        active.extend(by_start.get(j,[]))
        next_active=[]
        for q in active:
            if j > int(q['deadline_i']):
                continue
            long=q['dir']=='long'; inv=q.get('invalidate_price')
            entry=float(q['entry'])
            filled_at_open = o[j]<=entry if long else o[j]>=entry
            if inv is not None and (h[j]>inv if long else l[j]<inv) and not filled_at_open:
                continue  # resting intrabar order: invalidation/fill order is ambiguous
            if j<=busy:
                continue  # only one active position; pending orders are cancelled
            touched=l[j]<=entry if long else h[j]>=entry
            if not touched:
                next_active.append(q); continue
            if j+max_bars>block_end or any(j<=g<=j+max_bars for g in gaps):
                continue
            walked=walk_trade(h,l,c,j,entry,q['sl'],q['tp'],max_bars,long,o=o)
            if walked is None:
                continue
            gross,exit_i,mae=walked
            risk=abs(entry-q['sl']); exit_price=entry+(1 if long else -1)*gross*risk
            cost=(fees_bps+slippage_bps)/1e4*(entry+abs(exit_price))/risk
            funding=funding_bps_per_bar/1e4*entry/risk*(exit_i-j)
            a=float(q.get('atr',risk))
            trades.append({"order_id":q['id'],"created_i":q['created_i'],"entry_i":j,
                           "exit_i":exit_i,"max_exit_i":j+max_bars,"dir":q['dir'],"entry":entry,"exit":exit_price,
                           "sl":q['sl'],"tp":q['tp'],"gross_R":gross,"cost_R":cost+funding,
                           "R":gross-cost-funding,"mae_atr":mae/a,
                           "mae_kind":"conservative_OHLC_bound","atr_fallback":False})
            busy=exit_i
        active=next_active
    return trades


def freeze_baseline_policy(df, training_orders, *, train_start=0, train_end):
    """Freeze order descriptors AND submission intensity using training only.

    No holdout trade count, direction mix, formation or later price geometry
    enters the policy. Prices are normalized to the last completed training
    close/ATR at submission. The subsequent schedule uses a fixed seed and
    one Bernoulli submission opportunity per bar at this training rate.
    """
    templates=[]
    for q in training_orders:
        i=int(q['created_i']); a=float(q['atr'])
        if not max(train_start,1)<=i<=train_end or not np.isfinite(a) or a<=0:
            continue
        prev=float(df['close'].iloc[i-1])
        template={'dir':q['dir'],'lifetime':max(0,int(q['deadline_i'])-i)}
        for key in ('entry','sl','tp','invalidate_price'):
            if q.get(key) is not None:
                template[key]=(float(q[key])-prev)/a
        templates.append(template)
    exposure=max(1,int(train_end)-max(int(train_start),1)+1)
    return {'templates':templates,'submit_probability_per_bar':min(1.,len(templates)/exposure),
            'train_start_i':int(train_start),'train_end_i':int(train_end),
            'training_exposure_bars':exposure,'training_submission_count':len(templates),
            'source':'training_only_frozen_descriptors_and_submission_intensity'}


def baseline_orders(df, policy, atr, *, start, end, seed=7):
    """Causal train-frozen benchmark schedule; earlier orders are prefix invariant.

    Every scheduled order uses only close/ATR from j-1. The number of future
    holdout events never controls the schedule. The common executor handles
    gaps, full horizons, invalidation and portfolio capacity for both sides.
    """
    if not isinstance(policy,dict) or policy.get('train_end_i',start)>=start:
        raise ValueError('baseline policy must be frozen strictly before evaluation')
    templates=policy.get('templates',[])
    if not templates: return []
    probability=float(policy['submit_probability_per_bar'])
    if not 0<=probability<=1: raise ValueError('invalid baseline submission probability')
    rng=np.random.default_rng(seed); orders=[]
    for j in range(max(start,1),end+1):
        submit=rng.random()<probability
        template=templates[int(rng.integers(0,len(templates)))]
        if not submit or not np.isfinite(atr[j-1]) or atr[j-1]<=0: continue
        a=float(atr[j-1]); prev=float(df['close'].iloc[j-1])
        q={'id':f'baseline-{j}','created_i':j,'deadline_i':j+template['lifetime'],
           'dir':template['dir'],'atr':a}
        for key in ('entry','sl','tp','invalidate_price'):
            if key in template: q[key]=prev+template[key]*a
        if min(q['entry'],q['sl'],q['tp'])>0: orders.append(q)
    return orders


def matched_baseline(df, policy, atr, *, start, end, fees_bps, slippage_bps,
                     max_bars, seed=7, funding_bps_per_bar=0., gaps=(), block_bars=None):
    """Train-frozen random-timing policy evaluated with identical execution.

    Descriptor distribution and submission rate are fixed before holdout.
    Fills/counts can differ through realized prices and the common capacity
    rule. Paired calendar blocks include zero-trade periods. No permutation
    p-value or knowledge of future holdout opportunities is assumed.
    """
    shifted=baseline_orders(df,policy,atr,start=start,end=end,seed=seed)
    return execute_orders(df,shifted,start=start,end=end,fees_bps=fees_bps,
                          slippage_bps=slippage_bps,max_bars=max_bars,
                          funding_bps_per_bar=funding_bps_per_bar,gaps=gaps,block_bars=block_bars)


def evaluate_blocks(trades, baseline, *, start, end, block_bars, min_blocks=10,
                    min_trades=10, seed=7, axis_valid=True):
    """Paired calendar-block net-R comparison; no IID-per-trade significance."""
    block_bars=max(1,int(block_bars)); n=(end-start+1)//block_bars
    actual=np.zeros(n); reference=np.zeros(n)
    # Trades crossing boundaries are purged from BOTH series, avoiding double use.
    def aggregate(rows,out):
        used=0
        for t in rows:
            b=(t['entry_i']-start)//block_bars
            if 0<=b<n and (t.get('max_exit_i',t['exit_i'])-start)//block_bars==b:
                out[b]+=t['R']; used+=1
        return used
    used=aggregate(trades,actual); base_used=aggregate(baseline,reference)
    ci=bootstrap_ci(actual,seed=seed) if n else None
    delta=bootstrap_ci(actual-reference,seed=seed) if n else None
    adequate=n>=min_blocks and used>=min_trades and base_used>=min_trades and axis_valid
    halves=[float(x.mean()) if len(x) else None for x in np.array_split(actual,2)]
    supported=bool(adequate and ci[0]>0 and delta[0]>0 and all(x is not None and x>0 for x in halves))
    return {"status":"heldout_support" if supported else ("heldout_inconclusive" if adequate else "insufficient_evidence"),
            "supported":supported,"adequate":bool(adequate),"n_blocks":n,"block_bars":block_bars,
            "n_trades_used":used,"n_baseline_trades_used":base_used,
            "net_R_per_block_ci":ci,"paired_excess_R_per_block_ci":delta,
            "net_R_blocks":actual.tolist(),"baseline_net_R_blocks":reference.tolist(),
            "half_period_net_R_per_block":halves,
            "assumptions":"Frozen policy; approximately independent calendar blocks; train-frozen random-timing benchmark; no future guarantee.",
            "inference_unit":"nonoverlapping_calendar_block", "purged_boundary_trades":len(trades)-used}


def permutation_pvalue(h,l,c,atr,actual_mean_r,dirs,atr_mult,tp_rr,max_bars,n_perm=None,seed=7,*,o=None):
    """Deprecated descriptive close-entry benchmark. No inferential p or permission.

    Kept for external callers; timing is causal and full follow-up is required.
    Setup/FVG validation uses matched_baseline and paired time-block inference.
    """
    rng=np.random.default_rng(seed); n_perm=KONVANSIYON['n_perm'] if n_perm is None else int(n_perm)
    valid=[i for i in range(len(c)-int(max_bars)) if np.isfinite(atr[i]) and atr[i]>0]
    means=[]
    for _ in range(n_perm):
        rs=[]
        for d in dirs:
            if not valid: break
            i=int(rng.choice(valid)); entry=float(c[i]); risk=atr_mult*float(atr[i]); sign=1 if d=='long' else -1
            t=walk_trade(h,l,c,i,entry,entry-sign*risk,entry+sign*tp_rr*risk,max_bars,d=='long',o=o,entry_mode='close')
            if t is not None: rs.append(t[0])
        if rs: means.append(float(np.mean(rs)))
    return {"p":None,"descriptive_tail_fraction":float(np.mean(np.asarray(means)>=actual_mean_r)) if means else None,
            "null_ortalama":float(np.mean(means)) if means else None,
            "n_perm":n_perm,"valid_for_edge_permission":False,
            "not":"Deprecated random-close descriptive benchmark; no matched cost/capacity contract, no permutation p-value."}
