#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Türev girdi üreteci — "KLİNE KÖRLÜĞÜ" panzehirinin besleyicisi.

Sorun: `turev-akis` motoru var ama girdisi ELLE panelden okunuyordu; panel
gönderilmezse Genişletici merceği VERİ YOK kalıyor ve karar yalnız fiyat
yapısına dayanıyordu (K4 "KLİNE KÖRLÜĞÜ AÇIK" bayrağı).

Bu üreteç türev kanallarını ÖLÇÜLEBİLİR kaynaklardan doldurur:

  1. CVD — ÇEVRİMDIŞI, her zaman çalışır. Binance kline'ının 12 alanı
     içindeki taker-alış hacminden hesaplanır:
         bar_delta = 2 × taker_alis_base − toplam_hacim
     (taker alış > yarı hacim ⇒ alıcı agresif). Kümülatif toplam = CVD.
     Kullanıcının KENDİ verisinden gelir — aynı borsa, aynı bar, tam hizalı.
  2. OI / fiyat serisi — `--seri` dosyasındaki anlık görüntülerden. Görüntüler
     `--oi-snapshot` ile eklenir (ör. Crypto.com MCP `open_interest` alanı).
     Kaynak borsa kline'dan FARKLI olabilir → çıktıda AÇIKÇA etiketlenir.
  3. funding / taker-LSR / likidasyon — `--http` ile Binance vadeli genel
     uçlarından denenir. Ağ politikası engellerse `VERİ YOK` yazılır ve neden
     raporlanır (sessiz başarısızlık yok). Elle panel değeri `--ek` ile verilir.

Eksik kanal UYDURULMAZ: `turev-akis` kapsam düşükse skoru VERİ YOK'a çeker
(fail-closed) ve kurula zayıf/doğrulanmamış danışman olarak girer.

Kullanım:
    python turev_girdi.py --m15 engine/girdi/m15.json \
        --seri engine/state/turev_seri.jsonl --out engine/girdi/turev.json
    python turev_girdi.py --seri ... --oi-snapshot '{"ts":"...","price":64128.9,
        "oi":6159.98,"kaynak":"crypto.com BTCUSD-PERP"}'
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

YOK = "VERİ YOK"
SERI_N = 24          # OI/fiyat serisinde tutulacak azami anlık görüntü
CVD_N = 24           # CVD serisinde tutulacak azami bar


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# 1) CVD — çevrimdışı, kullanıcının kendi kline'ından
# --------------------------------------------------------------------------
def cvd_serisi(m15: Path, n: int = CVD_N) -> dict:
    """12 alanlı Binance kline'dan kümülatif hacim deltası.

    Alan 5 = toplam base hacim, alan 9 = taker ALIŞ base hacmi.
    delta = 2×taker_alis − hacim  (satıcı baskısında negatif)
    """
    try:
        ham = json.loads(m15.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {"cvd_series": None, "durum": f"{YOK} — kline okunamadı ({type(e).__name__})"}
    if not isinstance(ham, list) or not ham:
        return {"cvd_series": None, "durum": f"{YOK} — kline listesi boş"}
    if not isinstance(ham[0], list) or len(ham[0]) < 10:
        return {"cvd_series": None,
                "durum": f"{YOK} — kline 12 alanlı Binance biçiminde değil "
                         f"(taker alış hacmi yok, alan={len(ham[0]) if isinstance(ham[0], list) else '?'})"}
    cvd, seri, kapanis = 0.0, [], []
    for satir in ham:
        hacim, taker = _f(satir[5]), _f(satir[9])
        if hacim is None or taker is None:
            continue
        cvd += 2.0 * taker - hacim
        seri.append(round(cvd, 4))
        kapanis.append(_f(satir[4]))
    if len(seri) < 2:
        return {"cvd_series": None, "durum": f"{YOK} — CVD için en az 2 bar gerekli"}
    return {"cvd_series": seri[-n:], "kline_kapanis": kapanis[-n:],
            "durum": f"hesaplandı ({len(seri)} bar, kaynak: kullanıcının kendi kline'ı, "
                     "taker alış hacmi alan 9)"}


# --------------------------------------------------------------------------
# 2) OI / fiyat serisi — anlık görüntü defteri
# --------------------------------------------------------------------------
def snapshot_ekle(seri: Path, kayit: dict) -> dict:
    """Anlık görüntüyü seriye ekle (aynı ts ikinci kez yazılmaz)."""
    for alan in ("price", "oi"):
        if _f(kayit.get(alan)) is None:
            return {"eklendi": False, "neden": f"{alan} sayısal değil → yazılmadı ({YOK})"}
    mevcut = snapshot_oku(seri)
    if mevcut and str(mevcut[-1].get("ts")) == str(kayit.get("ts")):
        return {"eklendi": False, "neden": "aynı zaman damgası zaten var (tekilleme)"}
    seri.parent.mkdir(parents=True, exist_ok=True)
    with seri.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": kayit.get("ts"), "price": _f(kayit["price"]),
                            "oi": _f(kayit["oi"]),
                            "kaynak": kayit.get("kaynak", YOK)},
                           ensure_ascii=False) + "\n")
    return {"eklendi": True, "toplam": len(mevcut) + 1}


