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


def test_fvg_mitigasyon():
    """Orta noktaya DEĞEN ama uzak kenara değmeyen bar: eski kural (1.0) bölgeyi
    açık bırakır, yeni kural (0.5) doldurur. Bu test kural geri alınırsa KIRILIR
    — mevcut test_fvg üç ayarda da aynı sonucu verdiği için kuralı sınamıyordu."""
    # bull FVG: bar0.high=101, bar2.low=105 → bölge 101-105, orta nokta (ce)=103
    bars = [mk(0, 100, 101, 99, 100), mk(1, 100, 106, 100, 106),
            mk(2, 106, 108, 105, 107), mk(3, 107, 109, 106, 108)]
    # 102.5'e inen bar: ce'nin (103) ALTINDA ama uzak kenarın (101) üstünde
    bars.append(mk(4, 108, 108, 102.5, 104))
    esk = km.open_fvgs(bars, lookback=10)
    yeni = km.open_fvgs(bars, lookback=10)
    eski_sayi = len([f for f in _with_mit(1.0, lambda: km.open_fvgs(bars, lookback=10))])
    yeni_sayi = len([f for f in _with_mit(0.5, lambda: km.open_fvgs(bars, lookback=10))])
    check("fvg-mit-eski-acik", eski_sayi == 1, "1.0 eşiğinde açık kalmalı: %d" % eski_sayi)
    check("fvg-mit-yeni-dolu", yeni_sayi == 0, "0.5 eşiğinde dolmalı: %d" % yeni_sayi)
    check("fvg-mit-varsayilan", len(esk) == len(yeni) == yeni_sayi,
          "varsayılan sabit 0.5 davranışını vermeli")
    # ce ile eşik birebir tutmalı (aritmetik tutarlılık)
    f = _with_mit(1.0, lambda: km.open_fvgs(bars, lookback=10))[0]
    top, bot = f["ust"], f["alt"]
    check("fvg-mit-ce-esitligi", abs((top - (top - bot) * 0.5) - f["ce"]) < 1e-12,
          "esik=%r ce=%r" % (top - (top - bot) * 0.5, f["ce"]))
    # iki motorun sabiti AYNI olmak zorunda (elle senkron güvenilmez)
    try:
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".claude", "skills", "grafik-calisma", "scripts"))
        import smc_tespit as st  # noqa: E402
        check("fvg-mit-motorlar-ayni", st.FVG_MITIGASYON == km.FVG_MITIGASYON,
              "smc_tespit=%r karar_motoru=%r" % (st.FVG_MITIGASYON, km.FVG_MITIGASYON))
        check("fvg-mit-defaults-bagli", st.DEFAULTS["fvg_mitigasyon"] == st.FVG_MITIGASYON,
              "DEFAULTS=%r modul=%r" % (st.DEFAULTS["fvg_mitigasyon"], st.FVG_MITIGASYON))
    except ImportError as e:                       # pandas yoksa atlanır, gizlenmez
        check("fvg-mit-motorlar-ayni", True, "ATLANDI (smc_tespit yüklenemedi: %s)" % e)
    # zincir-1 kapısı: leaves_fvg bölgesi mitige ise fvg_mitige True demeli
    lf = km.leaves_fvg(bars, 1)
    check("fvg-mit-leaves-bar", lf is not None and lf.get("bar") == 2,
          "leaves_fvg tamamlanma barı: %r" % (lf,))
    check("fvg-mit-zincir1-kapisi", bool(lf) and km.fvg_mitige(bars, lf) is True,
          "ce'si geçilmiş bölge zincir-1'de mitige sayılmalı: %r" % (lf,))
    check("fvg-mit-zincir1-eski-gecirir", bool(lf) and km.fvg_mitige(bars, lf, 1.0) is False,
          "1.0 eşiğinde aynı bölge mitige OLMAMALI")


