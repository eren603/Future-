#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PİRAMİT VERİ TOPLAYICI — telefonda (Pydroid 3) ya da masaüstünde çalışır.

BTCUSDT + ETHUSDT için beş kanalı TEK seferde çeker, TEK dosyaya yazar,
İndirilenler klasörüne kaydeder (sembol başına 5 kanal = toplam 10 çekim):

  1. 15M kline   (fiyat yapısı + CVD'nin taker hacmi)
  2. 4H kline    (üst zaman dilimi bağlamı)
  3. openInterestHist  (açık faiz serisi + hizalı fiyat — motorun en ağır faktörü)
  4. premiumIndex      (funding / fonlama oranı)
  5. takerlongshortRatio (taker alıcı/satıcı oranı)

Kurulum GEREKMEZ: yalnız Python standart kütüphanesi kullanılır (urllib).
Pydroid 3'te dosyayı açıp ▶ tuşuna basmak yeterli.

Çıktı: /storage/emulated/0/Download/piramit_veri_BTC_ETH_<zaman>.json
Başka çift isterseniz: python veri_topla.py BTCUSDT ETHUSDT SOLUSDT
(yazılamazsa sırayla ~/Download, /sdcard/Download, betiğin bulunduğu klasör)

Bu dosyayı Claude'a yükleyin; `paket_ac.py` onu depoya açar ve piramit boru
hattı bir sonraki istemde kendiliğinden koşar.

Dürüstlük: veri OLDUĞU GİBİ kaydedilir — kırpma, düzeltme, doldurma YOK.
Çekilemeyen kanal `hatalar` listesine yazılır; sessiz başarısızlık yok.

Ayarlar (isterseniz aşağıdan değiştirin):
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# ---------------------------------------------------------------- AYARLAR --
SEMBOLLER = ["BTCUSDT", "ETHUSDT"]   # tek koşuda çekilecek çiftler (sırayla)
SEMBOL = "BTCUSDT"      # geriye uyumluluk (tek sembol kullanımı)
KLINE_15M = 200         # kaç 15 dakikalık bar (motorun asgarisi ~104)
KLINE_4H = 200          # kaç 4 saatlik bar (motorun asgarisi ~25)
TUREV_LIMIT = 48        # OI / LSR serisi kaç nokta (48 × 15dk = 12 saat)
ZAMAN_ASIMI = 25        # saniye
# ---------------------------------------------------------------------------

# Binance vadeli API aynaları — biri engellenirse sıradaki denenir
SUNUCULAR = ["https://fapi.binance.com", "https://fapi1.binance.com",
             "https://fapi2.binance.com", "https://fapi3.binance.com"]

INDIRME_KLASORLERI = [
    "/storage/emulated/0/Download",     # Android (Pydroid 3)
    "/sdcard/Download",                 # Android (eski yol)
    os.path.expanduser("~/Download"),
    os.path.expanduser("~/Downloads"),
    os.path.expanduser("~/İndirilenler"),
    os.path.dirname(os.path.abspath(__file__)),
]


def uc_listesi(sembol: str) -> dict:
    return {
        "m15": f"/fapi/v1/klines?symbol={sembol}&interval=15m&limit={KLINE_15M}",
        "h4": f"/fapi/v1/klines?symbol={sembol}&interval=4h&limit={KLINE_4H}",
        "openInterestHist": (f"/futures/data/openInterestHist?symbol={sembol}"
                             f"&period=15m&limit={TUREV_LIMIT}"),
        "premiumIndex": f"/fapi/v1/premiumIndex?symbol={sembol}",
        "takerlongshortRatio": (f"/futures/data/takerlongshortRatio?symbol={sembol}"
                                f"&period=15m&limit={TUREV_LIMIT}"),
    }


def cek(yol: str) -> tuple:
    """Aynaları sırayla dene; (veri, kullanılan_sunucu) ya da (None, hata)."""
    son_hata = "bilinmeyen hata"
    for sunucu in SUNUCULAR:
        url = sunucu + yol
        try:
            istek = urllib.request.Request(
                url, headers={"User-Agent": "piramit-veri-toplayici/1.0"})
            with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as r:  # noqa: S310
                return json.loads(r.read().decode("utf-8")), sunucu
        except urllib.error.HTTPError as e:
            son_hata = f"HTTP {e.code} ({sunucu})"
        except (urllib.error.URLError, OSError) as e:
            son_hata = f"{type(e).__name__}: {str(e)[:90]} ({sunucu})"
        except (ValueError, json.JSONDecodeError) as e:
            son_hata = f"JSON değil ({sunucu}): {str(e)[:60]}"
    return None, son_hata


def indirme_klasoru() -> str:
    for k in INDIRME_KLASORLERI:
        try:
            os.makedirs(k, exist_ok=True)
            deneme = os.path.join(k, ".piramit_yazma_testi")
            with open(deneme, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(deneme)
            return k
        except OSError:
            continue
    return os.getcwd()


def sembol_cek(sembol: str) -> tuple:
    """Bir sembolün beş kanalını çek; (veri, hatalar, sunucular)."""
    veri, hatalar, sunucular = {}, [], {}
    for ad, yol in uc_listesi(sembol).items():
        print(f"  → {sembol} {ad} çekiliyor...", end=" ", flush=True)
        d, bilgi = cek(yol)
        if d is None:
            print(f"BAŞARISIZ ({bilgi})")
            hatalar.append(f"{sembol}/{ad}: {bilgi}")
        else:
            n = len(d) if isinstance(d, list) else 1
            print(f"tamam ({n} kayıt)")
            veri[ad] = d
            sunucular[ad] = bilgi
    return veri, hatalar, sunucular


def sembol_ozet(veri: dict) -> dict:
    """Kullanıcı dosyayı vermeden önce doğrulayabilsin diye kısa özet."""
    o = {}
    for ad in ("m15", "h4"):
        d = veri.get(ad)
        if isinstance(d, list) and d:
            o[ad] = {"bar": len(d), "alan": len(d[-1]),
                     "son_bar_ms": d[-1][0], "son_kapanis": d[-1][4]}
    if isinstance(veri.get("openInterestHist"), list) and veri["openInterestHist"]:
        o["openInterestHist"] = {"nokta": len(veri["openInterestHist"]),
                                 "son_oi": veri["openInterestHist"][-1].get("sumOpenInterest")}
    if isinstance(veri.get("premiumIndex"), dict):
        o["premiumIndex"] = {"lastFundingRate": veri["premiumIndex"].get("lastFundingRate"),
                             "markPrice": veri["premiumIndex"].get("markPrice")}
    if isinstance(veri.get("takerlongshortRatio"), list) and veri["takerlongshortRatio"]:
        o["takerlongshortRatio"] = {"nokta": len(veri["takerlongshortRatio"]),
                                    "son_oran": veri["takerlongshortRatio"][-1].get("buySellRatio")}
    return o


def main() -> int:
    semboller = ([s.upper() for s in sys.argv[1:]] if len(sys.argv) > 1
                 else list(SEMBOLLER))
    print("=" * 58)
    print(f"PİRAMİT VERİ TOPLAYICI — {', '.join(semboller)}")
    print("=" * 58)

    baslangic = time.time()
    veri, hatalar, sunucular, ozet = {}, [], {}, {}
    for sembol in semboller:
        v, h, sn = sembol_cek(sembol)
        veri[sembol] = v
        hatalar.extend(h)
        sunucular[sembol] = sn
        ozet[sembol] = sembol_ozet(v)

    simdi = datetime.now(timezone.utc)
    paket = {
        "paket": "piramit-veri", "surum": 2, "semboller": semboller,
        "sembol": semboller[0],
        "cekim_utc": simdi.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "cekim_ms": int(simdi.timestamp() * 1000),
        "sure_sn": round(time.time() - baslangic, 2),
        "sunucular": sunucular, "veri": veri, "hatalar": hatalar,
        "not": ("Veri Binance genel uçlarından OLDUĞU GİBİ kaydedildi; "
                "kırpma/düzeltme yapılmadı. Çekilemeyen kanal hatalar[] içinde."),
    }

    paket["ozet"] = ozet

    klasor = indirme_klasoru()
    etiket = "_".join(s.replace("USDT", "") for s in semboller)
    dosya = os.path.join(
        klasor, f"piramit_veri_{etiket}_{simdi.strftime('%Y%m%d_%H%M')}.json")
    try:
        with open(dosya, "w", encoding="utf-8") as f:
            json.dump(paket, f, ensure_ascii=False, separators=(",", ":"))
    except OSError as e:
        print(f"\nDOSYA YAZILAMADI: {e}")
        print("Android'de Pydroid'e depolama izni verin: "
              "Ayarlar → Uygulamalar → Pydroid 3 → İzinler → Depolama")
        return 1

    boyut = os.path.getsize(dosya) / 1024.0
    print("-" * 58)
    for sem, o in ozet.items():
        print(f"  [{sem}]")
        for ad, v in o.items():
            print(f"    {ad}: {v}")
    if hatalar:
        print("-" * 58)
        print("  ÇEKİLEMEYEN KANALLAR (uydurulmadı, VERİ YOK olarak gidecek):")
        for h in hatalar:
            print(f"   ✖ {h}")
    print("-" * 58)
    print(f"KAYDEDİLDİ: {dosya}")
    print(f"Boyut: {boyut:.1f} KB | Süre: {paket['sure_sn']} sn")
    print("Bu dosyayı Claude'a yükleyin — gerisi otomatik.")
    print("=" * 58)
    return 0 if not hatalar else 2


if __name__ == "__main__":
    sys.exit(main())
