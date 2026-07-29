#!/usr/bin/env python3
"""izleme-telemetri — ölçüm JSONL'inden Markdown rapor üretici.

Rapor bölüm başlıkları kaynak `sample-report-output.md`'nin yapısına
SADIKTIR (eşleme KANIT.md'de satır satır verilir):

    Claude Code Productivity Report → Piramit Boru Hattı İzleme Raporu
    Executive Summary              → Yönetici Özeti
    Usage Metrics / Key Metrics    → Kullanım Metrikleri / Anahtar Metrikler
    Linear Integration Metrics     → Katman ve Kapı Dökümü
      Issue Completion             →   Kapı Durumu
      Active Development Tickets   →   Doğrulanmayan Danışmanlar
      Team Velocity                →   Katman Süre Eğilimi
      Productivity Comparison      →   Boru Hattı Sağlığı Kıyası (ilk/son yarı)
    Cost Analysis                  → Süre Analizi (maliyet = süre; USD yok)
    Actionable Insights            → Uygulanabilir İçgörüler
    Recommendations                → Öneriler
    Session Duration Distribution  → Koşu Süresi Dağılımı

Doğruluk sözleşmesi: rapordaki HER sayı JSONL'den okunur. Veri yoksa "VERİ YOK"
yazılır — yorum/varsayım açıkça etiketlenir, uydurma sayı üretilmez.

Kullanım:
    python rapor.py --dosya state/olcum.jsonl --out ornek/rapor.md
    python rapor.py --self-test
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import olcum as OL  # noqa: E402

YOK = OL.YOK
SKILL_DIR = OL.SKILL_DIR
ORNEK_DIZIN = OL.ORNEK_DIZIN

# İçgörü kuralları — SABİT DEĞİL, ETİKETLİ konvansiyon (CLAUDE.md eşik
# politikası: kalibre edilemeyen her eşik `varsayimlar` ile açıkça yazılır).
ESIK = {
    "katman_pay": 0.50,        # bir katman toplam sürenin bu payını aşarsa darboğaz
    "kapi_durdurma_orani": 0.25,   # koşuların bu payında durduysa kronik kapı
    "dogrulama_orani": 0.50,   # danışman doğrulama oranı bunun altıysa zayıf
    "kapsam_tam": 1.0,         # türev kapsamı hedefi (turev_akis.py: 1.0 = tüm alanlar)
    "kapsam_esigi": 0.5,       # turev-akis fail-closed eşiği (motorun kendi kapısı)
}


# --------------------------------------------------------------------------
def _yuzdelik(dizi, p):
    """En yakın sıra (nearest-rank) yüzdelik — numpy'sız, tekrarlanabilir."""
    if not dizi:
        return None
    s = sorted(dizi)
    k = max(1, int(round(p / 100.0 * len(s))))
    return s[min(k, len(s)) - 1]


def _ms(v):
    return YOK if v is None else f"{v:,.0f} ms".replace(",", " ")


def _oran(a, b):
    return None if not b else a / b


def _yuzde(x, hane=0):
    return YOK if x is None else f"%{x * 100:.{hane}f}"


