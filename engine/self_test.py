#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Karar Motoru öz-testi. İki katman:
1) Birim testleri: quantile, yüzdelik sıra, swing, FVG, akıbet etiketi.
2) Uçtan uca duman testi: sentetik (tohumlu) veriyle iki ardışık koşu —
   determinizm, durum dosyası, akıbet raporu ve zorunlu çıktı blokları.
NOT: Bu test isabet/kârlılık KANITI DEĞİLDİR; motorun mekanik doğruluğunu ve
tekrarlanabilirliğini sınar. İsabet yalnız gerçek koşu defterinden ölçülür.
"""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import karar_motoru as km  # noqa: E402

FAIL = []


def check(name, cond, detail=""):
    status = "OK " if cond else "FAIL"
    print("[%s] %s %s" % (status, name, detail))
    if not cond:
        FAIL.append(name)


# ---------------------------------------------------------------- birim
def test_stats():
    check("quantile-medyan", km.quantile([1, 2, 3, 4, 5], 0.5) == 3)
    check("quantile-q90", abs(km.quantile(list(range(1, 11)), 0.9) - 9.1) < 1e-9)
    check("pct_rank", abs(km.pct_rank([1, 2, 3, 4], 3) - 0.75) < 1e-9)


def mk(t, o, h, l, c, v=100.0):
    return km.Bar(t, o, h, l, c, v)


def test_swings():
    bars = [mk(i, 10, 10 + (5 - abs(i - 5)), 9, 10) for i in range(11)]
    swings = km.find_swings(bars, k=2)
    highs = [s for s in swings if s[2] == "H"]
    check("swing-tepe", len(highs) == 1 and highs[0][0] == 5,
          "bulunan=%s" % highs)


def test_fvg():
    # bull FVG: bar2.low (105) > bar0.high (101); sonrasında dolmuyor
    bars = [mk(0, 100, 101, 99, 100), mk(1, 100, 106, 100, 106),
            mk(2, 106, 108, 105, 107), mk(3, 107, 109, 106, 108)]
    fvgs = km.open_fvgs(bars, lookback=10)
    check("fvg-bull-acik", len(fvgs) == 1 and fvgs[0]["tip"] == "bull"
          and fvgs[0]["ust"] == 105 and fvgs[0]["alt"] == 101, str(fvgs))
    # dolduran bar eklenince düşmeli
    bars.append(mk(4, 108, 108, 100, 101))
    fvgs2 = km.open_fvgs(bars, lookback=10)
    check("fvg-dolunca-duser", len(fvgs2) == 0, str(fvgs2))


def test_outcome_label():
    karar = {"karar": "LONG", "yon": "LONG", "giris_alt": 100.0, "giris_ust": 100.0,
             "giris": 100.0, "stop": 95.0, "iptal": 96.0, "t1": 110.0, "t2": 120.0}
    takip = {"son_bar": 1000, "karar": karar}
    # giriş tetiklenir (bar 2000: 99-101), sonra stop (bar 3000: low 94)
    bars = [mk(2000, 100, 101, 99, 100), mk(3000, 99, 100, 94, 95)]
    txt = km.label_outcome(takip, bars)
    check("akibet-stop", "STOP" in txt, txt)
    # T1+T2 yolu
    bars2 = [mk(2000, 100, 101, 99, 101), mk(3000, 101, 121, 100, 120)]
    txt2 = km.label_outcome(takip, bars2)
    check("akibet-t2", "T1 ve T2" in txt2, txt2)
    # LIMIT girişi tetiklenmeden İPTAL: SHORT bölge [100,102], iptal close>102;
    # bar bölgeye DEĞMEDEN (low 102.3>102) 103'e kapanır → İPTAL
    karar_s = {"karar": "SHORT", "yon": "SHORT", "giris_alt": 100.0, "giris_ust": 102.0,
               "giris": 101.0, "stop": 104.0, "iptal": 102.0, "t1": 95.0, "t2": 90.0}
    takip_s = {"son_bar": 1000, "karar": karar_s}
    bars3 = [mk(2000, 102.5, 103.0, 102.3, 103.0)]
    txt3 = km.label_outcome(takip_s, bars3)
    check("akibet-iptal", "İPTAL" in txt3, txt3)
    # MARKET girişi (bölge tek nokta) anında dolar; gövde iptal (98) altına kapanınca
    # INVALIDATION-EXIT (stop 95 değil) — market emri İPTAL olamaz
    karar_m = {"karar": "LONG", "yon": "LONG", "giris_alt": 100.0, "giris_ust": 100.0,
               "giris": 100.0, "stop": 95.0, "iptal": 98.0, "t1": 110.0, "t2": 120.0}
    takip_m = {"son_bar": 1000, "karar": karar_m}
    bars4 = [mk(2000, 100, 101, 99, 97.5)]
    txt4 = km.label_outcome(takip_m, bars4)
    check("akibet-market-exit", "INVALIDATION-EXIT" in txt4, txt4)


# ---------------------------------------------------------------- uçtan uca
def synth(seed, n15=400):
    """Tohumlu sentetik random-walk kline seti (15M + türetilmiş 4H)."""
    rng = random.Random(seed)
    price = 100.0
    m15 = []
    t0 = 1700000000000
    for i in range(n15):
        drift = 0.03 if i > n15 * 0.55 else -0.01
        o = price
        steps = [rng.gauss(drift, 0.35) for _ in range(4)]
        path = [o]
        for s in steps:
            path.append(max(1.0, path[-1] + s))
        c = path[-1]
        h = max(path) + abs(rng.gauss(0, 0.1))
        l = min(path) - abs(rng.gauss(0, 0.1))
        v = abs(rng.gauss(100, 30)) + (150 if abs(c - o) > 0.8 else 0)
        m15.append([t0 + i * 900000, o, h, l, c, v])
        price = c
    h4 = []
    for i in range(0, len(m15) - 15, 16):
        grp = m15[i:i + 16]
        h4.append([grp[0][0], grp[0][1], max(g[2] for g in grp),
                   min(g[3] for g in grp), grp[-1][4], sum(g[5] for g in grp)])
    return m15, h4


def run_engine(m15, h4, state_dir, workdir):
    p15 = os.path.join(workdir, "m15.json")
    p4 = os.path.join(workdir, "h4.json")
    with open(p15, "w") as f:
        json.dump(m15, f)
    with open(p4, "w") as f:
        json.dump(h4, f)
    r = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "karar_motoru.py"),
         "--m15", p15, "--h4", p4, "--state-dir", state_dir],
        capture_output=True, text=True)
    return r.returncode, r.stdout


def test_end_to_end():
    work = tempfile.mkdtemp(prefix="motor_test_")
    try:
        state = os.path.join(work, "state")
        m15, h4 = synth(seed=7, n15=420)

        # koşu 1
        rc, out1 = run_engine(m15, h4, state, work)
        check("e2e-kosu1-calisti", rc == 0, "rc=%d" % rc)
        for blok in ("ÖNCEKİ KARAR AKIBETİ", "SABİTLER", "BU KOŞUNUN EŞİKLERİ",
                     "KARAR", "NEDEN"):
            check("e2e-blok-%s" % blok.split()[0], blok in out1)
        check("e2e-ilk-kosu-kiyas", "İLK KOŞU" in out1)
        check("e2e-tek-karar",
              sum(out1.count(x) for x in ("KARAR : LONG", "KARAR : SHORT",
                                          "KARAR : BEKLE")) == 1, "tek karar şartı")
        check("e2e-durum-dosyasi", os.path.exists(os.path.join(state, "durum.json")))

        # determinizm: aynı veri + aynı başlangıç durumu -> aynı karar bloğu
        state_b = os.path.join(work, "state_b")
        _, out1b = run_engine(m15, h4, state_b, work)
        karar_a = [l for l in out1.splitlines() if l.startswith(("KARAR", "NEDEN",
                   "GİRİŞ", "STOP", "T1", "R "))]
        karar_b = [l for l in out1b.splitlines() if l.startswith(("KARAR", "NEDEN",
                   "GİRİŞ", "STOP", "T1", "R "))]
        check("e2e-determinizm", karar_a == karar_b)

        # koşu 2: 40 bar daha — akıbet raporu İLK KOŞU olmamalı
        m15x, h4x = synth(seed=7, n15=460)
        rc2, out2 = run_engine(m15x, h4x, state, work)
        check("e2e-kosu2-calisti", rc2 == 0, "rc=%d" % rc2)
        check("e2e-kosu2-kiyas-var", "İLK KOŞU" not in out2)
        with open(os.path.join(state, "durum.json")) as f:
            st = json.load(f)
        check("e2e-durum-alanlari",
              all(k in st for k in ("karar", "takip", "acik_bolgeler",
                                    "rejim_4h", "son_bar")))

        # yetersiz veri -> BEKLE + rc 1, uydurma eşik yok
        rc3, out3 = run_engine(m15[:30], h4[:5], os.path.join(work, "s3"), work)
        check("e2e-yetersiz-veri", rc3 == 1 and "YETERSİZ" in out3)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    test_stats()
    test_swings()
    test_fvg()
    test_outcome_label()
    test_end_to_end()
    print("-" * 50)
    if FAIL:
        print("SONUÇ: %d test BAŞARISIZ: %s" % (len(FAIL), ", ".join(FAIL)))
        sys.exit(1)
    print("SONUÇ: tüm testler geçti (mekanik doğruluk; isabet kanıtı DEĞİL).")
