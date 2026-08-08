#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""İLK-GEÇİŞ MONTE CARLO — bir emrin hedefe mi stopa mı ÖNCE değeceği yarışı.

STRATEJI.md §2: "Taze emir ancak O KOŞUNUN ölçümü hedef-önceyi favori
gösteriyorsa alınır (MC/analog ilk-geçiş yarışında p_hedef > p_stop)."

R≥1.35 geometrisi driftless dünyada DAİMA stop-favoridir: p_hedef =
(giriş−stop)/(hedef−stop) = 1/(1+R). Dengeyi çeviren tek şey O KOŞUNUN
verisinde ölçülen SÜRÜKLENİŞ + oynaklık şeklidir. Bu motor onu ölçer.

Yöntem — ANALOG BAR BOOTSTRAP (kapalı-fiyat değil, gerçek bar şekilleri):
  Her tarihsel bar bir "analog"dur: önceki kapanışa göre (yüksek, düşük,
  kapanış) çarpanları. Simülasyon her adımda rastgele bir tarihsel bar seçer,
  onun intrabar menzilini (high/low) mevcut fiyata uygular ve bariyerleri
  KAPANIŞLA DEĞİL intrabar dokunuşla dener. Aynı barda hem stop hem hedef
  değerse → STOP (muhafazakâr, akibet_etiketle ile aynı kural).

