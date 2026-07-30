#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Akıbet etiketleyici — SI döngüsünün yakıtı, ELLE yazımdan kurtarır.

Sorun: `defter.jsonl`'daki `gercek_r` alanı bugüne dek ELLE dolduruluyordu.
Elle etiketleme durursa K5 (SI) katmanı öğrenemez — ağırlıklar sonsuza dek
1.0 kalır. Bu motor akıbeti FİYAT YOLUNDAN mekanik hesaplar.

Ne yapar: deftere yazılmış her kararı (giriş/stop/T1/iptal) sonraki 15M
barlarda ileriye doğru simüle eder, gerçekleşen R'yi hesaplar ve satıra
`gercek_r` + `gercek_sonuc` yazar.

Kurallar (muhafazakâr, ileriye bakış YOK — hepsi çıktıda raporlanır):
  - MARKET karar (giris_alt == giris_ust): karar barının kapanışında dolar.
  - LIMIT bölge: bölgeye İLK dokunuşta dolar; dolum fiyatı bölgenin
    ALEYHTE kenarıdır (short → alt kenar, long → üst kenar).
  - Dolumdan ÖNCE gövde kapanışı iptal seviyesinin ötesine geçerse: İPTAL
    (pozisyon açılmadı) → R YAZILMAZ; istatistiğe girmez.
  - Aynı barda hem dolum hem iptal: BELİRSİZ → R YAZILMAZ (fail-closed).
  - Aynı barda hem stop hem hedef: STOP sayılır (muhafazakâr).
  - Çıkış sırası: STOP → HEDEF(T1) → iptal gövde kapanışı.
  - `azami_tutma` bar içinde çıkış yoksa: AÇIK → R YAZILMAZ (sonraki koşuda
    veri uzayınca yeniden denenir).
  - Maliyet (komisyon/kayma) DÜŞÜLMEZ: ham R. Motorun ilan ettiği R ile aynı
    ölçekte kalsın diye — bu bir VARSAYIMDIR ve çıktıda yazılır.

ELLE yazılmış `gercek_r` ASLA ezilmez: insan düzeltmesi otoritedir.

Bar arşivi: 15M pencere kayan olduğundan eski kararlar veri penceresinden
düşer. `--arsiv` ile birleşik bar havuzu tutulur (zaman damgasına göre tekil,
sıralı) → karar penceresi kaysa bile akıbet ölçülebilir.

Kullanım:
    python akibet_etiketle.py --defter engine/state/defter.jsonl \
        --m15 engine/girdi/m15.json --arsiv engine/state/bar_arsivi.jsonl [--yaz]

`--yaz` verilmezse KURU KOŞU: ne yazacağını raporlar, dosyaya dokunmaz.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
REPO = _HERE.parents[3]
sys.path.insert(0, str(REPO / "engine"))
import karar_motoru as km  # noqa: E402

YOK = "VERİ YOK"

KONVANSIYON = {
    "azami_bekleme": 24,   # LIMIT bölge dolumu için azami bar (6 saat)
    "azami_tutma": 96,     # dolumdan sonra çıkış için azami bar (24 saat)
    "maliyet_dusuldu": False,
}


class EtiketError(Exception):
    pass


# --------------------------------------------------------------------------
# Bar havuzu
# --------------------------------------------------------------------------
def bar_yukle(yollar: list) -> list:
    """Verilen kaynaklardan barları birleştir: zaman damgasına göre tekil+sıralı."""
    havuz = {}
    atlanan = 0                       # bozuk/eksik satır sayacı (B3: sessiz kayıp yok)
    for y in yollar:
        p = Path(y)
        if not p.exists():
            continue
        if p.suffix == ".jsonl":
            for satir in p.read_text(encoding="utf-8").splitlines():
                satir = satir.strip()
                if not satir:
                    continue
                try:
                    d = json.loads(satir)
                    havuz[int(d["t"])] = (float(d["o"]), float(d["h"]),
                                          float(d["l"]), float(d["c"]),
                                          float(d.get("v", 0.0)))
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    atlanan += 1      # arşiv kısmi bozulursa havuz sessizce küçülmesin
                    continue
        else:
            for b in km.parse_klines(str(p)):
                havuz[int(b.t)] = (b.o, b.h, b.l, b.c, b.v)
    if atlanan:
        sys.stderr.write(f"[akibet_etiketle] bar_yukle: {atlanan} bozuk/eksik "
                         "satır atlandı (arşiv kısmi bozuk olabilir).\n")
    return [(t, *havuz[t]) for t in sorted(havuz)]