def test_zincir1_kapisi_fail_closed():
    """DEĞİŞMEZ: 4/4 dizi mitige ise karar BEKLE'dir, alt zincire DEVREDİLMEZ.

    Gözlemci bunun ihlal edildiğini ölçtü: kapı zincir-1'i düşürünce karar alt
    zincire devroluyor ve BEKLE'ler zincir-2 market sinyaline dönüyordu
    (fail-OPEN). Bu test SABİT fixture kullanır — canlı `girdi/` dosyalarına
    bağlı DEĞİLDİR (o dosyaların üzerine her yeni pakette yazılır; değişmez
    testi değişken girdiye çivilemek yanlış-kırmızı/sessiz-yeşil üretir)."""
    # decide()'ın çalışabileceği en küçük sentetik zemin (deterministik)
    b15 = [mk(i * 900000, 100, 100.4, 99.6, 100) for i in range(km.MIN_M15 + 20)]
    b4 = [mk(i * 14400000, 100, 100.4, 99.6, 100) for i in range(km.MIN_H4 + 5)]
    # 4/4 tamamlanmış, FVG'si MİTİGE bir dönüş dizisi enjekte edilir
    sahte_rev = {"yon": "LONG", "adim": 4, "supurme_ucu": 98.0, "seviye": 99.0,
                 "supurme_bar": 5, "disp_bar": 8, "bos_bar": 10, "bos_seviye": 101.0,
                 "fvg": {"tip": "bull", "ust": 103.0, "alt": 101.0, "ce": 102.0, "bar": 8}}
    o_rev, o_mit = km.detect_reversal, km.fvg_mitige
    try:
        km.detect_reversal = lambda *a, **k: dict(sahte_rev)
        # (a) MİTİGE → BEKLE, zincir 1, alt zincire devretmek YASAK
        km.fvg_mitige = lambda *a, **k: True
        k_mit, _ = km.decide(b15, b4)
        check("zincir1-kapi-bekle", k_mit["karar"] == "BEKLE",
              "4/4+mitige BEKLE olmalı: %r" % (k_mit.get("karar"),))
        check("zincir1-kapi-devretmez", k_mit.get("zincir") == 1,
              "karar alt zincire DEVREDİLMEMELİ (zincir=%r)" % (k_mit.get("zincir"),))
        check("zincir1-kapi-gerekce", "mitige" in k_mit.get("neden", "").lower(),
              "gerekçe mitigasyonu söylemeli: %r" % (k_mit.get("neden", "")[:80],))
        # (b) MİTİGE DEĞİL → aynı dizi zincir-1'e girebilmeli (kapı her şeyi kesmez)
        km.fvg_mitige = lambda *a, **k: False
        k_tmz, _ = km.decide(b15, b4)
        check("zincir1-kapi-temizi-gecirir",
              k_tmz.get("zincir") == 1 and k_tmz.get("neden") != k_mit.get("neden"),
              "mitige olmayan 4/4 aynı BEKLE gerekçesini almamalı: %r" %
              (k_tmz.get("neden", "")[:80],))
    finally:
        km.detect_reversal, km.fvg_mitige = o_rev, o_mit


def test_zincir1_kapisi_gercek_veri():
    """Ek ölçüm: canlı girdi varsa kapının sinyal AÇMADIĞI orada da sınanır.

    Veri yoksa ya da veride 4/4+mitige deseni yoksa ÖLÇÜM YOK denir — sessizce
    yeşil sayılmaz. Değişmezin kendisi yukarıdaki sabit fixture'da kilitlidir."""
    base = os.path.dirname(os.path.abspath(__file__))
    setler = [(os.path.join(base, "girdi", "m15.json"), os.path.join(base, "girdi", "h4.json")),
              (os.path.join(base, "girdi", "eth", "m15.json"),
               os.path.join(base, "girdi", "eth", "h4.json"))]
    setler = [(a, b) for a, b in setler if os.path.exists(a) and os.path.exists(b)]
    if not setler:
        print("[  - ] zincir1-kapi-gercek-veri ÖLÇÜM YOK (girdi/ verisi yok — "
              "değişmez sabit fixture'da sınandı)")
        return
    orij = km.fvg_mitige
    acti, kapatti, pencere = [], 0, 0
    try:
        for m15p, h4p in setler:
            b15, b4 = km.parse_klines(m15p), km.parse_klines(h4p)
            for e in range(110, len(b15) + 1):
                w, h4 = b15[:e], b4[:max(km.MIN_H4, int(e / 16) + 1)]
                if len(h4) < km.MIN_H4:
                    h4 = b4[:km.MIN_H4]
                km.fvg_mitige = lambda *a, **k: False
                yok, _ = km.decide(w, h4)
                km.fvg_mitige = orij
                var, _ = km.decide(w, h4)
                pencere += 1
                y, v = yok.get("karar"), var.get("karar")
                if y == "BEKLE" and v in ("LONG", "SHORT"):
                    acti.append((m15p.split("/")[-2], e, v))
                elif y in ("LONG", "SHORT") and v == "BEKLE":
                    kapatti += 1
    finally:
        km.fvg_mitige = orij
    check("zincir1-kapi-gercek-veri", not acti,
          "%d pencere: kapattı=%d AÇTI=%d %s" %
          (pencere, kapatti, len(acti), acti[:3] if acti else ""))
    if kapatti == 0:
        print("[  - ] zincir1-kapi-etkili ÖLÇÜM YOK (bu veri paketinde 4/4+mitige "
              "deseni yok — kapının etkisi ölçülemedi, HATA DEĞİL)")