İki koşu RAPORLANIR (drift'in ne yaptığı gizlenmez):
  · HAM      : tarihsel barlar olduğu gibi (bu pencerenin sürüklenişi dahil)
  · DEMEAN   : her bar getirisinden ortalama çıkarılır (saf geometri+oynaklık;
               driftsiz taban — R≥1.35 burada stop-favori çıkmalı)

Determinist: numpy tohumu sabit (repo kuralı). Duvar saati yok.

Kullanım:
    python ilk_gecis.py --m15 engine/girdi/eth/m15.json \
        --yon LONG --giris 1921.12 --stop 1887.79 --hedef 1966.12 \
        --ufuk 96 --n 20000
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

YOK = "VERİ YOK"


def _barlar(yol: Path) -> np.ndarray:
    """Binance 12-alanlı kline → (open, high, low, close) matrisi."""
    d = json.loads(Path(yol).read_text(encoding="utf-8"))
    out = []
    for r in d:
        if isinstance(r, list) and len(r) >= 5:
            out.append([float(r[1]), float(r[2]), float(r[3]), float(r[4])])
        elif isinstance(r, dict):
            o = r.get("open", r.get("o")); h = r.get("high", r.get("h"))
            lo = r.get("low", r.get("l")); c = r.get("close", r.get("c"))
            if None not in (o, h, lo, c):
                out.append([float(o), float(h), float(lo), float(c)])
    return np.array(out, dtype=float)


def analog_carpanlar(barlar: np.ndarray, demean: bool) -> tuple:
    """Her bar için önceki kapanışa göre (yüksek, düşük, kapanış) log-oranları.

    demean=True: kapanış getirisinin ortalaması high/low/close'un ÜÇÜNDEN de
    çıkarılır (bar şekli — intrabar menzil — korunur, yalnız sürükleniş sıfırlanır).
    """
    close = barlar[:, 3]
    prev = close[:-1]
    hi = np.log(barlar[1:, 1] / prev)   # yüksek / önceki kapanış
    lo = np.log(barlar[1:, 2] / prev)   # düşük / önceki kapanış
    cl = np.log(barlar[1:, 3] / prev)   # kapanış / önceki kapanış
    if demean:
        mu = cl.mean()
        hi = hi - mu; lo = lo - mu; cl = cl - mu
    return hi, lo, cl, float(cl.mean())


def kos(barlar: np.ndarray, yon: str, giris: float, stop: float, hedef: float,
        ufuk: int, n: int, seed: int, demean: bool) -> dict:
    yon = yon.upper()
    if yon not in ("LONG", "SHORT"):
        return {"durum": f"{YOK} — yön LONG|SHORT değil ({yon})"}
    # geçerlilik: LONG'ta stop<giriş<hedef, SHORT'ta hedef<giriş<stop
    if yon == "LONG" and not (stop < giris < hedef):
        return {"durum": f"{YOK} — LONG için stop<giriş<hedef değil"}
    if yon == "SHORT" and not (hedef < giris < stop):
        return {"durum": f"{YOK} — SHORT için hedef<giriş<stop değil"}
    if len(barlar) < 30:
        return {"durum": f"{YOK} — {len(barlar)} bar < 30 (analog havuzu yetersiz)"}

    hi, lo, cl, mu = analog_carpanlar(barlar, demean)
    m = len(hi)
    rng = np.random.default_rng(seed)

    # her yolda ufuk kadar bar; rastgele analog indeksleri
    idx = rng.integers(0, m, size=(n, ufuk))
    fiyat = np.full(n, giris, dtype=float)
    sonuc = np.zeros(n, dtype=np.int8)   # 0=açık, 1=hedef, -1=stop
    for h in range(ufuk):
        aktif = sonuc == 0
        if not aktif.any():
            break
        j = idx[aktif, h]
        p = fiyat[aktif]
        bar_hi = p * np.exp(hi[j])
        bar_lo = p * np.exp(lo[j])
        bar_cl = p * np.exp(cl[j])
        if yon == "LONG":
            stop_vur = bar_lo <= stop
            hedef_vur = bar_hi >= hedef
        else:
            stop_vur = bar_hi >= stop
            hedef_vur = bar_lo <= hedef
        # aynı barda ikisi de → STOP (muhafazakâr)
        yeni = np.where(stop_vur, -1, np.where(hedef_vur, 1, 0)).astype(np.int8)
        s = sonuc[aktif]; s[yeni != 0] = yeni[yeni != 0]; sonuc[aktif] = s
        p2 = np.where(yeni == 0, bar_cl, p); fiyat[aktif] = p2

    p_hedef = float((sonuc == 1).mean())
    p_stop = float((sonuc == -1).mean())
    p_acik = float((sonuc == 0).mean())
    R = (hedef - giris) / (giris - stop) if yon == "LONG" else (giris - hedef) / (stop - giris)
    R = abs(R)
    ev_r = p_hedef * R - p_stop   # açık kalanlar 0 (nötr) sayılır
    return {
        "durum": "ÖLÇÜLDÜ", "kip": "DEMEAN (driftsiz)" if demean else "HAM (sürükleniş dahil)",
        "p_hedef": round(p_hedef, 4), "p_stop": round(p_stop, 4),
        "p_acik_ufuk_sonu": round(p_acik, 4),
        "R": round(R, 4), "EV_R": round(ev_r, 4),
        "favori": ("HEDEF" if p_hedef > p_stop else "STOP" if p_stop > p_hedef else "BERABERE"),
        "bar_getiri_ort_gunluk_yaklasik": round(mu * 96, 5),
        "n_yol": n, "ufuk_bar": ufuk, "analog_havuz": m,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="İlk-geçiş Monte Carlo (analog bar bootstrap)")
    ap.add_argument("--m15", required=True)
    ap.add_argument("--yon", required=True)
    ap.add_argument("--giris", type=float, required=True)
    ap.add_argument("--stop", type=float, required=True)
    ap.add_argument("--hedef", type=float, required=True)
    ap.add_argument("--ufuk", type=int, default=96)   # akibet_etiketle azami_tutma
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(argv)

    barlar = _barlar(Path(a.m15))
    ortak = dict(yon=a.yon, giris=a.giris, stop=a.stop, hedef=a.hedef,
                 ufuk=a.ufuk, n=a.n, seed=a.seed)
    rapor = {
        "girdi": {"m15": a.m15, **ortak, "analitik_driftless_p_hedef": round(
            (a.giris - a.stop) / (a.hedef - a.stop) if a.yon.upper() == "LONG"
            else (a.stop - a.giris) / (a.stop - a.hedef), 4)},
        "HAM": kos(barlar, demean=False, **ortak),
        "DEMEAN": kos(barlar, demean=True, **ortak),
    }
    print(json.dumps(rapor, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