# --------------------------------------------------------------------------
def topla(olaylar: list) -> dict:
    """JSONL olaylarını rapor için toplulaştır. Her alan izlenebilir."""
    ok = [o for o in olaylar if "_bozuk" not in o and o.get("descriptor")]
    bozuk = [o["_bozuk"] for o in olaylar if "_bozuk" in o]
    ok.sort(key=lambda o: o.get("ts_ms") or 0)

    A = {
        "olay_sayisi": len(ok), "bozuk_satir": bozuk,
        "ilk_ts": ok[0]["ts_utc"] if ok else YOK,
        "son_ts": ok[-1]["ts_utc"] if ok else YOK,
        "kosu_sure": [], "katman_sure": defaultdict(list),
        "motor_sure": defaultdict(list),
        "kosu_sayisi": 0, "semboller": Counter(),
        "kapi_gecti": Counter(), "kapi_durdu": Counter(), "durdu_kapi_metni": {},
        "dogrulandi": Counter(), "dogrulanmadi": Counter(),
        "ihlal": Counter(), "ihlal_katman": Counter(), "kritik_ihlal": 0,
        "uyari": Counter(), "muhur": 0,
        "zorunlu_eksik": Counter(), "motor_hata": Counter(),
        "turev_kapsam": [], "emir_var": 0, "emir_yok": 0,
        "det_ilk": 0, "det_ayni": 0, "det_kirik": 0, "det_kirik_kayit": [],
        "kosular": {},                    # kosu_id -> koşu özeti
    }

    def _kosu(a):
        kid = a.get("kosu_id") or YOK
        k = A["kosular"].setdefault(kid, {
            "kosu_id": kid, "sembol": a.get("sembol", YOK), "toplam_sure": 0.0,
            "kosu_sure": None, "ihlal": 0, "uyari": 0, "muhur": False,
            "durdu": None, "kapsam": None, "emir": None, "ts": None})
        if a.get("sembol"):
            k["sembol"] = a["sembol"]
        return k

    for o in ok:
        ad = o["descriptor"]["name"]
        a = o.get("attributes") or {}
        v = o.get("value")
        k = _kosu(a)
        k["ts"] = k["ts"] or o.get("ts_utc")
        if ad == "piramit.katman.sure_ms":
            A["katman_sure"][a.get("katman", YOK)].append(v)
            k["toplam_sure"] += v
        elif ad == "piramit.motor.sure_ms":
            A["motor_sure"][a.get("motor", YOK)].append(v)
        elif ad == "piramit.kosu.sure_ms":
            A["kosu_sure"].append(v)
            k["kosu_sure"] = v
        elif ad == "piramit.kosu.sayisi":
            A["kosu_sayisi"] += int(v)
            A["semboller"][a.get("sembol", YOK)] += int(v)
        elif ad == "piramit.kapi.gecti":
            A["kapi_gecti"][a.get("katman", YOK)] += int(v)
        elif ad == "piramit.kapi.durdu":
            if int(v) > 0:                       # 0 = "koşmadı" bilgi kaydı
                A["kapi_durdu"][a.get("katman", YOK)] += int(v)
                A["durdu_kapi_metni"][a.get("katman", YOK)] = a.get("kapi", YOK)
                k["durdu"] = a.get("katman", YOK)
        elif ad == "piramit.danisman.dogrulandi":
            A["dogrulandi"][a.get("danisman", YOK)] += int(v)
        elif ad == "piramit.danisman.dogrulanmadi":
            A["dogrulanmadi"][a.get("danisman", YOK)] += int(v)
        elif ad == "piramit.gozlemci.ihlal":
            A["ihlal"][a.get("kod", YOK)] += int(v)
            A["ihlal_katman"][a.get("katman", YOK)] += int(v)
            A["kritik_ihlal"] += int(v) if a.get("kritik") else 0
            k["ihlal"] += int(v)
        elif ad == "piramit.gozlemci.uyari":
            A["uyari"][a.get("kod", YOK)] += int(v)
            k["uyari"] += int(v)
        elif ad == "piramit.muhur":
            A["muhur"] += int(v)
            k["muhur"] = True
        elif ad == "piramit.zorunlu_girdi.eksik":
            A["zorunlu_eksik"][a.get("girdi", YOK)] += int(v)
        elif ad == "piramit.motor.hata":
            A["motor_hata"][a.get("motor", YOK)] += int(v)
        elif ad == "piramit.turev.kapsam":
            A["turev_kapsam"].append(v)
            k["kapsam"] = v
        elif ad == "piramit.emir.uretildi":
            if int(v) > 0:
                A["emir_var"] += 1
            else:
                A["emir_yok"] += 1
            k["emir"] = a.get("emir", YOK)
        elif ad == "piramit.determinizm":
            if a.get("ilk_gozlem"):
                A["det_ilk"] += 1
            elif v == 1.0:
                A["det_ayni"] += 1
            else:
                A["det_kirik"] += 1
                A["det_kirik_kayit"].append(
                    {"kosu_id": a.get("kosu_id"), "veri_imzasi": a.get("veri_imzasi"),
                     "onceki": a.get("onceki_sonuc_imzasi"),
                     "yeni": a.get("sonuc_imzasi")})
    A["katman_sure"] = dict(A["katman_sure"])
    A["motor_sure"] = dict(A["motor_sure"])
    return A


# --------------------------------------------------------------------------
def _mermaid_pie(baslik, ciftler):
    if not ciftler:
        return f"*{baslik}: {YOK}*"
    L = ["```mermaid", "pie", f"    title {baslik}"]
    for ad, v in ciftler:
        L.append(f'    "{ad}" : {round(v, 1)}')
    L.append("```")
    return "\n".join(L)


def _tablo(basliklar, satirlar):
    if not satirlar:
        return f"*{YOK}*"
    L = ["| " + " | ".join(basliklar) + " |",
         "|" + "|".join(["---"] * len(basliklar)) + "|"]
    for s in satirlar:
        # Hücredeki `|` tabloyu kırar (emir metni "@giriş | stop | T1" içerir)
        L.append("| " + " | ".join(str(x).replace("|", "\\|") for x in s) + " |")
    return "\n".join(L)


