"""Bind a rendered position to geometry, decision state and numeric provenance.

Confirmed means the stated condition was established, never statistical accuracy.
ATR-floor R is a labelled scenario; it never changes the drawn stop.
"""
from __future__ import annotations
import importlib.util
import math
import unicodedata
from pathlib import Path
from veri_sozlesmesi import finite, timestamp_ms


def direction(value):
    aliases = {'long':'long','buy':'long','al':'long','bull':'long',
               'short':'short','sell':'short','sat':'short','bear':'short'}
    result = aliases.get(str(value).strip().lower())
    if result is None:
        raise ValueError('pozisyon yönü açıkça long veya short olmalı')
    return result


def geometry(spec, side):
    values = [finite(spec[k], k) for k in ('giris','stop','hedef')]
    entry, stop, target = values
    if any(v <= 0 for v in values):
        raise ValueError('pozisyon fiyatları pozitif olmalı')
    if not (stop < entry < target if side == 'long' else stop > entry > target):
        raise ValueError(f'{side}: giriş/stop/hedef sırası geçersiz')
    return entry, stop, target, abs(target-entry)/abs(entry-stop)


def _status(value):
    text = ''.join(c for c in unicodedata.normalize('NFKD',str(value).lower()) if not unicodedata.combining(c)).replace('ı','i').strip()
    if any(k in text for k in ('emir yok','engellendi','blocked','no_call','no-call','gecersiz')):
        return 'blocked'
    aliases = {'confirmed':'confirmed','onayli':'confirmed','approved':'confirmed',
               'conditional':'conditional','kosullu':'conditional','draft':'draft','taslak':'draft'}
    return aliases.get(text)


def _same_price(given, expected, field):
    if not math.isclose(finite(given,field),expected,rel_tol=1e-12,abs_tol=0.0):
        raise ValueError(f'son karar/plan {field} çizilen seviye ile çelişiyor')


def _check_geometry(obj, entry, stop, target, required=False):
    """Validate every declared level; never infer an entry-zone sampling policy."""
    data=obj.get('geometry',obj)
    if not isinstance(data,dict):
        raise ValueError('karar geometry nesne olmalı')
    found=set()
    entry_data=data.get('entry',data.get('giris'))
    zone=data.get('entry_zone')
    if isinstance(entry_data,dict):
        zone=entry_data.get('zone',zone)
    if zone is not None:
        if not isinstance(zone,(list,tuple)) or len(zone)!=2:
            raise ValueError('karar entry_zone iki fiyat içermeli')
        lo,hi=(finite(value,'entry_zone') for value in zone)
        if lo>hi:
            raise ValueError('karar entry_zone artan sırada olmalı')
        policy=data.get('entry_policy',obj.get('entry_policy'))
        if policy=='midpoint':
            expected_entry=(lo+hi)/2
        elif policy=='lower':
            expected_entry=lo
        elif policy=='upper':
            expected_entry=hi
        elif policy=='reference_price':
            ref=data.get('reference_price')
            if ref is None and isinstance(entry_data,dict):
                ref=entry_data.get('reference_price')
            expected_entry=finite(ref,'reference_price')
            if not lo<=expected_entry<=hi:
                raise ValueError('reference_price giriş bölgesinde olmalı')
        else:
            raise ValueError('giriş bölgesi için açık entry_policy gerekli')
        _same_price(expected_entry,entry,'entry');found.add('entry')
    elif entry_data is not None:
        _same_price(entry_data,entry,'entry');found.add('entry')
    invalidation=data.get('invalidation') or {}
    if not isinstance(invalidation,dict):
        raise ValueError('invalidation nesne olmalı')
    stop_data=data.get('stop',invalidation.get('stop'))
    if stop_data is not None:
        _same_price(stop_data,stop,'stop');found.add('stop')
    targets=data.get('targets')
    if targets is not None:
        index=data.get('target_index',obj.get('target_index'))
        if not isinstance(targets,list) or not targets or isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(targets):
            raise ValueError('hedef listesi için geçerli target_index gerekli')
        _same_price(targets[index],target,'target');found.add('target')
    scalar_target=data.get('target',data.get('hedef',data.get('t1')))
    if scalar_target is not None:
        _same_price(scalar_target,target,'target');found.add('target')
    if required and found!={'entry','stop','target'}:
        raise ValueError('confirmed son karar giriş/stop/hedef geometrisine bağlanmalı')
    return found=={'entry','stop','target'}


