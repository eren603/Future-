"""Canli yon + giris/cikis sinyali — KONSEY kanit sozlesmesiyle.

Akis (KONSEY_Evidence_Engine.md "Onerilen uretim akisi"):
  1) gorev JSON olarak kurulur          -> EvidenceRegistry
  2) kaynak adaptorleri Source/Evidence -> market.bar_kaynagi_ekle
  3) model YALNIZ bu kayitlarla uretir  -> yon_turet + emir_uret (adapter)
  4) Python her kritik iddiayi denetler -> registry.audit()
  5) basarisiz sonuc REPAIR/LIMITED/HALT
  6) yalnizca basarili sonuc yayinlanir

Sert kural: hicbir seviye UYDURULMAZ. Giris/stop/hedef YALNIZCA deponun
olcen motoru `emir_plani.plan()` ciktisidir; yon ise olculen yapi
(`smc_tespit`) + turev skorundan agirlikli turetilir ve agirliklar BEYAN edilir.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .core import EvidenceRegistry

DEPO = Path("/home/user/Future-")
SKILLS = DEPO / ".claude/skills"
for _p in (SKILLS / "grafik-calisma/scripts", SKILLS / "piramit-sistem/scripts", DEPO / "engine"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# Yon agirliklari — BEYAN EDILIR, gizli esik yok.
AGIRLIK = {"h4_trend": 0.50, "m15_trend": 0.30, "turev": 0.20}
# 'range' rejiminde alt zaman dilimi trendi gurultudur -> agirligi yarilanir
RANGE_KIRPMA = 0.5
# Canli sinyal icin azami veri yasi (dk). Asilirsa emir ONERILMEZ (fail-closed).
AZAMI_YAS_DK = 30.0


def _mumlar(barlar: list) -> list[dict]:
    out = []
    for x in barlar:
        if isinstance(x, dict):
            out.append({"o": float(x["o"]), "h": float(x["h"]),
                        "l": float(x["l"]), "c": float(x["c"])})
        else:
            out.append({"o": float(x[1]), "h": float(x[2]),
                        "l": float(x[3]), "c": float(x[4])})
    return out


def yapi_olc(reg: EvidenceRegistry, barlar: list, etiket: str,
             sid: str, eid: str) -> dict:
    """smc_tespit ile OLCUM — sonuc bir EVIDENCE olarak kayda gecer."""
    import smc_tespit as S  # noqa: PLC0415
    r = S.detect({"candles": _mumlar(barlar)})
    rej = r.get("rejim") or {}
    reg.add_evidence(eid, sid, "smc_tespit.detect (olculdu)",
                     f"{etiket} yapi olcumu",
                     f"trend={r.get('trend')} adx={rej.get('adx')} "
                     f"rejim={rej.get('durum')} atr={r.get('atr')} "
                     f"acik_fvg={len(r.get('acik_fvgler') or [])} "
                     f"likidite={len(r.get('likidite') or [])}")
    return {"trend": r.get("trend"), "rejim": rej.get("durum"),
            "adx": rej.get("adx"), "atr": r.get("atr"),
            "fvg": r.get("acik_fvgler") or [], "likidite": r.get("likidite") or [],
            "evidence_id": eid}


def turev_olc(reg: EvidenceRegistry, yol: Path, sid: str, eid: str) -> dict | None:
    """turev.json varsa yon skorunu okur; YOKSA None (uydurma yok)."""
    if not yol.exists():
        return None
    d = json.loads(yol.read_text(encoding="utf-8"))
    skor = d.get("yon_skoru")
    if skor is None:
        skor = ((d.get("skor") or {}).get("yon") if isinstance(d.get("skor"), dict) else None)
    kapsam = d.get("kapsam")
    reg.add_source(sid, str(yol), "yerel dosya", "LIMITED", "G3",
                   content=json.dumps(d)[:500], note="turev kanali (kanca uretti)")
    reg.add_evidence(eid, sid, "turev.json okumasi",
                     "turev yon skoru", f"yon_skoru={skor} kapsam={kapsam}")
    return {"skor": skor, "kapsam": kapsam, "evidence_id": eid}


def yon_turet(h4: dict, m15: dict, turev: dict | None) -> dict:
    """Agirlikli yon. Her bilesen kanit kimligiyle birlikte raporlanir."""
    def isaret(t: str | None) -> float:
        return {"bull": 1.0, "bear": -1.0}.get(str(t or "").lower(), 0.0)

    bilesen, toplam, agirlik_toplam = [], 0.0, 0.0

    s4 = isaret(h4["trend"]) * AGIRLIK["h4_trend"]
    toplam += s4; agirlik_toplam += AGIRLIK["h4_trend"]
    bilesen.append({"ad": "4H trend", "deger": h4["trend"], "agirlik": AGIRLIK["h4_trend"],
                    "katki": round(s4, 4), "evidence_id": h4["evidence_id"]})

    a15 = AGIRLIK["m15_trend"] * (RANGE_KIRPMA if m15["rejim"] == "range" else 1.0)
    s15 = isaret(m15["trend"]) * a15
    toplam += s15; agirlik_toplam += a15
    bilesen.append({"ad": "15M trend", "deger": m15["trend"], "agirlik": round(a15, 4),
                    "katki": round(s15, 4), "evidence_id": m15["evidence_id"],
                    "not": ("rejim=range -> agirlik %d%% kirpildi" % int(RANGE_KIRPMA * 100)
                            if m15["rejim"] == "range" else "")})

    if turev and isinstance(turev.get("skor"), (int, float)):
        st = max(-1.0, min(1.0, float(turev["skor"]))) * AGIRLIK["turev"]
        toplam += st; agirlik_toplam += AGIRLIK["turev"]
        bilesen.append({"ad": "turev skoru", "deger": turev["skor"],
                        "agirlik": AGIRLIK["turev"], "katki": round(st, 4),
                        "evidence_id": turev["evidence_id"]})
    else:
        bilesen.append({"ad": "turev skoru", "deger": "VERI YOK", "agirlik": 0.0,
                        "katki": 0.0, "evidence_id": None,
                        "not": "kanal yok -> agirliga GIRMEDI (uydurma yok)"})

    skor = toplam / agirlik_toplam if agirlik_toplam else 0.0
    yon = "LONG" if skor > 0 else ("SHORT" if skor < 0 else "NOTR")
    return {"yon": yon, "skor": round(skor, 4), "bilesenler": bilesen,
            "agirlik_toplam": round(agirlik_toplam, 4)}


def emir_uret(yon: str, m15_yol: str, h4_yol: str, fiyat: float | None,
              profil: dict | None = None) -> dict:
    """Seviyeler YALNIZ emir_plani.plan()'dan gelir (uydurma yok)."""
    import emir_plani as EP  # noqa: PLC0415
    job: dict[str, Any] = {"yon": yon, "m15": m15_yol, "h4": h4_yol}
    if fiyat is not None:
        job["fiyat"] = fiyat
    if profil:
        job["profil"] = profil
    return EP.plan(job)