def _icgoruler(A: dict) -> list:
    """Sayıdan TÜRETİLEN içgörüler. Her madde bir ölçüme bağlıdır; kural yoksa
    madde de yoktur (anlatı için içgörü uydurulmaz)."""
    G = []
    toplam_katman = sum(sum(v) for v in A["katman_sure"].values())
    if toplam_katman > 0:
        ad, sur = max(((k, sum(v)) for k, v in A["katman_sure"].items()),
                      key=lambda kv: kv[1])
        pay = sur / toplam_katman
        if pay >= ESIK["katman_pay"]:
            G.append(f"**Darboğaz katman `{ad}`**: katman süresinin "
                     f"{_yuzde(pay, 1)}'i burada geçiyor ({_ms(sur)} / "
                     f"{_ms(toplam_katman)}). Optimizasyon önce burada anlamlı "
                     f"(kural: pay ≥ {_yuzde(ESIK['katman_pay'])}, etiketli konvansiyon).")
    if A["kosu_sayisi"] and A["kapi_durdu"]:
        ad, n = A["kapi_durdu"].most_common(1)[0]
        oran = n / A["kosu_sayisi"]
        if oran >= ESIK["kapi_durdurma_orani"]:
            G.append(f"**Kronik kapı `{ad}`**: {A['kosu_sayisi']} koşunun "
                     f"{n}'inde ({_yuzde(oran)}) boru hattı burada durdu — "
                     f"gerekçe: {A['durdu_kapi_metni'].get(ad, YOK)}")
    zayif = []
    for d in set(A["dogrulandi"]) | set(A["dogrulanmadi"]):
        ev, hy = A["dogrulandi"][d], A["dogrulanmadi"][d]
        o = _oran(ev, ev + hy)
        if o is not None and o < ESIK["dogrulama_orani"]:
            zayif.append((d, o, ev + hy))
    for d, o, n in sorted(zayif, key=lambda x: x[1]):
        G.append(f"**`{d}` danışmanı zayıf doğrulanıyor**: {n} koşuda doğrulama "
                 f"oranı {_yuzde(o)} (kural: < {_yuzde(ESIK['dogrulama_orani'])}). "
                 "Bu danışmanın kanıtı sentezde ağırlık kaybediyor.")
    if A["ihlal"]:
        kod, n = A["ihlal"].most_common(1)[0]
        kritik = " (KRİTİK — mühür sebebi)" if kod in OL.KRITIK else ""
        G.append(f"**En sık gözlemci ihlali `{kod}`**: {n} kez{kritik}. "
                 f"Toplam mühürlenen koşu: {A['muhur']}.")
    if A["zorunlu_eksik"]:
        g, n = A["zorunlu_eksik"].most_common(1)[0]
        G.append(f"**Zorunlu girdi `{g}` en sık eksik**: {n} kez. Kapsam bu "
                 "yüzden 1.00'e çıkamıyor; karar eksik kanalla veriliyor.")
    if A["turev_kapsam"]:
        ort = statistics.fmean(A["turev_kapsam"])
        alt = sum(1 for x in A["turev_kapsam"] if x < ESIK["kapsam_esigi"])
        G.append(f"**Türev kapsamı ortalama {ort:.2f}** "
                 f"(hedef {ESIK['kapsam_tam']:.2f}); {alt} koşu turev-akis'in "
                 f"kendi fail-closed eşiğinin ({ESIK['kapsam_esigi']}) altında "
                 "kaldı → danışman doğrulanmamış sayıldı.")
    if A["det_kirik"]:
        G.append(f"**Determinizm KIRIK**: {A['det_kirik']} kez aynı veri imzası "
                 "farklı sonuç imzası üretti. Bu bir motor/hafıza sızıntısı "
                 "işaretidir; kıyas ve akıbet ölçümü güvenilmez hale gelir.")
    elif A["det_ayni"]:
        G.append(f"**Determinizm korunuyor**: {A['det_ayni']} tekrar gözleminde "
                 "aynı veri aynı sonucu verdi.")
    if A["motor_hata"]:
        m, n = A["motor_hata"].most_common(1)[0]
        G.append(f"**En çok sonuç üretemeyen motor `{m}`**: {n} kez "
                 "(K2 hata kaydı + sarmalanan istisna).")
    return G