def _check_source(obj,context,required=False):
    values=[obj[key] for key in ('input_sha256','normalized_sha256') if obj.get(key) is not None]
    if required and not values:
        raise ValueError('confirmed son karar input_sha256 ile çizilen veriye bağlanmalı')
    if any(value!=context.get('normalized_sha256') for value in values):
        raise ValueError('son karar/plan normalize veri hash uyuşmazlığı')
    if obj.get('case_sha256') is not None and obj['case_sha256']!=context.get('case_sha256'):
        raise ValueError('son karar/plan case_sha256 uyuşmazlığı')
    return bool(values)


def prepare(spec, context):
    s = dict(spec)
    side = 'short' if s['arac'] == 'short_pozisyon' else 'long'
    entry, stop, target, raw = geometry(s, side)
    warnings = []
    plan = s.get('plan_metadata') or {}
    decision = context.get('final_decision') or s.get('final_decision') or {}
    if not isinstance(plan, dict) or not isinstance(decision, dict):
        raise ValueError('plan_metadata/final_decision nesne olmalı')
    primary=plan.get('birincil') if isinstance(plan.get('birincil'),dict) else {}
    for obj in (plan,primary,decision,s):
        for key in ('EMIR','status','plan_durumu','rr_denetim'):
            value = obj.get(key)
            if isinstance(value, str) and _status(value) == 'blocked':
                raise ValueError(f'pozisyon engellendi: {key}={value}')
        declared = obj.get('direction', obj.get('plan_yonu', obj.get('yon')))
        if declared is not None and direction(declared) != side:
            raise ValueError('son karar/plan yönü ile pozisyon yönü çelişiyor')
    for obj in (plan,primary):
        _check_geometry(obj,entry,stop,target)
        _check_source(obj,context)
    geometry_bound=_check_geometry(decision,entry,stop,target)
    source_bound=_check_source(decision,context)
    contract = context.get('time_contract') or {}
    time_verified = contract.get('status') in ('verified','time_verified')
    status_value = decision.get('status', decision.get('plan_durumu', 'draft'))
    status = _status(status_value)
    if status is None:
        raise ValueError(f'bilinmeyen son karar durumu: {status_value}')
    expected_cut=contract.get('cutoff_ms',contract.get('cutoff'))
    declared_cuts=[timestamp_ms(decision[key]) for key in ('cutoff','c0','as_of','cutoff_ms')
                   if decision.get(key) is not None]
    if declared_cuts and any(value!=expected_cut for value in declared_cuts):
        raise ValueError('son karar kesim alanları çizilen verinin C0 anıyla uyuşmuyor')
    if status == 'confirmed':
        geometry_bound=_check_geometry(decision,entry,stop,target,required=True)
        source_bound=_check_source(decision,context,required=True)
        dcut = next((decision[k] for k in ('cutoff','c0','as_of','cutoff_ms') if decision.get(k) is not None), None)
        expected_cut = contract.get('cutoff_ms', contract.get('cutoff'))
        if not time_verified or dcut is None or timestamp_ms(dcut) != expected_cut:
            raise ValueError('confirmed pozisyon aynı C0 ve kapanmış veri sözleşmesi gerektirir')
        if not decision.get('direction', decision.get('plan_yonu', decision.get('yon'))):
            raise ValueError('confirmed son karar yönü gerekli')
    elif not time_verified:
        status = 'draft'
    labels = [f'R ham {raw:.2f} (fiyat mesafesi)']
    audit = s.get('rr_audit') or plan.get('rr_audit')
    audited, audit_result = False, None
    declared_r = s.get('R', s.get('r'))
    if audit is not None:
        if not isinstance(audit, dict):
            raise ValueError('rr_audit nesne olmalı')
        if not time_verified:
            raise ValueError('R kaynak doğrulaması zaman sözleşmesi gerektirir')
        if audit.get('input_sha256') != context.get('normalized_sha256'):
            raise ValueError('R denetimi veri hash uyuşmazlığı')
        if timestamp_ms(audit.get('cutoff')) != contract.get('cutoff_ms', contract.get('cutoff')):
            raise ValueError('R denetimi C0 uyuşmazlığı')
        for key, value in (('entry',entry),('stop',stop),('target',target)):
            if not math.isclose(finite(audit.get(key), key), value, rel_tol=1e-12, abs_tol=0.0):
                raise ValueError(f'R denetimi {key} uyuşmazlığı')
        if direction(audit.get('direction')) != side:
            raise ValueError('R denetimi yön uyuşmazlığı')
        method = audit.get('method', 'raw_price_distance')
        if method == 'raw_price_distance':
            result = raw
        elif method == 'net_of_costs':
            win_cost = finite(audit.get('win_cost_price'), 'win_cost_price')
            loss_cost = finite(audit.get('loss_cost_price'), 'loss_cost_price')
            if min(win_cost, loss_cost) < 0:
                raise ValueError('işlem maliyeti negatif olamaz')
            result = (abs(target-entry)-win_cost)/(abs(entry-stop)+loss_cost)
            labels.append(f'R net {result:.2f} (verilen maliyetler)')
        elif method == 'atr_floor_scenario':
            path = Path(__file__).resolve().parents[2] / 'karar-kurulu' / 'scripts' / 'rr_denetim.py'
            module_spec = importlib.util.spec_from_file_location('chart_rr_audit', path)
            module = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(module)
            audit_result = module.denetle({'yon':side,'entry':entry,'stop':stop,'target':target,
                                          'atr':finite(audit.get('atr'),'atr')})
            result = audit_result['R_gercekci']
            labels.append(f'R ATR senaryosu {result:.2f} (varsayım)')
        else:
            raise ValueError(f'bilinmeyen R hesap yöntemi: {method}')
        expected = audit.get('R', audit.get('r'))
        if expected is None or not math.isclose(finite(expected, 'audit.R'), result, abs_tol=.005, rel_tol=1e-9):
            raise ValueError('R denetim değeri yeniden hesapla uyuşmuyor')
        if declared_r is not None and not math.isclose(finite(declared_r,'R'), result, abs_tol=.005, rel_tol=1e-9):
            raise ValueError('plan R değeri denetimle çelişiyor')
        audited = True
    elif declared_r is not None and not math.isclose(finite(declared_r,'R'), raw, abs_tol=.005, rel_tol=1e-9):
        raise ValueError('kaynak denetimi olmayan plan R değeri fiyat mesafesiyle çelişiyor')
    if not audited:
        labels[0] += ' · denetimsiz'
    if s.get('r_etiketi'):
        warnings.append('serbest r_etiketi doğrulama sayılmadı; hesaplanan R etiketlendi')
    s['_position'] = {'status':status,'raw_R':raw,'audited':audited,
                      'time_verified':time_verified,'decision_verified':status=='confirmed' and geometry_bound and source_bound,
                      'geometry_bound':geometry_bound,'source_bound':source_bound,
                      'decision_binding':{'input_sha256':context.get('normalized_sha256') if source_bound else None,
                                          'case_sha256':decision.get('case_sha256'),
                                          'entry':entry,'stop':stop,'target':target},
                      'R_labels':labels, 'audit_result':audit_result}
    s.pop('r_etiketi', None)
    return s, warnings