def arsiv_guncelle(arsiv: Path, barlar: list) -> dict:
    """Yeni barları arşive ekle (tekil). Var olan satır yeniden yazılmaz."""
    mevcut = set()
    if arsiv.exists():
        for satir in arsiv.read_text(encoding="utf-8").splitlines():
            satir = satir.strip()
            if not satir:
                continue
            try:
                mevcut.add(int(json.loads(satir)["t"]))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
    yeni = [b for b in barlar if b[0] not in mevcut]
    if yeni:
        arsiv.parent.mkdir(parents=True, exist_ok=True)
        with arsiv.open("a", encoding="utf-8") as f:
            for t, o, h, l, c, v in yeni:
                f.write(json.dumps({"t": t, "o": o, "h": h, "l": l,
                                    "c": c, "v": v}) + "\n")
    return {"arsiv": str(arsiv), "eklenen_bar": len(yeni),
            "toplam_bar": len(mevcut) + len(yeni)}


# --------------------------------------------------------------------------
# Simülasyon
# --------------------------------------------------------------------------
def _yon_isaret(karar: dict) -> int:
    y = str(karar.get("yon") or karar.get("karar", "")).upper()
    if y == "LONG":
        return 1
    if y == "SHORT":
        return -1
    raise EtiketError(f"yön okunamadı: {y!r}")


