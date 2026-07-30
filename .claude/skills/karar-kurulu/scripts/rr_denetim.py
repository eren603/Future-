#!/usr/bin/env python3
"""R:R tutarlılık denetçisi — "şişirilmiş R" panzehiri.

Sorun (bu aracın var oluş sebebi): bir kurulumun R:R'si, DAR bir stop (scalp
ölçeği) UZAK bir hedefle (swing ölçeği) eşleştirilerek yapay yükseltilebilir.
Örn. 1.0×ATR stop + 4×ATR hedef → "R=4.0" görünür, ama o stop tek normal
mumda (≈1×ATR) süpürülür; gerçekte kurulum o hedefe kadar yaşamaz. Bu, doğruluk
sözleşmesinin yasakladığı "serbest ayar / aşırı-uyum"dur.

Bu araç MEKANİK olarak sınar: stop ATR cinsinden yeterince geniş mi? Uzak hedef
+ dar stop uyumsuz mu? Uyumsuzsa "ŞİŞİRİLMİŞ" işaretler ve stopu gerçekçi bir
ATR tabanına çekerek GERÇEKÇİ R'yi yeniden hesaplar. Determinist; uydurma yok.

Girdi JSON:
{
  "yon": "short",            # short|long
  "entry": 65161, "stop": 65291, "target": 64636,
  "atr": 131.2,
  "esikler": {               # opsiyonel override (varsayım etiketlenir)
    "min_stop_atr": 0.8,     # stop bunun altındaysa: gürültüde süpürülür
    "swing_stop_atr": 2.0,   # UZAK hedefte stop en az bu olmalı
    "far_target_atr": 3.0    # hedef bu kadar ATR ötesindeyse "uzak/swing"
  }
}
Çıktı: verdict (TUTARLI|ŞİŞİRİLMİŞ|GEÇERSİZ) + rapor edilen R + gerçekçi R + gerekçe.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path


class RRError(Exception):
    pass


ESIK = {"min_stop_atr": 0.8, "swing_stop_atr": 2.0, "far_target_atr": 3.0}


def denetle(job: dict) -> dict:
    yon = str(job.get("yon", "")).strip().lower()
    if yon not in ("short", "long", "sat", "al", "sell", "buy"):
        raise RRError(f"yon short|long olmalı: {job.get('yon')!r}")
    yon = "short" if yon in ("short", "sat", "sell") else "long"
    try:
        entry = float(job["entry"]); stop = float(job["stop"]); target = float(job["target"])
        atr = float(job["atr"])
    except (KeyError, TypeError, ValueError) as e:
        raise RRError(f"entry/stop/target/atr sayısal gerekli: {e}")
    # NaN/inf denetimi (S1): NaN için `atr <= 0` False'tur → NaN ATR kapıdan
    # geçer, tüm ATR-ölçek karşılaştırmaları (NaN < eşik) False olur, verdict
    # daima TUTARLI kalır ve şişirilmiş-R panzehiri sessizce DEVRE DIŞI olurdu.
    if not all(math.isfinite(x) for x in (entry, stop, target, atr)):
        raise RRError("entry/stop/target/atr sonlu (NaN/inf değil) olmalı")
    if atr <= 0:
        raise RRError("atr > 0 olmalı")
    e = {**ESIK, **(job.get("esikler") or {})}

    reasons = []
    # Yön geometrisi: short → stop>entry>target ; long → stop<entry<target
    geom_ok = (stop > entry > target) if yon == "short" else (stop < entry < target)
    if not geom_ok:
        return {
            "verdict": "GEÇERSİZ", "yon": yon,
            "R_rapor": None, "R_gercekci": None,
            "gerekce": [f"{yon} geometrisi bozuk: stop {stop} / entry {entry} / target {target} "
                        "sırası yanlış (short: stop>entry>target, long: tersi)"],
            "esik_kaynagi": "yön geometrisi (tanım)",
            "esikler": e,
            "not": "Karar-destek; R doğrulaması. Canlı emir DAHİL DEĞİL.",
        }

    risk = abs(entry - stop)
    reward = abs(target - entry)
    if risk == 0:
        raise RRError("risk (entry-stop) sıfır")
    R = reward / risk
    stop_atr = risk / atr
    reward_atr = reward / atr

    verdict = "TUTARLI"
    if stop_atr < e["min_stop_atr"]:
        verdict = "ŞİŞİRİLMİŞ"
        reasons.append(f"stop {stop_atr:.2f}×ATR < {e['min_stop_atr']}×ATR → gürültüde süpürülür")
    if reward_atr >= e["far_target_atr"] and stop_atr < e["swing_stop_atr"]:
        verdict = "ŞİŞİRİLMİŞ"
        reasons.append(f"UZAK hedef {reward_atr:.2f}×ATR + DAR stop {stop_atr:.2f}×ATR "
                       f"(<{e['swing_stop_atr']}×ATR) → scalp-stopu swing-hedefiyle eşleşmiş; R yapay yüksek")

    # Gerçekçi R: uzak hedefte swing tabanı, yakında min taban ile stopu yerde tut.
    floor_atr = e["swing_stop_atr"] if reward_atr >= e["far_target_atr"] else e["min_stop_atr"]
    real_stop_dist = max(risk, floor_atr * atr)
    R_gercekci = reward / real_stop_dist

    if verdict == "TUTARLI":
        reasons.append(f"stop {stop_atr:.2f}×ATR, hedef {reward_atr:.2f}×ATR — ölçekler uyumlu")

    return {
        "verdict": verdict, "yon": yon,
        "R_rapor": round(R, 2), "R_gercekci": round(R_gercekci, 2),
        "stop_atr": round(stop_atr, 2), "hedef_atr": round(reward_atr, 2),
        "gerekli_stop_mesafe": round(real_stop_dist, 1),
        "gerekce": reasons,
        "esik_kaynagi": ("ATR-ölçek konvansiyonu (stop gürültüyü aşmalı; uzak hedef "
                         "geniş stop ister) — esikler ile koşu başına değiştirilebilir"),
        "esikler": e,
        "not": ("Rapor edilen R şişirilmişse GERÇEKÇİ R kullanılır. Karar-destek; "
                "canlı/otomatik emir DAHİL DEĞİL."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="R:R tutarlılık denetçisi (şişirilmiş-R panzehiri)")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = json.loads(Path(args.job).expanduser().resolve().read_text(encoding="utf-8"))
    print(json.dumps(denetle(job), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