def _with_mit(deger, fn):
    """FVG_MITIGASYON'u geçici olarak değiştirip fn()'i koştur (sabiti geri koyar)."""
    onceki = km.FVG_MITIGASYON
    km.FVG_MITIGASYON = deger
    try:
        return fn()
    finally:
        km.FVG_MITIGASYON = onceki


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
    # K1 regresyonu: INVALIDATION-EXIT TERMINAL bir koda eşlenmeli (defter kapanır),
    # 'DİĞER' DEĞİL. Ayrıca outcome_code her terminal/nonterminal kodu tanımalı.
    check("outcome-invalidation-terminal", km.outcome_code(txt4) == "INVALIDATION-EXIT",
          km.outcome_code(txt4))
    check("outcome-invalidation-in-terminal", "INVALIDATION-EXIT" in km.TERMINAL_OUTCOMES,
          str(km.TERMINAL_OUTCOMES))
    for _c in km.OUTCOME_CODES:
        check("outcome-code-tanir-%s" % _c, km.outcome_code("... %s ..." % _c) == _c, _c)
    test_akibet_arsiv_boslugu()


def test_akibet_arsiv_boslugu():
    """REGRESYON — 2026-08-08: 15M arşivindeki 7515 dk'lık boşluk, T2'de +2.50R
    kazanan BTC SHORT'unu deftere 'STOP' diye yazdırmıştı (boşluk sonrası ilk
    stop teması bulundu, boşluğun içindeki T1/T2 barları görünmedi).
    Kapı: boşluk varsa ÖLÇÜLEMEDİ (nonterminal, R yazılmaz); boşluk YOKSA
    eski davranış birebir korunur (aksi halde kapı tüm ölçümü öldürür)."""
    BAR = 900_000                       # 15 dk
    T0 = 1_785_000_000_000
    T0 -= T0 % BAR
    karar = {"karar": "SHORT", "yon": "SHORT", "giris_alt": 100.0,
             "giris_ust": 101.0, "giris": 100.5, "stop": 103.0,
             "iptal": 101.0, "t1": 96.0, "t2": 95.0, "giris_tipi": "limit"}
    takip = {"son_bar": T0, "karar": karar}

    def seri(bosluklu):
        b = [mk(T0 + BAR, 100.2, 101.5, 100.0, 100.4)]          # DOLUM
        atlama = 5 * 24 * 60 * 60_000 if bosluklu else BAR      # 5 gün / normal
        t = T0 + BAR + atlama
        b.append(mk(t, 102.0, 103.5, 101.8, 102.5))             # stop teması
        for i in range(1, 6):
            b.append(mk(t + i * BAR, 102.5, 102.8, 102.2, 102.6))
        return b

    txt_b = km.label_outcome(takip, seri(True))
    check("akibet-bosluk-olculemedi", "ÖLÇÜLEMEDİ" in txt_b and "STOP" not in txt_b,
          txt_b)
    check("akibet-bosluk-nonterminal",
          km.outcome_code(txt_b) == "ÖLÇÜLEMEDİ"
          and "ÖLÇÜLEMEDİ" not in km.TERMINAL_OUTCOMES, km.outcome_code(txt_b))
    txt_k = km.label_outcome(takip, seri(False))
    check("akibet-bosluksuz-degismedi", "STOP" in txt_k, txt_k)

    # (a) KIRILGANLIK KİLİDİ: hüküm metni hiçbir TERMINAL kodu İÇERMEMELİ —
    # büyük/küçük harf farkı GÖZETMEKSİZİN. Koruma yalnız harf duyarlılığına
    # dayanırsa metin bir gün .upper()'lanınca ÖLÇÜLEMEDİ sessizce terminal
    # STOP'a döner ve tamir tersine çevrilir (denetçi bulgusu 2026-08-08).
    _ust = txt_b.upper()
    check("akibet-bosluk-metni-terminal-kod-icermez",
          not any(c.upper() in _ust for c in km.TERMINAL_OUTCOMES),
          [c for c in km.TERMINAL_OUTCOMES if c.upper() in _ust] or txt_b[:80])

    # (b) PENCERE KAYMASI ≠ ARŞİV DELİĞİ: karar barı 200 barlık kayan
    # pencerenin dışına düştüyse hüküm bunu AÇIKÇA söylemeli ve çareyi
    # (--arsiv) göstermeli; "arşiv deliği" diye yanlış teşhis koymamalı.
    _uzak = [mk(T0 + 30 * 24 * 60 * 60_000 + i * BAR,
                102.0, 102.5, 101.5, 102.0) for i in range(6)]
    txt_p = km.label_outcome(takip, _uzak)
    check("akibet-pencere-kaymasi-ayirt-edilir",
          "PENCERE KAYMASI" in txt_p and "--arsiv" in txt_p
          and km.outcome_code(txt_p) == "ÖLÇÜLEMEDİ", txt_p)

    # (c) NOMİNAL ARALIK boşluk ÇOĞUNLUKTAYKEN de doğru olmalı: farkların
    # çoğu boşluksa medyan da mod da boşluğa kayıp kapıyı fail-OPEN yapıyordu.
    _seyrek = [mk(T0, 99, 99.5, 98.5, 99.0),
               mk(T0 + BAR, 100.2, 101.5, 100.0, 100.4),
               mk(T0 + 2 * BAR, 100.4, 100.8, 100.1, 100.5)]
    for i in range(1, 6):                       # 5 adet 24×BAR'lık atlama
        _seyrek.append(mk(T0 + 2 * BAR + i * 24 * BAR, 100.5, 100.9, 100.2, 100.6))
    check("akibet-bar-araligi-boslukla-kaymaz",
          km._bar_araligi(_seyrek) == BAR,
          "ölçülen=%s dk, beklenen=%s dk (farkların 5/7'si boşluk)"
          % (km._bar_araligi(_seyrek) // 60000, BAR // 60000))
    # (d) tek bozuk zaman damgası nominali sıfıra çekip TÜM ölçümü kapatmamalı
    _bozuk = [mk(T0 + i * BAR, 100, 100.5, 99.5, 100) for i in range(6)]
    _bozuk.insert(3, mk(T0 + 2 * BAR + 1, 100, 100.5, 99.5, 100))   # 1 ms sapma
    check("akibet-bar-araligi-tek-bozuk-damga-yutulur",
          km._bar_araligi(_bozuk) == BAR,
          "ölçülen=%s ms, beklenen=%s ms" % (km._bar_araligi(_bozuk), BAR))


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
    # timeout (S3): motor takılırsa öz-test süresiz asılı kalmasın (sabit argüman
    # listesi + shell=False → enjeksiyon yok; eksik olan yalnız zaman sınırıydı).
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "karar_motoru.py"),
             "--m15", p15, "--h4", p4, "--state-dir", state_dir],
            capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT: karar_motoru 120 sn içinde bitmedi"
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
    test_fvg_mitigasyon()
    test_zincir1_kapisi_fail_closed()
    test_zincir1_kapisi_gercek_veri()
    test_outcome_label()
    test_end_to_end()
    print("-" * 50)
    if FAIL:
        print("SONUÇ: %d test BAŞARISIZ: %s" % (len(FAIL), ", ".join(FAIL)))
        sys.exit(1)
    print("SONUÇ: tüm testler geçti (mekanik doğruluk; isabet kanıtı DEĞİL).")