def simule_et(karar: dict, karar_zamani: int, barlar: list, p: dict) -> dict:
    """Kararı ileriye doğru simüle et → gerçekleşen R (ya da neden ölçülemediği)."""
    idx = {t: i for i, (t, *_) in enumerate(barlar)}
    i0 = idx.get(int(karar_zamani))
    if i0 is None:
        return {"olculebilir": False, "sonuc": f"{YOK} — karar barı veri havuzunda yok "
                                               "(pencere kaydı; arşiv büyüdükçe ölçülebilir)"}
    s = _yon_isaret(karar)
    giris_alt = float(karar["giris_alt"]); giris_ust = float(karar["giris_ust"])
    stop = float(karar["stop"]); t1 = float(karar["t1"])
    iptal = float(karar.get("iptal", giris_ust if s < 0 else giris_alt))
    # MARKET DOLUM AÇIKÇA BEYAN EDİLMELİDİR (fail-closed).
    # Eski kural `market = (giris_alt == giris_ust)` idi ve TEK FİYATLI LİMİT
    # girişi market sanıyordu: fiyat o seviyeye HİÇ GİTMESE bile pozisyon
    # dolmuş sayılıp R yazılıyordu. 2026-07-25'te yakalandı — sistem hiç
    # tetiklenmemiş bir SHORT'a kendini "+1.9073 R, T1" diye ödüllendirdi
    # (karar sonrası en yüksek 64236.8 iken giriş 64611.55'ti). Kanıtsız
    # dolum = kendini memnun etme; artık dolum ancak fiyat DOKUNURSA sayılır.
    market = bool(karar.get("market")
                  or str(karar.get("giris_tipi", "")).strip().lower() == "market")

    def iptal_asildi(c):     # gövde kapanışı iptalin ötesinde mi?
        return c > iptal if s < 0 else c < iptal

    # --- 1) dolum ---------------------------------------------------------
    if market:
        f = i0
        giris = float(karar["giris"])
    else:
        f, giris = None, None
        son = min(len(barlar) - 1, i0 + int(p["azami_bekleme"]))
        for j in range(i0 + 1, son + 1):
            _, o, h, l, c, _v = barlar[j]
            dokundu = (h >= giris_alt) if s < 0 else (l <= giris_ust)
            iptal_oldu = iptal_asildi(c)
            if dokundu and iptal_oldu:
                return {"olculebilir": False,
                        "sonuc": "BELİRSİZ (aynı barda dolum ve iptal) — R yazılmaz"}
            if iptal_oldu:
                return {"olculebilir": False,
                        "sonuc": "İPTAL (tetiklenmedi) — pozisyon açılmadı, R yazılmaz"}
            if dokundu:
                f = j
                giris = giris_alt if s < 0 else giris_ust   # aleyhte kenar
                break
        if f is None:
            if son < i0 + int(p["azami_bekleme"]):
                return {"olculebilir": False,
                        "sonuc": f"{YOK} — bekleme penceresi henüz dolmadı (veri kısa)"}
            return {"olculebilir": False,
                    "sonuc": "İPTAL (bölgeye dokunulmadı) — R yazılmaz"}

    risk = abs(giris - stop)
    if risk <= 0:
        return {"olculebilir": False, "sonuc": f"{YOK} — giriş=stop, R tanımsız"}

    # --- 2) çıkış ---------------------------------------------------------
    son = min(len(barlar) - 1, f + int(p["azami_tutma"]))
    for k in range(f, son + 1):
        if k == i0 and market:
            continue                      # karar barında market dolum: aynı barı sayma
        _, o, h, l, c, _v = barlar[k]
        stop_vuruldu = (h >= stop) if s < 0 else (l <= stop)
        hedef_vuruldu = (l <= t1) if s < 0 else (h >= t1)
        # LIMIT dolum barında (k==f, market değil) HEDEF yalnız dolum AÇILIŞTA
        # gerçekleştiyse kredilenir (B1): bar giriş fiyatında/ötesinde açıldıysa
        # dolum ilk tiktedir → sonraki tüm hareket (hedef dahil) KANITLI sonradır.
        # Fitille-dolumda (açılış giriş dışı, wick ile dokunur) bar-içi sıra
        # kanıtsız — fiyat önce hedefe gidip sonra girişe dönmüş olabilir → hedef
        # ertelenir. Stop yine değerlendirilir (aleyhte kenar, muhafazakâr).
        if k == f and not market:
            dolum_acilista = (o >= giris) if s < 0 else (o <= giris)
            if not dolum_acilista:
                hedef_vuruldu = False
        if stop_vuruldu:                  # aynı barda ikisi de → STOP (muhafazakâr)
            cikis, kod = stop, "STOP"
        elif hedef_vuruldu:
            cikis, kod = t1, "T1"
        elif iptal_asildi(c):
            cikis, kod = c, "INVALIDATION-EXIT"
        else:
            continue
        r = s * (cikis - giris) / risk
        return {"olculebilir": True, "sonuc": kod, "r": round(r, 4),
                "giris_fiyat": round(giris, 4), "cikis_fiyat": round(cikis, 4),
                "cikis_bar": barlar[k][0], "bar_sayisi": k - f,
                "dolum": "market" if market else "limit"}

    if son < f + int(p["azami_tutma"]):
        return {"olculebilir": False,
                "sonuc": f"AÇIK — çıkış henüz olmadı (veri kısa); sonraki koşuda ölçülür"}
    return {"olculebilir": False,
            "sonuc": f"AÇIK — {p['azami_tutma']} barda çıkış olmadı, R yazılmaz"}


