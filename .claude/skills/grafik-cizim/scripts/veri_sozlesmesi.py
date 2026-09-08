"""Auditable, stdlib-only candle/time contract shared by the SVG entry points.

No sorting, deduplication or OHLC repair is implicit. Cutoff uses bar close time.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

PEER = Path(__file__).resolve().parents[2] / "grafik-calisma" / "scripts"
if str(PEER) not in sys.path:
    sys.path.append(str(PEER))


class VeriError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def finite(value, label):
    if isinstance(value, bool) or value is None:
        raise VeriError(f'{label}: sonlu sayı gerekli')
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise VeriError(f'{label}: sonlu sayı gerekli') from exc
    if not math.isfinite(number):
        raise VeriError(f'{label}: NaN/inf kabul edilmez')
    return number


def timestamp_ms(value, unit='auto'):
    # One shared time contract; the public renderer accepts epoch s/ms/us/ns or ISO.
    from candle_contract import epoch_ms
    return epoch_ms(value)


def read_rows(job, base, repo_root):
    veri = job.get('veri') or {}
    if 'mumlar' in veri:
        rows = veri['mumlar']
        return rows, 'job.veri.mumlar', digest(rows)
    if not veri.get('kline'):
        raise VeriError('veri.kline ya da veri.mumlar gerekli; ekran görüntüsü ayrı kalibrasyon iş akışıdır')
    path = Path(veri['kline']).expanduser()
    if not path.is_absolute():
        path = base / path if (base / path).exists() else repo_root / path
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig')
    if text.lstrip().startswith(('[', '{')):
        rows = json.loads(text)
        if isinstance(rows, dict):
            rows = rows.get('data', rows.get('klines'))
    else:
        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            raise VeriError('kaynak dosya boş')
        parsed = list(csv.reader(lines)) if ',' in lines[0] else [line.split() for line in lines]
        keys = [x.strip().lower() for x in parsed[0]]
        if any(k in keys for k in ('open','o')):
            rows = [dict(zip(keys, row)) for row in parsed[1:]]
        else:
            rows = parsed
    return rows, str(path.resolve()), hashlib.sha256(raw).hexdigest()


def normalize_rows(rows, job):
    if not isinstance(rows, list) or not rows:
        raise VeriError('mum listesi boş veya dizi değil')
    from candle_contract import normalize_candles
    normalized, contract = normalize_candles(rows, job)
    if not normalized:
        raise VeriError('cutoff/closed süzgecinden sonra mum yok')
    for row in normalized:
        row['time'] = row['open_time_ms']
        row['close_time'] = row['close_time_ms']
        if 'volume' not in row:
            row['volume']=0.0  # rendering placeholder, never a measured zero
            row['_volume_missing']=True
    contract = dict(contract, input_rows=len(rows), retained_rows=len(normalized),
                    timezone='UTC', timestamp_unit='ms')
    warnings = []
    missing_volume=sum(bool(row.get('_volume_missing')) for row in normalized)
    contract['missing_volume_rows']=missing_volume
    if missing_volume:
        warnings.append(f'{missing_volume} mumda hacim eksik; sıfır ölçüm sayılmaz')
    excluded = sum(contract.get('excluded', {}).values())
    if excluded:
        warnings.append(f'{excluded} mum cutoff/closed nedeniyle dışlandı')
    if contract['status'] != 'verified' or contract.get('cutoff_ms') is None:
        warnings.append('time_unverified: ortak C0 kapanış sözleşmesi yok; grafik TASLAK')
    if contract.get('gaps_before_i'):
        warnings.append('düzensiz zaman aralıkları: x ekseni eşit bar aralıklı; segmentler ayrıldı')
    contract['warnings'] = warnings
    return normalized, contract


def load(job, base, repo_root):
    rows, source, source_hash = read_rows(job, base, repo_root)
    normalized, contract = normalize_rows(rows, job)
    return normalized, source, {'source_sha256':source_hash, 'normalized_sha256':digest(normalized),
                                 'time_contract':contract}
