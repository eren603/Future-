#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Piramit sistemi öz-testi — iddia edilen her mekanizma KANITLANIR.

Sınananlar:
  T1 zirveye tırmanma  : gerçek depo verisiyle K1→K5, ZIRVE üretilir
  T2 K1 fail-closed    : veri yoksa K1 kapısı kapanır, üst katman KOŞMAZ
  T3 K2 fail-closed    : tek motor koşarsa K2 kapısı kapanır
  T4 SI kalibrasyonu   : n ≥ n_taban olan defterde ağırlık formülle ÖLÇÜLÜR
  T5 SI geri beslemesi : üretilen ağırlık BİR SONRAKİ koşunun güvenini böler
  T6 işlem kalitesi    : "TEMİZ GİRİŞ VAR" ancak rr TUTARLI + R ≥ R_MIN ise
  T7 determinizm       : aynı girdi = aynı zirve

Çalıştırma: python self_test.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import piramit as P  # noqa: E402

sys.path.insert(0, str(P.SKILLS / "grafik-calisma" / "scripts"))
import kalibrasyon as kb  # noqa: E402

GECEN, KALAN = [], []


def kontrol(ad: str, kosul: bool, ayrinti: str = "") -> None:
    (GECEN if kosul else KALAN).append(f"{ad}{(' — ' + ayrinti) if ayrinti else ''}")
    print(f"{'✔' if kosul else '✖'} {ad}{(' — ' + ayrinti) if ayrinti else ''}")


def _job(tmp: Path, veri: dict, **ek) -> Path:
    j = {"soru": "öz-test", "sembol": "TEST", "veri": veri,
         "state_dir": str(tmp / "state"), **ek}
    p = tmp / "job.json"
    p.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
    return p


def _kos(job_path: Path) -> dict:
    return P.kos(json.loads(job_path.read_text(encoding="utf-8")), job_path.parent)