# --------------------------------------------------------------------------
# Defter işleme
# --------------------------------------------------------------------------
def etiketle(defter: Path, barlar: list, p: dict, yaz: bool) -> dict:
    if not defter.exists():
        return {"defter": str(defter), "durum": f"{YOK} — defter dosyası yok",
                "etiketlenen": 0, "elle_korunan": 0, "olculemeyen": 0,
                "yazildi": False, "kayitlar": []}
    satirlar, rapor = [], []
    etiketlenen = elle_korunan = olculemeyen = 0
    for ham in defter.read_text(encoding="utf-8").splitlines():
        ham = ham.strip()
        if not ham:
            continue
        try:
            d = json.loads(ham)
        except json.JSONDecodeError:
            satirlar.append(ham)
            continue
        mevcut = d.get("gercek_r")
        if isinstance(mevcut, (int, float)) and not isinstance(mevcut, bool):
            elle_korunan += 1                      # insan düzeltmesi otoritedir
            satirlar.append(json.dumps(d, ensure_ascii=False))
            continue
        try:
            s = simule_et(d.get("karar") or {}, d.get("karar_zamani"), barlar, p)
        except (EtiketError, KeyError, TypeError, ValueError) as e:
            s = {"olculebilir": False, "sonuc": f"{YOK} — {type(e).__name__}: {e}"}
        if s["olculebilir"]:
            d["gercek_r"] = s["r"]
            d["gercek_sonuc"] = s["sonuc"]
            d["etiketleyici"] = "otomatik (akibet_etiketle.py v1)"
            d["etiket_ayrinti"] = {k: v for k, v in s.items()
                                   if k not in ("olculebilir", "sonuc", "r")}
            etiketlenen += 1
        else:
            d["etiket_denemesi"] = s["sonuc"]
            olculemeyen += 1
        rapor.append({"karar_zamani": d.get("karar_zamani"),
                      "yon": (d.get("karar") or {}).get("karar"),
                      "sonuc": s["sonuc"], "r": s.get("r")})
        satirlar.append(json.dumps(d, ensure_ascii=False))

    if yaz and satirlar:
        fd, gecici = tempfile.mkstemp(dir=str(defter.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(satirlar) + "\n")
        os.replace(gecici, defter)     # atomik: yarım yazılmış defter olmaz

    return {"defter": str(defter), "etiketlenen": etiketlenen,
            "elle_korunan": elle_korunan, "olculemeyen": olculemeyen,
            "yazildi": bool(yaz), "kayitlar": rapor,
            "varsayimlar": [
                f"LIMIT dolum penceresi={p['azami_bekleme']} bar, "
                f"tutma penceresi={p['azami_tutma']} bar (konvansiyon)",
                "dolum fiyatı bölgenin ALEYHTE kenarı (muhafazakâr)",
                "aynı barda stop+hedef → STOP (muhafazakâr)",
                f"maliyet (komisyon/kayma) düşülmedi: ham R "
                f"(maliyet_dusuldu={p['maliyet_dusuldu']})",
                "elle yazılmış gercek_r ezilmez (insan düzeltmesi otoritedir)",
            ]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Akıbet etiketleyici (SI döngüsü yakıtı)")
    ap.add_argument("--defter", required=True)
    ap.add_argument("--m15", help="güncel 15M kline dosyası")
    ap.add_argument("--arsiv", help="bar arşivi (jsonl) — kayan pencere panzehiri")
    ap.add_argument("--yaz", action="store_true", help="defteri güncelle (yoksa kuru koşu)")
    ap.add_argument("--azami-bekleme", type=int, default=KONVANSIYON["azami_bekleme"])
    ap.add_argument("--azami-tutma", type=int, default=KONVANSIYON["azami_tutma"])
    a = ap.parse_args(argv)

    p = {**KONVANSIYON, "azami_bekleme": a.azami_bekleme, "azami_tutma": a.azami_tutma}
    kaynaklar = [x for x in (a.m15, a.arsiv) if x]
    if not kaynaklar:
        print(json.dumps({"hata": f"{YOK} — --m15 ya da --arsiv gerekli"},
                         ensure_ascii=False))
        return 1

    arsiv_bilgi = None
    if a.arsiv and a.m15:
        arsiv_bilgi = arsiv_guncelle(Path(a.arsiv), bar_yukle([a.m15]))
    barlar = bar_yukle(kaynaklar)
    sonuc = etiketle(Path(a.defter), barlar, p, a.yaz)
    sonuc["bar_havuzu"] = {"bar": len(barlar),
                           "ilk": barlar[0][0] if barlar else YOK,
                           "son": barlar[-1][0] if barlar else YOK}
    if arsiv_bilgi:
        sonuc["arsiv"] = arsiv_bilgi
    print(json.dumps(sonuc, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
