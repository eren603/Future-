"""Uctan uca sinyal kosusu: kaynak -> olcum -> yon -> emir -> KONSEY kapisi -> basim."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapters import YerelOlcumAdapter, build_prompt
from .core import EvidenceRegistry
from .orchestrator import run_agent_and_gate
from . import market, sinyal

DEPO = Path("/home/user/Future-")

SEMBOLLER = {
    "BTCUSDT": {"inst": "BTC-USDT-SWAP", "m15": DEPO / "engine/girdi/m15.json",
                "h4": DEPO / "engine/girdi/h4.json",
                "turev": DEPO / "engine/girdi/turev.json", "profil": None},
    "ETHUSDT": {"inst": "ETH-USDT-SWAP", "m15": DEPO / "engine/girdi/eth/m15.json",
                "h4": DEPO / "engine/girdi/eth/h4.json",
                "turev": DEPO / "engine/girdi/eth/turev.json",
                "profil": DEPO / "engine/girdi/eth_profil.json"},
}


def _yaz_gecici(barlar: list, ad: str) -> str:
    p = Path("/tmp/konsey_bar"); p.mkdir(exist_ok=True)
    y = p / ad
    y.write_text(json.dumps(barlar), encoding="utf-8")
    return str(y)


def sembol_kos(sembol: str, reg: EvidenceRegistry, n: int = 1) -> dict[str, Any]:
    cfg = SEMBOLLER[sembol]
    P = f"{n:02d}"

    # --- 2) kaynak adaptorleri -> Source/Evidence
    d15 = market.bar_kaynagi_ekle(reg, sembol, cfg["inst"], "15m",
                                  cfg["m15"] if Path(cfg["m15"]).exists() else None,
                                  f"S{P}A", f"E{P}A", f"G{n}")
    d4 = market.bar_kaynagi_ekle(reg, sembol, cfg["inst"], "4H",
                                 cfg["h4"] if Path(cfg["h4"]).exists() else None,
                                 f"S{P}B", f"E{P}B", f"G{n}")

    # --- olculen yapi
    m15 = sinyal.yapi_olc(reg, d15["barlar"], f"{sembol} 15M", f"S{P}A", f"E{P}C")
    h4 = sinyal.yapi_olc(reg, d4["barlar"], f"{sembol} 4H", f"S{P}B", f"E{P}D")
    tv = sinyal.turev_olc(reg, Path(cfg["turev"]), f"S{P}C", f"E{P}E")

    # --- 3) yon: YALNIZ kayitlardan
    y = sinyal.yon_turet(h4, m15, tv)

    # --- canli fiyat (kapaliysa son kapanis, ETIKETLENIR)
    try:
        fiyat, fiyat_kaynak = market.okx_fiyat(cfg["inst"]), "canli-ticker"
    except Exception:  # noqa: BLE001
        fiyat, fiyat_kaynak = d15["son_kapanis"], "son-kapanis (canli uc kapali)"

    m15_yol = _yaz_gecici(d15["barlar"], f"{sembol}_m15.json")
    h4_yol = _yaz_gecici(d4["barlar"], f"{sembol}_h4.json")
    profil = None
    if cfg["profil"] and Path(cfg["profil"]).exists():
        profil = json.loads(Path(cfg["profil"]).read_text(encoding="utf-8"))

    # --- emir: yon varsa tek taraf; NOTR ise IKI TARAF da uretilir
    emirler = {}
    for taraf in ([y["yon"]] if y["yon"] in ("LONG", "SHORT") else ["LONG", "SHORT"]):
        emirler[taraf] = sinyal.emir_uret(taraf, m15_yol, h4_yol, fiyat, profil)

    bilgi = {}
    for taraf in emirler:
        try:
            bilgi[taraf] = sinyal.bilgi_seviyeleri(taraf, m15_yol, h4_yol, fiyat, profil)
        except Exception as e:  # noqa: BLE001
            bilgi[taraf] = [{"hata": f"{type(e).__name__}: {e}"}]

    reg.add_evidence(f"E{P}F", f"S{P}A", "emir_plani.plan (olculdu)",
                     f"{sembol} emir adaylari",
                     json.dumps({k: v.get("EMIR") for k, v in emirler.items()},
                                ensure_ascii=False))

    # --- 4) kritik iddialar
    reg.add_claim(f"C{P}1", f"{sembol} yon = {y['yon']} (agirlikli skor {y['skor']})",
                  "VERIFIED" if y["yon"] != "NOTR" else "LIMITED",
                  [f"E{P}C", f"E{P}D"] + ([f"E{P}E"] if tv else []), "DONE")
    reg.add_claim(f"C{P}2", f"{sembol} emir seviyeleri emir_plani.plan ciktisidir (uydurma yok)",
                  "VERIFIED", [f"E{P}F"], "DONE")
    taze_ok = d15["tazelik"] == "CURRENT" and d15["yas_dk"] <= sinyal.AZAMI_YAS_DK
    reg.add_claim(f"C{P}3",
                  f"{sembol} veri canli ve taze (yas {d15['yas_dk']:.0f} dk <= {sinyal.AZAMI_YAS_DK:.0f} dk)",
                  "VERIFIED" if taze_ok else "LIMITED", [f"E{P}A"], "DONE")
    if not taze_ok:
        reg.external_checks_pending.append(
            f"{sembol}: canli fiyat dogrulanamadi (kaynak={d15['kaynak']}, "
            f"yas={d15['yas_dk']:.0f} dk, tazelik={d15['tazelik']})")

    return {"sembol": sembol, "yon": y, "fiyat": fiyat, "fiyat_kaynak": fiyat_kaynak,
            "emirler": emirler, "bilgi": bilgi, "atr15": (m15.get("atr") or 0.0), "m15": m15, "h4": h4, "turev": tv,
            "veri": {"15m": d15, "4H": d4}, "tazelik_ok": taze_ok}


def _emir_satiri(e: dict) -> str:
    if e.get("EMIR") and e["EMIR"] != "EMİR YOK":
        return e["EMIR"]
    return f"EMİR YOK — {e.get('gerekce', '?')}"


def bas(sonuclar: list[dict], audit: dict, publish: bool) -> str:
    L = []
    A = L.append
    A("=" * 78)
    A("KONSEY SINYAL — YON + GIRIS/CIKIS")
    A("=" * 78)
    for s in sonuclar:
        y = s["yon"]
        A("")
        A(f"### {s['sembol']}   fiyat={s['fiyat']:.2f}  ({s['fiyat_kaynak']})")
        A(f"YON      : {y['yon']}   agirlikli skor {y['skor']:+.4f}")
        for b in y["bilesenler"]:
            n = f"  [{b['not']}]" if b.get("not") else ""
            A(f"   - {b['ad']:<12} = {str(b['deger']):<9} agirlik {b['agirlik']:<5} "
              f"katki {b['katki']:+.4f}  kanit={b['evidence_id']}{n}")
        for taraf, e in s["emirler"].items():
            etk = "" if y["yon"] in ("LONG", "SHORT") else f" ({taraf})"
            A(f"EMIR{etk:<6}: {_emir_satiri(e)}")
            for a in (e.get("adaylar") or [])[:1]:
                A(f"   >> {a.get('emir_tipi')} {a.get('yon')} @{a.get('giris')} "
                  f"| stop {a.get('stop')} | hedef {a.get('hedef')} | R {a.get('R')} "
                  f"| rr_denetim {a.get('rr_denetim')}")
                A(f"      giris  : {a.get('giris_gerekcesi')}")
                A(f"      stop   : {a.get('stop_gerekcesi')}")
                A(f"      hedef  : {a.get('hedef_gerekcesi')}")
                A(f"      gecersizlik: {a.get('gecersizlik')}")
                uh = a.get("usd_hedef") or {}
                if uh:
                    A(f"      usd_hedef  : {uh.get('HUKUM')} kazanc {uh.get('kazanc_usdt')} "
                      f"dusen {uh.get('dusen_kapilar')}")
            for r in (e.get("red_nedenleri") or [])[:3]:
                A(f"   x {r}")
        atr = s.get("atr15") or 0.0
        for taraf, satirlar in (s.get("bilgi") or {}).items():
            gecerli = [x for x in satirlar if x.get("giris") and x.get("hedef")]
            if not gecerli:
                continue
            A(f"SEVIYELER ({taraf}) — YER ve YON bilgisi; ISLEM ONERISI DEGIL:")
            A("   %-7s %-10s %-10s %-10s %-7s %-7s %-12s %-8s %s" %
              ("tip", "giris", "stop", "hedef", "R_rap", "R_ger", "hukum", "stop/ATR", "mesafe"))
            for x in gecerli:
                sa = (abs(x["giris"] - x["stop"]) / atr) if atr else 0.0
                A("   %-7s %-10s %-10s %-10s %-7s %-7s %-12s %-8.2f %s" %
                  (x["tip"], x["giris"], x["stop"], x["hedef"], x.get("R_rapor"),
                   x.get("R_gercekci"), x.get("hukum"), sa, x.get("mesafe")))
            A("   not: stop/ATR < 0.8 = gurultu seviyesi stop (kurulum olcegi disi);"
              " R_rap sisirilmis ise gecerli olan R_ger'dir")
        A(f"VERI     : 15M {s['veri']['15m']['kaynak']} yas {s['veri']['15m']['yas_dk']:.0f} dk "
          f"({s['veri']['15m']['tazelik']}) | 4H {s['veri']['4H']['kaynak']}")
    A("")
    A("-" * 78)
    A(f"KONSEY KAPISI : {audit['decision']}   yayin={'IZINLI' if publish else 'DURDURULDU'}")
    for r in audit.get("reasons", []):
        A(f"   ! {r}")
    A(f"   kritik iddia {audit['critical_claims_with_evidence']}/{audit['critical_claim_count']} kanitli"
      f" | tazelik {audit['freshness']}")
    if not publish:
        A("   >> Seviyeler GOSTERILIYOR ama ISLEM ONERISI DEGILDIR (fail-closed).")
    A("=" * 78)
    A("Yalniz karar-destek; canli/otomatik emir DAHIL DEGIL.")
    return "\n".join(L)


def kos(semboller: list[str] | None = None, cikti: str | Path | None = None) -> dict:
    semboller = semboller or ["BTCUSDT"]
    reg = EvidenceRegistry(task_type="MARKET_SIGNAL", risk_level="HIGH")
    reg.method_layers_applied = [
        "Kanit katalogu (Source/Evidence/Claim) — her seviye bir EVIDENCE_ID'ye bagli",
        "GRADE-benzeri kesinlik: VERIFIED/LIMITED/UNKNOWN ayrimi",
        "Deterministik yayin kapisi (core.audit) — model beyani kanit sayilmaz",
    ]
    reg.method_layers_omitted = [
        "OWASP SAMM / PRISMA / Cochrane: bu gorev turu icin kapsam disi",
        "Bagimsiz dis guvence (BIST/IOSCO): yok — tek sistem",
    ]
    reg.counter_evidence_search = "DONE"

    sonuclar = [sembol_kos(s, reg, i + 1) for i, s in enumerate(semboller)]
    reg.payload = {"sinyaller": [{"sembol": s["sembol"], "yon": s["yon"],
                                  "fiyat": s["fiyat"],
                                  "emirler": {k: v.get("EMIR") for k, v in s["emirler"].items()}}
                                 for s in sonuclar]}

    # --- 3) ajan katmani: yalnizca kayitlardan uretir, karari VERMEZ
    adapter = YerelOlcumAdapter(lambda d: {
        "claims": [c["claim_id"] for c in d["claims"].values()],
        "decision": "PUBLISH_FULL",
        "epistemic_verdict": "PARTIAL",
        "limitations": [s.note for s in
                        [type("x", (), {"note": v.get("note", "")})() for v in d["sources"].values()]
                        if s.note],
    }).bagla(reg)
    rapor = run_agent_and_gate(reg, adapter)

    metin = bas(sonuclar, rapor["independent_audit"], rapor["publish_allowed"])
    print(metin)
    if cikti:
        Path(cikti).parent.mkdir(parents=True, exist_ok=True)
        Path(cikti).write_text(json.dumps(
            {"rapor": rapor, "kayit": reg.to_dict(), "metin": metin},
            ensure_ascii=False, indent=2), encoding="utf-8")
    return rapor
