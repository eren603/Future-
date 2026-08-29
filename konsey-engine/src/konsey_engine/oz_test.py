"""Oz-test: kapinin GERCEKTEN calistigini kanitlar (her zaman REPAIR demiyor)."""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

from .core import EvidenceRegistry
from . import market, sinyal


def _taze_barlar(n: int, aralik_ms: int, p0: float = 65000.0,
                 egim: float = 0.0, tohum: int = 7) -> list[list]:
    """Deterministik sentetik bar (Date/random YOK - tohumlu LCG)."""
    simdi = int(time.time() * 1000)
    bas = simdi - (n - 1) * aralik_ms
    s, out, p = tohum, [], p0
    for i in range(n):
        s = (1103515245 * s + 12345) % (2 ** 31)
        d = ((s / 2 ** 31) - 0.5) * p0 * 0.004 + egim
        o = p; p = max(1.0, p + d)
        h = max(o, p) * 1.0009; l = min(o, p) * 0.9991
        out.append([bas + i * aralik_ms, f"{o:.2f}", f"{h:.2f}", f"{l:.2f}",
                    f"{p:.2f}", "1000", bas + i * aralik_ms + 1, "0", 0, None, "0", "0"])
    return out


def kos() -> list[tuple[str, str, str]]:
    R: list[tuple[str, str, str]] = []

    def kayit(ad, ok, detay=""):
        R.append((ad, "PASS" if ok else "FAIL", detay))

    # T1 - bos kayit yayinlanamaz
    a = EvidenceRegistry().audit("PUBLISH_FULL")
    kayit("T1 bos kayit -> REPAIR", a.decision == "REPAIR", a.decision)

    # T2 - kanitsiz VERIFIED kritik iddia kapiyi kapatir
    r = EvidenceRegistry()
    r.add_source("S1", "yerel", "dosya", "CURRENT", content="x")
    r.add_claim("C1", "kanitsiz", "VERIFIED", [], "DONE")
    a = r.audit("PUBLISH_FULL")
    kayit("T2 kanitsiz VERIFIED -> REPAIR",
          a.decision == "REPAIR" and "C1" in a.missing_evidence_claims, a.decision)

    # T3 - cozulemeyen kanit referansi yakalanir
    r = EvidenceRegistry()
    r.add_source("S1", "yerel", "dosya", "CURRENT", content="x")
    r.add_claim("C1", "hayalet kanit", "VERIFIED", ["E_YOK"], "DONE")
    a = r.audit("PUBLISH_FULL")
    kayit("T3 cozulemeyen kanit -> invalid", bool(a.invalid_references), str(a.invalid_references))

    # T4 - TAM kayit PUBLISH_FULL verir (kapi her zaman REPAIR DEMIYOR)
    r = EvidenceRegistry(risk_level="HIGH")
    r.add_source("S1", "yerel", "dosya", "CURRENT", content="x")
    r.add_evidence("E1", "S1", "olcum", "d", "gozlem")
    r.add_claim("C1", "kanitli", "VERIFIED", ["E1"], "DONE")
    a = r.audit("PUBLISH_FULL")
    kayit("T4 tam kayit -> PUBLISH_FULL", a.decision == "PUBLISH_FULL", a.decision)

    # T5 - karsit kanit bekliyorsa HIGH riskte PUBLISH_LIMITED
    r = EvidenceRegistry(risk_level="HIGH")
    r.add_source("S1", "yerel", "dosya", "CURRENT", content="x")
    r.add_evidence("E1", "S1", "olcum", "d", "g")
    r.add_claim("C1", "karsit kanit yok", "VERIFIED", ["E1"], "NOT_RUN")
    a = r.audit("PUBLISH_FULL")
    kayit("T5 karsit kanit bekliyor -> PUBLISH_LIMITED", a.decision == "PUBLISH_LIMITED", a.decision)

    # T6 - erisilemeyen kaynak KAYDEDILMEZ
    r = EvidenceRegistry()
    try:
        r.fetch("https://kesinlikle-yok-12345.invalid", "S9", "E9")
        ok = False
    except Exception:  # noqa: BLE001
        ok = ("S9" not in r.sources) and ("E9" not in r.evidence)
    kayit("T6 erisilemeyen kaynak kaydedilmez", ok, f"kaynak={len(r.sources)}")

    # T7 - tazelik OLCULUR: taze bar CURRENT, eski bar STALE
    taze = _taze_barlar(60, 900_000)
    eski = [[x[0] - 40 * 86400_000] + x[1:] for x in taze]
    t1, y1 = market.tazelik(taze, "15m")
    t2, y2 = market.tazelik(eski, "15m")
    kayit("T7 tazelik olculur", t1 == "CURRENT" and t2 == "STALE",
          f"taze={t1}({y1:.0f}dk) eski={t2}({y2/1440:.0f}gun)")

    # T8 - TAZE veriyle uctan uca kosu PUBLISH_FULL + exit 0 verir
    kok = Path("/tmp/konsey_oztest"); kok.mkdir(exist_ok=True)
    m15 = kok / "m15.json"; h4 = kok / "h4.json"
    m15.write_text(json.dumps(_taze_barlar(200, 900_000, egim=12.0)), encoding="utf-8")
    h4.write_text(json.dumps(_taze_barlar(200, 14_400_000, egim=90.0)), encoding="utf-8")
    reg = EvidenceRegistry(risk_level="HIGH")
    reg.counter_evidence_search = "DONE"
    d15 = market.bar_kaynagi_ekle(reg, "TEST", "YOK-SWAP", "15m", m15, "S01A", "E01A", "G1")
    d4 = market.bar_kaynagi_ekle(reg, "TEST", "YOK-SWAP", "4H", h4, "S01B", "E01B", "G1")
    mm = sinyal.yapi_olc(reg, d15["barlar"], "TEST 15M", "S01A", "E01C")
    hh = sinyal.yapi_olc(reg, d4["barlar"], "TEST 4H", "S01B", "E01D")
    y = sinyal.yon_turet(hh, mm, None)
    reg.add_claim("C11", f"yon={y['yon']}", "VERIFIED", ["E01C", "E01D"], "DONE")
    reg.add_claim("C12", "veri taze", "VERIFIED", ["E01A"], "DONE")
    a = reg.audit("PUBLISH_FULL")
    kayit("T8 TAZE veri -> PUBLISH_FULL (kapi acilabiliyor)",
          a.decision == "PUBLISH_FULL" and d15["tazelik"] == "CURRENT",
          f"{a.decision} tazelik={d15['tazelik']} yon={y['yon']}")

    # T9 - BAYAT veri kapiyi kapatir (fail-closed)
    reg2 = EvidenceRegistry(risk_level="HIGH"); reg2.counter_evidence_search = "DONE"
    bayat = kok / "bayat.json"
    bayat.write_text(json.dumps([[x[0] - 40 * 86400_000] + x[1:]
                                 for x in json.loads(m15.read_text())]), encoding="utf-8")
    db = market.bar_kaynagi_ekle(reg2, "TEST", "YOK-SWAP", "15m", bayat, "S02A", "E02A", "G2")
    reg2.add_evidence("E02X", "S02A", "olcum", "d", "g")
    reg2.add_claim("C21", "bayat", "VERIFIED", ["E02X"], "DONE")
    if db["tazelik"] != "CURRENT":
        reg2.external_checks_pending.append("canli fiyat dogrulanamadi")
    a2 = reg2.audit("PUBLISH_FULL")
    kayit("T9 BAYAT veri -> yayin DURUR", a2.decision != "PUBLISH_FULL",
          f"{a2.decision} tazelik={db['tazelik']}")

    # T10 - yon agirliklari toplami ve isaret dogrulugu
    hb = {"trend": "bear", "rejim": "trend", "evidence_id": "X1"}
    mb = {"trend": "bear", "rejim": "trend", "evidence_id": "X2"}
    yb = sinyal.yon_turet(hb, mb, None)
    hl = {"trend": "bull", "rejim": "trend", "evidence_id": "X1"}
    yl = sinyal.yon_turet(hl, mb, None)
    kayit("T10 yon isareti dogru", yb["yon"] == "SHORT" and yb["skor"] == -1.0
          and yl["yon"] == "LONG", f"bear={yb['skor']} karisik={yl['skor']}")

    # T11 - turev kanali yoksa AGIRLIGA GIRMEZ (uydurma yok)
    kayit("T11 eksik kanal agirliga girmez",
          abs(yb["agirlik_toplam"] - (sinyal.AGIRLIK["h4_trend"] + sinyal.AGIRLIK["m15_trend"])) < 1e-9,
          f"agirlik_toplam={yb['agirlik_toplam']}")

    # T12 - seviyeler motordan gelir: bilgi_seviyeleri hicbir sayi uretmez
    import emir_plani as EP  # noqa: PLC0415
    yapi = EP.yapi_oku(str(m15), str(h4))
    lv = sinyal.bilgi_seviyeleri("LONG", str(m15), str(h4), yapi["son_kapanis"])
    motor_adaylari = {round(g, 2) for g, _ in EP._giris_adaylari(yapi, "LONG", yapi["son_kapanis"])}
    disarida = [x["giris"] for x in lv if "giris" in x and round(x["giris"], 2) not in motor_adaylari]
    kayit("T12 seviyeler YALNIZ motordan", not disarida, f"motor disi={disarida}")

    # T13 - MARKET/LIMIT siniflandirmasi 0.1xATR15 kuralina uyar
    atr15 = yapi["atr15"] or 0.0
    hatali = [x for x in lv if "tip" in x
              and x["tip"] != ("MARKET" if x["mesafe"] <= 0.1 * atr15 else "LIMIT")]
    kayit("T13 MARKET/LIMIT kurali", not hatali, f"esik={0.1*atr15:.2f} hatali={len(hatali)}")

    # T14 - kullanicinin adapters/orchestrator sozlesmesi korunuyor
    from .adapters import AgentAdapter, OpenAICompatibleAdapter, GenericJSONAdapter, build_prompt
    from .orchestrator import run_agent_and_gate, DEFAULT_SCHEMA
    kayit("T14 sozlesme korunuyor",
          OpenAICompatibleAdapter.provider == "openai-compatible"
          and GenericJSONAdapter.provider == "generic-json"
          and DEFAULT_SCHEMA["required"] == ["claims", "decision", "epistemic_verdict", "limitations"]
          and hasattr(AgentAdapter, "complete"),
          "adapters+orchestrator birebir")

    # T15 - model karari kapiyi EZEMEZ
    from .adapters import YerelOlcumAdapter
    reg3 = EvidenceRegistry(risk_level="HIGH")
    ad = YerelOlcumAdapter(lambda d: {"claims": [], "decision": "PUBLISH_FULL",
                                      "epistemic_verdict": "KNOWN", "limitations": []}).bagla(reg3)
    rap = run_agent_and_gate(reg3, ad)
    kayit("T15 model karari kapiyi EZEMEZ",
          rap["model_output"]["decision"] == "PUBLISH_FULL" and not rap["publish_allowed"],
          f"model=PUBLISH_FULL ama kapi={rap['final_decision']}")

    return R


def main(argv=None) -> int:
    R = kos()
    for ad, d, det in R:
        print(f"[{d}] {ad}  {det}")
    hata = sum(1 for _, d, _ in R if d == "FAIL")
    print(f"\n{len(R) - hata}/{len(R)} PASS")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
