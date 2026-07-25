#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EŞİK KALİBRATÖRÜ — sentez karar kapıları her koşuda VERİDEN türetilir.

Sorun (kullanıcı tarafından işaretlendi): `sentez.py`'nin üç karar kapısı
(score 0.15, min_agreement 0.55, min_side_weight 0.60) TASARIM VARSAYIMIYDI.
Sabit eşik, rejim değiştiğinde ya çok gevşek (çalkantıda sahte sinyal) ya çok
sıkı (güçlü trendde kaçan işlem) olur. Literatür bunu açıkça söyler: "Arbitrary
thresholds give false signals because they fail to capture the persistence in
regimes and changing volatilities" (Kritzman, Page & Turkington, Financial
Analysts Journal 2012). Ayrıca getiri öngörülebilirliği ZAMANLA DEĞİŞİR
(Adaptive Markets Hypothesis; Urquhart & McGroarty 2016; Lim & Brooks 2011) —
yani tek bir sabit eşiğin "doğru" olduğu bir dünya yok.

ÇÖZÜM — iki bileşenli, ikisi de ölçülen:

  (A) TABAN — "sinyal kendi gürültüsünü aşıyor mu + çoğunluk var mı?"
      · score eşiği ÖLÇÜLÜR: danışmanlar yerine konularak yeniden örneklenir
        (bootstrap) → skorun örnekleme hatası SE. Eşik = z_{1-α/2} × SE.
        Aynı yöne bakan kurul → küçük SE → düşük eşik; bölünmüş kurul →
        büyük SE → yüksek eşik. Koşudan koşuya değişir.
      · uzlaşı ve yön-ağırlığı tabanı YAPISALDIR: çoğunluk kuralı (0.5 pay,
        mutlak ölçekte 0.5 × toplam etkin ağırlık). Bu veriden türetilmez ve
        çıktıda öyle etiketlenir. Yan fayda: sabit 0.60 bir ÖLÇEK HATASIYDI —
        yön ağırlığı mutlak toplamdır, danışman sayısı arttıkça kapı kendiliğinden
        gevşiyordu (4 danışmanda toplam ≈ 2.2 iken eşik 0.60).
      · Sign-flip randomizasyon testi eşik ÜRETMEZ, TANI verir: k yönlü
        danışmanla ulaşılabilir en küçük p, p_min = 2/2^k'dır (k=3 → 0.25),
        yani küçük kurulda α=0.05 matematiksel olarak ulaşılamaz. Bu ölçülüp
        raporlanır; gizlenmez.

  (B) REJİM SERTLİĞİ — "bu piyasada yön devam ediyor mu?"
      O koşunun KENDİ kline'ından ölçülür:
        · Lo–MacKinlay (1988) varyans oranı VR(q) + heteroskedastisiteye
          dayanıklı z: VR>1 momentum/trend, VR<1 ortalamaya dönüş.
        · Yön devamlılığı: h barlık getirinin işareti, önceki h barlık
          getirinin işaretiyle aynı mı? Ham oran değil, WILSON ALT SINIRI
          (kötümser) alınır — küçük örnek şişirmesin.
        · Başabaş oran: R_MIN ödül/risk ile p_be = 1/(1+R_MIN).
      sertlik = clamp(p_be / p_lo, 1.0, sertlik_tavan)
      Yani ölçülen devamlılık başabaşın ALTINDAYSA kuruldan orantılı olarak
      DAHA FAZLA kanıt istenir. Devamlılık başabaşın üstündeyse taban aynen
      kalır (sertlik 1.0). Sertlik asla 1.0'ın ALTINA inmez: eşiği gevşetip
      işlem sayısını artırmak kanıtlanmamış bir bahistir; yanlış-pozitifin
      maliyeti (gerçek para) kaçan işlemin maliyetinden büyüktür (asimetrik
      maliyetli eşik seçimi — Youden J'nin maliyet oranı eleştirisi).

  Son eşik = clamp(taban × sertlik, korkuluk_alt, korkuluk_ust).

FAIL-CLOSED: bar sayısı yetersizse, yönlü danışman 2'den azsa ya da ölçüm
yapılamıyorsa STATİK korkuluk değerleri kullanılır ve bu AÇIKÇA etiketlenir
("VERİ YOK → statik korkuluk"). Uydurma eşik üretilmez.

Determinist: tohumlu RNG (seed=7), duvar saati yok. Aynı girdi = aynı eşik.

Kullanım:
    python esik_kalibre.py --job job.json
    job = {"advisors": [...], "verifier": {...}, "m15": "engine/girdi/m15.json",
           "r_min": 1.35, "ufuk_bar": 8}
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SKILLS = _HERE.parent.parent
for _p in (SKILLS / "karar-kurulu" / "scripts", SKILLS / "grafik-calisma" / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import sentez as SZ          # noqa: E402  — AYNI etkin ağırlık aritmetiği
import kalibrasyon as KB     # noqa: E402  — wilson_lo + α konvansiyonu

YOK = "VERİ YOK"

KONVANSIYON = {
    # α: bilimsel anlamlılık konvansiyonu (kalibrasyon.py ile aynı kaynak)
    "alpha": KB.KONVANSIYON["alpha"],
    "n_perm": 2000,           # sign-flip tekrarı — p çözünürlüğü 1/(n+1)
    "seed": 7,                # determinizm (repo kuralı: rastgelelik tohumlu)
    "min_bar": 120,           # VR/devamlılık için asgari bar (altı → statik)
    "min_yonlu_danisman": 2,  # altında null dağılımı dejenere olur
    "ufuk_bar": 8,            # devamlılık/VR ufku (bar) — job'dan gelebilir
    "sertlik_tavan": 2.0,     # rejim sertliği üst sınırı (korkuluk)
    # STATİK KORKULUKLAR — hem fallback hem clamp sınırları (etiketli)
    "statik": {"score": 0.15, "min_agreement": 0.55, "min_side_weight": 0.60},
    "alt": {"score": 0.05, "min_agreement": 0.40, "min_side_weight": 0.30},
    "ust": {"score": 0.60, "min_agreement": 0.90, "min_side_weight": 3.00},
}


# --------------------------------------------------------------------------
# Kline okuma (Binance 12 alanlı) — motorun kendi parseri kadar basit
# --------------------------------------------------------------------------
def kapanislar(yol: Path) -> list:
    d = json.loads(Path(yol).read_text(encoding="utf-8"))
    out = []
    for x in d:
        if isinstance(x, list) and len(x) >= 5:
            out.append(float(x[4]))
        elif isinstance(x, dict):
            v = x.get("close", x.get("c"))
            if v is not None:
                out.append(float(v))
    return out


# --------------------------------------------------------------------------
# (B1) Lo–MacKinlay varyans oranı — trend mi, ortalamaya dönüş mü?
# --------------------------------------------------------------------------
def varyans_orani(kapanis: list, q: int) -> dict:
    """VR(q) + heteroskedastisiteye dayanıklı z (Lo & MacKinlay 1988).

    Saf rassal yürüyüşte q-periyot getiri varyansı = q × 1-periyot varyansı,
    yani VR(q)=1. VR>1 pozitif otokorelasyon (trend), VR<1 negatif (dönüş).
    """
    r = [math.log(kapanis[i] / kapanis[i - 1])
         for i in range(1, len(kapanis)) if kapanis[i - 1] > 0]
    n = len(r)
    if n < max(20, 2 * q):
        return {"durum": f"{YOK} — {n} getiri < gerek {max(20, 2 * q)}"}
    mu = sum(r) / n
    var1 = sum((x - mu) ** 2 for x in r) / (n - 1)
    if var1 <= 0:
        return {"durum": f"{YOK} — birim varyans sıfır"}
    # q-periyot örtüşen toplamlar
    toplam = [sum(r[i:i + q]) for i in range(n - q + 1)]
    m = q * (n - q + 1) * (1 - q / n)
    varq = sum((s - q * mu) ** 2 for s in toplam) / m if m > 0 else float("nan")
    vr = varq / var1
    # heteroskedastisiteye dayanıklı asimptotik varyans (Lo–MacKinlay teorem 2)
    delta_top = 0.0
    for j in range(1, q):
        pay = sum((r[i] - mu) ** 2 * (r[i - j] - mu) ** 2
                  for i in range(j, n))
        payda = (sum((x - mu) ** 2 for x in r)) ** 2
        d_j = (n * pay / payda) if payda > 0 else 0.0
        delta_top += ((2.0 * (q - j) / q) ** 2) * d_j
    z = ((vr - 1.0) / math.sqrt(delta_top / n)) if delta_top > 0 else float("nan")
    if vr > 1:
        etiket = "TREND (momentum)"
    elif vr < 1:
        etiket = "ORTALAMAYA DÖNÜŞ (çalkantı)"
    else:
        etiket = "RASSAL YÜRÜYÜŞ"
    return {"durum": "ÖLÇÜLDÜ", "VR": round(vr, 4), "z": (round(z, 3) if z == z else YOK),
            "q": q, "n_getiri": n, "etiket": etiket,
            "yorum": ("|z| > 1.96 → %5 düzeyinde rassal yürüyüşten anlamlı sapma"
                      " (Lo–MacKinlay 1988)")}


# --------------------------------------------------------------------------
# (B2) Yön devamlılığı — kötümser (Wilson) tahmin
# --------------------------------------------------------------------------
def yon_devamliligi(kapanis: list, h: int) -> dict:
    """P(sonraki h barın işareti = önceki h barın işareti), Wilson alt sınırı.

    Bu, "trend devam eder mi?" sorusunun doğrudan, parametresiz ölçümüdür.
    Ham oran yerine Wilson alt sınırı kullanılır: küçük örnek iyimserliği
    kararı yanıltmasın (aynı disiplin K5 ağırlık kalibrasyonunda da var).
    """
    n = len(kapanis)
    if n < 3 * h + 10:
        return {"durum": f"{YOK} — {n} bar < gerek {3 * h + 10}"}
    ayni = toplam = 0
    for i in range(h, n - h):
        onceki = kapanis[i] - kapanis[i - h]
        sonraki = kapanis[i + h] - kapanis[i]
        if onceki == 0 or sonraki == 0:
            continue
        toplam += 1
        if (onceki > 0) == (sonraki > 0):
            ayni += 1
    if toplam == 0:
        return {"durum": f"{YOK} — ölçülebilir örnek yok"}
    p_ham = ayni / toplam
    p_lo = KB.wilson_lo(ayni, toplam)
    return {"durum": "ÖLÇÜLDÜ", "h_bar": h, "ornek": toplam, "ayni_yon": ayni,
            "p_ham": round(p_ham, 4), "p_wilson_lo": round(p_lo, 4),
            "yorum": "p_wilson_lo = devamlılığın kötümser alt sınırı"}


def rejim_olc(kapanis: list, r_min: float, h: int) -> dict:
    """Rejim ölçümü + sertlik katsayısı (başabaş oranla kıyaslanmış)."""
    vr = varyans_orani(kapanis, h)
    dev = yon_devamliligi(kapanis, h)
    p_be = 1.0 / (1.0 + float(r_min))          # başabaş kazanma oranı
    out = {"varyans_orani": vr, "devamlilik": dev,
           "basabas_oran": round(p_be, 4),
           "basabas_kaynagi": f"1/(1+R_MIN), R_MIN={r_min} (motor kuralı)"}
    if dev.get("durum") != "ÖLÇÜLDÜ":
        out["sertlik"] = None
        out["sertlik_gerekce"] = f"{YOK} — devamlılık ölçülemedi, sertlik yok"
        return out
    p_lo = dev["p_wilson_lo"]
    if p_lo <= 0:
        sertlik = KONVANSIYON["sertlik_tavan"]
        gerekce = "devamlılık alt sınırı 0 → tavan sertlik (fail-closed)"
    else:
        ham = p_be / p_lo
        sertlik = min(max(ham, 1.0), KONVANSIYON["sertlik_tavan"])
        gerekce = (f"p_be {p_be:.4f} / p_lo {p_lo:.4f} = {ham:.3f} → "
                   f"clamp[1.0, {KONVANSIYON['sertlik_tavan']}] = {sertlik:.3f}"
                   + ("; devamlılık başabaşın ÜSTÜNDE, taban korunur"
                      if ham <= 1.0 else
                      "; devamlılık başabaşın ALTINDA, kuruldan daha çok kanıt istenir"))
    out["sertlik"] = round(sertlik, 4)
    out["sertlik_gerekce"] = gerekce
    return out


# --------------------------------------------------------------------------
# (A) Sign-flip null → istatistiksel taban eşikleri
# --------------------------------------------------------------------------
def _rng(seed: int):
    """Determinist, bağımlılıksız LCG (numpy zorunlu değil)."""
    durum = {"s": (seed * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)}

    def sonraki() -> float:
        durum["s"] = (durum["s"] * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
        return ((durum["s"] >> 11) & ((1 << 53) - 1)) / float(1 << 53)
    return sonraki


def signflip_tani(rows: list, alpha: float, n_perm: int, seed: int) -> dict:
    """Sign-flip randomizasyon TANISI (eşik değil — ulaşılabilirlik denetimi).

    İlk tasarımda eşik doğrudan bu null'ın %95 quantile'ı olacaktı. ÖLÇÜNCE
    çıktı ki k yönlü danışmanla iki-yönlü randomizasyonun ulaşabileceği en
    küçük p değeri p_min = 2/2^k'dır: k=3 → 0.25, k=4 → 0.125, k=5 → 0.0625.
    Yani 3-4 danışmanlık bir kurulda α=0.05 anlamlılık MATEMATİKSEL OLARAK
    ULAŞILAMAZ; quantile en uç atoma oturur ve eşik "gözlenen skorun kendisi"
    olur (kapı anlamsızlaşır). Bu yüzden sign-flip burada eşik üretmez, yalnız
    dürüst bir tanı verir: gözlenen skor, bilgisiz kurulun neresinde?
    """
    yonlu = [i for i, r in enumerate(rows) if r["dir"] != 0]
    k = len(yonlu)
    if k < KONVANSIYON["min_yonlu_danisman"]:
        return {"durum": f"{YOK} — {k} yönlü danışman < "
                         f"{KONVANSIYON['min_yonlu_danisman']}"}
    gozlenen = abs(SZ.olcumler(rows)["score"])
    rnd = _rng(seed)
    ge = 0
    for _ in range(n_perm):
        sanal = [{**r, "dir": (1 if rnd() < 0.5 else -1)} if i in yonlu else r
                 for i, r in enumerate(rows)]
        if abs(SZ.olcumler(sanal)["score"]) >= gozlenen - 1e-12:
            ge += 1
    p = (1 + ge) / (n_perm + 1)
    p_min = 2.0 / (2 ** k)
    return {"durum": "ÖLÇÜLDÜ", "yonlu_danisman": k, "gozlenen_skor": round(gozlenen, 4),
            "randomizasyon_p": round(p, 4), "p_min_ulasilabilir": round(p_min, 4),
            "alpha_ulasilabilir": bool(p_min <= alpha), "n_perm": n_perm,
            "yorum": (f"p_min = 2/2^{k} = {p_min:.4f}; α={alpha} "
                      + ("ulaşılabilir" if p_min <= alpha else
                         "BU KURUL BÜYÜKLÜĞÜNDE ULAŞILAMAZ — sign-flip eşik "
                         "üretemez, yalnız tanıdır"))}


def bootstrap_taban(rows: list, alpha: float, n_boot: int, seed: int) -> dict:
    """Taban eşikler: sinyal KENDİ gürültüsünü aşmalı + yapısal çoğunluk.

    score eşiği  : z_{1-α/2} × SE_bootstrap(skor). Danışmanlar yerine
                   konularak (with replacement) yeniden örneklenir; skorun
                   örnekleme hatası ölçülür. Anlamı: "skor sıfırdan, kendi
                   iç dağılımına göre anlamlı biçimde farklı mı?" Aynı yöne
                   bakan kurul → küçük SE → düşük eşik; bölünmüş kurul →
                   büyük SE → yüksek eşik. Küçük kurulda da dejenere olmaz.
    uzlaşı eşiği : 0.5 — YAPISAL çoğunluk kuralı (ağırlığın yarısından fazlası
                   tek tarafta). Veriden türetilmez, açıkça etiketlenir.
    yön ağırlığı : 0.5 × toplam etkin ağırlık — aynı çoğunluk kuralının MUTLAK
                   ölçekteki karşılığı. Sabit 0.60 ölçek hatasıydı: danışman
                   sayısı arttıkça mutlak toplam büyüdüğü için kapı kendiliğinden
                   gevşiyordu (4 danışmanda toplam ~2.2 iken eşik 0.60).
    """
    n = len(rows)
    if n < KONVANSIYON["min_yonlu_danisman"]:
        return {"durum": f"{YOK} — {n} danışman < {KONVANSIYON['min_yonlu_danisman']}"}
    rnd = _rng(seed)
    skorlar = []
    for _ in range(n_boot):
        ornek = [rows[int(rnd() * n) % n] for _ in range(n)]
        skorlar.append(SZ.olcumler(ornek)["score"])
    ort = sum(skorlar) / len(skorlar)
    se = math.sqrt(sum((x - ort) ** 2 for x in skorlar) / max(1, len(skorlar) - 1))
    try:
        import statistics  # noqa: PLC0415
        z = statistics.NormalDist().inv_cdf(1.0 - float(alpha) / 2.0)
    except Exception:  # noqa: BLE001
        z = 1.96
    toplam_w = sum(r["eff_weight"] for r in rows)
    isaret = sum(1 for x in skorlar if (x > 0) == (SZ.olcumler(rows)["score"] > 0))
    return {"durum": "ÖLÇÜLDÜ", "n_boot": n_boot, "alpha": alpha, "z": round(z, 4),
            "se_skor": round(se, 4), "bootstrap_ort_skor": round(ort, 4),
            "isaret_kararliligi": round(isaret / len(skorlar), 4),
            "toplam_etkin_agirlik": round(toplam_w, 4),
            "score": round(z * se, 4),
            "min_agreement": 0.5,
            "min_side_weight": round(0.5 * toplam_w, 4),
            "yorum": ("score = z×SE_bootstrap (sinyal kendi gürültüsünü aşmalı); "
                      "uzlaşı/yön ağırlığı = çoğunluk kuralı (yapısal, "
                      "veriden türetilmedi — ölçek TOPLAM AĞIRLIKTAN gelir)")}


def _quantile(xs: list, q: float) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    i = q * (len(s) - 1)
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


# --------------------------------------------------------------------------
# Birleştirme
# --------------------------------------------------------------------------
def esikler(job: dict) -> dict:
    p = {**KONVANSIYON, **(job.get("konvansiyon") or {})}
    advisors = job.get("advisors") or []
    rows = SZ.satirlar(advisors, job.get("verifier") or {},
                       float((job.get("thresholds") or {}).get("refute_penalty", 0.25)))
    h = int(job.get("ufuk_bar") or p["ufuk_bar"])
    r_min = float(job.get("r_min") or 1.35)

    kapanis, kaynak = [], job.get("m15")
    if kaynak:
        try:
            kapanis = kapanislar(Path(kaynak))
        except (OSError, json.JSONDecodeError, ValueError, KeyError) as e:
            kapanis = []
            kaynak = f"{kaynak} OKUNAMADI ({type(e).__name__})"

    rejim = (rejim_olc(kapanis, r_min, h) if len(kapanis) >= p["min_bar"]
             else {"durum": f"{YOK} — {len(kapanis)} bar < asgari {p['min_bar']}",
                   "sertlik": None})
    taban = bootstrap_taban(rows, p["alpha"], p["n_perm"], p["seed"])
    tani = signflip_tani(rows, p["alpha"], p["n_perm"], p["seed"])

    statik = dict(p["statik"])
    if taban.get("durum") != "ÖLÇÜLDÜ" or rejim.get("sertlik") is None:
        return {
            "esikler": statik, "kaynak": "STATİK KORKULUK (fail-closed)",
            "gerekce": [x for x in (taban.get("durum"), rejim.get("durum"),
                                    rejim.get("sertlik_gerekce")) if x],
            "taban": taban, "rejim": rejim, "sertlik": None,
            "signflip_tanisi": tani,
            "not": ("Eşik VERİDEN türetilemedi → statik korkuluk kullanıldı ve "
                    "AÇIKÇA etiketlendi. Uydurma eşik üretilmez."),
            "varsayimlar": _varsayimlar(p, r_min, h),
        }

    s = float(rejim["sertlik"])
    son, ayrinti = {}, {}
    for ad in ("score", "min_agreement", "min_side_weight"):
        ham = taban[ad] * s
        kirpik = min(max(ham, p["alt"][ad]), p["ust"][ad])
        son[ad] = round(kirpik, 4)
        ayrinti[ad] = {"null_taban": taban[ad], "sertlik": round(s, 4),
                       "ham": round(ham, 4), "son": round(kirpik, 4),
                       "korkuluk": [p["alt"][ad], p["ust"][ad]],
                       "kirpildi": abs(kirpik - ham) > 1e-9,
                       "statik_karsiligi": statik[ad],
                       "degisim_statige_gore": round(kirpik - statik[ad], 4)}
    return {
        "esikler": son,
        "kaynak": ("VERİDEN TÜRETİLDİ: bootstrap gürültü tabanı (score) + "
                   "çoğunluk kuralı (uzlaşı/yön ağırlığı) × ÖLÇÜLEN rejim "
                   "sertliği (yön devamlılığı vs başabaş oran)"),
        "taban": taban, "rejim": rejim, "sertlik": round(s, 4),
        "signflip_tanisi": tani, "ayrinti": ayrinti, "bar": len(kapanis), "veri_kaynagi": str(kaynak),
        "varsayimlar": _varsayimlar(p, r_min, h),
    }


def _varsayimlar(p: dict, r_min: float, h: int) -> list:
    return [
        f"α = {p['alpha']} (bilimsel konvansiyon — piyasadan türetilmez), "
        f"n_perm = {p['n_perm']}, tohum = {p['seed']} (determinizm)",
        f"ufuk h = {h} bar (kurulum ölçeği); VR(q) aynı q ile ölçülür",
        f"başabaş oran = 1/(1+{r_min}) — R_MIN motor kuralı",
        f"sertlik ∈ [1.0, {p['sertlik_tavan']}]: eşik yalnız SIKILAŞIR, "
        "gevşemez (yanlış-pozitifin maliyeti asimetrik)",
        f"korkuluk aralıkları: score {p['alt']['score']}–{p['ust']['score']}, "
        f"uzlaşı {p['alt']['min_agreement']}–{p['ust']['min_agreement']}, "
        f"yön ağırlığı {p['alt']['min_side_weight']}–{p['ust']['min_side_weight']} "
        "(kırpılma çıktıda `kirpildi` ile raporlanır)",
        "uzlaşı ve yön-ağırlığı tabanı = çoğunluk kuralı (YAPISAL, piyasadan "
        "türetilmedi); yalnız score tabanı bootstrap ile ÖLÇÜLÜR",
        "sign-flip randomizasyon testi eşik ÜRETMEZ (küçük kurulda p_min = "
        "2/2^k > α); yalnız tanı olarak raporlanır",
    ]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sentez karar kapılarını veriden türet")
    ap.add_argument("--job", required=True)
    a = ap.parse_args(argv)
    job = json.loads(Path(a.job).read_text(encoding="utf-8"))
    print(json.dumps(esikler(job), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