def _oneriler(A: dict) -> list:
    """Öneriler yalnız ölçülen bulgudan doğar; bulgu yoksa öneri de yok."""
    O = []
    if A["zorunlu_eksik"]:
        g = ", ".join(f"`{k}`×{v}" for k, v in A["zorunlu_eksik"].most_common())
        O.append(f"Zorunlu girdi toplama akışını sıkılaştır ({g}) — CoinGlass "
                 "likidasyon ve görsel okuma damgalı gelmeden koşu başlatma; "
                 "bayat okuma yeni kline ile birleştirilmiyor (fail-closed).")
    if A["kapi_durdu"]:
        ad = A["kapi_durdu"].most_common(1)[0][0]
        O.append(f"`{ad}` kapısında duran koşular için girdi eksiğini koşudan "
                 "ÖNCE denetle; kapı gevşetilmez (yanlış-pozitifin maliyeti "
                 "asimetrik), girdi tamamlanır.")
    if A["det_kirik"]:
        O.append("Determinizm kırılan koşuları (aşağıdaki imza tablosu) tekrar "
                 "koştur; fark motor sürümünden mi, hafıza/ağırlık dosyasından mı "
                 "geliyor ayrıştır.")
    if A["motor_hata"]:
        O.append("Sonuç üretemeyen motorları K2 kapısı öncesinde raporla — "
                 "motor sayısı `min_motor_k2` altına düşerse koşu boşa gider.")
    toplam_katman = sum(sum(v) for v in A["katman_sure"].values())
    if toplam_katman > 0 and A["motor_sure"]:
        m, s = max(((k, sum(v)) for k, v in A["motor_sure"].items()),
                   key=lambda kv: kv[1])
        O.append(f"En pahalı motor `{m}` ({_ms(s)}); ölçüm sarmalamasını bu "
                 "motorun alt adımlarına indir ki darboğaz alt-fonksiyon "
                 "seviyesinde görünsün.")
    if not O:
        O.append(f"{YOK} — ölçülen bulgu yok, öneri üretilmedi (uydurma yok).")
    return O