def snapshot_oku(seri: Path) -> list:
    if not seri or not seri.exists():
        return []
    out = []
    for satir in seri.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir:
            continue
        try:
            d = json.loads(satir)
            if _f(d.get("price")) is not None and _f(d.get("oi")) is not None:
                out.append(d)
        except json.JSONDecodeError:
            continue
    return out


# --------------------------------------------------------------------------
# 3) Çevrimiçi kanallar (ağ politikası izin verirse)
# --------------------------------------------------------------------------
BINANCE = "https://fapi.binance.com"


def _get(url: str, zaman: int = 15):
    with urllib.request.urlopen(url, timeout=zaman) as r:   # noqa: S310 — sabit https
        return json.loads(r.read().decode("utf-8"))


def http_kanallar(sembol: str) -> dict:
    """funding + taker-LSR + OI serisi. Engellenirse neden raporlanır."""
    sonuc, hatalar = {}, []
    denemeler = {
        "funding": f"{BINANCE}/fapi/v1/premiumIndex?symbol={sembol}",
        "taker_lsr": f"{BINANCE}/futures/data/takerlongshortRatio?symbol={sembol}&period=15m&limit=1",
        "oi_hist": f"{BINANCE}/futures/data/openInterestHist?symbol={sembol}&period=15m&limit=24",
    }
    for ad, url in denemeler.items():
        try:
            sonuc[ad] = _get(url)
        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as e:
            hatalar.append(f"{ad}: {type(e).__name__} — {str(e)[:120]}")
    return {"veri": sonuc, "hatalar": hatalar}


# --------------------------------------------------------------------------
# 3b) ELLE YAPIŞTIRILAN ham API yanıtları (ağ engelliyken tam çözüm)
# --------------------------------------------------------------------------
HAM_DOSYA = {
    "funding": "premiumIndex.json",              # /fapi/v1/premiumIndex
    "oi_hist": "openInterestHist.json",          # /futures/data/openInterestHist
    "taker_lsr": "takerlongshortRatio.json",     # /futures/data/takerlongshortRatio
}
HAM_LIKIDASYON = "likidasyon.json"               # elle: {"liq_long":..,"liq_short":..}


def ham_oku(dizin: Path, sembol: str) -> dict:
    """Tarayıcıdan kopyalanan ham Binance yanıtlarını oku.

    Ağ politikası engelliyken kanal doldurmanın YOLU budur: kullanıcı adresi
    tarayıcıda açar, JSON'u dosyaya yapıştırır. Biçim API'nin kendisidir —
    dönüştürme yapılmaz, uydurma alan eklenmez. Bozuk/boş dosya sessizce
    geçilmez: hata listesine yazılır.
    """
    veri, hatalar, yas = {}, [], {}
    if not dizin or not dizin.exists():
        return {"veri": veri, "hatalar": hatalar, "yas": yas}
    for ad, dosya in HAM_DOSYA.items():
        p = dizin / dosya
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            hatalar.append(f"{dosya}: okunamadı ({type(e).__name__}) → atlandı")
            continue
        # premiumIndex tüm sembolleri döndürebilir → istenen sembolü seç
        if ad == "funding" and isinstance(d, list):
            d = next((x for x in d if str(x.get("symbol")) == sembol), None)
            if d is None:
                hatalar.append(f"{dosya}: {sembol} bulunamadı → atlandı")
                continue
        if isinstance(d, list) and d:
            sym = str(d[0].get("symbol", sembol))
            if sym != sembol:
                hatalar.append(f"{dosya}: sembol {sym} ≠ {sembol} → atlandı "
                               "(yanlış sembol karara giremez)")
                continue
            ts = d[-1].get("timestamp")
        else:
            ts = (d or {}).get("time")
        veri[ad] = d
        if isinstance(ts, (int, float)):
            yas[ad] = int(ts)
    p = dizin / HAM_LIKIDASYON
    if p.exists():
        try:
            veri["likidasyon"] = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            hatalar.append(f"{HAM_LIKIDASYON}: okunamadı ({type(e).__name__})")
    return {"veri": veri, "hatalar": hatalar, "yas": yas}


