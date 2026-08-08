#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EMİR PLANI — kararı MARKET/LIMIT emrine çeviren motor.

Sorun: boru hattı "YÖN LONG ama temiz giriş yok" diyordu ve kullanıcı elinde
uygulanabilir bir şey olmadan kalıyordu. Seviyeleri elle kurmak da yasak
(uydurma riski). Bu motor aradaki boşluğu MEKANİKLEŞTİRİR: seviyeler yalnız
ÖLÇÜLEN yapıdan (swing + FVG + ATR) gelir, her aday `rr_denetim`den ve —
sabit-USDT profili varsa — `usd_hedef` kapılarından geçer.

ÇIKTI SÖZLEŞMESİ (hikâye değil, emir):
    EMİR: LIMIT LONG @1863.68 | stop 1830.35 | T1 1908.68 | R 1.35
ya da
    EMİR YOK — <mekanik gerekçe>

KURALLAR
1. Giriş adayları ÖLÇÜLENDİR: açık 15M FVG kenarları + teyitli swing
   destek/dirençler. Rastgele "yuvarlak seviye" YOK.
2. Stop:
   · sabit-USDT profili varsa → mesafe profilden (usdt / kontrat), yönün
     aleyhine; ayrıca stop yapının ÖTESİNDE olmalı (usd_hedef sınar).
   · profil yoksa → giriş yapısının ötesindeki ilk teyitli swing.
3. Hedef: yön tarafındaki İLK likidite (teyitli swing). Yoksa aday düşer —
   "R katı" uydurma hedef ÜRETİLMEZ.
4. Her aday `rr_denetim`den geçer: ŞİŞİRİLMİŞ olan REDDEDİLİR (dar stop +
   uzak hedef eşleşmesi ATR ölçeğiyle yakalanır).
5. R < r_min olan aday reddedilir (depo kuralı, varsayılan 1.35).
6. MARKET yalnız fiyat ZATEN giriş bölgesindeyse verilir (tolerans 0.1×ATR);
   aksi halde LIMIT. "Şimdi gir" demek için fiyatın orada olması gerekir.
7. Hiçbir aday geçemezse "EMİR YOK" + hangi kapının düştüğü yazılır.