# --------------------------------------------------------------------------
def markdown(A: dict, kaynak: Path) -> str:
    L = []
    add = L.append

    add("# Piramit Boru Hattı İzleme Raporu")
    add(f"## {A['ilk_ts']} - {A['son_ts']}")
    add("")
    add("> **Not**: Bu rapor `izleme-telemetri` becerisinin yerel JSONL "
        f"ölçümlerinden üretildi (`{kaynak}`, {A['olay_sayisi']} veri noktası). "
        "OTel/Prometheus/Grafana bu ortamda KURULU DEĞİLDİR; dış yığın "
        "opsiyoneldir (`sunucu/`). Her sayı dosyadan okunmuştur.")
    if A["bozuk_satir"]:
        add(f"> ⚠ Bozuk satır: {len(A['bozuk_satir'])} → {A['bozuk_satir'][:3]}")
    add("")

    # ---- Yönetici Özeti (Executive Summary) ----
    kosu = A["kosu_sayisi"]
    ort = statistics.fmean(A["kosu_sure"]) if A["kosu_sure"] else None
    toplam_katman = sum(sum(v) for v in A["katman_sure"].values())
    dogr_t = sum(A["dogrulandi"].values())
    dogr_h = sum(A["dogrulanmadi"].values())
    dogr_o = _oran(dogr_t, dogr_t + dogr_h)
    add("## Yönetici Özeti")
    add("")
    if kosu == 0:
        add(f"{YOK} — dosyada koşu kaydı yok.")
    else:
        durdu = sum(A["kapi_durdu"].values())
        add(f"Bu dönemde **{kosu} piramit koşusu** ölçüldü; **{durdu}** koşu bir "
            f"katman kapısında durdu, **{A['muhur']}** koşu gözlemci kritik "
            f"ihlaliyle **mühürlendi** (işlem yok). Danışman doğrulama oranı "
            f"**{_yuzde(dogr_o)}** ({dogr_t}/{dogr_t + dogr_h}). "
            f"Toplam katman süresi **{_ms(toplam_katman)}**, koşu başına "
            f"ortalama **{_ms(ort)}**.")
        add("")
        add(f"Emir çıktısı: **{A['emir_var']}** koşuda emir üretildi, "
            f"**{A['emir_yok']}** koşuda \"EMİR YOK\". Determinizm: "
            f"**{A['det_ayni']}** tekrar gözlemi aynı, **{A['det_kirik']}** kırık "
            f"({A['det_ilk']} ilk gözlem kıyaslanmadı).")
    add("")

    # ---- Kullanım Metrikleri (Usage Metrics) ----
    add("## Kullanım Metrikleri")
    add("")
    add(_mermaid_pie("Katman Süre Dağılımı (ms)",
                     [(k, sum(v)) for k, v in sorted(
                         A["katman_sure"].items(),
                         key=lambda kv: (OL.KATMANLAR.index(kv[0])
                                         if kv[0] in OL.KATMANLAR else 99))]))
    add("")
    add("### Anahtar Metrikler")
    add("")
    add(f"- **Koşu Sayısı**: {kosu}"
        + (f" ({', '.join(f'{s}: {n}' for s, n in A['semboller'].most_common())})"
           if A["semboller"] else ""))
    add(f"- **Ortalama Koşu Süresi**: {_ms(ort)}"
        + (f" (p50 {_ms(_yuzdelik(A['kosu_sure'], 50))}, "
           f"p95 {_ms(_yuzdelik(A['kosu_sure'], 95))})" if A["kosu_sure"] else ""))
    add(f"- **Danışman Doğrulama Oranı**: {_yuzde(dogr_o)}")
    for d in sorted(set(A["dogrulandi"]) | set(A["dogrulanmadi"])):
        ev, hy = A["dogrulandi"][d], A["dogrulanmadi"][d]
        add(f"  - {d}: {_yuzde(_oran(ev, ev + hy))} ({ev}/{ev + hy})")
    add(f"- **Gözlemci İhlali**: {sum(A['ihlal'].values())} "
        f"(kritik {A['kritik_ihlal']}), **Uyarı**: {sum(A['uyari'].values())}")
    add(f"- **Zorunlu Girdi Eksiği**: {sum(A['zorunlu_eksik'].values())}")
    add("")

    # ---- Katman ve Kapı Dökümü (Linear Integration Metrics) ----
    add("## Katman ve Kapı Dökümü")
    add("")
    add("Boru hattının kendi artefaktından (piramit raporu) okunan kapı ve "
        "danışman kayıtları:")
    add("")
    add("### Kapı Durumu")
    add("")
    add(_tablo(["Katman", "GEÇTİ", "DURDU", "Son durdurma gerekçesi"],
               [[k, A["kapi_gecti"].get(k, 0), A["kapi_durdu"].get(k, 0),
                 A["durdu_kapi_metni"].get(k, "—")]
                for k in OL.KATMANLAR
                if A["kapi_gecti"].get(k) or A["kapi_durdu"].get(k)]))
    add("")
    add("### Doğrulanmayan Danışmanlar")
    add("")
    add(_tablo(["Danışman", "Doğrulandı", "Doğrulanmadı", "Oran"],
               [[d, A["dogrulandi"][d], A["dogrulanmadi"][d],
                 _yuzde(_oran(A["dogrulandi"][d],
                              A["dogrulandi"][d] + A["dogrulanmadi"][d]))]
                for d in sorted(set(A["dogrulandi"]) | set(A["dogrulanmadi"]),
                                key=lambda x: -A["dogrulanmadi"][x])]))
    add("")
    add("### Gözlemci İhlalleri")
    add("")
    add(_tablo(["Kod", "Adet", "Kritik mi", "En sık katman"],
               [[kod, n, "EVET (mühür)" if kod in OL.KRITIK else "hayır",
                 A["ihlal_katman"].most_common(1)[0][0] if A["ihlal_katman"] else YOK]
                for kod, n in A["ihlal"].most_common()]))
    if A["uyari"]:
        add("")
        add("Uyarılar (mühür sebebi değil): "
            + ", ".join(f"`{k}`×{v}" for k, v in A["uyari"].most_common()))
    add("")
    add("### Katman Süre Eğilimi")
    add("")
    add(_tablo(["Katman", "Koşu", "Ortalama", "p95", "En uzun", "Toplam"],
               [[k, len(v), _ms(statistics.fmean(v)), _ms(_yuzdelik(v, 95)),
                 _ms(max(v)), _ms(sum(v))]
                for k, v in sorted(A["katman_sure"].items(),
                                   key=lambda kv: OL.KATMANLAR.index(kv[0])
                                   if kv[0] in OL.KATMANLAR else 99)]))
    add("")
    add("### Boru Hattı Sağlığı Kıyası")
    add("")
    kos = [v for v in A["kosular"].values() if v["toplam_sure"] > 0]
    kos.sort(key=lambda k: k["ts"] or "")
    if len(kos) >= 2:
        yari = len(kos) // 2
        ilk, son = kos[:yari], kos[yari:]

        def _oz(g):
            return (statistics.fmean([x["toplam_sure"] for x in g]),
                    statistics.fmean([x["ihlal"] for x in g]),
                    sum(1 for x in g if x["muhur"]),
                    sum(1 for x in g if x["durdu"]))
        a1, a2, a3, a4 = _oz(ilk)
        b1, b2, b3, b4 = _oz(son)
        add("```mermaid")
        add("graph TD")
        add('    subgraph "İlk yarı"')
        add(f'    B1["Katman süresi: {a1:.0f} ms"]')
        add(f'    B2["İhlal/koşu: {a2:.2f}"]')
        add(f'    B3["Mühür: {a3}"]')
        add(f'    B4["Kapı durdurma: {a4}"]')
        add("    end")
        add('    subgraph "Son yarı"')
        add(f'    A1["Katman süresi: {b1:.0f} ms"]')
        add(f'    A2["İhlal/koşu: {b2:.2f}"]')
        add(f'    A3["Mühür: {b3}"]')
        add(f'    A4["Kapı durdurma: {b4}"]')
        add("    end")
        add('    subgraph "Değişim"')
        add(f'    I1["{(b1 - a1) / a1 * 100:+.1f}%"]' if a1 else '    I1["VERİ YOK"]')
        add(f'    I2["{b2 - a2:+.2f}"]')
        add(f'    I3["{b3 - a3:+d}"]')
        add(f'    I4["{b4 - a4:+d}"]')
        add("    end")
        for i in range(1, 5):
            add(f"    B{i} --> I{i}")
            add(f"    A{i} --> I{i}")
        add("```")
        add("")
        add(f"*Kıyas {len(ilk)} + {len(son)} koşu üzerinden; ölçüm penceresi "
            "kısaysa eğilim YORUMDUR, kanıt değildir.*")
    else:
        add(f"{YOK} — kıyas için en az 2 koşu gerekir "
            f"(şu an {len(kos)}); eğilim UYDURULMAZ.")
    add("")
    add("### Koşu Dökümü")
    add("")
    add(_tablo(["Koşu", "Sembol", "Katman süresi", "İhlal", "Mühür", "Durduğu kapı",
                "Türev kapsamı", "Emir"],
               [[k["kosu_id"], k["sembol"], _ms(k["toplam_sure"]), k["ihlal"],
                 "EVET" if k["muhur"] else "hayır", k["durdu"] or "—",
                 YOK if k["kapsam"] is None else f"{k['kapsam']:.2f}",
                 (k["emir"] or YOK)[:46]]
                for k in kos]))
    add("")

    # ---- Süre Analizi (Cost Analysis) ----
    add("## Süre Analizi")
    add("")
    add("*Kaynak rehberin \"Cost Analysis\" bölümünün karşılığı: bu depoda "
        "harcanan kaynak para/token değil, **koşu süresidir** (USD metriği "
        f"{YOK} — bkz. KANIT.md/SAPMALAR).*")
    add("")
    add(_mermaid_pie("Motor Süre Dağılımı (ms)",
                     sorted(((k, sum(v)) for k, v in A["motor_sure"].items()),
                            key=lambda kv: -kv[1])))
    add("")
    add(f"- **Toplam Katman Süresi**: {_ms(toplam_katman)}")
    add(f"- **Toplam Motor Süresi (sarmalanan)**: "
        f"{_ms(sum(sum(v) for v in A['motor_sure'].values()))}")
    add(f"- **Koşu Başına Süre**: {_ms(ort)}")
    if A["turev_kapsam"]:
        add(f"- **Türev Kapsamı**: ortalama {statistics.fmean(A['turev_kapsam']):.2f}, "
            f"en düşük {min(A['turev_kapsam']):.2f}, en yüksek "
            f"{max(A['turev_kapsam']):.2f} (n={len(A['turev_kapsam'])})")
        kova = Counter()
        for x in A["turev_kapsam"]:
            alt = min(int(x * 4) / 4, 0.75)          # 1.00 üst kovaya taşmasın
            kova[f"{alt:.2f}–{alt + 0.25:.2f}"] += 1
        add(f"- **Kapsam Dağılımı**: "
            + ", ".join(f"{k}: {v}" for k, v in sorted(kova.items())))
    else:
        add(f"- **Türev Kapsamı**: {YOK}")
    add(f"- **Determinizm**: {A['det_ayni']} aynı / {A['det_kirik']} kırık / "
        f"{A['det_ilk']} ilk gözlem")
    if A["det_kirik_kayit"]:
        add("")
        add(_tablo(["Koşu", "Veri imzası", "Önceki sonuç", "Yeni sonuç"],
                   [[r["kosu_id"], r["veri_imzasi"], r["onceki"], r["yeni"]]
                    for r in A["det_kirik_kayit"]]))
    add("")

    # ---- Uygulanabilir İçgörüler (Actionable Insights) ----
    add("## Uygulanabilir İçgörüler")
    add("")
    G = _icgoruler(A)
    if not G:
        add(f"{YOK} — ölçüm yok, içgörü üretilmedi.")
    for i, g in enumerate(G, 1):
        add(f"{i}. {g}")
    add("")

    # ---- Öneriler (Recommendations) ----
    add("## Öneriler")
    add("")
    for i, o in enumerate(_oneriler(A), 1):
        add(f"{i}. {o}")
    add("")

    # ---- Koşu Süresi Dağılımı (Session Duration Distribution) ----
    add("## Koşu Süresi Dağılımı")
    add("")
    hepsi = A["kosu_sure"] or [k["toplam_sure"] for k in kos]
    if hepsi:
        kenar = [0, 500, 1000, 2500, 5000, 10000, float("inf")]
        etiket = ["< 0.5 sn", "0.5–1 sn", "1–2.5 sn", "2.5–5 sn", "5–10 sn", "10+ sn"]
        say = [0] * len(etiket)
        for x in hepsi:
            for i in range(len(etiket)):
                if kenar[i] <= x < kenar[i + 1]:
                    say[i] += 1
                    break
        add(_tablo(["Aralık", "Koşu", "Sıklık"],
                   [[etiket[i], say[i], "█" * say[i] or "—"]
                    for i in range(len(etiket))]))
        add("")
        add(f"*Kaynak seri: {'piramit.kosu.sure_ms' if A['kosu_sure'] else 'katman süreleri toplamı'} "
            f"(n={len(hepsi)}); p50 {_ms(_yuzdelik(hepsi, 50))}, "
            f"p95 {_ms(_yuzdelik(hepsi, 95))}, en uzun {_ms(max(hepsi))}.*")
    else:
        add(f"{YOK} — süre ölçümü bulunamadı.")
    add("")
    add("### Varsayımlar / eşik kaynağı")
    add("")
    for k, v in ESIK.items():
        add(f"- `{k}` = {v} — ETİKETLİ KONVANSİYON (kalibre edilmiş piyasa eşiği "
            "DEĞİL; içgörü kuralı sınırıdır)")
    add("")
    add("---")
    add("")
    add("*Bu rapor `izleme-telemetri/scripts/rapor.py` tarafından yerel JSONL "
        "ölçümünden otomatik üretildi. Gerçek = dosyadan okunan sayı; yorum = "
        "eşik kuralıyla türetilen içgörü; eksik = VERİ YOK.*")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------
