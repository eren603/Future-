#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HEADROOM SINAVI — sıkıştırma katmanı sözleşmeyi bozuyor mu?

    python3 .claude/eklenti/headroom_sinav.py

NEDEN VAR: Headroom, dosya ile model arasına giren bir sıkıştırma katmanıdır.
Bu deponun sözleşmesi (CLAUDE.md) "kullanıcıya sunulan her sayı koşu raporunda
BİREBİR var mı" diye sorar (`iddia_denetle.py`). Sıkıştırma tam bu zincirin
ortasına oturduğu için "aynı cevaplar" iddiası KABUL EDİLMEZ, SINANIR.

İKİ AYRI DENETİM — biri diğerinin kör noktasını kapatır:

  1) SAYI BÜTÜNLÜĞÜ — rapordaki sayılar sıkıştırmadan sonra duruyor mu?
     Çıkarım deponun KENDİ aracıyla yapılır (iddia_denetle.rapor_sayilari).
     ADİL KIYAS ŞART: Headroom JSON'u minify eder; asıl rapor GİRİNTİLİDİR.
     `iddia_denetle.SAYI` regex'i aralık koruması için `(?<![\\d.,])` bakışına
     sahip → girintili metinde boşlukla gelen sayıyı görür, minify metinde
     virgülle gelen aynı sayıyı ATLAR. İki taraf aynı biçime getirilmezse
     araç YANLIŞ ALARM verir (bu sınavın ilk sürümü tam buna düştü).

  2) YAPI BÜTÜNLÜĞÜ — asıl kör nokta. `iddia_denetle` yalnız SAYI denetler,
     kendi belgesinde yazdığı gibi ANLAM denetlemez. Sıkıştırma sayıyı hiç
     bozmadan KOMPLE BÖLÜM silebilir. Bu yüzden sıkıştırılmış çıktıdan rapor
     JSON'u geri ayrıştırılır ve asıl raporla NESNE olarak karşılaştırılır.

⚠️ Bu sınav Headroom'un genel kalitesi hakkında hüküm vermez; yalnız BU
   deponun sözleşmesiyle uyumunu ölçer.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / ".claude/skills/piramit-sistem/scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    from iddia_denetle import rapor_sayilari
except ImportError as e:  # pragma: no cover
    print(f"HATA: iddia_denetle içe aktarılamadı ({e}) — {SCRIPTS} yerinde mi?")
    sys.exit(1)

try:
    import headroom
except ImportError:
    print('ATLANDI: headroom kurulu değil. Kurmak için:\n'
          '  pip install --ignore-installed pyjwt "headroom-ai[all]"')
    sys.exit(77)

RAPOR = REPO / ".claude/skills/piramit-sistem/state/son_rapor.json"
# Sözleşmenin ZİRVE katmanında beklediği alanlar. Biri düşerse karar yazılırken
# KIYAS/ÇELİŞKİ TURU/HESAP VERME görünmez olur → gözlemci EKSİK_AKTARIM ihlali.
ZIRVE_ZORUNLU = ("iki_satir", "KIYAS", "CELISKI_TURU", "ONCEKI_AKIBET",
                 "ILK_GECIS", "EMIR_GEREKCE", "kapi_gerekceleri")
DOLGU = ("Ara adım: yapı kontrolü yapıldı, swing teyidi arandı, sonuç yok. "
         "Devam ediliyor, ek bulgu yok, bir sonraki adıma geçiliyor.")


def metin_topla(mesajlar) -> str:
    p = []
    for m in mesajlar:
        c = m.get("content")
        if isinstance(c, str):
            p.append(c)
        elif isinstance(c, list):
            for blok in c:
                if isinstance(blok, str):
                    p.append(blok)
                elif isinstance(blok, dict):
                    for a in ("text", "content"):
                        v = blok.get(a)
                        if isinstance(v, str):
                            p.append(v)
                        elif isinstance(v, list):
                            p += [b["text"] for b in v
                                  if isinstance(b, dict) and isinstance(b.get("text"), str)]
    return "\n".join(p)