Determinist. Uydurma sayı yok: her seviye bir ölçümden gelir.
⚠️ Yalnız karar-destek; canlı/otomatik emir (gerçek para) DAHİL DEĞİL.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SKILL = _HERE.parent
SKILLS = SKILL.parent
REPO = SKILLS.parent.parent
ENGINE = REPO / "engine"
for _p in (str(ENGINE),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

RR = SKILLS / "karar-kurulu" / "scripts" / "rr_denetim.py"
USD = _HERE / "usd_hedef.py"
YOK = "VERİ YOK"

KONVANSIYON = {
    "r_min": 1.35,              # depo risk kuralı
    "market_tolerans_atr": 0.1,  # fiyat bölgeye bu kadar yakınsa MARKET sayılır
    "azami_aday": 6,            # rapor şişmesin
    "asgari_mesafe_atr": 0.15,   # girişe bu kadar yakın hedef/stop anlamsız
}


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _nd(ref) -> int:
    """Ondalık hane sayısı fiyat ölçeğinden türetilir.

    Sabit 6 hane, mikro-fiyatlı sembolde (PEPE tipi, ~1e-5) farklı yapı
    seviyelerini TEK seviyeye çökertip yapıda olmayan giriş üretiyordu
    (giriş==stop, R basılan seviyelerle tutarsız)."""
    try:
        r = abs(float(ref))
    except (TypeError, ValueError):
        return 6
    if r == 0 or r >= 0.1:
        return 6
    return min(12, 6 + int(math.ceil(-math.log10(r))))


def _kos(script: Path, job: dict) -> dict:
    """Denetim motorunu subprocess ile koştur (bağımsız kanıt)."""
    tmp = SKILL / "state" / "_job" / f"{script.stem}_emir.json"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    try:
        pr = subprocess.run([sys.executable, str(script), "--job", str(tmp)],
                            capture_output=True, text=True, timeout=90,
                            cwd=str(REPO))
        if pr.stdout.strip().startswith("{"):
            return json.loads(pr.stdout)
        return {"_hata": (pr.stderr or pr.stdout or "").strip()[-200:]}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        return {"_hata": f"{type(e).__name__}: {e}"}


def yapi_oku(m15: str, h4: str) -> dict:
    """Swing/FVG/ATR ölçümü — motorun KENDİ parseriyle (ikinci kopya yok)."""
    import karar_motoru as KM  # noqa: PLC0415
    b15 = KM.parse_klines(m15)
    b4 = KM.parse_klines(h4)
    sw15, sw4 = KM.find_swings(b15), KM.find_swings(b4)
    son = b15[-1].c

    def _atr(bars, n=14):
        """ATR — WILDER yumuşatması (smc_tespit.py ile AYNI tanım).

        Eskiden son n TR'nin BASİT ortalamasıydı. Aynı barlar için smc_tespit'in
        Wilder ATR'sinden FARKLI bir sayı üretiyordu; oysa `usd_hedef` ve
        `rr_denetim` kapılarının eşikleri ([0.8, 2.0] kurulum bandı ve 3.0
        şişirilmiş-R sınırı) Wilder ölçeğine göre kalibre edilmiştir — yani kapı
        yanlış ölçekte değerlendiriliyordu. `usd_hedef`in kendi girdi beyanı da
        zaten "smc_tespit_h4.atr (4H — kurulum ölçeği)" diyor.
        Ölçülen fark (2026-08-08, ETH 4H, engine/girdi/eth/h4.json):
          basit ortalama 20.8914  →  33.3333 puanlık sabit stop = 1.60×ATR
          Wilder         22.1913  →  aynı stop                  = 1.50×ATR
        Bu veride ikisi de banttan geçiyor; fark bandın KENARINDA taraf
        değiştirir. İki motorun aynı barlar için tek sayı üretmesi şart.
        """
        if len(bars) < 2:
            return None
        tr = []
        for i in range(1, len(bars)):
            h, l, pc = bars[i].h, bars[i].l, bars[i - 1].c
            tr.append(max(h - l, abs(h - pc), abs(l - pc)))
        if len(tr) < n:                   # periyot dolmadı → basit ortalama
            return sum(tr) / len(tr)
        atr = sum(tr[:n]) / n             # Wilder tohumu: ilk n TR'nin ortalaması
        for x in tr[n:]:                  # sonra yinelemeli yumuşatma
            atr = (atr * (n - 1) + x) / n
        return atr

    return {
        "son_kapanis": son, "atr15": _atr(b15), "atr4h": _atr(b4),
        "direnc15": sorted({s[1] for s in sw15 if s[2] == "H" and s[1] > son}),
        "destek15": sorted({s[1] for s in sw15 if s[2] == "L" and s[1] < son},
                           reverse=True),
        "direnc4h": sorted({s[1] for s in sw4 if s[2] == "H" and s[1] > son}),
        "destek4h": sorted({s[1] for s in sw4 if s[2] == "L" and s[1] < son},
                           reverse=True),
        "fvg": [(f["alt"], f["ust"]) for f in KM.open_fvgs(b15)],
        "bar15": len(b15), "bar4h": len(b4),
    }


def _giris_adaylari(yapi: dict, yon: str, fiyat: float) -> list:
    """Ölçülen yapıdan giriş adayları (yakından uzağa)."""
    ad = []
    if yon == "LONG":
        for alt, ust in yapi["fvg"]:
            if ust <= fiyat:                       # altta kalan FVG = pusu
                ad.append((ust, f"15M FVG üst kenarı {alt}-{ust}"))
        for s in yapi["destek15"][:4]:
            ad.append((s, "15M teyitli swing desteği"))
        for s in yapi["destek4h"][:3]:
            ad.append((s, "4H teyitli swing desteği"))
    else:
        for alt, ust in yapi["fvg"]:
            if alt >= fiyat:
                ad.append((alt, f"15M FVG alt kenarı {alt}-{ust}"))
        for s in yapi["direnc15"][:4]:
            ad.append((s, "15M teyitli swing direnci"))
        for s in yapi["direnc4h"][:3]:
            ad.append((s, "4H teyitli swing direnci"))
    # fiyatın kendisi de adaydır (MARKET olasılığı)
    ad.append((fiyat, "güncel fiyat (MARKET adayı)"))
    nd = _nd(fiyat)
    gorulen, temiz = set(), []
    for g, gerekce in ad:
        k = round(float(g), nd)
        if k in gorulen:
            continue
        gorulen.add(k)
        temiz.append((k, gerekce))
    return sorted(temiz, key=lambda x: abs(x[0] - fiyat))


def _hedef(yapi: dict, yon: str, giris: float, risk: float, p: dict,
           profil: dict | None = None):
    """Hedef seviyesi.

    · Sabit-USDT profili VARSA hedef mesafesi PROFİLDEN gelir (usdt/kontrat).
      "İlk likidite" kuralı burada geçersizdir: kullanıcı kazanç bandını
      sabitlemiştir; yapının o banda düşüp düşmediğini `usd_hedef` sınar.
    · Profil YOKSA hedef, yön tarafındaki İLK teyitli likiditedir. Yoksa aday
      düşer — "R katı" uydurma hedef üretilmez.
    """
    if profil:
        kontrat = _f(profil.get("kontrat"))
        band = profil.get("hedef_usdt") or []
        hedef_usdt = _f(band[0]) if band else None
        if kontrat and hedef_usdt:
            mesafe = hedef_usdt / kontrat
            h = giris + mesafe if yon == "LONG" else giris - mesafe
            return h, (f"sabit-USDT profili: {hedef_usdt} USDT / {kontrat} "
                       f"kontrat = {round(mesafe, 4)} puan")
        return None, f"{YOK} — profilde hedef bandı/kontrat eksik"
    asgari = p["asgari_mesafe_atr"] * (yapi.get("atr15") or 0.0)
    havuz = (sorted(set(yapi["direnc15"] + yapi["direnc4h"]))
             if yon == "LONG" else
             sorted(set(yapi["destek15"] + yapi["destek4h"]), reverse=True))
    for lv in havuz:
        if yon == "LONG" and lv > giris + max(asgari, risk * 0.5):
            return lv, "yön tarafındaki ilk teyitli likidite"
        if yon == "SHORT" and lv < giris - max(asgari, risk * 0.5):
            return lv, "yön tarafındaki ilk teyitli likidite"
    return None, f"{YOK} — yön tarafında teyitli likidite hedefi yok"


def _stop(yapi: dict, yon: str, giris: float, profil: dict | None):
    """Stop: profil varsa sabit mesafe; yoksa yapının ötesindeki ilk swing."""
    if profil:
        kontrat = _f(profil.get("kontrat"))
        stop_usdt = abs(_f(profil.get("stop_usdt")) or 0.0)
        if kontrat and stop_usdt:
            mesafe = stop_usdt / kontrat
            return ((giris - mesafe) if yon == "LONG" else (giris + mesafe),
                    f"sabit-USDT profili: {stop_usdt} USDT / {kontrat} kontrat "
                    f"= {round(mesafe, 4)} puan")
    havuz = (yapi["destek15"] + yapi["destek4h"] if yon == "LONG"
             else yapi["direnc15"] + yapi["direnc4h"])
    if yon == "LONG":
        alt = [s for s in havuz if s < giris]
        if alt:
            return max(alt), "girişin altındaki EN YAKIN teyitli swing (yapı stopu)"
    else:
        ust = [s for s in havuz if s > giris]
        if ust:
            return min(ust), "girişin üstündeki EN YAKIN teyitli swing (yapı stopu)"
    return None, f"{YOK} — yapı stopu bulunamadı"


def plan(job: dict) -> dict:
    p = {**KONVANSIYON, **(job.get("konvansiyon") or {})}
    yon = str(job.get("yon", "")).strip().upper()
    profil = job.get("profil") or None
    # `esikler: null` (ya da dict olmayan değer) motoru düşürmesin (fail-open
    # değil: r_min yine depo kuralına düşer)
    esikler = (profil or {}).get("esikler")
    esikler = esikler if isinstance(esikler, dict) else {}
    r_min = _f(esikler.get("r_min")) or _f(job.get("r_min")) or p["r_min"]

    if yon not in ("LONG", "SHORT"):
        return {"EMIR": "EMİR YOK", "gerekce": f"yön {yon or YOK} — yönsüz kurulumda "
                "giriş/stop tanımsız (fail-closed)", "adaylar": []}
    try:
        yapi = yapi_oku(job["m15"], job["h4"])
    except Exception as e:  # noqa: BLE001
        return {"EMIR": "EMİR YOK",
                "gerekce": f"yapı okunamadı ({type(e).__name__}: {e})", "adaylar": []}

    fiyat = _f(job.get("fiyat")) or yapi["son_kapanis"]
    # Kurulum ölçeği ATR'si: profil varsa 4H (duran kural), yoksa 15M.
    atr_olcek = (yapi["atr4h"] if profil else yapi["atr15"]) or yapi["atr15"]
    adaylar, redler = [], []

    for giris, gerekce in _giris_adaylari(yapi, yon, fiyat)[:p["azami_aday"] * 3]:
        stop, s_gerekce = _stop(yapi, yon, giris, profil)
        if stop is None:
            redler.append(f"giriş {giris}: {s_gerekce}")
            continue
        risk = abs(giris - stop)
        if risk <= 0:
            redler.append(f"giriş {giris}: risk 0 (giriş=stop)")
            continue
        hedef, h_gerekce = _hedef(yapi, yon, giris, risk, p, profil)
        if hedef is None:
            redler.append(f"giriş {giris}: {h_gerekce}")
            continue
        # --- bağımsız R denetimi (ATR ölçeği) ---
        rr = _kos(RR, {"yon": yon.lower(), "entry": giris, "stop": stop,
                       "target": hedef, "atr": atr_olcek})
        rv = rr.get("verdict", YOK)
        if rr.get("_hata"):
            # rr_denetim'in gerçek hatası yutulmasın: "R None < r_min" yerine
            # düşen kapının asıl nedeni yazılır (ör. "atr > 0 olmalı").
            redler.append(f"giriş {giris}: rr_denetim ÇALIŞMADI "
                          f"({str(rr['_hata'])[:80]}) — reddedildi")
            continue
        R = _f(rr.get("R_gercekci"))
        if R is None:
            R = _f(rr.get("R_rapor"))   # eski "R_ham" anahtarı hiç basılmıyordu
        if rv == "ŞİŞİRİLMİŞ":
            redler.append(f"giriş {giris}: rr_denetim ŞİŞİRİLMİŞ (R {R}) — reddedildi")
            continue
        if rv == "GEÇERSİZ":
            redler.append(f"giriş {giris}: geometri GEÇERSİZ — reddedildi")
            continue
        if R is None or R < r_min:
            redler.append(f"giriş {giris}: R {R} < r_min {r_min} — reddedildi")
            continue
        nd = _nd(fiyat)
        if round(giris, nd) == round(stop, nd):
            redler.append(f"giriş {giris}: yuvarlanınca stop ile çakışıyor "
                          f"(hane {nd}) — reddedildi")
            continue
        aday = {
            "emir_tipi": ("MARKET" if abs(giris - fiyat) <=
                          p["market_tolerans_atr"] * (yapi["atr15"] or 0) else "LIMIT"),
            "yon": yon, "giris": round(giris, nd), "stop": round(stop, nd),
            "hedef": round(hedef, nd), "R": R, "rr_denetim": rv,
            "risk_puan": round(risk, nd),
            "giris_gerekcesi": gerekce, "stop_gerekcesi": s_gerekce,
            "hedef_gerekcesi": h_gerekce,
            "gecersizlik": (f"{round(stop, nd)} ötesinde 15M gövde kapanışı → "
                            "kurulum iptal"),
        }
        # STOP-AV RİSKİ (ölçülü tuzak merceği): stop, bariz likidite havuzunun
        # ≤ 0.25×ATR15 dibinde/tepesindeyse süpürülme olasılığı yüksektir —
        # emir REDDEDİLMEZ, bayrak görünür basılır (anlatı değil, mesafe ölçümü).
        havuzlar = (yapi["destek15"] + yapi["destek4h"] if yon == "LONG"
                    else yapi["direnc15"] + yapi["direnc4h"])
        atr15 = yapi["atr15"] or 0
        if havuzlar and atr15:
            yakin = min(havuzlar, key=lambda s: abs(stop - s))
            if abs(stop - yakin) <= 0.25 * atr15:
                aday["tuzak_uyarisi"] = (
                    f"STOP-AV RİSKİ: stop {round(stop, nd)}, likidite "
                    f"{round(yakin, nd)} havuzunun ≤0.25×ATR15 yakınında — "
                    "süpürülme (stop avı) olasılığı yüksek")
        # --- sabit-USDT profili varsa 5 kapı ---
        if profil:
            uj = {**profil, "yon": yon.lower(), "fiyat": fiyat,
                  "atr_kurulum": yapi["atr4h"], "giris_adaylari": [giris],
                  "likidite_hedefleri": sorted(set(
                      yapi["direnc15"] + yapi["direnc4h"] if yon == "LONG"
                      else yapi["destek15"] + yapi["destek4h"])),
                  "karsi_yapi_seviyeleri": sorted(set(
                      yapi["destek15"] + yapi["destek4h"] if yon == "LONG"
                      else yapi["direnc15"] + yapi["direnc4h"]))}
            uj["stop_usdt"] = abs(_f(profil.get("stop_usdt")) or 0.0)
            u = _kos(USD, uj)
            aday["usd_hedef"] = {"HUKUM": u.get("HUKUM", YOK),
                                 "dusen_kapilar": u.get("dusen_kapilar"),
                                 "kazanc_usdt": (u.get("cevrim") or {}).get(
                                     "net_kazanc_band_usdt")}
            if u.get("HUKUM") != "UYGUN":
                redler.append(f"giriş {giris}: usd_hedef {u.get('HUKUM', YOK)} "
                              f"— düşen kapı {u.get('dusen_kapilar')}")
                continue
        adaylar.append(aday)
        if len(adaylar) >= p["azami_aday"]:
            break

    if not adaylar:
        return {"EMIR": "EMİR YOK", "yon": yon, "fiyat": fiyat,
                "gerekce": "hiçbir aday kapıları geçemedi",
                "red_nedenleri": redler[:12], "adaylar": [],
                "yapi_ozeti": {k: yapi[k] for k in
                               ("son_kapanis", "atr15", "atr4h", "bar15", "bar4h")},
                "varsayimlar": _varsayimlar(p, r_min, bool(profil))}

    birincil = adaylar[0]
    return {
        "EMIR": (f"{birincil['emir_tipi']} {yon} @{birincil['giris']} | "
                 f"stop {birincil['stop']} | T1 {birincil['hedef']} | "
                 f"R {birincil['R']}"),
        "birincil": birincil, "adaylar": adaylar, "yon": yon, "fiyat": fiyat,
        "red_nedenleri": redler[:12],
        "yapi_ozeti": {k: yapi[k] for k in
                       ("son_kapanis", "atr15", "atr4h", "bar15", "bar4h")},
        "varsayimlar": _varsayimlar(p, r_min, bool(profil)),
    }


def _varsayimlar(p: dict, r_min: float, profil_var: bool) -> list:
    import karar_motoru as KM  # noqa: PLC0415
    return [
        f"R_min = {r_min} (depo risk kuralı); ŞİŞİRİLMİŞ aday rr_denetim ile elenir",
        f"MARKET eşiği: |giriş − fiyat| ≤ {p['market_tolerans_atr']}×ATR15 "
        "(fiyat bölgede değilse emir LIMIT'tir)",
        ("kurulum ölçeği ATR'si 4H (sabit-USDT profili var)" if profil_var
         else "kurulum ölçeği ATR'si 15M (sabit-USDT profili yok)"),
        "giriş adayları YALNIZ ölçülen yapıdan: açık 15M FVG kenarları + "
        "teyitli swingler; yuvarlak/uydurma seviye kullanılmaz",
        # "açık FVG"yi tanımlayan eşik burada BEYAN EDİLİR: aday havuzunu
        # doğrudan belirlediği için etiketsiz bırakılırsa gizli eşik olur.
        (f"'açık FVG' eşiği = karar_motoru.FVG_MITIGASYON {KM.FVG_MITIGASYON} "
         "(bölgenin bu oranı tükenince mitige sayılır; KALİBRE EDİLMEMİŞ "
         "tasarım varsayımı — consequent encroachment konvansiyonu). Bu değer "
         "open_fvgs üzerinden aday havuzunu doğrudan daraltır/genişletir. "
         "NOT: bu modülde giriş adayı bölgenin KENARIDIR (alt/üst), orta "
         "noktası değil — 'giriş=ce' hizalaması karar_motoru.decide için "
         "geçerlidir, buradaki adaylar için değil"),
        "hedef yön tarafındaki İLK teyitli likidite; yoksa aday düşer "
        "(R-katı uydurma hedef üretilmez)",
    ]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kararı MARKET/LIMIT emrine çevir")
    ap.add_argument("--job", required=True)
    a = ap.parse_args(argv)
    job = json.loads(Path(a.job).read_text(encoding="utf-8"))
    print(json.dumps(plan(job), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