def yas_kontrol(yas: dict, m15: Path | None, tolerans_bar: int = 8) -> list:
    """Yapıştırılan veri kline'ın son barından ÇOK eskiyse uyar (gizlenmez)."""
    uyari = []
    if not yas or m15 is None or not m15.exists():
        return uyari
    try:
        ham = json.loads(m15.read_text(encoding="utf-8"))
        son_bar = int(ham[-1][0])
    except (OSError, json.JSONDecodeError, IndexError, ValueError, TypeError):
        return uyari
    for ad, ts in yas.items():
        fark_dk = (son_bar - ts) / 60000.0
        if abs(fark_dk) > tolerans_bar * 15:
            uyari.append(f"[VARSAYIM] {ad}: yapıştırılan veri kline son barından "
                         f"{fark_dk:+.0f} dk uzakta — eşzamanlı değil")
    return uyari


def http_isle(h: dict) -> dict:
    """Ham HTTP yanıtlarını turev-akis alanlarına çevir (eksik = YOK)."""
    v, out = h.get("veri") or {}, {}
    fr = (v.get("funding") or {}).get("lastFundingRate")
    if _f(fr) is not None:
        out["funding"] = round(_f(fr) * 100.0, 6)      # oran → yüzde (motor % bekler)
    lsr = v.get("taker_lsr")
    if isinstance(lsr, list) and lsr:
        r = _f(lsr[-1].get("buySellRatio"))
        if r is not None:
            out["taker_lsr"] = r
    oih = v.get("oi_hist")
    if isinstance(oih, list) and len(oih) >= 2:
        oi = [_f(x.get("sumOpenInterest")) for x in oih]
        px = [_f(x.get("sumOpenInterestValue")) for x in oih]
        if all(o is not None for o in oi):
            out["oi_series"] = oi
            if all(p is not None and o for p, o in zip(px, oi)):
                out["price_series"] = [round(p / o, 4) for p, o in zip(px, oi)]
    return out