def main() -> int:
    m15 = P.ENGINE / "girdi" / "m15.json"
    h4 = P.ENGINE / "girdi" / "h4.json"
    if not (m15.exists() and h4.exists()):
        print(f"ATLANDI: {P.ENGINE/'girdi'} altında m15/h4 yok — test verisi gerekli.")
        return 1

    agirlik_p = P.STATE_DIR / "agirlik.json"
    yedek = agirlik_p.read_text(encoding="utf-8") if agirlik_p.exists() else None
    tmp = Path(tempfile.mkdtemp(prefix="piramit_test_"))
    try:
        if agirlik_p.exists():
            agirlik_p.unlink()   # T1 temiz başlasın (ağırlık 1.0 nötr)

        # ---- T1: zirveye tırmanma -----------------------------------------
        (tmp / "state").mkdir(parents=True, exist_ok=True)
        r1 = _kos(_job(tmp, {"m15": str(m15), "h4": str(h4)}))
        katmanlar = [k["katman"] for k in r1["katmanlar"]]
        kontrol("T1 zirveye tırmanma",
                katmanlar == P.KATMANLAR and r1["ZIRVE"].get("YON_BIAS") in
                ("LONG", "SHORT", "NÖTR"),
                f"katmanlar={len(katmanlar)}/5, YON_BIAS={r1['ZIRVE'].get('YON_BIAS')}")

        # ---- T2: K1 fail-closed (dosya yok → hiç üst katman koşmaz) --------
        r2 = _kos(_job(tmp, {"m15": "yok_boyle_bir_dosya.json"}))
        kontrol("T2 K1 fail-closed",
                (not r2["katmanlar"][0]["gecti"]) and len(r2["katmanlar"]) == 1
                and r2["ZIRVE"]["YON_BIAS"] == P.YOK
                and r2["ZIRVE"]["ulasilan_katman"] == "K1-LLM",
                f"durdu={r2['durum']}")

        # ---- T3: K2 fail-closed — K1 GEÇER (csv var) ama motorlar üretemez -
        # 8 satırlık CSV: tablo okunur (K1 ✔) ama hiçbir SMC motoru istatistik
        # kuramaz → K2 kapısı kapanmalı. Aksi halde "yetersiz veriyle karar".
        kisa = tmp / "kisa.csv"
        kisa.write_text("open,high,low,close,volume\n" +
                        "\n".join(f"{100+i},{101+i},{99+i},{100+i},{10+i}"
                                  for i in range(8)) + "\n", encoding="utf-8")
        r3 = _kos(_job(tmp, {"ohlcv_csv": str(kisa)}))
        k1_3 = r3["katmanlar"][0]
        k2_3 = next((k for k in r3["katmanlar"] if k["katman"] == "K2-AI-AJAN"), None)
        kontrol("T3 K2 fail-closed (K1 geçti, motorlar üretemedi)",
                k1_3["gecti"] and k2_3 is not None and not k2_3["gecti"]
                and r3["ZIRVE"]["ulasilan_katman"] == "K2-AI-AJAN",
                f"K1={k1_3['gecti']}, K2 motor sayısı="
                f"{k2_3['motor_sayisi'] if k2_3 else P.YOK}, durum={r3['durum']}")

        # ---- T4: SI kalibrasyonu (n ≥ n_taban) -----------------------------
        st = tmp / "kal_state"
        st.mkdir(parents=True, exist_ok=True)
        rs = [0.9, -1.0, 1.4, -1.0, 0.7, 1.1, -1.0, 0.6, -1.0, 1.2, 0.8, -1.0]
        with (st / "defter.jsonl").open("w", encoding="utf-8") as f:
            for i, r in enumerate(rs):
                f.write(json.dumps({"karar_zamani": i, "gercek_r": r,
                                    "karar": {"karar": "LONG"}}) + "\n")
        wins = sum(1 for r in rs if r > 0)
        beklenen = round(max(P.KONVANSIYON["agirlik_alt"],
                             min(P.KONVANSIYON["agirlik_ust"],
                                 2.0 * kb.wilson_lo(wins, len(rs)))), 4)
        jp = _job(tmp, {"m15": str(m15), "h4": str(h4)})
        j = json.loads(jp.read_text(encoding="utf-8"))
        j["state_dir"] = str(st)
        jp.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
        r4 = _kos(jp)
        kal = [k for k in r4["katmanlar"] if k["katman"] == "K5-SI"][0]["kalibrasyon"]
        olculen = kal["agirliklar"].get("karar-motoru")
        kontrol("T4 SI kalibrasyonu (n≥n_taban)",
                olculen == beklenen and kal["ayrinti"]["karar-motoru"]["n"] == len(rs)
                and kal["ayrinti"]["karar-motoru"]["wins"] == wins,
                f"{wins}/{len(rs)} → wilson_lo="
                f"{round(kb.wilson_lo(wins, len(rs)), 4)} → ağırlık={olculen} "
                f"(beklenen {beklenen})")

        # ---- T5: geri besleme bir SONRAKİ koşuyu değiştirir ----------------
        r5 = _kos(jp)
        d5 = {d["name"]: d for d in
              [k for k in r5["katmanlar"] if k["katman"] == "K3-COKLU-AJAN"][0]["danismanlar"]}
        km = d5.get("karar-motoru", {})
        uygulandi = (km.get("_agirlik") == beklenen and
                     km.get("confidence") == round(km.get("_ham_confidence", 0) * beklenen, 4))
        kontrol("T5 SI geri beslemesi K3'e uygulandı", bool(uygulandi),
                f"ham={km.get('_ham_confidence')} × ağırlık={km.get('_agirlik')} "
                f"= {km.get('confidence')}")

        # ---- T6: işlem kalitesi hükmü kanıta bağlı -------------------------
        ik = [k for k in r1["katmanlar"] if k["katman"] == "K5-SI"][0]["islem_kalitesi"]
        if ik["hukum"] == "TEMİZ GİRİŞ VAR":
            a = ik["adaylar"][0]
            ok = a["rr_verdict"] == "TUTARLI" and a["R_gercekci"] >= P.KONVANSIYON["r_min"]
            det = f"aday {a['motor']} R={a['R_gercekci']} rr={a['rr_verdict']}"
        else:
            ok = bool(ik["engeller"]) or not ik["seviyeler"]
            det = f"BEKLE gerekçeli: {ik['engeller'] or 'seviye yok'}"
        kontrol("T6 işlem kalitesi hükmü kanıta bağlı", ok, det)

        # ---- T7: determinizm ------------------------------------------------
        r7 = _kos(jp)
        a, b = r5["ZIRVE"], r7["ZIRVE"]
        kontrol("T7 determinizm",
                (a["YON_BIAS"], a["yon_skoru"], a["ISLEM_KALITESI"]) ==
                (b["YON_BIAS"], b["yon_skoru"], b["ISLEM_KALITESI"]),
                f"{a['YON_BIAS']}/{a['yon_skoru']} == {b['YON_BIAS']}/{b['yon_skoru']}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if yedek is not None:
            agirlik_p.write_text(yedek, encoding="utf-8")
        elif agirlik_p.exists():
            agirlik_p.unlink()

    print("-" * 60)
    print(f"GEÇEN {len(GECEN)} / {len(GECEN) + len(KALAN)}")
    if KALAN:
        print("KALAN:")
        for k in KALAN:
            print("  ✖", k)
    return 0 if not KALAN else 1


if __name__ == "__main__":
    sys.exit(main())