def uret(dosya=None, out=None) -> tuple:
    olaylar = OL.oku(dosya)
    A = topla(olaylar)
    md = markdown(A, OL.dosya_yolu(dosya))
    if out:
        p = Path(str(out)).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(md, encoding="utf-8")
    return md, A


def self_test(ornek=False) -> dict:
    """olcum --self-test verisini üret → rapor yaz → sayıları BAĞIMSIZ doğrula.

    Doğrulama dairesel DEĞİLDİR: beklenen sayılar `topla()` ile değil, ham
    JSONL satırları tek tek sayılarak hesaplanır ve Markdown metninde ARANIR.

    Rapor zaman damgası ve ölçülen süreler her koşuda değişir; bu yüzden
    varsayılan hedef geçici dizindir (çalışma ağacı kirlenmez). Depodaki
    örneği tazelemek için `--ornek-yaz`.
    """
    dizin = ORNEK_DIZIN if ornek else Path(tempfile.mkdtemp(prefix="izleme_rapor_ozt_"))
    dizin.mkdir(parents=True, exist_ok=True)
    jsonl = dizin / "olcum_ornek.jsonl"
    o_sonuc = OL.self_test(jsonl)
    OL.ayarla(jsonl)
    md_yol = dizin / "rapor_ornek.md"
    md, A = uret(jsonl, md_yol)

    # --- BAĞIMSIZ sayım: ham satırlardan ---
    ham = [json.loads(x) for x in jsonl.read_text(encoding="utf-8").splitlines() if x.strip()]
    def _c(ad, **f):
        n = 0
        for o in ham:
            if o["descriptor"]["name"] != ad:
                continue
            a = o.get("attributes") or {}
            if all(a.get(k) == v for k, v in f.items()):
                n += int(o["value"])
        return n
    b_kosu = _c("piramit.kosu.sayisi")
    b_muhur = _c("piramit.muhur")
    b_ihlal = _c("piramit.gozlemci.ihlal")
    b_eksik = _c("piramit.zorunlu_girdi.eksik")
    b_durdu = sum(int(o["value"]) for o in ham
                  if o["descriptor"]["name"] == "piramit.kapi.durdu"
                  and int(o["value"]) > 0)
    b_dogrulanmadi = _c("piramit.danisman.dogrulanmadi")
    b_kirik = sum(1 for o in ham if o["descriptor"]["name"] == "piramit.determinizm"
                  and o["value"] == 0.0 and not o["attributes"]["ilk_gozlem"])

    kontroller = [
        ("olcum öz-testi geçti", o_sonuc["SONUC"] == "GEÇTİ"),
        ("rapor dosyası yazıldı", md_yol.exists() and md_yol.stat().st_size > 0),
        ("koşu sayısı raporda doğru",
         f"**{b_kosu} piramit koşusu**" in md and A["kosu_sayisi"] == b_kosu),
        ("kapı durdurma sayısı doğru",
         f"**{b_durdu}** koşu bir katman kapısında durdu" in md
         and sum(A["kapi_durdu"].values()) == b_durdu),
        ("mühür sayısı doğru",
         f"**{b_muhur}** koşu gözlemci kritik" in md and A["muhur"] == b_muhur),
        ("ihlal sayısı doğru", A["ihlal"].total() == b_ihlal
         and f"**Gözlemci İhlali**: {b_ihlal}" in md),
        ("zorunlu girdi eksiği doğru",
         f"**Zorunlu Girdi Eksiği**: {b_eksik}" in md
         and A["zorunlu_eksik"].total() == b_eksik),
        ("doğrulanmayan danışman sayısı doğru",
         A["dogrulanmadi"].total() == b_dogrulanmadi),
        ("determinizm kırığı raporlandı",
         A["det_kirik"] == b_kirik and f"**{b_kirik}** kırık" in md),
        ("kaynak bölümleri eksiksiz",
         all(b in md for b in ["## Yönetici Özeti", "## Kullanım Metrikleri",
                               "### Anahtar Metrikler", "## Katman ve Kapı Dökümü",
                               "### Kapı Durumu", "### Doğrulanmayan Danışmanlar",
                               "## Süre Analizi", "## Uygulanabilir İçgörüler",
                               "## Öneriler", "## Koşu Süresi Dağılımı"])),
        ("mermaid görselleştirme var", md.count("```mermaid") >= 2),
        ("uydurma sayı yok: tüm katman adları defterden",
         all(k in OL.KATMANLAR for k in A["katman_sure"])),
    ]
    gecen = sum(1 for _, ok in kontroller if ok)
    return {
        "arac": "rapor.py --self-test",
        "olcum_dosyasi": str(jsonl), "rapor_dosyasi": str(md_yol),
        "rapor_satir": md.count("\n"), "olay_sayisi": A["olay_sayisi"],
        "bagimsiz_sayim": {"kosu": b_kosu, "kapi_durdu": b_durdu,
                           "muhur": b_muhur, "ihlal": b_ihlal,
                           "zorunlu_eksik": b_eksik,
                           "dogrulanmadi": b_dogrulanmadi,
                           "determinizm_kirik": b_kirik},
        "kontroller": [{"ad": a, "sonuc": "GEÇTİ" if ok else "KALDI"}
                       for a, ok in kontroller],
        "gecen": f"{gecen}/{len(kontroller)}",
        "SONUC": "GEÇTİ" if gecen == len(kontroller) else "KALDI",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="ölçüm JSONL → Markdown rapor")
    ap.add_argument("--dosya", help="ölçüm JSONL "
                                    f"(varsayılan: {OL.VARSAYILAN_DOSYA})")
    ap.add_argument("--out", help="Markdown çıktı yolu (yoksa stdout)")
    ap.add_argument("--json", action="store_true", help="toplulaştırmayı JSON bas")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--ornek-yaz", action="store_true",
                    help="öz-test çıktısını depodaki ornek/ dizinine yaz "
                         "(varsayılan: geçici dizin — çalışma ağacı kirlenmez)")
    a = ap.parse_args()

    if a.self_test:
        s = self_test(ornek=a.ornek_yaz)
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0 if s["SONUC"] == "GEÇTİ" else 1

    md, A = uret(a.dosya, a.out)
    if a.json:
        yazdirilabilir = {k: (dict(v) if isinstance(v, (Counter, defaultdict)) else v)
                          for k, v in A.items()}
        print(json.dumps(yazdirilabilir, ensure_ascii=False, indent=2,
                         default=str))
    elif a.out:
        print(f"Rapor yazıldı: {a.out} ({A['olay_sayisi']} veri noktası, "
              f"{A['kosu_sayisi']} koşu)")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