# --------------------------------------------------------------------------
# İş üretimi
# --------------------------------------------------------------------------
def uret(m15: Path | None, seri: Path | None, ek: dict, http: dict | None,
         ham: dict | None = None) -> dict:
    job, kaynak, eksik = {}, {}, []

    # ham (elle yapıştırılan) kanallar HTTP ile aynı işleyiciden geçer;
    # çakışırsa ham öncelikli (kullanıcı bilerek yapıştırdı)
    hamp = http_isle(ham) if ham else {}
    if ham and (ham.get("veri") or {}).get("likidasyon"):
        lk = ham["veri"]["likidasyon"]
        for k in ("liq_long", "liq_short"):
            if _f(lk.get(k)) is not None and _f(ek.get(k)) is None:
                ek[k] = _f(lk[k])

    # --- CVD (çevrimdışı) ---
    if m15 is not None:
        c = cvd_serisi(m15)
        if c.get("cvd_series"):
            job["cvd_series"] = c["cvd_series"]
            kaynak["cvd"] = c["durum"]
        else:
            eksik.append(f"cvd: {c['durum']}")
    else:
        eksik.append(f"cvd: m15 verilmedi ({YOK})")

    # --- OI + hizalı fiyat (öncelik: HTTP serisi > anlık görüntü defteri) ---
    hp = {**(http_isle(http) if http else {}), **hamp}   # ham öncelikli
    if hp.get("oi_series") and hp.get("price_series"):
        job["oi_series"], job["price_series"] = hp["oi_series"], hp["price_series"]
        kaynak["oi"] = ("Binance vadeli openInterestHist (15m) — kline ile AYNI borsa"
                        + (" [elle yapıştırıldı]" if hamp.get("oi_series") else ""))
    else:
        snaps = snapshot_oku(seri) if seri else []
        if len(snaps) >= 2:
            son = snaps[-SERI_N:]
            job["oi_series"] = [s["oi"] for s in son]
            job["price_series"] = [s["price"] for s in son]
            kaynaklar = sorted({str(s.get("kaynak", YOK)) for s in son})
            kaynak["oi"] = (f"anlık görüntü defteri ({len(son)} nokta) — kaynak: "
                            f"{', '.join(kaynaklar)}")
            if any("binance" not in k.lower() for k in kaynaklar):
                kaynak["oi_uyari"] = ("[VARSAYIM] OI kaynağı kline'ın borsasından "
                                      "FARKLI olabilir — vekil gösterge, birebir değil")
        else:
            eksik.append(f"oi: en az 2 anlık görüntü gerekli (mevcut {len(snaps)}) → {YOK}")

    # --- funding / lsr (HTTP ya da elle) ---
    for alan, ad in (("funding", "funding"), ("taker_lsr", "taker LSR")):
        if _f(ek.get(alan)) is not None:
            job[alan] = _f(ek[alan]); kaynak[alan] = "elle verildi (--ek)"
        elif _f(hp.get(alan)) is not None:
            job[alan] = hp[alan]
            kaynak[alan] = ("Binance vadeli genel uç"
                            + (" [elle yapıştırıldı]" if hamp.get(alan) is not None
                               else ""))
        else:
            eksik.append(f"{ad}: {YOK}")

    # --- likidasyon (yalnız elle; genel REST ucu yok) ---
    if _f(ek.get("liq_long")) is not None and _f(ek.get("liq_short")) is not None:
        job["liq_long"], job["liq_short"] = _f(ek["liq_long"]), _f(ek["liq_short"])
        kaynak["likidasyon"] = "elle verildi (--ek)"
    else:
        eksik.append(f"likidasyon: {YOK} — genel REST ucu yok, panelden elle girilir")

    job["_kaynaklar"] = kaynak
    job["_eksikler"] = eksik
    job["_not"] = ("Eksik kanal UYDURULMAZ; turev-akis kapsamı düşükse skoru "
                   "VERİ YOK'a çeker (fail-closed).")
    return job


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Türev girdi üreteci (kline körlüğü panzehiri)")
    ap.add_argument("--m15", help="12 alanlı Binance kline dosyası (CVD kaynağı)")
    ap.add_argument("--seri", help="OI anlık görüntü defteri (jsonl)")
    ap.add_argument("--out", help="üretilen turev job'ını buraya yaz")
    ap.add_argument("--ek", help="elle okunan alanlar (JSON: funding/taker_lsr/liq_long/liq_short)")
    ap.add_argument("--oi-snapshot", help="seriye anlık görüntü ekle (JSON) ve çık")
    ap.add_argument("--http", action="store_true", help="çevrimiçi kanalları dene")
    ap.add_argument("--ham", help="tarayıcıdan yapıştırılan ham API yanıtları dizini")
    ap.add_argument("--sembol", default="BTCUSDT")
    a = ap.parse_args(argv)

    if a.oi_snapshot:
        if not a.seri:
            print(json.dumps({"hata": "--oi-snapshot için --seri gerekli"}, ensure_ascii=False))
            return 1
        try:
            kayit = json.loads(a.oi_snapshot)
        except json.JSONDecodeError as e:
            print(json.dumps({"hata": f"snapshot JSON değil: {e}"}, ensure_ascii=False))
            return 1
        print(json.dumps(snapshot_ekle(Path(a.seri), kayit), ensure_ascii=False, indent=2))
        return 0

    ek = {}
    if a.ek:
        p = Path(a.ek)
        try:
            ek = json.loads(p.read_text(encoding="utf-8")) if p.exists() else json.loads(a.ek)
        except (OSError, json.JSONDecodeError):
            ek = {}
    http = http_kanallar(a.sembol) if a.http else None
    ham = ham_oku(Path(a.ham), a.sembol) if a.ham else None
    job = uret(Path(a.m15) if a.m15 else None,
               Path(a.seri) if a.seri else None, ek, http, ham)
    if ham:
        uy = yas_kontrol(ham.get("yas", {}), Path(a.m15) if a.m15 else None)
        if ham["hatalar"]:
            job["_ham_hatalari"] = ham["hatalar"]
        if uy:
            job.setdefault("_uyarilar", []).extend(uy)
    # Ağ hataları DOSYAYA yazılmaz: turev.json yalnız VERİDEN türemeli.
    # Aksi halde "ağ denendi mi" bilgisi dosyanın parmak izini oynatır →
    # veri değişmediği halde boru hattı yeniden koşar (gereksiz + depo kirliliği).
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(job, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    if http and http["hatalar"]:
        job["_ag_hatalari"] = http["hatalar"]        # yalnız stdout/kanca için
    print(json.dumps(job, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
