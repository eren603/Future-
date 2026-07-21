#!/usr/bin/env python3
"""iddia_denetim.py öz-testi. SELF_TEST_OK basar."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import iddia_denetim as d  # noqa: E402


def main():
    # 1) kanıtlı + doğrulanmış gerçek → GEÇTİ, yayınlanabilir
    r = d.run_job({"claims": [
        {"id": "c1", "text": "0.618 fib seviyesi 24170'te", "type": "gerçek",
         "evidence": "grafik-calisma motoru çıktısı: level=24170", "verified": True},
    ]})
    assert r["genel_sonuc"] == "YAYINLANABİLİR", r
    assert r["gecti"] == 1

    # 2) kanıtsız gerçek → KARANTİNA → REVİZE
    r = d.run_job({"claims": [
        {"id": "c2", "text": "Fiyat kesin yükselecek", "type": "gerçek",
         "evidence": "", "verified": False},
    ]})
    assert r["genel_sonuc"] == "REVİZE", r
    assert r["karantina"] == 1 and r["revize_gerekce"] == ["c2"]

    # 3) gerçek ama doğrulanmadı → KARANTİNA
    r = d.run_job({"claims": [
        {"id": "c3", "text": "RSI 28", "type": "gerçek",
         "evidence": "bir yerde gördüm", "verified": False},
    ]})
    assert r["genel_sonuc"] == "REVİZE", r

    # 4) etiketli yorum, kanıtsız → kabul (yayınlanabilir)
    r = d.run_job({"claims": [
        {"id": "c4", "text": "Bence momentum güçlü", "type": "yorum",
         "evidence": "", "verified": False},
    ]})
    assert r["genel_sonuc"] == "YAYINLANABİLİR", r

    # 5) dairesel gerçek (kanıt = metnin kendisi) → KARANTİNA
    r = d.run_job({"claims": [
        {"id": "c5", "text": "Trend yukarı çünkü trend yukarı",
         "type": "gerçek", "evidence": "trend yukarı çünkü trend yukarı", "verified": True},
    ]})
    assert r["genel_sonuc"] == "REVİZE", r
    v = {a["id"]: a for a in r["iddia_denetimi"]}
    assert any("dairesel" in x for x in v["c5"]["reasons"]), v

    # 6) karışık: 1 iyi gerçek + 1 kötü gerçek → REVİZE
    r = d.run_job({"claims": [
        {"id": "a", "text": "Kapanış 100", "type": "gerçek", "evidence": "veri: close=100", "verified": True},
        {"id": "b", "text": "Yarın 120 olur", "type": "gerçek", "evidence": "", "verified": False},
    ]})
    assert r["genel_sonuc"] == "REVİZE" and r["revize_gerekce"] == ["b"], r

    print("SELF_TEST_OK: kanit-kapisi, dogrulama-kapisi, dairesellik, etiket, karisik")


if __name__ == "__main__":
    main()