def kur_mesajlar(rapor_metni: str, dolgu: int):
    msgs = [
        {"role": "user", "content": "BTCUSDT piramit koşusunu çalıştır."},
        {"role": "assistant", "content": [
            {"type": "text", "text": "Boru hattını koşuyorum."},
            {"type": "tool_use", "id": "t1", "name": "Bash",
             "input": {"command": "python3 scripts/piramit.py"}}]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": rapor_metni}]},
    ]
    for i in range(dolgu):     # dolgu SAYISIZDIR — yoksa "uydurma" sütunu kirlenir
        msgs.append({"role": "assistant", "content": [
            {"type": "text", "text": DOLGU},
            {"type": "tool_use", "id": f"f{i}", "name": "Bash",
             "input": {"command": "grep -c swing engine/girdi/m15.json"}}]})
        msgs.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": f"f{i}", "content": DOLGU}]})
    msgs.append({"role": "user", "content": "Şimdi kararı yaz."})
    return msgs


def json_geri_oku(metin: str):
    """Sıkıştırılmış metinden rapor JSON'unu geri ayrıştır."""
    i = metin.find('"sistem"')
    if i < 0:
        return None
    i = metin.rfind("{", 0, i)
    d = 0
    for j, ch in enumerate(metin[i:], start=i):
        if ch == "{":
            d += 1
        elif ch == "}":
            d -= 1
            if d == 0:
                try:
                    return json.loads(metin[i:j + 1])
                except json.JSONDecodeError:
                    return None
    return None


def nesne_farki(a, b, yol="", out=None):
    out = [] if out is None else out
    if type(a) is not type(b):
        out.append(f"TİP {yol}: {type(a).__name__} → {type(b).__name__}")
    elif isinstance(a, dict):
        for k in a:
            if k not in b:
                out.append(f"SİLİNDİ {yol}.{k}")
            else:
                nesne_farki(a[k], b[k], f"{yol}.{k}", out)
        for k in b:
            if k not in a:
                out.append(f"EKLENDİ {yol}.{k}")
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"UZUNLUK {yol}: {len(a)} → {len(b)}")
        else:
            for n, (x, y) in enumerate(zip(a, b)):
                nesne_farki(x, y, f"{yol}[{n}]", out)
    elif a != b:
        out.append(f"DEĞER {yol}: {a!r} → {b!r}")
    return out


def kosu(ad: str, dolgu: int, **kw) -> dict:
    ham = RAPOR.read_text(encoding="utf-8")
    asil = json.loads(ham)
    # ADİL KIYAS: asıl raporu da Headroom'un yaptığı gibi minify ederek çıkar
    mini = json.dumps(asil, ensure_ascii=False, separators=(",", ":"))

    s = headroom.compress(kur_mesajlar(ham, dolgu), **kw)
    sik = metin_topla(s.messages)

    a_sayi, k_sayi = rapor_sayilari(mini), rapor_sayilari(sik)
    geri = json_geri_oku(sik)
    fark = ["JSON GERİ AYRIŞTIRILAMADI"] if geri is None else nesne_farki(asil, geri)
    dusen = [k for k in ZIRVE_ZORUNLU
             if geri is not None and k not in (geri.get("ZIRVE") or {})]

    return {
        "senaryo": ad,
        "token": f"{s.tokens_before} → {s.tokens_after} "
                 f"(%{round(100 * (1 - s.tokens_after / s.tokens_before), 1)} tasarruf)",
        "donusumler": list(s.transforms_applied or []),
        "SAYI_kayip": sorted(a_sayi - k_sayi),
        "SAYI_uydurma": sorted(k_sayi - a_sayi),
        "YAPI_fark_sayisi": len(fark),
        "YAPI_fark": fark[:20],
        "ZIRVE_dusen_alan": dusen,
    }


def main() -> int:
    if not RAPOR.exists():
        print(f"ATLANDI: koşu raporu yok — {RAPOR}")
        return 77
    print(f"headroom {headroom.__version__} · rapor {RAPOR.name} "
          f"({RAPOR.stat().st_size} B)\n")

    sonuclar = [
        kosu("A_varsayilan", dolgu=0),
        kosu("B_uzun_oturum", dolgu=12),
        kosu("C_agresif", dolgu=12, compress_user_messages=True,
             target_ratio=0.5, protect_recent=0),
    ]
    print(json.dumps(sonuclar, ensure_ascii=False, indent=2))

    sayi_kotu = [s for s in sonuclar if s["SAYI_kayip"] or s["SAYI_uydurma"]]
    yapi_kotu = [s for s in sonuclar if s["ZIRVE_dusen_alan"] or s["YAPI_fark_sayisi"]]

    print("\n" + "=" * 64)
    print(f"1) SAYI BÜTÜNLÜĞÜ : {'BOZULDU' if sayi_kotu else 'GEÇTİ — kayıp 0, uydurma 0'}")
    print(f"2) YAPI BÜTÜNLÜĞÜ : {'BOZULDU' if yapi_kotu else 'GEÇTİ — nesne birebir'}")
    for s in yapi_kotu:
        print(f"   {s['senaryo']}: ZİRVE'den düşen → {', '.join(s['ZIRVE_dusen_alan']) or '—'}")
    if yapi_kotu:
        print("\nHÜKÜM: Headroom sayıları bozmuyor ama ZİRVE bölümlerini siliyor.")
        print("Karar yazılırken KIYAS / ÇELİŞKİ TURU / HESAP VERME / İLK-GEÇİŞ")
        print("görünmez olur → gözlemci EKSİK_AKTARIM. Karar yolunda KULLANILMAZ.")
    return 2 if (sayi_kotu or yapi_kotu) else 0


if __name__ == "__main__":
    sys.exit(main())