def bilgi_seviyeleri(yon: str, m15_yol: str, h4_yol: str, fiyat: float,
                     profil: dict | None = None, azami: int = 6) -> list[dict]:
    """Emir kapisini GECEMEYEN adaylarin OLCULEN seviyeleri — bilgi olarak.

    Kullanici "giris yok diyorsa limit fiyattaki yeri ve yonu" istedi. Aday
    duserse seviye YOK OLMAZ: burada motorun KENDI ic fonksiyonlariyla
    (emir_plani._giris_adaylari/_stop/_hedef + rr_denetim) yeniden okunur ve
    R_gercekci ile birlikte doner. Bunlar ISLEM ONERISI DEGILDIR - depo kapisi
    (R>=1.35 + sisirilmis-R) onlari zaten reddetmistir; yalniz YER ve YON bilgisi.
    Hicbir sayi uydurulmaz; hepsi motor ciktisidir.
    """
    import emir_plani as EP  # noqa: PLC0415
    yapi = EP.yapi_oku(m15_yol, h4_yol)
    p = {**EP.KONVANSIYON, **{}}
    atr15 = yapi["atr15"] or 0.0
    atr_olcek = (yapi["atr4h"] if profil else yapi["atr15"]) or atr15
    out = []
    for giris, gerekce in EP._giris_adaylari(yapi, yon, fiyat)[:azami * 3]:
        stop, s_ger = EP._stop(yapi, yon, giris, profil)
        if stop is None:
            out.append({"giris": giris, "gerekce": gerekce, "durum": "stop yok",
                        "not": s_ger})
            continue
        risk = abs(giris - stop)
        if risk <= 0:
            continue
        hedef, h_ger = EP._hedef(yapi, yon, giris, risk, p, profil)
        if hedef is None:
            out.append({"giris": giris, "stop": stop, "gerekce": gerekce,
                        "durum": "hedef yok", "not": h_ger})
            continue
        rr = EP._kos(EP.RR, {"yon": yon.lower(), "entry": giris, "stop": stop,
                             "target": hedef, "atr": atr_olcek})
        R_rap = rr.get("R_rapor")
        R_ger = rr.get("R_gercekci")
        tip = "MARKET" if abs(giris - fiyat) <= 0.1 * atr15 else "LIMIT"
        out.append({
            "tip": tip, "yon": yon, "giris": round(giris, 2), "stop": round(stop, 2),
            "hedef": round(hedef, 2),
            "R_rapor": R_rap, "R_gercekci": R_ger, "hukum": rr.get("verdict"),
            "mesafe": round(abs(giris - fiyat), 2),
            "gerekce": gerekce, "stop_gerekce": s_ger, "hedef_gerekce": h_ger,
            "gecti": (rr.get("verdict") not in ("ŞİŞİRİLMİŞ", "GEÇERSİZ")
                      and (R_ger or R_rap or 0) >= EP.KONVANSIYON["r_min"]),
        })
        if len(out) >= azami:
            break
    return out
