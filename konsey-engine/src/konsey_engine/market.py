"""Piyasa verisi kaynak adaptorleri -> RetrievedSource sozlesmesi.

KONSEY kurali: erisilemeyen kaynak ERISILMIS gibi kaydedilmez. Canli uc
kapaliysa istisna firlatilir; cagiran taraf yerel kaynaga DUSEBILIR ama bu
dusus kayda GECER ve tazelik damgasi buna gore hesaplanir.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from .core import EvidenceRegistry

OKX_MUM = "https://www.okx.com/api/v5/market/candles"
OKX_TICKER = "https://www.okx.com/api/v5/market/ticker"
# 15M ve 4H bar araligi (ms) - tazelik hesabi icin
ARALIK_MS = {"15m": 900_000, "4H": 14_400_000}
# Bir bar kaynagi kac bar geride kalirsa BAYAT sayilir (fail-closed)
BAYAT_BAR = 3


def _http(url: str, params: dict, timeout: int = 20) -> dict:
    q = "&".join(f"{k}={v}" for k, v in params.items())
    req = Request(f"{url}?{q}", headers={"User-Agent": "konsey-engine/1.0"})
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def okx_mumlar(inst: str, bar: str, limit: int = 300) -> list[list]:
    """OKX public mum ucu -> Binance 12-alan satirina cevrilmis liste (eskiden yeniye).

    OKX 9 alan dondurur; taker_alis (indeks 9) OKX'te YOKTUR. Bu alan NOTR
    dolguyla (hacim/2) doldurulmaz - None birakilir ve tuketici kanali EKSIK
    sayar. (v5 denetimindeki P1-4 hatasinin tekrarlanmamasi icin.)
    """
    j = _http(OKX_MUM, {"instId": inst, "bar": bar, "limit": limit})
    if str(j.get("code")) != "0":
        raise RuntimeError(f"OKX code={j.get('code')} msg={j.get('msg')}")
    satir = []
    for x in reversed(j.get("data") or []):
        ts, o, h, l, c, vol = int(x[0]), x[1], x[2], x[3], x[4], x[5]
        satir.append([ts, o, h, l, c, vol, ts + 1, x[6] if len(x) > 6 else "0",
                      0, None, "0", "0"])
    return satir


def okx_fiyat(inst: str) -> float:
    j = _http(OKX_TICKER, {"instId": inst})
    if str(j.get("code")) != "0":
        raise RuntimeError(f"OKX code={j.get('code')} msg={j.get('msg')}")
    return float(j["data"][0]["last"])


def yerel_mumlar(yol: str | Path) -> list[list]:
    d = json.loads(Path(yol).read_text(encoding="utf-8"))
    if not isinstance(d, list) or not d:
        raise ValueError(f"{yol}: bos ya da liste degil")
    return d


def _son_ts(barlar: list) -> int:
    son = barlar[-1]
    return int(son[0] if isinstance(son, list) else son["t"])


def tazelik(barlar: list, bar_kodu: str) -> tuple[str, float]:
    """(freshness, yas_dakika) - olculur, beyan edilmez."""
    yas_ms = time.time() * 1000 - _son_ts(barlar)
    yas_dk = yas_ms / 60000.0
    araliк = ARALIK_MS.get(bar_kodu, 900_000)
    if yas_ms <= araliк * 1.5:
        return "CURRENT", yas_dk
    if yas_ms <= araliк * BAYAT_BAR:
        return "LIMITED", yas_dk
    return "STALE", yas_dk


def bar_kaynagi_ekle(reg: EvidenceRegistry, sembol: str, inst: str, bar_kodu: str,
                     yerel_yol: str | Path | None, sid: str, eid: str,
                     grup: str, limit: int = 300) -> dict:
    """Once CANLI dener; kapaliysa yerel dosyaya duser ve DUSUSU kayda gecer."""
    kaynak_turu, hata = "canli-okx", None
    try:
        barlar = okx_mumlar(inst, bar_kodu, limit)
        konum = f"{OKX_MUM}?instId={inst}&bar={bar_kodu}&limit={limit}"
        yontem = "OKX public GET"
    except (URLError, HTTPError, RuntimeError, TimeoutError, OSError) as e:
        hata = f"{type(e).__name__}: {e}"
        if not yerel_yol:
            raise
        barlar = yerel_mumlar(yerel_yol)
        konum, yontem, kaynak_turu = str(yerel_yol), "yerel dosya", "yerel-arsiv"
    taze, yas_dk = tazelik(barlar, bar_kodu)
    reg.add_source(sid, konum, yontem, taze, grup,
                   content=json.dumps(barlar[-5:]),
                   note=(f"canli uc KAPALI ({hata}) -> yerel arsive dusuldu"
                         if hata else "canli uc acik"))
    son = barlar[-1]
    kap = float(son[4] if isinstance(son, list) else son["c"])
    reg.add_evidence(eid, sid, yontem,
                     f"{sembol} {bar_kodu}: {len(barlar)} bar, son kapanis {kap}",
                     f"son_bar_utc={datetime.fromtimestamp(_son_ts(barlar)/1000, timezone.utc):%Y-%m-%d %H:%M} "
                     f"yas={yas_dk:.0f}dk tazelik={taze} kaynak={kaynak_turu}")
    return {"barlar": barlar, "tazelik": taze, "yas_dk": yas_dk,
            "kaynak": kaynak_turu, "hata": hata, "son_kapanis": kap,
            "source_id": sid, "evidence_id": eid}
