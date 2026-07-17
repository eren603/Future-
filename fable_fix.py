#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fable10.py — FABLE6_5 UZERINE F9 (SENARYO-YON) + F10 (TELEFON STORAGE/LATENCY) ONARIMI.
  (soy: fable6_5.py — FABLE6_4 UZERINE ANAPRONT v3.3.1 KANIT-DISIPLINLI DENETIM F1-F8)

F10 (canli telefon/Pydroid bulgusu — davranis degisikligi belgelidir):
  * F10a STORAGE ENOSYS-DAYANIKLILIGI: Android/Pydroid FS'inde flock()/fsync() calisma
        aninda [Errno 38] ENOSYS firlatinca eski kod TUM yazimi dusuruyordu -> tahmin/
        sinyal/plan/ledger HIC yazilmiyordu (kayit-altina-alma sozlesmesi olu). Artik
        desteklenmeyen-cagri hatasinda bir kez uyarilir, oturum icin kilit/fsync atlanir
        ve yazim ATOMIK temp+os.replace ile SURER (tek-surec telefonda guvenli; append-
        only hash-zinciri korunur). _FLOCK_OK oturum bayragi tekrar-deneme spam'ini keser.
  * F10b LATENCY BUTCESI: ledger_max_latency_ms 120sn -> 360sn. Telefon 4 sembolu SIRAYLA
        (agir MC) islerken son semboller (SOL/DOGE) her kosuda LATENCY_GATE'e dusuyordu;
        oysa 15m bar hala GECERLI. 6 dk barin ortasindan once, tazelik korunur; giris
        kaymasi AYRI live-price-gap kapisiyla denetlenir.

F9 (KULLANICI DIREKTIFI — DURUSTLUK-ETIKETI DEGISIKLIGI, BILINCLI):
  Kullanici acik istegi uzerine 144-hucre/6-aile senaryosu artik YON KAYNAGI olabilir.
  Istatistik topluluk kenari YOKKEN (zero-skill / dusuk-guven / flat / down-up tie /
  uzlasmazlik) senaryo side_hint'i (LONG/SHORT) YONU URETIR; sonra market/pusu secilir:
    - MARKET yalniz veto + maliyet + EV + market-kalite + htf + RR kapilarinin TAMAMINI
      gecerse acilir (negatif-EV/ters-yon market YINE uretilmez).
    - Bu kapilar market'i keserse KOR BEKLE degil, o yonde PUSU (scen_driven+scen_side).
  DURUSTLUK: bu, onceki 'senaryo yon uydurmaz' (F3) sozlesmesini KULLANICI ISTEGIYLE
  DELER. Bu sinyallerin KENARI KANITLANMAMISTIR; sentetik/offline uretim gercek-piyasa
  ustunlugu DEGILDIR (DSR=N/A aynen surer). scen_yon_enabled=False eski F3 davranisini
  (senaryo yalniz fail-closed risk kapisi) geri getirir. Guvenlik: side_hint zaten taze
  dipte SHORT / taze tepede LONG uretmez (classify_scenario) + yapisal veto -> cift koruma.

FABLE6_5 ONARIM NOTU (Anapront denetimi bulgusu -> kullanici sozlesmesi; davranis degisiklikleri belgelidir):
  * F1  ARGUMANSIZ = SUREKLI MOD: telefon/Pydroid'de argumansiz baslatma artik 15m
        kapanisina hizali LOOP'tur (run_loop). Tek-atim: sembol argumani ver veya YON_LOOP=0.
  * F2  TEK-KENAR PUSU: ayni kosuda iki zit bekleyen plan KURULMAZ (kullanici: "ayni anda
        hem long hem short plani uretmemeli"). Kenar secimi deterministik ve veri-turevli:
        (1) canli MC ilk-temas olasiligi (p_ust vs p_alt), (2) yoksa fiyatin bant-ortasina
        gore konumu, (3) tam esitlikte plan kurulmaz (esitlik=BEKLE ilkesi).
        pusu_tek_kenar=False eski cift-kenar davranisini geri getirir (regresyon kiyasi).
  * F3  SENARYO ONCE + RISK KAPISI: 144-hucre + 6-aile siniflandirmasi artik KARARDAN ONCE
        _decide_core icinde hesaplanir (d.scen144/d.aile ile log/ekrana tasinir) ve
        scen_risk_gate_enabled=True iken hucre okumasi secilen yone ACIKCA TERS ise market
        sinyali BEKLE'ye duser. Senaryo YON URETMEZ (yalniz fail-closed risk keser);
        bagimsiz OOS katkisi HALA olculmemistir (durust sicil degismedi).
  * F4  MALIYET-SONRASI NET SONUC OLCULUR: karar maliyeti d.cost_abs olarak tasinir; cozulen
        canli sinyale net_abs/net_r, pusu karnesine net_r yazilir; _cpcv_r_multiple R'leri
        artik maliyet-SONRASIDIR. Maliyet alani olmayan eski kayitlar brut kalir (uydurulmaz).
  * F5  PUSU TETIK TEYIDINDE CANLI GIRIS ONERISI: ateslenme (igne + kapanmis-mum geri-alisi)
        raporuna, o anki mark/bid-ask + spread + slip + maliyetle "SIMDI MARKET gir" satiri
        eklenir. Bayat/kopuk fiyat veya hedef-otesi durumda onerilmez; "kovalamak yasak" ustundur.
  * F6  PLAN-STORE-V2 TETIK SOZLESMESI legacy ile esitlendi: salt fiyat-dokunusu artik
        TRIGGERED degil TOUCHED'dir; TRIGGERED yalniz kapanmis 15m mumun geri-alisiyla verilir.
  * F7  (a) BTC getiri-hizalamasi: timestamp kesisimi <5 ise POZISYONEL kuyruk eslemesine
        DUSMEZ (bos doner -> katman veri-yetersiz susar); (b) spot kline'lara vadeli ile
        ayni sort + dedupe geldi.
  * F8  KARAR ciktisina ayri MALIYET ve GECERSIZLIK satirlari; islem planina giris bandi;
        acik-sinyal store'una entry_band/cost alanlari.
  ONARIM KAPSAMI DISI (durust sicil): gercek-piyasa davranisi, canli ag kosusu, OOS
  dogrulamasi — bu onarim offline kanitla sinirlidir; DSR=N/A sozlesmesi aynen surer.

FABLE6_4 SOY NOTU: FABLE6_2 UZERINE BAGIMSIZ REJIM/SENARYO/BIAS DENETIMI (REPORT_3_REGIME_BIAS) ONARIMI
+ BAGIMSIZ SIMULASYON/SINYAL DENETIMI (REPORT_4_SIMULATION_SIGNAL) ONARIMI (S1-S6 notu asagida).

FABLE6_3 ONARIM NOTU (REPORT_3 bulgusu -> duzeltme; davranis degisiklikleri belgelidir):
  * R1  ensemble_side_conflict kapisi (denetim: OLU KAPI — side zaten ayni probs'un
        argmax'i; 0/200.000 ozellik testi + 400 canli kosuda 0 ateslenme) artik DURUST
        etiketli SOZLESME-TRIPWIRE'dir: normal akista tetiklenemez; tetiklenirse ic
        sozlesme bozulmus demektir (fail-closed BEKLE + gorunur tani). Yaniltici
        'ic tutarlilik freni' iddiasi kaldirildi; saf predikat + birim testi korunur.
  * R2  fable6'daki cift decorrelation_risk>=1.0 dali (denetim 1536-1537) fable6_2'de
        ZATEN tekti; dogrulandi (grep=1), degisiklik gerekmedi.
  * R3  SIFIR-SKILL KAPISI: bes skill tahmincisi (lojistik/analog/ampirik/markov/
        montecarlo) walk-forward'da 0 agirlik aldiysa havuz yalniz overlay bloklaridir
        (flow/macro/btc) ve overlay SOZLESME geregi yon acamaz. Eski davranis bunu
        'abstain 0.45 < overlay-tavani 0.4667' sayisal tesadufune emanet ediyordu ve
        0.45-0.4667 araligi ACIKTI (denetim M3/6). Artik acik kural: sifir-skill ->
        BEKLE (zero_skill_abstain=True; False=eski davranis). Davranis degisimi yalniz
        bu dar aralikta ve sifir-skill kosulundadir.
  * R4  144-hucre iddiasi kucultuldu/belgelendi: SCEN_IMKANSIZ_HUCRELER (15 yapisal
        ulasilamaz hucre; kod-yolu ispati denetim 4.1) + 'pratik cesitlilik ~75 hucre,
        ~54 hucre NOT-VERIFIED' notu + selftest tarama regresyonu. OI verisi yokken
        ACCUMULATION/DISTRIBUTION olculemez -> Scenario144.oi_var alani + gorunur not.
  * R5  Uc rejim taksonomisi TEK KAYNAKTA birlestirildi: rejim_gorunumu() kanonik
        gorunum — vol_regime karara giren TEK alan (yalniz EXTREME->guven kismasi +
        taze_donus uyarisi; canli_only=True iken adaptive_disagree_max devre disi),
        rejim_ailesi=gosterim+mikro-siralama, family6=YALNIZ gosterim. Karar mantigi
        degismedi; iliski tek yerde belgeli ve ekranda tek satirda.
  * R6  Kadans belgeleme: 15m motoru icin ONERILEN varsayilan LOOP modudur (saat-basi
        tek-atim 4 kurulumdan 3'unu atlar); YON_LOOP=1 argumansiz kosuyu loop'a cevirir;
        run() sonunda gorunur ipucu. F1 hizalamasi tek-atimi gecerli noktaya ceker.
        (FABLE6_5/F1 GUNCELLEMESI: argumansiz varsayilan ARTIK dogrudan LOOP'tur.)
  * R7  Ortak-girdi ifsasi: of.delta_z hem MC drift'ine hem flow blokuna girer —
        mc/flow uyumu BAGIMSIZ teyit DEGILDIR; uzlasmazlik olcumu bloklari bagimsiz
        sayar (kod ici + ekran notu; davranis degismedi).
  * R8  Nadir-hucre telemetri acligi belgelendi: scen_cell_min_resolved=15 nadir
        hucrelerde pratik olarak olgunlasamaz (SCEN_IMKANSIZ_HUCRELER blogunda not).
  * R9  abstain_prob(0.45) ile 2/3*(0.5+macro_p_clip)=0.4667 overlay-tavani iliskisi
        Config'te acikca belgelendi (R3 kapisiyla birlikte).
  ONARILAMAYANLAR (REPORT_3 NOT-VERIFIED sicili — offline uydurulmaz): gercek-piyasa
  davranisi, ~54 gozlemlenmemis hucre, elle-ayarli esiklerin OOS dogrulamasi (F11),
  canli PIT uyumu. DSR=N/A sozlesmesi aynen surer.

REPORT_4 ONARIM NOTU (bagimsiz simulasyon/sinyal denetimi bulgusu -> duzeltme):
  * S1  SHORT uretimi RUNTIME'DA KANITLANDI: denetimde ~520 sahnede motor-uretimi SHORT hic
        gozlenmemisti. Kok neden dusuk-katman simetrisizligi DEGIL (mc/first-passage/senaryo
        AYNA-simetrik; olculdu): trend fikstUrlerinde skill=0 -> yon contrarian flow
        overlay'inden geliyor, EV kapisi da bu yanlis yonu (dogru sekilde) kesiyordu.
        Ogrenilebilir OOS kenarli sahnelerde motor varsayilanlarla SHORT da LONG da uretir;
        selftest [VARSAYILAN-SINYAL] iki yonu URUN Config() ile olcer (7L/4S 120-sahne tarama).
  * S2  'Varsayilan esiklerle sifir sinyal' bulgusu ayni regresyonla kapatildi: serbestlestirme
        olmadan LONG (seed=3,+0.004,0.008) ve SHORT (seed=1,-0.004,0.008) uretimi selftest'te
        surekli olculur. Onceki 0-sinyal sahneleri kalici trend+skill=0 kosuluydu (R3 sozlesmesi
        geregi DURUST BEKLE; kusur degil, olcum eksigiydi).
  * S3  Dip/tepe veto regresyonlarinin mutasyon korlugu kapatildi (EXEC-YOL baglayici-veto
        sahneleri): forbid_short/forbid_long mutantlari artik OLDURULUYOR (olculdu, rc=1).
  * S4  CLI bilinmeyen-komut bekcisi: taninmayan kucuk-harf arguman (or. 'sefltest') artik
        canli veri yoluna DUSMEZ; kullanim metni + exit 2 (fail-closed). Sembol ('usdt' soneki
        veya BUYUK-harf alfasayisal) ve argumansiz belgelenmis varsayilan yol korunur.
  * S5  EV maliyet modeline GECIKME + KISMI-DOLUM temsili eklendi (exec_latency_ms=1500,
        latency_vol_k=1.0 -> bacak basina k*ATR*sqrt(gecikme/bar); derinlik olculemeyen
        bacaklarda partial_fill_extra_frac=0.25 kayma payi). Konservatif UST-SINIR; etiketler
        'komisyon/spread/slip/gecikme/kismi-dolum' olarak guncellendi. Funding path-modeli
        yine yok (ust-sinir katkisi mevcut, belgeli). 0 vererek eski davranisa donulur.
  * S6  Kozmetik durustluk: render kaynak etiketi OFFLINE kararda 'fapi.binance.com' demez;
        target_end_ms, last_closed_ms atanmamis (sentetik) snapshot'ta son kapali mumun
        close_ms'inden PIT-guvenli turetilir.
  REPORT_4'te ACIK KALANLAR (offline kapatilamaz; durust sicil): gercek-piyasa LONG/SHORT
  emisyon oranlari, olculmus OOS/PBO/DSR kaniti, cihaz-ustu Pydroid kosusu. DSR=N/A surer.

FABLE6_2 ONARIM NOTU (denetim bulgusu -> duzeltme; davranis degisiklikleri belgelidir):
  * F1  run(): tek-atim kosu 15m kapanisina otomatik hizalanir (YON_HIZALA=0 kapatir);
        saat-basi kosuda %100 latency-BEKLE ve 4'te-3 atlama giderildi. run_loop degismedi.
  * F2  fetch_klines: bozuk openTime satiri sayfalama/siralamada da ATLANIR (fetch cokmez).
  * F3  build_snapshot: 15m/1h penceresinde zaman boslugu varsa bosluk-oncesi barlar atilir,
        bosluk-SONRASI bitisik sufiksle karar verilir (no-lookahead korunur; tani yazilir).
  * F4  FHS: getiriler sigma_{t-1} ile arindirilir (Barone-Adesi sozlesmesi; kuyruk sonuklugu fix).
  * F5  mc_ilk_temas: bar-ici fitil kesisi Brownian-kopruyle olculur (tetik 'igne' ile ayni dil).
  * F6  robust_z: sabit gecmis + medyandan farkli deger -> None (mutlak-fallback devreye girer).
  * F7  _quantile: dogrusal interpolasyon (kucuk-n yarim-adim sapmasi fix).
  * F8  robust_z: cift n'de gercek medyan (iki ortanin ortalamasi) — medyan ve MAD icin.
  * F12 predicted_at sunucu-saat cipali (cihaz saati kaymissa kapi yanlis BEKLE uretmez).
  * F13 build_snapshot: bagimsiz REST uclari paralel cekilir (YON_PARALEL_FETCH=0 eski seri yol);
        en-kotu seri fetch suresi 120sn latency butcesini yiyemez.
  * F14 reversal_radar: CVD-iraksama z taban istatistigi son kovayi dislar (delta_z ile simetrik).
  * F16 _moving_block_ci: blok uzunlugu n^(1/3) kurali (taban 2).
  * F17 funding z-penceresi ayri isimli parametre (funding_norm_win; varsayilan davranis ayni).
  * F9/F10/F15 belgeli tasarim direktifi (degistirilmedi); F11 (~60 sabitin OOS dogrulamasi)
    canli veri gerektirir — bu onarimda YAPILMADI ve yapildigi iddia edilmez.

FABLE6 SOZLESMESI:
  * Istatistiksel hedef, tam 16 mum sonraki endpoint icin DOWN/FLAT/UP uc siniftir.
  * Olgunlasmamis veya hedef timestamp'i eksik etiket egitime GIRMEZ.
  * LIVE ve OFFLINE karar baglamlari ayridir; backtest/CPCV canli store veya mark
    kapilarini okuyamaz.
  * Esitlik her yerde FLAT/BEKLE'dir; EV esitliginde LONG zorlanmaz.
  * Tahmin defteri append-only, hash-zincirli ve model/feature/config nesillidir.
  * Mikro ve 1..144 sparse-ID senaryo katmanlari TELEMETRI/PUSU katmanidir; bagimsiz OOS
    katkisi kanitlanmadigi icin piyasa yonunu secmez.
  * DSR, dogrulanmis net getiri ve gercek trial registry yokken N/A'dir.

Asagidaki eski aciklamalar FABLE5 soy-agacini belgelemek icin korunmustur.
Iki paralel yon4-dali BIRLESTIRILDI: (a) yon5'in "sihirli sayi" altyapisi — tum mutlak/gomulu esikler
robust-z / quantile / isimli-Config'e donusturuldu (sembol- ve rejim-bagimsiz veri-goreli olcum,
NO-LOOKAHEAD; yeterli gecmis yoksa eski sabite duser = "kalibre DEGIL"); (b) yon6'nin 1s+15m MTF
hizalama kapisi, islem maliyeti (varsayilan market giris/cikis + slip), zaman-azalimli lojistik (ussel recency-agirligi),
Wilson secim-biasi fix ve Deflated-Sharpe/trial-count durustluk gostergesi. Cakisan sabitlerde
tutarli-olan secildi (or. rev_calib_bucket_min=12, Wilson ile uyumlu).
PANEL7 soy-agacindaki karar motorunun uzerinde 6 ust aile/12 ayrintili durum x 12 olay
kimlik katalogu bulunur: senaryo tespit edilir (hucre no + sade dil sinyali),
giris/hedef/stop SEVIYELERINI MC ilk-temas tradeability katmani 15m'de verir.
+ MIKRO-SENARYO KATALOGU (29 kalip): VADELI+SPOT KOMBINE adlandirilmis-kalip taramasi —
fiyat-aksiyonu (yutan mum, sikisma, uc-itis, likidite havuzlari, FVG, W/M, VWAP-gerilme,
iraksama), turev-akis (OI-flush/birikim, kalabalik-tuzagi, squeeze-yakiti), SPOT-vadeli
(basis prim/iskonto z, spot-onculuk, teyitsiz-kopus) + belgelenmis KOMBO kurulumlar.
Her kalip "15m'de fiyat SU hareketi yapabilir (ADAY)" cumlesi + guvenilirlik kati (A/B/C)
+ legacy bilesik islem-cozum telemetrisiyle gosterilir (bagimsiz OOS katkisi DEGIL).
KARARA DOKUNMAZ: gosterir+loglar. Senaryo yonu ile endpoint3
karariyla hiza/uyusmazlik yalniz betimsel raporlanir; karar veya guven degismez. ID alaninin
tam kartezyen OOS katkisi dogrulanmamistir. Tum cikti [PAPER].

--- yon5 KATKISI: SIHIRLI-SAYI TEMIZLIGI (veri-goreli olcum, saf stdlib) ---
  * DINAMIK NORMALIZASYON: mutlak esikler (funding<-0.0003, OI>0.003, taker>1.05, htf 1.0008,
    vol-rejim 2.0/1.4 ...) yerine ilgili buyuklugun KENDI tarihsel dagilimina gore robust-z
    (median/MAD) veya quantile. Sembol/rejim-bagimsiz; yetersiz gecmis -> Config fallback (cold-start).
  * robust_z() + _change_series() yardimcilari; ~60 isimli Config meta-parametresi (STRUCTURAL/STATISTICAL).
--- yon6 KATKISI (arastirma-onayli, saf stdlib) ---
  * MTF: 1 saatlik trend KARARA girer (htf_trend). 15m yonu guclu 1s trendine karsi ve donus
    teyidi yoksa -> BEKLE. Hesap 1s+15m; giris/cikis 15m.
  * ISLEM MALIYETI: varsayilan MARKET giris/cikis + yonlu derinlik/slippage cost'a eklenir.
    EV kapisi maliyet-SONRASI EV'yi olcer; kapida ekstra maliyet-katmani YOK (cifte-sayim fix).
  * ZAMAN-AZALIMLI OGRENME: lojistik fit'te ussel recency agirligi
    (rejim etiketiyle kosullama degildir).
  * SECIM-BIASI FIX: reversal_calib'te Wilson alt-guven siniri (winner's curse notr).
  * DURUST TESHIS: net getiri/trial registry yoksa DSR=N/A; OAT-CPCV yalniz kismi tani; MODEL KARTI;
    perturbation kararlilik testi; sessiz hatalar stderr'e.

--- PANEL7 CEKIRDEGI (korundu) ---
Ogrenen olasilik CEKIRDEGI; yon uretimi, birlestirme ve donus katmanlari (PANEL7_TASARIM.md).

TEK ILKE: 4s endpoint yonu kalibre DOWN/FLAT/UP toplulugundan secilir. Monte-Carlo
ilk-temas EV'si, maliyet, yapi ve canli icra bu yonu yalniz KABUL veya RED eder;
endpoint yonunu tersine ceviremez. Kanit yetersizse BEKLE.

Katmanlar:
  A) Yon = argmax(P_DOWN, P_FLAT, P_UP), esitlik=FLAT/BEKLE. MC seviye-miknatisi
     secilen yonun tradeability/ilk-temas planini olcer; yon secmez.
  B) Hedge agirlik TUM tahmincilere (kenarsiz -> gercekten 0). Korelasyonlu ogrenenler tek
     blok sayilir; uzlasmazlik bloklar-arasi olculur. Esikler maliyet/volatiliteye adaptif.
  C) Oncu-makro blok: origin-PIT OI momentum + funding + taker karara girer.
     Origin-sonrasi order-book yalniz icra/abstain katmanindadir; yon secemez.

Pydroid: sari (>) RUN — ARGUMANSIZ BASLATMA SUREKLI MODDUR (FABLE6_5/F1):
  python fable6.py          -> BTC,ETH,SOL,DOGE; her 15m kapanisinda otomatik yeniden degerlendirir
  (eski tek-atim: YON_LOOP=0 python fable6.py; 'loop' argumani da ayni surekli moda acilir.)
Terminal tek-atim: python fable6.py BTCUSDT   (sembol argumani = tek-atim, F1-hizalamali)
Self-test (ag YOK): python fable6.py selftest   |   Mutasyon testi (dev, ag YOK): python fable6.py mutasyon
CPCV/PBO overfit olcumu (dev): python fable6.py cpcv BTCUSDT [fast]   (agsiz kanit: cpcv sentetik fast)
Yalniz Python stdlib + internet (fapi.binance.com). Yatirim tavsiyesi DEGILDIR; basari orani onceden bilinmez.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import random
import sys
import time
import urllib.request
import urllib.parse
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Dict, List, Optional, Tuple

# ════════════════════════════════════════════════════════════════════════════
# Bug 4/6/8/9: STORE ATOMIKLIK + DAYANIKLILIK (fcntl.flock + fsync + os.replace)
#   * fcntl process-kilidi ve fsync ile telefonda yarim-yazim/es-zamanli-yazim
#     store'u bozamaz; commit basarisizsa CommitReceipt DONMEZ, exception firlar
#     ('updated' asla yalan soylemez).
#   * Bozuk JSON sessizce {} ile EZILMEZ -> .corrupt.<ts> karantinasina alinir.
#   * fcntl yoksa (or. Windows dev) dayaniklilik korunur, kilit atlanir (fail-open import).
# ════════════════════════════════════════════════════════════════════════════
try:
    import fcntl as _fcntl
    _HAS_FLOCK = True
except Exception:
    _fcntl = None
    _HAS_FLOCK = False
# F10 (canli telefon/Pydroid bulgusu): fcntl IMPORT edilebilir ama Android app-private /
# sdcard/FUSE dosya sisteminde flock() CALISMA ANINDA [Errno 38] ENOSYS ('Function not
# implemented') firlatir. Eski kod yalniz 'import edilemedi' halini ele aliyordu -> flock
# runtime'da patlayinca TUM yazim (tahmin/sinyal/plan/ledger) dusuyor ve HICBIR kayit
# tutulmuyordu. Cozum: flock/fsync runtime'da desteklenmezse bir kez uyar, o oturum icin
# kapat ve yazima ATOMIK temp+os.replace ile DEVAM et (tek-surec telefonda flock zaten
# gereksiz; atomiklik ve hash-zinciri korunur). _FLOCK_OK oturum-boyu durum bayragidir.
_FLOCK_OK = _HAS_FLOCK
_DEGRADE_WARNED: set = set()
# ENOSYS/desteklenmeyen-cagri hata numaralari (Android/FUSE/exotic FS'lerde flock/fsync)
_UNSUPPORTED_ERRNOS = frozenset(x for x in (
    getattr(__import__("errno"), n, None)
    for n in ("ENOSYS", "ENOTSUP", "EOPNOTSUPP", "EINVAL", "EPERM", "EACCES", "ENOLCK", "EBADF")
) if x is not None)


def _warn_once(key: str, msg: str) -> None:
    if key not in _DEGRADE_WARNED:
        _DEGRADE_WARNED.add(key)
        try:
            sys.stderr.write("[STORE-DEGRADE] " + msg + "\n")
        except Exception:
            pass


def _flock_or_degrade(fd, exclusive: bool = True) -> bool:
    """flock dener; desteklenmiyorsa (ENOSYS vb.) oturum icin kapatir ve False doner
    (yazim yine de atomik temp+replace ile surer). True=kilit kuruldu."""
    global _FLOCK_OK
    if not _FLOCK_OK or _fcntl is None:
        return False
    try:
        _fcntl.flock(fd, _fcntl.LOCK_EX if exclusive else _fcntl.LOCK_SH)
        return True
    except OSError as exc:
        if getattr(exc, "errno", None) in _UNSUPPORTED_ERRNOS:
            _FLOCK_OK = False
            _warn_once("flock", "flock bu dosya sisteminde desteklenmiyor (%s); "
                       "surec-kilidi ATLANIR, yazim atomik temp+replace ile surer "
                       "(tek-surec telefonda guvenli)." % exc)
            return False
        raise


def _funlock_safe(fd) -> None:
    if _fcntl is None:
        return
    try:
        _fcntl.flock(fd, _fcntl.LOCK_UN)
    except OSError:
        pass


def _fsync_safe(fd) -> None:
    """fsync dener; desteklenmiyorsa (ENOSYS) sessizce gecer (veri yine os.replace ile atomik)."""
    try:
        os.fsync(fd)
    except OSError as exc:
        if getattr(exc, "errno", None) in _UNSUPPORTED_ERRNOS:
            _warn_once("fsync", "fsync bu dosya sisteminde desteklenmiyor (%s); atlaniyor." % exc)
            return
        raise


from datetime import datetime as _dt, timezone as _tz


class StoreError(Exception):
    """Store katmani temel hatasi."""


class StoreCorrupt(StoreError):
    """JSON bozuk — karantinaya alinmali, asla {} ile ezilmemeli."""
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Store corrupt: {path}: {reason}")


@dataclass
class CommitReceipt:
    """Atomik commit basariliysa doner. Yoksa 'updated' yalani imkansiz."""
    path: str
    sha256: str
    bytes_written: int
    committed_at_ms: int


def _quarantine_corrupt(path: str, reason: str) -> str:
    """Bozuk dosyayi .corrupt.<ts> karantinasina tasi (sessizce yok etme)."""
    ts = _dt.now(_tz.utc).strftime("%Y%m%d_%H%M%S")
    corrupt_path = f"{path}.corrupt.{ts}"
    try:
        if os.path.exists(path):
            os.rename(path, corrupt_path)
    except OSError:
        pass
    return corrupt_path


def _safe_load_json_file(path: str, name: str = "file"):
    """Guvenli tek-JSON yukleme. Bozuk -> karantina + StoreCorrupt exception."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        if not raw.strip():
            qpath = _quarantine_corrupt(path, "empty_file")
            raise StoreCorrupt(path, f"bos dosya -> karantina: {qpath}")
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        qpath = _quarantine_corrupt(path, f"json_decode: {exc}")
        raise StoreCorrupt(path, f"bozuk JSON -> karantina: {qpath}") from exc
    except OSError as exc:
        qpath = _quarantine_corrupt(path, f"read_error: {exc}")
        raise StoreCorrupt(path, f"okuma hatasi -> karantina: {qpath}") from exc


def _atomic_write_bytes(path: str, data_bytes: bytes) -> CommitReceipt:
    """Ortak atomik yazim: flock -> temp+fsync -> os.replace -> dir fsync -> CommitReceipt.
    Herhangi bir asama basarisizsa StoreError firlar (kismi dosya birakilmaz)."""
    dir_path = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(dir_path, exist_ok=True)
    sha = hashlib.sha256(data_bytes).hexdigest()
    tmp_path = f"{path}.tmp.{os.getpid()}.{int(time.time() * 1e6)}"
    lock_path = f"{path}.lock"
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    _locked = False
    try:
        _locked = _flock_or_degrade(lock_fd, exclusive=True)  # F10: desteklenmezse atla, yazima devam
        try:
            with open(tmp_path, "wb") as f:
                f.write(data_bytes)
                f.flush()
                _fsync_safe(f.fileno())   # F10: ENOSYS'te atla (atomiklik os.replace'te)
            os.replace(tmp_path, path)
            try:
                dir_fd = os.open(dir_path, os.O_RDONLY)
                try:
                    _fsync_safe(dir_fd)
                finally:
                    os.close(dir_fd)
            except OSError:
                pass
        except Exception as exc:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except OSError:
                pass
            raise StoreError(f"Commit basarisiz (fsync/rename): {path}: {exc}") from exc
        finally:
            if _locked:
                _funlock_safe(lock_fd)
    finally:
        os.close(lock_fd)
    return CommitReceipt(path=path, sha256=sha, bytes_written=len(data_bytes),
                         committed_at_ms=int(time.time() * 1000))


def _atomic_commit(path: str, data: Any) -> CommitReceipt:
    """Tek-JSON atomik commit (plan store gibi tek-nesne dosyalar icin)."""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return _atomic_write_bytes(path, payload.encode("utf-8"))


def _atomic_commit_jsonl(path: str, rows: List[Any]) -> CommitReceipt:
    """JSONL (satir-basi-JSON) atomik commit — sinyal/tahmin sicili formatini korur.
    _atomic_commit (tek-dizi-JSON) satir-satir okuyan _load_signals/_fc_yukle'yi
    bozacagi icin AYRI tutulur; dayaniklilik (flock+fsync+replace) ayni."""
    buf = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    return _atomic_write_bytes(path, buf.encode("utf-8"))


# ════════════════════════════════════════════════════════════════════════════
# KONFIGURASYON
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class Config:
    # veri
    # 1000 mum: 4s-ankrajli OOS skill/backtest kapilarinda >=30 etkin kohort
    # birakmak icin 500 yetersizdi (varsayilanla azami 26 kohort).
    kline_limit: int = 1000
    atr_period: int = 14
    # etiketleme (4 saatlik endpoint, uc sinif)
    horizon: int = 16               # ileri ufuk (mum). 15m*16 = 4 saat
    interval_ms: int = 900_000      # 15m; hedef timestamp'i bununla kilitlenir
    price_type: str = "LAST_CLOSE" # istatistiksel hedef fiyat turu
    label_neutral_atr: float = 0.10 # |P[t+h]-P[t]| <= bu*ATR -> FLAT
    barrier_atr: float = 1.2
    # yapi / seviye
    struct_window: int = 60
    pivot_w: int = 2
    range_window: int = 40
    inval_pad_atr: float = 0.30
    entry_buffer_atr: float = 0.20
    min_target_atr: float = 0.7
    # topluluk / secicilik
    knn_k: int = 40
    min_train: int = 120
    disagree_max: float = 0.16      # BLOKLAR-arasi p std esigi (adaptif tabanla birlikte)
    prob_cap: int = 95
    weak_thresh: int = 55
    abstain_prob: float = 0.45       # en yuksek sinif olasiligi bunun altinda -> ABSTAIN
    # R9 (REPORT_3): bes skill tahmincisi 0 agirlik aldiginda havuz yalniz overlay
    # bloklaridir; Estimate.probs() FLAT'i 1/3'e sabitler ve max sinif olasiligi
    # <= (2/3)*(0.5+macro_p_clip) = 0.4667 olur. 0.45 esigi bu tavanin hemen
    # ALTINDADIR: sifir-skill rejim cogunlukla BEKLE'ye duser ama 0.45-0.4667
    # araligi acikti. R3 kapisi (zero_skill_abstain) bu araligi ACIK kurala baglar.
    zero_skill_abstain: bool = True  # R3: skill agirliklarinin TAMAMI 0 ise market acilmaz
    # ══ DENETIM ONARIM FLAGLERI (hepsi varsayilan KAPALI => motor davranisi AYNEN korunur) ══
    fix_meta_label_yon: bool = False      # Sorun1: skill=0 + guclu-uyumlu trendde yon trend-primary'den (meta-labeling)
    fix_zayif_yol_kapisi: bool = False    # Sorun3: guven+uzlasmazlik kapisi oncu/senaryo yoluna da uygulanir
    fix_pusu_donus_muaf: bool = False     # Sorun4: karsi-trend pusu, taze donus teyidinde market ile simetrik
    fix_funding_isaret: bool = False      # Sorun12: funding maliyeti isaret-farkindalikli (odemeyen taraf phantom-maliyet yazmaz)
    fix_gap_tolerans_bar: int = 0         # Sorun7: <=N barlik zaman boslugu tolere edilir (0=eski davranis)
    fix_attach_max_age_ms: int = 0        # Sorun1v: seri degeri bu yastan (ms) eskiyse baglanmaz (0=sinirsiz/eski)
    fix_gap_slip: bool = False            # Sorun8: cozumde bosluk-otesi (open) stop dolumu modellenir
    fix_meta_opp_max: float = 0.55        # Sorun1: meta-label, trende TERS sinif olasiligi bunun ustundeyse DEVREYE GIRMEZ
    #                                  (overlay bloklari yon acamaz — sozlesme). False -> eski davranis.
    min_directional_coverage: float = 0.20
    tie_eps_rel: float = 1e-12
    tie_eps_atr: float = 1e-9
    # EV kapisi (RR+MC yerine TEK kriter)
    ev_min_atr: float = 0.08        # min beklenen-deger (ATR); EV maliyet-SONRASI, bu deger marj
    dir_edge_min: float = 0.05      # MC P(hedef) - P(stop) bunun uzerinde olmali (yon dogrulugu)
    # monte carlo
    mc_paths: int = 3000
    mc_window: int = 300
    mc_drift_k: float = 0.05        # cok hafif akis biasi (panel6'da 0.10 idi -> miknatis baskin)
    mc_recency_tau_div: float = 5.0 # recency tau = nr/bu; buyuk -> son barlar daha baskin
    mc_magnet_k: float = 0.15       # seviye-miknatis adim-basi (ATR frac); driftten baskin
    edge_band_atr: float = 0.8      # kenara bu ATR icinde -> "ucta"
    accept_n: int = 3               # kabul penceresi (mum)
    accept_k: int = 2               # kirilim "kabul" icin gereken kapanis sayisi
    veto_touch_atr: float = 0.25    # mum ekstremi range-ekstreme bu ATR icindeyse "test etti"
    veto_wick_atr: float = 0.75     # bant ucunda bu x ATR'den uzun KARSI-fitil = supurme olcekli reddedilis:
                                    # kapanis zayif kalsa bile o ucu kovalamak yasak (OLCUM: V-DIP seed=20'de
                                    # 0.90 ATR alt fitil + orta kapanis -> dip_rejection tetiklenmedi, SHORT cikti)
    reversal_flag: float = 0.45     # P(stop) bunun ustunde -> DONUS RISKI bayragi
    # tick order-flow (aggTrades)
    aggtrades_limit: int = 1000
    of_buckets: int = 8
    flip_thresh: float = 0.66       # tick radari YON CEVIRME esigi
    veto_thresh: float = 0.66       # ters radar + pozitif karsi-EV yoksa -> BEKLE
    # blok agirliklari (oncu/overlay bloklari; ogrenen+markov+MC skill ile gelir)
    w_flow: float = 0.6
    w_macro: float = 0.6
    w_btc: float = 0.5
    w_mc_cap: float = 1.1
    # ── YON9-EK: ensemble kapisi + yeni veri katmanlari (denetci bulgulari) ──
    ens_gate_minw: float = 1.5      # kapinin devreye girmesi icin asgari toplam tahminci agirligi
    wick_karsit_shrink: float = 0.85  # son mumda karara KARSI supurme-olcekli fitil -> guven kismasi
    funding_settle_warn_min: int = 30  # funding settle'a bu kadar dk kala sinyal uyarisi
    spoof_kayip_oran: float = 0.5   # 2. derinlik orneginde duvarin bu orani kaybolduysa SPOOF suphesi
    spoof_bekle_sn: float = 1.2     # iki derinlik ornegi arasi bekleme (sn)
    slip_depth_notional: float = 5000.0  # derinlikten slippage olcumu icin varsayimsal buyukluk (USDT)
    tasfiye_prem_bps: float = 25.0  # |mark-index| bu bps'i asar + OI dusuyorsa TASFIYE VEKILI uyarisi
    ls_crowd_hi: float = 1.25       # top-trader L/S bu ustunde -> kalabalik LONG (asagi-tilt adayi)
    ls_crowd_lo: float = 0.80       # bu altinda -> kalabalik SHORT (yukari-tilt adayi)
    ls_tilt: float = 0.05           # L/S kalabalik tiltinin buyuklugu (yalniz makro blokaj katmani)
    fc_notr_atr: float = 0.10       # ONCU TAHMIN: MC medyan hareketi bu x ATR altindaysa yon NOTR
    fc_log_max: int = 600           # tahmin sicili dosya tavani (karne icin bol; dosya sismez)
    # log
    signal_horizon_bars: int = 16
    signal_log_max: int = 3000
    min_track_resolved: int = 12    # walk-forward geri-besleme icin min cozulen sinyal
    # ── ADAPTIF ONLINE OZ-KALIBRASYON (gecmis cozulen sinyal loglarindan ogrenilir) ──
    # CLUSTER 1: EV kapisi
    ev_calib_min: int = 20
    ev_calib_k: float = 20.0
    # CLUSTER 2: uzlasmazlik (sidecar dosya)
    disagree_adapt_min: int = 30
    disagree_window: int = 250
    disagree_quantile: float = 0.80
    disagree_shrink_k: float = 40.0
    disagree_ring_max: int = 400
    # CLUSTER 3: donus/flip/veto
    rev_calib_min: int = 20
    rev_calib_k: float = 30.0
    rev_calib_bucket_min: int = 12   # per-strength bucket min (selection-bias fix; Wilson alt-sinir ile birlikte)
    # CLUSTER 4: skor/olasilik kalibrasyonu
    calib_min_resolved: int = 20
    calib_prior_strength: float = 8.0
    calib_shrink_k: float = 20.0
    calib_prob_ceiling: int = 95
    calib_edge_bins: Tuple[float, ...] = (0.10, 0.18, 0.26, 0.34)
    # CLUSTER 5: GOZLEM dogrulama
    gozlem_min_resolved: int = 20
    gozlem_prior_n: int = 4
    # CLUSTER 6: senaryo-HUCRE (scen_cell) isabet olcumu — olu 'scen_cell' alanini canlandirir
    scen_cell_min_resolved: int = 15
    scen_cell_prior_n: int = 4
    # ── ISLEM MALIYETI (arastirma-onayli: Binance USDT-M VIP0) — STRUCTURAL ──
    taker_fee: float = 0.0005       # tek-yon taker (0.05%) — cikis (stop market) tarafi
    maker_fee: float = 0.0002       # tek-yon maker (0.02%) — giris limit-band tarafi
    slip_default_1w: float = 0.0005 # bilinmeyen sembol icin tek-yon cikis-slippage (konservatif)
    decision_entry_order_type: str = "MARKET"  # anlik LONG/SHORT karari; PUSU ayri LIMIT planidir
    decision_exit_order_type: str = "MARKET"
    # ── REPORT_4 #5: GECIKME + KISMI-DOLUM temsili (EV maliyetine konservatif UST-SINIR) ──
    # Gecikme: karar->borsa emri arasi surede fiyat aleyhte yuruyebilir. Beklenen |hareket|
    # ~ ATR * sqrt(gecikme/bar) olceklenir (difuzyon); TAHMIN degil ALEYHTE varsayimli pay:
    # giris ve cikis bacaklarina AYRI AYRI eklenir. 0 -> kapali (eski davranis).
    exec_latency_ms: int = 1500     # karar->emir gecikme varsayimi (sinyal isleme + ag + motor)
    latency_vol_k: float = 1.0      # gecikme payi katsayisi: k * ATR * sqrt(gecikme_ms/bar_ms)
    # Kismi-dolum: MARKET emri defteri yurutur; derinlik OLCULDUYSE (slip_olcum_frac) bu
    # yurutme zaten VWAP kaymasinin icindedir -> ek pay YOK. Derinlik OLCULEMEDIGINDE
    # (defter yok/eksik) sabit tablo kaymasi tam-dolumu varsayar -> tek-yon kaymaya
    # kismi-dolum/yeniden-deneme payi eklenir. 0 -> kapali (eski davranis).
    partial_fill_extra_frac: float = 0.25
    # ── ZAMAN-AZALIMLI OGRENME: ussel recency agirligi (rejim-kosullu degil) ──
    logistic_decay_tau: float = 160.0  # w_i=exp(-(n-1-i)/tau); ~kline/3, yari-omur ~1 gun. 0 -> kapali
    # ── CANLI-ONLY (kullanici direktifi): geciken KALIBRASYON/ESIK dosyalari KARARA GIRMEZ ──
    # Gerekce: dinamik/manipulasyonlu piyasada onceki zaman diliminde olculen esikler bir sonraki
    # dilimde gecersiz olabilir -> gecikmis-veri karari = likidasyon riski. Bu bayrak True iken
    # ev_gate_calib/reversal_calib/calibrate_score/adaptive_disagree_max/scen_cell-bump SABIT canli
    # varsayilanlarina duser; gecmis loglar YALNIZ olcum/telemetri olarak kalir (karari OYNATMAZ).
    # False -> eski (kalibre) davranis (regresyon/mutasyon karsilastirmasi icin korunur).
    canli_only: bool = True
    # ── FABLE6_5 (Anapront denetimi F2/F3/F5 — kullanici sozlesmesi) ──
    pusu_tek_kenar: bool = True          # F2: ayni kosuda TEK bekleyen kenar plani (False=eski cift-kenar)
    scen_risk_gate_enabled: bool = True  # F3: 144-hucre okumasi secilen yone ters ise market yok (yon uydurmaz)
    pusu_canli_giris_onerisi: bool = True  # F5: tetik teyidinde canli fiyat/spread/slip ile giris onerisi
    # ── F9 (kullanici direktifi): SENARYO-YON KAYNAGI ──
    # DURUSTLUK NOTU: bu bayrak 'senaryo yon uydurmaz' (F3) sozlesmesini KULLANICI
    # ISTEGIYLE deler. True iken istatistik topluluk kenari YOKKEN (zero-skill/dusuk-
    # guven/flat/tie/uzlasmazlik) senaryo side_hint'i (LONG/SHORT) yonu URETIR; sonra
    # market/pusu secimi yapilir. Bu sinyallerin KENARI KANITLANMAMISTIR (sentetik
    # veride uretilmeleri gercek-piyasa ustunlugu demek DEGILDIR). Yon KAYNAGI senaryo
    # olsa da veto (dip-short/tepe-long), maliyet, EV, market-kalite, htf ve RR kapilari
    # AYNEN korunur -> ters-yon ve negatif-EV market yine uretilmez. False=eski F3 davranisi.
    scen_yon_enabled: bool = True
    scen_yon_min_herald: int = 0         # >0 ise senaryo-yon icin en az bu kadar haberci sart (0=kapali)
    # ── ONCU-YON (kullanici direktifi): ONCU (leading) SINYAL KARARA GIRER ──
    # DURUSTLUK NOTU: F9 gibi bu da 'kanitlanmamis sinyal parayi yonetmez' (DSR=N/A)
    # sozlesmesini KULLANICI ISTEGIYLE deler. Iki degisiklik birlikte gelir:
    #  (1) GECIKMELI pump/dump (olay 4/5) YON KAYNAGI OLMAKTAN CIKARILDI: classify_scenario
    #      side_hint'i 4/5 icin NEUTRAL doner ve erken_uyari'nin pump/dump oylari kaldirildi
    #      (olay etiketi TELEMETRI olarak kalir; 144-hucre/testler bozulmaz).
    #  (2) ONCU (leading) sinyaller — reversal_radar (tick donus), taze_donus, senaryo
    #      V-DIP/V-TOP/EXH ve sikisma->genisleme — karardan ONCE (PIT-temiz) hesaplanip
    #      istatistik kenar YOKKEN yonu URETIR (F9 senaryo-yonundan ONCE, cunku kullanici
    #      onculere daha cok guvenir); kenar VARKEN teyit/karsi-veto/guven eder ve SEVIYE +
    #      PUSU secimine girer. Tam-surucu olsa da veto/EV/kalite/htf/RR kapilari AYNEN kalir.
    oncu_yon_enabled: bool = True        # istatistik kenar yoksa oncu leading sinyal LONG/SHORT yonu uretir (tam surucu)
    oncu_yon_min_guc: float = 0.50       # yon uretmek/pusu filtresi icin gereken min oncu-guc (0..1; 0.5 = >=1 yonlu kanit)
    oncu_veto_enabled: bool = True       # oncu sinyal secilen yone GUCLU ters ise market BEKLE (yon cevrilmez)
    oncu_veto_min_guc: float = 1.0       # oncu-karsi veto icin guc esigi (1.0 = >=2 yonlu kanit ters)
    oncu_counter_shrink: float = 0.85    # oncu zayifca ters ise (veto esigi alti) gosterilen guveni kis
    oncu_stop_widen: float = 1.25        # sikisma->genisleme (patlama yakin) varken stop payi carpani (market+pusu seviyesine etki)
    oncu_pusu_filtre: bool = True        # guclu oncu sinyal PUSU kenar secimine girer (ters kenar dusurulur)

    # ════════════════════════════════════════════════════════════════════════
    # DINAMIK NORMALIZASYON (yon5) — mutlak "sihirli" esikler yerine veri-goreli olcum.
    # Bu meta-parametreler ISTATISTIKSEL/SEMBOL-BAGIMSIZ (z-skoru / quantile / oran);
    # piyasa-mutlak DEGIL. Mutlak-fallback alanlari YALNIZ cold-start icindir (yeterli
    # gecmis yoksa) ve "kalibre DEGIL" mantigiyla eski davranisi korur. NO-LOOKAHEAD.
    # ════════════════════════════════════════════════════════════════════════
    norm_win: int = 96              # robust-z / percentile geriye-pencere (mum)
    funding_norm_win: int = 96      # F17 fix: funding z-penceresi AYRI isimlendirildi (96 settle
                                    # ~= 32 gun; 15m serilerdeki norm_win=96 ~= 1 gun ile ayni
                                    # "yakin gecmis" DEGILDIR). Varsayilan eski davranisi korur;
                                    # artik bagimsiz ayarlanabilir/belgelidir.
    norm_min_n: int = 24            # bu kadar gecmis yoksa -> mutlak-fallback
    z_extreme: float = 1.5          # "kendi tarihine gore asiri" z esigi (funding/OI/taker)
    z_heavy: float = 1.0            # funding "kalabalik taraf" (d4) z esigi
    # Tip A mutlak-fallback (yalniz z hesaplanamazsa devreye girer)
    oi_chg_fallback: float = 0.003
    price_chg_ref: float = 0.002
    funding_neg_fallback: float = -0.0004
    funding_pos_fallback: float = 0.0004
    taker_hi_fallback: float = 1.05
    taker_lo_fallback: float = 0.95
    funding_long_heavy: float = 0.0004
    funding_short_heavy: float = -0.0004
    funding_flip_floor: float = 0.0001
    htf_slope_floor: float = 0.0008  # htf-trend esigi tabani (uzeri: htf-vol'e adaptif)
    htf_er_strong: float = 0.30      # 1s trendin GUCLU sayilmasi icin yon-verimliligi esigi
    #                                  (2.tur: govdeye gomulu 0.30 idi — yon5 ilkesine aykiriydi)
    # Makro tilt buyuklukleri (eskiden fonksiyon govdesine gomulu isimsiz sabitlerdi)
    tilt_oi_squeeze: float = 0.10
    tilt_oi_long: float = 0.045
    tilt_oi_liq: float = 0.04
    tilt_oi_shortcov: float = 0.04
    tilt_oi_short_cont: float = 0.045  # FABLE6: ayna-simetrik trend katkisi
    #                                   devami' ASAGI tilti (CME: artan OI trendi teyit eder; eski
    #                                   kosulsuz +sikisma tilti funding-koru kontra-LONG biasiydi)
    tilt_funding_neg: float = 0.07
    tilt_funding_pos: float = 0.07
    tilt_taker: float = 0.05
    tilt_imb_k: float = 0.15
    tilt_imb_cap: float = 0.08
    macro_p_clip: float = 0.20      # makro P(up) 0.5'ten sapma siniri
    # Vadeli-rejim (Tip D): ratio dagiliminin KENDI quantile'lari; fallback sabit
    regime_win: int = 50
    regime_min_n: int = 60
    regime_q_ext: float = 0.975
    regime_q_hi: float = 0.90
    regime_q_lo: float = 0.10
    regime_q_comp: float = 0.03
    # Mum-sekli (Tip C): fitil/govde oranlari (isimlendirildi)
    wick_rej_frac: float = 0.45
    body_mid_frac: float = 0.50
    # classify esikleri (isimlendirildi; er/momentum/hacim-z/sfp)
    er_trend_min: float = 0.35
    mb_strong: float = 0.20
    mb_range: float = 0.30
    volz_pump: float = 1.8
    mom_pump: float = 0.8
    volz_exh: float = 2.0
    mom_exh_max: float = 0.4
    volz_herald: float = 1.5
    mom_herald: float = 0.3
    volx_mom_min: float = 2.0
    sfp_reclaim_atr: float = 0.15
    # Order-flow radar (Tip C; z-esikleri zaten sembol-bagimsiz — isimlendirildi)
    climax_z: float = 1.5
    cvd_div_z: float = 0.8
    climax_prox_atr: float = 1.2
    whale_prox_atr: float = 1.5
    of_delta_scale: float = 2.0
    of_delta_gain: float = 0.4
    of_rev_gain: float = 0.12
    btc_lead_gain: float = 0.15
    market_bias_scale: float = 2.0
    # Skor->guven haritalama (Tip E; calibrate_score "kalibre" olunca ETKISIZ kalir)
    conf_dis_pen: float = 2.0
    conf_dis_floor: float = 0.4
    conf_extreme_shrink: float = 0.8
    conf_htf_shrink: float = 0.9    # 1s trendine karsi (zayif/donus) -> gosterilen guveni kis
    # ════════════════════════════════════════════════════════════════════════
    # MIKRO-SENARYO KATALOGU (vadeli+spot KOMBINE; Tip C/D — z/quantile tabanli)
    # 1..144 sparse senaryo-ID alani korunur; bu katman EK bir adlandirilmis-kalip
    # taramasidir: "15m'de fiyat su hareketi yapabilir (ADAY)" dilinde konusur.
    # Endpoint3 kararina DOKUNMAZ; legacy telemetri bagimsiz OOS katkisi sayilmaz.
    # ════════════════════════════════════════════════════════════════════════
    micro_top_n: int = 3            # gosterilecek en guclu kalip sayisi
    micro_min_resolved: int = 10    # kalip-isabet olcumu icin min cozulen sinyal
    micro_prior_n: int = 4          # Beta-prior (kucuk-ornek shrink)
    spot_kline_limit: int = 200     # spot 15m mum (basis z-gecmisi icin yeterli)
    basis_win: int = 96             # basis robust-z penceresi (mum)
    basis_z_hi: float = 1.5         # basis "asiri prim/iskonto" z esigi
    eq_tol_atr: float = 0.15        # esit-tepe/dip kumeleme toleransi (ATR)
    eq_min_touch: int = 2           # havuz icin min dokunus
    inside_min: int = 2             # ust-uste ic-mum (coil) esigi
    nr_lookback: int = 7            # NR7 daralma penceresi
    fvg_min_atr: float = 0.30       # 3-mum dengesizlik boslugu (FVG) min genislik
    wick_cluster_n: int = 3         # ayni-yonde fitil kumesi esigi
    vwap_win: int = 96              # rolling-VWAP penceresi
    vwap_z: float = 1.5             # VWAP'tan uzaklik z esigi (gerilme)
    div_lookback: int = 12          # momentum-iraksama geriye-bakis (mum)
    spotlead_win: int = 8           # spot-mu-vadeli-mi onculuk penceresi (mum)
    absorb_flat_atr: float = 0.25   # absorpsiyon: fiyat-duz esigi (ATR)
    moved_min_atr: float = 0.30     # 'fiyat gercekten hareket etti' esigi (ATR; #15/#17)
    div_mom_delta: float = 0.15     # momentum-iraksama anlamlilik farki (#14)
    # ── ACIK SINYAL YASAM-DONGUSU takibi (gosterim esikleri) ──
    takip_goster_bar: int = 32      # cozulmus sinyali son ~8 saat goster
    takip_yakin_prog: float = 0.70  # 'hedefe yaklasti' yol orani
    takip_dondu_prog: float = 0.35  # yaklastiktan sonra bunun altina dustu -> geri dondu
    takip_be_prog: float = 0.50     # bu orani gecti -> stop girise cekilebilir
    takip_overshoot_atr: float = 0.5  # hedef otesi bu kadar ATR -> delip gecti
    takip_stop_yakin: float = 0.50  # stopa bu yol oraninda yaklasti -> uyari
    # ── REJIM-DINAMIK MOTOR (Paket 1: saha verisi 24/24 LONG + donuste %8 isabet fix) ──
    fhs_lambda: float = 0.94        # FHS: EWMA-vol arindirma (RiskMetrics); rejim donusunde MC aninda adapte
    fhs_min_n: int = 60             # bu kadar getiri yoksa FHS devre disi (ham bootstrap'a duser)
    taze_donus_bars: int = 4        # egilim/rejim donusu son N mum icindeyse 'TAZE DONUS' uyarisi
    taze_donus_mb: float = 0.25     # egilim-isareti donusu icin min |market_bias| (iki tarafta da)
    taze_donus_shrink: float = 0.85 # taze donus penceresinde gosterilen guven carpani
    kayma_win: int = 12             # kayma alarmi: son N cozulmus sinyalin isabeti izlenir
    kayma_esik: float = 0.35        # isabet bunun altina duserse ALARM (motor kendine guveni kisar)
    kayma_shrink: float = 0.80      # alarm aktifken guven carpani
    ext_bar_atr: float = 2.0        # OFORI/KAPITULASYON mumu: son mum TR > bu x ATR ise bant ucunda kovalamak yasak
    monokultur_win: int = 12        # tek-yon uyarisi: son N logdaki sinyal yonu izlenir
    monokultur_pay: float = 0.90    # bu oranin ustunde tek yonse UYARI (24/24 LONG belirtisi)
    # ── BAR-ICI FITIL SIMULASYONU (Brownian-koprusu; arastirma-onayli FIT #1) ──
    # MC eskiden yalniz KAPANIS yolunu gorup fitille yenen stoplari atliyordu
    # (saha: stop yiyen sinyallerde MC ort. p_stop %20, gercek %100). Kopru, iki
    # kapanis arasindaki bar-ici ekstremin bariyeri kesme olasiligini analitik
    # ekler: p = exp(-2(b-x0)(b-x1)/sigma^2). sigma = (ATR/fiyat)/bridge_range_div
    # (Brown hareketinde E[range] ~= 1.6*sigma -> ATR'den turetilir; veri-goreli).
    bridge_range_div: float = 1.6   # 0 veya negatif -> kopru KAPALI (eski davranis)
    # ── SUPURME-DERINLIGI KALIBRASYONU (stop paylari sabit DEGIL, olculur) ──
    # Saha bulgusu: sabit 0.30 ATR pad, olculen supurmelerin ~%35'inin ICINDE kaliyordu
    # (stop tam likidite-avi bolgesinde). Pay artik sembolun KENDI gecmis supurme
    # derinliginin q80'i (kirpilmis); yetersiz ornek -> eski sabit (cold-start korunur).
    sweep_win: int = 40             # 'onceki ekstrem' referans penceresi (mum)
    sweep_reclaim_bars: int = 3     # supurme sayilmasi icin geri-alis penceresi
    sweep_q: float = 0.80           # pay = derinlik dagiliminin bu quantile'i
    sweep_min_n: int = 10           # bu kadar olcum yoksa kalibre DEGIL -> sabit pad
    sweep_pad_cap: float = 1.5      # pay ust siniri (ATR) — risk patlamasin
    # ── KOSULLU PLAN (PUSU) yasam dongusu ──
    plan_tasima_atr: float = 0.10   # yeni pusu seviyesi eskisine bu ATR icindeyse plan TASINIR (bar_ms korunur;
    #                                 aksi halde SURE-DOLDU'ya hic ulasilamazdi — her kosu saati sifirlardi)
    plan_gec_prog: float = 0.25     # ateslenmis plan hedef yolunun bu oranini gectiyse 'GEC KALINDI' (kovalama yasak)
    plan_hist_cap: int = 200        # sonuclanan plan gecmisi tavani (karne olcumu icin yeterli, dosya sismez)
    plan_aktif_max_bars: int = 96   # ateslenmis plan bu kadar 15m mumda hedef/stop'a degmezse ZAMAN-ASIMI:
                                    # kapatilir, karneye SAYILMAZ (yoksa OZET sonsuza dek 'AKTIF!' gosterirdi)
    # ── STEP4B: PUSU KARNE RISK KAPISI (gecmis yon URETMEZ; yalniz yeni pusu riskini kisar) ──
    # Pusu karnesi kotuyse ayni tip yeni bekleyen limit kurulmaz. Bu, market yonu degistirmez
    # ve gecmis basariyi canli karlilik kaniti yapmaz; salt risk/uyari kapisidir. Wilson alt
    # guven siniri kullanilir: kucuk ornekte acimasiz 'nokta oran' secim-biasi yapmasin.
    pusu_karne_gate_enabled: bool = True
    pusu_karne_min_resolved: int = 8
    pusu_karne_bad_wilson: float = 0.18
    # ── STEP4C: MARKET RISK KAPISI (canli-only uyumlu; yon URETMEZ, yalniz asimetrik
    # riskte market emrini BEKLE'ye cevirir). RR burada karlilik kaniti degildir;
    # yapisal risk/fren parametresidir ve Config icinde isimlidir. Cikti bulgusu:
    # RR~0.24 iken 'tek stop ~3-4 kazanci siler' uyarisi varken market aciliyordu.
    market_risk_gate_enabled: bool = True
    market_rr_min: float = 0.35
    market_open_signal_gate_enabled: bool = True  # ayni sembolde acik market sinyali varken yeni market yok
    # ── STEP4E: MARKET KALITE / OLASILIK KAPISI ──
    # fable4_3 saha ciktisi: DOGE'de MC hedef %45 / stop %33, edge %12 ve KARSI-FITIL
    # varken market SHORT uretti. RR iyi gorunse bile hedef olasiligi mutlak olarak dusuk
    # ve stop riski yuksekse bu trade "az ama emin" sozlesmesini bozar. Bu kapi yon
    # URETMEZ; sadece zayif kalitedeki market emrini BEKLE'ye cevirir.
    market_quality_gate_enabled: bool = True
    market_min_target_prob: float = 0.50
    market_max_stop_prob: float = 0.30
    market_min_prob_gap: float = 0.15
    market_counter_wick_gate_enabled: bool = True
    market_counter_wick_min_target: float = 0.55
    market_counter_wick_max_stop: float = 0.25
    # ── STEP4F: CANLI-FIYAT / KAPALI-MUM AYRIMI ──
    # Sinyaller kapali mumla hesaplanir (no-repaint), fakat market/pusu icrasi ANLIK
    # mark/last fiyattan olur. Kapali bar fiyati ile live mark arasinda buyuk ATR farki
    # varsa 'eski gerceklesmis hareketi ilac gibi' kullanmamak icin yeni market/pusu bloklanir.
    live_price_audit_enabled: bool = True
    live_gap_market_gate_enabled: bool = True
    live_gap_pusu_gate_enabled: bool = True
    live_gap_block_atr: float = 0.60
    live_gap_warn_atr: float = 0.25
    live_age_warn_min: float = 18.0
    # STEP4D: ESKI-SURUM / ACIK SINYAL RISK DENETIMI. Canli yon URETMEZ; yalniz
    # onceki kosulardan kalan acik sinyali bugunku Step4 risk kapilarina gore isaretler.
    # Ozellikle fable4_1 oncesi dusuk-RR market sinyalleri raporda normal 'izle' gibi
    # kalmasin; kullanici 'eski riskli sinyal' oldugunu gorsun.
    open_signal_audit_enabled: bool = True
    open_signal_rr_min: float = 0.35
    open_signal_adverse_atr_warn: float = 1.0
    open_signal_resolved_price_gate_enabled: bool = True  # STEP4G: bu kosuda hedef/stop gorulduyse yeni marketi bloklama

    # ── STEP4.8: OLCULEN YON-SAGLIGI / TEK-MARUZIYET KAPILARI ──
    # Canli cikti bulgusu: oncu tahmin karnesi BTC/SOL ~%30, DOGE ~%37 iken
    # ekranda model-tahmini %55-68 gorunebiliyordu. Bu yeni katman gecmis basariyi
    # yon URETMEK icin kullanmaz; yalniz kotu olculmus yon motorunda guveni kapatir
    # veya marketi BEKLE'ye alir. Canli-only ilkeye uygundur: log salt risk kapisidir.
    forecast_truth_min_resolved: int = 12
    forecast_truth_soft_acc: float = 0.45
    forecast_truth_hard_acc: float = 0.40
    forecast_truth_min_band: float = 0.60
    forecast_truth_conf_cap_soft: int = 52
    forecast_truth_conf_cap_hard: int = 50
    # Tek sembolde aktif market/aktif pusu varken yeni pusu yazma; market sinyali varsa
    # pusu store temizlenir. Bu, ETH'de gorulen aktif SHORT + yeni market + ters pusu
    # gibi cift/ters maruziyet durumunu risk kapisina alir.
    single_exposure_gate_enabled: bool = True
    no_new_pusu_when_active_plan: bool = True
    no_pusu_when_market_signal: bool = True
    # ── STEP4.9: MARK/LIVE ZORUNLU DENETIM + FORMAL OPEN SIGNAL / PLAN STORE ──
    # Bu katman mevcut yon/pusu motoruna yeni yon uretmez. Cikti ve yasam-dongusu sozlesmesini
    # resmilestirir: live veri dogrulanamiyorsa market emir bloklanir; acik sinyal/plan varken
    # yeni zit sinyal kor-kurulmaz; her eylem audit_log'a yazilir.
    mark_live_required_for_market: bool = True
    # STEP5: data_freshness_seconds artik kapali bar yasi degil, mark price orneginin
    # yerel kosu anina gore yasidir. Kapali bar yasi ayri last_closed_bar_age_seconds
    # alanina yazilir; boylece 2-3 dk bar yasi "taze mark" gibi yorumlanmaz.
    mark_live_warn_stale_seconds: int = 60
    mark_live_max_data_age_seconds: int = 60
    pusu_live_gap_blocks_existing_advice: bool = True
    forecast_red_quarantine_enabled: bool = True
    forecast_red_quarantine_conf_cap: int = 45
    open_signal_store_enabled: bool = True
    plan_store_v2_enabled: bool = True
    plan_store_v2_audit_cap: int = 120
    plan_store_v2_expire_bars: int = 16
    # ── CPCV / PBO — OFFLINE OVERFIT OLCUMU (Lopez de Prado CSCV) ──
    # Kullanim: python fable6.py cpcv [SEMBOL|sentetik] [fast] — OAT varyantlari
    # icin kismi overfit tanisi; formal trial-registry PBO degildir.
    cpcv_blocks: int = 8            # CSCV blok sayisi S (tam mod: C(8,4)=70 bolunme)
    cpcv_blocks_fast: int = 6       # fast mod: C(6,3)=20 bolunme
    cpcv_rows_per_block: int = 24   # blok basina satir (tam: 8x24=192 satir/karar-noktasi)
    cpcv_rows_per_block_fast: int = 16  # fast: 6x16=96 satir
    cpcv_stride: int = 16           # ana kohort: 4s hedefler ortusmez
                                    # pencereleri (H bar) ortusur -> orneklem siser ve
                                    # purge tum egitimi yerdi; stride hem ortusmeyi
                                    # seyreltir hem purge'u satir olcegine kucultur
    cpcv_knobs: Tuple[str, ...] = ("barrier_atr", "ev_min_atr",
                                   "mc_magnet_k", "reversal_flag")   # varyant eksenleri
    cpcv_mults: Tuple[float, ...] = (0.8, 1.2)  # OAT carpanlari -> 1 taban + 4x2 = 9 varyant
                                    # (kartezyen 81 BILEREK yok: decide pahali; OAT 9-15 hedefi)
    cpcv_mc_paths: int = 800        # cpcv icinde MC yol sayisi (olcum: sure mc_paths'e ~duyarsiz)
    cpcv_mc_paths_fast: int = 400
    cpcv_hist_cap: int = 320        # decide'a verilen GECMIS penceresi (maliyet siniri;
                                    # yalniz gecmisi kisaltir, gelecege dokunmaz -> no-lookahead)
    cpcv_min_sinyal: int = 30       # en aktif varyantin sinyali bunun altinda -> KALIBRE DEGIL
    cpcv_min_split: int = 10        # gecerli bolunme bunun altinda -> KALIBRE DEGIL
    cpcv_sent_seed: int = 4041      # sentetik kanit serisi sabit tohumu (deterministik)
    cpcv_sent_trend: float = -0.002 # sentetik seri: hafif dusus (motor sinyal uretebilsin)
    cpcv_sent_vol: float = 0.012

    # ── STEP4: BTC BAS-AT / LIDER TEMPO KATMANI (kanit-disiplinli, canli-only uyumlu) ──
    # BTC dogrudan 5. islem ati DEGILDIR. Altcoin dort-at skorunu yalniz kosullu
    # tempo/confirm/veto/risk olarak etkiler. Yeni sabitler karlilik kaniti DEGIL;
    # hepsi isimli Config parametresi + rolling/robust-z/quantile olcumune baglidir.
    btc_leader_enabled: bool = True
    btc_core_symbol: str = "BTCUSDT"
    btc_corr_win: int = 96
    btc_corr_min_n: int = 30
    btc_beta_win: int = 96
    btc_beta_min_n: int = 30
    btc_leadlag_win: int = 96
    btc_leadlag_min_n: int = 30
    btc_leadlag_lags: Tuple[int, ...] = (1, 2, 3, 4)
    btc_metric_norm_win: int = 160
    btc_metric_norm_min_n: int = 40
    btc_leader_z_hi: float = 1.0
    btc_leader_q_hi: float = 0.75
    btc_confirm_cap: float = 0.08      # BTC teyidinin p_up'a azami katkisi (yon URETMEZ)
    btc_risk_penalty_cap: float = 0.10 # gosterilen guven icin azami risk kismasi
    btc_hard_veto_min_confirm: int = 4 # ters liderlik icin gereken bagimsiz kanit sayisi
    btc_soft_veto_min_confirm: int = 3
    btc_decorrelation_min_confirm: int = 3
    btc_vol_spike_z: float = 1.0
    btc_oi_stress_z: float = 1.0
    btc_funding_stress_z: float = 1.0
    btc_taker_stress_z: float = 1.0
    btc_eth_major_profile: bool = True # ETH'de hard-veto daha kosullu; BTC tek-lider varsayilmaz

    # FABLE6 protokol/defter
    protocol_id: str = "fable6-endpoint3c-v1"
    # F10 (canli telefon bulgusu): 120sn butcesi, telefon 4 sembolu SIRAYLA (her biri agir
    # MC) islerken son sembolleri (SOL/DOGE) her kosuda LATENCY_GATE'e dusuruyordu — oysa
    # 15m bar hala GECERLI (yeni mum kapanmamis). 6 dakika, 15m barin ORTASINDAN once olup
    # tazeligi korur; giris-fiyati kaymasi AYRI live-price-gap kapisiyla zaten denetlenir.
    ledger_max_latency_ms: int = 360_000
    require_exact_target_timestamp: bool = True
    offline_nonoverlap_stride: int = 16
    bootstrap_reps: int = 1000
    skill_min_oos: int = 20
    skill_mc_min_oos: int = 12
    backtest_min_effective: int = 30
    # ── ERKEN UYARI KATMANI (S3): karar kapisi DEGIL; salt AYRI uyari + olcum ──
    # Olusacak pump/dump/V-donus/trend-degisimini MEVCUT dedektorlerden (taze_donus,
    # reversal_radar, senaryo olaylari, vol-rejim gecisi, mikro OI-flush/squeeze-yakiti)
    # + ONCEKI kosunun forecast/ledger kaymasindan toplayip 15-30dk RISKI olarak basar.
    # KANITLANMAMIS: kesinlik degil olasilik/uyari; DSR=N/A disiplini gecerli. Yon URETMEZ.
    erken_uyari_enabled: bool = True
    erken_uyari_lookahead_bars: int = 2   # 1 mum ~= 15dk, 2 mum ~= 30dk (olcum ufku)
    erken_uyari_min_kanit: int = 2        # bu kadar BAGIMSIZ kanit toplanmadan uyari basilmaz
    erken_uyari_move_atr: float = 1.0     # olcumde 'gercekten hareket etti' esigi (ATR)
    erken_uyari_log_max: int = 600        # uyari sicili dosya tavani
    # ── F11 (YÖNTEM.txt tamiri): BEKLENTI (E_net/Sharpe/Kelly) TELEMETRI KATMANI ──
    # DURUSTLUK/KAPSAM: bu katman SALT OLCUM/GOSTERIMDIR. Karar (yon/EV/kapi), boyutlandirma
    # ve DSR=N/A sozlesmesi DEGISMEZ; hicbir alani decide()/gate'e beslenmez (karar-degismezligi
    # selftest'te [YONTEM] blogunda kanitlanir). YÖNTEM.txt tezi: teshis metrigi yon-isabeti (p)
    # DEGIL, maliyet-sonrasi beklenti E_net + risk-normalize (Sharpe) + Kelly f*'tir. Ham veri
    # (net_r, edge, p_target, ledger) zaten uretiliyordu; bu katman onu R-birimi teshise cevirir.
    yontem_expectancy_enabled: bool = True   # E_net/Kelly/(p,b,c,p*_c) teshis karti (salt gosterim)
    yontem_kelly_fraction: float = 0.25      # ceyrek-Kelly gosterimi (kestirim hatasi; SADECE kart)
    yontem_regime_enet_enabled: bool = True  # rejim-kosullu E_net tablosu (analiz_metni)
    yontem_ece_enabled: bool = True          # ECE + reliability binleri (ledger; Brier zaten var)
    yontem_ece_bins: int = 10                # reliability decile sayisi
    yontem_wilson_z: float = 1.96            # iki-tarafli Wilson CI (%95); legacy oran kartlari
    yontem_ortho_enabled: bool = True        # blok-ortogonallik tanisi (mean|corr|); salt telemetri
    yontem_ortho_min_n: int = 20             # blok-serisi bu kadar dolmadan mean|corr| YETERSIZ
    yontem_ortho_corr_hi: float = 0.5        # |corr| bu ustundeyse 'sahte-confluence riski' bayragi
    yontem_ortho_log_max: int = 400          # blok yonsel serisi dosya tavani
    # KIRMIZI TEST (offline komut 'kirmizitest'): KT-1 random-entry null, KT-2 p-yeterlilik,
    # KT-4 shuffle/shift sizinti. decide()'a DOKUNMAZ; ayri offline yol. Sonuc GEC/KAL telemetri.
    kirmizi_n_perm: int = 1000               # KT-1 random-entry permutasyon sayisi
    kirmizi_pctl: float = 0.95               # gercek E_net bu persantili asmali (KT-1 gecme)
    kirmizi_sent_n: int = 900                # sentetik seri uzunlugu (offline deterministik)
    kirmizi_sent_seed: int = 7331            # sentetik tohum (deterministik)


@dataclass(frozen=True)
class DecisionContext:
    """Karar motorunun dis dunya ile temas sozlesmesi.

    OFFLINE baglaminda dosya/store, canli mark, gecmis dashboard kalibrasyonu ve
    stateful yasam-dongusu kapilari okunmaz. Bu ayrim backtest'in bugunku canli
    duruma baglanmasini onler.
    """
    mode: str = "LIVE"                    # LIVE | OFFLINE
    apply_live_gates: bool = True
    apply_stateful_gates: bool = True
    predicted_at_ms: Optional[int] = None

    @classmethod
    def offline(cls, predicted_at_ms: Optional[int] = None) -> "DecisionContext":
        return cls("OFFLINE", False, False, predicted_at_ms)

    def validate(self) -> "DecisionContext":
        if self.mode not in ("LIVE", "OFFLINE"):
            raise ValueError("DecisionContext.mode LIVE veya OFFLINE olmali")
        if self.mode == "OFFLINE" and (self.apply_live_gates or self.apply_stateful_gates):
            raise ValueError("OFFLINE baglaminda live/stateful kapilar acik olamaz")
        return self


# ── ISLEM MALIYETI: isimli emir turleri + iki-yon derinlik/slippage (mutlak fiyat) ──
# Ana karar varsayilan MARKET/MARKET'tir; pusu LIMIT plani ayri katmandir.
# ESKI model (2x taker + 2x slip) 15m ATR'ye gore maliyeti ~2-3x sisiriyordu ve EV kapisiyla
# birlesince sinyal uretimini fiilen kilitliyordu (canli olcum: BTC esik %143·ATR, max EV negatif).
SLIP_1W = {"BTC": 0.0001, "ETH": 0.0001, "SOL": 0.0003, "DOGE": 0.0003}  # tek-yon slippage (cikis)


def txn_cost_abs(symbol: str, price: float, cfg: "Config", book=None,
                 side: Optional[str] = None,
                 entry_order_type: Optional[str] = None,
                 exit_order_type: Optional[str] = None,
                 atr: Optional[float] = None) -> float:
    """Yon-farkindalikli gidis-donus komisyon + kayma (fiyat birimi).

    Main karar MARKET ise giris maker varsayilmaz. Derinlik varsa LONG icin BUY->SELL,
    SHORT icin SELL->BUY aynen olculur; iki taraf ortalamasi kullanilmaz.
    REPORT_4 #5: atr verilirse karar->emir GECIKME payi (k*ATR*sqrt(gecikme/bar), bacak
    basina) eklenir; derinlik OLCULEMEYEN bacaklarin sabit-tablo kaymasina KISMI-DOLUM
    payi (partial_fill_extra_frac) eklenir. Olculen derinlik kaymasi defter-yurutmeyi
    zaten icerdiginden ek pay almaz. atr=None -> gecikme payi 0 (eski cagri uyumu).
    """
    sym = (symbol or "").upper().replace("USDT", "").replace("_", "").replace("PERP", "")
    base_slip = SLIP_1W.get(sym, cfg.slip_default_1w)
    entry_order_type = (entry_order_type or cfg.decision_entry_order_type).upper()
    exit_order_type = (exit_order_type or cfg.decision_exit_order_type).upper()
    side = (side or "LONG").upper()
    entry_side, exit_side = (("BUY", "SELL") if side == "LONG" else ("SELL", "BUY"))
    _pf = max(0.0, getattr(cfg, "partial_fill_extra_frac", 0.0))
    slips = []      # (tek-yon kayma, olculen-derinlik-mi)
    if book is not None:
        try:
            for s in (entry_side, exit_side):
                m = slip_olcum_frac(book, cfg.slip_depth_notional, s)
                slips.append((max(base_slip, m if m is not None else base_slip),
                              m is not None))
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            sys.stderr.write(f"[UYARI] derinlik-kayma olculemedi: {exc}\n")
    if not slips:
        slips = [(base_slip, False), (base_slip, False)]
    slip_sum = sum(sl * (1.0 if measured else 1.0 + _pf) for sl, measured in slips)
    fee_in = cfg.maker_fee if entry_order_type == "LIMIT" else cfg.taker_fee
    fee_out = cfg.maker_fee if exit_order_type == "LIMIT" else cfg.taker_fee
    exit_half_spread = 0.0
    if book is not None:
        try:
            exit_half_spread = max(0.0, float(book.get("spread", 0.0))) / 2.0
        except (TypeError, ValueError, AttributeError):
            exit_half_spread = 0.0
    latency_pad = 0.0
    _lat_ms = max(0, getattr(cfg, "exec_latency_ms", 0))
    _lat_k = max(0.0, getattr(cfg, "latency_vol_k", 0.0))
    if atr is not None and atr > 0 and _lat_ms > 0 and _lat_k > 0 and cfg.interval_ms > 0:
        # giris + cikis bacaklari ayri gecikme yasar -> 2x (alehte varsayim, ust-sinir)
        latency_pad = 2.0 * _lat_k * atr * math.sqrt(_lat_ms / cfg.interval_ms)
    return (fee_in + fee_out + slip_sum) * price + exit_half_spread + latency_pad


# ════════════════════════════════════════════════════════════════════════════
# VERI MODELI
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    oi: Optional[float] = None
    taker: Optional[float] = None
    close_ms: Optional[int] = None
    quote_volume: float = 0.0
    trade_count: int = 0
    taker_buy_base: float = 0.0
    taker_buy_quote: float = 0.0
    oi_value: Optional[float] = None
    taker_buy_vol: Optional[float] = None
    taker_sell_vol: Optional[float] = None


@dataclass
class OrderFlow:
    cvd: float = 0.0
    delta_z: float = 0.0
    buckets_delta: List[float] = field(default_factory=list)
    buckets_price: List[float] = field(default_factory=list)
    whale_delta: float = 0.0
    sell_climax_z: float = 0.0
    buy_climax_z: float = 0.0
    n: int = 0


@dataclass
class Snapshot:
    symbol: str
    candles: List[Candle]
    htf: List[Candle] = field(default_factory=list)
    orderflow: Optional[OrderFlow] = None
    book: Optional[Dict[str, float]] = None
    funding: Optional[float] = None
    funding_hist: Optional[List[float]] = None
    taker_ratio: Optional[float] = None
    spot: Optional[List[Candle]] = None   # SPOT 15m mumlari (basis/iraksama; yoksa None -> katman susar)
    premium: Optional[Dict] = None        # premiumIndex: mark/index fiyat, predicted funding, settle zamani
    ls_top: Optional[float] = None        # top-trader Long/Short pozisyon orani (15m, son)
    ls_global: Optional[float] = None     # global hesap Long/Short orani (15m, son)
    book2: Optional[Dict[str, float]] = None  # ikinci derinlik ornegi (spoof kontrolu; yoksa katman susar)
    # STEP4F: kapali-mum sinyali ile CANLI icra fiyatini ayir.
    # Mumlar raw[:-1] ile kapali barlardan olusur (no-repaint); live_price ise
    # premiumIndex.markPrice'dir. Fark buyukse eski kapali fiyatla market/pusu kurulmaz.
    live_price: Optional[float] = None
    live_server_ms: Optional[int] = None
    live_fetched_ms: Optional[int] = None  # STEP5: REST cevabinin yerel alinma ani; freshness bununla olculur
    last_closed_ms: Optional[int] = None
    stale: bool = False
    predicted_at_ms: Optional[int] = None
    data_watermark_ms: Optional[int] = None
    source_times: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    source_errors: List[str] = field(default_factory=list)


@dataclass
class Estimate:
    name: str
    p_up: float
    weight: float
    n: int
    note: str = ""
    block: str = "learn"       # learn | mc | streak | flow | macro | btc
    p_down: Optional[float] = None
    p_flat: float = 0.0

    def probs(self) -> Tuple[float, float, float]:
        """(DOWN, FLAT, UP); eski ikili katmanlari geriye uyumlu donusturur."""
        up = _clip(float(self.p_up), 0.0, 1.0)
        if self.p_down is None and self.p_flat == 0.0:
            # Directional overlay FLAT hakkinda bilgi tasimaz; 1/3 notr kutleyi
            # ezmeden kalan 2/3'u eski down/up gorusune dagitir.
            return normalize_probs((2.0 / 3.0) * (1.0 - up), 1.0 / 3.0,
                                   (2.0 / 3.0) * up)
        flat = _clip(float(self.p_flat), 0.0, 1.0)
        down = (1.0 - up - flat) if self.p_down is None else float(self.p_down)
        down = _clip(down, 0.0, 1.0)
        z = down + flat + up
        if z <= 0:
            return (1.0 / 3.0,) * 3
        return down / z, flat / z, up / z


@dataclass
class BtcLeaderState:
    """STEP4 BTC bas-at katmani.

    BTC burada 5. islem ati degil; altcoin dort-at skorunun USTUNDE calisan
    lider-tempo/risk/confirm/veto tanisidir. Alanlar canli bar verisinden
    hesaplanir; gecmis isabet/karlilik canli yon uretmez.
    """
    mode: str = "BTC_DATA_INSUFFICIENT"  # CONFIRM | VETO | IGNORE | RISK_ONLY | DECORRELATION_RISK | DATA...
    side: int = 0                         # BTC tempo yonu: +1 LONG baski, -1 SHORT baski, 0 notr
    strength: float = 0.0                 # 0..1; robust-z/quantile ile olculen liderlik
    corr: Optional[float] = None
    corr_z: Optional[float] = None
    beta: Optional[float] = None
    beta_z: Optional[float] = None
    leadlag: Optional[float] = None
    leadlag_q: Optional[float] = None
    btc_vol_z: Optional[float] = None
    alt_vol_z: Optional[float] = None
    decorrelation_risk: float = 0.0
    risk_penalty: float = 0.0
    confirm_adj: float = 0.0              # p_up'a sinirli katkı; yon uretmez
    quality: float = 0.0
    reasons: List[str] = field(default_factory=list)


# ════════════════════════════════════════════════════════════════════════════
# TEMEL MATEMATIK
# ════════════════════════════════════════════════════════════════════════════
def mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def std(xs: List[float], mu: Optional[float] = None) -> float:
    if len(xs) < 2:
        return 0.0
    m = mu if mu is not None else mean(xs)
    return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5


def _tanh(x: float) -> float:
    if x > 20:
        return 1.0
    if x < -20:
        return -1.0
    e = math.exp(2 * x)
    return (e - 1) / (e + 1)


def _net_r(gross_abs: float, cost: Optional[float], risk: float
           ) -> Tuple[Optional[float], Optional[float]]:
    """F4 (FABLE6_5): maliyet-SONRASI net sonuc. gross_abs = fiyat-birimi BRUT PnL,
    risk = |giris-stop| > 0. cost None (eski kayit, maliyet bilinmiyor) -> (None, None):
    brut kayit netmis gibi SUNULMAZ. Doner: (net_abs, net_r)."""
    if cost is None or risk <= 0:
        return None, None
    na = gross_abs - float(cost)
    return na, na / risk


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


CLASSES: Tuple[int, int, int] = (-1, 0, 1)


def _softmax(zs: List[float]) -> List[float]:
    if not zs:
        return []
    m = max(zs)
    es = [math.exp(_clip(z - m, -700.0, 700.0)) for z in zs]
    s = sum(es)
    return [e / s for e in es] if s > 0 else [1.0 / len(zs)] * len(zs)


def normalize_probs(p_down: float, p_flat: float, p_up: float,
                    floor: float = 1e-9) -> Tuple[float, float, float]:
    vals = [max(floor, float(p_down)), max(floor, float(p_flat)), max(floor, float(p_up))]
    z = sum(vals)
    return vals[0] / z, vals[1] / z, vals[2] / z


def sign_eps(x: float, scale: float = 1.0, rel: float = 1e-12,
             abs_eps: float = 0.0) -> int:
    eps = max(abs_eps, rel * max(1.0, abs(scale)))
    return 1 if x > eps else (-1 if x < -eps else 0)


def argmax_class(probs: Tuple[float, float, float], eps: float = 1e-12) -> int:
    """Olasilik tepesinde esitlik varsa yon zorlamaz, FLAT doner."""
    ps = normalize_probs(*probs)
    m = max(ps)
    winners = [i for i, p in enumerate(ps) if abs(p - m) <= eps]
    return CLASSES[winners[0]] if len(winners) == 1 else 0


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def _sha256_obj(obj: Any) -> str:
    return hashlib.sha256(_stable_json(obj).encode("utf-8")).hexdigest()


def config_hash(cfg: Config) -> str:
    return _sha256_obj(asdict(cfg))


def feature_hash() -> str:
    return _sha256_obj({"features": FEATURES if "FEATURES" in globals() else (),
                        "target": "endpoint3", "version": 1})


_CODE_HASH_CACHE: Optional[str] = None


def code_hash() -> str:
    global _CODE_HASH_CACHE
    if _CODE_HASH_CACHE is None:
        try:
            h = hashlib.sha256()
            with open(os.path.abspath(__file__), "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            _CODE_HASH_CACHE = h.hexdigest()
        except OSError:
            _CODE_HASH_CACHE = _sha256_obj({"engine": "fable6", "fallback": True})
    return _CODE_HASH_CACHE


def model_hash(cfg: Config) -> str:
    # Dosyanin tamamini okumadan, karar sozlesmesi + kod surumuyle kararlı nesil kimligi.
    return _sha256_obj({"protocol": cfg.protocol_id, "config": config_hash(cfg),
                        "code": code_hash(),
                        "engine": "fable6-multiclass-softmax-v1"})


def validate_config(cfg: Config) -> None:
    if cfg.price_type != "LAST_CLOSE":
        raise ValueError("FABLE6 bu surumde price_type=LAST_CLOSE ile kilitlidir")
    if cfg.horizon <= 0 or cfg.interval_ms <= 0:
        raise ValueError("horizon ve interval_ms pozitif olmali")
    if not (0.0 <= cfg.label_neutral_atr and 0.0 < cfg.abstain_prob < 1.0):
        raise ValueError("neutral bant/abstain esigi gecersiz")
    if not (0.0 <= cfg.min_directional_coverage <= 1.0):
        raise ValueError("min_directional_coverage 0..1 olmali")
    if cfg.skill_min_oos <= 0 or cfg.skill_mc_min_oos <= 0 or cfg.backtest_min_effective <= 0:
        raise ValueError("OOS/backtest asgari ornek sayilari pozitif olmali")
    if cfg.offline_nonoverlap_stride < cfg.horizon:
        raise ValueError("offline_nonoverlap_stride hedef ufkundan kisa olamaz")
    if (cfg.exec_latency_ms < 0 or cfg.latency_vol_k < 0
            or cfg.partial_fill_extra_frac < 0):
        raise ValueError("gecikme/kismi-dolum maliyet parametreleri negatif olamaz")


def snapshot_pit_violations(snap: Snapshot, cfg: Config,
                            predicted_at_ms: Optional[int]) -> List[str]:
    bad: List[str] = []
    times = [c.close_ms for c in snap.candles if c.close_ms is not None]
    if len(times) != len(snap.candles):
        bad.append("mum close_ms eksik")
    if any(b <= a for a, b in zip(times, times[1:])):
        bad.append("mum zamanlari artan/tekil degil")
    if times and snap.last_closed_ms is not None and snap.last_closed_ms != times[-1]:
        bad.append("last_closed_ms son mumla uyusmuyor")
    if any(b - a != cfg.interval_ms for a, b in zip(times, times[1:])):
        bad.append("kullanilan 15m gecmisinde zaman boslugu var")
    htimes = [c.close_ms for c in snap.htf if c.close_ms is not None]
    if len(htimes) != len(snap.htf) or any(b <= a for a, b in zip(htimes, htimes[1:])):
        bad.append("4s mum zamanlari eksik/artan degil")
    if any(b - a != 16 * cfg.interval_ms for a, b in zip(htimes, htimes[1:])):
        bad.append("kullanilan 4s gecmisinde zaman boslugu var")
    if predicted_at_ms is not None and times and times[-1] > predicted_at_ms:
        bad.append("kapanmamis/gelecek mum kullanildi")
    origin = snap.last_closed_ms or (times[-1] if times else None)
    if (predicted_at_ms is not None and snap.data_watermark_ms is not None and
            snap.data_watermark_ms > predicted_at_ms):
        bad.append("data_watermark tahminden sonra")
    if predicted_at_ms is not None:
        for name, meta in snap.source_times.items():
            av = meta.get("available_time") if isinstance(meta, dict) else None
            ev = meta.get("event_time") if isinstance(meta, dict) else None
            role = meta.get("role", "direction") if isinstance(meta, dict) else "direction"
            if isinstance(av, (int, float)) and av > predicted_at_ms:
                bad.append(f"{name} available_time tahminden sonra")
            if isinstance(ev, (int, float)) and ev > predicted_at_ms:
                bad.append(f"{name} event_time tahminden sonra")
            if (role == "direction" and origin is not None and
                    isinstance(ev, (int, float)) and ev > origin):
                bad.append(f"{name} event_time hedef origininden sonra")
    return bad


# ── DINAMIK NORMALIZASYON YARDIMCILARI (yon5; mutlak esik -> veri-goreli) ─────
def robust_z(hist: List[float], x: float, min_n: int) -> Optional[float]:
    """x'i SALT-GECMIS hist dagilimina gore robust-z'ler (median/MAD, aykiriya dayanikli).
    hist SADECE gecmis degerler icermeli (no-lookahead cagirana ait). Yetersiz -> None
    (cagiran mutlak-fallback'e duser). MAD=0 ise std'e duser.
    F8 fix: cift n'de GERCEK medyan (iki ortanin ortalamasi) — hem medyan hem MAD icin
    (eski ust-medyan sistematik kucuk-orneklem biasi).
    F6 fix: gecmis SABIT (MAD=0 ve std=0) iken x medyandan farkliysa 0.0 yerine None
    doner; boylece belgelenmis mutlak-esik fallback'i gercekten devreye girer (asiri
    deger dejenere gecmise karsi sessizce 'sinyalsiz' sayilmaz)."""
    if not hist or len(hist) < min_n:
        return None
    s = sorted(hist)
    n = len(s)
    med = 0.5 * (s[(n - 1) // 2] + s[n // 2])
    dev = sorted(abs(v - med) for v in hist)
    mad = 0.5 * (dev[(n - 1) // 2] + dev[n // 2])
    if mad > 0:
        return (x - med) / (1.4826 * mad)
    sd = std(hist)
    if sd > 1e-12:
        return (x - med) / sd
    return 0.0 if abs(x - med) <= 1e-12 * max(1.0, abs(med)) else None


def _change_series(vals: List[float], lag: int = 3) -> List[float]:
    """vals ham serisinden (k vs k-lag) goreli-degisim serisi — OI/oran momentumu icin."""
    return [(vals[i] - vals[i - lag]) / vals[i - lag]
            for i in range(lag, len(vals)) if vals[i - lag] > 0]


def true_range(c: Candle, prev: Optional[Candle]) -> float:
    if prev is None:
        return max(c.high - c.low, 0.0)
    return max(c.high - c.low, abs(c.high - prev.close), abs(c.low - prev.close))


def atr_series(cs: List[Candle], period: int) -> List[float]:
    out = [0.0] * len(cs)
    trs: List[float] = []
    for i in range(len(cs)):
        trs.append(true_range(cs[i], cs[i - 1] if i > 0 else None))
        seg = trs[-period:] if len(trs) >= period else trs
        out[i] = mean(seg)
    return out


def efficiency_ratio(cs: List[Candle], i: int, n: int = 10) -> float:
    if i < n:
        return 0.0
    net = abs(cs[i].close - cs[i - n].close)
    tot = sum(abs(cs[k].close - cs[k - 1].close) for k in range(i - n + 1, i + 1))
    return (net / tot) if tot > 1e-12 else 0.0


# ════════════════════════════════════════════════════════════════════════════
# YAPI / SEVIYE
# ════════════════════════════════════════════════════════════════════════════
def swing_points(cs: List[Candle], w: int) -> Tuple[List[float], List[float]]:
    highs, lows = [], []
    for i in range(w, len(cs) - w):
        h = cs[i].high
        if all(h >= cs[j].high for j in range(i - w, i + w + 1)) and \
           any(h > cs[j].high for j in range(i - w, i + w + 1) if j != i):
            highs.append(h)
        lo = cs[i].low
        if all(lo <= cs[j].low for j in range(i - w, i + w + 1)) and \
           any(lo < cs[j].low for j in range(i - w, i + w + 1) if j != i):
            lows.append(lo)
    return highs, lows


@dataclass
class Structure:
    price: float
    atr: float
    range_low: float
    range_high: float
    swing_highs: List[float]
    swing_lows: List[float]
    valid: bool


def build_structure(cs: List[Candle], cfg: Config) -> Structure:
    price = cs[-1].close
    a = atr_series(cs, cfg.atr_period)[-1]
    win = cs[-cfg.range_window:] if len(cs) > cfg.range_window else cs
    rl = min(c.low for c in win)
    rh = max(c.high for c in win)
    sw = cs[-cfg.struct_window:] if len(cs) > cfg.struct_window else cs
    sh, sl = swing_points(sw, cfg.pivot_w)
    valid = a > 0 and rh > rl
    return Structure(price, a, rl, rh, sorted(sh), sorted(sl), valid)


def htf_bias(htf: List[Candle], cfg: Optional[Config] = None) -> int:
    if len(htf) < 10:
        return 0
    closes = [c.close for c in htf]
    a = mean(closes[-5:])
    b = mean(closes[-min(20, len(closes)):])
    # Esik SABIT %0.08 DEGIL: htf-oynakligina adaptif (taban=htf_slope_floor). Sakin
    # piyasada kucuk MA-farki trenddir, calkantida degil -> sembol/rejim-goreli.
    floor = cfg.htf_slope_floor if cfg else 0.0008
    rets = [abs(closes[i] / closes[i - 1] - 1.0) for i in range(1, len(closes)) if closes[i - 1] > 0]
    typ = mean(rets[-20:]) if rets else 0.0
    thr = max(floor, 0.5 * typ)
    if a > b * (1.0 + thr):
        return 1
    if a < b * (1.0 - thr):
        return -1
    return 0


def htf_trend(htf: List[Candle], cfg: Optional[Config] = None) -> Tuple[int, bool]:
    """4 SAATLIK (ust-zaman) trend yonu + GUCLU mu. dir: -1/0/+1. 'hesap 4s+15m' filtresi.
    Guclu = 5-vs-20 MA yonu (htf_bias) + 1s yon-verimliligi (efficiency ratio) yeterli -> gurultu elenir."""
    if len(htf) < 20:
        return 0, False
    d = htf_bias(htf, cfg)
    if d == 0:
        return 0, False
    er = efficiency_ratio(htf, len(htf) - 1, 10)
    return d, er >= (cfg.htf_er_strong if cfg else 0.30)


def _accepted_break(cs: List[Candle], level: float, side: str, n: int, k: int) -> bool:
    """side='dn': son n mumun >=k kapanisi level ALTINDA -> kirilim KABUL edildi (fitil degil).
    side='up': >=k kapanis level USTUNDE. Taze fitil-dip 'kabul' sayilmaz -> V-donus adayi."""
    seg = cs[-n:] if len(cs) >= n else cs
    if side == "dn":
        return sum(1 for c in seg if c.close < level) >= k
    return sum(1 for c in seg if c.close > level) >= k


def _dip_rejection(cs: List[Candle], cfg: Optional[Config] = None) -> bool:
    """Destekte REDDEDILIS: hammer (uzun alt fitil, kapanis ust yaride) veya kisa-vade reclaim
    (kapanis 3 mum oncesinden yukarida). -> taze V-donus adayi; SHORT'lanmamali."""
    c = cs[-1]
    rng = c.high - c.low
    if rng <= 0:
        return False
    wf = cfg.wick_rej_frac if cfg else 0.45
    bf = cfg.body_mid_frac if cfg else 0.50
    lower_wick = min(c.open, c.close) - c.low
    hammer = lower_wick > wf * rng and c.close > c.low + bf * rng
    reclaim = len(cs) >= 4 and c.close > cs[-4].close
    return hammer or reclaim


def _top_rejection(cs: List[Candle], cfg: Optional[Config] = None) -> bool:
    """Direncte REDDEDILIS: shooting-star (uzun ust fitil, kapanis alt yaride) VEYA
    kisa-vade asagi-reclaim (kapanis 3 mum oncesinin ALTINDA). SIMETRI FIX: dip tarafi
    iki tetikliydi (hammer VEYA reclaim), tepe tek tetikliydi -> SHORT'u vetolamak
    LONG'u vetolamaktan yapisal olarak kolaydi (saha verisi: 24/24 LONG). Artik esit."""
    c = cs[-1]
    rng = c.high - c.low
    if rng <= 0:
        return False
    wf = cfg.wick_rej_frac if cfg else 0.45
    bf = cfg.body_mid_frac if cfg else 0.50
    upper_wick = c.high - max(c.open, c.close)
    # AYNA-FIX: dip tarafi 'c.close > c.low + bf*rng' -> gercek aynasi 'c.close < c.high - bf*rng'.
    # Eski 'c.close < c.low + bf*rng' yalniz bf=0.50'de ozdesti; knob oynarsa iki veto sessizce
    # ayrisirdi (olculdu: bf=0.60'ta dikey-ayna mum ciftinde dip=False/tepe=True asimetrisi).
    star = upper_wick > wf * rng and c.close < c.high - bf * rng
    reclaim_dn = len(cs) >= 4 and c.close < cs[-4].close
    return star or reclaim_dn


# ════════════════════════════════════════════════════════════════════════════
# OZELLIK MUHENDISLIGI (no-lookahead)
# ════════════════════════════════════════════════════════════════════════════
FEATURES = ("mom1", "mom3", "mom6", "mom12", "accel", "er", "rpos", "volz",
            "atrr", "dhi", "dlo", "qvolz", "tradesz", "kline_taker_imb")


def bar_features(cs: List[Candle], i: int, atrs: List[float], cfg: Config) -> Optional[List[float]]:
    """Bar i icin ozellik vektoru — YALNIZ cs[:i+1]. cfg.range_window GERCEKTEN kullanilir
    (panel6'da global sabit yok sayiyordu)."""
    if i < 14 or atrs[i] <= 0:
        return None
    a = atrs[i]
    c = [x.close for x in cs]
    mom1 = (c[i] - c[i - 1]) / a
    mom3 = (c[i] - c[i - 3]) / a
    mom6 = (c[i] - c[i - 6]) / a
    mom12 = (c[i] - c[i - 12]) / a
    accel = mom1 - (c[i - 1] - c[i - 2]) / a
    er = efficiency_ratio(cs, i, 10)
    rw = cfg.range_window
    win = cs[max(0, i - rw + 1):i + 1]
    rl = min(x.low for x in win)
    rh = max(x.high for x in win)
    rpos = ((c[i] - rl) / (rh - rl) * 2.0 - 1.0) if rh > rl else 0.0
    vols = [x.volume for x in cs[max(0, i - 20):i]]
    vmu = mean(vols)
    vsd = std(vols, vmu)
    volz = ((cs[i].volume - vmu) / vsd) if vsd > 1e-9 else 0.0
    short_a = mean([true_range(cs[k], cs[k - 1]) for k in range(max(1, i - 2), i + 1)])
    atrr = (short_a / a) if a > 0 else 1.0
    dhi = (rh - c[i]) / a
    dlo = (c[i] - rl) / a
    qhist = [(x.quote_volume if x.quote_volume > 0 else x.volume * x.close)
             for x in cs[max(0, i - 20):i]]
    qcur = cs[i].quote_volume if cs[i].quote_volume > 0 else cs[i].volume * cs[i].close
    qmu, qsd = mean(qhist), std(qhist)
    qvolz = (qcur - qmu) / qsd if qsd > 1e-9 else 0.0
    thist = [float(x.trade_count) for x in cs[max(0, i - 20):i]]
    tmu, tsd = mean(thist), std(thist)
    tradesz = (float(cs[i].trade_count) - tmu) / tsd if tsd > 1e-9 else 0.0
    kimb = ((2.0 * cs[i].taker_buy_base / cs[i].volume) - 1.0
            if cs[i].volume > 1e-12 else 0.0)
    return [mom1, mom3, mom6, mom12, accel, er, rpos, volz, atrr, dhi, dlo,
            qvolz, tradesz, _clip(kimb, -1.0, 1.0)]


def endpoint_label(cs: List[Candle], i: int, atrs: List[float], cfg: Config) -> Optional[int]:
    """Tam H mum sonraki DOWN/FLAT/UP etiketi.

    Sonucu henuz olusmamis satirlar ve exact timestamp sozlesmesini bozan bosluklar
    olgun sayilmaz. Boylece eksik ufuk son kapanisa kisaltilmaz.
    """
    end = i + cfg.horizon
    if i < 0 or end >= len(cs) or i >= len(atrs):
        return None
    a = atrs[i]
    if a <= 0 or cs[i].close <= 0 or cs[end].close <= 0:
        return None
    if cfg.require_exact_target_timestamp:
        t0, t1 = cs[i].close_ms, cs[end].close_ms
        if t0 is None or t1 is None or t1 - t0 != cfg.horizon * cfg.interval_ms:
            return None
    move = cs[end].close - cs[i].close
    delta = max(0.0, cfg.label_neutral_atr) * a
    return sign_eps(move, scale=cs[i].close, rel=cfg.tie_eps_rel,
                    abs_eps=max(delta, cfg.tie_eps_atr * a))


def triple_barrier_label(cs: List[Candle], i: int, atrs: List[float], cfg: Config) -> Optional[int]:
    """Geriye uyumlu ad; FABLE6'da semantik endpoint_label'dir."""
    return endpoint_label(cs, i, atrs, cfg)


def build_training(cs: List[Candle], atrs: List[float], cfg: Config
                   ) -> Tuple[List[List[float]], List[int], List[int]]:
    """(X, y, idxs) — idxs: her ornegin mum indeksi (markov/MC skill dogrulamasi icin)."""
    X, y, idxs = [], [], []
    last_resolvable = len(cs) - 1 - cfg.horizon
    for i in range(14, last_resolvable + 1):
        lbl = triple_barrier_label(cs, i, atrs, cfg)
        if lbl is None:
            continue
        f = bar_features(cs, i, atrs, cfg)
        if f is None:
            continue
        X.append(f)
        y.append(lbl)
        idxs.append(i)
    return X, y, idxs


def standardize(X: List[List[float]]) -> Tuple[List[float], List[float]]:
    if not X:
        return [], []
    d = len(X[0])
    mu = [mean([row[j] for row in X]) for j in range(d)]
    sd = [std([row[j] for row in X], mu[j]) or 1.0 for j in range(d)]
    return mu, sd


def apply_std(f: List[float], mu: List[float], sd: List[float]) -> List[float]:
    return [(f[j] - mu[j]) / sd[j] for j in range(len(f))]


# ════════════════════════════════════════════════════════════════════════════
# OGRENEN TAHMINCILER
# ════════════════════════════════════════════════════════════════════════════
def _fit_logistic(X: List[List[float]], y: List[int], iters: int = 250, lr: float = 0.3,
                  tau: float = 0.0):
    n = len(X)
    mu, sd = standardize(X)
    Xs = [apply_std(row, mu, sd) for row in X]
    d = len(Xs[0])
    # ZAMAN-AZALIMLI (rejim-kosullu degil): ussel recency agirligi. X bar-sirasinda gelir
    # (index 0 en eski, n-1 en yeni). tau>0 -> son barlar (guncel rejim) baskin, eski rejim
    # yumusakca soluk. W ile normalize -> etkin lr ve L2 olcegi degismez. tau=0 -> eski davranis.
    if tau and tau > 0 and n > 1:
        wts = [math.exp(-(n - 1 - i) / tau) for i in range(n)]
    else:
        wts = [1.0] * n
    W = sum(wts) or 1.0
    w = [[0.0] * d for _ in CLASSES]
    b = [0.0] * len(CLASSES)
    for _ in range(iters):
        gw = [[0.0] * d for _ in CLASSES]
        gb = [0.0] * len(CLASSES)
        for wi, row, yi in zip(wts, Xs, y):
            ps = _softmax([b[k] + sum(w[k][j] * row[j] for j in range(d))
                           for k in range(len(CLASSES))])
            for k, cls in enumerate(CLASSES):
                e = (ps[k] - (1.0 if yi == cls else 0.0)) * wi
                for j in range(d):
                    gw[k][j] += e * row[j]
                gb[k] += e
        for k in range(len(CLASSES)):
            for j in range(d):
                w[k][j] -= lr * (gw[k][j] / W + 0.001 * w[k][j])
            b[k] -= lr * gb[k] / W
    return (w, b, mu, sd)


def _pred_logistic(model, f: List[float]) -> Tuple[float, float, float]:
    w, b, mu, sd = model
    fs = apply_std(f, mu, sd)
    ps = _softmax([b[k] + sum(w[k][j] * fs[j] for j in range(len(fs)))
                   for k in range(len(CLASSES))])
    return normalize_probs(*ps)


def est_logistic(X, y, cur, cfg) -> Estimate:
    n = len(X)
    if n < 40 or len(set(y)) < 2:
        return Estimate("lojistik", 1 / 3, 0.0, n, "yetersiz", "learn",
                        p_down=1 / 3, p_flat=1 / 3)
    pd, pf, pu = _pred_logistic(_fit_logistic(X, y, tau=cfg.logistic_decay_tau), cur)
    return Estimate("lojistik", pu, 1.0, n, "", "learn", p_down=pd, p_flat=pf)


def _knn_pred(X, y, cur, k) -> Tuple[float, float, float]:
    mu, sd = standardize(X)
    cs_ = apply_std(cur, mu, sd)
    dists = []
    for row, yi in zip(X, y):
        rs = apply_std(row, mu, sd)
        dd = sum((rs[j] - cs_[j]) ** 2 for j in range(len(rs)))
        dists.append((dd, yi))
    dists.sort(key=lambda t: t[0])
    top = dists[:k]
    acc = {-1: 1.0, 0: 1.0, 1: 1.0}  # Laplace; uc sinifin hicbiri sifirlanmaz
    wsum = 3.0
    for dd, yi in top:
        wt = 1.0 / (1.0 + dd)
        acc[yi] = acc.get(yi, 0.0) + wt
        wsum += wt
    return normalize_probs(acc[-1] / wsum, acc[0] / wsum, acc[1] / wsum)


def est_knn(X, y, cur, cfg) -> Estimate:
    n = len(X)
    if n < cfg.knn_k:
        return Estimate("analog", 1 / 3, 0.0, n, "yetersiz", "learn",
                        p_down=1 / 3, p_flat=1 / 3)
    pd, pf, pu = _knn_pred(X, y, cur, cfg.knn_k)
    return Estimate("analog", pu, 1.0, cfg.knn_k, "", "learn", p_down=pd, p_flat=pf)


def _emp_cell(f):
    mom6 = 1 if f[2] > 0 else 0
    accel = 1 if f[4] > 0 else 0
    rp = f[6]
    rb = 0 if rp < -0.33 else (2 if rp > 0.33 else 1)
    return (mom6, accel, rb)


def _emp_pred(X, y, cur) -> Tuple[Tuple[float, float, float], int]:
    cur_cell = _emp_cell(cur)
    ys = [yi for f, yi in zip(X, y) if _emp_cell(f) == cur_cell]
    if len(ys) < 10:
        return (1 / 3, 1 / 3, 1 / 3), len(ys)
    n = len(ys) + 3.0
    return normalize_probs((ys.count(-1) + 1.0) / n,
                           (ys.count(0) + 1.0) / n,
                           (ys.count(1) + 1.0) / n), len(ys)


def est_empirical(X, y, cur, cfg) -> Estimate:
    n = len(X)
    if n < 60:
        return Estimate("ampirik", 1 / 3, 0.0, n, "yetersiz", "learn",
                        p_down=1 / 3, p_flat=1 / 3)
    p, m = _emp_pred(X, y, cur)
    if m < 10:
        return Estimate("ampirik", 1 / 3, 0.0, m, "hucre-seyrek", "learn",
                        p_down=1 / 3, p_flat=1 / 3)
    return Estimate("ampirik", p[2], 1.0, m, "", "learn", p_down=p[0], p_flat=p[1])


def _streak_at(cs, i) -> int:
    if i <= 0:
        return 0
    s = 0
    k = i
    s0 = sign_eps(cs[i].close - cs[i - 1].close, cs[i - 1].close)
    if s0 == 0:
        return 0
    while k > 0 and sign_eps(cs[k].close - cs[k - 1].close, cs[k - 1].close) == s0:
        s += 1
        k -= 1
        if s >= 6:
            break
    return s * s0


def _markov_pred_at(cs, i, atrs: Optional[List[float]] = None,
                    cfg: Optional[Config] = None) -> Optional[Tuple[float, float, float]]:
    """Ayni streak durumundan H-bar endpoint sinif dagilimi; yalniz bar i oncesi."""
    cfg = cfg or Config()
    atrs = atrs or atr_series(cs, cfg.atr_period)
    cur_s = _streak_at(cs, i)
    if cur_s == 0:
        return None
    labels: List[int] = []
    for j in range(14, i - cfg.horizon + 1):
        sj = _streak_at(cs, j)
        if sj != 0 and (sj > 0) == (cur_s > 0) and abs(sj) == abs(cur_s):
            lbl = endpoint_label(cs, j, atrs, cfg)
            if lbl is not None:
                labels.append(lbl)
    if len(labels) < 8:
        return None
    n = len(labels) + 3.0
    return normalize_probs((labels.count(-1) + 1.0) / n,
                           (labels.count(0) + 1.0) / n,
                           (labels.count(1) + 1.0) / n)


def est_markov(cs, atrs, cfg) -> Estimate:
    if len(cs) < 60:
        return Estimate("markov", 1 / 3, 0.0, len(cs), "yetersiz", "streak",
                        p_down=1 / 3, p_flat=1 / 3)
    p = _markov_pred_at(cs, len(cs) - 1, atrs, cfg)
    if p is None:
        return Estimate("markov", 1 / 3, 0.0, 0, "az-ornek", "streak",
                        p_down=1 / 3, p_flat=1 / 3)
    return Estimate("markov", p[2], 1.0, 20, "", "streak", p_down=p[0], p_flat=p[1])


def market_bias(cs: List[Candle], cfg: Optional[Config] = None) -> float:
    if len(cs) < 20:
        return 0.0
    a = atr_series(cs, cfg.atr_period if cfg else 14)[-1]
    if a <= 0:
        return 0.0
    scale = cfg.market_bias_scale if cfg else 2.0
    m = (cs[-1].close - cs[-6].close) / a
    return _clip(_tanh(m / scale), -1.0, 1.0)


def est_btc_lead(btc_bias: Optional[float], cfg: Config) -> Estimate:
    if btc_bias is None or abs(btc_bias) < 1e-6:
        return Estimate("BTC-lider", 0.5, 0.0, 0, "yok", "btc")
    g = cfg.btc_lead_gain
    p = _clip(0.5 + btc_bias * g, 0.5 - g, 0.5 + g)
    return Estimate("BTC-lider", p, cfg.w_btc, 1, f"btc={btc_bias:+.2f}", "btc")


def est_btc_leader_state(st: Optional[BtcLeaderState], cfg: Config) -> Estimate:
    """STEP4: BTC bas-at tanisini tahminci bloguna cevirir.
    Bu katman yon URETMEZ; yalniz ayni/ters tempo bilgisini sinirli p_up katkisiyla
    combine() icine sokar. Hard/soft veto ayri kapida uygulanir."""
    if st is None or st.quality <= 0 or st.side == 0:
        note = "yok" if st is None else (st.mode + ": " + "; ".join(st.reasons[:2]))[:90]
        return Estimate("BTC-bas-at", 0.5, 0.0, 0, note, "btc")
    # confirm_adj zaten cap'lenmis ve imzali: + LONG, - SHORT. p_up'a sinirli yansir.
    p = _clip(0.5 + st.confirm_adj, 0.5 - cfg.btc_confirm_cap, 0.5 + cfg.btc_confirm_cap)
    note = f"{st.mode} s={st.strength:.2f}"
    if st.corr is not None:
        note += f" corr={st.corr:+.2f}"
    if st.beta is not None:
        note += f" beta={st.beta:+.2f}"
    return Estimate("BTC-bas-at", p, cfg.w_btc * _clip(st.quality, 0.0, 1.0), 1, note[:100], "btc")


def _series_returns(cs: List[Candle]) -> List[Tuple[Optional[int], float]]:
    out: List[Tuple[Optional[int], float]] = []
    for i in range(1, len(cs)):
        if cs[i - 1].close > 0:
            out.append((cs[i].close_ms, cs[i].close / cs[i - 1].close - 1.0))
    return out


def _aligned_returns(a: List[Candle], b: List[Candle]) -> Tuple[List[float], List[float]]:
    """Iki sembolun 15m getirilerini close_ms ile hizalar. F7a (FABLE6_5): timestamp
    kesisimi yetersizse (<5) POZISYONEL kuyruk eslemesi YAPILMAZ — farkli donemlerin
    getirileri eslesirdi; katman veri-yetersiz olarak susar (bos liste doner)."""
    ra = _series_returns(a)
    rb = _series_returns(b)
    ma = {t: r for t, r in ra if t is not None}
    mb = {t: r for t, r in rb if t is not None}
    ortak = sorted(set(ma) & set(mb))
    if len(ortak) >= 5:
        return [ma[t] for t in ortak], [mb[t] for t in ortak]
    return [], []


def _corr(xs: List[float], ys: List[float]) -> Optional[float]:
    n = min(len(xs), len(ys))
    if n < 3:
        return None
    xs, ys = xs[-n:], ys[-n:]
    mx, my = mean(xs), mean(ys)
    sx, sy = std(xs, mx), std(ys, my)
    if sx <= 1e-12 or sy <= 1e-12:
        return None
    return _clip(sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / n / (sx * sy), -1.0, 1.0)


def _beta(xs: List[float], ys: List[float]) -> Optional[float]:
    """xs = sembol getirisi, ys = BTC getirisi; beta = cov(sym,btc)/var(btc)."""
    n = min(len(xs), len(ys))
    if n < 3:
        return None
    xs, ys = xs[-n:], ys[-n:]
    mx, my = mean(xs), mean(ys)
    vy = sum((y - my) ** 2 for y in ys) / n
    if vy <= 1e-12:
        return None
    cov = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / n
    return cov / vy


def _rolling_metric_history(xs: List[float], ys: List[float], win: int, min_n: int, fn) -> List[float]:
    out: List[float] = []
    n = min(len(xs), len(ys))
    xs, ys = xs[-n:], ys[-n:]
    for end in range(min_n, n + 1):
        segx = xs[max(0, end - win):end]
        segy = ys[max(0, end - win):end]
        v = fn(segx, segy)
        if v is not None and math.isfinite(v):
            out.append(float(v))
    return out


def _lagged_corr_current(sym_r: List[float], btc_r: List[float], lags: Tuple[int, ...], win: int, min_n: int) -> Optional[float]:
    """Pozitif skor: BTC gecmisi sembolu acikliyor; negatif skor: sembol BTC'yi daha cok acikliyor."""
    n = min(len(sym_r), len(btc_r))
    if n < min_n + max(lags or (1,)) + 2:
        return None
    s = sym_r[-n:]
    b = btc_r[-n:]
    best_btc, best_sym = 0.0, 0.0
    for lag in lags:
        if lag <= 0 or n <= lag + min_n:
            continue
        # BTC(t-lag) -> Sembol(t)
        c1 = _corr(s[-win:], b[-win - lag:-lag])
        # Sembol(t-lag) -> BTC(t)
        c2 = _corr(b[-win:], s[-win - lag:-lag])
        if c1 is not None:
            best_btc = max(best_btc, abs(c1))
        if c2 is not None:
            best_sym = max(best_sym, abs(c2))
    return best_btc - best_sym


def _lagged_corr_history(sym_r: List[float], btc_r: List[float], lags: Tuple[int, ...], win: int, min_n: int) -> List[float]:
    out: List[float] = []
    n = min(len(sym_r), len(btc_r))
    for end in range(min_n + max(lags or (1,)) + 2, n + 1):
        v = _lagged_corr_current(sym_r[:end], btc_r[:end], lags, win, min_n)
        if v is not None and math.isfinite(v):
            out.append(float(v))
    return out


def _vol_history(rs: List[float], win: int, min_n: int) -> List[float]:
    out = []
    for end in range(min_n, len(rs) + 1):
        seg = rs[max(0, end - win):end]
        if len(seg) >= min_n:
            out.append(std(seg))
    return out


def _last4_chronology(cs: List[Candle], atrs: List[float], cfg: Config) -> Dict[str, float]:
    if len(cs) < 5:
        return {"dir": 0, "body": 0.0, "wick_against_long": 0.0, "wick_against_short": 0.0}
    seg = cs[-4:]
    a = atrs[-1] if atrs and atrs[-1] > 0 else mean([max(c.high - c.low, 0.0) for c in seg]) or 1.0
    dir_sum = sum(1 if c.close > c.open else (-1 if c.close < c.open else 0) for c in seg)
    body = sum((c.close - c.open) / a for c in seg) / 4.0
    uw = sum((c.high - max(c.open, c.close)) / a for c in seg) / 4.0
    lw = sum((min(c.open, c.close) - c.low) / a for c in seg) / 4.0
    return {"dir": 1 if dir_sum >= 2 else (-1 if dir_sum <= -2 else 0),
            "body": body, "wick_against_long": uw, "wick_against_short": lw}


def build_btc_leader_state(symbol_snap: Snapshot, btc_snap: Optional[Snapshot], cfg: Config) -> Optional[BtcLeaderState]:
    """STEP4 BTC bas-at durumu.

    Kanit-disiplini: BTC core = BTCUSDT perpetual; spot/dominance yoksa katman susar.
    Liderlik sabit esikle degil rolling corr/beta/leadlag + robust-z/quantile ile olculur.
    """
    if not getattr(cfg, "btc_leader_enabled", True):
        return None
    if btc_snap is None or not btc_snap.candles or symbol_snap.symbol.upper() == cfg.btc_core_symbol.upper():
        return None
    sym_r, btc_r = _aligned_returns(symbol_snap.candles, btc_snap.candles)
    n = min(len(sym_r), len(btc_r))
    st = BtcLeaderState(reasons=[])
    if n < max(cfg.btc_corr_min_n, cfg.btc_leadlag_min_n, cfg.btc_beta_min_n):
        st.mode = "BTC_DATA_INSUFFICIENT"
        st.reasons.append(f"veri az n={n}")
        return st
    sym_r, btc_r = sym_r[-n:], btc_r[-n:]
    corr_hist = _rolling_metric_history(sym_r, btc_r, cfg.btc_corr_win, cfg.btc_corr_min_n, _corr)
    beta_hist = _rolling_metric_history(sym_r, btc_r, cfg.btc_beta_win, cfg.btc_beta_min_n, _beta)
    lead_hist = _lagged_corr_history(sym_r, btc_r, cfg.btc_leadlag_lags, cfg.btc_leadlag_win, cfg.btc_leadlag_min_n)
    sym_vol_hist = _vol_history(sym_r, cfg.btc_corr_win, cfg.btc_corr_min_n)
    btc_vol_hist = _vol_history(btc_r, cfg.btc_corr_win, cfg.btc_corr_min_n)
    st.corr = corr_hist[-1] if corr_hist else None
    st.beta = beta_hist[-1] if beta_hist else None
    st.leadlag = lead_hist[-1] if lead_hist else None
    st.corr_z = robust_z(corr_hist[:-1][-cfg.btc_metric_norm_win:], st.corr, cfg.btc_metric_norm_min_n) if st.corr is not None else None
    st.beta_z = robust_z(beta_hist[:-1][-cfg.btc_metric_norm_win:], st.beta, cfg.btc_metric_norm_min_n) if st.beta is not None else None
    st.leadlag_q = None
    if st.leadlag is not None and len(lead_hist) > 1:
        hist = lead_hist[:-1][-cfg.btc_metric_norm_win:]
        if len(hist) >= cfg.btc_metric_norm_min_n:
            st.leadlag_q = sum(1 for v in hist if v <= st.leadlag) / len(hist)
    st.alt_vol_z = robust_z(sym_vol_hist[:-1][-cfg.btc_metric_norm_win:], sym_vol_hist[-1], cfg.btc_metric_norm_min_n) if sym_vol_hist else None
    st.btc_vol_z = robust_z(btc_vol_hist[:-1][-cfg.btc_metric_norm_win:], btc_vol_hist[-1], cfg.btc_metric_norm_min_n) if btc_vol_hist else None

    btc_bias = market_bias(btc_snap.candles, cfg)
    st.side = 1 if btc_bias > 0 else (-1 if btc_bias < 0 else 0)
    # Gucluluk: tek metrik degil; corr/beta/leadlag/vol birlikte, her biri veri-goreli.
    kanit = 0
    if st.corr_z is not None and st.corr_z >= cfg.btc_leader_z_hi:
        kanit += 1; st.reasons.append(f"corr_z={st.corr_z:+.1f}")
    if st.beta_z is not None and st.beta_z >= cfg.btc_leader_z_hi:
        kanit += 1; st.reasons.append(f"beta_z={st.beta_z:+.1f}")
    if st.leadlag_q is not None and st.leadlag_q >= cfg.btc_leader_q_hi and (st.leadlag or 0) > 0:
        kanit += 1; st.reasons.append(f"lead_q={st.leadlag_q:.2f}")
    if st.btc_vol_z is not None and st.btc_vol_z >= cfg.btc_vol_spike_z:
        kanit += 1; st.reasons.append(f"btc_vol_z={st.btc_vol_z:+.1f}")
    # DECORRELATION_RISK: dusuk/kopan corr tek basina 'ignore' DEGIL; vol/stres ile risk olur.
    risk_k = 0
    if st.corr_z is not None and st.corr_z <= -cfg.btc_leader_z_hi:
        risk_k += 1
    if st.alt_vol_z is not None and st.alt_vol_z >= cfg.btc_vol_spike_z:
        risk_k += 1
    if symbol_snap.candles and len(symbol_snap.candles) >= 4:
        ois = [c.oi for c in symbol_snap.candles if c.oi is not None]
        if len(ois) >= 7 and ois[-4] > 0:
            oi_hist = _change_series(ois, lag=3)
            oi_chg = (ois[-1] - ois[-4]) / ois[-4]
            oi_z = robust_z(oi_hist[:-1][-cfg.norm_win:], oi_chg, cfg.norm_min_n)
            if oi_z is not None and abs(oi_z) >= cfg.btc_oi_stress_z:
                risk_k += 1; st.reasons.append(f"oi_z={oi_z:+.1f}")
    if symbol_snap.funding is not None and symbol_snap.funding_hist:
        fz = robust_z(symbol_snap.funding_hist[:-1][-cfg.funding_norm_win:], symbol_snap.funding, cfg.norm_min_n)
        if fz is not None and abs(fz) >= cfg.btc_funding_stress_z:
            risk_k += 1; st.reasons.append(f"fund_z={fz:+.1f}")
    if symbol_snap.taker_ratio is not None:
        tak = [c.taker for c in symbol_snap.candles if c.taker is not None]
        tz = robust_z(tak[:-1][-cfg.norm_win:], symbol_snap.taker_ratio, cfg.norm_min_n) if tak else None
        if tz is not None and abs(tz) >= cfg.btc_taker_stress_z:
            risk_k += 1; st.reasons.append(f"taker_z={tz:+.1f}")
    _prem_role = (symbol_snap.source_times.get("premium", {}).get("role")
                  if symbol_snap.source_times else None)
    if (_prem_role == "direction" and symbol_snap.premium and
            symbol_snap.premium.get("mark") and symbol_snap.premium.get("index")):
        try:
            bps = abs((symbol_snap.premium["mark"] - symbol_snap.premium["index"]) / symbol_snap.premium["index"] * 10000.0)
            if bps > cfg.tasfiye_prem_bps:
                risk_k += 1; st.reasons.append(f"prem={bps:.0f}bps")
        except Exception as exc:
            symbol_snap.source_errors.append("BTC premium stresi hesaplanamadi: " + str(exc)[:100])
    st.decorrelation_risk = _clip(risk_k / max(1, cfg.btc_decorrelation_min_confirm), 0.0, 1.0)
    st.risk_penalty = cfg.btc_risk_penalty_cap * max(0.0, st.decorrelation_risk)

    # ETH major profile: hard-veto icin bir kanit daha iste; BTC tek-lider sayilmaz.
    hard_need = cfg.btc_hard_veto_min_confirm
    if cfg.btc_eth_major_profile and symbol_snap.symbol.upper().startswith("ETH"):
        hard_need += 1
    st.quality = _clip((kanit + 0.5 * risk_k) / max(1, hard_need), 0.0, 1.0)
    st.strength = _clip((abs(btc_bias) + st.quality) / 2.0, 0.0, 1.0)
    st.confirm_adj = st.side * min(cfg.btc_confirm_cap, cfg.btc_confirm_cap * st.strength)
    if st.side == 0 or kanit < cfg.btc_soft_veto_min_confirm:
        st.mode = "DECORRELATION_RISK" if risk_k >= cfg.btc_decorrelation_min_confirm else "BTC_IGNORE"
    elif kanit >= hard_need:
        st.mode = "BTC_CONFIRM"
    else:
        st.mode = "BTC_RISK_ONLY" if risk_k else "BTC_IGNORE"
    if not st.reasons:
        st.reasons.append("liderlik zayif/olculum notr")
    return st


def btc_veto_mode_for_side(st: Optional[BtcLeaderState], side: str, last4: Optional[Dict[str, float]],
                           symbol: str, cfg: Config) -> Tuple[str, str]:
    """Seçilen altcoin yonune gore BTC hard/soft veto karari. Yon uretmez."""
    if st is None:
        return "NONE", "BTC yok/notr"
    if st.decorrelation_risk >= 1.0:
        why0 = f"{st.mode} kalite={st.quality:.2f}; " + "; ".join(st.reasons[:4])
        return "RISK", why0 + " | decorrelation-risk"
    if st.side == 0 or st.quality <= 0:
        return "NONE", "BTC yok/notr"
    sgn = 1 if side == "LONG" else -1
    ters = st.side != sgn
    l4 = last4 or {}
    l4_against = (side == "LONG" and (l4.get("dir", 0) < 0 or l4.get("wick_against_long", 0) > 0.4)) or \
                 (side == "SHORT" and (l4.get("dir", 0) > 0 or l4.get("wick_against_short", 0) > 0.4))
    hard_need = cfg.btc_hard_veto_min_confirm + (1 if cfg.btc_eth_major_profile and symbol.upper().startswith("ETH") else 0)
    kanit_say = int(round(st.quality * hard_need))
    why = f"{st.mode} BTC={'LONG' if st.side>0 else 'SHORT'} kalite={st.quality:.2f}; " + "; ".join(st.reasons[:4])
    if ters and kanit_say >= hard_need and l4_against:
        return "HARD", why + " | son4 sembol aleyhte"
    if ters and kanit_say >= cfg.btc_soft_veto_min_confirm:
        return "SOFT", why
    if not ters and st.mode == "BTC_CONFIRM":
        return "CONFIRM", why
    return "NONE", why


# ─── ONCU-MAKRO BLOK: panel6'da cekilip ATILAN veriyi karara sokar ───────────
def macro_leading_estimate(snap: Snapshot, cfg: Config) -> Estimate:
    """Origin-PIT OI/funding/taker ve varsa origin-book -> P(yukari) egilimi.
    Modest agirlik; oncu-makro sinyal (Beklenti #4). 15m periyot -> dakika-alti flash yakalamaz."""
    tilts: List[float] = []
    notes: List[str] = []
    cs = snap.candles
    # ── FUNDING DURUMU ONCE olculur (KAZANC-1): OI hucreleri funding'e KOSULLU.
    # Ayni z tek kez hesaplanir ve asagidaki funding tiltinde AYNEN kullanilir.
    _f = snap.funding
    _fh = snap.funding_hist or []
    _fz = robust_z(_fh[:-1][-cfg.funding_norm_win:], _f, cfg.norm_min_n) if _f is not None else None
    fund_neg_ext = (_fz <= -cfg.z_extreme) if _fz is not None else (
        _f is not None and _f < cfg.funding_neg_fallback)
    fund_pos_ext = (_fz >= cfg.z_extreme) if _fz is not None else (
        _f is not None and _f > cfg.funding_pos_fallback)
    # ── OI momentum: MUTLAK esik (0.003) DEGIL -> OI'nin KENDI momentum dagilimina gore z.
    ois = [c.oi for c in cs if c.oi is not None]
    if len(ois) >= 7 and len(cs) >= 4 and cs[-4].close > 0 and ois[-4] > 0:
        oi_ch_hist = _change_series(ois, lag=3)           # gecmis OI-momentum dagilimi
        oi_chg = (ois[-1] - ois[-4]) / ois[-4]
        p_chg = (cs[-1].close - cs[-4].close) / cs[-4].close
        oi_z = robust_z(oi_ch_hist[:-1], oi_chg, cfg.norm_min_n)   # son haric -> no-lookahead
        oi_up = (oi_z >= cfg.z_extreme) if oi_z is not None else (oi_chg > cfg.oi_chg_fallback)
        oi_dn = (oi_z <= -cfg.z_extreme) if oi_z is not None else (oi_chg < -cfg.oi_chg_fallback)
        p_up = p_chg > cfg.price_chg_ref
        p_dn = p_chg < -cfg.price_chg_ref
        if oi_up and p_dn:
            # KAZANC-1 (CME: artan OI trend GUCUNU teyit eder): eski kod bu hucrede KOSULSUZ
            # yukari tilt veriyordu (+sikisma varsayimi). Simdi: funding ASIRI-NEGATIFSE
            # (kalabalik short = squeeze yakiti) yukari tilt korunur; funding NORMAL/POZITIFSE
            # bu 'saglikli short devami'dir -> asagi tilt. Funding verisi YOKSA eski davranis
            # AYNEN korunur (cold-start ilkesi).
            if fund_neg_ext or _f is None:
                tilts.append(+cfg.tilt_oi_squeeze); notes.append("OI+/fiyat- + funding asiri-negatif (kalabalik short->sikisma)")
            else:
                tilts.append(-cfg.tilt_oi_short_cont); notes.append("OI+/fiyat- funding normal (saglikli short devami)")
        elif oi_up and p_up:
            if fund_pos_ext:
                tilts.append(-cfg.tilt_oi_squeeze)
                notes.append("OI+/fiyat+ + funding asiri-pozitif (kalabalik long->asagi sikisma riski)")
            else:
                tilts.append(+cfg.tilt_oi_long); notes.append("OI+/fiyat+ (long birikim)")
        elif oi_dn and p_dn:
            tilts.append(-cfg.tilt_oi_liq); notes.append("OI-/fiyat- (long tasfiye)")
        elif oi_dn and p_up:
            tilts.append(+cfg.tilt_oi_shortcov); notes.append("OI-/fiyat+ (short kapanis)")
    # ── funding: MUTLAK esik DEGIL -> funding'in KENDI tarihsel dagilimina gore z.
    if snap.funding is not None:
        # fz/neg/pos yukarida TEK kez hesaplandi (fund_neg_ext/fund_pos_ext) — davranis birebir.
        if fund_neg_ext:
            tilts.append(+cfg.tilt_funding_neg); notes.append("negatif funding (short odul->squeeze)")
        elif fund_pos_ext:
            tilts.append(-cfg.tilt_funding_pos); notes.append("asiri+ funding (long kalabalik)")
    # ── taker orani: MUTLAK 1.05/0.95 DEGIL -> taker serisinin KENDI dagilimina gore z.
    if snap.taker_ratio is not None:
        tr = snap.taker_ratio
        tk_hist = [c.taker for c in cs if c.taker is not None]
        tz = robust_z(tk_hist[:-1][-cfg.norm_win:], tr, cfg.norm_min_n)  # [:-1]: cari degeri disla (OI/funding ile simetrik)
        hi = (tz >= cfg.z_extreme) if tz is not None else (tr > cfg.taker_hi_fallback)
        lo = (tz <= -cfg.z_extreme) if tz is not None else (tr < cfg.taker_lo_fallback)
        if hi:
            tilts.append(+cfg.tilt_taker); notes.append("taker-alim baskin")
        elif lo:
            tilts.append(-cfg.tilt_taker); notes.append("taker-satim baskin")
    _bm = snap.source_times.get("book", {}) if snap.source_times else {}
    _bev = _bm.get("event_time") if isinstance(_bm, dict) else None
    _origin = snap.last_closed_ms or (cs[-1].close_ms if cs else None)
    _book_direction_ok = (isinstance(_bm, dict) and _bm.get("role") == "direction"
                          and isinstance(_bev, (int, float)) and _origin is not None
                          and _bev <= _origin)
    if snap.book is not None and _book_direction_ok:
        # SPOOF-SUSTURMA FIX (denetim): spoof suphesi yalniz render'da UYARI basiyordu,
        # imbalance ayni kosuda makro tilt'e girmeye DEVAM ediyordu ("imbalance'a guvenme"
        # deyip guvenmek). Simdi: iki derinlik ornegi arasinda duvar kaybi olculduyse
        # imbalance tilt'i bu kosuda ATLANIR (veri atilmiyor; supheli olcumun karari
        # tiltlemesi engelleniyor — olcum yoksa eski davranis aynen).
        _sp_taraf, _ = spoof_kontrol(snap.book, snap.book2, cfg.spoof_kayip_oran)
        if _sp_taraf is None:
            imb = float(snap.book.get("imbalance", 0.0))
            tilts.append(_clip(imb * cfg.tilt_imb_k, -cfg.tilt_imb_cap, cfg.tilt_imb_cap))
        else:
            notes.append(f"OB-imbalance ATLANDI (spoof suphesi: {_sp_taraf} duvari)")
    elif snap.book is not None:
        notes.append("OB-imbalance ATLANDI (origin-sonrasi execution verisi)")
    # YON9-EK: taraf ayrisimi artik OLCULUYOR (denetim: 'OI+/fiyat- hucresi short birikimi
    # VARSAYIYORDU'). Top-trader L/S kalabaligi kontra tilt verir; blok zaten yalniz
    # uzlasmazlik/blokaj katmanina girer (p_up yon uretmez), etki alani sinirli+guvenli.
    # OLU-VERI FIX (denetim): ls_global cekilip yalniz ekranda gosteriliyordu, hicbir
    # hesaba girmiyordu. Simdi: top-trader orani birincil kalir; global ayni yonde
    # kalabaliksa tilt %50 guclenir (teyit), top yoksa global TEK basina YARI tiltle
    # konusur. Etki alani ayni (yalniz makro blok; yon uretmez), buyukluk sinirli.
    _lt_yon = 0
    if snap.ls_top is not None:
        _lt_yon = -1 if snap.ls_top >= cfg.ls_crowd_hi else (1 if snap.ls_top <= cfg.ls_crowd_lo else 0)
    _lg_yon = 0
    if snap.ls_global is not None:
        _lg_yon = -1 if snap.ls_global >= cfg.ls_crowd_hi else (1 if snap.ls_global <= cfg.ls_crowd_lo else 0)
    if _lt_yon != 0:
        _lt_t = cfg.ls_tilt * (1.5 if _lg_yon == _lt_yon else 1.0)
        tilts.append(_lt_yon * _lt_t)
        notes.append(f"top-trader L/S {snap.ls_top:.2f} ({'LONG' if _lt_yon < 0 else 'SHORT'} kalabalik"
                     + ("; global teyit" if _lg_yon == _lt_yon else "") + ")")
    elif _lg_yon != 0:
        tilts.append(_lg_yon * cfg.ls_tilt * 0.5)
        notes.append(f"global L/S {snap.ls_global:.2f} ({'LONG' if _lg_yon < 0 else 'SHORT'} kalabalik; yari tilt)")
    if not tilts and not notes:
        return Estimate("makro-oncu", 0.5, 0.0, 0, "veri yok", "macro")
    if not tilts:      # yalniz not var (orn. spoof nedeniyle imbalance atlandi) -> notr ama notu tasi
        return Estimate("makro-oncu", 0.5, 0.0, 0, "; ".join(notes)[:140], "macro")
    p = _clip(0.5 + sum(tilts), 0.5 - cfg.macro_p_clip, 0.5 + cfg.macro_p_clip)
    return Estimate("makro-oncu", p, cfg.w_macro, len(tilts), "; ".join(notes)[:140], "macro")


# ════════════════════════════════════════════════════════════════════════════
# MONTE CARLO (blok-bootstrap + kirilim/kabul-bilincli miknatis)
# ════════════════════════════════════════════════════════════════════════════
def mc_simulate(cs: List[Candle], st: Structure, drift: float, cfg: Config,
                rng: random.Random, paths_n: Optional[int] = None
                ) -> Tuple[List[List[float]], float]:
    """Ileri fiyat-carpani yollari + P(up-once) doner. Miknatis KABUL-bilincli:
    kabul-edilmemis taze dip -> yukari sicrama; kabul-edilmis kirilim -> devam."""
    n = len(cs)
    a = st.atr
    N = paths_n if paths_n is not None else cfg.mc_paths
    if n < 30 or a <= 0 or cs[-1].close <= 0:   # price>0 guard: bozuk/sifir kapanista ZeroDivisionError'i onle
        return [], 0.5
    W = min(cfg.mc_window, n - 1)
    rets = [math.log(cs[i].close / cs[i - 1].close)
            for i in range(n - W, n) if cs[i - 1].close > 0 and cs[i].close > 0]
    if len(rets) < 20:
        return [], 0.5
    L = max(2, int(round(len(rets) ** (1.0 / 3.0))))
    nr = len(rets)
    price = cs[-1].close
    # ── FHS (Filtered Historical Simulation): getiriler EWMA-vol ile ARINDIRILIR,
    # simulasyon adiminda GUNCEL vol ile geri olceklenir. Boylece rejim kirilmasinda
    # (vol sicrayinca/dusunce) MC dagilimi 1 bar icinde adapte olur; eski rejimin
    # olu dagilimiyla fiyatlama biter. Kanit tabani: Barone-Adesi ve ark. FHS; saf stdlib.
    _use_fhs = nr >= cfg.fhs_min_n and cfg.fhs_lambda > 0
    if _use_fhs:
        _lam = cfg.fhs_lambda
        # F4 fix (Barone-Adesi FHS sozlesmesi): r_t, KENDINDEN ONCEKI sigma_{t-1} ile
        # arindirilir. Eski kod sigma_t'ye r_t'nin kendisini de katiyordu; standardize
        # sok 1/sqrt(1-lambda)~4.08'de tikaniyor, MC kuyruklari sonukluyordu (denetim
        # olcumu: z 4.07 vs 50.0). Tohum ilk getirinin karesi (pencere-ici gelecek
        # bilgisi kullanilmaz; no-lookahead korunur). _cursig, son getiri DAHIL guncel
        # vol'dur (ileri-simulasyon olceklemesi icin dogru buyukluk; eski davranisla ayni).
        _var = rets[0] * rets[0] + 1e-12
        _sig_prev = []
        for _r0 in rets:
            _sig_prev.append(math.sqrt(_var) if _var > 0 else 1e-9)
            _var = _lam * _var + (1.0 - _lam) * _r0 * _r0
        _cursig = math.sqrt(_var) if _var > 1e-24 else 1e-9
        rets_fhs = [rets[_k] / _sig_prev[_k] if _sig_prev[_k] > 1e-12 else 0.0
                    for _k in range(nr)]
    else:
        rets_fhs, _cursig = rets, 1.0
    up_lvl = 1.0 + cfg.barrier_atr * a / price
    dn_lvl = 1.0 - cfg.barrier_atr * a / price
    d = drift * (a / price) * cfg.mc_drift_k
    # RECENCY-AGIRLIKLI bootstrap: son barlar (rejim/donus) baskin, eski trend degil.
    # Boylece V-donusunde MC eski dususu tekrar orneklemeyip dibi short'lamaz.
    tau = max(5.0, nr / float(cfg.mc_recency_tau_div))
    _cw = []
    _acc = 0.0
    for k in range(nr):
        _acc += math.exp(-(nr - 1 - k) / tau)
        _cw.append(_acc)
    _tot = _cw[-1] or 1.0

    def _pick_start():
        x = rng.random() * _tot
        lo, hi = 0, nr - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if _cw[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        return lo

    rl = st.range_low if st.valid else None
    rh = st.range_high if st.valid else None
    mag_k = cfg.mc_magnet_k * a / price
    edge_band = cfg.edge_band_atr
    # KABUL referansi: SON accept_n mum HARIC pencere ekstremleri. ESKI kod bandin kendi
    # ekstremine (rl/rh) bakiyordu -> kapanis bant disina cikamayacagi icin kabul HEP False
    # kaliyordu = kirilan destekte bile MC yukari-sicrama biasi ekliyordu (saha verisi:
    # dusus fazinda 24/24 LONG, %8 isabet). Simdi gercek kirilim 'kabul' sayilir -> devam.
    _mcb = cfg.accept_n
    _mcw = cs[-(cfg.range_window + _mcb + 1):-(_mcb + 1)] if n > cfg.range_window + _mcb + 1 else cs[:-(_mcb + 1)]
    _mlo = min(x.low for x in _mcw) if _mcw else rl
    _mhi = max(x.high for x in _mcw) if _mcw else rh
    floor_acc = _accepted_break(cs, _mlo, "dn", cfg.accept_n, cfg.accept_k) if rl is not None else False
    ceil_acc = _accepted_break(cs, _mhi, "up", cfg.accept_n, cfg.accept_k) if rh is not None else False
    H = cfg.horizon
    ups = 0
    paths: List[List[float]] = []
    for _ in range(N):
        mult = 1.0
        idx = _pick_start()
        blk = 0
        first = 0
        path = []
        for _h in range(H):
            if blk == 0:
                idx = _pick_start()
                blk = L
            r = (rets_fhs[idx] * _cursig if _use_fhs else rets[idx]) + d
            idx = (idx + 1) % nr
            blk -= 1
            if rl is not None and rh is not None and a > 0:
                cur = price * mult
                if cur < rl:
                    r += (-mag_k if floor_acc else +mag_k)      # kabul-> devam asagi; taze-> sicra yukari
                elif cur > rh:
                    r += (+mag_k if ceil_acc else -mag_k)
                else:
                    ld = (cur - rl) / a
                    hd = (rh - cur) / a
                    push = 0.0
                    if ld < edge_band and not floor_acc:
                        push += mag_k * (1.0 - ld / edge_band)    # destek katkisi
                    if hd < edge_band and not ceil_acc:
                        push -= mag_k * (1.0 - hd / edge_band)    # direnc katkisi
                    r += push  # dar bantta iki etki BAGIMSIZ ve net; if/elif UP onceligi yok
            mult *= math.exp(_clip(r, -0.50, 0.50))
            path.append(mult)
            if first == 0:
                if mult >= up_lvl:
                    first = 1
                elif mult <= dn_lvl:
                    first = -1
        if first == 1 or (first == 0 and mult > 1.0 + cfg.tie_eps_rel):
            ups += 1
        elif first == 0 and abs(mult - 1.0) <= cfg.tie_eps_rel:
            ups += 0.5
        paths.append(path)
    return paths, ups / N


def mc_endpoint_probs(paths: List[List[float]], price: float, atr: float,
                      cfg: Config) -> Tuple[float, float, float]:
    """MC yollarinin tam H endpoint uc-sinif dagilimi; ara bariyer kullanmaz."""
    if not paths or price <= 0 or atr <= 0:
        return (1 / 3, 1 / 3, 1 / 3)
    band = max(0.0, cfg.label_neutral_atr) * atr / price
    counts = [0.0, 0.0, 0.0]
    for path in paths:
        if not path:
            continue
        move = path[-1] - 1.0
        s = sign_eps(move, 1.0, cfg.tie_eps_rel, band)
        counts[CLASSES.index(s)] += 1.0
    return normalize_probs(counts[0], counts[1], counts[2])


def _mc_dir_at(cs: List[Candle], i: int, atrs: List[float], cfg: Config,
               rng: random.Random) -> Optional[Tuple[float, float, float]]:
    """Skill dogrulamasi icin bar i'de mini-MC endpoint dagilimi. Yalniz prefix."""
    sub = cs[:i + 1]
    if len(sub) < 40:
        return None
    st = build_structure(sub, cfg)
    if not st.valid:
        return None
    paths, _ = mc_simulate(sub, st, 0.0, cfg, rng, paths_n=300)
    return mc_endpoint_probs(paths, st.price, st.atr, cfg) if paths else None


def _bridge_cross(x0: float, x1: float, b: float, sig: float, ust: bool) -> float:
    """Brownian-koprusu: x0->x1 adiminda bariyer b'nin BAR-ICI kesilme olasiligi.
    ust=True: b iki ucun da USTUNDE (fitil yukari); ust=False: altinda (fitil asagi).
    Uclardan biri zaten gectiyse 1.0. p = exp(-2(b-x0)(b-x1)/sig^2). NO-LOOKAHEAD."""
    if ust:
        if x0 >= b or x1 >= b:
            return 1.0
        d0, d1 = b - x0, b - x1
    else:
        if x0 <= b or x1 <= b:
            return 1.0
        d0, d1 = x0 - b, x1 - b
    if sig <= 1e-12:
        return 0.0
    z = -2.0 * d0 * d1 / (sig * sig)
    return math.exp(z) if z > -700 else 0.0


def mc_first_passage(paths, price, target, stop, side,
                     wick_sig: float = 0.0, rng: Optional[random.Random] = None,
                     return_terminal: bool = False,
                     payoff_entry: Optional[float] = None):
    """Ilk-gecis: hedef mi stop mu ONCE vurulur. wick_sig>0 ve rng verilirse her adimda
    BAR-ICI fitil kesisi Brownian-kopruyle orneklenir (fitille yenen stoplar artik
    gorunur). Ayni adimda iki bariyer de kesilirse KONSERVATIF: stop sayilir
    (_bt_resolve'un 'ayni-bar -> kayip' kuraliyla tutarli). wick_sig=0 -> eski davranis."""
    if not paths or price <= 0:
        return (0.0, 0.0, 0.0) if return_terminal else (0.0, 0.0)
    tgt_m = target / price
    stp_m = stop / price
    payoff_entry = price if payoff_entry is None else payoff_entry
    kopru = wick_sig > 0.0 and rng is not None
    ht = hs = 0
    terminal_sum = 0.0
    draws = None
    if kopru:
        # Tum akisi bastan uret: bir bariyerde erken durmak sonraki yolun RNG'sini
        # LONG/SHORT'a gore kaydiramaz. Iki yon ayni seed ile common-random-number kullanir.
        draws = [[(rng.random(), rng.random()) for _ in path] for path in paths]
    for pi, path in enumerate(paths):
        res = 0
        prev = 1.0
        for hi, m in enumerate(path):
            if kopru:
                if side == "LONG":
                    p_stp = _bridge_cross(prev, m, stp_m, wick_sig, ust=False)
                    p_tgt = _bridge_cross(prev, m, tgt_m, wick_sig, ust=True)
                else:
                    p_stp = _bridge_cross(prev, m, stp_m, wick_sig, ust=True)
                    p_tgt = _bridge_cross(prev, m, tgt_m, wick_sig, ust=False)
                u_stp, u_tgt = draws[pi][hi]
                stp_hit = p_stp >= 1.0 or u_stp < p_stp
                tgt_hit = p_tgt >= 1.0 or u_tgt < p_tgt
                if stp_hit:                      # konservatif oncelik: stop
                    res = -1; break
                if tgt_hit:
                    res = 1; break
            else:
                if side == "LONG":
                    tgt_hit, stp_hit = m >= tgt_m, m <= stp_m
                else:
                    tgt_hit, stp_hit = m <= tgt_m, m >= stp_m
                if stp_hit:  # ayni adimda ikisi de: konservatif stop
                    res = -1; break
                if tgt_hit:
                    res = 1; break
            prev = m
        if res == 1:
            ht += 1
        elif res == -1:
            hs += 1
        elif path:
            final_price = price * path[-1]
            raw = ((final_price - payoff_entry) if side == "LONG"
                   else (payoff_entry - final_price))
            reward = abs(target - payoff_entry)
            risk = abs(payoff_entry - stop)
            terminal_sum += _clip(raw, -risk, reward)
    n = len(paths)
    if return_terminal:
        return ht / n, hs / n, terminal_sum / n
    return ht / n, hs / n


def mc_ilk_temas(paths, price: float, ust: float, alt: float,
                 wick_sig: float = 0.0, rng: Optional[random.Random] = None
                 ) -> Tuple[float, float, float]:
    """CANLI ilk-temas: bu barin MC yollarinda ufuk icinde ONCE ust seviye mi alt seviye
    mi vurulur. Kullanicinin 'aradaki fiyatta ilk once long mu short mu' sorusunun DOGRUDAN
    cevabi -> hangi LIMIT/pusu once tetiklenir. Doner (p_ust_once, p_alt_once, p_hicbiri).
    Gecmis kalibrasyon DEGIL: yalniz su anki oynaklik+yapi dagilimindan olasilik (kehanet degil).
    price>0 ve ust>alt olmali; yollar mc_simulate'ten (price'a gore CARPAN yolu).
    F5 fix: wick_sig>0 ve rng verilirse bar-ici fitil kesisi Brownian-kopruyle orneklenir
    (mc_first_passage ile ayni yontem). Pusu tetigi 'igne' ile ateslenirken basilan olasilik
    yalniz KAPANIS yolundan olculuyordu -> gercek temas sikligi sistematik dusuk basiliyordu.
    Ayni adimda iki seviye de kesilirse buyuk gecis-olasilikli taraf sayilir; tam esitlikte
    yarim-yarim bolunur. wick_sig=0 -> eski (kapanis-yolu) davranis."""
    if not paths or price <= 0 or ust <= alt:
        return 0.0, 0.0, 1.0
    u = ust / price
    d = alt / price
    kopru = wick_sig > 0.0 and rng is not None
    # Akis bastan uretilir: erken duran yol sonraki yolun RNG'sini kaydirmasin (determinizm).
    draws = ([[(rng.random(), rng.random()) for _ in path] for path in paths]
             if kopru else None)
    nu = nd = 0.0
    for pi, path in enumerate(paths):
        r = 0.0
        prev = 1.0
        for hi, m in enumerate(path):
            if kopru:
                p_u = _bridge_cross(prev, m, u, wick_sig, ust=True)
                p_d = _bridge_cross(prev, m, d, wick_sig, ust=False)
                uu, ud = draws[pi][hi]
                hit_u = p_u >= 1.0 or uu < p_u
                hit_d = p_d >= 1.0 or ud < p_d
                if hit_u and hit_d:
                    r = 1.0 if p_u > p_d else (-1.0 if p_d > p_u else 0.5)
                    break
                if hit_u:
                    r = 1.0
                    break
                if hit_d:
                    r = -1.0
                    break
            else:
                if m >= u:
                    r = 1.0
                    break
                if m <= d:
                    r = -1.0
                    break
            prev = m
        if r == 1.0:
            nu += 1.0
        elif r == -1.0:
            nd += 1.0
        elif r == 0.5:      # ayni adimda esit-olasilikli cift kesis: yarim-yarim
            nu += 0.5
            nd += 0.5
    n = len(paths)
    return nu / n, nd / n, max(0.0, n - nu - nd) / n


# ════════════════════════════════════════════════════════════════════════════
# TICK ORDER-FLOW + DONUS RADARI
# ════════════════════════════════════════════════════════════════════════════
def compute_orderflow(trades, cfg: Config) -> Optional[OrderFlow]:
    if not trades or len(trades) < 20:
        return None
    trades = sorted(trades, key=lambda t: t[2])
    nb = cfg.of_buckets
    per = max(1, len(trades) // nb)
    b_delta, b_price, b_sellvol, b_buyvol = [], [], [], []
    qtys = sorted(t[1] for t in trades)
    p90 = qtys[int(0.9 * (len(qtys) - 1))]
    whale = 0.0
    cvd = 0.0
    for bi in range(nb):
        seg = trades[bi * per:(bi + 1) * per] if bi < nb - 1 else trades[bi * per:]
        if not seg:
            continue
        dd = sv = bv = 0.0
        for p, q, _t, maker in seg:
            signed = -q if maker else q
            dd += signed
            if maker:
                sv += q
            else:
                bv += q
            if q >= p90:
                whale += signed
        cvd += dd
        b_delta.append(dd); b_price.append(seg[-1][0])
        b_sellvol.append(sv); b_buyvol.append(bv)
    if len(b_delta) < 3:
        return None
    dmu = mean(b_delta[:-1]); dsd = std(b_delta[:-1], dmu) or 1e-9
    smu = mean(b_sellvol[:-1]); ssd = std(b_sellvol[:-1], smu) or 1e-9
    bmu = mean(b_buyvol[:-1]); bsd = std(b_buyvol[:-1], bmu) or 1e-9
    return OrderFlow(cvd=cvd, delta_z=(b_delta[-1] - dmu) / dsd,
                     buckets_delta=b_delta, buckets_price=b_price, whale_delta=whale,
                     sell_climax_z=(b_sellvol[-1] - smu) / ssd,
                     buy_climax_z=(b_buyvol[-1] - bmu) / bsd, n=len(trades))


def reversal_radar(of: Optional[OrderFlow], st: Structure, cfg: Config) -> Tuple[int, float, List[str]]:
    """ONCU tick radari. +1 DIP donusu (yukari), -1 TEPE donusu (asagi). CVD-iraksama artik
    z-esikli (panel6'daki ~%87 gurultu tetigi degil)."""
    if of is None or of.n < 40 or not st.valid:
        return 0, 0.0, []
    bp, bd = of.buckets_price, of.buckets_delta
    if len(bp) < 4:
        return 0, 0.0, []
    up: List[str] = []
    dn: List[str] = []
    price = st.price
    to_low = (price - st.range_low) / st.atr if st.atr > 0 else 9
    to_high = (st.range_high - price) / st.atr if st.atr > 0 else 9
    # CVD-iraksama: fiyat yeni dip AMA delta bariz daha yuksek (z ile) -> satici tukendi
    # F14 fix: z-taban istatistigi SON kovayi dislar (compute_orderflow.delta_z ile ayni
    # sozlesme; kardes olcumler farkli normalizasyon konusmasin). len(bp)>=4 garantili.
    _bd_ref = bd[:-1] if len(bd) > 3 else bd
    dmu = mean(_bd_ref); dsd = std(_bd_ref, dmu) or 1e-9
    price_new_low = bp[-1] <= min(bp) + 1e-12
    price_new_high = bp[-1] >= max(bp) - 1e-12
    if price_new_low and (bd[-1] - min(bd)) / dsd > cfg.cvd_div_z:
        up.append("CVD-iraksama(satici tukendi)")
    if price_new_high and (max(bd) - bd[-1]) / dsd > cfg.cvd_div_z:
        dn.append("CVD-iraksama(alici tukendi)")
    if len(bp) >= 3:
        d1 = bp[-1] - bp[-2]; d2 = bp[-2] - bp[-3]
        if d1 < 0 and abs(d1) < abs(d2):
            up.append("ivme-kaybi(dusus yavasladi)")
        if d1 > 0 and abs(d1) < abs(d2):
            dn.append("ivme-kaybi(cikis yavasladi)")
    if of.sell_climax_z >= cfg.climax_z and to_low <= cfg.climax_prox_atr:
        up.append("satis-dorugu(kapitulasyon)")
    if of.buy_climax_z >= cfg.climax_z and to_high <= cfg.climax_prox_atr:
        dn.append("alim-dorugu(euforya)")
    if of.whale_delta > 0 and to_low <= cfg.whale_prox_atr:
        up.append("balina-alim(absorpsiyon)")
    if of.whale_delta < 0 and to_high <= cfg.whale_prox_atr:
        dn.append("balina-satim(dagitim)")
    if len(up) > len(dn) and len(up) >= 2:
        return 1, min(1.0, len(up) / 3.0), up
    if len(dn) > len(up) and len(dn) >= 2:
        return -1, min(1.0, len(dn) / 3.0), dn
    return 0, 0.0, (up + dn)


def orderflow_estimate(of: Optional[OrderFlow], rev_sign: int, rev_str: float, cfg: Config) -> Estimate:
    if of is None or of.n < 40:
        return Estimate("order-flow", 0.5, 0.0, 0, "veri yok", "flow")
    base = 0.5 + 0.5 * _clip(_tanh(of.delta_z / cfg.of_delta_scale), -1, 1) * cfg.of_delta_gain
    if rev_sign != 0:
        base = 0.5 + rev_sign * rev_str * cfg.of_rev_gain
    return Estimate("order-flow", _clip(base, 0.5 - cfg.macro_p_clip, 0.5 + cfg.macro_p_clip),
                    cfg.w_flow, of.n, "canli-tick", "flow")


# ════════════════════════════════════════════════════════════════════════════
# KATMAN B: TUM-TAHMINCI HEDGE + BLOK-BILINCLI BIRLESTIRME
# ════════════════════════════════════════════════════════════════════════════
def skill_weights(X, y, idxs, cs, atrs, cfg, rng) -> Dict[str, float]:
    """Purged expanding walk-forward proper-score agirliklari.

    Her fold yalniz gecmiste fit edilir; test baslangiciyla etiketi ortusen egitim
    satirlari purge edilir. Agirlik, uc-sinif Brier'da fold'un sinif-onseline olan
    iyilesmeden gelir. Dis katmanlar (mikro/senaryo) burada yer almaz.
    """
    names = ("lojistik", "analog", "ampirik", "markov", "montecarlo")
    out = {k: 0.0 for k in names}
    n = len(y)
    if n < 90:
        return out
    scores: Dict[str, List[float]] = {k: [] for k in names}
    bases: Dict[str, List[float]] = {k: [] for k in names}

    def brier(ps: Tuple[float, float, float], yy: int) -> float:
        return sum((ps[k] - (1.0 if yy == CLASSES[k] else 0.0)) ** 2
                   for k in range(3))

    # Uc dis zaman parcasi; her biri bir kez kullanilir.
    for frac0, frac1 in ((0.55, 0.70), (0.70, 0.85), (0.85, 1.00)):
        cut = max(45, int(frac0 * n))
        end = min(n, int(frac1 * n))
        if cut >= end:
            continue
        te0 = cut
        while te0 < end and idxs[te0] - idxs[cut - 1] <= cfg.horizon:
            te0 += 1
        if te0 >= end:
            continue
        Xtr, ytr = X[:cut], y[:cut]
        if len(set(ytr)) < 2:
            continue
        # 4s endpointler 15/16 ortusur. Skill agirligi ham 15m satir sayisindan
        # degil, sabit UTC fazli ve birbiriyle ortusmeyen etkin kohorttan ogrenilir.
        def _skill_cohort(j: int) -> bool:
            cm = cs[idxs[j]].close_ms if 0 <= idxs[j] < len(cs) else None
            return (((cm + 1) % (cfg.horizon * cfg.interval_ms) == 0)
                    if cm is not None else (idxs[j] % cfg.horizon == 0))
        tests = [j for j in range(te0, end) if _skill_cohort(j)]
        prior = normalize_probs((ytr.count(-1) + 1) / (len(ytr) + 3),
                                (ytr.count(0) + 1) / (len(ytr) + 3),
                                (ytr.count(1) + 1) / (len(ytr) + 3))
        lm = _fit_logistic(Xtr, ytr, tau=cfg.logistic_decay_tau)
        for j in tests:
            preds: Dict[str, Optional[Tuple[float, float, float]]] = {
                "lojistik": _pred_logistic(lm, X[j]),
                "analog": _knn_pred(Xtr, ytr, X[j], cfg.knn_k)
                          if len(Xtr) >= cfg.knn_k else None,
                "ampirik": None,
                "markov": _markov_pred_at(cs, idxs[j], atrs, cfg),
            }
            ep, en = _emp_pred(Xtr, ytr, X[j])
            if en >= 10:
                preds["ampirik"] = ep
            for name, ps in preds.items():
                if ps is not None:
                    scores[name].append(brier(ps, y[j]))
                    bases[name].append(brier(prior, y[j]))  # ayni timestamp/prior
        # MC pahali: fold basina en fazla 8 nokta; toplamda min OOS kapisi asilir.
        step = max(1, len(tests) // 8)
        for j in tests[::step][:8]:
            ps = _mc_dir_at(cs, idxs[j], atrs, cfg,
                            random.Random(rng.randrange(1, 2 ** 31)))
            if ps is not None:
                scores["montecarlo"].append(brier(ps, y[j]))
                bases["montecarlo"].append(brier(prior, y[j]))

    caps = {"lojistik": 1.4, "analog": 1.4, "ampirik": 1.4,
            "markov": 1.0, "montecarlo": cfg.w_mc_cap}
    for name in names:
        min_n = cfg.skill_mc_min_oos if name == "montecarlo" else cfg.skill_min_oos
        if len(scores[name]) >= min_n and len(scores[name]) == len(bases[name]):
            base = mean(bases[name])
        else:
            base = 0.0
        if base > 1e-12:
            improvement = max(0.0, (base - mean(scores[name])) / base)
            out[name] = _clip(4.0 * improvement, 0.0, caps[name])
    return out


def combine_multiclass(estimates: List[Estimate]
                       ) -> Tuple[Tuple[float, float, float], float, float, Dict[str, float]]:
    """Blok-bilincli agirlikli log-pool; (DOWN,FLAT,UP) olasiligi doner.

    R7 (REPORT_3): bloklar log-pool ve uzlasmazlik olcumunde BAGIMSIZ varsayilir;
    oysa mc (drift) ile flow ayni of.delta_z girdisini paylasir. Blok uyumu bu
    yuzden bagimsiz teyit sayilmaz; ifsa _decide_core drift satirinda ve ekranda."""
    act = [e for e in estimates if e.weight > 0 and e.n > 0]
    if not act:
        return (1 / 3, 1 / 3, 1 / 3), 1.0, 0.0, {}
    blocks: Dict[str, List[Estimate]] = {}
    for e in act:
        blocks.setdefault(e.block, []).append(e)
    block_p: Dict[str, float] = {}
    logs = [0.0, 0.0, 0.0]
    tw = 0.0
    directional: List[float] = []
    for bname, es in blocks.items():
        wsum = sum(x.weight for x in es)
        bp = [sum(x.weight * x.probs()[k] for x in es) / wsum for k in range(3)]
        bp = list(normalize_probs(*bp))
        bw = max(x.weight for x in es)      # blok TEK kaynak gibi tartilir (max), toplam degil
        block_p[bname] = bp[2]
        directional.append(bp[2] - bp[0])
        for k in range(3):
            logs[k] += bw * math.log(max(1e-9, bp[k]))
        tw += bw
    probs = tuple(_softmax([v / tw for v in logs])) if tw > 0 else (1 / 3, 1 / 3, 1 / 3)
    opinion = [v for v in directional if abs(v) > 0.02]
    dis = (std(opinion) / 2.0) if len(opinion) >= 2 else 0.0  # [-1,+1] skoru -> eski p olcegi
    return normalize_probs(*probs), dis, tw, block_p


def ensemble_side_conflict(side: str, probs: Tuple[float, float, float],
                           total_weight: float, cfg: Config) -> bool:
    """R1 (REPORT_3): saf SOZLESME-TRIPWIRE predikati — side, probs argmax'i ile
    celisiyor mu. Normal decide akisinda side=argmax(probs) oldugu icin False
    doner (olu-kapi tespiti); yalniz ileriye-donuk regresyon bekcisi + birim test."""
    if total_weight < cfg.ens_gate_minw or side not in ("LONG", "SHORT"):
        return False
    cls = argmax_class(normalize_probs(*probs), cfg.tie_eps_rel)
    if cls == 0:
        return True
    predicted = "LONG" if cls > 0 else "SHORT"
    return predicted != side


# ════════════════════════════════════════════════════════════════════════════
# SEVIYE + EV
# ════════════════════════════════════════════════════════════════════════════
def supurme_olcumu(cs: List[Candle], atrs: List[float], cfg: Config
                   ) -> Tuple[float, float, int, int, bool]:
    """Sembolun KENDI gecmisinden supurme derinligi olcumu: 'onceki sweep_win-bar
    ekstremini gecip sweep_reclaim_bars icinde GERI ALINAN' fitillerin derinligi (ATR).
    Doner: (pad_lo, pad_hi, n_lo, n_hi, kalibre). Pay = max(sabit, q80) kirpilmis;
    yetersiz olcum -> eski sabit pad (durust cold-start). NO-LOOKAHEAD: yalniz gecmis."""
    w, k = cfg.sweep_win, cfg.sweep_reclaim_bars
    lo_d: List[float] = []
    hi_d: List[float] = []
    for i in range(w + 2, len(cs) - 1):
        a = atrs[i]
        if a <= 0:
            continue
        seg = cs[i - w:i]
        ref_lo = min(c.low for c in seg)
        if cs[i].low < ref_lo and any(cs[j].close > ref_lo
                                      for j in range(i, min(i + 1 + k, len(cs)))):
            lo_d.append((ref_lo - cs[i].low) / a)
        ref_hi = max(c.high for c in seg)
        if cs[i].high > ref_hi and any(cs[j].close < ref_hi
                                       for j in range(i, min(i + 1 + k, len(cs)))):
            hi_d.append((cs[i].high - ref_hi) / a)
    def _pad(d):
        if len(d) < cfg.sweep_min_n:
            return cfg.inval_pad_atr, False
        return _clip(max(cfg.inval_pad_atr, _quantile(d, cfg.sweep_q)),
                     cfg.inval_pad_atr, cfg.sweep_pad_cap), True
    p_lo, c_lo = _pad(lo_d)
    p_hi, c_hi = _pad(hi_d)
    return p_lo, p_hi, len(lo_d), len(hi_d), (c_lo and c_hi)


def scenario_levels(st: Structure, side: str, cfg: Config,
                    pad_atr: Optional[float] = None,
                    entry_price: Optional[float] = None) -> Tuple[float, float, float]:
    price, a = (entry_price if entry_price is not None else st.price), st.atr
    pad = (pad_atr if pad_atr is not None else cfg.inval_pad_atr) * a
    gap = cfg.min_target_atr * a
    if side == "LONG":
        res = [p for p in st.swing_highs if p > price + gap] + \
              ([st.range_high] if st.range_high > price + gap else [])
        target = min(res) if res else price + cfg.barrier_atr * a
        sup = [p for p in st.swing_lows if p < price] + [st.range_low]
        stop = (max(sup) if sup else st.range_low) - pad
        stop = min(stop, price - 0.3 * a)
    else:
        sup = [p for p in st.swing_lows if p < price - gap] + \
              ([st.range_low] if st.range_low < price - gap else [])
        target = max(sup) if sup else price - cfg.barrier_atr * a
        res = [p for p in st.swing_highs if p > price] + [st.range_high]
        stop = (min(res) if res else st.range_high) + pad
        stop = max(stop, price + 0.3 * a)
    return price, target, stop


@dataclass
class Scenario:
    side: str
    entry: float
    target: float
    stop: float
    p_target: float
    p_stop: float
    ev: float          # ATR-normalize beklenen deger (maliyet sonrasi)
    rr: float


def executable_entry_price(snap: Snapshot, side: str, anchor: float,
                           context: DecisionContext) -> float:
    """LIVE market karari icin ask/bid; OFFLINE'da bar kapanisi (simule edilebilir)."""
    if context.mode == "OFFLINE":
        return anchor
    if snap.book:
        key = "ask" if side == "LONG" else "bid"
        try:
            p = float(snap.book.get(key, 0.0))
            if p > 0:
                return p
        except (TypeError, ValueError) as exc:
            snap.source_errors.append("book executable fiyat okunamadi: " + str(exc)[:80])
    # Book yoksa mark salt referanstir; maliyet modeli varsayilan kaymayi ayrica keser.
    return float(snap.live_price or anchor)


def build_scenario(st, side, paths, cost, cfg, rng: Optional[random.Random] = None,
                   pad_atr: Optional[float] = None,
                   entry_price: Optional[float] = None) -> Scenario:
    entry, target, stop = scenario_levels(st, side, cfg, pad_atr=pad_atr,
                                          entry_price=entry_price)
    # bar-ici fitil sigma'si: ATR fiyat-oranindan (Brown E[range]~1.6*sigma); veri-goreli
    wick_sig = ((st.atr / st.price) / cfg.bridge_range_div
                if cfg.bridge_range_div > 0 and st.price > 0 and rng is not None else 0.0)
    p_t, p_s, terminal = mc_first_passage(paths, st.price, target, stop, side,
                                           wick_sig=wick_sig, rng=rng,
                                           return_terminal=True,
                                           payoff_entry=entry)
    if side == "LONG":
        reward = target - entry
        risk = entry - stop
    else:
        reward = entry - target
        risk = stop - entry
    reward = max(reward, 0.0)
    risk = max(risk, 1e-9)
    ev_abs = p_t * reward - p_s * risk + terminal - cost
    ev = ev_abs / st.atr if st.atr > 0 else 0.0
    rr = (reward - cost) / (risk + cost) if (risk + cost) > 0 else 0.0
    return Scenario(side, entry, target, stop, p_t, p_s, ev, rr)


# ════════════════════════════════════════════════════════════════════════════
# KARAR
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class Decision:
    karar: str
    prob: int
    entry: Optional[float]
    target: Optional[float]
    stop: Optional[float]
    rr: float
    p_target: float
    reversal_risk: int
    weak: bool
    sebep: str
    estimates: List[Estimate]
    rev_sign: int
    rev_reasons: List[str]
    disagree: float
    regime: str
    ev: float
    warn: str
    ev_long: float
    ev_short: float
    block_p: Dict[str, float]
    edge: float = 0.0
    score_label: str = ""
    calibrated: bool = False
    rev_str: float = 0.0
    funding_bound_atr: float = 0.0     # settle ufuktaysa EV/RR maliyetine eklenen funding UST-SINIRI (ATR orani; 0=uygulanmadi)
    fc: Optional[Dict] = None          # ONCU TAHMIN hammaddesi (yon/pup/q10-q50-q90; analyze doldurur)
    fc_rapor: Optional[List[str]] = None  # onceki tahminlerin COZUM+karne satirlari (render basar)
    plan: Optional[Dict] = None        # ISLEM PLANI hammaddesi: canli MC ilk-temas (ust/alt) + gir seviyeleri
    btc_leader: Optional[BtcLeaderState] = None  # STEP4 BTC bas-at tanisi (rapor + veto/confirm kaniti)
    cost_abs: float = 0.0                 # F4 (FABLE6_5): karar aninda kullanilan gidis-donus maliyeti (fiyat birimi)
    scen144: Optional["Scenario144"] = None  # F3: karar-ONCESI 144-hucre siniflandirmasi (yon uretmez)
    aile: str = ""                        # F3: karar-oncesi 6-aile etiketi (gosterim/log)
    scen_driven: bool = False             # F9: yon istatistikten DEGIL senaryo side_hint'inden geldi (kanitlanmamis kenar)
    scen_side: Optional[str] = None       # F9: senaryonun urettigi yon (LONG/SHORT); scen_driven iken dolu
    oncu_driven: bool = False             # ONCU: yon istatistikten DEGIL oncu leading sinyalden geldi (kanitlanmamis kenar)
    oncu_side: Optional[str] = None       # ONCU: oncu sinyalin urettigi yon (LONG/SHORT); oncu_driven iken dolu
    oncu: Optional[Dict] = None           # ONCU: leading-sinyal hammaddesi (side/guc/tur/kanit/expansion); gosterim/PUSU
    p_down: float = 0.0
    p_flat: float = 0.0
    p_up: float = 0.0
    gate_code: str = ""
    mode: str = "LIVE"
    predicted_at_ms: Optional[int] = None
    target_end_ms: Optional[int] = None
    data_watermark_ms: Optional[int] = None
    model_hash: str = ""
    code_hash: str = ""
    feature_hash: str = ""
    protocol_id: str = ""
    diagnostics: List[str] = field(default_factory=list)
    erken: Optional[Dict] = None           # S3: erken-uyari hammaddesi (analyze doldurur; render basar)


def vol_regime(cs: List[Candle], cfg: Config) -> str:
    if len(cs) < 5:
        return "NORMAL"
    trs = [true_range(cs[i], cs[i - 1]) for i in range(1, len(cs))]
    win = cfg.regime_win
    seg = trs[-win:] if len(trs) >= win else trs
    med = sorted(seg)[len(seg) // 2]
    ratio = (mean(seg[-3:]) / med) if med > 0 else 1.0
    # Esikler MUTLAK (2.0/1.4/0.6/0.85) DEGIL -> ratio'nun KENDI tarihsel dagiliminin
    # quantile'lari. Boylece "asiri/sikisik" sembolun OYNAKLIK KARAKTERINE gore olculur
    # (BTC ile DOGE ayni sabitle etiketlenmez). Yeterli gecmis yoksa eski sabitlere duser.
    ratios: List[float] = []
    if len(trs) > win:
        for t in range(win, len(trs)):
            s = trs[t - win:t]
            m = sorted(s)[len(s) // 2]
            if m > 0:
                ratios.append(mean(trs[t - 3:t]) / m)
    if len(ratios) >= cfg.regime_min_n:
        ex = _quantile(ratios, cfg.regime_q_ext)
        hi = _quantile(ratios, cfg.regime_q_hi)
        lo = _quantile(ratios, cfg.regime_q_lo)
        cq = _quantile(ratios, cfg.regime_q_comp)
        if ratio >= ex:
            return "EXTREME"
        if ratio >= hi:
            return "EXPANDING"
        if ratio <= cq:
            return "COMPRESSED"
        if ratio <= lo:
            return "LOW"
        return "NORMAL"
    if ratio >= 2.0:
        return "EXTREME"
    if ratio >= 1.4:
        return "EXPANDING"
    if ratio <= 0.6:
        return "COMPRESSED"
    if ratio <= 0.85:
        return "LOW"
    return "NORMAL"


def taze_donus(cs: List[Candle], htf: List[Candle], cfg: Config) -> Tuple[bool, str]:
    """Egilim/rejim DONUSU son taze_donus_bars mum icinde mi? Saatlik kullanicinin
    donus-penceresine denk gelen calistirmasi KENDINI BILSIN: kehanet degil, durum tespiti.
    Tetikler: (a) 15m egilim isareti dondu (iki tarafta da anlamli buyuklukle),
    (b) vol rejimi NORMAL/LOW'dan EXTREME'e sicradi, (c) 1s trend isareti dondu."""
    n = cfg.taze_donus_bars
    if len(cs) < 30 + n:
        return False, ""
    mb_now = market_bias(cs, cfg)
    mb_prev = market_bias(cs[:-n], cfg)
    if (abs(mb_now) >= cfg.taze_donus_mb and abs(mb_prev) >= cfg.taze_donus_mb
            and (mb_now > 0) != (mb_prev > 0)):
        return True, f"15m egilim {'ASAGI->YUKARI' if mb_now > 0 else 'YUKARI->ASAGI'} (~{n} mum)"
    vr_now = vol_regime(cs, cfg)
    vr_prev = vol_regime(cs[:-n], cfg)
    if vr_now == "EXTREME" and vr_prev in ("NORMAL", "LOW", "COMPRESSED"):
        return True, f"vol rejimi {vr_prev}->EXTREME (~{n} mum)"
    if htf and len(htf) > 22:
        hb_now = htf_bias(htf, cfg)
        hb_prev = htf_bias(htf[:-1], cfg)
        if hb_now != 0 and hb_prev != 0 and hb_now != hb_prev:
            return True, f"4s trend {'ASAGI->YUKARI' if hb_now > 0 else 'YUKARI->ASAGI'}"
    return False, ""


def _oncu_yon(cs: List[Candle], htf: List[Candle], scen: Optional["Scenario144"],
              rev_sign: int, rev_str: float, cfg: Config) -> Dict:
    """ONCU (leading) SINYAL FUZYONU — kullanici direktifi (karar SURUCUSU).
    YALNIZ kapanmis-mum PIT-temiz kaynaklardan (ledger OKUMAZ -> lookahead yok):
      (1) reversal_radar (tick DIP->YUKARI / TEPE->ASAGI),
      (2) taze_donus (15m egilim / vol-rejim / 4s trend donusu),
      (3) senaryo V-DIP(2)->LONG, V-TOP(3)->SHORT, EXH(8)->trend tersi (side_hint yonu),
      (4) sikisma->genisleme (COMPRESSED/LOW -> EXPANDING/EXTREME): 'patlama yakin', YONSUZ.
    GECIKMELI pump/dump (olay 4/5) YON KAYNAGI DEGILDIR (kullanici: 'kaziyip at').
    Doner: {side, guc(0..1), tur, kanitlar, expansion}. guc = yonlu-kanit-sayisi/2 kirpik."""
    long_v = 0
    short_v = 0
    kanit: List[str] = []
    expansion = False
    # (1) tick donus radari (dedektor >=2 ic-kanitla ateslenir -> tek isaret bile guclu)
    if rev_sign > 0 and rev_str > 0:
        long_v += 1; kanit.append("tick-radar DIP->YUKARI")
    elif rev_sign < 0 and rev_str > 0:
        short_v += 1; kanit.append("tick-radar TEPE->ASAGI")
    # (2) taze donus (egilim/rejim/4s)
    try:
        td, td_msg = taze_donus(cs, htf, cfg)
        if td and "->YUKARI" in td_msg:
            long_v += 1; kanit.append("taze-donus: " + td_msg)
        elif td and "->ASAGI" in td_msg:
            short_v += 1; kanit.append("taze-donus: " + td_msg)
    except Exception:
        pass
    # (3) senaryo olayi — V-DIP/V-TOP/EXH (pump/dump 4/5 HARIC)
    try:
        ev = getattr(scen, "event_idx", 0) if scen is not None else 0
        if ev == 2:
            long_v += 1; kanit.append("senaryo V-DIP (dipte red)")
        elif ev == 3:
            short_v += 1; kanit.append("senaryo V-TOP (tepede red)")
        elif ev == 8:                       # EXH tukenme: donus riski -> side_hint yonu
            _sh = getattr(scen, "side_hint", "NEUTRAL")
            if _sh == "LONG":
                long_v += 1; kanit.append("senaryo EXH (tukenme -> donus)")
            elif _sh == "SHORT":
                short_v += 1; kanit.append("senaryo EXH (tukenme -> donus)")
    except Exception:
        pass
    # (4) vol-rejim gecisi: sikisma -> genisleme = patlama yakin (YONSUZ; seviye/pusu genisletir)
    try:
        if vol_regime(cs[:-1], cfg) in ("COMPRESSED", "LOW") and \
                vol_regime(cs, cfg) in ("EXPANDING", "EXTREME"):
            expansion = True
            kanit.append("vol-rejim sikisma->genisleme (patlama yakin)")
    except Exception:
        pass
    n_dir = max(long_v, short_v)
    side = "LONG" if long_v > short_v else ("SHORT" if short_v > long_v else "NEUTRAL")
    guc = min(1.0, n_dir / 2.0)
    tur = ("DONUS-YUKARI" if side == "LONG" else
           "DONUS-ASAGI" if side == "SHORT" else
           "SIKISMA-PATLAMA" if expansion else "YOK")
    return {"side": side, "guc": guc, "tur": tur, "kanitlar": kanit, "expansion": expansion}


# ════════════════════════════════════════════════════════════════════════════
# S3: ERKEN UYARI KATMANI — AYRI, KANITLANMAMIS, KARAR KAPISI DEGIL
# Olusacak pump/dump/V-donus/trend-degisim/sikisma-patlamasini MEVCUT dedektorlerden
# (taze_donus, reversal_radar, senaryo olaylari, vol-rejim gecisi, mikro #15/#18) + ONCEKI
# kosunun forecast kaymasindan toplayip 15-30dk RISKINI OLASILIK/UYARI dilinde bildirir.
# Yon URETMEZ, karar/EV/kapi DEGISTIRMEZ. NO-LOOKAHEAD (yalniz kapanmis mum). Kesin DEGIL;
# olculen isabet ayri sicilde (yon_erken_uyari) MEKANIK dogrulanir (DSR=N/A disiplini).
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class ErkenUyari:
    risk_var: bool = False
    tur: str = "YOK"             # PUMP | DUMP | V-DONUS | TREND-DEGISIM | SIKISMA-PATLAMA | YOK
    yon_egilim: str = "NEUTRAL"  # LONG | SHORT | NEUTRAL (uyarilan hareketin OLASI yonu)
    guc: float = 0.0             # 0..1 (bagimsiz kanit sayisi / 3, kirpik)
    kanitlar: List[str] = field(default_factory=list)
    onceki_kosu_notu: str = ""


def erken_uyari(symbol: str, snap: Snapshot, st: Optional[Structure],
                scen: Optional["Scenario144"], cfg: Config) -> ErkenUyari:
    """AYRI uyari katmani (karar kapisi DEGIL). Mevcut dedektorleri + onceki-kosu
    kaymasini toplar. Tek kaynaga guvenmez: >= cfg.erken_uyari_min_kanit BAGIMSIZ kanit
    gerektirir. Kehanet degil, KANITLANMAMIS risk uyarisi."""
    if not getattr(cfg, "erken_uyari_enabled", True):
        return ErkenUyari()
    cs = snap.candles
    if st is None or not getattr(st, "valid", False) or st.atr <= 0 or len(cs) < 30:
        return ErkenUyari()
    kanitlar: List[str] = []
    vdon = trend = sikisma = 0     # tur oy sayaclari (ONCU: pump/dump sayaclari kaldirildi)
    yon_long = yon_short = 0
    # (1) taze donus (egilim/rejim/1s donusu son N mum)
    try:
        td, td_msg = taze_donus(cs, snap.htf, cfg)
        if td:
            kanitlar.append("taze-donus: " + td_msg)
            trend += 1
            if "->YUKARI" in td_msg:
                yon_long += 1
            elif "->ASAGI" in td_msg:
                yon_short += 1
    except Exception:
        pass
    # (2) reversal radar (oncu tick DIP/TEPE)
    try:
        rev_sign, rev_str, rev_r = reversal_radar(snap.orderflow, st, cfg)
        if rev_sign != 0 and rev_str > 0:
            kanitlar.append(f"tick-radar {'DIP->YUKARI' if rev_sign > 0 else 'TEPE->ASAGI'}"
                            + (f" ({', '.join(rev_r[:2])})" if rev_r else ""))
            vdon += 1
            yon_long += 1 if rev_sign > 0 else 0
            yon_short += 1 if rev_sign < 0 else 0
    except Exception:
        pass
    # (3) senaryo olayi (V_DIP/V_TOP/EXH/SQZ) — ONCU degisikligi: gecikmeli PUMP/DUMP
    # (olay 4/5) erken-uyari YON oyundan CIKARILDI (kullanici: 'kaziyip at'); olay etiketi
    # senaryoda telemetri olarak durur ama burada donus/patlama oyu URETMEZ.
    try:
        ev_idx = getattr(scen, "event_idx", 0) if scen is not None else 0
        if ev_idx == 2:
            vdon += 1; yon_long += 1; kanitlar.append("senaryo: V-DIP (dipte red)")
        elif ev_idx == 3:
            vdon += 1; yon_short += 1; kanitlar.append("senaryo: V-TOP (tepede red)")
        elif ev_idx == 8:
            vdon += 1; kanitlar.append("senaryo: EXH (tukenme -> donus riski)")
        elif ev_idx == 9:
            sikisma += 1; kanitlar.append("senaryo: SQZ (sikisma -> patlama yakin)")
    except Exception:
        pass
    # (4) vol-rejim gecisi: sikisma -> genisleme = patlama yakin
    try:
        vr_prev = vol_regime(cs[:-1], cfg)
        vr_now = vol_regime(cs, cfg)
        if vr_prev in ("COMPRESSED", "LOW") and vr_now in ("EXPANDING", "EXTREME"):
            sikisma += 1
            kanitlar.append(f"vol-rejim {vr_prev}->{vr_now} (patlama yakin)")
    except Exception:
        pass
    # (5) mikro OI-flush (#15) / squeeze-yakiti (#18)
    try:
        for m in classify_micro(snap, st, cfg):
            if m.mid == 15:
                vdon += 1; kanitlar.append("mikro #15 OI-flush (kaldirac temizligi)")
                yon_long += 1 if m.side == "LONG" else 0
                yon_short += 1 if m.side == "SHORT" else 0
            elif m.mid == 18:
                sikisma += 1; kanitlar.append("mikro #18 squeeze-yakiti")
                yon_long += 1 if m.side == "LONG" else 0
                yon_short += 1 if m.side == "SHORT" else 0
    except Exception:
        pass
    # (6) ONCEKI kosu kaymasi: onceki forecast yonu ile simdiki 15m egilim TERS ise
    onceki = ""
    try:
        prev = None
        for r in reversed(_fc_yukle()):
            if r.get("symbol") == symbol and r.get("bar_ms") != cs[-1].close_ms:
                prev = r
                break
        if prev is not None and prev.get("dir") in (1, -1):
            now_bias = market_bias(cs, cfg)
            if abs(now_bias) > 0.2 and (prev["dir"] > 0) != (now_bias > 0):
                trend += 1
                onceki = (f"onceki kosu tahmini {'YUKARI' if prev['dir'] > 0 else 'ASAGI'} iken "
                          f"simdiki 15m egilim {'YUKARI' if now_bias > 0 else 'ASAGI'} (kayma)")
                kanitlar.append(onceki)
                yon_long += 1 if now_bias > 0 else 0
                yon_short += 1 if now_bias < 0 else 0
    except Exception:
        pass
    n_kanit = len(kanitlar)
    if n_kanit < max(1, int(getattr(cfg, "erken_uyari_min_kanit", 2))):
        return ErkenUyari(onceki_kosu_notu=onceki)
    turlar = [("V-DONUS", vdon),
              ("TREND-DEGISIM", trend), ("SIKISMA-PATLAMA", sikisma)]
    turlar.sort(key=lambda t: -t[1])
    tur = turlar[0][0] if turlar[0][1] > 0 else "TREND-DEGISIM"
    yon = "LONG" if yon_long > yon_short else ("SHORT" if yon_short > yon_long else "NEUTRAL")
    return ErkenUyari(True, tur, yon, min(1.0, n_kanit / 3.0), kanitlar, onceki)


def kayma_alarmi(symbol: str, cfg: Config) -> Tuple[bool, float, int]:
    """KAYMA (drift) ALARMI: son kayma_win cozulmus sinyalin isabeti kayma_esik altina
    dustuyse motor kendine guvenini kisar. 'Model tutmuyor'un ERKEN istatistiksel tespiti
    (CUSUM-lite). Doner: (alarm, son_isabet, n)."""
    rows = [r for r in _load_signals()
            if r.get("symbol") == symbol and r.get("outcome") in ("HIT", "STOP", "DIR_OK", "DIR_BAD")]
    son = rows[-cfg.kayma_win:]
    n = len(son)
    if n < max(8, cfg.kayma_win // 2 + 2):
        return False, 0.5, n
    rate = sum(1 for r in son if r.get("outcome") in ("HIT", "DIR_OK")) / n
    return rate <= cfg.kayma_esik, rate, n


def yon_monokultur(symbol: str, cfg: Config) -> Tuple[bool, str, float, int]:
    """TEK-YON UYARISI: son monokultur_win sinyalin buyuk cogunlugu ayni yondeyse motor
    tek tarafa kilitlenmis olabilir (saha belirtisi: 24/24 LONG). SONUC BEKLEMEDEN calisir
    (acik sinyaller de sayilir) -> kayma alarmindan 12-48 saat once yakalar. Gosterim-amacli."""
    rows = [r for r in _load_signals()
            if r.get("symbol") == symbol and r.get("side") in ("LONG", "SHORT")]
    son = rows[-cfg.monokultur_win:]
    n = len(son)
    if n < max(6, cfg.monokultur_win // 2):
        return False, "", 0.0, n
    nl = sum(1 for r in son if r.get("side") == "LONG")
    pay_l, pay_s = nl / n, (n - nl) / n
    if pay_l >= cfg.monokultur_pay:
        return True, "LONG", pay_l, n
    if pay_s >= cfg.monokultur_pay:
        return True, "SHORT", pay_s, n
    return False, "", max(pay_l, pay_s), n


def rejim_ailesi(snap: Snapshot, cfg: Config) -> str:
    """Kaba YONLU rejim ailesi: YUKARI-TREND / ASAGI-TREND / YATAY / ASIRI-VOL.
    Saha bulgusu: eski 'rejim' yalniz volatilite olcuyordu (89/100 NORMAL), YON hic
    olculmuyordu -> senaryolar tek rejimde araniyordu. Bu aile o boslugu doldurur."""
    cs = snap.candles
    if len(cs) < 30:
        return "YATAY"
    if vol_regime(cs, cfg) == "EXTREME":
        return "ASIRI-VOL"
    tb = htf_bias(snap.htf, cfg) if snap.htf else 0
    mb = market_bias(cs, cfg)
    # ERKEN-YATAY (kapi bulgusu): 1s MA-20 penceresi chop'a gecisi ~18 saat gec goruyordu.
    # 15m'de egilim SURDURULMUS bicimde zayif + yon-verimliligi dusukse 1s'i bekleme.
    _n4 = cfg.taze_donus_bars
    _mb_once = market_bias(cs[:-_n4], cfg) if len(cs) > 30 + _n4 else mb
    _er15 = efficiency_ratio(cs, len(cs) - 1, 10)
    if abs(mb) < 0.30 and abs(_mb_once) < 0.30 and _er15 < cfg.er_trend_min:
        return "YATAY"
    # 15m egilim guclu ve 1s ile CELISIYORSA 15m'e oncelik (donusleri 20 saat once yakala).
    # SURDURULMUS sart (canli SOL bulgusu): tek anlik tepki sicramasi (dip-bounce) aileyi
    # ceviriyordu (1s ASAGI iken aile YUKARI yazdi). Simdi hem simdiki hem 4-mum-onceki
    # egilim ayni yonde guclu olmali -> tepki degil, gercek 15m trendi.
    if (abs(mb) >= 0.35 and abs(_mb_once) >= 0.35 and (mb > 0) == (_mb_once > 0)
            and tb != 0 and (mb > 0) != (tb > 0)):
        return "YUKARI-TREND" if mb > 0 else "ASAGI-TREND"
    if tb > 0:
        return "YUKARI-TREND"
    if tb < 0:
        return "ASAGI-TREND"
    # 1s YATAY iken 15m-yedegi de SURDURULMUS egilim ister (canli BTC bulgusu:
    # tek anlik +0.3 sicrama, 1s yatayken aileyi YUKARI-TREND yapmisti).
    if mb >= 0.3 and _mb_once >= 0.3:
        return "YUKARI-TREND"
    if mb <= -0.3 and _mb_once <= -0.3:
        return "ASAGI-TREND"
    return "YATAY"


# ── R5 (REPORT_3): UC REJIM TAKSONOMISININ TEK-KAYNAK KANONIK GORUNUMU ──
# Denetim bulgusu: 5-durumlu vol_regime, 4-aileli rejim_ailesi ve 6-aileli
# REGIME_FAMILY6 ciktida bagimsiz taksonomiler gibi geziyordu ve karar-etkileri
# belirsizdi. KANONIK TANIM (tek yerde):
#   * vol_regime   -> KARARA GIREN TEK ALAN; o da yalniz iki yerde: EXTREME'de
#     gosterilen-guven kismasi (conf_extreme_shrink) ve taze_donus uyarisi.
#     (adaptive_disagree_max tuketimi canli_only=True iken devre disidir.)
#   * rejim_ailesi -> gosterim + mikro-kalip SIRALAMA onseli (karar/pusu yonu uretmez).
#   * family6      -> YALNIZ gosterim (12 senaryo-rejiminin ekran haritasi).
# Bu fonksiyon uc gorunumu tek nesnede, karar-etkisi etiketiyle dondurur; render tek
# satirda basar. Karar mantigina DOKUNMAZ (salt okuma/sunum birlestirme).
@dataclass
class RegimeView:
    vol: str
    aile: str
    family6: str
    karar_etkisi: str


def rejim_gorunumu(snap: Snapshot, cfg: Config,
                   scen: Optional["Scenario144"] = None) -> RegimeView:
    vol = vol_regime(snap.candles, cfg)
    aile = rejim_ailesi(snap, cfg)
    fam6 = scen.family6 if scen is not None else "BELIRSIZ"
    etki = ("vol=EXTREME -> gosterilen-guven kismasi AKTIF" if vol == "EXTREME"
            else "karara giren rejim alani yok (vol!=EXTREME)")
    return RegimeView(vol, aile, fam6, etki)


def _wait(sebep, estimates=None, disagree=1.0, regime="NORMAL", block_p=None,
          ev_long: float = 0.0, ev_short: float = 0.0) -> Decision:
    # ev_long/ev_short: senaryolar HESAPLANDIKTAN sonra BEKLE'ye dusen yollar gercek
    # EV'leri tasir -> acik-sinyal takibi 'GUC KAYBI' olcumunu BEKLE'de de yapabilir.
    return Decision("BEKLE", 0, None, None, None, 0.0, 0.0, 0, False, sebep,
                    estimates or [], 0, [], disagree, regime, 0.0, "",
                    ev_long, ev_short, block_p or {})


# ════════════════════════════════════════════════════════════════════════════
# SENARYO KATMANI (144) — HIBRIT: 12 vadeli-rejim x 12 olay
# Rejim = D1(trend) x D2(volatilite) x D3(konum) x D4(turev) bilesimi -> tek isimli rejim.
# yon2 motoruna DOKUNMAZ; giris/cikis seviyeleri hep yon2'den gelir. Bu katman "ne oluyor"u
# sade dille soyler + kac haberci hizalandigini sayar (dokuman §4). no-lookahead.
# ════════════════════════════════════════════════════════════════════════════
REGIME_NAMES = {
    0: "BELIRSIZ", 1: "TREND-UP-STRONG", 2: "TREND-UP-PULLBACK", 3: "TREND-DOWN-STRONG",
    4: "TREND-DOWN-BOUNCE", 5: "RANGE-TIGHT", 6: "RANGE-WIDE", 7: "BREAKOUT-EXPANSION",
    8: "REVERSAL-BOTTOM", 9: "REVERSAL-TOP", 10: "ACCUMULATION", 11: "DISTRIBUTION",
    12: "VOL-PATLAMA(proxy)",
}
REGIME_FAMILY6 = {
    0: "BELIRSIZ", 1: "TREND-YUKARI", 2: "TREND-YUKARI",
    3: "TREND-ASAGI", 4: "TREND-ASAGI", 5: "YATAY", 6: "YATAY",
    7: "KIRILIM-VOL", 12: "KIRILIM-VOL", 8: "DONUS", 9: "DONUS",
    10: "POZISYONLANMA", 11: "POZISYONLANMA",
}
EVENT_NAMES = {1: "BAZ", 2: "V_DIP", 3: "V_TOP", 4: "PUMP", 5: "DUMP", 6: "SFP",
               7: "FBO", 8: "EXH", 9: "SQZ", 10: "SH", 11: "FFLIP", 12: "VOLX*"}
# manset onceligi (dokuman §3): V_DIP/V_TOP > SFP > PUMP/DUMP > EXH > SQZ > VOLX* > FFLIP > FBO > SH > BAZ
EVENT_PRIORITY = [2, 3, 6, 4, 5, 8, 9, 12, 11, 7, 10, 1]
# canlida ONCEDEN kesin iddia edilemeyen olaylar (gelecek-pencereli veya yon-belirsiz) -> "izleniyor"
WATCH_EVENTS = {7, 9, 10, 11}   # FBO, SQZ, SH, FFLIP -> yon belirsiz/gelecek-pencereli
# ── R4 (REPORT_3): 144 hucre bir KIMLIK ALANIDIR, 144 ayri davranis DEGILDIR. ──
# Kod-yolu ispatiyla YAPISAL ULASILAMAZ 15 hucre (denetim 4.1; yapi fable6_2'de ayni):
#   (ri!=12, ev=12): event 12 yalniz volx_proxy ile eklenir, volx_proxy ise rejim
#     zincirinde ONCE ri=12'yi secer -> 11 hucre {12,24,...,132}.
#   (5,1)=49: rejim 5 d2==SQUEEZE ister; SQUEEZE kosulsuz event 9 ekler -> BAZ imkansiz.
#   (7,9)=81: event 9 SQUEEZE ister; rejim 7 EXPANSION ister.
#   (12,1)=133: volx_proxy'de 4/5/8 yoksa event 12 eklenir -> olay listesi bos kalamaz.
#   (12,9)=141: rejim 12 vr==EXTREME -> d2==EXPANSION; event 9 SQUEEZE ister.
# Pratik cesitlilik ~75 gozlenen hucredir (denetim: 9.612 siniflandirma); ~54 hucre ne
# gozlendi ne imkansiz-ispatli (NOT VERIFIED — iddia edilmez). R8: nadir hucrelerde
# scen_cell telemetrisi (scen_cell_min_resolved=15) pratikte OLGUNLASAMAZ; hucre-isabet
# sayilari bu yuzden cogu hucre icin sonsuza dek 'YETERSIZ' kalir (belgeli kisit).
# Selftest'te [IMKANSIZ-HUCRE] tarama regresyonu vardir.
SCEN_IMKANSIZ_HUCRELER = frozenset(
    {(ri - 1) * 12 + 12 for ri in range(1, 12)} | {49, 81, 133, 141})

# ── TURKCE KARSILIKLAR (gosterim): HUCRE satirinin hemen altinda basilir ──
REGIME_TR = {
    "BELIRSIZ": "belirsiz", "TREND-UP-STRONG": "guclu yukselis trendi",
    "TREND-UP-PULLBACK": "yukselis trendinde geri cekilme",
    "TREND-DOWN-STRONG": "guclu dusus trendi",
    "TREND-DOWN-BOUNCE": "dusus trendinde tepki yukselisi",
    "RANGE-TIGHT": "dar bant (yatay)", "RANGE-WIDE": "genis bant (yatay)",
    "BREAKOUT-EXPANSION": "kirilim + genisleme",
    "REVERSAL-BOTTOM": "dip donusu", "REVERSAL-TOP": "tepe donusu",
    "ACCUMULATION": "toplama (dipte birikim)", "DISTRIBUTION": "dagitim (tepede bosaltma)",
    "VOL-PATLAMA(proxy)": "vol patlamasi (likidasyon vekili)",
}
EVENT_TR = {
    "BAZ": "ozel olay yok", "V_DIP": "dipte reddedilis", "V_TOP": "tepede reddedilis",
    "PUMP": "alim patlamasi", "DUMP": "satim patlamasi", "SFP": "likidite avi",
    "FBO": "tuzak kirilim", "EXH": "tukenme", "SQZ": "sikisma",
    "SH": "stop avi", "FFLIP": "funding donusu", "VOLX*": "vol patlamasi",
}
DIM_TR = {
    "SU": "guclu yukari trend", "WU": "zayif yukari trend", "SD": "guclu asagi trend",
    "WD": "zayif asagi trend", "RG": "yatay",
    "SQUEEZE": "sikisik volatilite", "NORMAL": "normal volatilite",
    "EXPANSION": "genisleyen volatilite",
    "DIP": "fiyat bant DIBINDE", "MID": "fiyat bant ortasinda", "TOP": "fiyat bant TEPESINDE",
    "NEU": "turev kalabaligi notr", "LONG-HEAVY": "LONG'cular kalabalik (funding)",
    "SHORT-HEAVY": "SHORT'cular kalabalik (funding)", "FLIP": "funding yon degistirdi",
}


def scenario_turkce(scen: "Scenario144") -> str:
    """HUCRE kodlarinin tek-satir Turkcesi (salt gosterim; karari etkilemez)."""
    reg = REGIME_TR.get(scen.regime, scen.regime)
    ev = EVENT_TR.get(scen.event, scen.event)
    parca = [DIM_TR.get(t.split("=", 1)[-1], t.split("=", 1)[-1])
             for t in (scen.dims or "").split()]
    return f"{reg} x {ev}" + (("  ·  " + " | ".join(parca)) if parca else "")

# ── SENARYO ANLAMI (insan dili): "ne oluyor / neden" — kehanet DEGIL, KALIP okumasi ──
EVENT_MEANING = {
    1: "belirgin ozel olay yok — yon mevcut rejimden turer",
    2: "DIPTE REDDEDILIS: fiyat destege indi ama uzun alt fitil/reclaim ile geri alindi -> saticilar tukeniyor, alicilar devraldi (yukari donus adayi)",
    3: "TEPEDE REDDEDILIS: fiyat dirence carpti ve uzun ust fitil birakti -> alicilar tukeniyor, saticilar devraldi (asagi donus adayi)",
    4: "PUMP: agresif ALIM patlamasi (hacim + momentum yukari) -> yukari devam adayi",
    5: "DUMP: agresif SATIM patlamasi (hacim + momentum asagi) -> asagi devam adayi",
    6: "LIKIDITE AVI (SFP): bir ekstremi supurup ICERI kapandi -> stoplar avlandi, ters yone donus adayi",
    7: "TUZAK KIRILIM (FBO): kirilim tutmadi, fiyat bandin icine geri dondu -> yon belirsiz, izleniyor",
    8: "TUKENME (EXH): yuksek hacim ama momentum YOK -> mevcut hareket zayifliyor, donus riski",
    9: "SIKISMA (SQZ): volatilite daraliyor -> patlama yakin ama yon belirsiz -> BEKLE",
    10: "STOP AVI (SH): bir seviye supuruldu ve AYNI yonde kapandi -> supurme yonunde devam",
    11: "FUNDING DONUSU (FFLIP): kalabalik taraf yon degistirdi -> sikisma riski, yon belirsiz",
    12: "ASIRI VOLATILITE PATLAMASI (VOLX*, PROXY): asiri true-range + buyuk momentum. DIKKAT: gercek likidasyon/forceOrder verisi YOK -> bu yalniz vol-rejimi vekilidir; fitil sonrasi ters donus adayi (dogrulanmamis)",
}
REGIME_MEANING = {
    0: "belirsiz", 1: "guclu yukari trend", 2: "yukari trendde geri cekilme",
    3: "guclu asagi trend", 4: "asagi trendde tepki yukselisi", 5: "dar/sikisik range",
    6: "genis range salinimi", 7: "kirilim / genisleme", 8: "dip bolgesi (donus adayi)",
    9: "tepe bolgesi (donus adayi)", 10: "birikim (accumulation)", 11: "dagitim (distribution)",
    12: "asiri volatilite patlamasi (proxy; gercek likidasyon verisi yok)",
}


def _herald_read(heralds: List[str]) -> str:
    """Haberci kaliplarini 'kim baskin' diline cevir (insan okumasi)."""
    out: List[str] = []
    for h in heralds:
        if h.startswith("delta+"):
            out.append("net ALICI baskisi")
        elif h.startswith("delta-"):
            out.append("net SATICI baskisi")
        elif h.startswith("hacim-z"):
            out.append("hacim patlamasi")
        elif h == "konum=DIP":
            out.append("bandin dibinde")
        elif h == "konum=TOP":
            out.append("bandin tepesinde")
        elif h == "alt-fitil/reclaim":
            out.append("alt fitil / reclaim (dip reddi)")
        elif h == "ust-fitil":
            out.append("ust fitil (tepe reddi)")
        elif h == "momentum-dusus":
            out.append("dususte ivme kaybi")
        elif h == "momentum-yukselis":
            out.append("yukselen momentum")
        elif h == "tick-radar-DIP":
            out.append("tick radari DIP donusu")
        elif h == "tick-radar-TEPE":
            out.append("tick radari TEPE donusu")
    seen = set()
    uniq = [x for x in out if not (x in seen or seen.add(x))]
    return ("isaretler: " + ", ".join(uniq)) if uniq else ""


def scenario_explanation(scen: "Scenario144") -> str:
    """SENARYONUN sade dil aciklamasi: ne oluyor / neden. Kehanet DEGIL, KALIP okumasi.
    Rejim anlami + olay mekanigi + konum/volatilite baglami + alici/satici baskisi."""
    parts: List[str] = []
    rg = REGIME_MEANING.get(scen.regime_idx, "")
    if rg:
        parts.append(f"[{rg}]")
    ev_txt = EVENT_MEANING.get(scen.event_idx, "")
    if ev_txt:
        parts.append(ev_txt)
    dd = dict(tok.split("=") for tok in scen.dims.split() if "=" in tok)
    pos = {"TOP": "fiyat bandin TEPESINDE", "DIP": "fiyat bandin DIBINDE",
           "MID": "fiyat bandin ORTASINDA"}.get(dd.get("D3", ""), "")
    vol = {"SQUEEZE": "volatilite SIKISIK", "EXPANSION": "volatilite GENISLIYOR"}.get(dd.get("D2", ""), "")
    ctx = ", ".join(x for x in (pos, vol) if x)
    if ctx:
        parts.append(ctx)
    hr = _herald_read(scen.heralds)
    if hr:
        parts.append(hr)
    return "  ·  ".join(parts)


@dataclass
class Scenario144:
    cell: int
    regime_idx: int
    regime: str
    event_idx: int
    event: str
    dims: str
    signal: str
    side_hint: str          # LONG | SHORT | NEUTRAL
    heralds: List[str]
    herald_n: int
    watch: bool
    events_all: List[str]
    family6: str = "BELIRSIZ"
    oi_var: bool = True   # R4: OI verisi var miydi (yokken ACCUMULATION/DISTRIBUTION olculemez)


def _plain_signal(regime_idx: int, event_idx: int, side_hint: str) -> str:
    ev = event_idx
    # Not: KESIN gelecek zaman ("olacak") YOK -> bunlar KALIP tespitidir, kehanet degil.
    if ev == 2:
        return "V-donus adayi (dipte reddedilis) -> tetiklenirse LONG"
    if ev == 3:
        return "V-donus adayi (tepede reddedilis) -> tetiklenirse SHORT"
    if ev == 4:
        return "PUMP gozlendi -> yukari devam adayi (LONG)"
    if ev == 5:
        return "DUMP gozlendi -> asagi devam adayi (SHORT)"
    if ev == 6:
        return ("dipte likidite avi + iceri kapanis -> yukari donus adayi" if side_hint == "LONG"
                else "tepede likidite avi + red -> asagi donus adayi")
    if ev == 7:
        return "tuzak kirilim (FBO) -> geri donebilir [izleniyor, yon belirsiz]"
    if ev == 8:
        return "tukenme (EXH) -> mevcut hareket zayifliyor, donus riski"
    if ev == 9:
        return "sikisma (SQZ) -> patlama yakin, yon belirsiz -> BEKLE"
    if ev == 11:
        return "funding isaret donusu (FFLIP) -> sikisma riski, yon belirsiz"
    if ev == 12:
        return "asiri volatilite patlamasi (VOLX proxy; gercek likidasyon verisi YOK) -> sonrasi donus adayi"
    if ev == 10:
        return "stop avi (SH) -> supurme yonunde devam [izleniyor]"
    # BAZ: rejimden turet (hepsi ADAY dilinde)
    if regime_idx == 8:
        return "dip bolgesi -> toparlanma adayi (yukari)"
    if regime_idx == 9:
        return "tepe bolgesi -> red adayi (asagi)"
    if regime_idx == 10:
        return "birikim -> yukari kirilim hazirligi"
    if regime_idx == 11:
        return "dagitim -> asagi kirilim hazirligi"
    if regime_idx in (1, 2):
        return "yukari trend -> geri cekilmede LONG"
    if regime_idx in (3, 4):
        return "asagi trend -> tepkide SHORT"
    if regime_idx == 5:
        return "dar range/sikisma -> patlama beklenir -> BEKLE"
    if regime_idx == 6:
        return "range salinimi -> alttan LONG / ustten SHORT"
    return "net senaryo yok -> BEKLE"


def classify_scenario(snap: Snapshot, st: Optional[Structure], cfg: Config) -> Scenario144:
    """Snapshot'tan 144-senaryo hucresini + sade sinyali uretir. YALNIZ kapanmis mumlar
    (no-lookahead). yon2 motorunun kullandigi ayni ilkellerle tutarli."""
    cs = snap.candles
    if st is None or not st.valid or len(cs) < 30:
        return Scenario144(0, 0, "BELIRSIZ", 1, "BAZ", "veri yok",
                           "net senaryo yok -> BEKLE", "NEUTRAL", [], 0, True, ["BAZ"],
                           family6="BELIRSIZ", oi_var=False)
    atrs = atr_series(cs, cfg.atr_period)
    feats = bar_features(cs, len(cs) - 1, atrs, cfg)
    price, atr, rl, rh = st.price, st.atr, st.range_low, st.range_high
    rpos = ((price - rl) / (rh - rl) * 2.0 - 1.0) if rh > rl else 0.0
    volz = feats[7] if feats else 0.0
    mom1 = feats[0] if feats else 0.0
    vr = vol_regime(cs, cfg)
    tb = htf_bias(snap.htf, cfg)
    mb = market_bias(cs, cfg)
    er = efficiency_ratio(cs, len(cs) - 1, 10)
    of = snap.orderflow
    rev_sign, rev_str, _rev_r = reversal_radar(of, st, cfg)
    dip_rej = _dip_rejection(cs, cfg)
    top_rej = _top_rejection(cs, cfg)
    tested_sup = (cs[-1].low - rl) <= cfg.veto_touch_atr * atr
    tested_res = (rh - cs[-1].high) <= cfg.veto_touch_atr * atr
    ois = [c.oi for c in cs if c.oi is not None]
    # oi_rising: MUTLAK %0.3 DEGIL -> OI momentum'un KENDI dagilimina gore z (fallback sabit).
    oi_rising = False
    _oi_var = len(ois) >= 7 and ois[-4] > 0   # R4: OI erisilebilirligi (rejim 10/11 on-sarti)
    if len(ois) >= 7 and ois[-4] > 0:
        _oi_hist = _change_series(ois, lag=3)
        _oi_chg = (ois[-1] - ois[-4]) / ois[-4]
        _oi_z = robust_z(_oi_hist[:-1], _oi_chg, cfg.norm_min_n)
        oi_rising = (_oi_z >= cfg.z_extreme) if _oi_z is not None else (_oi_chg > cfg.oi_chg_fallback)
    fh = snap.funding_hist or []
    # d4_flip: isaret degisimi + iki tarafta da anlamli buyukluk (sifira yakin salinim FLIP degil)
    d4_flip = (len(fh) >= 2 and (fh[-1] > 0) != (fh[-2] > 0)
               and abs(fh[-1]) > cfg.funding_flip_floor and abs(fh[-2]) > cfg.funding_flip_floor)

    # ── D1..D4 alt-boyutlar ──
    if tb > 0:
        d1 = "SU" if (er > cfg.er_trend_min and mb > cfg.mb_strong) else "WU"
    elif tb < 0:
        d1 = "SD" if (er > cfg.er_trend_min and mb < -cfg.mb_strong) else "WD"
    else:
        d1 = "WU" if mb > cfg.mb_range else ("WD" if mb < -cfg.mb_range else "RG")
    d2 = ("SQUEEZE" if vr in ("COMPRESSED", "LOW")
          else "EXPANSION" if vr in ("EXPANDING", "EXTREME") else "NORMAL")
    d3 = "DIP" if rpos < -0.33 else ("TOP" if rpos > 0.33 else "MID")
    # d4: funding "kalabalik taraf" MUTLAK esik DEGIL -> funding'in KENDI dagilimina gore z.
    if d4_flip:
        d4 = "FLIP"
    elif snap.funding is None:
        d4 = "NEU"
    else:
        _fz = robust_z(fh[:-1][-cfg.funding_norm_win:], snap.funding, cfg.norm_min_n)  # [:-1]: cari settle'i disla
        _heavy_long = (_fz >= cfg.z_heavy) if _fz is not None else (snap.funding > cfg.funding_long_heavy)
        _heavy_short = (_fz <= -cfg.z_heavy) if _fz is not None else (snap.funding < cfg.funding_short_heavy)
        d4 = "LONG-HEAVY" if _heavy_long else ("SHORT-HEAVY" if _heavy_short else "NEU")
    dims = f"D1={d1} D2={d2} D3={d3} D4={d4}"

    # VOLX proxy: gercek likidasyon verisi (forceOrders) YOK -> asiri vol-rejimi + buyuk momentum vekili
    volx_proxy = vr == "EXTREME" and abs(mom1) > cfg.volx_mom_min
    # onceki pencere ekstremleri (mevcut mum HARIC) -> gercek kirilim/sweep icin
    prior = cs[-(cfg.range_window + 1):-1] if len(cs) > cfg.range_window + 1 else cs[:-1]
    prl = min(x.low for x in prior) if prior else rl
    prh = max(x.high for x in prior) if prior else rh
    # referans pencere: SON accept_n mum HARIC -> kirilimi/sweep'i bu tabana gore olc (FBO/SH icin)
    _back = cfg.accept_n
    ref = (cs[-(cfg.range_window + _back + 1):-(_back + 1)]
           if len(cs) > cfg.range_window + _back + 1 else (cs[:-(_back + 1)] or prior))
    rrl = min(x.low for x in ref) if ref else prl
    rrh = max(x.high for x in ref) if ref else prh
    c_last = cs[-1]
    # KABUL edilmis kirilim mi (accept_n mumdan accept_k kapanis disarida) yoksa taze fitil mi
    # KABUL: referans, accept-penceresi HARIC taban (rrl/rrh). Eski prl/prh (yalniz son
    # mum haric) ile accept_k=2 kapanis esigine fiilen ulasilamiyordu -> her dip 'taze'
    # sayilip SHORT ipuclari surekli notrleniyordu (saha: dusus fazinda tek SHORT yok).
    floor_acc = _accepted_break(cs, rrl, "dn", cfg.accept_n, cfg.accept_k)
    ceil_acc = _accepted_break(cs, rrh, "up", cfg.accept_n, cfg.accept_k)
    # kirilim = KAPANIS onceki pencere ekstremini gecti (yakinlik degil, gercek kirilim)
    broke_up = c_last.close > prh
    broke_dn = c_last.close < prl
    recent_breakout = d2 == "EXPANSION" and (broke_up or broke_dn)

    # ── REJIM secimi (oncelikli) ──
    if volx_proxy:
        ri = 12
    elif d3 == "DIP" and (rev_sign > 0 or (tested_sup and dip_rej)):
        ri = 8
    elif d3 == "TOP" and (rev_sign < 0 or (tested_res and top_rej)):
        ri = 9
    elif recent_breakout:
        ri = 7
    elif d2 == "SQUEEZE" and d1 == "RG":
        ri = 5
    elif d1 == "SU":
        ri = 1
    elif d1 == "WU":
        ri = 2
    elif d1 == "SD":
        ri = 3
    elif d1 == "WD":
        ri = 4
    else:  # d1 kumesi {SU,WU,SD,WD,RG} icinde kalan tek deger RG (bkz. d1 atamasi)
        ri = 10 if (oi_rising and d3 == "DIP") else (11 if (oi_rising and d3 == "TOP") else 6)

    # ── OLAY tespiti (coklu; manset oncelikle) ──
    # sweep/kirilim olaylari ONCEKI-pencere ekstremine gore (mevcut mum haric) -> triviyal degil
    wick_below = c_last.low <= prl
    wick_above = c_last.high >= prh
    sfp_up = wick_below and c_last.close > prl + cfg.sfp_reclaim_atr * atr   # supurup ICERI kapanis (reclaim)
    sfp_dn = wick_above and c_last.close < prh - cfg.sfp_reclaim_atr * atr
    # SH stop-avi: onceki bar referansin ICINDEYKEN, bu bar disari supurup AYNI yonde kapandi (taze gecis)
    sh_dn = len(cs) >= 2 and cs[-2].close >= rrl and c_last.low <= rrl and c_last.close < rrl
    sh_up = len(cs) >= 2 and cs[-2].close <= rrh and c_last.high >= rrh and c_last.close > rrh
    # FBO tuzak kirilim: son birkac bar referansi KAPANISLA kirdi ama su an ICERI geri dondu
    recent_seg = cs[-(cfg.accept_n + 1):-1] if len(cs) > cfg.accept_n + 1 else cs[:-1]
    fbo = ((any(x.close > rrh for x in recent_seg) and c_last.close < rrh) or
           (any(x.close < rrl for x in recent_seg) and c_last.close > rrl))
    events: List[int] = []
    if tested_sup and dip_rej:
        events.append(2)
    if tested_res and top_rej:
        events.append(3)
    if sfp_up or sfp_dn:
        events.append(6)
    if volz >= cfg.volz_pump and mom1 > cfg.mom_pump:
        events.append(4)
    if volz >= cfg.volz_pump and mom1 < -cfg.mom_pump:
        events.append(5)
    if fbo:
        events.append(7)
    if volz >= cfg.volz_exh and abs(mom1) < cfg.mom_exh_max:
        events.append(8)
    if d2 == "SQUEEZE":
        events.append(9)
    if sh_dn or sh_up:
        events.append(10)
    if d4_flip:
        events.append(11)
    if volx_proxy and not any(e in events for e in (4, 5, 8)):
        events.append(12)              # VOLX*: YALNIZ yonlu vol-olayi (PUMP/DUMP/EXH) YOKKEN ekle
    if not events:
        events = [1]
    ev_idx = next((e for e in EVENT_PRIORITY if e in events), 1)
    # DEJENERASYON DUZELTMESI: eski 'volx_proxy -> ev_idx=12' zorlamasi KALDIRILDI. O zorlama
    # regime-12 (VOL-PATLAMA) ile event-12'yi AYNI boole'den turetip kose hucreyi (144) HEP
    # degismez yapiyordu (regime ile olay bagimsiz DEGILDI). Artik VOL-PATLAMA rejimi gercek/
    # ayrik olayla (PUMP/DUMP/EXH/SFP...) eslesir; VOLX* olayi yalniz yonlu-olay yoksa manset olur.

    # ── yon ipucu (olay semantigi rejimden ONCE gelir; celiskiler giderildi) ──
    # ONCU degisikligi (kullanici direktifi): GECIKMELI pump/dump (olay 4/5) artik YON
    # URETMEZ -> side_hint NEUTRAL. Pump/dump patlama mumu kapaninca dogrular (gec kalinmis
    # giris); olay etiketi TELEMETRI olarak kalir ama F9/senaryo-risk-kapisi yolundan yon
    # KAYNAGI olamaz. Donus/giris artik ONCU (leading) sinyallerden gelir (bkz. _oncu_yon).
    prevailing_up = mb > 0
    if ev_idx == 2:
        side_hint = "LONG"
    elif ev_idx == 3:
        side_hint = "SHORT"
    elif ev_idx in (4, 5):            # PUMP/DUMP: gecikmeli -> yon URETMEZ (kullanici: 'kaziyip at')
        side_hint = "NEUTRAL"
    elif ev_idx == 6:
        side_hint = "LONG" if sfp_up else "SHORT"
    elif ev_idx in (7, 9, 11):        # FBO/SQZ/FFLIP: yon belirsiz -> NEUTRAL
        side_hint = "NEUTRAL"
    elif ev_idx == 8:                 # EXH tukenme: mevcut trendin TERSI (donus riski)
        side_hint = "SHORT" if prevailing_up else "LONG"
    elif ev_idx == 12:                # VOLX*: vol-patlamasinin TERSI (dump->LONG, pump->SHORT)
        side_hint = "LONG" if mom1 < 0 else "SHORT"
    elif ev_idx == 10:                # SH stop-avi: supurme yonunde devam
        side_hint = "SHORT" if sh_dn else "LONG"
    elif ri in (1, 2, 8, 10):
        side_hint = "LONG"
    elif ri in (3, 4, 9, 11):
        side_hint = "SHORT"
    else:
        side_hint = "NEUTRAL"

    # ── dip-short / tepe-long korumasi (yon2 felsefesi): kirilmamis/taze uçta ters yon onerme.
    # Taze dipte (d3=DIP, kabul edilmemis) SHORT -> NEUTRAL; taze tepede LONG -> NEUTRAL.
    # ATR-KIRLENME FIX (denetim): esik sok-mumu-DAHIL ATR'ye olculuyordu -> dev mumun
    # kendi TR'si paydayi sisirip etkin esigi ~2.17x ONCEKI ATR yapiyordu. Niyet 2.0x:
    # olcum tabani SON MUM HARIC ATR. Tum kardes kopyalar ayni turda duzeltildi (H4).
    _atr_onc_sc = atrs[-2] if len(atrs) >= 2 and atrs[-2] > 0 else atr
    _ext_sc = true_range(cs[-1], cs[-2] if len(cs) >= 2 else None) > cfg.ext_bar_atr * _atr_onc_sc
    if side_hint == "SHORT" and d3 == "DIP" and (not floor_acc or dip_rej or _ext_sc):
        side_hint = "NEUTRAL"
    elif side_hint == "LONG" and d3 == "TOP" and (not ceil_acc or top_rej or _ext_sc):
        side_hint = "NEUTRAL"

    # ── GOZLEM sayimi (dokuman §4 kalibi) — 6 AYRI, cakismayan kalip; momentum!=konum.
    # ONEMLI: bu sayi ISABETLE DOGRULANMADI; hizalanan kalip adedidir, kazanma olasiligi DEGIL.
    heralds: List[str] = []
    if side_hint == "LONG":
        if mom1 < -cfg.mom_herald:
            heralds.append("momentum-dusus")
        if d3 == "DIP":
            heralds.append("konum=DIP")
        if dip_rej:
            heralds.append("alt-fitil/reclaim")
        if volz >= cfg.volz_herald:
            heralds.append(f"hacim-z{volz:.1f}")
        if rev_sign > 0:
            heralds.append("tick-radar-DIP")
        if of and of.delta_z > 0:
            heralds.append("delta+")
    elif side_hint == "SHORT":
        if mom1 > cfg.mom_herald:
            heralds.append("momentum-yukselis")
        if d3 == "TOP":
            heralds.append("konum=TOP")
        if top_rej:
            heralds.append("ust-fitil")
        if volz >= cfg.volz_herald:
            heralds.append(f"hacim-z{volz:.1f}")
        if rev_sign < 0:
            heralds.append("tick-radar-TEPE")
        if of and of.delta_z < 0:
            heralds.append("delta-")

    signal = _plain_signal(ri, ev_idx, side_hint)
    cell = (ri - 1) * 12 + ev_idx if ri >= 1 else 0
    watch = ev_idx in WATCH_EVENTS or ri == 0
    events_all = [EVENT_NAMES[e] for e in events]
    return Scenario144(cell, ri, REGIME_NAMES[ri], ev_idx, EVENT_NAMES[ev_idx],
                       dims, signal, side_hint, heralds, len(heralds), watch, events_all,
                       family6=REGIME_FAMILY6.get(ri, "BELIRSIZ"), oi_var=_oi_var)


def scenario_headline(scen: Scenario144, d: "Decision") -> str:
    """Senaryo ipucunu endpoint3 karariyla goster. NOT: iki katman AYNI
    primitifleri paylasir (build_structure/bar_features/reversal_radar/...); ayni yon =
    BAGIMSIZ teyit DEGIL, ortak-girdi hizasi. Bu yuzden 'ONAYLADI' dili KULLANILMAZ."""
    sig = scen.signal
    karar_str = f"{d.karar} ~%{d.prob}" if d.karar in ("LONG", "SHORT") else d.karar
    # yon-belirsiz/izlenen olay: uzlastirma etiketi yok, endpoint3 karari ayrica gosterilir
    if scen.watch or scen.side_hint == "NEUTRAL":
        return f"{sig}   [endpoint3: {karar_str}]"
    if d.karar in ("LONG", "SHORT"):
        if scen.side_hint == d.karar:
            return f"{sig}   [endpoint3 ayni yonde: {karar_str} — bagimsiz teyit DEGIL, ortak girdi]"
        if scen.side_hint in ("LONG", "SHORT"):
            return f"{sig}   [CELISKI: endpoint3 {d.karar} -> endpoint3 onceklidir]"
        return f"{sig}   [endpoint3: {karar_str}]"
    # endpoint3 BEKLE
    if scen.side_hint in ("LONG", "SHORT"):
        return f"{sig}   [aday; endpoint3 teyit etmedi -> BEKLE]"
    return f"{sig}   [endpoint3: {karar_str}]"


# ════════════════════════════════════════════════════════════════════════════
# MIKRO-SENARYO KATALOGU (29 kalip) — VADELI + SPOT KOMBINE, MAX CESITLENDIRME
# Amac: "veriler geldiginde 15m'de fiyat SU hareketi yapabilir" demek (ADAY dili,
# kehanet degil). 1..144 sparse makro-ID katalogu durur; bu katman EK adlandirilmis-kalip
# taramasidir. KARARA DOKUNMAZ: yon/giris/hedef/stop DAIMA yon2'den. Yalniz
# gosterir + loglar; legacy bilesik cozum telemetrisi OOS katkisi sayilmaz.
# Esikler z/quantile tabanli (yon5 ilkesi: sihirli sayi yok, veri-goreli olcum).
# Kaynaklar: fiyat-aksiyonu (mum yapilari), turev-akis (OI/funding/taker),
# SPOT-VADELI iliskisi (basis primi/iskontosu, spot-mu-onculuk, teyitsiz-kopus).
# NO-LOOKAHEAD: yalniz kapanmis mumlar; z-gecmisi cari degeri DISLAR.
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class MicroScen:
    mid: int           # kalici kalip no (log anahtari)
    ad: str
    side: str          # LONG | SHORT | NEUTRAL
    guc: float         # 0..1
    beklenen: str      # 15m'de beklenen hareket (ADAY dili)
    kanit: str         # tetikleyen olcum ozeti
    tier: str = "C"    # A=mekanizma-kanitli B=teyit-ister C=yalniz-baglam
    seviye: float = 0.0  # kalibin ana fiyat seviyesi (havuz/vwap; NET OKUMA icin)


MICRO_ADLAR = {
    1: "YUTAN-BOGA", 2: "YUTAN-AYI", 3: "IC-MUM-SIKISMA", 4: "DIS-MUM-TARAMA",
    5: "UC-ITIS-TUKENME", 6: "ESIT-TEPELER(likidite)", 7: "ESIT-DIPLER(likidite)",
    8: "KIRILIM-RETEST", 9: "FVG-BOSLUK-MIKNATIS", 10: "FITIL-KUMESI-SAVUNMA",
    11: "W-DIP", 12: "M-TEPE", 13: "VWAP-GERILME", 14: "MOMENTUM-IRAKSAMA",
    15: "OI-FLUSH(temizlik)", 16: "OI-BIRIKIM(sessiz)", 17: "KALABALIK-TERS(tuzak)",
    18: "SQUEEZE-YAKITI", 19: "BASIS-PRIM-KOPUK", 20: "BASIS-ISKONTO-KORKU",
    21: "SPOT-ONCU(organik)", 22: "VADELI-KOPUS(teyitsiz)",
    23: "ABSORPSIYON-DUVARI", 24: "HACIM-KURUMASI",
    25: "KOMBO-DIP-TEMIZLIK", 26: "KOMBO-TEPE-KOPUGU", 27: "GUN-UCU-MIKNATISI",
    28: "KOMBO-TUZAK-TEPE", 29: "KOMBO-TUZAK-DIP",
}
# GUVENILIRLIK KATMANI (arastirma-onayli): A = objektif mekanizma (funding/OI/basis
# arbitraj-geri-donuslu, belgelenmis); B = mekanizma-makul, teyit ister; C = grafik-lore,
# YALNIZ baglam — arXiv 2605.04004: OHLCV-tek-basina mum kaliplarinin maliyet-sonrasi
# bagimsiz kenari YOK -> C-katman tek basina sinyal gibi OKUNMAMALI.
MICRO_TIER = {
    15: "A", 17: "A", 18: "A", 19: "A", 20: "A", 25: "A", 26: "A", 28: "A", 29: "A",
    6: "B", 7: "B", 8: "B", 13: "B", 16: "B", 21: "B", 22: "B", 23: "B",
    1: "C", 2: "C", 3: "C", 4: "C", 5: "C", 9: "C", 10: "C", 11: "C", 12: "C",
    14: "C", 24: "C", 27: "C",
}
_TIER_SIRA = {"A": 0, "B": 1, "C": 2}

# ── REJIM-ONSEL CARPANLARI: hangi kalip hangi rejim ailesinde daha guvenilir? ──
# Arastirma-temelli KABA onseller (log doldukca micro_rate olcumu one gecer; carpan
# yalniz siralama/guc icindir, karara dokunmaz). Trendde DEVAM kaliplari one alinir,
# trend-KARSITI donus kaliplari kisilir; yatayda bant-kenari/likidite; asiri-vol'de
# fitil/absorpsiyon/flush. Tabloda olmayan kalip = 1.0 (notr).
MICRO_REJIM_CARPAN = {
    "YUKARI-TREND": {8: 1.25, 21: 1.2, 9: 1.1, 26: 1.1, 12: 0.8, 5: 0.85, 11: 0.9, 13: 0.85},
    "ASAGI-TREND":  {8: 1.25, 21: 1.2, 9: 1.1, 25: 1.1, 15: 1.15, 20: 1.15, 11: 0.8, 5: 0.85, 12: 0.9, 13: 0.85},
    "YATAY":        {6: 1.25, 7: 1.25, 13: 1.2, 3: 1.1, 27: 1.1, 8: 0.85, 21: 0.8},
    "ASIRI-VOL":    {4: 1.2, 10: 1.2, 23: 1.2, 15: 1.25, 24: 1.1, 3: 0.8, 13: 0.9, 9: 0.85},
}


def _micro_vwap(cs: List[Candle], win: int) -> Optional[float]:
    seg = cs[-win:] if len(cs) > win else cs
    tv = sum(c.volume for c in seg)
    if tv <= 0:
        return None
    return sum(c.close * c.volume for c in seg) / tv


def _micro_basis_z(perp: List[Candle], spot: Optional[List[Candle]], cfg: Config
                   ) -> Tuple[Optional[float], Optional[float]]:
    """(basis, basis_z). basis = perp/spot - 1 (timestamp-hizali). z: SALT-GECMIS dagilim."""
    if not spot or len(spot) < cfg.norm_min_n + 2:
        return None, None
    sp = {c.close_ms: c.close for c in spot if c.close_ms is not None and c.close > 0}
    series: List[float] = []
    for c in perp:
        if c.close_ms in sp:
            series.append(c.close / sp[c.close_ms] - 1.0)
    if len(series) < cfg.norm_min_n + 1:
        return None, None
    series = series[-cfg.basis_win:]
    b = series[-1]
    z = robust_z(series[:-1], b, cfg.norm_min_n)
    return b, z


def classify_micro(snap: Snapshot, st: Optional[Structure], cfg: Config) -> List[MicroScen]:
    """29-kalip taramasi; tek-kalip hatasi paneli dusurmez ama gorunur kaydedilir."""
    out: List[MicroScen] = []
    def _micro_error(tag: str, exc: Exception) -> None:
        msg = f"mikro[{tag}] hesaplanamadi: {type(exc).__name__}: {str(exc)[:80]}"
        snap.source_errors.append(msg)
        sys.stderr.write("[MIKRO-UYARI] " + msg + "\n")
    cs = snap.candles
    if st is None or not st.valid or len(cs) < 40:
        return out
    a = st.atr
    price = st.price
    if a <= 0:
        return out
    atrs = atr_series(cs, cfg.atr_period)
    feats = bar_features(cs, len(cs) - 1, atrs, cfg)
    mom1 = feats[0] if feats else 0.0
    mom6 = feats[2] if feats else 0.0
    volz = feats[7] if feats else 0.0
    rl, rh = st.range_low, st.range_high
    rpos = ((price - rl) / (rh - rl) * 2.0 - 1.0) if rh > rl else 0.0
    c1, c2 = cs[-1], cs[-2]
    body1 = abs(c1.close - c1.open)
    body2 = abs(c2.close - c2.open)
    er = efficiency_ratio(cs, len(cs) - 1, 10)
    # KABUL edilmis kirilim: referans, SON accept_n mum HARIC oncesi pencerenin
    # ekstremleri (rl/rh DEGIL — bant son mumlari da kapsar, kapanis bant disina
    # cikamayacagi icin rl/rh'a karsi kabul HEP False kalirdi = olu kontrol).
    _back = cfg.accept_n
    _ref = (cs[-(cfg.range_window + _back + 1):-(_back + 1)]
            if len(cs) > cfg.range_window + _back + 1 else cs[:-(_back + 1)])
    ref_lo = min(x.low for x in _ref) if _ref else rl
    ref_hi = max(x.high for x in _ref) if _ref else rh
    floor_acc = _accepted_break(cs, ref_lo, "dn", cfg.accept_n, cfg.accept_k)
    ceil_acc = _accepted_break(cs, ref_hi, "up", cfg.accept_n, cfg.accept_k)

    def _ekle(mid, side, guc, beklenen, kanit, seviye=0.0):
        out.append(MicroScen(mid, MICRO_ADLAR[mid], side, _clip(guc, 0.0, 1.0),
                             beklenen, kanit[:80], MICRO_TIER.get(mid, "C"), seviye))

    # ── 1/2 YUTAN mum (engulfing) band ucunda ─────────────────────────────
    try:
        if body1 > body2 > 0 and body1 > 0.3 * a:
            engulf_up = c1.close > c1.open and c2.close < c2.open and \
                c1.close >= max(c2.open, c2.close) and c1.open <= min(c2.open, c2.close)
            engulf_dn = c1.close < c1.open and c2.close > c2.open and \
                c1.open >= max(c2.open, c2.close) and c1.close <= min(c2.open, c2.close)
            if engulf_up and rpos < -0.2:
                _ekle(1, "LONG", 0.5 + 0.5 * min(1.0, body1 / a),
                      f"onceki mumu yutan boga mumu band dibinde: 1-4 mumda {_fmt(min(rh, price + a))} yonune itis ADAYI; {_fmt(c1.low)} alti kapanis kalibi bozar",
                      f"yutan-boga govde={body1/a:.1f}ATR rpos={rpos:+.2f}")
            elif engulf_dn and rpos > 0.2:
                _ekle(2, "SHORT", 0.5 + 0.5 * min(1.0, body1 / a),
                      f"onceki mumu yutan ayi mumu band tepesinde: 1-4 mumda {_fmt(max(rl, price - a))} yonune sarkma ADAYI; {_fmt(c1.high)} ustu kapanis kalibi bozar",
                      f"yutan-ayi govde={body1/a:.1f}ATR rpos={rpos:+.2f}")
    except Exception as exc:
        _micro_error("1-2", exc)
    # ── 3 IC-MUM sikisma / NR daralma ────────────────────────────────────
    try:
        ic = 0
        k = len(cs) - 1
        while k > 0 and cs[k].high <= cs[k - 1].high and cs[k].low >= cs[k - 1].low:
            ic += 1
            k -= 1
        trs = [true_range(cs[i], cs[i - 1]) for i in range(len(cs) - cfg.nr_lookback, len(cs))]
        nr = trs[-1] <= min(trs) + 1e-12 if len(trs) >= cfg.nr_lookback else False
        if ic >= cfg.inside_min or nr:
            _ekle(3, "NEUTRAL", 0.4 + 0.15 * ic,
                  "ic-mum/daralma sikismasi: 1-3 mumda YONLU PATLAMA beklenir (yon henuz belirsiz); kirilan yonde devam ADAYI, ilk kirilim tuzak da olabilir (FBO riski)",
                  f"ic-mum={ic} NR{cfg.nr_lookback}={'evet' if nr else 'hayir'}")
    except Exception as exc:
        _micro_error("3", exc)
    # ── 4 DIS-MUM (iki tarafi tarayan) ───────────────────────────────────
    try:
        if c1.high > c2.high and c1.low < c2.low and (c1.high - c1.low) > 1.2 * a:
            side4 = "LONG" if c1.close > c1.open else ("SHORT" if c1.close < c1.open else "NEUTRAL")
            _ekle(4, side4, 0.5,
                  "dis-mum iki tarafin stoplarini taradi: kapanis yonunde 1-3 mum devam ADAYI; genelde taramadan sonra tek yon secilir",
                  f"dis-mum tr={(c1.high-c1.low)/a:.1f}ATR kapanis={'yukari' if side4=='LONG' else 'asagi'}")
    except Exception as exc:
        _micro_error("4", exc)
    # ── 5 UC-ITIS tukenme (kuculen adimlarla 3. itis) ─────────────────────
    try:
        w = cs[-(cfg.struct_window):]
        sh, sl = swing_points(w, cfg.pivot_w)
        if len(sh) >= 3 and price > mean([x.close for x in w]):
            h1, h2, h3 = sh[-3], sh[-2], sh[-1]
            if h3 > h2 > h1 and (h2 - h1) > (h3 - h2) and mom6 < cfg.mom_exh_max and rpos > 0.2:
                _ekle(5, "SHORT", 0.6,
                      f"3. itis kuculuyor (tepe {_fmt(h3)}): momentum tukenmesi -> 2-6 mumda {_fmt(max(rl, price - a))} yonune geri cekilme ADAYI",
                      f"itisler {_fmt(h2-h1)}->{_fmt(h3-h2)} mom6={mom6:+.2f}")
        if len(sl) >= 3 and price < mean([x.close for x in w]):
            l1, l2, l3 = sl[-3], sl[-2], sl[-1]
            if l3 < l2 < l1 and (l1 - l2) > (l2 - l3) and mom6 > -cfg.mom_exh_max and rpos < -0.2:
                _ekle(5, "LONG", 0.6,
                      f"3. dusus adimi kuculuyor (dip {_fmt(l3)}): satici tukenmesi -> 2-6 mumda {_fmt(min(rh, price + a))} yonune tepki ADAYI",
                      f"adimlar {_fmt(l1-l2)}->{_fmt(l2-l3)} mom6={mom6:+.2f}")
    except Exception as exc:
        _micro_error("5", exc)
    # ── 6/7 ESIT tepe/dip = likidite havuzu ──────────────────────────────
    try:
        w = cs[-(cfg.struct_window):]
        sh, sl = swing_points(w, cfg.pivot_w)
        tol = cfg.eq_tol_atr * a
        eq_h = [h for h in sh if h > price and abs(h - (min([x for x in sh if x > price] or [0]))) <= tol]
        if len(eq_h) >= cfg.eq_min_touch:
            lvl = mean(eq_h)
            _ekle(6, "NEUTRAL", 0.4 + 0.1 * len(eq_h),
                  f"{_fmt(lvl)} uzerinde ESIT TEPELER = stop havuzu: fiyat once havuzu SUPUREBILIR ({_fmt(lvl)}+); supurup ICERI donerse SHORT tepki ADAYI, kapanisla ustunde kalirsa yukari devam",
                  f"esit-tepe x{len(eq_h)} @{_fmt(lvl)}", seviye=lvl)
        eq_l = [l for l in sl if l < price and abs(l - (max([x for x in sl if x < price] or [1e18]))) <= tol]
        if len(eq_l) >= cfg.eq_min_touch:
            lvl = mean(eq_l)
            _ekle(7, "NEUTRAL", 0.4 + 0.1 * len(eq_l),
                  f"{_fmt(lvl)} altinda ESIT DIPLER = stop havuzu: fiyat once havuzu SUPUREBILIR ({_fmt(lvl)}-); supurup ICERI donerse LONG tepki ADAYI, kapanisla altinda kalirsa asagi devam",
                  f"esit-dip x{len(eq_l)} @{_fmt(lvl)}", seviye=lvl)
    except Exception as exc:
        _micro_error("6-7", exc)
    # ── 8 KIRILIM-RETEST (kabul edilmis kirilim + seviye ustunde tutunma) ─
    try:
        if ceil_acc and abs(price - ref_hi) <= 0.5 * a and c1.low <= ref_hi + 0.2 * a and c1.close > ref_hi:
            _ekle(8, "LONG", 0.7,
                  f"kirilan direnc {_fmt(ref_hi)} retest edilip TUTTU: 1-4 mumda kirilim yonunde ({_fmt(price + a)}+) devam ADAYI; {_fmt(ref_hi - 0.3*a)} alti kapanis kalibi bozar",
                  f"retest@{_fmt(ref_hi)} kabul=evet")
        if floor_acc and abs(price - ref_lo) <= 0.5 * a and c1.high >= ref_lo - 0.2 * a and c1.close < ref_lo:
            _ekle(8, "SHORT", 0.7,
                  f"kirilan destek {_fmt(ref_lo)} retest edilip REDDETTI: 1-4 mumda kirilim yonunde ({_fmt(price - a)}-) devam ADAYI; {_fmt(ref_lo + 0.3*a)} ustu kapanis kalibi bozar",
                  f"retest@{_fmt(ref_lo)} kabul=evet")
    except Exception as exc:
        _micro_error("8", exc)
    # ── 9 FVG (3-mum dengesizlik boslugu) miknatisi ───────────────────────
    try:
        gap_up = gap_dn = None   # (alt, ust)
        for i in range(len(cs) - 3, max(len(cs) - 22, 1), -1):
            aa, bb, cc = cs[i], cs[i + 1], cs[i + 2]
            if cc.low - aa.high >= cfg.fvg_min_atr * a:      # boga boslugu (fiyatin altinda kalirsa destek)
                lo, hi = aa.high, cc.low
                if not any(x.low <= lo for x in cs[i + 3:]) and hi < price and gap_up is None:
                    gap_up = (lo, hi)
            if aa.low - cc.high >= cfg.fvg_min_atr * a:      # ayi boslugu (fiyatin ustunde kalirsa direnc)
                lo, hi = cc.high, aa.low
                if not any(x.high >= hi for x in cs[i + 3:]) and lo > price and gap_dn is None:
                    gap_dn = (lo, hi)
            if gap_up and gap_dn:
                break
        if gap_up and (price - gap_up[1]) <= 1.5 * a:
            _ekle(9, "LONG", 0.5,
                  f"altta DOLDURULMAMIS bosluk {_fmt(gap_up[0])}-{_fmt(gap_up[1])}: fiyat bosluga cekilip (dolum) oradan TEPKI ADAYI; bosluk kapanisla delinirse asagi hizlanma riski",
                  f"boga-FVG {_fmt(gap_up[0])}-{_fmt(gap_up[1])}")
        if gap_dn and (gap_dn[0] - price) <= 1.5 * a:
            _ekle(9, "SHORT", 0.5,
                  f"ustte DOLDURULMAMIS bosluk {_fmt(gap_dn[0])}-{_fmt(gap_dn[1])}: fiyat bosluga cekilip (dolum) oradan RED ADAYI; bosluk kapanisla asilirsa yukari hizlanma riski",
                  f"ayi-FVG {_fmt(gap_dn[0])}-{_fmt(gap_dn[1])}")
    except Exception as exc:
        _micro_error("9", exc)
    # ── 10 FITIL KUMESI (ayni yonde tekrarlanan savunma fitilleri) ────────
    try:
        n_lw = sum(1 for c in cs[-5:]
                   if (c.high - c.low) > 0 and (min(c.open, c.close) - c.low) > cfg.wick_rej_frac * (c.high - c.low))
        n_uw = sum(1 for c in cs[-5:]
                   if (c.high - c.low) > 0 and (c.high - max(c.open, c.close)) > cfg.wick_rej_frac * (c.high - c.low))
        if n_lw >= cfg.wick_cluster_n and rpos < 0:
            _ekle(10, "LONG", 0.4 + 0.1 * n_lw,
                  f"son 5 mumda {n_lw} kez alt fitil: {_fmt(min(c.low for c in cs[-5:]))} bolgesi SAVUNULUYOR -> tutundukca yukari donus ADAYI",
                  f"alt-fitil x{n_lw}")
        elif n_uw >= cfg.wick_cluster_n and rpos > 0:
            _ekle(10, "SHORT", 0.4 + 0.1 * n_uw,
                  f"son 5 mumda {n_uw} kez ust fitil: {_fmt(max(c.high for c in cs[-5:]))} bolgesi SATIS DUVARI -> reddedildikce asagi donus ADAYI",
                  f"ust-fitil x{n_uw}")
    except Exception as exc:
        _micro_error("10", exc)
    # ── 11/12 W-DIP / M-TEPE ─────────────────────────────────────────────
    try:
        w = cs[-(cfg.struct_window):]
        sh, sl = swing_points(w, cfg.pivot_w)
        tol = cfg.eq_tol_atr * a * 2.0
        if len(sl) >= 2 and abs(sl[-1] - sl[-2]) <= tol and rpos < 0.2 and price > sl[-1] and mom1 > 0:
            neck = max(x.high for x in w[-15:]) if len(w) >= 15 else rh
            _ekle(11, "LONG", 0.55,
                  f"W-DIP olusumu (cift dip ~{_fmt(mean([sl[-1], sl[-2]]))}): boyun {_fmt(neck)} kirilirsa yukari ivmelenme ADAYI; dipler {_fmt(min(sl[-2:]))} alti kapanista gecersiz",
                  f"cift-dip {_fmt(sl[-2])}/{_fmt(sl[-1])}")
        if len(sh) >= 2 and abs(sh[-1] - sh[-2]) <= tol and rpos > -0.2 and price < sh[-1] and mom1 < 0:
            neck = min(x.low for x in w[-15:]) if len(w) >= 15 else rl
            _ekle(12, "SHORT", 0.55,
                  f"M-TEPE olusumu (cift tepe ~{_fmt(mean([sh[-1], sh[-2]]))}): boyun {_fmt(neck)} kirilirsa asagi ivmelenme ADAYI; tepeler {_fmt(max(sh[-2:]))} ustu kapanista gecersiz",
                  f"cift-tepe {_fmt(sh[-2])}/{_fmt(sh[-1])}")
    except Exception as exc:
        _micro_error("11-12", exc)
    # ── 13 VWAP gerilmesi (ortalamaya donus) ─────────────────────────────
    try:
        vw = _micro_vwap(cs, cfg.vwap_win)
        if vw is not None and vw > 0:
            dists = []
            for i in range(max(20, len(cs) - cfg.vwap_win), len(cs) - 1):
                v2 = _micro_vwap(cs[:i + 1], cfg.vwap_win)
                if v2 and atrs[i] > 0:
                    dists.append((cs[i].close - v2) / atrs[i])
            dz = robust_z(dists, (price - vw) / a, cfg.norm_min_n)
            if dz is not None and abs(dz) >= cfg.vwap_z:
                side13 = "SHORT" if dz > 0 else "LONG"
                _ekle(13, side13, 0.45 + 0.1 * min(3.0, abs(dz)),
                      f"fiyat hacim-ortalamasindan ({_fmt(vw)}) asiri {'yukari' if dz>0 else 'asagi'} gerildi (z={dz:+.1f}): 2-6 mumda VWAP'a DONUS ADAYI",
                      f"vwap={_fmt(vw)} z={dz:+.1f}", seviye=vw)
    except Exception as exc:
        _micro_error("13", exc)
    # ── 14 MOMENTUM iraksamasi ───────────────────────────────────────────
    try:
        lb = cfg.div_lookback
        if len(cs) > lb + 14:
            seg_hi = max(range(len(cs) - lb, len(cs)), key=lambda i: cs[i].high)
            f_then = bar_features(cs, seg_hi, atrs, cfg)
            if c1.high >= cs[seg_hi].high - 0.1 * a and f_then and mom6 < f_then[2] - cfg.div_mom_delta and rpos > 0.2:
                _ekle(14, "SHORT", 0.5,
                      "fiyat tepeyi yeniliyor ama MOMENTUM yenilemiyor (negatif iraksama): 2-6 mumda geri cekilme ADAYI",
                      f"mom6 {f_then[2]:+.2f}->{mom6:+.2f}")
            seg_lo = min(range(len(cs) - lb, len(cs)), key=lambda i: cs[i].low)
            f_then2 = bar_features(cs, seg_lo, atrs, cfg)
            if c1.low <= cs[seg_lo].low + 0.1 * a and f_then2 and mom6 > f_then2[2] + cfg.div_mom_delta and rpos < -0.2:
                _ekle(14, "LONG", 0.5,
                      "fiyat dibi yeniliyor ama SATIS MOMENTUMU zayifliyor (pozitif iraksama): 2-6 mumda tepki ADAYI",
                      f"mom6 {f_then2[2]:+.2f}->{mom6:+.2f}")
    except Exception as exc:
        _micro_error("14", exc)
    # ── 15/16 OI kaliplari (turev) ───────────────────────────────────────
    try:
        ois = [c.oi for c in cs if c.oi is not None]
        if len(ois) >= 8 and ois[-4] > 0:
            hist = _change_series(ois, lag=3)
            chg = (ois[-1] - ois[-4]) / ois[-4]
            oz = robust_z(hist[:-1], chg, cfg.norm_min_n)
            p3 = (price - cs[-4].close) / a if len(cs) >= 4 else 0.0
            if oz is not None and oz <= -cfg.z_extreme and p3 < -cfg.moved_min_atr:
                _ekle(15, "LONG", 0.55 + 0.1 * min(3.0, -oz),
                      "OI SERT DUSTU + fiyat dustu = kaldiracli longlar temizlendi (flush): satis baskisi bosaldi -> 2-8 mumda V-TEPKI ADAYI",
                      f"OIz={oz:+.1f} fiyat3={p3:+.1f}ATR")
            if oz is not None and oz >= cfg.z_extreme and abs(p3) < cfg.absorb_flat_atr:
                yon16 = "LONG" if rpos < -0.2 else ("SHORT" if rpos > 0.2 else "NEUTRAL")
                yer = "dipte" if rpos < -0.2 else ("tepede" if rpos > 0.2 else "ortada")
                _ekle(16, yon16, 0.5,
                      f"OI ARTIYOR ama fiyat DUZ ({yer}): sessiz pozisyon birikimi -> kirilim yonunde ({'yukari' if yon16=='LONG' else 'asagi' if yon16=='SHORT' else 'belirsiz'}) patlama ADAYI",
                      f"OIz={oz:+.1f} fiyat3={p3:+.1f}ATR")
    except Exception as exc:
        _micro_error("15-16", exc)
    # ── 17 KALABALIK-TERS (taker tuzagi) ─────────────────────────────────
    try:
        tks = [c.taker for c in cs if c.taker is not None]
        if snap.taker_ratio is not None and len(tks) >= cfg.norm_min_n + 1:
            tz = robust_z(tks[:-1][-cfg.norm_win:], snap.taker_ratio, cfg.norm_min_n)
            p3 = (price - cs[-4].close) / a if len(cs) >= 4 else 0.0
            if tz is not None and tz >= cfg.z_extreme and p3 < -cfg.moved_min_atr:
                _ekle(17, "SHORT", 0.5,
                      "kalabalik agresif ALIYOR ama fiyat DUSUYOR: alanlar tuzakta -> stoplari asagi tetiklenip dususu HIZLANDIRMA ADAYI",
                      f"takerZ={tz:+.1f} fiyat3={p3:+.1f}ATR")
            elif tz is not None and tz <= -cfg.z_extreme and p3 > cfg.moved_min_atr:
                _ekle(17, "LONG", 0.5,
                      "kalabalik agresif SATIYOR ama fiyat YUKSELIYOR: satanlar tuzakta -> short-kapatmalarla yukselisi HIZLANDIRMA ADAYI",
                      f"takerZ={tz:+.1f} fiyat3={p3:+.1f}ATR")
    except Exception as exc:
        _micro_error("17", exc)
    # ── 18 SQUEEZE yakiti (funding + konum) ──────────────────────────────
    try:
        fh = snap.funding_hist or []
        if snap.funding is not None and len(fh) >= cfg.norm_min_n + 1:
            fz = robust_z(fh[:-1][-cfg.funding_norm_win:], snap.funding, cfg.norm_min_n)
            if fz is not None and fz <= -cfg.z_extreme and not floor_acc and rpos < 0.3:
                _ekle(18, "LONG", 0.55,
                      "funding ASIRI NEGATIF (shortlar odiyor) + destek kirilmadi: SHORT-SQUEEZE yakiti dolu -> yukari kivilcimda zincirleme short-kapama ADAYI",
                      f"fundingZ={fz:+.1f} destek=saglam")
            elif fz is not None and fz >= cfg.z_extreme and not ceil_acc and rpos > -0.3:
                _ekle(18, "SHORT", 0.55,
                      "funding ASIRI POZITIF (longlar odiyor) + direnc asilamadi: LONG-SQUEEZE riski -> asagi kivilcimda zincirleme long-tasfiye ADAYI",
                      f"fundingZ={fz:+.1f} direnc=saglam")
    except Exception as exc:
        _micro_error("18", exc)
    # ── 19/20 BASIS (spot-vadeli primi) — SPOT KOMBINE ───────────────────
    try:
        basis, bz = _micro_basis_z(cs, snap.spot, cfg)
        if bz is not None:
            ois = [c.oi for c in cs if c.oi is not None]
            oi_up = len(ois) >= 4 and ois[-4] > 0 and (ois[-1] - ois[-4]) / ois[-4] > 0
            if bz >= cfg.basis_z_hi and oi_up and rpos > 0.0:
                _ekle(19, "SHORT", 0.55 + 0.1 * min(3.0, bz),
                      f"vadeli SPOTTAN kopuk prim yapiyor (basis z={bz:+.1f}) + OI artiyor = KALDIRAC KOPUGU: spot teyit etmeyen yukselis -> prim sonerken geri cekilme ADAYI",
                      f"basis={basis*100:+.3f}% z={bz:+.1f} OI+")
            elif bz <= -cfg.basis_z_hi and rpos < 0.0:
                _ekle(20, "LONG", 0.55 + 0.1 * min(3.0, -bz),
                      f"vadeli SPOT ALTINDA iskontoda (basis z={bz:+.1f}) = korku asiri: spot sahiplenirse iskonto kapanip yukari TEPKI ADAYI",
                      f"basis={basis*100:+.3f}% z={bz:+.1f}")
    except Exception as exc:
        _micro_error("19-20", exc)
    # ── 21/22 SPOT-ONCULUK / TEYITSIZ-KOPUS — SPOT KOMBINE ───────────────
    try:
        if snap.spot and len(snap.spot) >= cfg.spotlead_win + 2:
            sp = {c.close_ms: c for c in snap.spot if c.close_ms is not None}
            pairs = [(c, sp[c.close_ms]) for c in cs[-(cfg.spotlead_win + 1):] if c.close_ms in sp]
            if len(pairs) >= cfg.spotlead_win:
                pr = (pairs[-1][0].close / pairs[0][0].close - 1.0)
                sr = (pairs[-1][1].close / pairs[0][1].close - 1.0)
                fark = (sr - pr) * price / a   # spot-eksi-vadeli getiri farki (ATR)
                if sr > 0 and fark > 0.15:
                    _ekle(21, "LONG", 0.5 + min(0.3, fark),
                          "yukselisi SPOT surukluyor (vadeliden guclu): ORGANIK talep -> geri cekilmeler alinip devam ADAYI (kaldirac kopugune gore daha saglam)",
                          f"spot={sr*100:+.2f}% vadeli={pr*100:+.2f}%")
                elif sr < 0 and fark < -0.15:
                    _ekle(21, "SHORT", 0.5 + min(0.3, -fark),
                          "dususu SPOT surukluyor (gercek arz): ORGANIK satis -> tepkiler satilip devam ADAYI",
                          f"spot={sr*100:+.2f}% vadeli={pr*100:+.2f}%")
                # teyitsiz kopus: vadeli yeni band-ekstremi yapti, spot yapmadi
                sp_prior = [p[1] for p in pairs[:-1]]
                if c1.high >= rh - 0.05 * a and sp_prior and pairs[-1][1].high < max(x.high for x in sp_prior):
                    _ekle(22, "SHORT", 0.5,
                          "vadeli yeni TEPE denedi ama SPOT TEYIT ETMEDI: kaldirac-itisli kopus -> tuzak/geri cekilme ADAYI",
                          "vadeli-tepe spot-teyitsiz")
                elif c1.low <= rl + 0.05 * a and sp_prior and pairs[-1][1].low > min(x.low for x in sp_prior):
                    _ekle(22, "LONG", 0.5,
                          "vadeli yeni DIP denedi ama SPOT TEYIT ETMEDI: kaldirac-itisli sarkma -> tuzak/tepki ADAYI",
                          "vadeli-dip spot-teyitsiz")
    except Exception as exc:
        _micro_error("21-22", exc)
    # ── 23 ABSORPSIYON duvari (tick) ─────────────────────────────────────
    try:
        of = snap.orderflow
        if of is not None and of.n >= 40 and abs(of.delta_z) >= cfg.climax_z and abs(mom1) < cfg.absorb_flat_atr:
            side23 = "LONG" if of.delta_z < 0 else "SHORT"
            _ekle(23, side23, 0.55,
                  f"agresif {'SATIS' if of.delta_z < 0 else 'ALIS'} yagiyor ama fiyat YERINDEN OYNAMIYOR: pasif {'alici' if of.delta_z < 0 else 'satici'} duvari EMIYOR -> duvarin yonunde ({'yukari' if side23=='LONG' else 'asagi'}) donus ADAYI",
                  f"deltaZ={of.delta_z:+.1f} mom1={mom1:+.2f}")
    except Exception as exc:
        _micro_error("23", exc)
    # ── 24 HACIM kurumasi (yakit bitti) ──────────────────────────────────
    try:
        vols = [c.volume for c in cs[-60:-3]]
        v3 = mean([c.volume for c in cs[-3:]])
        if vols and v3 <= _quantile(vols, 0.15) and er > cfg.er_trend_min and abs(mom6) > 0.3:
            side24 = "SHORT" if mom6 > 0 else "LONG"
            _ekle(24, side24, 0.45,
                  f"trend surerken HACIM KURUDU: {'yukselisin' if mom6>0 else 'dususun'} yakiti azaliyor -> 2-6 mumda duraklama/geri cekilme ADAYI (guclu donus sinyali DEGIL)",
                  f"hacim q15 alti, er={er:.2f}")
    except Exception as exc:
        _micro_error("24", exc)

    # ── 27 ONCEKI GUN ucu miknatisi (PDH/PDL) ─────────────────────────────
    try:
        if cs[-1].close_ms is not None:
            gun = cs[-1].close_ms // 86_400_000
            dun = [c for c in cs if c.close_ms is not None and c.close_ms // 86_400_000 == gun - 1]
            if len(dun) >= 24:
                pdh = max(c.high for c in dun)
                pdl = min(c.low for c in dun)
                if 0 < (pdh - price) <= 1.0 * a:
                    _ekle(27, "NEUTRAL", 0.4,
                          f"onceki gun tepesi {_fmt(pdh)} yakinda (miknatis): test edilip TUTUNAMAZSA sahte-kirilim SHORT tepki ADAYI; kapanisla asilirsa yukari devam",
                          f"PDH={_fmt(pdh)} mesafe={(pdh-price)/a:.1f}ATR")
                elif 0 < (price - pdl) <= 1.0 * a:
                    _ekle(27, "NEUTRAL", 0.4,
                          f"onceki gun dibi {_fmt(pdl)} yakinda (miknatis): test edilip TUTUNURSA LONG tepki ADAYI; kapanisla kirilirsa asagi devam",
                          f"PDL={_fmt(pdl)} mesafe={(price-pdl)/a:.1f}ATR")
    except Exception as exc:
        _micro_error("25-26", exc)

    # ── KOMBO kurulumlar (arastirma: belgelenmis GUC birlesimleri) ────────
    # 25 DIP-TEMIZLIK = OI-flush(15) + basis-iskonto/squeeze-yakiti(20|18) dip bolgesinde
    # 26 TEPE-KOPUGU = basis-prim(19) + (kalabalik-tuzak(17)|vadeli-kopus(22)) tepe bolgesinde
    try:
        var = {m.mid for m in out}
        if 15 in var and (20 in var or 18 in var) and rpos < 0:
            _ekle(25, "LONG", 0.85,
                  "KOMBO: kaldirac temizligi + asiri korku ayni anda (belgelenmis DIP kalibi): satis yakiti bitti -> 2-8 mumda V-TEPKI GUCLU ADAYI",
                  "OI-flush + " + ("basis-iskonto" if 20 in var else "squeeze-yakiti"))
        if 19 in var and (17 in var or 22 in var) and rpos > 0:
            _ekle(26, "SHORT", 0.85,
                  "KOMBO: kaldirac kopugu + tuzak/teyitsizlik ayni anda (belgelenmis TEPE kalibi): yakit bitince sert geri cekilme GUCLU ADAYI",
                  "basis-prim + " + ("kalabalik-tuzak" if 17 in var else "vadeli-kopus"))
    except Exception as exc:
        _micro_error("27", exc)

    # ── 28/29 KOMBO TUZAK (KAZANC-2; 'yemleme->yutulma->tuzak' 3 asamasi tek kalip) ──
    # Bant UCUNDA agresif akis EMILIYOR (|delta_z| buyuk ama fiyat yerinde) + OI siskin;
    # spoof duvar-cekilmesi varsa guc artar. #23 absorpsiyonun konum+OI+spoof KOMBO hali.
    # Salt gosterim+log+olcum (micro_rate); karara DOKUNMAZ (sozlesme).
    try:
        of28 = snap.orderflow
        ois28 = [c.oi for c in cs if c.oi is not None]
        oz28 = None
        if len(ois28) >= 8 and ois28[-4] > 0:
            _h28 = _change_series(ois28, lag=3)
            oz28 = robust_z(_h28[:-1], (ois28[-1] - ois28[-4]) / ois28[-4], cfg.norm_min_n)
        _sp28, _ = spoof_kontrol(snap.book, snap.book2, cfg.spoof_kayip_oran)
        if (of28 is not None and of28.n >= 40 and abs(mom1) < cfg.absorb_flat_atr
                and oz28 is not None and oz28 >= cfg.z_heavy):
            if rpos > 0.33 and of28.delta_z >= cfg.climax_z:
                _ekle(28, "SHORT", 0.6 + (0.15 if _sp28 == "ALIS" else 0.0),
                      f"bant TEPESINDE agresif alimlar EMILIYOR + OI siskin (yem-yutulma kalibi): destek cekilirse sert ASAGI bosalma ADAYI; {_fmt(rh)} ustu guclu kapanis kalibi bozar",
                      f"deltaZ={of28.delta_z:+.1f} OIz={oz28:+.1f} mom1={mom1:+.2f}"
                      + (" spoof=ALIS" if _sp28 == "ALIS" else ""), seviye=rh)
            elif rpos < -0.33 and of28.delta_z <= -cfg.climax_z:
                _ekle(29, "LONG", 0.6 + (0.15 if _sp28 == "SATIS" else 0.0),
                      f"bant DIBINDE agresif satislar EMILIYOR + OI siskin (yem-yutulma kalibi): baski cekilirse sert YUKARI bosalma ADAYI; {_fmt(rl)} alti guclu kapanis kalibi bozar",
                      f"deltaZ={of28.delta_z:+.1f} OIz={oz28:+.1f} mom1={mom1:+.2f}"
                      + (" spoof=SATIS" if _sp28 == "SATIS" else ""), seviye=rl)
    except Exception as exc:
        _micro_error("28", exc)
    # ── dip-short / tepe-long korumasi (yon2 vetosuyla AYNI semantik) ─────
    # Kabul edilmis kirilim SHORT-devamini serbest birakir; AMA dipte TAZE
    # reddedilis mumu (hammer/reclaim) varsa kabul olsa bile SHORT onerilmez —
    # decide() vetosu da kabule bakmadan boyle davranir (dip-short YASAK ilkesi).
    dip_rej_now = _dip_rejection(cs, cfg)
    top_rej_now = _top_rejection(cs, cfg)
    _atr_onc_m = atrs[-2] if len(atrs) >= 2 and atrs[-2] > 0 else a   # ATR-kirlenme fix (H4 kopyasi)
    ext_now = true_range(cs[-1], cs[-2] if len(cs) >= 2 else None) > cfg.ext_bar_atr * _atr_onc_m
    for m in out:
        if m.side == "SHORT" and rpos < -0.33 and (not floor_acc or dip_rej_now or ext_now):
            m.side = "NEUTRAL"
            m.beklenen += "  [taze dipte SHORT onerilmez -> notr]"
        elif m.side == "LONG" and rpos > 0.33 and (not ceil_acc or top_rej_now or ext_now):
            m.side = "NEUTRAL"
            m.beklenen += "  [taze tepede LONG onerilmez -> notr]"
    # REJIM-ONSEL: kalip gucunu icinde bulunulan rejim ailesine gore agirla
    try:
        _aile = rejim_ailesi(snap, cfg)
        _carp = MICRO_REJIM_CARPAN.get(_aile, {})
        for m in out:
            m.guc = _clip(m.guc * _carp.get(m.mid, 1.0), 0.0, 1.0)
    except Exception as exc:
        _micro_error("rejim-carpani", exc)
    # once guvenilirlik katmani (A>B>C), sonra (rejim-agirli) kalip siddeti
    out.sort(key=lambda m: (_TIER_SIRA.get(m.tier, 3), -m.guc))
    return out


def micro_rate(symbol: str, mid: int, side: str, cfg: Config):
    """Kalibin legacy HIT/STOP+expiry bilesik cozum telemetrisi; OOS katkisi DEGIL.
    Yalniz cozulmus satirlar; kalip karar-yonuyle ayni yondeyken sayilir. NO-LOOKAHEAD."""
    if side not in ("LONG", "SHORT"):
        return None
    wins = tot = bad = 0
    for r in _load_signals():
        if r.get("symbol") != symbol or r.get("side") != side:
            continue
        pairs = r.get("micro") or []
        try:
            hit = any(isinstance(p, (list, tuple)) and len(p) == 2
                      and int(p[0]) == mid and p[1] == side for p in pairs)
        except (ValueError, TypeError):
            bad += 1
            continue                     # bozuk/elle-duzenlenmis log satiri paneli cokertmesin
        if not hit:
            continue
        oc = r.get("outcome")
        if oc in ("HIT", "DIR_OK"):
            wins += 1
            tot += 1
        elif oc in ("STOP", "DIR_BAD"):
            tot += 1
    if bad:
        sys.stderr.write(f"[UYARI] mikro telemetri: {bad} bozuk alan atlandi\n")
    if tot < cfg.micro_min_resolved:
        return None
    a2 = cfg.micro_prior_n / 2.0
    return ((wins + a2) / (tot + cfg.micro_prior_n), tot)


def micro_tag(symbol: str, m: MicroScen, cfg: Config) -> str:
    res = micro_rate(symbol, m.mid, m.side, cfg)
    if res is None:
        return "legacy telemetri yetersiz (OOS katkisi degil)"
    rate, n = res
    return f"legacy bilesik cozum ~%{round(rate*100)} (n={n}; OOS katkisi degil)"


_FC_HOLDER = {"v": None}   # decide -> analyze tasima kabi (tek-is parcacikli CLI; her decide sifirlar)
_PLAN_HOLDER = {"v": None}  # decide -> analyze: ISLEM PLANI (canli MC ilk-temas); BEKLE'de de dolar
_PROB_HOLDER = {"v": (1 / 3, 1 / 3, 1 / 3)}
_SCEN_YON_HOLDER = {"v": None}  # F9: senaryo-yon kurtarmasi atesledi mi (side/cell); market gate'lense de PUSU olarak isaretlenir
_ONCU_HOLDER = {"v": None}  # ONCU-YON: leading-sinyal fuzyonu (side/guc/tur/kanit/expansion + driven); PUSU/gosterime tasinir

# ═══ Bug 5: senaryo fail-closed sentinel — None'dan FARKLI (hesaplama hatasi != "senaryo yok") ═══
_SCEN_UNKNOWN = object()


# ═══ Bug 3: decide() sonucunda uretilen tum ara yapilar tek nesnede doner ═══
# Global holder'lar korunur (geri uyumluluk) ama artifacts ile cagrilar-arasi kirlenme
# gorunur/izole hale gelir: decide_with_artifacts anlik snapshot'i dondurur.
@dataclass
class DecisionArtifacts:
    decision: Any = None
    prob: Tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3)
    fuel_cell: Optional[Any] = None
    plan: Optional[Any] = None
    scen144: Optional[Any] = None
    aile: str = ""


def _mirror_invariant_seed(cs: List[Candle]) -> int:
    vals = []
    for i in range(max(1, len(cs) - 64), len(cs)):
        if cs[i - 1].close > 0 and cs[i].close > 0:
            vals.append(round(abs(math.log(cs[i].close / cs[i - 1].close)), 12))
    raw = _sha256_obj({"abs_log_returns": vals,
                       "last_time": cs[-1].close_ms if cs else None})
    return int(raw[:16], 16) % (2 ** 31 - 1) or 1


def scenario_market_engeli(side_hint: Optional[str], side: Optional[str]) -> bool:
    """F3 (FABLE6_5) saf predikat: 144-hucre okumasi ACIK yonlu (LONG/SHORT) ve secilen
    market yonune TERS ise market engellenir (BEKLE). NEUTRAL/eksik okuma engellemez.
    Senaryo yon URETMEZ; yalniz fail-closed risk keser (kullanici sozlesmesi, madde 6)."""
    return (side_hint in ("LONG", "SHORT") and side in ("LONG", "SHORT")
            and side_hint != side)


def _decide_core(snap: Snapshot, cfg: Config, context: DecisionContext,
                 btc_bias: Optional[float] = None,
                 btc_leader: Optional[BtcLeaderState] = None) -> Decision:
    cs = snap.candles
    if context.mode == "LIVE":
        _FC_HOLDER["v"] = None
        _PLAN_HOLDER["v"] = None
    _PROB_HOLDER["v"] = (1 / 3, 1 / 3, 1 / 3)
    _SCEN_YON_HOLDER["v"] = None   # F9: her kararda sifirla (offline dahil)
    _ONCU_HOLDER["v"] = None        # ONCU: her kararda sifirla (cagrilar-arasi kirlenme yok)
    if context.apply_live_gates and snap.stale:
        return _wait("Veri bayat")
    if len(cs) < cfg.min_train // 2 + cfg.horizon:
        return _wait("Yetersiz mum")
    st = build_structure(cs, cfg)
    if not st.valid:
        return _wait("Yapisal kurulum yok")
    atrs = atr_series(cs, cfg.atr_period)
    cur = bar_features(cs, len(cs) - 1, atrs, cfg)
    if cur is None:
        return _wait("Ozellik yok")

    # ── F3 (FABLE6_5): SENARYO SINIFLANDIRMASI NIHAI KARARDAN ONCE ──
    # 144-hucre + 6-aile burada (her karar yolundan once) hesaplanir; d.scen144/d.aile ile
    # log/ekrana tasinir. Yon URETMEZ; asagida yalniz fail-closed market risk kapisi olarak
    # kullanilir. Hesaplanamazsa None kalir ve kapi devreye girmez (mevcut davranis korunur).
    _scen144 = None
    _aile_dc = ""
    _scen_unknown = False  # Bug 5: senaryo HESAPLANAMADI mi (None="senaryo yok" ile karistirma)
    _scen_for_yon = None   # F9: risk-gate kapali olsa da senaryo-yon icin ayri tutulan siniflandirma
    try:
        _scen144 = classify_scenario(snap, st, cfg)
        _aile_dc = rejim_ailesi(snap, cfg)
        _scen_for_yon = _scen144
    except Exception as exc:
        snap.source_errors.append("karar-oncesi senaryo siniflandirmasi: " + str(exc)[:80])
        _scen144 = None      # gosterim-guvenli: sentinel nesnesi hicbir karar yoluna sizmaz
        _scen_unknown = True  # fail-closed kapisi bu bayrakla tetiklenir
    # Kasitli kapatma ayri tutulur (kullanici scen_risk_gate_enabled=False dediyse senaryo yok say)
    if not getattr(cfg, "scen_risk_gate_enabled", True):
        _scen144 = None
        _scen_unknown = False
    # F9: senaryo-yon KAYNAGI risk-gate'ten bagimsizdir (risk-gate market'i keser; yon-kaynagi
    # yon URETIR). side_hint LONG/SHORT ve (varsa) haberci esigi saglaniyorsa aday yon budur.
    _scen_side = None
    if getattr(cfg, "scen_yon_enabled", True) and _scen_for_yon is not None:
        _sh = getattr(_scen_for_yon, "side_hint", "NEUTRAL")
        _min_h = int(getattr(cfg, "scen_yon_min_herald", 0) or 0)
        # TUTARLILIK FIX: F9 senaryo-yonu, plan_kur'un kulladigi AYNI guclu-1s-trend
        # filtresine (bkz. ~satir 6871) tabidir. Guclu 1s trende KARSI senaryo-yon
        # BENIMSENMEZ: aksi halde _decide_core "SENARYO-YON PUSU SHORT" der ama plan_kur
        # o kenari trend filtresiyle siler ve TERS (LONG) pusu kurar -> KARAR mesaji store
        # ile CELISIRDI (canli BTC bulgusu). Zayif/notr 1s trend F9'u kesmez (eski davranis).
        _htd_f9, _hts_f9 = htf_trend(snap.htf, cfg)
        _counter_strong_f9 = (_hts_f9 and _htd_f9 != 0 and _sh in ("LONG", "SHORT")
                              and (_sh == "LONG") != (_htd_f9 > 0))
        if (_sh in ("LONG", "SHORT")
                and getattr(_scen_for_yon, "herald_n", 0) >= _min_h
                and not _counter_strong_f9):
            _scen_side = _sh

    X, y, idxs = build_training(cs, atrs, cfg)
    of = snap.orderflow
    rev_sign, rev_str, rev_reasons = reversal_radar(of, st, cfg)
    # drift: YALNIZ canli order-flow tilt (hafif). htf-trend'i EKLEME — zaten bootstrap
    # orneklerinde var; eklemek cifte-sayim olur ve V-donusunde dibi short'latir.
    # R7 (REPORT_3 ifsa): of.delta_z BURADA (MC drift) ve orderflow_estimate'te (flow
    # bloku) AYNI girdidir -> mc ile flow bloklarinin ayni yonu gostermesi BAGIMSIZ
    # teyit degildir; uzlasmazlik olcumu bloklari bagimsiz sayar (bilincli, belgeli).
    drift = float(_tanh((of.delta_z if of else 0.0) / 2.0))
    seed = _mirror_invariant_seed(cs)
    rng = random.Random(seed)

    paths, _ = mc_simulate(cs, st, drift, cfg, rng)
    mc_probs = mc_endpoint_probs(paths, st.price, st.atr, cfg)
    # LAST_CLOSE endpoint yonu, origin-sonrasi book/premium ile beslenmez. Bu iki
    # yuzey yalniz icra/maliyet ve canli-tazelik kapilarinda kullanilir.
    macro_snap = replace(snap, book=None, book2=None, premium=None)

    estimates = [
        est_logistic(X, y, cur, cfg),
        est_knn(X, y, cur, cfg),
        est_empirical(X, y, cur, cfg),
        est_markov(cs, atrs, cfg),
        Estimate("montecarlo", mc_probs[2],
                 1.0, cfg.mc_paths if paths else 0, "", "mc",
                 p_down=mc_probs[0], p_flat=mc_probs[1]),
        orderflow_estimate(of, rev_sign, rev_str, cfg),
        macro_leading_estimate(macro_snap, cfg),
        est_btc_leader_state(btc_leader, cfg) if btc_leader is not None else est_btc_lead(btc_bias, cfg),
    ]
    # KATMAN B: skill agirliklari (ogrenen+markov+MC); overlay bloklar sabit-modest.
    sk = skill_weights(X, y, idxs, cs, atrs, cfg, random.Random(seed ^ 0x5f3759df))
    for e in estimates:
        if e.n <= 0:
            e.weight = 0.0
        elif e.name in sk:
            e.weight = sk[e.name]
        # flow/macro/btc weight zaten kendi Estimate'inde set (w_flow/w_macro/w_btc)
    probs, disagree, tw, block_p = combine_multiclass(estimates)
    p_down, p_flat, p_up = probs
    _PROB_HOLDER["v"] = probs
    n_train = len(y)
    regime = vol_regime(cs, cfg)
    # ── ONCU (leading) SINYAL FUZYONU (kullanici direktifi; PIT-temiz, ledger okumaz) ──
    # reversal_radar (yukarida 4219) + taze_donus + senaryo V-DIP/V-TOP/EXH + sikisma->genisleme.
    # Karar SURUCUSU: istatistik kenar YOKKEN yonu uretir; kenar VARKEN teyit/karsi-veto/guven +
    # SEVIYE (stop genisletme) + PUSU kenar secimine girer. Gecikmeli pump/dump YON kaynagi DEGIL.
    _oncu = (_oncu_yon(cs, snap.htf, _scen_for_yon, rev_sign, rev_str, cfg)
             if getattr(cfg, "oncu_yon_enabled", True)
             else {"side": "NEUTRAL", "guc": 0.0, "tur": "YOK", "kanitlar": [], "expansion": False})
    _ONCU_HOLDER["v"] = dict(_oncu)     # gosterim/PUSU'ya tasinir (BEKLE'de de dolar)
    _oncu_side = None
    if (getattr(cfg, "oncu_yon_enabled", True) and _oncu["side"] in ("LONG", "SHORT")
            and _oncu["guc"] >= cfg.oncu_yon_min_guc):
        # F9 ile AYNI guclu-4s-karsi filtresi; ANCAK tick radari bizi teyit ediyorsa serbest
        # (gercek donus kaliplari ust-trende karsi mesru — 4s hizalama kapisi da bunu tanir).
        _htd_o, _hts_o = htf_trend(snap.htf, cfg)
        _counter_o = (_hts_o and _htd_o != 0 and (_oncu["side"] == "LONG") != (_htd_o > 0))
        _rev_conf_o = (rev_sign != 0 and ((rev_sign > 0) == (_oncu["side"] == "LONG")))
        if not (_counter_o and not _rev_conf_o):
            _oncu_side = _oncu["side"]
    # ── ONCU TAHMIN hammaddesi (YON9-EK; kullanici isteri: 'hareket OLMADAN once yon soyle') ──
    # Karar kapilarindan BAGIMSIZ hesaplanir ve _FC_HOLDER ile analyze'a tasinir: karar BEKLE
    # olsa bile her kosuda kosulsuz yon+bant tahmini vardir; sicili sonraki kosular OLCer.
    # Karar mantigina dokunmaz (yalniz okuma; RNG tuketmez — paths zaten uretilmis).
    if paths and context.mode == "LIVE":
        try:
            _fin9 = sorted(p9[-1] for p9 in paths)
            _n9 = len(_fin9)
            _q10 = st.price * _fin9[int(0.10 * _n9)]
            _q50 = st.price * _fin9[int(0.50 * _n9)]
            _q90 = st.price * _fin9[min(_n9 - 1, int(0.90 * _n9))]
            _mcp9 = mc_endpoint_probs(paths, st.price, st.atr, cfg)
            _dir9 = argmax_class(_mcp9, cfg.tie_eps_rel)
            _imax9 = CLASSES.index(_dir9) if _dir9 != 0 else 1
            _FC_HOLDER["v"] = {"dir": _dir9, "pup": round(_mcp9[2], 4),
                               "pdown": round(_mcp9[0], 4), "pflat": round(_mcp9[1], 4),
                               "p_selected": round(max(_mcp9) if _dir9 == 0 else _mcp9[_imax9], 4),
                               "class_tie": 1 if _dir9 == 0 and _mcp9[1] < max(_mcp9) else 0,
                               "q10": _q10, "q50": _q50, "q90": _q90,
                               "price0": st.price, "atr": st.atr, "h": cfg.horizon,
                               "celiski": 1 if ((_dir9 > 0 and p_up < p_down) or
                                                (_dir9 < 0 and p_down < p_up)) else 0}
        except Exception as exc:
            _FC_HOLDER["v"] = None
            snap.source_errors.append("oncu tahmin hesaplanamadi: " + str(exc)[:100])
        # ── CANLI MC ILK-TEMAS (ISLEM PLANI hammaddesi; BEKLE'de de dolar) ──
        # 'aradaki fiyatta once ust mu alt mi vurulur' -> hangi limit/pusu once tetiklenir.
        # Bant ucleri (range_high/low) SALT bu barin MC dagilimindan; gecmis kalibrasyon DEGIL.
        try:
            # F5 fix: ilk-temas da bar-ici fitili gorur (Brownian-kopru; mc_first_passage
            # ile ayni yontem ve ayni sigma turetimi). Tetik mekanigi 'igne' ile atesleniyor;
            # basilan olasilik artik ayni dille olculur. Seed veri-turevli ve ana rng
            # akisindan bagimsiz -> ayni bar ayni sayiyi uretir (determinizm korunur).
            _it_sig = ((st.atr / st.price) / cfg.bridge_range_div
                       if cfg.bridge_range_div > 0 and st.price > 0 else 0.0)
            _it_seed = seed ^ 0x517CC1B7
            _pu, _pd, _pn = mc_ilk_temas(paths, st.price, st.range_high, st.range_low,
                                         wick_sig=_it_sig, rng=random.Random(_it_seed))
            # 'paths' da tasinir: islem_plani ayni yollari KENDI bastigi seviyelerde yeniden
            # olcer (havuz seviyesi bant ucundan farkliysa olasilik o seviyeye ait olur —
            # yazilan sayi yazilan seviyenin sayisidir; ek MC maliyeti yok). wick_sig ve
            # seed de tasinir ki render-tarafi olcum AYNI kopru sozlesmesini kullansin.
            _PLAN_HOLDER["v"] = {"p_ust": round(_pu, 4), "p_alt": round(_pd, 4),
                                 "p_yok": round(_pn, 4), "ust_bant": st.range_high,
                                 "alt_bant": st.range_low, "price0": st.price,
                                 "atr": st.atr, "h": cfg.horizon, "paths": paths,
                                 "wick_sig": _it_sig, "it_seed": _it_seed}
        except Exception as exc:
            _PLAN_HOLDER["v"] = None
            snap.source_errors.append("ilk-temas plani hesaplanamadi: " + str(exc)[:100])

    if n_train < cfg.min_train:
        return _wait(f"Kalibrasyon zayif (n={n_train}<{cfg.min_train})", estimates, disagree, regime, block_p)
    # ── ISTATISTIK-KENARI (skill-ailesi) ABSTAIN TESPITI ──
    # F9: bu kapilar artik ERKEN return ETMEZ; once istatistik yon denenir, kenar yoksa
    # (ve scen_yon_enabled) senaryo side_hint'i yonu URETIR. Skill-ailesi kapilari:
    # tw<=0 / sifir-skill / dusuk-guven / flat / down-up tie / uzlasmazlik. Veri/MC kapilari
    # (min_train, MC kurulamadi) ve tum yapisal/maliyet/EV/kalite/htf/RR kapilari AYNEN sert kalir.
    # R3 sifir-skill acik kurali korunur; yalniz senaryo-yon ile kurtarilabilir hale gelir.
    _stat_side = None
    _stat_abstain = None
    if tw <= 0:
        _stat_abstain = "Hicbir tahminci kenarli degil (hepsi sustu)"
    elif getattr(cfg, "zero_skill_abstain", True) and max(sk.values(), default=0.0) <= 0.0:
        _stat_abstain = ("SIFIR-SKILL: hicbir ogrenen/MC tahminci walk-forward kenari kazanamadi; "
                         "yalniz overlay bloklari kaldi — overlay yon acamaz (sozlesme)")
    elif max(probs) < cfg.abstain_prob:
        _stat_abstain = (f"Olasilik guveni dusuk (max sinif=%{max(probs)*100:.0f} < "
                         f"%{cfg.abstain_prob*100:.0f})")
    elif probs[1] >= max(probs[0], probs[2]):
        _stat_abstain = f"Endpoint sinifi FLAT/NOTR (p_flat=%{probs[1]*100:.0f})"
    else:
        _mc = argmax_class(probs, cfg.tie_eps_rel)
        if _mc == 0:
            _stat_abstain = "Endpoint DOWN/UP olasiliklari esit"
        else:
            _stat_side = "LONG" if _mc > 0 else "SHORT"
    # Sorun1 ONARIM (flag fix_meta_label_yon): istatistik kenar YOK + GUCLU-UYUMLU trend ->
    # yonu trend-primary'den al (meta-labeling: yon=trend, ML=gir/girme). Nihai olasilik
    # trende TERS ise DEVREYE GIRMEZ (fail-safe). Yon yine tum EV/HTF/RR kapilarindan gecer.
    if getattr(cfg, "fix_meta_label_yon", False) and _stat_side is None:
        _mlh_d, _mlh_s = htf_trend(snap.htf, cfg)
        # Meta-labeling: skill=0 iken YON trend-primary'den alinir. Emniyet: yalniz nihai
        # olasilik trende ASIRI-ters (opp >= fix_meta_opp_max) ise DEVREYE GIRMEZ. (Hafif
        # contrarian overlay'i veto SAYMAYIZ; yoksa fix kendini kilitler.) Tum EV/HTF/RR kapilari korunur.
        _opp = probs[0] if _mlh_d > 0 else (probs[2] if _mlh_d < 0 else 1.0)
        if _mlh_s and _mlh_d != 0 and _opp < getattr(cfg, "fix_meta_opp_max", 0.55):
            _stat_side = "LONG" if _mlh_d > 0 else "SHORT"
            _stat_abstain = None
            snap.source_errors.append("META-LABEL(flag): skill=0; yon guclu-uyumlu trendden alindi "
                                      "(KANITLANMAMIS kenar; tum kapilar korunur)")
    # uzlasmazlik kapisi: yalniz istatistik yon varken uygulanir (senaryo-yon std'ye bakmaz)
    if context.apply_stateful_gates:
        thr_dis, dis_label, n_dis = adaptive_disagree_max(snap.symbol, cfg, regime)
    else:
        thr_dis, dis_label, n_dis = cfg.disagree_max, "offline-sabit", 0
    if _stat_side is not None and disagree > thr_dis:
        _stat_abstain = (f"Bloklar uzlasmiyor (std={disagree:.2f} > adaptif {thr_dis:.2f}; {dis_label})"
                         if n_dis >= cfg.disagree_adapt_min
                         else f"Bloklar uzlasmiyor (std={disagree:.2f})")
        _stat_side = None

    # ── YON KAYNAGI: istatistik varsa o; yoksa (F9) senaryo side_hint ──
    scen_driven = False
    oncu_driven = False
    if _stat_side is not None:
        model_side = _stat_side
    elif _oncu_side is not None:
        # ONCU-YON (kullanici direktifi, F9'dan ONCE): istatistik kenar yok -> yon oncu
        # (leading) sinyalden gelir. Kullanici onculere daha cok guvenir; bu yuzden senaryo
        # side_hint'inden ONCE denenir. KANITLANMAMIS kenar; tum kapilar AYNEN korunur.
        model_side = _oncu_side
        oncu_driven = True
        if isinstance(_ONCU_HOLDER.get("v"), dict):
            _ONCU_HOLDER["v"]["driven"] = True
        snap.source_errors.append(
            "ONCU-YON: istatistik kenar yok (" + (_stat_abstain or "") +
            f"); yon oncu leading sinyalden alindi ({_oncu_side}, {_oncu['tur']}, "
            f"guc %{int(_oncu['guc']*100)}; KANITLANMAMIS kenar)")
    elif _scen_side is not None:
        model_side = _scen_side
        scen_driven = True
        _SCEN_YON_HOLDER["v"] = {"side": _scen_side,
                                 "cell": getattr(_scen_for_yon, "cell", None),
                                 "aile": _aile_dc,
                                 "abstain": _stat_abstain or ""}
        snap.source_errors.append(
            "F9 SENARYO-YON: istatistik kenar yok (" + (_stat_abstain or "") +
            f"); yon senaryo side_hint'inden alindi ({_scen_side}, hucre #"
            + str(getattr(_scen_for_yon, "cell", "?")) + "; KANITLANMAMIS kenar)")
    else:
        return _wait((_stat_abstain or "Yon yok") + " -> BEKLE",
                     estimates, disagree, regime, block_p)

    # Sorun3 ONARIM (flag fix_zayif_yol_kapisi): kanitsiz yollar (oncu/senaryo) da guven+
    # uzlasmazlik kapisina tabidir (eski kod bunlari yalniz istatistik yolda uyguluyordu).
    if getattr(cfg, "fix_zayif_yol_kapisi", False) and (oncu_driven or scen_driven):
        if disagree > thr_dis or max(probs) < cfg.abstain_prob:
            return _wait("kanitsiz yon + zayif kanit (uzlasmazlik/dusuk-guven) -> BEKLE",
                         estimates, disagree, regime, block_p)

    # ── KATMAN A: origin-PIT iki-tarafli model EV'si ──
    if not paths:
        return _wait("MC kurulamadi", estimates, disagree, regime, block_p)
    # Yon secimi last_closed origininden SONRA gelen book/mark/premium'e bakamaz.
    # Bu nedenle iki taraf ayni origin fiyati + onceden kilitli statik maliyetle
    # karsilastirilir. Canli icra verisi, yon secildikten sonra yalniz tradeability/
    # abstain ve gerceklesebilir seviyeleri belirler; karsi yone ceviremez.
    _model_cost = txn_cost_abs(snap.symbol, st.price, cfg, book=None, side="LONG",
                               atr=st.atr)
    _bridge_seed = seed ^ 0x9E3779B9
    # STOP PAYI sabit degil OLCULUR: sembolun kendi supurme-derinligi q80'i.
    # LONG stopu asagi-supurmelerden (pad_lo), SHORT stopu yukari-supurmelerden (pad_hi).
    _p_lo, _p_hi, _n_lo, _n_hi, _p_cal = supurme_olcumu(cs, atrs, cfg)
    # ── ONCU-RISK STOP GENISLETME (kullanici direktifi; SEVIYEYE etki): sikisma->genisleme
    # (patlama yakin) varken stop paylarini genislet -> patlama fitiliyle erken stoplanma
    # azalir. build_scenario ONCESI uygulanir; p_stop/EV/RR MC ile YENIDEN fiyatlanir, boylece
    # EV/dogruluk/RR kapilari tutarli kalir (seviye yon UYDURMAZ, yalniz stop mesafesi acilir).
    if getattr(cfg, "oncu_yon_enabled", True) and _oncu.get("expansion"):
        _p_lo *= cfg.oncu_stop_widen
        _p_hi *= cfg.oncu_stop_widen
    sc_L = build_scenario(st, "LONG", paths, _model_cost, cfg,
                          rng=random.Random(_bridge_seed), pad_atr=_p_lo,
                          entry_price=st.price)
    sc_S = build_scenario(st, "SHORT", paths, _model_cost, cfg,
                          rng=random.Random(_bridge_seed), pad_atr=_p_hi,
                          entry_price=st.price)
    # Istatistiksel yon endpoint3 toplulugundan gelir. Bariyer EV/RR geometrisi
    # daha az olasi endpoint tarafini secemez; yalniz secilen yonu kabul/red eder.
    primary = sc_L if model_side == "LONG" else sc_S
    other = sc_S if primary is sc_L else sc_L

    if context.apply_stateful_gates:
        ev_min_atr_eff, dir_edge_eff, ev_cal_label = ev_gate_calib(snap.symbol, snap, st, cfg)
    else:
        ev_min_atr_eff, dir_edge_eff, ev_cal_label = cfg.ev_min_atr, cfg.dir_edge_min, "offline-sabit"
    # EV kapisi: EV komisyon/spread/slip SONRASI (funding path-modeli yok). Eski
    # 'max(..., 2*cost)' tabani maliyeti fiilen 3x sayiyordu (EV icinde 1x + kapida 2x) ->
    # BTC'de esik %143·ATR olculdu ve panel yapisal olarak BEKLE'ye kilitlendi. TEK ILKE
    # ("pozitif ve maliyeti asan yon") net-EV>0 ile saglanir; ev_min_atr marj olarak kalir.
    ev_min_abs = ev_min_atr_eff * st.atr

    # ── YAPISAL DIP-SHORT / TEPE-LONG VETOSU (Beklenti #1, kesin garanti) ──
    # Kirilmamis destege yakin + mum reddedilis/reclaim gosteriyorsa SHORT YASAK (dibi short'lama);
    # simetrik: kirilmamis dirence yakin + reddedilis -> LONG yasak. Temiz kirilim/trend'de veto YOK.
    # proximite MUM EKSTREMINE gore: bu mum destegi/direnci TEST etti mi (kapanisa gore degil).
    tested_sup = (cs[-1].low - st.range_low) <= cfg.veto_touch_atr * st.atr
    tested_res = (st.range_high - cs[-1].high) <= cfg.veto_touch_atr * st.atr
    # ASIRI-MUM korumasi: bant ucundaki dev mum (TR > ext_bar_atr x ATR) OFORI/KAPITULASYON
    # adayidir — reddedilis fitili OLMASA bile o ucu KOVALAMAK yasak (V-TEPE seed=7 bulgusu:
    # +%4 govdeli oforide star olusmuyor, veto silahsiz kaliyordu -> tepede LONG cikti).
    # ATR-KIRLENME FIX (denetim, olculdu): fitilsiz -%3 dev kirmizi mum yeni dipte
    # TR/ATR_onceki=2.01 iken ext_bar=False kaliyor ve motor dipte SHORT veriyordu —
    # cunku esik sok-mumun KENDI TR'sini iceren ATR'ye olculuyordu (etkin esik ~2.17x).
    # Niyet 'TR > 2.0 x ATR': taban SON MUM HARIC ATR (atrs[-2]).
    _atr_onc = atrs[-2] if len(atrs) >= 2 and atrs[-2] > 0 else st.atr
    ext_bar = true_range(cs[-1], cs[-2] if len(cs) >= 2 else None) > cfg.ext_bar_atr * _atr_onc
    # FITIL-KOLU (olculen bosluk): bant ucunda SUPURME OLCEKLI karsi-fitil varsa kapanis
    # zayif kalsa bile o ucu kovalamak yasak. V-DIP seed=20 otopsisi: 0.90 ATR alt fitil +
    # kapanis mumun alt yarisinda -> _dip_rejection(False) + ext_bar(False) = veto silahsiz,
    # motor bant dibinde (rpos=0.14) SHORT verdi. Iki yon SIMETRIK (H4).
    _wick_lo = (min(cs[-1].open, cs[-1].close) - cs[-1].low) > cfg.veto_wick_atr * st.atr
    _wick_hi = (cs[-1].high - max(cs[-1].open, cs[-1].close)) > cfg.veto_wick_atr * st.atr
    # CIFT-UC FIX (denetim): dev mum IKI ucu da test ettiyse eski 'elif' yalniz SHORT'u
    # yasaklar, tepe-long vetosu sessizce devre disi kalirdi. Iki bayrak artik BAGIMSIZ;
    # veto-cevirme yasakli yone donemez (iki uc da yasaksa BEKLE).
    forbid_short = tested_sup and (_dip_rejection(cs, cfg) or ext_bar or _wick_lo)
    forbid_long = tested_res and (_top_rejection(cs, cfg) or ext_bar or _wick_hi)

    def _yasak(s):
        return (s == "SHORT" and forbid_short) or (s == "LONG" and forbid_long)
    veto_note = ""
    if _yasak(primary.side):
        _fs = primary.side
        return _wait(f"{_fs} yasak (kirilmamis {'destek' if _fs == 'SHORT' else 'direnc'}te "
                     "reddedilis/reclaim); endpoint yonu tersine cevrilmez -> BEKLE",
                     estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)

    # ── KATMAN C: tick radari veto / uyari (endpoint yonunu cevirmez) ──
    if context.apply_stateful_gates:
        flip_thr, veto_thr, rev_flag, _rev_info = reversal_calib(snap.symbol, cfg)
    else:
        flip_thr, veto_thr, rev_flag = cfg.flip_thresh, cfg.veto_thresh, cfg.reversal_flag
        _rev_info = {"offline": True}
    warn = veto_note
    side_sign = 1 if primary.side == "LONG" else -1
    if rev_sign != 0 and rev_sign != side_sign and rev_str >= flip_thr:
        if rev_str >= veto_thr:
            return _wait(f"Tick radari endpoint yonune guclu karsi; yon cevrilmez "
                         f"({'DIP' if rev_sign > 0 else 'TEPE'} donusu: {', '.join(rev_reasons)})",
                         estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)
        else:
            warn = "ters tick uyarisi; endpoint yonu cevrilmedi"
    elif rev_sign == side_sign and rev_str > 0:
        warn = "tick-akis teyit"

    # VETO-BEKCISI (denetci bulgusu, PLAUSIBLE ama sozlesme geregi kapatildi): tick-flip
    # blogu 'forbid'i yeniden kontrol etmiyordu — teoride radar karari yasakli yone GERI
    # cevirebilirdi (300 sahnede fiilen 0 kez; koruyan sey vetonun kendisi degil EV
    # anti-korelasyonuydu). 'Dipte SHORT ASLA' garantisi artik kod duzeyinde kesin.
    if _yasak(primary.side):
        return _wait(f"{primary.side} yasak (yapisal veto); tick-flip yasakli yone cevirdi -> BEKLE",
                     estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)

    # ── ONCU-SINYAL KARSI-VETO (kullanici direktifi): oncu leading sinyal secilen yone
    # GUCLU ters ise market BEKLE. Yon CEVRILMEZ (yalniz reddedilir) — tam-surucu modda bile
    # karsi-oncu (dump/donus riski) varken acik market kovalanmaz. oncu_driven iken oncu ile
    # yon zaten AYNIdir; bu kapi yalniz oncu ile istatistik/senaryo yonu CELISTIGINDE tetikler.
    if (getattr(cfg, "oncu_veto_enabled", True) and _oncu["side"] in ("LONG", "SHORT")
            and _oncu["side"] != primary.side and _oncu["guc"] >= cfg.oncu_veto_min_guc):
        return _wait(f"ONCU-SINYAL KARSI VETO: {_oncu['tur']} (guc %{int(_oncu['guc']*100)}) "
                     f"secilen {primary.side} yonune ters -> BEKLE "
                     f"({', '.join(_oncu['kanitlar'][:2])})",
                     estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)

    # ── STEP4 BTC BAS-AT KAPISI: BTC 5. islem ati DEGIL; yalniz lider-tempo/risk/veto.
    # Once sembolun kendi son-4 15m kronolojisi okunur, sonra BTC confirm/veto uygulanir.
    # Hard veto yalniz coklu kanit + son4 sembol aleyhteyse market sinyalini kapatir;
    # soft veto islemi kovalamaz, pusu/teyit bekletir. Karsi-yon pusu URETMEZ.
    _last4 = _last4_chronology(cs, atrs, cfg)
    _btc_mode, _btc_why = btc_veto_mode_for_side(btc_leader, primary.side, _last4, snap.symbol, cfg)
    if _btc_mode == "HARD":
        d0 = _wait(f"BTC BAS-AT HARD VETO: {primary.side} market yok -> BEKLE ({_btc_why[:120]})",
                   estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)
        d0.btc_leader = btc_leader
        d0.scen144, d0.aile = _scen144, _aile_dc
        return d0
    elif _btc_mode == "SOFT":
        d0 = _wait("BTC BAS-AT SOFT VETO: market yok; teyit/pusu bekle (" +
                   _btc_why[:110] + ")", estimates, disagree, regime, block_p,
                   sc_L.ev, sc_S.ev)
        d0.btc_leader = btc_leader
        d0.scen144, d0.aile = _scen144, _aile_dc
        return d0
    elif _btc_mode == "RISK":
        veto_note = (veto_note + " | " if veto_note else "") + "BTC DECORRELATION-RISK: guven kismi (" + _btc_why[:90] + ")"
    elif _btc_mode == "CONFIRM":
        veto_note = (veto_note + " | " if veto_note else "") + "BTC CONFIRM: ayni tempo; emir degil (" + _btc_why[:90] + ")"

    # ── F3 (FABLE6_5) SENARYO RISK KAPISI: hucre okumasi secilen yone ACIKCA ters ise
    # market ACILMAZ. Senaryo yon uydurmaz/degistirmez; yalniz fail-closed BEKLE uretir
    # (kullanici sozlesmesi madde 6: "senaryo ... secimi yoneten bir risk katmani").
    # Bagimsiz OOS katkisi olculmedi — bu kapi kanit degil, kullanici-direktifli frendir.
    if getattr(cfg, "scen_risk_gate_enabled", True):
        if _scen_unknown:
            # Bug 5 fail-closed: senaryo hesaplanamadi -> BEKLE ("senaryo yok" ile karistirilmaz)
            d0 = _wait("SENARYO RISK KAPISI: senaryo bilinmiyor; risk kapisi fail-closed "
                       "(hesaplama hatasi) -> market yok",
                       estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)
            d0.btc_leader = btc_leader
            d0.scen144, d0.aile = None, _aile_dc
            return d0
        elif _scen144 is not None and \
                scenario_market_engeli(getattr(_scen144, "side_hint", None), primary.side):
            d0 = _wait(f"SENARYO RISK KAPISI: hucre #{_scen144.cell} okumasi "
                       f"({_scen144.side_hint}) secilen {primary.side} yonune TERS -> market yok "
                       f"(senaryo yon uydurmaz; F3 kullanici sozlesmesi)",
                       estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)
            d0.btc_leader = btc_leader
            d0.scen144, d0.aile = _scen144, _aile_dc
            return d0

    # Yon artik kesin ve origin-PIT katmanindan cikti. Mevcut ask/bid, gorunen
    # derinlik ve ufuktaki funding-settle yalniz BU YONU icra-edilebilir kilabilir
    # veya BEKLE'ye dusurebilir; ters yon secimi yapamaz.
    _chosen_side = primary.side
    _entry_exec = executable_entry_price(snap, _chosen_side, st.price, context)
    _f_kat = 0.0
    if snap.premium and snap.premium.get("next_funding_ms") and snap.premium.get("server_ms"):
        _kalan_ms = snap.premium["next_funding_ms"] - snap.premium["server_ms"]
        _f_kat = 1.0 if 0 <= _kalan_ms <= cfg.horizon * cfg.interval_ms else 0.0
    _exec_cost = txn_cost_abs(snap.symbol, _entry_exec, cfg, book=snap.book,
                              side=_chosen_side, atr=st.atr)
    # FUNDING EN-KOTU-DURUM SINIRI: path-kosullu settlement modeli hala yok (erken
    # hedef/stop temasinda funding hic odenmeyebilir) -> TAHMIN degil UST SINIR ve
    # yalniz settle ufuk icindeyken eklenir. Isaret yok sayilir (|oran|): sinir iki
    # yon icin ayni buyukluktedir ve yon secimi bu noktadan cok once bitmistir ->
    # yalniz EV/RR kapilarini sikilastirabilir (fail-closed), sinyal ACAMAZ, yon CEVIREMEZ.
    _f_bound = 0.0
    if _f_kat:
        if getattr(cfg, "fix_funding_isaret", False):
            # Sorun12 ONARIM: isaret-farkindalikli. LONG funding>0 oder, SHORT funding<0 oder.
            # Odeyen taraf maliyet yazar; ALAN taraf 0 (fail-closed: funding'i kredi yazmayiz).
            _fr_raw = snap.funding if snap.funding is not None else (snap.premium.get("last_funding") or 0.0)
            _signed = _fr_raw if _chosen_side == "LONG" else -_fr_raw
            _f_rate = max(0.0, _signed)
        else:
            _f_rate = max(abs(snap.funding or 0.0),
                          abs(snap.premium.get("last_funding") or 0.0))
        _f_bound = _f_rate * _entry_exec
        if _f_bound > 0:
            _exec_cost += _f_bound
            snap.source_errors.append(
                f"funding ust-siniri EV/RR maliyetine eklendi: %{_f_rate * 100:.4f}"
                " (settle ufuk icinde; path-modeli degil, ust sinir)")
    primary = build_scenario(st, _chosen_side, paths, _exec_cost, cfg,
                             rng=random.Random(_bridge_seed),
                             pad_atr=(_p_lo if _chosen_side == "LONG" else _p_hi),
                             entry_price=_entry_exec)

    if primary.ev * st.atr <= ev_min_abs:
        return _wait(f"EV dusuk (max EV=%{primary.ev*100:.0f}·ATR, esik>%{ev_min_abs/st.atr*100:.0f}) "
                     f"— odul maliyeti asmiyor", estimates, disagree, regime, block_p,
                     sc_L.ev, sc_S.ev)
    # ── YON-DOGRULUGU KAPISI (Beklenti #3, #8): MC'de hedef olasiligi stop'tan DUSUKSE sinyal
    # verme. Saf-EV, uzak-hedef/yuksek-RR piyangolarini gecirebilir (hedef %30 / stop %63 gibi);
    # kullanici "yuksek dogruluk + durustluk" istiyor -> yonun stop'tan daha olasi olmasi SART.
    if primary.p_target <= primary.p_stop + dir_edge_eff:
        return _wait(f"Yon dogrulugu dusuk (MC hedef %{primary.p_target*100:.0f} <= stop "
                     f"%{primary.p_stop*100:.0f}) — az ama emin, BEKLE",
                     estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)

    # STEP4E: market kalite kapisi. RR tek basina yeterli degil; hedef olasiligi mutlak
    # olarak dusuk, stop riski yuksek veya edge kucukse marketi BEKLE'ye cevir.
    _mq_blk, _mq_why = market_quality_kapisi(snap.symbol, primary, cfg)
    if _mq_blk:
        return _wait(_mq_why, estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)
    if getattr(cfg, "market_counter_wick_gate_enabled", True):
        _lw_mq = (min(cs[-1].open, cs[-1].close) - cs[-1].low)
        _uw_mq = (cs[-1].high - max(cs[-1].open, cs[-1].close))
        _contra_wick = ((primary.side == "LONG" and _uw_mq > cfg.veto_wick_atr * st.atr) or
                        (primary.side == "SHORT" and _lw_mq > cfg.veto_wick_atr * st.atr))
        if _contra_wick and (primary.p_target < cfg.market_counter_wick_min_target or
                             primary.p_stop > cfg.market_counter_wick_max_stop):
            return _wait(f"KARSI-FITIL market kalite vetosu: son mum karara karsi buyuk fitil; "
                         f"MC hedef %{primary.p_target*100:.0f}, stop %{primary.p_stop*100:.0f} "
                         f"(esik hedef>=%{cfg.market_counter_wick_min_target*100:.0f}, "
                         f"stop<=%{cfg.market_counter_wick_max_stop*100:.0f}) -> BEKLE",
                         estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)

    # STEP4F: live mark / kapali mum farki buyukse kapali fiyatla yeni market acma.
    if context.apply_live_gates:
        _live_blk, _live_why = live_price_gap_kapisi(snap, st, cfg, kind="market")
        if _live_blk:
            return _wait(_live_why, estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)
        _ml_blk, _ml_why = market_live_data_kapisi(snap.symbol, snap, st, cfg)
        if _ml_blk:
            return _wait(_ml_why, estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)

    # STEP4C: market yasam-dongusu + asimetrik RR kapisi. Yon uretmez; yalniz marketi BEKLE'ye cevirir.
    if context.apply_stateful_gates:
        _open_price = getattr(snap, "live_price", None) or st.price
        _open_blk, _open_why = acik_market_sinyali_var(snap.symbol, cfg, _open_price)
        if _open_blk:
            return _wait("Acik sinyal yasam-dongusu: yeni market yok — " + _open_why,
                         estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)
    _rr_blk, _rr_why = market_risk_kapisi(snap.symbol, primary, cfg)
    if _rr_blk:
        return _wait(_rr_why, estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)

    side = primary.side
    side_sign = 1 if side == "LONG" else -1
    # ── 4 SAATLIK (HTF) HIZALAMA KAPISI — hesap 4s+15m, islem 15m ──
    # 15m yonu 4 saatlik trende KARSI ve 15m'de dogrulanmis donus (tick radari ayni yonde) YOKSA
    # -> BEKLE. Ust-trende karsi "devam" islemi acilmaz; gercek donus kaliplari serbest kalir.
    # Bu kapi YALNIZ sinyali BEKLE'ye cevirebilir; asla yon/giris/hedef/stop uydurmaz (temkinli).
    htf_dir, htf_strong = htf_trend(snap.htf, cfg)
    rev_confirms = (rev_sign != 0 and rev_sign == side_sign)   # tick radari donusu bizim yonde teyit
    if htf_dir != 0 and htf_dir != side_sign:
        if htf_strong and not rev_confirms:
            return _wait(f"4S trendine karsi ({side} 15m, 4s "
                         f"{'YUKARI' if htf_dir > 0 else 'ASAGI'}); donus teyidi yok -> BEKLE",
                         estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)
        warn = (warn + " | 4s trendine karsi (zayif/donus)") if warn else "4s trendine karsi (zayif/donus)"
    elif htf_dir == side_sign:
        warn = (warn + " | 4s trend uyumlu") if warn else "4s trend uyumlu"

    # ── R1 (REPORT_3): ENSEMBLE SOZLESME-TRIPWIRE ──
    # DURUSTLUK: bu blok ISTATISTIK yon yolu icin bir 'ic tutarlilik freni'dir ve o yolda
    # normal akista TETIKLENEMEZ — istatistik side AYNI probs'un argmax'indan turetildi ve
    # normalize_probs argmax'i degistiremez (denetim T9: 0/100.000; T4: 0/200.000).
    # ONCU/SENARYO-YON KAYNAKLARI (oncu_driven/scen_driven) BILINCLI olarak argmax-DISIDIR
    # (istatistik kenar yokken yonu ONLAR uretir) -> bu kaynaklar tripwire'dan MUAFtir; aksi
    # halde her oncu/senaryo-yon karari BEKLE'ye duserdi. Saf predikat DEGISMEDI (selftest
    # YON9-EK #4 birim testi aynen gecer); yalniz cagri yeri kaynak-farkindaligi kazandi.
    if not (scen_driven or oncu_driven) and ensemble_side_conflict(side, probs, tw, cfg):
        snap.source_errors.append("IC-SOZLESME IHLALI: secilen yon topluluk argmax'i degil "
                                  "(R1 tripwire tetiklendi — kod degisikligi sozlesmeyi bozmus)")
        return _wait(f"IC-SOZLESME TRIPWIRE: {side} topluluk argmax'i ile celisiyor "
                     f"(p_down=%{p_down*100:.0f}, p_flat=%{p_flat*100:.0f}, "
                     f"p_up=%{p_up*100:.0f}) -> BEKLE",
                     estimates, disagree, regime, block_p, sc_L.ev, sc_S.ev)

    # ── gosterilen olasilik: MC edge + uzlasma kismasi + walk-forward geri-besleme ──
    edge = _clip(primary.p_target - primary.p_stop, 0.0, 1.0)
    shrink = max(cfg.conf_dis_floor, 1.0 - disagree * cfg.conf_dis_pen)
    if regime == "EXTREME":
        shrink *= cfg.conf_extreme_shrink
    if htf_dir != 0 and htf_dir != side_sign:
        shrink *= cfg.conf_htf_shrink        # 1s trendine karsi (zayif/donus) -> gosterilen guveni kis
    if context.apply_stateful_gates:
        shrink *= realized_shrink(snap.symbol, cfg)  # LIVE risk telemetrisi; OFFLINE saf kalir
    if btc_leader is not None and btc_leader.risk_penalty > 0:
        shrink *= max(0.0, 1.0 - btc_leader.risk_penalty)
        warn = (warn + " | " if warn else "") + (
            "BTC RISK CEZASI: decorrelation/likidite riski -> guven kismi "
            f"({btc_leader.mode}, ceza={btc_leader.risk_penalty:.2f})")
    # REJIM-DINAMIK temkin: donus penceresinde ve/veya kayma alarminda guveni kis
    _td, _td_msg = taze_donus(cs, snap.htf, cfg)
    if _td:
        shrink *= cfg.taze_donus_shrink
        warn = (warn + " | " if warn else "") + "TAZE DONUS: " + _td_msg + " -> temkin"
    # ── ONCU-SINYAL GUVEN ETKISI (kullanici direktifi: 'guveni onculere ver') ──
    # oncu teyit -> uyari notu; oncu zayifca ters (veto esigi alti) -> guven kisilir;
    # sikisma->genisleme -> patlama/stop-genisletme notu. Yon/seviye burada DEGISMEZ.
    if _oncu["side"] in ("LONG", "SHORT"):
        if _oncu["side"] == side:
            warn = (warn + " | " if warn else "") + f"ONCU TEYIT: {_oncu['tur']} (guc %{int(_oncu['guc']*100)})"
        else:
            shrink *= cfg.oncu_counter_shrink
            warn = (warn + " | " if warn else "") + f"ONCU KARSI: {_oncu['tur']} -> guven kisildi"
    if _oncu.get("expansion"):
        warn = (warn + " | " if warn else "") + "SIKISMA->GENISLEME: patlama yakin (stop genisletildi)"
    _ky, _ky_rate, _ky_n = (kayma_alarmi(snap.symbol, cfg)
                             if context.apply_stateful_gates else (False, 0.0, 0))
    if _ky:
        # CANLI-ONLY: gecmis-isabet SAYIYI oynatmaz (uyari metni telemetri olarak kalir);
        # eski modda kisma aynen surer.
        if not getattr(cfg, 'canli_only', False):
            shrink *= cfg.kayma_shrink
        warn = (warn + " | " if warn else "") + ("KAYMA ALARMI: son %d sinyal isabet %%%d"
                                                 % (_ky_n, round(_ky_rate * 100)))
        warn += " -> guven kisildi" if not getattr(cfg, 'canli_only', False) else " (telemetri; sayi oynatilmadi)"
    # ── YON9-EK temkin katmanlari (yalniz gosterilen guven + uyari; yon/seviye DEGISMEZ) ──
    # NOT: eski 4H UST CERCEVE overlay'i KALDIRILDI — veri analizi 1s trend + 15m karar/pusu
    # olarak sadelestirildi (MTF: hesap 1s+15m). Ust-zaman temkini artik yalniz 1 saatlik
    # trenddir (yukaridaki htf_dir kapisi, satir ~4327); 1h'den 4h yeniden ornekleme yok.
    # (a) KARSI-FITIL: son mumda karara karsi supurme-olcekli fitil (bant ortasinda bile) —
    # V-TEPE seed=2/17 olcumu: 1+ ATR ust fitilden hemen sonra LONG frensiz gecmisti.
    _lw_c = min(cs[-1].open, cs[-1].close) - cs[-1].low
    _uw_c = cs[-1].high - max(cs[-1].open, cs[-1].close)
    if (side == "LONG" and _uw_c > cfg.veto_wick_atr * st.atr) or \
       (side == "SHORT" and _lw_c > cfg.veto_wick_atr * st.atr):
        shrink *= cfg.wick_karsit_shrink
        warn = (warn + " | " if warn else "") + "KARSI-FITIL: son mumda karara karsi buyuk fitil -> temkin"
    # (b) FUNDING SETTLE SAYACI: settle'a az kala acilan pozisyon settle oynakligina yakalanir
    # (denetim: predicted funding/nextFundingTime hic okunmuyordu).
    if snap.premium and snap.premium.get("next_funding_ms") and snap.premium.get("server_ms"):
        _dk = (snap.premium["next_funding_ms"] - snap.premium["server_ms"]) / 60000.0
        if 0 <= _dk <= cfg.funding_settle_warn_min:
            warn = (warn + " | " if warn else "") + (
                "FUNDING SETTLE %d dk kala (predicted %%%.4f) -> settle oynakligi riski"
                % (int(_dk), snap.premium.get("last_funding", 0.0) * 100))
    selected_prob = p_up if side == "LONG" else p_down
    uncal_prob = int(round(100.0 * selected_prob * shrink))
    uncal_prob = int(_clip(uncal_prob, 0, cfg.prob_cap))
    if context.apply_stateful_gates:
        prob, score_label, calibrated = calibrate_score(snap.symbol, edge, uncal_prob, cfg)
    else:
        prob, score_label, calibrated = (uncal_prob,
                                         f"OFFLINE OOS sinif olasiligi: %{uncal_prob}", False)
    # Mikro/senaryo bagimsiz OOS katkisi bu surumun kapsami disinda: yalniz telemetri,
    # karar guvenini dahi oynatmaz.
    weak = prob <= cfg.weak_thresh
    reversal_risk = int(round(primary.p_stop * 100))

    _f_maliyet_txt = ("komisyon/spread/slip/gecikme/kismi-dolum+funding-ust-siniri sonrasi"
                      if _f_bound > 0
                      else "komisyon/spread/slip/gecikme/kismi-dolum sonrasi; funding haric")
    _yon_kaynak = ("ONCU-YON (istatistik kenar yok; leading sinyal; KANITLANMAMIS kenar)"
                   if oncu_driven else
                   "SENARYO-YON (istatistik kenar yok; KANITLANMAMIS kenar; F9)"
                   if scen_driven else "endpoint toplulugu")
    sebep = (f"{side} [{_yon_kaynak}]: EV pozitif ({_f_maliyet_txt}); "
             f"MC hedef %{primary.p_target*100:.0f} / stop %{primary.p_stop*100:.0f}")
    tags = []
    if oncu_driven:
        tags.append(f"oncu-yon {_oncu['tur']} guc %{int(_oncu['guc']*100)}")
    if scen_driven:
        tags.append(f"senaryo-yon #{getattr(_scen_for_yon, 'cell', '?')}")
    if weak:
        tags.append(f"zayif ~%{prob}")
    if reversal_risk >= int(rev_flag * 100):
        tags.append(f"DONUS RISKI %{reversal_risk}")
    if warn in ("tick-akis teyit",):
        tags.append(warn)
    if tags:
        sebep += " (" + "; ".join(tags) + ")"

    return Decision(karar=side, prob=prob, entry=primary.entry, target=primary.target, stop=primary.stop,
                    rr=primary.rr, p_target=primary.p_target, reversal_risk=reversal_risk, weak=weak,
                    sebep=sebep, estimates=estimates, rev_sign=rev_sign, rev_reasons=rev_reasons,
                    disagree=disagree, regime=regime, ev=primary.ev, warn=warn,
                    ev_long=sc_L.ev, ev_short=sc_S.ev, block_p=block_p,
                    edge=edge, score_label=score_label, calibrated=calibrated, rev_str=rev_str,
                    funding_bound_atr=(_f_bound / st.atr if st.atr > 0 else 0.0),
                    btc_leader=btc_leader, cost_abs=_exec_cost,
                    scen144=_scen144, aile=_aile_dc,
                    scen_driven=scen_driven,
                    scen_side=(model_side if scen_driven else None),
                    oncu_driven=oncu_driven,
                    oncu_side=(model_side if oncu_driven else None),
                    oncu=dict(_oncu))


def _decision_gate_code(d: Decision) -> str:
    if d.karar in ("LONG", "SHORT"):
        return "EXECUTE_" + d.karar
    s = (d.sebep or "").upper()
    mapping = (("YETERSIZ", "DATA_INSUFFICIENT"), ("BAYAT", "DATA_STALE"),
               ("LATENCY", "LATENCY_GATE"), ("GECIKME", "LATENCY_GATE"),
               ("SIFIR-SKILL", "ZERO_SKILL_GATE"),
               ("OLASILIK GUVENI", "LOW_CONFIDENCE"), ("FLAT", "FLAT_CLASS"),
               ("UZLASMIYOR", "MODEL_DISAGREEMENT"), ("EV ESIT", "EV_TIE"),
               ("EV DUSUK", "LOW_NET_EV"), ("LIVE", "LIVE_DATA_GATE"),
               ("BTC", "BTC_GATE"), ("ACIK SINYAL", "EXPOSURE_GATE"),
               ("TRENDINE KARSI", "HTF_GATE"), ("TOPLULUK", "CLASS_CONFLICT"))
    return next((code for key, code in mapping if key in s), "ABSTAIN_OTHER")


def _canonical_prediction_time(snap: Snapshot, context: DecisionContext) -> Optional[int]:
    """LIVE'da gercek tahmin/fetch/server zamani zorunlu; origin 'simdi' diye kullanilmaz."""
    if context.mode == "LIVE":
        vals = (context.predicted_at_ms, snap.predicted_at_ms,
                snap.live_fetched_ms, snap.live_server_ms)
    else:
        vals = (context.predicted_at_ms, snap.predicted_at_ms, snap.last_closed_ms)
    return next((int(v) for v in vals if isinstance(v, (int, float))), None)


def _stamp_decision(d: Decision, snap: Snapshot, cfg: Config,
                    context: DecisionContext) -> Decision:
    pd, pf, pu = normalize_probs(*_PROB_HOLDER.get("v", (1 / 3, 1 / 3, 1 / 3)))
    predicted_at = _canonical_prediction_time(snap, context)
    d.p_down, d.p_flat, d.p_up = pd, pf, pu
    d.gate_code = _decision_gate_code(d)
    d.mode = context.mode
    d.predicted_at_ms = predicted_at
    # REPORT_4 #6b: last_closed_ms atanmamis (sentetik/harness) snapshot'ta hedef-bitis
    # PIT-guvenli olarak SON KAPALI MUMUN close_ms'inden turetilir; ikisi de yoksa None.
    _origin_ms = snap.last_closed_ms
    if _origin_ms is None and snap.candles and snap.candles[-1].close_ms is not None:
        _origin_ms = snap.candles[-1].close_ms
    d.target_end_ms = ((_origin_ms + cfg.horizon * cfg.interval_ms)
                       if _origin_ms is not None else None)
    d.data_watermark_ms = snap.data_watermark_ms or snap.last_closed_ms
    d.model_hash = model_hash(cfg)
    d.code_hash = code_hash()
    d.feature_hash = feature_hash()
    d.protocol_id = cfg.protocol_id
    d.diagnostics = list(snap.source_errors)
    if (predicted_at is not None and d.data_watermark_ms is not None and
            predicted_at - d.data_watermark_ms > cfg.ledger_max_latency_ms):
        d.diagnostics.append("prediction latency protokol esigini asti")
    if (predicted_at is not None and snap.last_closed_ms is not None and
            predicted_at - snap.last_closed_ms > cfg.ledger_max_latency_ms):
        d.diagnostics.append("origin-to-prediction latency protokol esigini asti")
    return d


def decide_with_artifacts(snap: Snapshot, cfg: Config, btc_bias: Optional[float] = None,
                          btc_leader: Optional[BtcLeaderState] = None,
                          context: Optional[DecisionContext] = None,
                          mode: Optional[str] = None) -> DecisionArtifacts:
    """Bug 3: asil karar motoru. Tum ara yapilari DecisionArtifacts icinde dondurur.
    Global holder'lar hala doldurulur (geri uyumluluk) ama sonuc artifacts'tan okunur ->
    cagrilar-arasi holder kirlenmesi gorunur/izole olur."""
    artifacts = DecisionArtifacts()
    validate_config(cfg)
    if context is not None and mode is not None and context.mode != mode.upper():
        raise ValueError("context.mode ile mode celisiyor")
    if context is None:
        context = (DecisionContext.offline() if (mode or "LIVE").upper() == "OFFLINE"
                   else DecisionContext())
    context = context.validate()
    # ── F10c: CAGRILAR-ARASI HOLDER KIRLENMESI (canli telefon bulgusu) ──
    # _FC_HOLDER/_PLAN_HOLDER/_SCEN_YON_HOLDER reset'i YALNIZ _decide_core basindaydi
    # (satir ~4006). Ama asagidaki LIVE kapilari (eksik-zaman / LATENCY / PIT) _decide_core
    # CAGRILMADAN erken doner; boylece bu holder'lar ONCEKI sembolun degerini korurdu.
    # Canli kanit: 4 sembol SIRAYLA islenirken DOGE LATENCY_GATE'e dustu ve d.fc =
    # _FC_HOLDER.get('v') (analyze ~9297) bir onceki sembolun (SOL) bandini okudu ->
    # yon_forecasts/forward_ledger interval + 'BEKLENEN BANT' ekrani SOL degeriyle kirlendi
    # (p'ler dogru-uniform kaldi, cunku _PROB_HOLDER'i kapilar zaten sifirliyordu). Reset'i
    # her erken-donus yolunu kapsayacak sekilde LIVE'da kapilardan ONCE yap (idempotent;
    # _decide_core'daki reset bilincli olarak korunur — dogrudan cagrilara karsi guvenli).
    if context.mode == "LIVE":
        _FC_HOLDER["v"] = None
        _PLAN_HOLDER["v"] = None
        _SCEN_YON_HOLDER["v"] = None
        _ONCU_HOLDER["v"] = None
    pred_ms = _canonical_prediction_time(snap, context)
    if context.mode == "LIVE" and (pred_ms is None or snap.last_closed_ms is None):
        _PROB_HOLDER["v"] = (1 / 3, 1 / 3, 1 / 3)
        msg = "LIVE LATENCY GATE: gercek tahmin/server zamani veya origin eksik -> BEKLE"
        if msg not in snap.source_errors:
            snap.source_errors.append(msg)
        artifacts.decision = _stamp_decision(_wait(msg), snap, cfg, context)
        artifacts.prob = _PROB_HOLDER.get("v", (1 / 3, 1 / 3, 1 / 3))
        return artifacts
    if context.mode == "LIVE" and pred_ms is not None and snap.last_closed_ms is not None:
        origin_latency = pred_ms - snap.last_closed_ms
        if origin_latency < 0 or origin_latency > cfg.ledger_max_latency_ms:
            _PROB_HOLDER["v"] = (1 / 3, 1 / 3, 1 / 3)
            msg = (f"LIVE LATENCY GATE: origin->tahmin {origin_latency}ms, "
                   f"izin 0..{cfg.ledger_max_latency_ms}ms -> BEKLE")
            if msg not in snap.source_errors:
                snap.source_errors.append(msg)
            artifacts.decision = _stamp_decision(_wait(msg), snap, cfg, context)
            artifacts.prob = _PROB_HOLDER.get("v", (1 / 3, 1 / 3, 1 / 3))
            return artifacts
    pit_bad = snapshot_pit_violations(snap, cfg, pred_ms)
    if pit_bad:
        _PROB_HOLDER["v"] = (1 / 3, 1 / 3, 1 / 3)
        snap.source_errors.extend(x for x in pit_bad if x not in snap.source_errors)
        artifacts.decision = _stamp_decision(
            _wait("PIT veri sozlesmesi bozuk: " + "; ".join(pit_bad)), snap, cfg, context)
        artifacts.prob = _PROB_HOLDER.get("v", (1 / 3, 1 / 3, 1 / 3))
        return artifacts
    d = _decide_core(snap, cfg, context, btc_bias=btc_bias, btc_leader=btc_leader)
    # ── ONCU-YON KAYNAGI atesledi ama MARKET kapisi kesti -> kor BEKLE degil, PUSU {yon} ──
    # (F9 senaryo-yonuyla ayni desen; oncu, ladder'da senaryodan ONCE denendigi icin burada da
    # ONCE kurtarilir.) Karar BEKLE kalir ama oncu_driven+oncu_side isaretlenir; kesin pusu
    # kenari plan_kur'da trend/karne/tek-kenar/oncu filtrelerine gore belirlenir.
    _oyh = _ONCU_HOLDER.get("v")
    if (_oyh and _oyh.get("driven") and getattr(d, "karar", None) == "BEKLE"
            and not getattr(d, "oncu_driven", False) and not getattr(d, "scen_driven", False)):
        d.oncu_driven = True
        d.oncu_side = _oyh.get("side")
        d.oncu = dict(_oyh)
        d.sebep = (f"ONCU-YON {_oyh.get('side')} adayi ({_oyh.get('tur')}, "
                   f"guc %{int(float(_oyh.get('guc', 0.0))*100)}; KANITLANMAMIS kenar): "
                   f"istatistik kenar yok, MARKET uygun degil -> pusu kenari asagidaki ISLEM "
                   f"PLANI'nda (trend/karne/tek-kenar/oncu filtresine gore) | market-red: "
                   + (d.sebep or ""))
    # ── F9: senaryo-yon KAYNAGI atesledi ama MARKET kapisi kesti -> kor BEKLE degil, PUSU {yon} ──
    # Yon senaryodan uretildi; market maliyet/EV/RR/kalite/htf sebebiyle uygun degil -> o yonde
    # PUSU (pusu edge'ini plan_kur zaten kurar). Karar BEKLE kalir (market emri yok) ama gorunur/
    # sayilabilir: scen_driven+scen_side isaretlenir, sebep 'SENARYO-YON PUSU {yon}' olur.
    _syh = _SCEN_YON_HOLDER.get("v")
    if _syh and getattr(d, "karar", None) == "BEKLE" and not getattr(d, "scen_driven", False) \
            and not getattr(d, "oncu_driven", False):
        d.scen_driven = True
        d.scen_side = _syh.get("side")
        # DURUSTLUK FIX: sabit "o yonde PUSU bekle" VAADI verilmez — kurulacak pusu kenari
        # plan_kur'da trend/karne/tek-kenar filtrelerine gore belirlenir ve senaryo-yonundan
        # FARKLI (hatta TERS) olabilir. Mesaj adayi soyler, kesin kenari ISLEM PLANI gosterir.
        d.sebep = (f"SENARYO-YON {_syh.get('side')} adayi (hucre #{_syh.get('cell')}; "
                   f"KANITLANMAMIS kenar): istatistik kenar yok, MARKET uygun degil -> "
                   f"pusu kenari asagidaki ISLEM PLANI'nda (trend/karne/tek-kenar filtresine gore) "
                   f"| market-red: " + (d.sebep or ""))
    artifacts.decision = _stamp_decision(d, snap, cfg, context)
    artifacts.fuel_cell = _FC_HOLDER.get("v")
    artifacts.plan = _PLAN_HOLDER.get("v")
    artifacts.prob = _PROB_HOLDER.get("v", (1 / 3, 1 / 3, 1 / 3))
    artifacts.scen144 = getattr(d, "scen144", None)
    artifacts.aile = getattr(d, "aile", "") or ""
    return artifacts


def decide(snap: Snapshot, cfg: Config, btc_bias: Optional[float] = None,
           btc_leader: Optional[BtcLeaderState] = None,
           context: Optional[DecisionContext] = None,
           mode: Optional[str] = None) -> Decision:
    """Kamu karar API'si. Backtest/CPCV mutlaka context=DecisionContext.offline() verir.
    Geriye uyumluluk icin Decision doner; ara yapilar icin decide_with_artifacts kullanin."""
    return decide_with_artifacts(
        snap, cfg, btc_bias=btc_bias, btc_leader=btc_leader,
        context=context, mode=mode).decision


# ════════════════════════════════════════════════════════════════════════════
# CANLI VERI (fapi.binance REST)
# ════════════════════════════════════════════════════════════════════════════
FAPI = "https://fapi.binance.com"
SAPI = "https://api.binance.com"     # SPOT (basis/iraksama icin; erisilemezse katman susar)
TIMEOUT = 12
HEADERS = {"User-Agent": "fable6/1.0"}
_API_ERRORS: List[str] = []


# ═══ Bug 12: API key sizintisi — public uclara ASLA X-MBX-APIKEY eklenmez ═══
# Eski _get her public istege env'deki BINANCE_API_KEY'i header olarak koyuyordu; bu anahtar
# proxy/loglara sizabiliyordu. Public ve imzali istemciler AYRI siniflardir (miras YOK):
# PublicClient auth header'i YAPISAL OLARAK kabul etmez -> sizinti imkansiz.
class PublicClient:
    """Public endpoint'ler. API key/header KABUL ETMEZ."""
    def __init__(self, base_url: str = FAPI, timeout: int = TIMEOUT):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return dict(HEADERS)  # auth YOK

    def get(self, path: str, params: Dict[str, str]) -> Optional[object]:
        q = urllib.parse.urlencode(params)
        url = f"{self._base_url}{path}" + (f"?{q}" if q else "")
        try:
            req = urllib.request.Request(url, headers=self._headers())
            with urllib.request.urlopen(req, timeout=self._timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:
            msg = f"{path}: {type(exc).__name__}: {str(exc)[:120]}"
            _API_ERRORS.append(msg)
            del _API_ERRORS[:-100]
            sys.stderr.write("[VERI-UYARI] " + msg + "\n")
            return None


class SignedClient:
    """Imzali endpoint'ler. API key GEREKTIRIR. PublicClient'tan MIRAS ALMAZ
    (bu proje public-only'dir; sinif yapisal ayrimi belgelemek/gelecekte guvenli
    kullanmak icindir — canli veri yolu bunu CAGIRMAZ)."""
    def __init__(self, base_url: str, api_key: str, api_secret: str,
                 timeout: int = TIMEOUT):
        if not api_key or not api_secret:
            raise ValueError("SignedClient: api_key/secret eksik")
        import hmac
        self._hmac = hmac
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._api_secret = api_secret
        self._timeout = timeout

    def _sign(self, query: str) -> str:
        return self._hmac.new(self._api_secret.encode("utf-8"),
                              query.encode("utf-8"), hashlib.sha256).hexdigest()


_public_client: Optional[PublicClient] = None


def _get_public_client() -> PublicClient:
    global _public_client
    if _public_client is None:
        _public_client = PublicClient()
    return _public_client


def _get(path: str, params: Dict[str, str], base: str = FAPI) -> Optional[object]:
    """Public GET. PublicClient kullanir — X-MBX-APIKEY header'i YOK (Bug 12)."""
    if base == FAPI:
        return _get_public_client().get(path, params)
    return PublicClient(base_url=base).get(path, params)


def fetch_klines(symbol, interval, limit, cutoff_ms: Optional[int] = None) -> List[Candle]:
    cutoff_ms = int(time.time() * 1000) if cutoff_ms is None else int(cutoff_ms)
    need, end_ms, raw_all = max(1, int(limit) + 1), cutoff_ms, []  # forming mum filtrelenince limit tam kalsin
    while need > 0:
        take = min(1500, need)
        raw = _get("/fapi/v1/klines", {"symbol": symbol, "interval": interval,
                                       "limit": str(take), "endTime": str(end_ms)})
        if not isinstance(raw, list) or not raw:
            break
        raw_all.extend(raw)
        # F2 fix: tek bozuk openTime tum sayfalamayi dusurmesin — parse edilebilenlerin min'i.
        _opens = []
        for k in raw:
            try:
                _opens.append(int(k[0]))
            except (ValueError, TypeError, IndexError):
                continue
        if not _opens:
            break
        next_end = min(_opens) - 1
        if next_end >= end_ms or len(raw) < take:
            break
        end_ms = next_end
        need -= len(raw)
    if not raw_all:
        return []
    out = []
    bad_rows = 0
    seen = set()
    # F2 fix: siralama anahtari (openTime) bozuksa ValueError TUM fetch'i dusuruyordu ve
    # 'bozuk satir atlandi' sozlesmesi alan-0 icin bosa cikiyordu. Once parse, sonra sirala.
    _rows = []
    for k in raw_all:
        try:
            _rows.append((int(k[0]), k))
        except (ValueError, TypeError, IndexError):
            bad_rows += 1
    for _open_ms, k in sorted(_rows, key=lambda t: t[0]):
        try:
            close_ms = int(k[6])
            if close_ms > cutoff_ms or close_ms in seen:  # forming + sayfalama duplikati yok
                continue
            seen.add(close_ms)
            out.append(Candle(open=float(k[1]), high=float(k[2]), low=float(k[3]),
                              close=float(k[4]), volume=float(k[5]),
                              close_ms=close_ms,
                              quote_volume=float(k[7]) if len(k) > 7 else 0.0,
                              trade_count=int(k[8]) if len(k) > 8 else 0,
                              taker_buy_base=float(k[9]) if len(k) > 9 else 0.0,
                              taker_buy_quote=float(k[10]) if len(k) > 10 else 0.0))
        except (ValueError, IndexError, TypeError):
            bad_rows += 1
            continue
    if bad_rows:
        _API_ERRORS.append(f"{symbol} futures kline: {bad_rows} bozuk satir atlandi")
    return out[-limit:]


def fetch_spot_klines(symbol, interval, limit, cutoff_ms: Optional[int] = None) -> List[Candle]:
    """SPOT 15m mumlari; yalniz cutoff aninda tamamlanmis mumlar."""
    raw = _get("/api/v3/klines", {"symbol": symbol, "interval": interval,
                                   "limit": str(min(1000, int(limit) + 1))},
               base=SAPI)
    if not isinstance(raw, list) or not raw:
        return []
    out = []
    bad_rows = 0
    cutoff_ms = int(time.time() * 1000) if cutoff_ms is None else int(cutoff_ms)
    # F7b (FABLE6_5): vadeli fetch_klines ile ayni sozlesme — openTime'a gore SIRALA ve
    # close_ms uzerinden DEDUPE et (tel-sirasina guvenilmez; bozuk satir zaten atlanir).
    _rows_sp = []
    for k in raw:
        try:
            _rows_sp.append((int(k[0]), k))
        except (ValueError, IndexError, TypeError):
            bad_rows += 1
            continue
    _seen_sp = set()
    for _open_ms, k in sorted(_rows_sp, key=lambda t: t[0]):
        try:
            close_ms = int(k[6])
            if close_ms > cutoff_ms or close_ms in _seen_sp:
                continue
            _seen_sp.add(close_ms)
            out.append(Candle(open=float(k[1]), high=float(k[2]), low=float(k[3]),
                              close=float(k[4]), volume=float(k[5]),
                              close_ms=close_ms,
                              quote_volume=float(k[7]) if len(k) > 7 else 0.0,
                              trade_count=int(k[8]) if len(k) > 8 else 0,
                              taker_buy_base=float(k[9]) if len(k) > 9 else 0.0,
                              taker_buy_quote=float(k[10]) if len(k) > 10 else 0.0))
        except (ValueError, IndexError, TypeError):
            bad_rows += 1
            continue
    if bad_rows:
        _API_ERRORS.append(f"{symbol} spot kline: {bad_rows} bozuk satir atlandi")
    return out[-limit:]


def fetch_aggtrades(symbol, limit, end_time: Optional[int] = None):
    params = {"symbol": symbol, "limit": str(limit)}
    if end_time is not None:
        params["endTime"] = str(int(end_time))
    raw = _get("/fapi/v1/aggTrades", params)
    if not isinstance(raw, list):
        return []
    out = []
    bad_rows = 0
    for t in raw:
        try:
            out.append((float(t["p"]), float(t["q"]), int(t["T"]), bool(t["m"])))
        except (KeyError, ValueError, TypeError):
            bad_rows += 1
            continue
    if bad_rows:
        _API_ERRORS.append(f"{symbol} aggTrades: {bad_rows} bozuk satir atlandi")
    return out


def fetch_oi(symbol, limit=100):
    # PENCERE FIX (2.tur): Config norm_win=96 z-penceresi isterken seri 48 bar cekiliyordu
    # (konfigurasyonun istedigi gecmisin YARISI sessizce eksikti). 100 bar = 96 + momentum lag.
    raw = _get("/futures/data/openInterestHist",
               {"symbol": symbol, "period": "15m", "limit": str(limit)})
    if not isinstance(raw, list):
        return []
    out = []
    bad_rows = 0
    for x in raw:
        try:
            out.append((int(x.get("timestamp", 0)), float(x.get("sumOpenInterest", 0.0)),
                        float(x.get("sumOpenInterestValue", 0.0))))
        except (ValueError, AttributeError, TypeError):
            bad_rows += 1
    if bad_rows:
        _API_ERRORS.append(f"{symbol} OI: {bad_rows} bozuk satir atlandi")
    return out


def fetch_taker_series(symbol, limit=100):
    # PENCERE FIX (2.tur): norm_win=96 icin 48 bar yetmiyordu (ayni gerekce fetch_oi'de).
    raw = _get("/futures/data/takerlongshortRatio",
               {"symbol": symbol, "period": "15m", "limit": str(limit)})
    if not isinstance(raw, list):
        return []
    out = []
    bad_rows = 0
    for x in raw:
        try:
            out.append((int(x.get("timestamp", 0)), float(x.get("buySellRatio")),
                        float(x.get("buyVol", 0.0)), float(x.get("sellVol", 0.0))))
        except (ValueError, AttributeError, TypeError):
            bad_rows += 1
    if bad_rows:
        _API_ERRORS.append(f"{symbol} taker: {bad_rows} bozuk satir atlandi")
    return out


def fetch_book(symbol):
    raw = _get("/fapi/v1/depth", {"symbol": symbol, "limit": "100"})
    fetched_ms = int(time.time() * 1000)
    if not isinstance(raw, dict):
        return None
    try:
        bids = [(float(p[0]), float(p[1])) for p in raw.get("bids", [])]
        asks = [(float(p[0]), float(p[1])) for p in raw.get("asks", [])]
    except (ValueError, IndexError):
        return None
    if not bids or not asks:
        return None
    bq = sum(q for _, q in bids)
    aq = sum(q for _, q in asks)
    tot = bq + aq
    if tot <= 0:
        return None
    bb = max(p for p, _ in bids)
    ba = min(p for p, _ in asks)
    mid = (bb + ba) / 2.0
    spread = max(ba - bb, 0.0)
    # YON9-EK: taraf toplamlari (spoof kiyasi) + seviye listeleri (derinlikten slippage olcumu)
    return {"imbalance": (bq - aq) / tot, "spread": spread,
            "spread_pct": (spread / mid) if mid > 0 else 0.0,
            "bid": bb, "ask": ba, "mid": mid,
            "bid_qty": bq, "ask_qty": aq,
            "last_update_id": raw.get("lastUpdateId"), "fetched_ms": fetched_ms,
            "bids": sorted(bids, key=lambda t: -t[0])[:50],
            "asks": sorted(asks, key=lambda t: t[0])[:50]}


def fetch_premium(symbol):
    """YON9-EK: /fapi/v1/premiumIndex — mark/index fiyati, PREDICTED funding
    (lastFundingRate) ve settle zamani (nextFundingTime). Public REST; auth istemez.
    NOT: sandbox'ta Binance engelli — canli ilk dogrulama kullanicinin telefonunda."""
    raw = _get("/fapi/v1/premiumIndex", {"symbol": symbol})
    fetched_ms = int(time.time() * 1000)  # cevap doner donmez; sonraki fetch'lerden ONCE
    if not isinstance(raw, dict):
        return None
    try:
        return {"mark": float(raw.get("markPrice", 0.0)),
                "index": float(raw.get("indexPrice", 0.0)),
                "last_funding": float(raw.get("lastFundingRate", 0.0)),
                "next_funding_ms": int(raw.get("nextFundingTime", 0)),
                "server_ms": int(raw.get("time", 0)),
                "fetched_ms": fetched_ms}
    except (ValueError, TypeError):
        return None


def fetch_ls_ratios(symbol, cutoff_ms: Optional[int] = None):
    """YON9-EK: top-trader pozisyon L/S + global hesap L/S oranlari (15m, son deger).
    /futures/data/... public REST. Eksik veri denetiminin dogrudan cevabi:
    'OI+/fiyat- hucresi short birikimi VARSAYIYORDU' — artik taraf ayrisimi OLCULUYOR."""
    out = [None, None]
    times = [None, None]
    endpoints = ("/futures/data/topLongShortPositionRatio",
                 "/futures/data/globalLongShortAccountRatio")
    for i, path in enumerate(endpoints):
        raw = _get(path, {"symbol": symbol, "period": "15m", "limit": "2"})
        try:
            if isinstance(raw, list) and raw:
                eligible = [x for x in raw if cutoff_ms is None or
                            int(x.get("timestamp", 0) or 0) <= cutoff_ms]
                if eligible:
                    out[i] = float(eligible[-1].get("longShortRatio", 0.0)) or None
                    times[i] = int(eligible[-1].get("timestamp", 0)) or None
        except (ValueError, TypeError, AttributeError) as exc:
            _API_ERRORS.append(f"{symbol} L/S {path}: satir okunamadi ({str(exc)[:60]})")
    return out[0], out[1], times[0], times[1]


def spoof_kontrol(book1, book2, kayip_oran: float):
    """YON9-EK (saf fonksiyon): iki derinlik ornegi arasinda bir tarafin duvari
    kayip_oran'dan fazla KUCULduyse spoof suphesi. Doner: (taraf|None, kayip_yuzde).
    L2 zaman-serisi yok (REST siniri) — bu iki-orneklik VEKIL olcumdur, kesin teshis degil."""
    if not book1 or not book2:
        return None, 0.0
    for taraf, k in (("ALIS", "bid_qty"), ("SATIS", "ask_qty")):
        a, b = book1.get(k, 0.0), book2.get(k, 0.0)
        if a > 0 and (a - b) / a >= kayip_oran:
            return taraf, (a - b) / a
    return None, 0.0


def slip_olcum_frac(book, notional: float, side: str):
    """YON9-EK (saf fonksiyon): derinlik seviyelerinden 'notional' buyuklukte piyasa
    emrinin fiyat etkisi (oran). Seviye yoksa None -> sabit SLIP tablosuna dusulur.
    Denetim bulgusu: sabit tablo ince defterde gercek kaymanin katlarca altindaydi."""
    if not book:
        return None
    lvls = book.get("asks" if side == "BUY" else "bids") or []
    if not lvls:
        return None
    best = lvls[0][0]
    kalan, maliyet, adet = notional, 0.0, 0.0
    for p, q in lvls:
        if p <= 0 or q <= 0:
            continue
        al = min(kalan / p, q)
        maliyet += al * p
        adet += al
        kalan -= al * p
        if kalan <= 0:
            break
    if adet <= 0 or best <= 0:
        return None
    vwap = maliyet / adet
    frac = abs(vwap - best) / best
    if kalan > max(1e-8, abs(notional) * 1e-12):
        # Istenen notional gorunen defterle dolmuyor: uydurma %0.1 ekleme yerine
        # icra-edilemez (sonsuz kayma) bildir; karar maliyet kapisinda bloke olur.
        return math.inf
    return frac


def fetch_funding_hist(symbol, limit=200):
    raw = _get("/fapi/v1/fundingRate", {"symbol": symbol, "limit": str(limit)})
    if not isinstance(raw, list):
        return []
    out = []
    bad_rows = 0
    for x in raw:
        try:
            out.append((int(x.get("fundingTime", 0)), float(x.get("fundingRate"))))
        except (ValueError, TypeError, AttributeError):
            bad_rows += 1
            continue
    if bad_rows:
        _API_ERRORS.append(f"{symbol} funding: {bad_rows} bozuk satir atlandi")
    return out


def _server_now():
    raw = _get("/fapi/v1/time", {})
    if isinstance(raw, dict) and "serverTime" in raw:
        try:
            return int(raw["serverTime"])
        except (ValueError, TypeError) as exc:
            _API_ERRORS.append("serverTime gecersiz, yerel saate dusuldu: " + str(exc)[:60])
    try:
        return int(time.time() * 1000)
    except Exception:
        return None


def _attach_series(cs: List[Candle], series: List[Tuple[int, float]], attr: str,
                   max_age_ms: int = 0) -> None:
    """timestamp-hizali ekleme (positional degil). En yakin <= close_ms olan degeri baglar.
    Sorun1v ONARIM: max_age_ms>0 iken en yakin deger bu yastan daha eskiyse BAGLANMAZ
    (bayat OI/taker/funding ileri-tasinmaz). max_age_ms=0 = eski davranis (sinirsiz)."""
    if not series or not cs:
        return
    series = sorted(series, key=lambda t: t[0])
    times = [t[0] for t in series]
    import bisect
    for c in cs:
        if c.close_ms is None:
            continue
        j = bisect.bisect_right(times, c.close_ms) - 1
        if j >= 0:
            if max_age_ms and (c.close_ms - series[j][0]) > max_age_ms:
                continue  # deger cok bayat -> baglanmaz (Sorun1v)
            setattr(c, attr, series[j][1])
            if attr == "oi" and len(series[j]) > 2:
                c.oi_value = series[j][2]
            elif attr == "taker" and len(series[j]) > 3:
                c.taker_buy_vol = series[j][2]
                c.taker_sell_vol = series[j][3]


def _gapsiz_sufiks(cs: List[Candle], step_ms: int, tol_bars: int = 0) -> Tuple[List[Candle], int]:
    """F3 fix yardimcisi: pencerede zaman boslugu varsa bosluk-SONRASI en uzun bitisik
    sufiksi doner (sufiks ayni SON kapanista biter; gelecege dokunulmaz -> no-lookahead).
    Sorun7 ONARIM: tol_bars>0 iken <= (1+tol_bars) barlik kucuk bosluklar TOLERE edilir
    (kesme yapilmaz); yalniz tol'u asan gercek boslukta gecmis kirpilir. tol_bars=0 =
    eski davranis (bxa != step -> kes)."""
    if len(cs) < 2:
        return cs, 0
    _maxgap = step_ms * (1 + max(0, int(tol_bars)))
    for i in range(len(cs) - 1, 0, -1):
        a, b = cs[i - 1].close_ms, cs[i].close_ms
        if a is None or b is None or (b - a) < step_ms or (b - a) > _maxgap:
            return cs[i:], i
    return cs, 0


# ═══ Bug 11: veri-yeterlilik degerlendirmesi (sade bar-sayisi DEGIL: sure+fold+gap) ═══
class DataStatus:
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    INSUFFICIENT_FOLDS = "INSUFFICIENT_FOLDS"
    EXCESSIVE_GAPS = "EXCESSIVE_GAPS"


@dataclass
class DataAssessment:
    status: str
    total_bars: int
    total_days: float
    fold_count: int
    gap_ratio: float
    message: str = ""

    @property
    def is_sufficient(self) -> bool:
        return self.status == DataStatus.SUFFICIENT


def assess_data_sufficiency(candles: List[Candle], interval_ms: int,
                            min_days: float = 730.0, min_folds: int = 5,
                            max_gap_ratio: float = 0.05) -> DataAssessment:
    """Bug 11: veri yeterliligi — sadece bar sayisi degil, SURE + FOLD + GAP politikasi.
    (min_days/min_folds varsayilanlari OOS/backtest baglamicidir; canli snapshot telemetrisi
    build_snapshot icinde CANLI-uygun parametrelerle cagirir, karar KAPISI DEGILDIR.)"""
    if not candles:
        return DataAssessment(DataStatus.INSUFFICIENT_HISTORY, 0, 0.0, 0, 1.0, "Veri bos")
    timestamps = sorted([c.close_ms for c in candles if c.close_ms is not None])
    total_bars = len(timestamps)
    if total_bars < 2:
        return DataAssessment(DataStatus.INSUFFICIENT_HISTORY, total_bars, 0.0, 0, 1.0,
                              "Tek bar — sure hesaplanamaz")
    total_days = (timestamps[-1] - timestamps[0]) / (1000 * 60 * 60 * 24)
    expected = interval_ms
    gaps = 0
    for i in range(1, len(timestamps)):
        delta = timestamps[i] - timestamps[i - 1]
        if delta > expected * 1.5:
            gaps += int(delta / expected) - 1
    expected_bars = int((timestamps[-1] - timestamps[0]) / expected) + 1
    gap_ratio = gaps / max(expected_bars, 1)
    fold_count = max(1, int(total_days / (min_days / min_folds))) if min_folds > 0 else 1
    if total_days < min_days:
        return DataAssessment(DataStatus.INSUFFICIENT_HISTORY, total_bars, total_days,
                              fold_count, gap_ratio,
                              f"Sure yetersiz: {total_days:.0f} gun < {min_days:.0f} gun")
    if fold_count < min_folds:
        return DataAssessment(DataStatus.INSUFFICIENT_FOLDS, total_bars, total_days,
                              fold_count, gap_ratio,
                              f"Fold yetersiz: {fold_count} < {min_folds}")
    if gap_ratio > max_gap_ratio:
        return DataAssessment(DataStatus.EXCESSIVE_GAPS, total_bars, total_days,
                              fold_count, gap_ratio,
                              f"Gap orani yuksek: %{gap_ratio*100:.1f} > %{max_gap_ratio*100:.1f}")
    return DataAssessment(DataStatus.SUFFICIENT, total_bars, total_days,
                          fold_count, gap_ratio, "Yeterli")


def build_snapshot(symbol: str, cfg: Config) -> Snapshot:
    err0 = len(_API_ERRORS)
    src: Dict[str, Dict[str, Any]] = {}
    _srv = _server_now()
    _t1 = int(time.time() * 1000)
    cutoff = _srv if _srv is not None else _t1
    # F12 fix: cihaz-saat sapmasi olculur (sunucu-yerel); _server_now yerel-fallback'te ~0.
    _clock_ofs = cutoff - _t1

    # ── F13 fix: bagimsiz REST uclari PARALEL cekilir (saf stdlib threading). Eski seri
    # zincir en-kotu ~12 istek x 12sn timeout + 1.2sn spoof beklemesi = 120sn latency
    # butcesinin tamamini yiyebiliyordu (yavas mobil agda kalici BEKLE). Bagimlilik sirasi
    # korunur: once cutoff; sonra bagimsiz uclar; en son last_closed'a bagli uclar + spoof
    # 2. derinlik ornegi (ilk book'tan >= spoof_bekle_sn sonra). PIT sozlesmesi degismez:
    # tum kline fetch'leri ayni sunucu-cutoff'unu kullanir, available_time gorev-bitis
    # zamanidir. YON_PARALEL_FETCH=0 -> eski seri davranis (ayni gorev listesi, sirali).
    _par = os.environ.get("YON_PARALEL_FETCH", "1") != "0"

    def _fetch_grubu(gorevler):
        """[(ad, fn)] -> {ad: (sonuc, bitis_ms)}. Gorev hatasi _API_ERRORS'a yazilir, sonuc None."""
        sonuc: Dict[str, Tuple[Any, int]] = {}

        def _tek(ad, fn):
            try:
                r = fn()
            except Exception as e:
                _API_ERRORS.append(f"{ad}: {type(e).__name__}: {str(e)[:100]}")
                r = None
            # F12: available_time damgasi da AYNI sunucu-ofsetiyle cipalanir; predicted_at
            # ile ayni saat cercevesi -> skew hicbir yonde sahte PIT ihlali uretemez.
            sonuc[ad] = (r, int(time.time() * 1000) + _clock_ofs)

        if not _par or len(gorevler) <= 1:
            for ad, fn in gorevler:
                _tek(ad, fn)
            return sonuc
        import threading
        ths = [threading.Thread(target=_tek, args=(ad, fn), daemon=True)
               for ad, fn in gorevler]
        for t in ths:
            t.start()
        for t in ths:
            t.join()
        return sonuc

    # MUKERRER-FETCH FIX (2.tur) korunur: funding, premium'dan degil funding_hist'ten;
    # /premiumIndex tek kez cekilir.
    g1 = _fetch_grubu([
        ("klines_15m", lambda: fetch_klines(symbol, "15m", cfg.kline_limit, cutoff_ms=cutoff)),
        ("klines_4h", lambda: fetch_klines(symbol, "4h", 120, cutoff_ms=cutoff)),
        ("open_interest", lambda: fetch_oi(symbol)),
        ("taker_ratio", lambda: fetch_taker_series(symbol)),
        ("book", lambda: fetch_book(symbol)),
        ("premium", lambda: fetch_premium(symbol)),
        ("funding_history", lambda: fetch_funding_hist(symbol)),
        ("spot_15m", lambda: fetch_spot_klines(symbol, "15m", cfg.spot_kline_limit,
                                               cutoff_ms=cutoff)),
    ])
    cs = g1["klines_15m"][0] or []
    htf = g1["klines_4h"][0] or []
    # F3 fix: gap -> bosluk-sonrasi bitisik sufiks + tani (PIT kontrolu backstop kalir).
    cs, _g15 = _gapsiz_sufiks(cs, cfg.interval_ms, tol_bars=cfg.fix_gap_tolerans_bar)
    if _g15:
        _API_ERRORS.append(f"{symbol} 15m: zaman boslugu — bosluk oncesi {_g15} bar atildi "
                           f"(bitisik sufiksle devam; kalan {len(cs)} bar)")
    htf, _g1h = _gapsiz_sufiks(htf, 16 * cfg.interval_ms, tol_bars=cfg.fix_gap_tolerans_bar)
    if _g1h:
        _API_ERRORS.append(f"{symbol} 4h: zaman boslugu — bosluk oncesi {_g1h} bar atildi "
                           f"(bitisik sufiksle devam; kalan {len(htf)} bar)")
    _last_closed_ms = cs[-1].close_ms if cs and cs[-1].close_ms is not None else None
    src["klines_15m"] = {"event_time": cs[-1].close_ms if cs else None,
                          "available_time": g1["klines_15m"][1], "role": "direction"}
    src["klines_4h"] = {"event_time": htf[-1].close_ms if htf else None,
                         "available_time": g1["klines_4h"][1], "role": "direction"}
    oi_series = g1["open_interest"][0] or []
    _oi_used = [x for x in oi_series if _last_closed_ms is not None and x[0] <= _last_closed_ms]
    src["open_interest"] = {"event_time": _oi_used[-1][0] if _oi_used else None,
                             "available_time": g1["open_interest"][1], "role": "direction"}
    _attach_series(cs, oi_series, "oi", max_age_ms=cfg.fix_attach_max_age_ms)
    taker_series = g1["taker_ratio"][0] or []
    _taker_used = [x for x in taker_series if _last_closed_ms is not None and x[0] <= _last_closed_ms]
    src["taker_ratio"] = {"event_time": _taker_used[-1][0] if _taker_used else None,
                           "available_time": g1["taker_ratio"][1], "role": "direction"}
    _attach_series(cs, taker_series, "taker", max_age_ms=cfg.fix_attach_max_age_ms)
    book = g1["book"][0]
    _book_bitti_ms = g1["book"][1]
    src["book"] = {"event_time": None,
                    "available_time": (book.get("fetched_ms") + _clock_ofs) if book and book.get("fetched_ms") else _book_bitti_ms,
                    "update_id": book.get("last_update_id") if book else None,
                    "role": "execution"}
    premium = g1["premium"][0]
    src["premium"] = {"event_time": premium.get("server_ms") if premium else None,
                       "available_time": (premium.get("fetched_ms") + _clock_ofs) if premium and premium.get("fetched_ms") else g1["premium"][1],
                       "role": "execution"}
    _fh_records = g1["funding_history"][0] or []
    _fh_used = [x for x in _fh_records if _last_closed_ms is not None and x[0] <= _last_closed_ms]
    fhist = [x[1] for x in _fh_used] or None
    funding = _fh_used[-1][1] if _fh_used else None
    src["funding_history"] = {"event_time": _fh_used[-1][0] if _fh_used else None,
                              "available_time": g1["funding_history"][1], "role": "direction"}
    taker = _taker_used[-1][1] if _taker_used else None  # ayni endpoint ikinci kez cekilmez
    spot = g1["spot_15m"][0] or None
    src["spot_15m"] = {"event_time": spot[-1].close_ms if spot else None,
                        "available_time": g1["spot_15m"][1], "role": "telemetry"}

    # 2. grup: last_closed'a bagli uclar + spoof 2. derinlik ornegi. Spoof sozlesmesi
    # korunur: book2, ilk book'tan en az spoof_bekle_sn SONRA orneklenir (kalan sure uyunur).
    def _spoof_book2():
        if book is None:
            return None
        # damga sunucu-cercevesinde; bekleme YEREL saatle hesaplanir (ofset geri alinir)
        _kalan = cfg.spoof_bekle_sn - max(0.0, time.time() - (_book_bitti_ms - _clock_ofs) / 1000.0)
        if _kalan > 0:
            time.sleep(_kalan)
        return fetch_book(symbol)

    g2 = _fetch_grubu([
        ("agg_trades", lambda: fetch_aggtrades(symbol, cfg.aggtrades_limit,
                                               end_time=_last_closed_ms)),
        ("long_short", lambda: fetch_ls_ratios(symbol, _last_closed_ms)),
        ("book2", _spoof_book2),
    ])
    trades = [x for x in (g2["agg_trades"][0] or [])
              if _last_closed_ms is not None and x[2] <= _last_closed_ms]
    src["agg_trades"] = {"event_time": trades[-1][2] if trades else None,
                          "available_time": g2["agg_trades"][1], "role": "direction"}
    of = compute_orderflow(trades, cfg)
    ls_top, ls_global, ls_top_ms, ls_global_ms = (g2["long_short"][0]
                                                  or (None, None, None, None))
    src["long_short"] = {"event_time": max((x for x in (ls_top_ms, ls_global_ms) if x is not None),
                                             default=None),
                                "available_time": g2["long_short"][1], "role": "direction"}
    book2 = g2["book2"][0]
    stale = False
    _live_server_ms = None
    _live_fetched_ms = None
    _live_price = None
    if premium:
        _live_fetched_ms = premium.get("fetched_ms")
        try:
            _live_price = float(premium.get("mark", 0.0)) or None
        except Exception:
            _live_price = None
        try:
            _live_server_ms = int(premium.get("server_ms", 0)) or None
        except Exception:
            _live_server_ms = None
    if cs and cs[-1].close_ms is not None:
        now = _live_server_ms if _live_server_ms is not None else _server_now()
        if now is not None:
            stale = (now - cs[-1].close_ms) > 2.0 * 900_000
    # F12 fix: tahmin zamani SUNUCU-cipali (yerel saat + olculen offset). Kayik cihaz
    # saati latency kapisini yanlis tetikleyip motoru sessizce surekli-BEKLE'ye dusurmez.
    predicted_at_ms = int(time.time() * 1000) + _clock_ofs
    if abs(_clock_ofs) > 5000:
        _API_ERRORS.append(f"{symbol}: cihaz-saat sapmasi {_clock_ofs:+d}ms olculdu; "
                           f"tahmin zamani sunucu-cipali duzeltildi")
    _event_times = [_last_closed_ms]
    for _meta in src.values():
        _et = _meta.get("event_time") if isinstance(_meta, dict) else None
        if isinstance(_et, (int, float)) and 1_000_000_000_000 <= _et <= predicted_at_ms:
            _event_times.append(int(_et))
    _watermark = max((x for x in _event_times if x is not None), default=_last_closed_ms)
    # Bug 11 (telemetri; KARAR KAPISI DEGIL): canli 15m snapshot icin sure/gap yeterliligi.
    # Esik motorun ihtiyacina gore (min_train+horizon bar) turetilir; 730-gun OOS esigi DEGIL.
    try:
        _need_bars = cfg.min_train + cfg.horizon + 5
        _need_days = (_need_bars * cfg.interval_ms) / (1000 * 60 * 60 * 24)
        _da = assess_data_sufficiency(cs, cfg.interval_ms, min_days=_need_days,
                                      min_folds=1, max_gap_ratio=0.05)
        if not _da.is_sufficient:
            _API_ERRORS.append(f"{symbol}: veri-yeterlilik [{_da.status}] {_da.message} "
                               f"(telemetri; karar kapisi degil)")
    except Exception as _exc:
        _API_ERRORS.append(f"{symbol}: veri-yeterlilik olcumu hata: {str(_exc)[:60]}")
    return Snapshot(symbol=symbol, candles=cs, htf=htf, orderflow=of, book=book,
                    funding=funding, funding_hist=fhist, taker_ratio=taker,
                    spot=spot, premium=premium, ls_top=ls_top, ls_global=ls_global,
                    book2=book2, live_price=_live_price, live_server_ms=_live_server_ms,
                    live_fetched_ms=_live_fetched_ms,
                    last_closed_ms=_last_closed_ms, stale=stale,
                    predicted_at_ms=predicted_at_ms,
                    data_watermark_ms=_watermark,
                    source_times=src,
                    source_errors=list(_API_ERRORS[err0:]))


# ════════════════════════════════════════════════════════════════════════════
# SINYAL LOG + WALK-FORWARD (expired-fix + geri-besleme)
# ════════════════════════════════════════════════════════════════════════════
_KALICI_KLASOR = None


def _kalici_klasor():
    """YON9-EK (denetci R8): env yokken store yollari CWD'ye goreliydi -> elle kosum ile
    oto kosum FARKLI dosyalara yazip iki yarim kalibrasyon olusturuyordu. Artik: once
    telefon Download adaylari (yazilabilirse), yoksa SCRIPT klasoru — cwd'den bagimsiz.
    Env degiskenleri (YON_PANEL_LOG vb.) her zaman oncelikli kalir."""
    global _KALICI_KLASOR
    if _KALICI_KLASOR is not None:
        return _KALICI_KLASOR
    adaylar = ["/storage/emulated/0/Download", "/sdcard/Download",
               os.path.expanduser("~/Download")]
    for k in adaylar:
        try:
            if not os.path.isdir(k):
                continue
            t = os.path.join(k, ".yon9_yaz_testi")
            with open(t, "w") as f:
                f.write("x")
            os.remove(t)
            _KALICI_KLASOR = k
            return k
        except Exception:
            continue
    try:
        _KALICI_KLASOR = os.path.dirname(os.path.abspath(__file__)) or os.getcwd()
    except Exception:
        _KALICI_KLASOR = os.getcwd()
    return _KALICI_KLASOR


def _log_path():
    p = os.environ.get("YON_PANEL_LOG")
    return p if p else os.path.join(_kalici_klasor(), "yon_signals.jsonl")


def _ledger_path() -> str:
    p = os.environ.get("FABLE6_LEDGER")
    return p if p else os.path.join(_kalici_klasor(), "fable6_forward_ledger.jsonl")


_LEDGER_READ_ERROR: Optional[str] = None


def _ledger_lock(f, exclusive: bool) -> None:
    """Linux/Android process lock. F10: kilit RUNTIME'da desteklenmiyorsa (Android/FUSE'de
    flock [Errno 38] ENOSYS) eskiden HATA firlatip ledger'i tamamen kapatiyordu -> hicbir
    tahmin kaydedilemiyordu. Artik desteklenmeyen-cagri hatasinda bir kez uyarir ve
    kilitsiz DEVAM eder (tek-surec telefonda guvenli; append-only hash-zinciri okuma-
    tarafinda zaten dogrulanir). Baska OSError'lar (or. gercek IO hatasi) yine yukselir."""
    if not _FLOCK_OK or _fcntl is None:
        return
    try:
        _fcntl.flock(f.fileno(), _fcntl.LOCK_EX if exclusive else _fcntl.LOCK_SH)
    except OSError as exc:
        if getattr(exc, "errno", None) in _UNSUPPORTED_ERRNOS:
            globals()["_FLOCK_OK"] = False
            _warn_once("ledger_flock", "ledger flock desteklenmiyor (%s); surec-kilidi "
                       "ATLANIR, append-only hash-zinciri korunur." % exc)
            return
        raise OSError("process-safe ledger kilidi kurulamadi") from exc


def _parse_ledger_handle(f) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    f.seek(0)
    for ln, line in enumerate(f, 1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError(f"satir {ln} dict degil")
        rows.append(obj)
    return rows


def _ledger_rows() -> List[Dict[str, Any]]:
    global _LEDGER_READ_ERROR
    p = _ledger_path()
    if not os.path.exists(p):
        _LEDGER_READ_ERROR = None
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            _ledger_lock(f, exclusive=False)
            rows = _parse_ledger_handle(f)
        _LEDGER_READ_ERROR = None
        return rows
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _LEDGER_READ_ERROR = str(exc)
        sys.stderr.write(f"[DEFTER-UYARI] ledger okunamadi: {_LEDGER_READ_ERROR}\n")
        return []


def verify_forward_ledger(rows: Optional[List[Dict[str, Any]]] = None) -> Tuple[bool, str]:
    if rows is None:
        rows = _ledger_rows()
        if _LEDGER_READ_ERROR is not None:
            return False, "ledger parse/okuma hatasi: " + _LEDGER_READ_ERROR
    prev = "GENESIS"
    for i, row in enumerate(rows, 1):
        body = {k: v for k, v in row.items() if k != "event_hash"}
        if row.get("prev_hash") != prev:
            return False, f"satir {i}: prev_hash zinciri kirik"
        got = _sha256_obj(body)
        if row.get("event_hash") != got:
            return False, f"satir {i}: event_hash uyusmuyor"
        prev = got
    return True, f"{len(rows)} event"


def _append_ledger_event(event: Dict[str, Any]) -> Optional[str]:
    """Append-only hash zinciri. Var olan baytlar hicbir zaman yeniden yazilmaz."""
    try:
        p = _ledger_path()
        os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
        with open(p, "a+", encoding="utf-8") as f:
            _ledger_lock(f, exclusive=True)
            rows = _parse_ledger_handle(f)
            ok, why = verify_forward_ledger(rows)
            if not ok:
                sys.stderr.write(f"[DEFTER-UYARI] yazma reddedildi: {why}\n")
                return None
            # Dedupe kontrolu da AYNI process lock icinde; TOCTOU yok.
            if event.get("event_type") == "PREDICTION" and event.get("prediction_key"):
                # Bir model nesli ayni sembol/target_end icin yalniz ILK tahmini
                # kilitler. Watermark/yeniden-kosum farki sonucu gorup tekrar tahmin
                # yazmaya veya ana kohort N'sini sisirmeye izin vermez.
                hit = next((r.get("event_hash") for r in rows
                            if r.get("event_type") == "PREDICTION"
                            and r.get("protocol_id") == event.get("protocol_id")
                            and r.get("symbol") == event.get("symbol")
                            and r.get("target_end") == event.get("target_end")
                            and r.get("model_hash") == event.get("model_hash")), None)
                if hit:
                    return hit
                hit = next((r.get("event_hash") for r in rows
                            if r.get("event_type") == "PREDICTION" and
                            r.get("prediction_key") == event.get("prediction_key")), None)
                if hit:
                    return hit
            if event.get("event_type") == "OUTCOME" and event.get("prediction_event"):
                hit = next((r.get("event_hash") for r in rows
                            if r.get("event_type") == "OUTCOME" and
                            r.get("prediction_event") == event.get("prediction_event")), None)
                if hit:
                    return hit
            body = dict(event)
            body["schema"] = "fable6-forward-ledger-v1"
            body["prev_hash"] = rows[-1]["event_hash"] if rows else "GENESIS"
            body["written_at_ms"] = int(time.time() * 1000)
            body["event_hash"] = _sha256_obj(body)
            f.seek(0, os.SEEK_END)
            f.write(_stable_json(body) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return body["event_hash"]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"[DEFTER-UYARI] append basarisiz: {exc}\n")
        return None


def record_forward_prediction(symbol: str, snap: Snapshot, d: Decision,
                              cfg: Config) -> Optional[str]:
    if d.mode != "LIVE" or d.predicted_at_ms is None or d.target_end_ms is None:
        return None
    key = _sha256_obj({"protocol": cfg.protocol_id, "symbol": symbol,
                       "target_end": d.target_end_ms, "watermark": d.data_watermark_ms,
                       "model": d.model_hash})
    atr_now = atr_series(snap.candles, cfg.atr_period)[-1] if snap.candles else 0.0
    price0 = snap.candles[-1].close if snap.candles else None
    fc = d.fc if isinstance(d.fc, dict) else {}
    pit_errors = snapshot_pit_violations(snap, cfg, d.predicted_at_ms)
    origin_latency = ((d.predicted_at_ms - snap.last_closed_ms)
                      if d.predicted_at_ms is not None and snap.last_closed_ms is not None
                      else None)
    protocol_errors = list(pit_errors)
    if origin_latency is None or origin_latency < 0 or origin_latency > cfg.ledger_max_latency_ms:
        protocol_errors.append("origin-to-prediction latency protokol disi")
    return _append_ledger_event({
        "event_type": "PREDICTION", "prediction_key": key,
        "protocol_id": cfg.protocol_id, "symbol": symbol,
        "predicted_at": d.predicted_at_ms, "target_end": d.target_end_ms,
        "data_watermark": d.data_watermark_ms, "source_times": snap.source_times,
        "prediction_latency_ms": ((d.predicted_at_ms - d.data_watermark_ms)
                                  if d.data_watermark_ms is not None else None),
        "origin_latency_ms": origin_latency,
        "protocol_valid": not protocol_errors,
        "protocol_errors": protocol_errors,
        "diagnostics": list(d.diagnostics),
        "p_down": d.p_down, "p_flat": d.p_flat, "p_up": d.p_up,
        "model_class": argmax_class((d.p_down, d.p_flat, d.p_up), cfg.tie_eps_rel),
        "trade_decision": d.karar, "decision": d.karar, "gate_code": d.gate_code,
        "entry": d.entry, "target": d.target, "stop": d.stop,
        "interval_low": fc.get("q10"), "median": fc.get("q50"),
        "interval_high": fc.get("q90"),
        "price0": price0, "neutral_delta_abs": cfg.label_neutral_atr * atr_now,
        "model_hash": d.model_hash, "code_hash": d.code_hash,
        "feature_hash": d.feature_hash,
        "config_hash": config_hash(cfg)})


def resolve_forward_predictions(symbol: str, candles: List[Candle], cfg: Config) -> int:
    """Tam target_end mumu geldikten sonra ayri OUTCOME eventi ekler."""
    rows = _ledger_rows()
    by_time = {c.close_ms: c for c in candles if c.close_ms is not None}
    resolved = {r.get("prediction_event") for r in rows if r.get("event_type") == "OUTCOME"}
    n = 0
    for r in rows:
        if r.get("event_type") != "PREDICTION" or r.get("symbol") != symbol:
            continue
        ref = r.get("event_hash")
        target_end = r.get("target_end")
        if ref in resolved or target_end not in by_time:
            continue
        p0 = r.get("price0")
        if not isinstance(p0, (int, float)) or p0 <= 0:
            continue
        move = by_time[target_end].close - float(p0)
        cls = sign_eps(move, p0, cfg.tie_eps_rel,
                       float(r.get("neutral_delta_abs", 0.0) or 0.0))
        if _append_ledger_event({"event_type": "OUTCOME", "prediction_event": ref,
                                 "prediction_key": r.get("prediction_key"),
                                 "protocol_id": r.get("protocol_id"), "symbol": symbol,
                                 "target_end": target_end, "outcome_class": cls,
                                 "outcome_price": by_time[target_end].close}) is not None:
            n += 1
    return n


def forward_ledger_metrics(symbol: str, cfg: Optional[Config] = None) -> Dict[str, Any]:
    """Kanonik append-only PREDICTION/OUTCOME ciftlerinden proper ve secici skorlar.

    Mutable eski forecast dosyasi bu olcume girmez. Esit olasilik tepesinde sinif
    zorlanmaz (FLAT); LONG/SHORT secici isabeti ayrica raporlanir.
    """
    cfg = cfg or Config()
    rows = _ledger_rows()
    ok, why = verify_forward_ledger(rows) if _LEDGER_READ_ERROR is None else (False, _LEDGER_READ_ERROR)
    base: Dict[str, Any] = {
        "valid": ok, "reason": why, "generation": model_hash(cfg),
        "n_operational": 0, "n": 0, "hit": 0, "acc": None,
        "selective_n": 0, "selective_hit": 0, "selective_acc": None,
        "accuracy_ci": (None, None), "selective_accuracy_ci": (None, None),
        "coverage": 0.0, "brier": None, "logloss": None,
        "balanced_accuracy": None, "band_n": 0, "band_hit": 0, "band": None,
        "confusion": {str(t): {str(p): 0 for p in CLASSES} for t in CLASSES},
    }
    if not ok:
        return base
    current_generation = model_hash(cfg)
    eligible_preds = [r for r in rows
                      if r.get("event_type") == "PREDICTION" and r.get("symbol") == symbol
                      and r.get("protocol_id") == cfg.protocol_id
                      and r.get("model_hash") == current_generation
                      and r.get("protocol_valid") is True]
    unique_targets: Dict[Tuple[Any, Any], Dict[str, Any]] = {}
    for r in eligible_preds:  # ledger sirasi: ilk kilitli tahmin kazanir
        unique_targets.setdefault((r.get("target_end"), r.get("model_hash")), r)
    all_preds = {r.get("event_hash"): r for r in unique_targets.values()}
    outs = {r.get("prediction_event"): r for r in rows
            if r.get("event_type") == "OUTCOME" and r.get("symbol") == symbol
            and r.get("protocol_id") == cfg.protocol_id}
    briers: List[float] = []
    losses: List[float] = []
    hit_seq: List[float] = []
    selective_hit_seq: List[float] = []
    class_hit = {c: [0, 0] for c in CLASSES}
    # Ana metrik sabit UTC fazli, 4s aralikli kohorttur. 15m operasyonel kayitlar
    # ledger'da kalir fakat 15/16 ortusen hedeflerle etkin N'yi sisirmez.
    for ref, p in sorted(all_preds.items(), key=lambda kv: kv[1].get("target_end", 0)):
        o = outs.get(ref)
        truth = o.get("outcome_class") if o else None
        if truth not in CLASSES:
            continue
        base["n_operational"] += 1
        te = p.get("target_end")
        if (not isinstance(te, (int, float)) or
                (int(te) + 1) % (cfg.horizon * cfg.interval_ms) != 0):
            continue
        try:
            ps = normalize_probs(float(p["p_down"]), float(p["p_flat"]), float(p["p_up"]))
        except (KeyError, TypeError, ValueError):
            base["valid"] = False
            base["reason"] = "ledger olasilik alani gecersiz"
            return base
        pred = argmax_class(ps, cfg.tie_eps_rel)
        base["n"] += 1
        hit = int(pred == truth)
        hit_seq.append(hit)
        base["hit"] += hit
        class_hit[truth][1] += 1
        class_hit[truth][0] += hit
        base["confusion"][str(truth)][str(pred)] += 1
        briers.append(sum((ps[k] - (1.0 if truth == CLASSES[k] else 0.0)) ** 2
                          for k in range(3)))
        losses.append(-math.log(max(1e-12, ps[CLASSES.index(truth)])))
        dec = p.get("decision")
        if dec in ("LONG", "SHORT"):
            dp = 1 if dec == "LONG" else -1
            base["selective_n"] += 1
            dh = int(dp == truth)
            base["selective_hit"] += dh
            selective_hit_seq.append(dh)
        lo, hi, px = p.get("interval_low"), p.get("interval_high"), o.get("outcome_price")
        if all(isinstance(v, (int, float)) for v in (lo, hi, px)) and lo <= hi:
            base["band_n"] += 1
            base["band_hit"] += int(lo <= px <= hi)
    n = base["n"]
    if n:
        base["acc"] = base["hit"] / n
        base["coverage"] = base["selective_n"] / n
        base["brier"] = mean(briers)
        base["logloss"] = mean(losses)
        recalls = [w / nn for w, nn in class_hit.values() if nn]
        base["balanced_accuracy"] = mean(recalls) if recalls else None
        base["accuracy_ci"] = _moving_block_ci(hit_seq, cfg.bootstrap_reps,
                                                seed=symbol + "-ledger-all")
    if base["selective_n"]:
        base["selective_acc"] = base["selective_hit"] / base["selective_n"]
        base["selective_accuracy_ci"] = _moving_block_ci(
            selective_hit_seq, cfg.bootstrap_reps,
            seed=symbol + "-ledger-selective")
    if base["band_n"]:
        base["band"] = base["band_hit"] / base["band_n"]
    return base


_SIGNALS_READ_FAIL = False   # son _load_signals G/C-duzeyinde basarisiz oldu mu (bozuk bayt/kilit)
# PERF FIX (denetim): kalibrasyon fonksiyonlari (kayma/monokultur/ev/rev/calib/gozlem/
# scen_cell/micro_rate x27...) her kosuda ayni JSONL'i ~30 kez bastan okuyordu (telefonda
# G/C yuku). mtime_ns+size imzasi degismediyse son ayristirilan liste (sig kopya) doner;
# _save_signals her yazimda imzayi gecersiz kilar. Davranis birebir ayni, yalniz hiz.
_SIG_CACHE = {"yol": None, "imza": None, "rows": None}


def _load_signals():
    global _SIGNALS_READ_FAIL
    p = _log_path()
    out = []
    try:
        if not os.path.exists(p):
            _SIGNALS_READ_FAIL = False
            _SIG_CACHE.update(yol=p, imza=None, rows=None)
            return out
        _st = os.stat(p)
        _imza = (_st.st_mtime_ns, _st.st_size)
        if _SIG_CACHE["yol"] == p and _SIG_CACHE["imza"] == _imza and _SIG_CACHE["rows"] is not None:
            _SIGNALS_READ_FAIL = False
            return list(_SIG_CACHE["rows"])
        with open(p, "r", encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        obj = json.loads(line)
                        if not isinstance(obj, dict):
                            raise ValueError("JSON nesnesi dict degil")
                        out.append(obj)
                    except (json.JSONDecodeError, TypeError, ValueError) as exc:
                        raise ValueError(f"sinyal logu satir {ln} bozuk: {exc}") from exc
    except Exception as e:
        # bozuk/kilitli log 'gecmis yok' gibi gorunup TUM kalibrasyonu sessizce sifirlar -> gorunur yap
        # + bayrak dik: record_and_resolve bu kosuda dosyayi EZMESIN (denetci R4a: tek bozuk bayt
        # 50 cozulmus sinyali kalici siliyordu).
        sys.stderr.write(f"[UYARI] sinyal logu okunamadi ({_log_path()}): {str(e)[:100]}\n")
        _SIGNALS_READ_FAIL = True
        _SIG_CACHE.update(yol=p, imza=None, rows=None)
        return []
    _SIGNALS_READ_FAIL = False
    _SIG_CACHE.update(yol=p, imza=_imza, rows=list(out))
    return out


def _save_signals(rows, cfg):
    """ATOMIK yazim (tmp+os.replace; plan store ile ayni koruma) + KORUMA: okuma bu kosuda
    basarisiz olduysa mevcut dosya EZILMEZ (gecmis > tek kosunun yeni kaydi). Denetci R4b:
    eski yol yazim ortasinda kesilince dosyayi yarim birakip istisnayi sessiz yutuyordu."""
    if _SIGNALS_READ_FAIL:
        sys.stderr.write("[UYARI] sinyal logu bu kosuda OKUNAMADIGI icin ustune YAZILMADI "
                         "(gecmis korunuyor; bu kosunun kaydi atlandi)\n")
        return None
    try:
        yol = _log_path()
        receipt = _atomic_commit_jsonl(yol, rows[-cfg.signal_log_max:])
        _SIG_CACHE.update(yol=None, imza=None, rows=None)   # yazim -> onbellek gecersiz
        return receipt
    except (StoreError, OSError) as e:
        sys.stderr.write(f"[UYARI] sinyal logu yazilamadi: {str(e)[:80]}\n")
        return None


def realized_shrink(symbol: str, cfg: Config) -> float:
    """Gecmis GERCEK yon-isabeti dusukse guveni kis (walk-forward geri-besleme, Beklenti #8).
    CANLI-ONLY: gecmis log HICBIR gosterilen sayiyi oynatmaz -> 1.0 (etkisiz).
    Iddia-kod tutarliligi: 'gecikmis veri karari da gosterilen orani da yonetmez' sozu
    ancak boyle birebir dogru olur; gecmis isabet ayri satirlarda TELEMETRI olarak kalir."""
    if getattr(cfg, 'canli_only', False):
        return 1.0
    rows = [r for r in _load_signals() if r.get("symbol") == symbol]
    res = [r for r in rows if r.get("outcome") in ("HIT", "STOP", "DIR_OK", "DIR_BAD")]
    if len(res) < cfg.min_track_resolved:
        return 1.0
    good = sum(1 for r in res if r.get("outcome") in ("HIT", "DIR_OK"))
    rate = good / len(res)
    if rate >= 0.55:
        return 1.0
    if rate >= 0.5:
        return 0.9
    return max(0.6, (rate / 0.5) * 0.8)


# ════════════════════════════════════════════════════════════════════════════
# ADAPTIF ONLINE OZ-KALIBRASYON — 5 KUME
# Her fonksiyon SYMBOL'e gore filtreler; yetersiz cozulen ornek -> SABIT Config sabiti +
# durust etiket. Kucuk-ornek shrinkage; NO-LOOKAHEAD (yalniz cozulmus log satirlari).
# ════════════════════════════════════════════════════════════════════════════
def ev_gate_calib(symbol, snap, st, cfg):
    """CLUSTER 1 — EV kapisi. Gecmis cozulen sinyallerden ev_min_atr + dir_edge_min ogren."""
    if getattr(cfg, 'canli_only', False):
        # CANLI-ONLY: gecmis kalibrasyon karara GIRMEZ -> sabit canli esik.
        return (cfg.ev_min_atr, cfg.dir_edge_min, 'CANLI (kalibrasyon karara girmez)')
    rows = [r for r in _load_signals() if r.get('symbol') == symbol]
    res = [r for r in rows if r.get('outcome') in ('HIT', 'STOP', 'DIR_OK', 'DIR_BAD')]
    n_res = len(res)
    EV_CALIB_MIN = cfg.ev_calib_min
    MC_MIN = 8
    K = cfg.ev_calib_k
    if st.atr <= 0 or n_res < EV_CALIB_MIN:
        return (cfg.ev_min_atr, cfg.dir_edge_min,
                'kalibre DEGIL (n=%d<%d)' % (n_res, EV_CALIB_MIN))
    s = n_res / float(n_res + K)
    good = sum(1 for r in res if r.get('outcome') in ('HIT', 'DIR_OK'))
    w_real = good / n_res
    shortfall = _clip(0.5 - w_real, 0, 0.5)
    surplus = _clip(w_real - 0.55, 0, 0.20)
    ev_mult = 1.0 + s * (4.0 * shortfall - 1.5 * surplus)
    ev_eff = _clip(cfg.ev_min_atr * ev_mult, 0.5 * cfg.ev_min_atr, 3.0 * cfg.ev_min_atr)
    barrier = [r for r in res if r.get('outcome') in ('HIT', 'STOP')
               and isinstance(r.get('p_target'), (int, float))]
    dir_eff = cfg.dir_edge_min
    if len(barrier) >= MC_MIN:
        h_real = sum(1 for r in barrier if r.get('outcome') == 'HIT') / len(barrier)
        mc_mean = mean([float(r['p_target']) for r in barrier])
        sb = len(barrier) / float(len(barrier) + K)
        cal_gap = _clip(mc_mean - h_real, 0, 0.5)
        over = _clip(h_real - mc_mean, 0, 0.10)
        dir_eff = _clip(cfg.dir_edge_min + sb * (cal_gap - 0.5 * over),
                        0.6 * cfg.dir_edge_min, 3.0 * cfg.dir_edge_min)
    # Canli maliyet-BELIRSIZLIGI (yalniz YUKARI ayarlar): funding dagiliminin oynakligi.
    # NOT: maliyetin KENDISI artik esige eklenmez — EV zaten maliyet-sonrasi (build_scenario);
    # eski '2*cost_now' tabani cifte-sayimdi ve kapiyi kilitliyordu. Yalniz funding-oynakligi
    # (cost_disp) guvenlik marji olarak kalir: funding cok dalgalanan sembolde esik yukselir.
    price = st.price
    fh = snap.funding_hist or []
    fund_atr = [abs(f) * price * 0.5 / st.atr for f in fh[-24:]]
    cost_disp = std(fund_atr) if len(fund_atr) >= 2 else 0.0
    ev_eff = max(ev_eff, cfg.ev_min_atr * 0.5 + cost_disp)
    label = 'kalibre (isabet ~%d%%, n=%d)' % (round(100 * w_real), n_res)
    return (ev_eff, dir_eff, label)


# ─── CLUSTER 2 — Uzlasmazlik (SIDECAR dosya; sinyal logu DEGIL) ───────────────
def _disagree_store_path():
    p = os.environ.get('YON_DISAGREE_LOG')
    return p if p else os.path.join(_kalici_klasor(), 'yon_disagree.json')


def _load_disagree(symbol):
    p = _disagree_store_path()
    try:
        if not os.path.exists(p):
            return []
        with open(p, 'r', encoding='utf-8') as f:
            store = json.load(f)
        ring = store.get(symbol, []) if isinstance(store, dict) else []
        out = []
        bad = 0
        for item in ring:
            try:
                out.append((int(item[0]), float(item[1])))
            except Exception:
                bad += 1
        if bad:
            sys.stderr.write(f"[UYARI] uzlasmazlik store: {bad} bozuk satir atlandi\n")
        out.sort(key=lambda t: t[0])
        return out
    except Exception as e:
        # gorunur uyari (denetci R3 kardesi): bozuk store 'gecmis yok' gibi gorunmesin
        sys.stderr.write(f"[UYARI] uzlasmazlik store okunamadi ({p}): {str(e)[:80]}\n")
        return []


def _persist_disagree(symbol, bar_ms, disagree, block_p, cfg):
    opinion = [v for v in (block_p or {}).values() if abs(v - 0.5) > 0.02]
    if bar_ms is None or len(opinion) < 2:
        return
    p = _disagree_store_path()
    bozuk = False
    try:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                store = json.load(f)
            if not isinstance(store, dict):
                store = {}
                bozuk = True
        else:
            store = {}
    except Exception as e:
        # BOZUK-DOSYA KORUMASI (denetci R3): sessiz {} diger sembollerin uzlasmazlik
        # halkalarini bir sonraki yazimda uyarisiz siliyordu -> gorunur uyari + .bozuk yedegi.
        sys.stderr.write(f"[UYARI] uzlasmazlik store okunamadi/bozuk ({p}): {str(e)[:80]}\n")
        store = {}
        bozuk = True
    ring = store.get(symbol, [])
    if any(int(m) == int(bar_ms) for m, _ in ring):
        return
    ring.append([int(bar_ms), round(float(disagree), 4)])
    store[symbol] = ring[-cfg.disagree_ring_max:]
    try:
        if bozuk and os.path.exists(p):
            try:
                os.replace(p, p + ".bozuk")
                sys.stderr.write(f"[UYARI] bozuk uzlasmazlik store yedeklendi: {p}.bozuk\n")
            except Exception as exc:
                raise OSError("bozuk uzlasmazlik store yedeklenemedi; yazma reddedildi") from exc
        tmp = p + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(store, f)
        os.replace(tmp, p)   # ATOMIK: yarim JSON kendi kendini besleyen silme dongusu yaratmasin
    except Exception as exc:
        sys.stderr.write("[UYARI] uzlasmazlik store yazilamadi: " + str(exc)[:120] + "\n")


def _quantile(xs, q):
    """F7 fix: dogrusal-interpolasyonlu quantile (eski nearest-rank + banker's-round,
    kucuk n'de yarim-adim sicramali sapma uretiyordu; sweep pad ve rejim kesitleri
    kenarda yanlis basamaga oturuyordu). Bos liste -> 0.0 (eski sozlesme korunur)."""
    if not xs:
        return 0.0
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    pos = _clip(float(q), 0.0, 1.0) * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] * (1.0 - frac) + s[hi] * frac


def adaptive_disagree_max(symbol, cfg, regime):
    if getattr(cfg, 'canli_only', False):
        return (cfg.disagree_max, 'CANLI (kalibrasyon karara girmez)', 0)
    vals = [v for _ms, v in _load_disagree(symbol)][-cfg.disagree_window:]
    n = len(vals)
    if n < cfg.disagree_adapt_min:
        return (cfg.disagree_max, 'kalibre DEGIL', n)
    base = _quantile(vals, cfg.disagree_quantile)
    if std(vals) <= 1e-6:
        base = cfg.disagree_max
    lam = n / (n + cfg.disagree_shrink_k)
    thr = lam * base + (1 - lam) * cfg.disagree_max
    rf = {'EXTREME': 1.30, 'EXPANDING': 1.15, 'COMPRESSED': 0.90, 'LOW': 0.90}.get(regime, 1.0)
    thr *= rf
    thr = _clip(thr, cfg.disagree_max * 0.6, cfg.disagree_max * 2.0)
    return (thr, 'kalibre q%d n=%d' % (int(cfg.disagree_quantile * 100), n), n)


# ─── CLUSTER 3 — Donus/flip/veto ─────────────────────────────────────────────
def _rev_against(r):
    rs = r.get('rev_sign')
    if rs in (None, 0):
        return False
    ss = 1 if r.get('side') == 'LONG' else (-1 if r.get('side') == 'SHORT' else None)
    return ss is not None and rs != ss


def _wilson_lower(k, n, z=1.64):
    """Wilson tek-tarafli ALT guven siniri (~%95). Kucuk n -> genis aralik -> alt sinir dusuk;
    boylece 'ilk esigi asan bin'i secmekten dogan winner's curse (secim-biasi) notrlenir."""
    if n <= 0:
        return 0.0
    p = k / n
    d = 1.0 + z * z / n
    c = p + z * z / (2.0 * n)
    m = z * ((p * (1.0 - p) / n + z * z / (4.0 * n * n)) ** 0.5)
    return (c - m) / d


# ════════════════════════════════════════════════════════════════════════════
# F11 (YÖNTEM.txt tamiri) — BEKLENTI TELEMETRI KATMANI (saf math; karara DOKUNMAZ)
# YÖNTEM tezi: teshis metrigi yon-isabeti p DEGIL, maliyet-sonrasi beklenti E_net,
# risk-normalize Sharpe ve Kelly f*'tir. Bu fonksiyonlarin HICBIRI decide()/EV/kapi/
# boyutlandirmaya girmez — yalniz kart/rapor uretir (karar-degismezligi korunur).
# ════════════════════════════════════════════════════════════════════════════
def _wilson_ci(k, n, z=1.96):
    """Iki-tarafli Wilson skor araligi (k basari / n deneme). Doner (lo, hi) ∈ [0,1].
    Nokta-tahmin asla yalniz gosterilmesin diye (YÖNTEM §4: SE(p_C)≈√(p_C(1−p_C)/N_C))."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half = (z * math.sqrt(max(0.0, p * (1.0 - p) / n + z2 / (4.0 * n * n)))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def expectancy_kelly(p_target, p_stop, reward_abs, risk_abs, cost_abs=0.0):
    """YÖNTEM §1.1/§1.4: maliyet-sonrasi beklenti (R-birimi) + Kelly f*. SALT TESHIS.
    b=RR=odul/risk; c=maliyet/risk (R-birimi); E[R]=p·b−(1−p) (ikili varsayim, ara/flat
    sonuc ~0R sayilir -> p_stop ile carpilir); E_net=p·b−p_stop−c; basabas p*_c=(1+c)/(1+b);
    Kelly pay f*=E_net/b (=E/b, sign(f*)=sign(E)); ceyrek-Kelly kestirim-hatasi payi.
    f*≤0 -> 'girme'. Doner None (risk<=0) veya dict. Bu fonksiyon boyutlandirmaya BAGLANMAZ.
    NOT: ikili ozel durumda (p_stop=1−p, c=0) YÖNTEM §1.2 capalarini birebir uretir:
    (p=.40,b=3)->+0.60R, (p=.58,b=.5)->−0.13R (selftest [YONTEM] kaniti)."""
    if risk_abs is None or risk_abs <= 0 or reward_abs is None:
        return None
    b = max(0.0, reward_abs) / risk_abs
    c = (max(0.0, cost_abs) / risk_abs) if cost_abs else 0.0
    p = _clip(float(p_target), 0.0, 1.0)
    ps = _clip(float(p_stop), 0.0, 1.0)
    e_r = p * b - ps                    # maliyetsiz beklenti (R); ara-sonuc 0R
    e_net = e_r - c                     # maliyet-sonrasi (R)
    p_star = 1.0 / (1.0 + b)            # b>=0 garantili (risk>0, reward>=0) -> payda >=1
    p_star_c = (1.0 + c) / (1.0 + b)
    f_star = (e_net / b) if b > 1e-12 else 0.0
    return {"b": b, "c": c, "p": p, "p_stop": ps, "E_R": e_r, "E_net": e_net,
            "p_star": p_star, "p_star_c": p_star_c, "f_star": f_star,
            "gecilir": e_net > 0.0}


def realized_expectancy(net_rs):
    """Gerceklesmis (maliyet-sonrasi) net_r serisinden TANIMLAYICI E_net + Sharpe + net-win
    Wilson CI. YÖNTEM §1.4/§4. DSR DEGIL: deflate edilmez, trial registry yok -> salt
    telemetri (dsr_report N/A sozlesmesi korunur). Doner None (bos) veya dict."""
    net_rs = [float(r) for r in net_rs if isinstance(r, (int, float))]
    n = len(net_rs)
    if n == 0:
        return None
    m = mean(net_rs)
    s = std(net_rs)
    sharpe = (m / s) if s > 1e-12 else None          # islem-basi tanimlayici Sharpe
    wins = sum(1 for r in net_rs if r > 0)
    lo, hi = _wilson_ci(wins, n)
    return {"E_net": m, "sharpe": sharpe, "std": s, "n": n,
            "win": wins, "win_rate": wins / n, "win_lo": lo, "win_hi": hi}


def ece_reliability(pairs, bins=10):
    """(guven, dogru01) ciftlerinden Expected Calibration Error + reliability binleri.
    ECE = Σ (n_b/N)·|acc_b − conf_b|  (YÖNTEM §2.3/KT-7). Brier ledger'da zaten var; bu
    onun eksik tamamlayicisidir. Doner None (bos) veya {ece, n, bins:[(lo,hi,n_b,conf,acc)]}."""
    pr = [(float(c), 1.0 if d else 0.0) for c, d in pairs
          if isinstance(c, (int, float))]
    n = len(pr)
    if n == 0 or bins < 1:
        return None
    edges = [i / bins for i in range(bins + 1)]
    buckets = [[] for _ in range(bins)]
    for conf, corr in pr:
        bi = min(bins - 1, max(0, int(conf * bins)))
        buckets[bi].append((conf, corr))
    ece = 0.0
    rows = []
    for i in range(bins):
        b = buckets[i]
        if not b:
            rows.append((edges[i], edges[i + 1], 0, None, None))
            continue
        nb = len(b)
        conf_b = mean([c for c, _ in b])
        acc_b = mean([d for _, d in b])
        ece += (nb / n) * abs(acc_b - conf_b)
        rows.append((edges[i], edges[i + 1], nb, conf_b, acc_b))
    return {"ece": ece, "n": n, "bins": rows}


def _yontem_beklenti_satiri(d, cfg, prefix="   "):
    """F11 (YÖNTEM §1.1/§1.4): karar kartina R-birimi E_net + Kelly f* teshis satiri.
    SALT GOSTERIM — hicbir kapiya/boyutlandirmaya baglanmaz (karar-degismezligi). d
    LONG/SHORT ve entry/target/stop dolu degilse None (satir basilmaz)."""
    if not getattr(cfg, "yontem_expectancy_enabled", True):
        return None
    if d.karar not in ("LONG", "SHORT") or not (d.entry and d.target and d.stop):
        return None
    reward = abs(d.target - d.entry)
    risk = abs(d.entry - d.stop)
    ek = expectancy_kelly(d.p_target, d.reversal_risk / 100.0, reward, risk,
                          cost_abs=getattr(d, "cost_abs", 0.0) or 0.0)
    if ek is None:
        return None
    kf = getattr(cfg, "yontem_kelly_fraction", 0.25)
    frac = kf * ek["f_star"]
    hkm = ("f*>0 -> pozitif beklenti" if ek["gecilir"]
           else "f*<=0 -> BEKLENTI NEGATIF (boyut kucult / girme)")
    return (f"{prefix}BEKLENTI (YÖNTEM; salt teshis, boyutlandirmaya baglanmaz): "
            f"E_net={ek['E_net']:+.2f}R | RR(b)={ek['b']:.2f} | maliyet c={ek['c']:.2f}R | "
            f"basabas p*_c=%{round(100 * ek['p_star_c'])} (canli p=%{round(100 * ek['p'])}) | "
            f"Kelly f*={ek['f_star']:+.2f} ({kf:.2f}f*={frac:+.2f}) -> {hkm}")


# ── F11 (YÖNTEM §2.1/§2.2/KT-5): BLOK ORTOGONALLIK TANISI ────────────────────
# Confluence yalniz bloklar BAGIMSIZ ise breadth uretir (IR≈IC·√breadth). Motor
# blok yonsel gorusunu (block_p) IZOLE bir append-only store'a yazar; buradan
# bloklar-arasi mean|Pearson| olculur. SALT TELEMETRI: log-pool agirligini
# DEGISTIRMEZ (karar-degismezligi); yuksek |corr| yalniz 'sahte-confluence riski'
# bayragi olarak gosterilir. Disagree store'a (karar-yolu) DOKUNULMAZ.
def _block_series_path():
    p = os.environ.get('YON_BLOCK_SERIES_LOG')
    return p if p else os.path.join(_kalici_klasor(), 'yon_block_series.json')


def _persist_block_series(symbol, bar_ms, block_p, cfg):
    if not getattr(cfg, "yontem_ortho_enabled", True) or bar_ms is None or not block_p:
        return
    p = _block_series_path()
    try:
        store = {}
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                store = json.load(f)
            if not isinstance(store, dict):
                store = {}
        ring = store.get(symbol, [])
        if any(item and int(item[0]) == int(bar_ms) for item in ring):
            return
        ring.append([int(bar_ms), {k: round(float(v), 4) for k, v in block_p.items()}])
        store[symbol] = ring[-getattr(cfg, "yontem_ortho_log_max", 400):]
        tmp = p + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(store, f)
        os.replace(tmp, p)   # ATOMIK
    except Exception as exc:
        sys.stderr.write("[UYARI] blok-serisi yazilamadi: " + str(exc)[:120] + "\n")


def block_orthogonality(symbol, cfg):
    """Bloklar-arasi mean|corr| — 'confluence bagimsiz mi'. Cift korelasyon YALNIZ iki
    blogun da mevcut oldugu barlarda olculur. Doner None (yetersiz) veya dict."""
    p = _block_series_path()
    try:
        if not os.path.exists(p):
            return None
        with open(p, 'r', encoding='utf-8') as f:
            store = json.load(f)
        ring = store.get(symbol, []) if isinstance(store, dict) else []
    except Exception:
        return None
    bybar = {}
    for item in ring:
        try:
            bybar[int(item[0])] = {k: float(v) for k, v in item[1].items()}
        except Exception:
            continue
    mss = sorted(bybar)
    names = sorted({k for m in mss for k in bybar[m]})
    min_n = getattr(cfg, "yontem_ortho_min_n", 20)
    hi_thr = getattr(cfg, "yontem_ortho_corr_hi", 0.5)
    corrs, hi = [], []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            xa, xb = [], []
            for m in mss:
                if names[i] in bybar[m] and names[j] in bybar[m]:
                    xa.append(bybar[m][names[i]])
                    xb.append(bybar[m][names[j]])
            if len(xa) >= min_n:
                c = _corr(xa, xb)
                if c is not None:
                    corrs.append(abs(c))
                    if abs(c) >= hi_thr:
                        hi.append((names[i], names[j], round(c, 2)))
    if not corrs:
        return {"n_bar": len(mss), "pairs": 0, "mean_abs_corr": None, "hi": []}
    return {"n_bar": len(mss), "pairs": len(corrs),
            "mean_abs_corr": mean(corrs), "hi": hi}


def reversal_calib(symbol, cfg):
    if getattr(cfg, 'canli_only', False):
        return (cfg.flip_thresh, cfg.veto_thresh, cfg.reversal_flag,
                {'n_against': 0, 'n_decisive': 0, 'flip_cal': False, 'flag_cal': False})
    rows = [r for r in _load_signals()
            if r.get('symbol') == symbol and r.get('outcome') in ('HIT', 'STOP', 'DIR_OK', 'DIR_BAD')]
    against = [r for r in rows if r.get('rev_sign') not in (None, 0)
               and r.get('rev_str') is not None and _rev_against(r)]
    n = len(against)
    flip_thr, veto_thr = cfg.flip_thresh, cfg.veto_thresh
    if n >= cfg.rev_calib_min:
        is_rev = lambda r: r.get('outcome') in ('STOP', 'DIR_BAD')
        strengths = sorted({round(r['rev_str'], 3) for r in against})

        def p_at(sv):
            # SECIM-BIASI FIX: nokta-oran yerine Wilson ALT-GUVEN SINIRI. Kucuk-orneklem bir
            # bin'i sirf sansla asamaz; gercek etki gerekir. n<bucket_min -> None (fixed prior'a duser).
            seg = [r for r in against if r['rev_str'] >= sv - 1e-9]
            if len(seg) < cfg.rev_calib_bucket_min:
                return None
            k = sum(1 for r in seg if is_rev(r))
            return _wilson_lower(k, len(seg))

        _pvals = [(sv, p_at(sv)) for sv in strengths]   # 2.tur: her esik TEK hesap (eski kod 2x cagiriyordu)
        flip_star = next((sv for sv, pv in _pvals if pv is not None and pv >= 0.50),
                         min(1.0, (max(strengths) + 0.05) if strengths else 1.0))
        veto_star = next((sv for sv, pv in _pvals if pv is not None and pv >= 0.58),
                         flip_star)
        w = n / (n + cfg.rev_calib_k)
        flip_thr = _clip(w * flip_star + (1 - w) * cfg.flip_thresh, 0.5, 1.0)
        veto_thr = _clip(w * max(veto_star, flip_star) + (1 - w) * cfg.veto_thresh, 0.5, 1.0)
        veto_thr = max(veto_thr, flip_thr)
    decisive = [r for r in rows if r.get('outcome') in ('HIT', 'STOP')]
    rev_flag = cfg.reversal_flag
    if len(decisive) >= cfg.rev_calib_min:
        stop_rate = sum(1 for r in decisive if r.get('outcome') == 'STOP') / len(decisive)
        w2 = len(decisive) / (len(decisive) + cfg.rev_calib_k)
        rev_flag = _clip(w2 * stop_rate + (1 - w2) * cfg.reversal_flag, 0.30, 0.65)
    info = {'n_against': n, 'n_decisive': len(decisive),
            'flip_cal': n >= cfg.rev_calib_min, 'flag_cal': len(decisive) >= cfg.rev_calib_min}
    return (flip_thr, veto_thr, rev_flag, info)


# ─── CLUSTER 4 — Skor / olasilik kalibrasyonu ────────────────────────────────
def _pav(values, weights):
    """Agirlikli izotonik regresyon (Pool-Adjacent-Violators) -> monoton azalmayan."""
    n = len(values)
    if n == 0:
        return []
    blocks = []  # [value, weight, count]
    for i in range(n):
        blocks.append([values[i], weights[i], 1])
        while len(blocks) >= 2 and blocks[-2][0] > blocks[-1][0]:
            v2, w2, c2 = blocks.pop()
            v1, w1, c1 = blocks.pop()
            tw = w1 + w2
            nv = (v1 * w1 + v2 * w2) / tw if tw > 0 else (v1 + v2) / 2.0
            blocks.append([nv, tw, c1 + c2])
    out = []
    for v, _w, c in blocks:
        out.extend([v] * c)
    return out


def calibrate_score(symbol, edge, uncal_prob, cfg):
    if getattr(cfg, 'canli_only', False):
        # CANLI-ONLY: gecmis kalibrasyon skoru OYNATMAZ; gosterilen sayi yalniz bu barin
        # MC kenarindan turer (uydurma 'yon bilme %' degil, canli olasilik turevi).
        return (uncal_prob, f"CANLI MC kenari (kalibrasyon yok): %{uncal_prob}", False)
    rows = [r for r in _load_signals() if r.get('symbol') == symbol]
    resolved = [r for r in rows if r.get('outcome') in ('HIT', 'STOP', 'DIR_OK', 'DIR_BAD')]
    cal = [r for r in resolved if isinstance(r.get('edge'), (int, float))]
    if len(cal) < cfg.calib_min_resolved:
        return (uncal_prob,
                f"SKOR (kalibre DEGIL, 0-{cfg.prob_cap} sinirli): %{uncal_prob}",
                False)
    boundaries = cfg.calib_edge_bins
    nb = len(boundaries) + 1
    n_b = [0] * nb
    w_b = [0.0] * nb
    for r in cal:
        bi = sum(1 for b in boundaries if b < r['edge'])
        n_b[bi] += 1
        if r.get('outcome') in ('HIT', 'DIR_OK'):
            w_b[bi] += 1.0
    sum_n = sum(n_b)
    sum_w = sum(w_b)
    p_glob = (sum_w + 1.0) / (sum_n + 2.0)
    m0 = cfg.calib_prior_strength
    rate_b = [(w_b[i] + m0 * p_glob) / (n_b[i] + m0) for i in range(nb)]
    weight_b = [n_b[i] + m0 for i in range(nb)]
    rates_iso = _pav(rate_b, weight_b)
    bi = sum(1 for b in boundaries if b < edge)
    realized_rate = rates_iso[bi]
    n_eff = n_b[bi]
    w = n_eff / (n_eff + cfg.calib_shrink_k)
    final = w * realized_rate + (1 - w) * (uncal_prob / 100.0)
    prob = int(_clip(int(round(final * 100)), 0, cfg.calib_prob_ceiling))
    X = int(round(realized_rate * 100))
    return (prob, f"SKOR (legacy bilesik islem-cozumu ~%{X} n={n_eff}; endpoint accuracy degil): %{prob}", True)


# ─── CLUSTER 5 — GOZLEM dogrulama ────────────────────────────────────────────
def _herald_bucket(n):
    return 'dusuk(1-2)' if n <= 2 else ('orta(3-4)' if n <= 4 else 'yuksek(5-6)')


def gozlem_bucket_rate(symbol, herald_n, side_hint, cfg):
    bkt = _herald_bucket(herald_n)
    wins = tot = bad = 0
    for r in _load_signals():
        if r.get('symbol') != symbol:
            continue
        if r.get('herald_side') != side_hint or r.get('side') != side_hint:
            continue
        try:
            _hn = int(r.get('herald_n', 0) or 0)
        except (ValueError, TypeError):
            bad += 1
            continue                       # bozuk/eski log satiri -> render'i cokertme
        if _herald_bucket(_hn) != bkt:
            continue
        oc = r.get('outcome')
        if oc in ('HIT', 'DIR_OK'):
            wins += 1
            tot += 1
        elif oc in ('STOP', 'DIR_BAD'):
            tot += 1
    if bad:
        sys.stderr.write(f"[UYARI] gozlem telemetrisi: {bad} bozuk alan atlandi\n")
    if tot < cfg.gozlem_min_resolved:
        return None
    a = cfg.gozlem_prior_n / 2.0
    return ((wins + a) / (tot + cfg.gozlem_prior_n), tot, wins)


def gozlem_validation_tag(symbol, scen, cfg):
    res = gozlem_bucket_rate(symbol, scen.herald_n, scen.side_hint, cfg)
    if res is None:
        return 'legacy cozum telemetrisi YETERSIZ (OOS katkisi degil)'
    rate, n, wins = res
    # F11 (YÖNTEM §4/§2.1): nokta-tahmin asla yalniz degil -> Wilson CI + N (ham orneklem).
    lo, hi = _wilson_ci(wins, n, z=getattr(cfg, "yontem_wilson_z", 1.96))
    ind = "  [CI 0.5'i kapsiyor -> DOGRULANAMADI]" if lo <= 0.5 <= hi else ""
    return (f"legacy bilesik cozum ~%{round(rate * 100)} "
            f"[W:%{round(100*lo)}-%{round(100*hi)} N={n}] (OOS katkisi degil){ind}")


def scen_cell_rate(symbol, cell, cfg, side=None):
    """Sparse senaryo ID'sinin legacy bilesik cozum telemetrisi; OOS katkisi DEGIL.
    side verilirse YALNIZ o yonde acilmis islemler sayilir (YON-FARKINDALIKLI) -> bir
    hucrenin LONG/SHORT isabeti karismaz; side=None -> tum islemler (havuz, sadece bilgi).
    Yalniz cozulmus satirlar; HIT/DIR_OK=kazanc, STOP/DIR_BAD=kayip; Beta-prior shrink.
    Yetersiz ornek -> None (durustce 'DOGRULANMADI'). NO-LOOKAHEAD (yalniz gecmis log)."""
    if not cell:
        return None
    wins = tot = bad = 0
    for r in _load_signals():
        try:
            rc = int(r.get('scen_cell', 0) or 0)
        except (ValueError, TypeError):
            bad += 1
            continue                       # bozuk/eski log satiri -> render'i cokertme
        if r.get('symbol') != symbol or rc != int(cell):
            continue
        if side is not None and r.get('side') != side:
            continue                       # yon-farkindalikli: yalniz istenen yondeki islemler
        oc = r.get('outcome')
        if oc in ('HIT', 'DIR_OK'):
            wins += 1
            tot += 1
        elif oc in ('STOP', 'DIR_BAD'):
            tot += 1
    if bad:
        sys.stderr.write(f"[UYARI] senaryo telemetrisi: {bad} bozuk alan atlandi\n")
    if tot < cfg.scen_cell_min_resolved:
        return None
    a = cfg.scen_cell_prior_n / 2.0
    return ((wins + a) / (tot + cfg.scen_cell_prior_n), tot, wins)


def scen_cell_validation_tag(symbol, cell, cfg, side=None):
    res = scen_cell_rate(symbol, cell, cfg, side=side)
    if res is None:
        return 'hucre legacy telemetrisi YETERSIZ (OOS katkisi degil)'
    rate, n, wins = res
    yon = f"{side} yonu " if side in ("LONG", "SHORT") else ""
    # F11 (YÖNTEM §4): Wilson CI + N -> kucuk-orneklem hucre orani yaniltmasin.
    lo, hi = _wilson_ci(wins, n, z=getattr(cfg, "yontem_wilson_z", 1.96))
    ind = "  [CI 0.5'i kapsiyor -> DOGRULANAMADI]" if lo <= 0.5 <= hi else ""
    return (f"hucre {yon}legacy bilesik cozum ~%{round(rate * 100)} "
            f"[W:%{round(100*lo)}-%{round(100*hi)} N={n}] (OOS katkisi degil){ind}")


def record_and_resolve(symbol, d: Decision, snap: Snapshot, cfg: Config) -> None:
    cs = snap.candles
    if not cs:
        return
    rows = _load_signals()
    if _SIGNALS_READ_FAIL:
        # KORUMA (denetci R4a): log G/C-duzeyinde okunamadiysa rows=[] 'gecmis yok' DEGILDIR;
        # cozum+kayit bu kosuda atlanir, dosyaya dokunulmaz. (Ic-cagrilarin bayragi sifirlama
        # riskine karsi guard kaynakta — _save_signals'taki kontrol ikinci savunma hattidir.)
        sys.stderr.write("[UYARI] sinyal logu okunamadi -> bu kosuda sinyal cozumu/kaydi "
                         "ATLANDI (gecmis dosya korunuyor)\n")
        return
    by_ms = {c.close_ms: c for c in cs if c.close_ms is not None}
    ms_sorted = sorted(by_ms)
    oldest = ms_sorted[0] if ms_sorted else None
    for r in rows:
        if r.get("symbol") != symbol or r.get("outcome") not in (None, "OPEN"):
            continue
        bar = r.get("bar_ms")
        if bar is None:
            continue
        # EXPIRED-FIX: sinyal mevcut pencerenin ALTINDA kaldiysa yanlis barla cozme
        if oldest is not None and bar < oldest:
            r["outcome"] = "EXPIRED"
            continue
        future = [by_ms[m] for m in ms_sorted if m > bar][:cfg.signal_horizon_bars]
        side, tgt, inv = r.get("side"), r.get("target"), r.get("inval")
        if tgt is None or inv is None:
            continue
        oc = "OPEN"
        for fc in future:
            if side == "LONG":
                ht, hs = fc.high >= tgt, fc.low <= inv
            else:
                ht, hs = fc.low <= tgt, fc.high >= inv
            if ht and hs:
                # SOZLESME-BIRLESTIRME (2.tur): ayni mumda hedef+stop uc kanalda uc farkli
                # cozuluyordu (canli=AMBIG/karne-disi, backtest=kayip, plan=STOP). Karne-disi
                # birakmak isabeti IYIMSER sisiriyordu; artik canli defter de backtest/plan
                # ile ayni: KONSERVATIF STOP (+ ambig=1 isareti; eski AMBIG kayitlar korunur).
                oc = "STOP"; r["ambig"] = 1; break
            if ht:
                oc = "HIT"; break
            if hs:
                oc = "STOP"; break
        if oc == "OPEN" and len(future) >= cfg.signal_horizon_bars:
            moved = future[-1].close - r.get("entry", future[-1].close)
            ok = (moved > 0) if side == "LONG" else (moved < 0)
            oc = "DIR_OK" if ok else "DIR_BAD"
        r["outcome"] = oc
        # F4 (FABLE6_5): MALIYET-SONRASI NET SONUC — cozulen sinyale net_abs/net_r yazilir.
        # Maliyet alani olmayan eski kayitlarda net UYDURULMAZ (None kalir, brut sicil surer).
        if oc in ("HIT", "STOP", "DIR_OK", "DIR_BAD"):
            try:
                _e_nr = float(r.get("entry") or 0.0)
                _risk_nr = abs(_e_nr - float(r.get("inval") or 0.0))
                if oc == "HIT":
                    _gross_nr = abs(float(r.get("target") or 0.0) - _e_nr)
                elif oc == "STOP":
                    _gross_nr = -_risk_nr
                else:
                    _mv_nr = future[-1].close - _e_nr
                    _gross_nr = _mv_nr if side == "LONG" else -_mv_nr
                _na_nr, _nr_nr = _net_r(_gross_nr, r.get("cost"), _risk_nr)
                if _nr_nr is not None:
                    r["net_abs"], r["net_r"] = round(_na_nr, 8), round(_nr_nr, 4)
            except (TypeError, ValueError):
                pass
    last = cs[-1]
    if d.karar in ("LONG", "SHORT") and last.close_ms is not None and d.target and d.stop:
        if not any(r.get("symbol") == symbol and r.get("bar_ms") == last.close_ms for r in rows):
            # F3 (FABLE6_5): karar-oncesi siniflandirma d.scen144 ile gelir; log onu kullanir
            # (cift hesap yok, karar ve log ayni hucreyi soyler). Eski yol fallback kalir.
            scen_r = getattr(d, "scen144", None)
            if scen_r is None:
                try:
                    st_r = build_structure(cs, cfg)
                    scen_r = classify_scenario(snap, st_r, cfg) if st_r.valid else None
                except Exception:
                    scen_r = None
            try:
                st_m = build_structure(cs, cfg)
                micro_r = [[m.mid, m.side] for m in classify_micro(snap, st_m, cfg)
                           if m.side in ("LONG", "SHORT")] if st_m.valid else []
            except Exception:
                micro_r = []
            try:
                _aile_log = rejim_ailesi(snap, cfg)
            except Exception:
                _aile_log = ""
            try:
                _td_log = 1 if taze_donus(cs, snap.htf, cfg)[0] else 0
            except Exception:
                _td_log = 0
            try:
                _htf_log = htf_bias(snap.htf, cfg) if snap.htf else 0
            except Exception:
                _htf_log = 0
            rows.append({"symbol": symbol, "bar_ms": last.close_ms, "side": d.karar,
                         "aile": _aile_log, "vol_rejim": d.regime,
                         "taze": _td_log, "htf_dir": _htf_log,
                         "micro": micro_r,
                         "entry": round(d.entry, 8), "target": round(d.target, 8),
                         "inval": round(d.stop, 8), "prob": d.prob, "outcome": "OPEN",
                         "cost": (round(getattr(d, "cost_abs", 0.0), 8)
                                  if getattr(d, "cost_abs", 0.0) > 0 else None),
                         "p_target": round(d.p_target, 4),
                         "p_stop": round(d.reversal_risk / 100.0, 4),
                         "rev_sign": d.rev_sign,
                         "rev_str": round(getattr(d, 'rev_str', 0.0), 3),
                         "edge": round(d.edge, 4),
                         "herald_n": (scen_r.herald_n if scen_r else 0),
                         "herald_side": (scen_r.side_hint if scen_r else 'NEUTRAL'),
                         "scen_cell": (scen_r.cell if scen_r else 0)})
    try:
        _persist_disagree(symbol, cs[-1].close_ms if cs else None, d.disagree, d.block_p, cfg)
    except Exception as exc:
        sys.stderr.write("[UYARI] uzlasmazlik telemetrisi kaydedilemedi: " + str(exc)[:120] + "\n")
    try:
        # F11 (YÖNTEM §2.1/KT-5): blok yonsel serisi ORTOGONALLIK tanisi icin (izole store)
        _persist_block_series(symbol, cs[-1].close_ms if cs else None, d.block_p, cfg)
    except Exception as exc:
        sys.stderr.write("[UYARI] blok-serisi telemetrisi kaydedilemedi: " + str(exc)[:120] + "\n")
    _save_signals(rows, cfg)


# ════════════════════════════════════════════════════════════════════════════
# DEFLATED SHARPE / TRIAL-COUNT — durust N/A sozlesmesi
# Dogrulanmis net getiri ve tam trial registry yoktur; sahte DSR hesaplanmaz.
# ════════════════════════════════════════════════════════════════════════════
def dsr_report(symbol, cfg) -> str:
    """DSR yalniz dogrulanmis net getiriler ve tam trial registry ile anlamlidir."""
    base = ("DSR=N/A (yon isabetlerini ±1 getiri saymak ve senaryo-hucresini trial "
            "saymak gecersiz; dogrulanmis net-getiri + trial registry yok) | "
            + _cpcv_pbo_txt(symbol) + " [OAT kismi tanisal]")
    # F11 (YÖNTEM §2.1/KT-5): blok ORTOGONALLIK tanisi (mean|corr|). Salt telemetri;
    # log-pool agirligini degistirmez. Yuksek |corr| -> confluence breadth'i sisirmis olabilir.
    if getattr(cfg, "yontem_ortho_enabled", True):
        try:
            _o = block_orthogonality(symbol, cfg)
            if _o and _o.get("mean_abs_corr") is not None:
                _flag = ("  [>%d: sahte-confluence riski]" % round(100 * cfg.yontem_ortho_corr_hi)
                         if _o["mean_abs_corr"] >= cfg.yontem_ortho_corr_hi else "")
                base += (f" | ORTOGONALLIK mean|corr|={_o['mean_abs_corr']:.2f}"
                         f" ({_o['pairs']} cift, {_o['n_bar']} bar){_flag}")
            elif _o is not None:
                base += " | ORTOGONALLIK: veri yetersiz (blok-serisi olgunlasmadi)"
        except Exception as exc:
            sys.stderr.write("[UYARI] ortogonallik tanisi hesaplanamadi: " + str(exc)[:100] + "\n")
    return base


def analiz_metni(symbols=None) -> str:
    """Legacy islem logunu bariyer/expiry cozum semantigiyle ozetler.

    HIT/STOP ilk-temas, DIR_OK/DIR_BAD ise yalniz bariyer degmeyen expiry sonucudur;
    bu ikisinin bilesik basarisi endpoint yon dogrulugu DEGILDIR. Saf endpoint
    olcumu append-only forward_ledger_metrics'tedir.
    tek-yon payi, kayma egilimi, hucre yogunlugu. Bu tablo bu oturumda ELLE hesaplanan
    '%92 yukselis / %8 donus' teshisinin otomatigidir. Saf okuma; karara dokunmaz."""
    cfg = Config()
    rows = [r for r in _load_signals()
            if not symbols or r.get("symbol") in symbols]
    coz = [r for r in rows if r.get("outcome") in ("HIT", "STOP", "DIR_OK", "DIR_BAD")]
    L = ["=" * 56, "OZ-ANALIZ — LEGACY ISLEM COZUM TELEMETRISI", "=" * 56,
         "UYARI: asagidaki HIT+DIR_OK bilesigi endpoint yon dogrulugu degildir."]
    if not rows:
        L.append("henuz sinyal yok."); return "\n".join(L)
    w_g = sum(1 for r in coz if r.get("outcome") in ("HIT", "DIR_OK"))
    L.append(f"toplam sinyal: {len(rows)} | cozulen: {len(coz)} | bilesik cozum basarisi: "
             + (f"%{100.0*w_g/len(coz):.0f}" if coz else "-"))
    # ── REJIM-FAZI x YON tablosu (yeni 'aile' alani; eski kayitlar ayri kovada) ──
    tab = {}
    for r in coz:
        k = (r.get("aile") or "ESKI-KAYIT(rejim yok)", r.get("side") or "?")
        w, l = tab.get(k, (0, 0))
        if r.get("outcome") in ("HIT", "DIR_OK"):
            w += 1
        else:
            l += 1
        tab[k] = (w, l)
    L.append("-" * 56)
    L.append("REJIM-FAZI x YON bilesik islem-cozum basarisi (endpoint accuracy degil):")
    for (aile, yon), (w, l) in sorted(tab.items(), key=lambda kv: -(kv[1][0] + kv[1][1])):
        n = w + l
        L.append(f"  {aile:22s} {yon:5s}  {w}/{n}  (%{100.0*w/n:.0f})")
    # ── VOL-REJIM x YON + 1S-UYUM: 'vol_rejim' ve 'htf_dir' alanlari her sinyalde
    # loga YAZILIYORDU ama hicbir yerde OKUNMUYORDU (yalniz-yazilan telemetri).
    # Artik OZ-ANALIZ ikisini de OLCER. Salt okuma/gosterim; karara dokunmaz.
    vt = {}
    for r in coz:
        kv2 = (r.get("vol_rejim") or "ESKI-KAYIT", r.get("side") or "?")
        w, l = vt.get(kv2, (0, 0))
        if r.get("outcome") in ("HIT", "DIR_OK"):
            w += 1
        else:
            l += 1
        vt[kv2] = (w, l)
    if vt:
        L.append("-" * 56)
        L.append("VOL-REJIM x YON bilesik islem-cozum basarisi:")
        for (vr2, yon2), (w, l) in sorted(vt.items(), key=lambda kv: -(kv[1][0] + kv[1][1])):
            n = w + l
            L.append(f"  {vr2:22s} {yon2:5s}  {w}/{n}  (%{100.0*w/n:.0f})")
    # ── F11 (YÖNTEM §3.4): REJIM-KOSULLU E_net (isabet DEGIL — maliyet-sonrasi beklenti).
    # net_r ve vol_rejim zaten AYNI satirda; bosluk yalniz gruplamaydi. Salt telemetri;
    # DSR=N/A surer (deflate yok). Bir rejimde E_net<0 ise 'kenar rejim-kosullu/yok'.
    if getattr(cfg, "yontem_regime_enet_enabled", True):
        renet = {}
        for r in coz:
            nr = r.get("net_r")
            if isinstance(nr, (int, float)):
                renet.setdefault(r.get("vol_rejim") or "ESKI-KAYIT", []).append(float(nr))
        if renet:
            L.append("-" * 56)
            L.append("REJIM-KOSULLU E_net (maliyet-sonrasi R; YÖNTEM §3.4; yon-isabeti DEGIL):")
            for rg, xs in sorted(renet.items(), key=lambda kv: -len(kv[1])):
                _re = realized_expectancy(xs)
                _sh = (f" Sharpe/islem={_re['sharpe']:+.2f}" if _re["sharpe"] is not None else "")
                L.append(f"  {rg:16s} E_net={_re['E_net']:+.2f}R{_sh} "
                         f"net-win %{round(100*_re['win_rate'])}"
                         f"[W:{round(100*_re['win_lo'])}-{round(100*_re['win_hi'])}] N={_re['n']}"
                         + ("  [E_net<=0: bu rejimde kenar YOK]" if _re["E_net"] <= 0 else ""))
    uy = {}
    for r in coz:
        hd2 = r.get("htf_dir")
        yon3 = r.get("side")
        if hd2 is None or yon3 not in ("LONG", "SHORT"):
            ku = "ESKI-KAYIT"
        elif hd2 == 0:
            ku = "4s-YATAY"
        else:
            ku = "4s-UYUMLU" if (hd2 > 0) == (yon3 == "LONG") else "4s-KARSI"
        w, l = uy.get(ku, (0, 0))
        if r.get("outcome") in ("HIT", "DIR_OK"):
            w += 1
        else:
            l += 1
        uy[ku] = (w, l)
    if uy:
        L.append("-" * 56)
        L.append("4S-UYUM bilesik islem-cozum basarisi:")
        for ku, (w, l) in sorted(uy.items(), key=lambda kv: -(kv[1][0] + kv[1][1])):
            n = w + l
            L.append(f"  {ku:22s}       {w}/{n}  (%{100.0*w/n:.0f})")
    # ── GUVEN + MC-RISK KALIBRASYONU: log'daki 'prob' ve 'p_stop' alanlari yaziliyor
    # ama hic okunmuyordu (denetim: olu log alani). T8 teshisi ("MC p_stop %20 dedi,
    # gercek %100 stop") artik OTOMATIK olculur. Salt okuma; karara dokunmaz.
    pr = [r for r in coz if isinstance(r.get("prob"), (int, float)) and r.get("prob")]
    if pr:
        _op = mean([float(r["prob"]) for r in pr])
        _gi = 100.0 * sum(1 for r in pr if r.get("outcome") in ("HIT", "DIR_OK")) / len(pr)
        L.append("-" * 56)
        L.append(f"LEGACY GUVEN KARSILASTIRMASI: ort. gosterilen guven %{_op:.0f} vs bilesik cozum "
                 f"%{_gi:.0f} (n={len(pr)})"
                 + ("  [ASIRI-GUVEN belirtisi]" if _op > _gi + 10 else ""))
        # F11 (YÖNTEM §2.3/KT-7): ECE — gosterilen guven ile gerceklesen isabet arasi
        # kalibrasyon hatasi. Brier ledger'da zaten var; bu onun eksik tamamlayicisi.
        if getattr(cfg, "yontem_ece_enabled", True):
            _ecep = [(float(r["prob"]) / 100.0, r.get("outcome") in ("HIT", "DIR_OK"))
                     for r in pr]
            _er = ece_reliability(_ecep, bins=getattr(cfg, "yontem_ece_bins", 10))
            if _er:
                L.append(f"KALIBRASYON ECE={_er['ece']:.3f} (0=mukemmel; |guven-gerceklesen| "
                         f"agirlikli, n={_er['n']})"
                         + ("  [ZAYIF KALIBRASYON]" if _er["ece"] > 0.10 else ""))
    ps = [r for r in coz if isinstance(r.get("p_stop"), (int, float))
          and r.get("outcome") in ("HIT", "STOP")]
    if ps:
        _mp = 100.0 * mean([float(r["p_stop"]) for r in ps])
        _gs = 100.0 * sum(1 for r in ps if r.get("outcome") == "STOP") / len(ps)
        L.append(f"MC STOP-RISKI KALIBRASYONU: MC ort. p_stop %{_mp:.0f} vs gercek stop orani "
                 f"%{_gs:.0f} (n={len(ps)})"
                 + ("  [RISK KUCUMSENIYOR]" if _gs > _mp + 15 else ""))
    # ── TEK-YON + KAYMA (sembol basina) ──
    L.append("-" * 56)
    for sym in sorted({r.get("symbol") for r in rows if r.get("symbol")}):
        mk, myon, mpay, mn = yon_monokultur(sym, cfg)
        ky, krate, kn = kayma_alarmi(sym, cfg)
        durum = []
        if mk:
            durum.append(f"TEK-YON {myon} %{round(mpay*100)}")
        if ky:
            durum.append(f"KAYMA isabet %{round(krate*100)}")
        L.append(f"  {sym:10s} {signals_summary(sym)}")
        if durum:
            L.append(f"  {'':10s} !! " + " | ".join(durum))
    # ── TAZE-DONUS penceresinde acilan sinyaller (ayri olculur) ──
    td = [r for r in coz if r.get("taze") == 1]
    if td:
        w_td = sum(1 for r in td if r.get("outcome") in ("HIT", "DIR_OK"))
        L.append("-" * 56)
        L.append(f"TAZE-DONUS penceresinde acilanlar: {w_td}/{len(td)} isabet "
                 f"(dusukse pencere kismasi gorevini yapiyor demektir)")
    # ── en yogun hucreler ──
    hc = {}
    for r in coz:
        c = r.get("scen_cell") or 0
        if c:
            w, l = hc.get(c, (0, 0))
            if r.get("outcome") in ("HIT", "DIR_OK"):
                w += 1
            else:
                l += 1
            hc[c] = (w, l)
    sik = [(c, w, l) for c, (w, l) in hc.items() if w + l >= 4]
    if sik:
        L.append("-" * 56)
        L.append("en yogun senaryo hucreleri (n>=4):")
        for c, w, l in sorted(sik, key=lambda t: -(t[1] + t[2]))[:6]:
            L.append(f"  hucre#{c:3d}  {w}/{w+l}  (%{100.0*w/(w+l):.0f})")
    # ── PUSU (kosullu plan) karnesi: tetik haritasinin OLCULEN sicili ──
    try:
        p_all = _plan_yukle()
        p_sem = [s for s in sorted(p_all) if not symbols or s in symbols]
        p_satir = []
        for s in p_sem:
            hist = (p_all.get(s) or {}).get("hist", [])
            if not hist:
                continue
            # TUTARLILIK FIX (2.tur): pusu_karne olcum=0 kayitlari SAYMAZKEN bu tablo
            # sayiyordu -> ayni sembol icin iki 'olculen' yuzde celisebiliyordu. Ayni filtre.
            _olc = [h for h in hist if h.get("olcum", 1)]
            n_at = sum(1 for h in _olc if h.get("sonuc") in ("HEDEF", "STOP"))
            n_h = sum(1 for h in _olc if h.get("sonuc") == "HEDEF")
            n_ip = sum(1 for h in hist if h.get("sonuc") == "IPTAL")
            n_bs = sum(1 for h in hist if h.get("sonuc") == "TETIKSIZ")
            # ENVANTER-FIX: ZAMAN-ASIMI ve olcum-disi (olcum=0) kayitlar eskiden
            # HICBIR kolonda gorunmuyordu -> tablo toplami hist ile tutmuyordu.
            # Karneye yine SAYILMAZLAR (dogru); yalniz envanterde gorunur oldular.
            n_za = sum(1 for h in hist if h.get("sonuc") == "ZAMAN-ASIMI")
            n_gk = sum(1 for h in hist if h.get("sonuc") == "GEC-KACTI")
            n_od = sum(1 for h in hist if h.get("sonuc") in ("HEDEF", "STOP")
                       and not h.get("olcum", 1))
            p_satir.append(f"  {s:10s} ateslenen {n_at:3d} -> {n_h} HEDEF "
                           f"(%{round(100*n_h/max(1,n_at))}) | iptal {n_ip} | tetiksiz {n_bs}"
                           + (f" | zaman-asimi {n_za}" if n_za else "")
                           + (f" | gec-kacti {n_gk}" if n_gk else "")
                           + (f" | olcum-disi {n_od}" if n_od else ""))
        if p_satir:
            L.append("-" * 56)
            L.append("PUSU KARNESI (kosullu tetik planlari, olculen):")
            L.extend(p_satir)
    except Exception as exc:
        L.append("PUSU KARNESI UYARISI: " + str(exc)[:100])
    L.append("=" * 56)
    return "\n".join(L)


def signals_summary(symbol=None) -> str:
    rows = [r for r in _load_signals() if symbol is None or r.get("symbol") == symbol]
    if not rows:
        return "KAYIT: henuz sinyal yok"
    hit = sum(1 for r in rows if r.get("outcome") == "HIT")
    stop = sum(1 for r in rows if r.get("outcome") == "STOP")
    dok = sum(1 for r in rows if r.get("outcome") == "DIR_OK")
    dbad = sum(1 for r in rows if r.get("outcome") == "DIR_BAD")
    opn = sum(1 for r in rows if r.get("outcome") in (None, "OPEN"))
    exp = sum(1 for r in rows if r.get("outcome") == "EXPIRED")
    bar_n = hit + stop
    exp_n = dok + dbad
    if bar_n + exp_n == 0:
        return f"KAYIT: {len(rows)} cagri | henuz cozulmedi (acik:{opn} expired:{exp})"
    tgt = f"ILK-TEMAS HEDEF %{100.0*hit/bar_n:.0f} ({hit}/{bar_n})" if bar_n else "ILK-TEMAS: -"
    son = (f"SURE-SONU AYNI-YON %{100.0*dok/exp_n:.0f} ({dok}/{exp_n}; bariyer-degmeyen)"
           if exp_n else "SURE-SONU: -")
    # F4 (FABLE6_5): maliyet-sonrasi NET karne (yalniz maliyeti bilinen yeni-nesil kayitlar)
    # F11 (YÖNTEM §1.4/§4): ham 'ortR' -> E_net + tanimlayici Sharpe + net-win Wilson CI.
    # DSR DEGIL (deflate yok, trial registry yok): salt telemetri; dsr_report N/A surer.
    _nets = [r.get("net_r") for r in rows if isinstance(r.get("net_r"), (int, float))]
    net_txt = ""
    _re = realized_expectancy(_nets)
    if _re:
        _sh = (f" Sharpe/islem={_re['sharpe']:+.2f}" if _re["sharpe"] is not None else "")
        net_txt = (f" | NET(maliyet-sonrasi) E_net={_re['E_net']:+.2f}R{_sh}"
                   f" net-win %{round(100*_re['win_rate'])}[W:{round(100*_re['win_lo'])}-"
                   f"{round(100*_re['win_hi'])}] (n={_re['n']})")
    return f"ISLEM TELEMETRISI: {tgt} | {son}{net_txt} | acik:{opn} expired:{exp} | toplam:{len(rows)}"


# ════════════════════════════════════════════════════════════════════════════
# CIKTI
# ════════════════════════════════════════════════════════════════════════════
def _tetik_seviyeleri(snap: Snapshot, st: Structure, micros: List[MicroScen], cfg: Config):
    """TETIK HARITASI + KOSULLU PLAN katmaninin TEK SEVIYE KAYNAGI (ikisi asla
    birbirinden sapamaz): (ust, alt, hedef_long, hedef_short, pay_lo, pay_hi,
    supurme_bilgi). Havuzlar mikro #6/#7 varsa onlarin seviyesi, yoksa bant
    kenarlari; LONG-tepki hedefi VWAP (giris SEVIYESININ ustundeyse) yoksa ust
    havuz; SHORT-tepki hedefi alt havuz. Stop paylari OLCULEN supurme derinligi."""
    a = st.atr
    ust = next((m.seviye for m in micros if m.mid == 6 and m.seviye > 0), st.range_high)
    alt = next((m.seviye for m in micros if m.mid == 7 and m.seviye > 0), st.range_low)
    vwp = next((m.seviye for m in micros if m.mid == 13 and m.seviye > 0), 0.0)
    _atrs_t = atr_series(snap.candles, cfg.atr_period)
    p_lo, p_hi, n_lo, n_hi, p_cal = supurme_olcumu(snap.candles, _atrs_t, cfg)
    # SIMETRI-FIX (denetim): eskiden LONG-tepki hedefi VWAP (yakin) iken SHORT-tepki hedefi
    # HEP alt havuzdu (uzak) -> iki planin RR/karnesi yapisal olarak esitsiz olculuyordu
    # (LONG planlar kisa hedefle sisirilmis isabet). Iki taraf AYNI kural: bant ICINDEKI
    # VWAP varsa en yakin makul hedef, yoksa karsi havuz; hedef girise en az
    # min_target_atr*ATR uzakta (mikro-hedefli/anlamsiz plan uretilmez).
    gap_t = cfg.min_target_atr * a
    hedef_long = vwp if (alt + gap_t < vwp <= ust) else ust
    if hedef_long - alt < gap_t:
        hedef_long = alt + gap_t
    hedef_short = vwp if (alt <= vwp < ust - gap_t) else alt
    if ust - hedef_short < gap_t:
        hedef_short = ust - gap_t
    return ust, alt, hedef_long, hedef_short, p_lo * a, p_hi * a, (p_lo, p_hi, n_lo, n_hi, p_cal)


def net_okuma(symbol: str, snap: Snapshot, st: Structure, d: Decision,
              micros: List[MicroScen], cfg: Config) -> List[str]:
    """INSAN OKUMASI: 'su olursa bu olur' dagilimini TEK haritada toplar — ana trend,
    kimin stop havuzu nerede, oncelikli taraf ve somut tetik->plan satirlari. ADAY dili;
    seviyeler yapidan/mikro-kaliplardan gelir, karari DEGISTIRMEZ, yalniz cevirir."""
    L: List[str] = []
    cs = snap.candles
    a = st.atr
    price = st.price
    if a <= 0:
        return L
    aile = rejim_ailesi(snap, cfg)
    hdir = htf_bias(snap.htf, cfg) if snap.htf else 0
    ust, alt, hedef_long, hedef_short, pay_lo, pay_hi, _sinfo = \
        _tetik_seviyeleri(snap, st, micros, cfg)
    p_lo, p_hi, n_lo, n_hi, p_cal = _sinfo
    trend_txt = {1: "YUKARI", -1: "ASAGI", 0: "belirsiz/yatay"}[hdir]
    L.append(f"ANA TREND (4s): {trend_txt}  |  rejim ailesi: {aile}")
    L.append(f"USTTEKI HAVUZ {_fmt(ust)} = SHORT'cularin stoplari (tepeye igne = zorunlu ALIS dalgasi)")
    L.append(f"ALTTAKI HAVUZ {_fmt(alt)} = LONG'cularin stoplari (dibe igne = zorunlu SATIS dalgasi)")
    if d.karar in ("LONG", "SHORT"):
        L.append(f"MOTOR KARARI NET: {d.karar} — seviyeler yukaridaki KARAR blogunda; "
                 f"asagidaki harita PLAN BOZULURSA ne olacagini soyler")
    else:
        _kaynak_up = "4s trend yukari" if hdir > 0 else "surdurulmus 15m egilim yukari (4s yatay)"
        _kaynak_dn = "4s trend asagi" if hdir < 0 else "surdurulmus 15m egilim asagi (4s yatay)"
        if aile == "ASAGI-TREND":
            L.append(f"ONCELIKLI TARAF: SHORT ({_kaynak_dn} -> tepkiler satis firsati); "
                     "ama su an TETIK YOK -> BEKLE dogru")
        elif aile == "YUKARI-TREND":
            L.append(f"ONCELIKLI TARAF: LONG ({_kaynak_up} -> geri cekilmeler alim firsati); "
                     "ama su an TETIK YOK -> BEKLE dogru")
        elif aile == "ASIRI-VOL":
            L.append("ONCELIK: TEMKIN — asiri oynaklik; fitil/absorpsiyon kaliplari olgunlasmadan girilmez")
        else:
            L.append("ONCELIK: iki kenar da oynanir (yatay) — kenara gelmeden islem yok -> BEKLE dogru")
    L.append(f"OLCULEN SUPURME DERINLIGI: asagi {p_lo:.2f} ATR (n={n_lo}), "
             f"yukari {p_hi:.2f} ATR (n={n_hi})"
             + ("" if p_cal else " [az ornek -> sabit pay]")
             + " — stop paylari buna gore (av bolgesi DISINDA)")
    L.append("TETIK HARITASI (hepsi 15m KAPANISLA teyit ister; ADAY dili):")
    # DAR-BANT (denetim): plan_kur ile AYNI kosul — harita, kurulmayacak plani
    # ADAY diye gosteremez (dar bantta hedef karsi av bolgesine tasar; celiskili geometri).
    if (ust - alt) < cfg.min_target_atr * a:
        L.append(f"  !! BANT DAR ({(ust - alt) / a:.2f} ATR < {cfg.min_target_atr:.1f} ATR): "
                 f"kenar-tepki pususu KURULMAZ — kirilim/kapanis teyidi beklenir")
    else:
        L.append(f"  {_fmt(ust)} ustune IGNE + iceri donus -> SHORT tepki ADAYI "
                 f"(stop ~{_fmt(ust + pay_hi)}, hedef {_fmt(hedef_short)})")
        L.append(f"  {_fmt(alt)} altina IGNE + geri alis  -> LONG tepki ADAYI "
                 f"(stop ~{_fmt(alt - pay_lo)}, hedef {_fmt(hedef_long)})")
    L.append(f"  {_fmt(ust)} ustunde KAPANIS          -> yukari devam; short iptal")
    L.append(f"  {_fmt(alt)} altinda KAPANIS          -> asagi devam"
             + (" (ana trendle uyumlu)" if hdir < 0 else ""))
    return L


# ════════════════════════════════════════════════════════════════════════════
# KOSULLU PLAN (PUSU) YASAM-DONGUSU — "su olursa bu olur"un OLCULEN hali
# Soru: "gecen calistirmada 'X'e igne+geri alis -> LONG' dendi; ARADAKI mumlarda
# o igne GELDI MI? Geldiyse plan su an KAZANIYOR mu, stop mu oldu, hedef mi
# vurdu? Kapanisla kirildiysa hangi senaryo gecerli?" Tetik haritasi duzyazi
# olarak kalmaz: her calistirma iki kenar planini KAYDEDER; bir sonraki
# calistirma bu planlari aradaki mumlara karsi MEKANIK degerlendirir.
# Karar motoruna DOKUNMAZ: salt kayit + rapor (net_okuma ile ayni seviye kaynagi).
# ════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════════
# ONCU TAHMIN SICILI (YON9-EK) — kullanici isteri: "fiyat hareket ETTIKTEN sonra
# degil, ONCE soyle". Her kosu kosulsuz yon+bant tahmini yayinlar (fc); bu katman
# tahmini KAYDEDER ve ufuk dolunca GERCEKLESENLE kiyaslayip OLCER (yon isabeti +
# bant kapsamasi). Boylece 'su olursa bu olur' degil: 'yonum SU, bandim SU; gecen
# tahminlerimin olculen isabeti SU' konusulur. Karar motoruna DOKUNMAZ (salt sicil).
# ════════════════════════════════════════════════════════════════════════════
def _fc_log_path():
    p = os.environ.get("YON_FORECAST_LOG")
    return p if p else os.path.join(_kalici_klasor(), "yon_forecasts.jsonl")


_FC_READ_FAIL = False   # tahmin sicili G/C-duzeyinde okunamadi mi (R4 korumasinin fc esdegeri)


def _fc_yukle() -> List[Dict]:
    # VERI-KAYBI FIX (denetim): sinyal logundaki R4 korumasi (okuma hatasi -> dosya EZILMEZ)
    # tahmin sicilinde YOKTU: G/C hatasinda kismi/bos liste donuyor ve _fc_kaydet gecmis
    # tahminleri sessizce siliyordu. Ayni koruma: bayrak dikilir, kaydetme atlanir.
    global _FC_READ_FAIL
    out = []
    try:
        if not os.path.exists(_fc_log_path()):
            _FC_READ_FAIL = False
            return out
        with open(_fc_log_path(), "r", encoding="utf-8") as f:
            for no, ln in enumerate(f, 1):
                ln = ln.strip()
                if ln:
                    try:
                        obj = json.loads(ln)
                        if not isinstance(obj, dict):
                            raise ValueError("JSON nesnesi dict degil")
                        out.append(obj)
                    except (json.JSONDecodeError, TypeError, ValueError) as exc:
                        raise ValueError(f"tahmin sicili satir {no} bozuk: {exc}") from exc
    except Exception as e:
        sys.stderr.write(f"[UYARI] tahmin sicili okunamadi ({_fc_log_path()}): {str(e)[:80]}\n")
        _FC_READ_FAIL = True
        return []
    _FC_READ_FAIL = False
    return out


def _fc_kaydet(rows: List[Dict], cfg: Config) -> Optional[CommitReceipt]:
    if _FC_READ_FAIL:
        sys.stderr.write("[UYARI] tahmin sicili bu kosuda OKUNAMADIGI icin ustune YAZILMADI "
                         "(gecmis korunuyor; bu kosunun tahmini atlandi)\n")
        return None
    try:
        yol = _fc_log_path()
        return _atomic_commit_jsonl(yol, rows[-cfg.fc_log_max:])   # ATOMIK (flock+fsync+replace)
    except (StoreError, OSError) as e:
        sys.stderr.write(f"[UYARI] tahmin sicili yazilamadi: {str(e)[:80]}\n")
        return None


def fc_karne(symbol: str, cfg: Optional[Config] = None) -> Tuple[int, int, int, int]:
    """Append-only ledger karnesi: tum 3-sinif model tahmini + p10/p90 kapsama."""
    m = forward_ledger_metrics(symbol, cfg or Config())
    if not m.get("valid"):
        return (0, 0, 0, 0)
    return (int(m["n"]), int(m["hit"]), int(m["band_hit"]), int(m["band_n"]))


def forecast_truth_state(symbol: str, cfg: Config) -> Dict[str, object]:
    """Append-only secici karnenin rapor/uyari durumu; karar kapisi DEGILDIR.

    Nokta accuracy, bagimlilik-dayanikli CI ve rejim protokolu olmadan otomatik
    market bloklayamaz. ``block`` bu nedenle daima False'tur.
    """
    lm = forward_ledger_metrics(symbol, cfg)
    # Risk telemetrisi trade_decision secici karnesidir; tum-3-sinif proper
    # model karnesi fc_karne/ledger raporunda ayridir.
    n, h, bi, bn = (int(lm["selective_n"]), int(lm["selective_hit"]),
                    int(lm["band_hit"]), int(lm["band_n"]))
    acc = (h / n) if n else None
    band = (bi / bn) if bn else None
    state = "YETERSIZ"
    cap = None
    block = False
    warn = False
    reasons: List[str] = []
    min_n = max(int(getattr(cfg, "forecast_truth_min_resolved", 12)),
                int(cfg.backtest_min_effective))
    if not lm.get("valid"):
        state = "GECERSIZ"
        warn = True
        reasons.append("append-only ledger dogrulanamadi: " + str(lm.get("reason", "?")))
    elif n >= min_n:
        if acc is not None and acc <= getattr(cfg, "forecast_truth_hard_acc", 0.40):
            state = "KIRMIZI"
            cap = int(getattr(cfg, "forecast_truth_conf_cap_hard", 50))
            block = False  # CI/rejim-dayanikli kapı yok; telemetri karari bloklamaz
            warn = True
            reasons.append(f"yon karnesi {h}/{n}=%{round(100*acc)} <= %{round(100*getattr(cfg, 'forecast_truth_hard_acc', 0.40))}")
        elif acc is not None and acc <= getattr(cfg, "forecast_truth_soft_acc", 0.45):
            state = "SARI"
            cap = int(getattr(cfg, "forecast_truth_conf_cap_soft", 52))
            warn = True
            reasons.append(f"yon karnesi {h}/{n}=%{round(100*acc)} zayif")
        else:
            state = "YESIL"
    else:
        reasons.append(f"yon karnesi n<{min_n} ({h}/{n})")
    if lm.get("valid") and bn >= min_n and band is not None and band < getattr(cfg, "forecast_truth_min_band", 0.60):
        warn = True
        reasons.append(f"bant kapsama {bi}/{bn}=%{round(100*band)} < %{round(100*getattr(cfg, 'forecast_truth_min_band', 0.60))}")
        if state == "YESIL":
            state = "SARI"
            cap = int(getattr(cfg, "forecast_truth_conf_cap_soft", 52))
    return {"state": state, "n": n, "hit": h, "acc": acc, "band_n": bn,
            "band_hit": bi, "band": band, "cap": cap, "block": block,
            "warn": warn, "reason": "; ".join(reasons)}


def forecast_truth_note(symbol: str, cfg: Config) -> str:
    st = forecast_truth_state(symbol, cfg)
    if st.get("state") in ("KIRMIZI", "SARI") or st.get("reason"):
        _acc = "-" if st.get("acc") is None else f"%{round(100*float(st['acc']))}"
        _band = "-" if st.get("band") is None else f"%{round(100*float(st['band']))}"
        return (f"YON-SAGLIGI {st['state']}: yon {st.get('hit')}/{st.get('n')} ({_acc}), "
                f"bant {st.get('band_hit')}/{st.get('band_n')} ({_band})"
                + (f" — {st.get('reason')}" if st.get('reason') else ""))
    return ""


def _clear_pending_pusu_keep_active(symbol: str) -> None:
    """Tek-maruziyet icin bekleyen pusu listesi temizlenir; aktif ve hist korunur."""
    try:
        eski = _plan_yukle().get(symbol) or {}
        _plan_kaydet(symbol, {"pusu": [], "aktif": eski.get("aktif", []), "hist": eski.get("hist", [])})
    except Exception as exc:
        sys.stderr.write("[UYARI] bekleyen pusu temizlenemedi: " + str(exc)[:100] + "\n")


def forecast_kaydet_ve_coz(symbol: str, snap: Snapshot, d: Decision, cfg: Config) -> List[str]:
    """COZUM adimi (record_and_resolve'un tahmin esdegeri): acik tahminlerin ufku dolduysa
    gercekle kiyasla (yon HIT/MISS + kapanis q10-q90 bandinin ICINDE mi), yenisini kaydet.
    Doner: rapor satirlari (render 'ONCU TAHMIN' blogunda basar)."""
    cs = snap.candles
    out: List[str] = []
    if not cs or cs[-1].close_ms is None:
        return out
    rows = _fc_yukle()
    if _FC_READ_FAIL:
        return ["[UYARI] tahmin sicili okunamadi -> bu kosuda tahmin cozumu/kaydi ATLANDI (dosya korunuyor)"]
    by_ms = sorted((c.close_ms, c.close) for c in cs if c.close_ms is not None)
    oldest = by_ms[0][0] if by_ms else None
    bar_sp = (cs[-1].close_ms - cs[-2].close_ms) if len(cs) >= 2 and cs[-2].close_ms else 900_000
    degisti = False
    for r in rows:
        if r.get("symbol") != symbol or r.get("outcome") is not None:
            continue
        try:
            hedef_ms = r["bar_ms"] + r["h"] * bar_sp
            # EXPIRED-FIX (denetim, olculdu): tahmin cozumu yalniz UFUK KAPANISINI ister
            # (price0/q'lar kayitta) — bar_ms'in pencereden dusmesi cozumu ENGELLEMEZ.
            # Eski kural (bar_ms < oldest) cozulebilir tahmini erken EXPIRED'a atip
            # karneden sessizce dusuruyordu; simdi kural hedef_ms uzerinden + GORUNUR satir.
            if oldest is not None and hedef_ms < oldest:
                r["outcome"] = "EXPIRED"   # ufuk kapanisi pencereden dustu -> OLCULEMEDI
                degisti = True
                out.append(f"[TAHMIN-EXPIRED] {time.strftime('%H:%M', time.localtime(r['bar_ms']/1000.0))} "
                           f"tahmini: ufuk kapanisi veri penceresinden dustu -> OLCULEMEDI (karneye sayilmaz)")
                continue
            son = next(((ms, cl) for ms, cl in by_ms if ms >= hedef_ms), None)
            if son is None:
                kalan = max(0, int((hedef_ms - cs[-1].close_ms) / bar_sp))
                out.append(f"[TAHMIN-BEKLIYOR] {time.strftime('%H:%M', time.localtime(r['bar_ms']/1000.0))} "
                           f"tahmini ({['ASAGI','NOTR','YUKARI'][r['dir']+1]}): ufka {kalan} mum var")
                continue
            cH = son[1]
            # OLCUM-SIMETRISI FIX (denetim): tahmin NOTR esigi fc_notr_atr*ATR iken
            # gerceklesme EPSILON ile sayiliyordu (1 tik yukari = HIT). Ayni esik iki
            # tarafa da uygulanir: esik-alti gerceklesme YATAY'dir -> yonlu tahmin
            # HIT/MISS yerine NOTR yazilir (kosullu dogruluk: piyasa GERCEKTEN hareket
            # ettiginde yon dogru muydu). Eski kayitta atr yok -> eski davranis aynen.
            _esik = (cfg.fc_notr_atr * float(r["atr"])) if r.get("atr") else 0.0
            _dm = cH - r["price0"]
            gerc = 0 if abs(_dm) <= _esik else (1 if _dm > 0 else -1)
            r["bant_ici"] = 1 if (r["q10"] <= cH <= r["q90"]) else 0
            if r["dir"] == 0 or gerc == 0:
                r["outcome"] = "NOTR"
            else:
                r["outcome"] = "HIT" if gerc == r["dir"] else "MISS"
            degisti = True
            out.append(f"[TAHMIN-COZUM] {time.strftime('%H:%M', time.localtime(r['bar_ms']/1000.0))} "
                       f"tahmini {['ASAGI','NOTR','YUKARI'][r['dir']+1]} @{_fmt(r['price0'])} -> "
                       f"gercek {['ASAGI','YATAY','YUKARI'][gerc+1]} @{_fmt(cH)} = "
                       f"{r['outcome']}{' | bant ICINDE' if r['bant_ici'] else ' | bant DISINDA'}")
        except Exception as exc:
            sys.stderr.write(f"[UYARI] bozuk tahmin satiri cozulmedi: {str(exc)[:100]}\n")
            continue   # bozuk satir tahmini SILDIRMEZ; sonraki kosuda tekrar denenir
    # yeni tahmin (ayni bar icin ikinci kez yazilmaz — saat ici cift kosu güvenli)
    if d.fc and not any(r.get("symbol") == symbol and r.get("bar_ms") == cs[-1].close_ms
                        for r in rows):
        kayit = {"symbol": symbol, "bar_ms": cs[-1].close_ms}
        kayit.update({k: d.fc[k] for k in ("dir", "pup", "q10", "q50", "q90", "price0", "h")})
        for k in ("pdown", "pflat", "p_selected"):
            if k in d.fc:
                kayit[k] = d.fc[k]
        if d.fc.get("atr"):
            kayit["atr"] = round(float(d.fc["atr"]), 8)   # cozumde NOTR-esigi icin (F6b)
        rows.append(kayit)
        degisti = True
    if degisti:
        _fc_kaydet(rows, cfg)
    return out


# ── S3 ERKEN UYARI SICILI (onceden yaz -> ufuk dolunca MEKANIK olc; forecast sicili deseni) ──
def _erken_log_path():
    p = os.environ.get("YON_ERKEN_UYARI_LOG")
    return p if p else os.path.join(_kalici_klasor(), "yon_erken_uyari.jsonl")


_ERKEN_READ_FAIL = False   # erken-uyari sicili G/C-duzeyinde okunamadi mi (R4 korumasi)


def _erken_yukle() -> List[Dict]:
    global _ERKEN_READ_FAIL
    out = []
    try:
        if not os.path.exists(_erken_log_path()):
            _ERKEN_READ_FAIL = False
            return out
        with open(_erken_log_path(), "r", encoding="utf-8") as f:
            for no, ln in enumerate(f, 1):
                ln = ln.strip()
                if ln:
                    try:
                        obj = json.loads(ln)
                        if not isinstance(obj, dict):
                            raise ValueError("JSON nesnesi dict degil")
                        out.append(obj)
                    except (json.JSONDecodeError, TypeError, ValueError) as exc:
                        raise ValueError(f"erken-uyari sicili satir {no} bozuk: {exc}") from exc
    except Exception as e:
        sys.stderr.write(f"[UYARI] erken-uyari sicili okunamadi ({_erken_log_path()}): {str(e)[:80]}\n")
        _ERKEN_READ_FAIL = True
        return []
    _ERKEN_READ_FAIL = False
    return out


def _erken_kaydet(rows: List[Dict], cfg: Config) -> Optional[CommitReceipt]:
    if _ERKEN_READ_FAIL:
        sys.stderr.write("[UYARI] erken-uyari sicili bu kosuda OKUNAMADIGI icin ustune YAZILMADI "
                         "(gecmis korunuyor; bu kosunun uyarisi atlandi)\n")
        return None
    try:
        return _atomic_commit_jsonl(_erken_log_path(), rows[-cfg.erken_uyari_log_max:])
    except (StoreError, OSError) as e:
        sys.stderr.write(f"[UYARI] erken-uyari sicili yazilamadi: {str(e)[:80]}\n")
        return None


def erken_uyari_karne(symbol: str) -> Tuple[int, int, int]:
    """OLCULEN erken-uyari karnesi: (cozulen, isabet, kacirilan). HIT=uyarilan hareket geldi,
    MISS=tersi/gelmedi (yonlu). NOTR sayilmaz. Salt-okuma; karara dokunmaz."""
    rows = [r for r in _erken_yukle()
            if r.get("symbol") == symbol and r.get("outcome") in ("HIT", "MISS")]
    n = len(rows)
    h = sum(1 for r in rows if r.get("outcome") == "HIT")
    return n, h, n - h


def erken_uyari_kaydet_ve_coz(symbol: str, snap: Snapshot, d: Decision, cfg: Config) -> List[str]:
    """Acik erken-uyarilarin ufku (lookahead_bars) dolunca gercekle kiyasla (HIT/MISS/NOTR),
    yenisini kaydet. Yon URETMEZ; salt olcum (DSR=N/A disiplini: kanitlanmamis kenar)."""
    cs = snap.candles
    out: List[str] = []
    if not getattr(cfg, "erken_uyari_enabled", True) or not cs or cs[-1].close_ms is None:
        return out
    rows = _erken_yukle()
    if _ERKEN_READ_FAIL:
        return ["[UYARI] erken-uyari sicili okunamadi -> cozum/kayit ATLANDI (dosya korunuyor)"]
    by_ms = sorted((c.close_ms, c.close) for c in cs if c.close_ms is not None)
    bar_sp = (cs[-1].close_ms - cs[-2].close_ms) if len(cs) >= 2 and cs[-2].close_ms else 900_000
    degisti = False
    for r in rows:
        if r.get("symbol") != symbol or r.get("outcome") is not None:
            continue
        try:
            hedef_ms = r["bar_ms"] + int(r.get("h", 2)) * bar_sp
            son = [cl for ms, cl in by_ms if r["bar_ms"] < ms <= hedef_ms]
            if not son or (by_ms and by_ms[-1][0] < hedef_ms):
                continue    # ufuk henuz dolmadi -> bekle
            p0 = float(r["price0"])
            thr = float(r.get("move_thr", 0.0))
            up_move = max(son) - p0
            dn_move = p0 - min(son)
            yon = r.get("yon", "NEUTRAL")
            if yon == "LONG":
                oc = "HIT" if up_move >= thr else ("MISS" if dn_move >= thr else "NOTR")
            elif yon == "SHORT":
                oc = "HIT" if dn_move >= thr else ("MISS" if up_move >= thr else "NOTR")
            else:      # NEUTRAL (SIKISMA-PATLAMA / trend-degisim): buyuk hareket geldi mi
                oc = "HIT" if max(up_move, dn_move) >= thr else "NOTR"
            r["outcome"] = oc
            r["realized_up"], r["realized_dn"] = round(up_move, 8), round(dn_move, 8)
            degisti = True
            out.append(f"[ERKEN-COZUM] {time.strftime('%H:%M', time.localtime(r['bar_ms'] / 1000.0))} "
                       f"{r.get('tur')}/{yon} -> {oc}")
        except Exception as exc:
            sys.stderr.write(f"[UYARI] bozuk erken-uyari satiri cozulmedi: {str(exc)[:80]}\n")
            continue
    eu = d.erken if isinstance(d.erken, dict) else None
    if eu and eu.get("risk_var") and not any(
            r.get("symbol") == symbol and r.get("bar_ms") == cs[-1].close_ms for r in rows):
        atr_now = atr_series(cs, cfg.atr_period)[-1] if cs else 0.0
        rows.append({"symbol": symbol, "bar_ms": cs[-1].close_ms, "tur": eu.get("tur"),
                     "yon": eu.get("yon_egilim", "NEUTRAL"), "guc": round(float(eu.get("guc", 0.0)), 3),
                     "price0": cs[-1].close, "atr": round(atr_now, 8),
                     "h": int(getattr(cfg, "erken_uyari_lookahead_bars", 2)),
                     "move_thr": round(getattr(cfg, "erken_uyari_move_atr", 1.0) * atr_now, 8)})
        degisti = True
    if degisti:
        _erken_kaydet(rows, cfg)
    return out


def _plan_store_path():
    p = os.environ.get("YON_PLAN_LOG")
    if p:
        return p
    d = os.path.dirname(_log_path())
    return os.path.join(d, "yon_plans.json") if d else "yon_plans.json"


def _plan_yukle() -> Dict:
    """Store semasi: {SEMBOL: {"pusu": [kurulu planlar], "aktif": [ateslenmis+
    suren planlar], "hist": [sonuclanmis kayitlar]}}. Eski duz-liste kayitlar
    'pusu' olarak okunur (geri uyum)."""
    global _PLAN_STORE_CORRUPT
    try:
        if not os.path.exists(_plan_store_path()):
            _PLAN_STORE_CORRUPT = False
            return {}
        with open(_plan_store_path(), "r", encoding="utf-8") as f:
            obj = json.load(f)
        if not isinstance(obj, dict):
            raise ValueError("plan store dict degil")
        for s, v in list(obj.items()):
            if isinstance(v, list):                     # eski sema -> v2
                obj[s] = {"pusu": v, "aktif": [], "hist": []}
        # HIST-TEKILLESTIRME (S4, canli BTC store kaniti): S3-oncesi donemde ayni-seviye cift
        # AKTIF ayni kosuda cozulunce hist'e BIREBIR AYNI kayit iki kez yazilmisti
        # (tip+seviye+sonuc+ts+olcum ozdes) -> pusu karnesi sisik olculuyordu (canli: 1/4
        # gorunuyordu, gercek 1/3). Birebir-ozdes satirlar tekillenir; farkli ts/sonuc tasiyan
        # mesru kayitlara DOKUNULMAZ. Idempotent; bir sonraki kayitta diske de temiz yazilir.
        for s, v in obj.items():
            h = v.get("hist") if isinstance(v, dict) else None
            if h:
                _gor, _tek = set(), []
                for _k9 in h:
                    try:
                        _im = (_k9.get("tip"), round(float(_k9.get("seviye", 0.0)), 8),
                               _k9.get("sonuc"), int(_k9.get("ts", 0)), _k9.get("olcum", 1))
                    except Exception:
                        _tek.append(_k9)
                        continue
                    if _im in _gor:
                        continue
                    _gor.add(_im)
                    _tek.append(_k9)
                v["hist"] = _tek
        _PLAN_STORE_CORRUPT = False
        return obj
    except Exception as e:
        # BOZUK-DOSYA KORUMASI (denetci R2): sessiz {} -> read-modify-write bir sonraki
        # kayitta DIGER TUM sembollerin pusu/aktif/karnesini uyarisiz siliyordu. Artik:
        # gorunur uyari + bayrak; _plan_kaydet ustune yazmadan once .bozuk yedegi alir.
        sys.stderr.write(f"[UYARI] plan store okunamadi/bozuk ({_plan_store_path()}): "
                         f"{str(e)[:80]} — kayittan once .bozuk yedegi alinacak\n")
        _PLAN_STORE_CORRUPT = True
        return {}


_PLAN_STORE_CORRUPT = False


def _plan_kaydet(symbol: str, kayit: Dict) -> Optional[CommitReceipt]:
    """ATOMIK yazim (tmp + os.replace): telefonda yazim yarida kesilirse dosya
    bozulup TUM canli planlar kaybolmasin (yarim JSON -> _plan_yukle {} donerdi).
    Bozuk mevcut dosya ustune yazilmadan ONCE .bozuk uzantisiyla YEDEKLENIR
    (H13: bozuk kayit sessizce yok edilmez; kanit dosyasi kalir)."""
    try:
        obj = _plan_yukle()
        yol = _plan_store_path()
        if _PLAN_STORE_CORRUPT and os.path.exists(yol):
            try:
                os.replace(yol, yol + ".bozuk")
                sys.stderr.write(f"[UYARI] bozuk plan store yedeklendi: {yol}.bozuk "
                                 f"(diger sembollerin gecmisi bu yedekte)\n")
            except Exception as exc:
                raise OSError("bozuk plan store yedeklenemedi; yazma reddedildi") from exc
        obj[symbol] = kayit
        return _atomic_commit(yol, obj)   # ATOMIK tek-JSON (flock+fsync+replace)
    except (StoreError, OSError) as e:
        sys.stderr.write(f"[UYARI] plan kaydi yazilamadi: {str(e)[:80]}\n")
        return None


def plan_kur(symbol: str, snap: Snapshot, st: Structure,
             micros: List[MicroScen], cfg: Config,
             mc_ilk: Optional[Dict] = None, oncu: Optional[Dict] = None) -> List[Dict]:
    """Bu calistirmanin PUSUSUNU kur: tetik haritasindaki iki kenar plani
    (LONG-TEPKI alt havuzda, SHORT-TEPKI ust havuzda) makine-okur formda
    kaydedilir. Seviyeler _tetik_seviyeleri'nden = NET OKUMA ile BIREBIR AYNI.
    'aktif' (ateslenmis, suren) planlara ve 'hist'e DOKUNMAZ — onlar plan_takip'in.
    ONCU (kullanici direktifi): 'oncu' leading sinyal verilirse (a) sikisma->genisleme'de
    stop paylari genisletilir, (b) guclu oncu yon bir kenara tersse o kenar listeden duser."""
    if snap.candles[-1].close_ms is None or st.atr <= 0:
        return []
    _live_blk_pk, _live_why_pk = live_price_gap_kapisi(snap, st, cfg, kind="pusu")
    if _live_blk_pk:
        return []
    ust, alt, hedef_long, hedef_short, pay_lo, pay_hi, _ = \
        _tetik_seviyeleri(snap, st, micros, cfg)
    # ── ONCU-RISK STOP GENISLETME (market seviyesiyle ayni ilke): patlama yakin -> pay genis ──
    if getattr(cfg, "oncu_yon_enabled", True) and oncu and oncu.get("expansion"):
        pay_lo *= cfg.oncu_stop_widen
        pay_hi *= cfg.oncu_stop_widen
    # DAR-BANT KAPISI (denetim, iki bagimsiz denetci ayni bulguyu olctu): ust-alt <
    # min_target_atr*ATR iken min-mesafe kurali hedefleri KARSI av bolgesine tasiriyordu
    # (hedef_long > ust / hedef_short < alt; 0.48-ATR havuz araligi gercek mumlarla
    # uretildi ve store'a yazildi) -> karsi havuza fitil dokunusu plani HEDEF yazip
    # karneyi sisirebilirdi. Bant bu kadar darken kenar-tepki pususu ANLAMSIZ:
    # plan KURULMAZ (mevcut pusu/aktif/hist'e dokunulmaz; kirilim senaryolari serbest).
    if ust - alt < cfg.min_target_atr * st.atr:
        return []
    bar = int(snap.candles[-1].close_ms)
    planlar = [
        {"tip": "LONG-TEPKI", "seviye": alt, "stop": alt - pay_lo,
         "hedef": hedef_long, "bar_ms": bar},
        {"tip": "SHORT-TEPKI", "seviye": ust, "stop": ust + pay_hi,
         "hedef": hedef_short, "bar_ms": bar},
    ]
    # ── TREND-YONU FILTRESI (devir B1b esigi DOLDU; canli 06-07.07 olcumu, 22 ateslenen):
    # karsi-trend kenar-tepki karnesi LONG-TEPKI 1/11 HEDEF (%9), trend-yonlu SHORT'lar 3/4
    # (ETH). SOL 80.975 uclu-STOP ayni sinifin kanitiydi. GUCLU 1s trendine KARSI kenar-tepki
    # pususu KURULMAZ: dusen trendde LONG-TEPKI, yukselen trendde SHORT-TEPKI listeden duser;
    # YATAY/zayif trendde iki kenar da mesru (bant ticareti). CANLI-ONLY uyumlu: kosul o anki
    # 1s serisinden (htf_trend) — gecmis kalibrasyon dosyasi DEGIL.
    _tdir_pk, _tstrong_pk = htf_trend(snap.htf, cfg)
    if _tstrong_pk and _tdir_pk != 0:
        _yasak_tip = "LONG-TEPKI" if _tdir_pk < 0 else "SHORT-TEPKI"
        # Sorun4 ONARIM (flag fix_pusu_donus_muaf): market yolundaki donus-teyidi muafiyetini
        # pusu'ya da tasi -> taze donus varsa karsi-trend kenar-tepki limiti KURULABILIR.
        _pusu_muaf = False
        if getattr(cfg, "fix_pusu_donus_muaf", False):
            try:
                _td_ok, _ = taze_donus(snap.candles, snap.htf, cfg)
                _pusu_muaf = bool(_td_ok)
            except Exception:
                _pusu_muaf = False
        if not _pusu_muaf:
            planlar = [p for p in planlar if p["tip"] != _yasak_tip]
    # ── ONCU-SINYAL FILTRESI (kullanici direktifi): guclu oncu leading yon bir kenara
    # ters ise o kenar-tepki pususu KURULMAZ (dump/donus riskine karsi kenar acma). Trend
    # filtresiyle AYNI desen: oncu LONG (yukari donus) -> SHORT-TEPKI duser; oncu SHORT -> LONG-TEPKI duser. ──
    if (getattr(cfg, "oncu_pusu_filtre", True) and oncu and oncu.get("side") in ("LONG", "SHORT")
            and float(oncu.get("guc", 0.0)) >= cfg.oncu_yon_min_guc):
        _yasak_oncu = "SHORT-TEPKI" if oncu["side"] == "LONG" else "LONG-TEPKI"
        planlar = [p for p in planlar if p["tip"] != _yasak_oncu]
    # STEP4B: PUSU KARNE RISK KAPISI — gecmis basari yon uretmez; yalniz kotu
    # tip-karneli bekleyen limitin tekrar kurulmasini engeller. Bu, canli market
    # kararini degistirmez; pusu/limit riskini kisar.
    _pusu_ok = []
    for _p in planlar:
        _blok, _neden = pusu_karne_riskli(symbol, _p["tip"], cfg)
        if not _blok:
            _pusu_ok.append(_p)
    planlar = _pusu_ok
    # ── F2 (FABLE6_5) TEK-KENAR KURALI: ayni kosuda iki zit bekleyen plan KURULMAZ ──
    # (kullanici sozlesmesi: "ayni anda hem long hem short plani uretmemeli"). Secim
    # deterministik ve veri-turevli: (1) canli MC ilk-temas olasiligi (p_ust vs p_alt) —
    # once test edilmesi daha olasi kenar; (2) MC yoksa/esitse fiyatin bant-ortasina gore
    # konumu (yakin kenar); (3) tam esitlik -> plan kurulmaz (esitlik=BEKLE ilkesi).
    if getattr(cfg, "pusu_tek_kenar", True) and len(planlar) > 1:
        _sec = None
        try:
            _pu_tk = (float(mc_ilk.get("p_ust"))
                      if mc_ilk and mc_ilk.get("p_ust") is not None else None)
            _pa_tk = (float(mc_ilk.get("p_alt"))
                      if mc_ilk and mc_ilk.get("p_alt") is not None else None)
        except (TypeError, ValueError):
            _pu_tk = _pa_tk = None
        if _pu_tk is not None and _pa_tk is not None and abs(_pu_tk - _pa_tk) > 1e-9:
            _sec = "SHORT-TEPKI" if _pu_tk > _pa_tk else "LONG-TEPKI"
        else:
            _mid_tk = (ust + alt) / 2.0
            _px_tk = snap.candles[-1].close
            if abs(_px_tk - _mid_tk) > cfg.tie_eps_atr * max(st.atr, 1e-12):
                _sec = "SHORT-TEPKI" if _px_tk > _mid_tk else "LONG-TEPKI"
        planlar = [p for p in planlar if _sec is not None and p["tip"] == _sec]
    eski = _plan_yukle().get(symbol) or {}
    if getattr(cfg, "single_exposure_gate_enabled", True) and getattr(cfg, "no_new_pusu_when_active_plan", True):
        if eski.get("aktif"):
            _plan_kaydet(symbol, {"pusu": [], "aktif": eski.get("aktif", []), "hist": eski.get("hist", [])})
            return []
    # CIFT-AKTIF ONLEME (3.tur, canli BTC bulgusu): ayni seviyede zaten ATESLENMIS (aktif)
    # plan izlenirken plan_kur her kosu ayni kenara YENI pusu kuruyordu -> ayni seviye ikinci
    # kez ateslenip 'pusu:2 AKTIF!' cifte maruziyet dogurdu (canli: BTC @62796.2 x2). Ayni
    # tip + plan_tasima_atr icinde AKTIF varken o kenara yeni pusu KURULMAZ.
    _aktifler = eski.get("aktif", [])
    planlar = [p for p in planlar
               if not any(a.get("tip") == p["tip"]
                          and abs(a.get("seviye", 0.0) - p["seviye"]) <= cfg.plan_tasima_atr * st.atr
                          for a in _aktifler)]
    # PLAN TASIMA: yeni seviye eskisine cok yakinsa (ayni pusu) kurulus zamani KORUNUR.
    # Aksi halde her kosu saati sifirlar ve SURE-DOLDU'ya asla ulasilamaz (olu kod olurdu);
    # BEKLEMEDE raporundaki 'N mum gecti' de hep ~1 kosu gosterirdi (yaniltici).
    for p in planlar:
        es = next((q for q in eski.get("pusu", []) if q.get("tip") == p["tip"]
                   and abs(q.get("seviye", 0.0) - p["seviye"]) <= cfg.plan_tasima_atr * st.atr), None)
        if es is not None:
            # HAYALET-TETIK FIX (denetim, olculdu): eskiden yalniz bar_ms korunur,
            # seviye/stop/hedef GUNCELLENIRDI -> hafif kaymis YENI seviyeyi, orijinal
            # seviyeyi tetiklememis GECMIS mumlar retroaktif ateslleyebiliyordu.
            # TASIMA artik planin TAMAMINI korur: pusu bir SOZLESMEDIR; tolerans
            # icindeyse aynen devam eder, disindaysa zaten YENI plan kurulur.
            p.update(es)
    # F4 (FABLE6_5): plan MALIYETI sozlesmeye yazilir (net karne icin; tasima SONRASI
    # nihai seviyeden, defter yok -> tablo-slip konservatif). Eski planlarda alan yoktur.
    for p in planlar:
        try:
            p["maliyet"] = round(txn_cost_abs(symbol, float(p["seviye"]), cfg,
                                              book=None, atr=st.atr), 8)
        except Exception:
            p.setdefault("maliyet", None)
    _plan_kaydet(symbol, {"pusu": planlar,
                          "aktif": eski.get("aktif", []),
                          "hist": eski.get("hist", [])})
    return planlar


def _plan_degerlendir(plan: Dict, cands: List[Candle], k: int, H: int) -> Dict:
    """Kurulmus plani SONRAKI mumlara karsi MEKANIK degerlendir (saf fonksiyon).
    Tetik: seviyeye IGNE (long: low<L / short: high>L) + k mum icinde dogru
    tarafa 15m KAPANIS (geri alis; supurme_olcumu ile ayni semantik).
    IPTAL: yanlis tarafta kapanis gelir ve k penceresi icinde geri ALINMAZSA
    (teyitli kirilim -> 'devam' senaryosu gerceklesti).
    ATESLENDIYSE: giris = geri-alis mumunun kapanisi; sonrasi ilk-temas
    (_bt_resolve semantigi: hedef+stop ayni mumda = STOP sayilir, konservatif).
    BILINCLI SOZLESME: fire mumunun kendi fitilleri SAYILMAZ (giris=KAPANIS,
    fitil giristen ONCE oldu) — hedef-fitili yonunden konservatif, stop-fitili
    yonunden iyimser; seviyeye ONCEDEN emir koyan icin sonuc farkli olabilir.
    Doner: {durum, i(bar-endeksi), entry, sonuc, prog, r}"""
    L = plan["seviye"]
    longp = plan["tip"].startswith("LONG")
    n = len(cands)
    if n == 0:
        return {"durum": "BEKLEMEDE", "gecen": 0}
    dogru = (lambda c: c.close > L) if longp else (lambda c: c.close < L)
    yanlis = (lambda c: c.close < L) if longp else (lambda c: c.close > L)
    igne = (lambda c: c.low < L) if longp else (lambda c: c.high > L)
    fire = None
    gordu = 0                                  # seviye en az bir kez test edildi mi (rapor icin)
    for i in range(n):
        c = cands[i]
        if not (igne(c) or yanlis(c)):
            continue
        gordu = 1
        son = min(i + 1 + k, n)
        j_re = next((j for j in range(i, son) if dogru(cands[j])), None)
        if j_re is not None:                   # k penceresinde geri alis -> tetik
            fire = j_re
            break
        if son < i + 1 + k:                    # pencere veri sonunda yarim -> henuz belli degil
            return {"durum": "BEKLEMEDE", "gecen": n, "test": 1}
        if any(yanlis(cands[j]) for j in range(i, son)):
            return {"durum": "IPTAL", "i": i, "gecen": n}   # teyitli kirilim: geri alinmadi
        # igne var ama pencerede ne geri-alis ne kirilim kapanisi -> izlemeye devam
    if fire is None:
        return {"durum": ("SURE-DOLDU" if n >= H else "BEKLEMEDE"), "gecen": n, "test": gordu}
    entry = cands[fire].close
    hedef, stop = plan["hedef"], plan["stop"]
    sgn = 1 if longp else -1
    # GEC-KACTI (denetim, olculdu): geri-alis kapanisi HEDEFIN otesindeyse islem
    # penceresi KACMISTIR; ilk-temas kurali bunu 'HEDEF' sayip NEGATIF-R kazanci
    # karneye yazardi (giris 101.50 > hedef 100.70 -> '+-0.4R HEDEF'). Karne-DISI.
    if (hedef - entry) * sgn <= 0:
        return {"durum": "ATESLENDI", "i": fire, "entry": entry, "sonuc": "GEC-KACTI",
                "prog": 1.0, "r": 0.0, "gecen": n}
    risk = (entry - stop) * sgn
    sonuc, prog = "SURUYOR", 0.0
    for kk in range(fire + 1, n):
        c = cands[kk]
        hit_t = (c.high >= hedef) if longp else (c.low <= hedef)
        hit_s = (c.low <= stop) if longp else (c.high >= stop)
        if hit_s:                      # ayni mumda ikisi de -> STOP (konservatif)
            sonuc = "STOP"
            break
        if hit_t:
            sonuc = "HEDEF"
            break
    span = (hedef - entry) * sgn
    if span > 0:
        prog = _clip((cands[-1].close - entry) * sgn / span, -9.0, 9.0)
    rr = (span / risk) if risk > 0 else 0.0
    return {"durum": "ATESLENDI", "i": fire, "entry": entry, "sonuc": sonuc,
            "prog": prog, "r": rr, "gecen": n}


def _aktif_degerlendir(p: Dict, cands: List[Candle]) -> Tuple[str, float]:
    """Ateslenmis (aktif) planin devami: fire sonrasi ilk-temas hedef/stop
    (ayni mumda ikisi = STOP, konservatif); temas yoksa SURUYOR + yol orani."""
    longp = p["tip"].startswith("LONG")
    sgn = 1 if longp else -1
    if (p["hedef"] - p["entry"]) * sgn <= 0:   # GEC-KACTI: giris hedef otesi (eski-surum kaydi)
        return "GEC-KACTI", 0.0
    for c in cands:
        hit_t = (c.high >= p["hedef"]) if longp else (c.low <= p["hedef"])
        hit_s = (c.low <= p["stop"]) if longp else (c.high >= p["stop"])
        if hit_s:
            return "STOP", -1.0
        if hit_t:
            return "HEDEF", 1.0
    span = (p["hedef"] - p["entry"]) * sgn
    prog = _clip((cands[-1].close - p["entry"]) * sgn / span, -9.0, 9.0) if (span > 0 and cands) else 0.0
    return "SURUYOR", prog


def _pusu_canli_giris_onerisi(symbol: str, snap: Snapshot, p: Dict, cfg: Config) -> str:
    """F5 (FABLE6_5): pusu tetigi TEYIT edildikten (igne + kapanmis 15m geri-alisi) sonra
    'o anki gercek piyasa fiyati + bid/ask + spread + slip' ile MARKET giris ONERISI uret.
    Bayat/kopuk fiyat veya hedef-otesi durumda onermez; 'kovalamak yasak' sozlesmesi
    ustundur (bu yardimci yalniz GEC-KALINMAMIS ateslemede cagrilir). Bos str = satir yok."""
    if not getattr(cfg, "pusu_canli_giris_onerisi", True):
        return ""
    yon = "LONG" if str(p.get("tip", "")).startswith("LONG") else "SHORT"
    try:
        book = snap.book or {}
        canli = None
        if book:
            canli = _step49_safe_float(book.get("ask" if yon == "LONG" else "bid"))
        if canli is None:
            canli = _step49_safe_float(getattr(snap, "live_price", None))
        cs_ = snap.candles
        atr_ = atr_series(cs_, cfg.atr_period)[-1] if cs_ else 0.0
        if canli is None or atr_ <= 0 or getattr(snap, "stale", False):
            return ("   [CANLI GIRIS] tetik teyitli fakat canli fiyat DOGRULANAMADI "
                    "(mark/book yok veya veri bayat) -> SIMDI GIRME; sonraki kosuyu bekle")
        _gap_cg = abs(canli - cs_[-1].close)
        if _gap_cg > getattr(cfg, "live_gap_block_atr", 0.60) * atr_:
            return (f"   [CANLI GIRIS] tetik teyitli fakat canli fiyat kapali mumdan "
                    f"{_gap_cg / atr_:.2f} ATR kopuk -> GIRME (kovalama yasak; F5)")
        sgn = 1 if yon == "LONG" else -1
        if (float(p["hedef"]) - canli) * sgn <= 0:
            return "   [CANLI GIRIS] canli fiyat hedefin otesinde -> GIRME (islem penceresi kacti)"
        maliyet = txn_cost_abs(symbol, canli, cfg, book=(snap.book or None),
                               side=yon, atr=atr_)
        spr = _step49_safe_float(book.get("spread_pct")) if book else None
        spr_txt = (f"spread %{spr * 100:.3f}, " if spr is not None
                   else "(defter yok: tablo-slip) ")
        return (f"   [CANLI GIRIS ONERISI] tetik 15m KAPANISLA teyitli -> SIMDI MARKET {yon} "
                f"~{_fmt(canli)} ({spr_txt}komisyon+slip+gecikme maliyeti ~{_fmt(maliyet)} "
                f"= %{maliyet / atr_ * 100:.0f}·ATR) | hedef {_fmt(float(p['hedef']))} / "
                f"stop {_fmt(float(p['stop']))} plandaki gibi")
    except Exception as exc:
        return "   [CANLI GIRIS] oneri hesaplanamadi: " + str(exc)[:80]


def pusu_karne(symbol: str) -> Tuple[int, int, int]:
    """OLCULEN pusu karnesi: (ateslenen_toplam, hedef, stop). Salt-okuma.
    OLCUM-DURUSTLUGU (denetci R5): ara donemi veri-penceresi disinda kalan cozumler
    (olcum=0) karneye SAYILMAZ — 'olculen' diye sunulan yuzdeye olculemeyen aralikli
    sonuc karistirilmaz (eski hali karneyi HEDEF yonune sisiriyordu)."""
    hist = (_plan_yukle().get(symbol) or {}).get("hist", [])
    ates = [h for h in hist if h.get("sonuc") in ("HEDEF", "STOP") and h.get("olcum", 1)]
    return len(ates), sum(1 for h in ates if h["sonuc"] == "HEDEF"), \
        sum(1 for h in ates if h["sonuc"] == "STOP")


def pusu_tip_karne(symbol: str, tip: str) -> Tuple[int, int, int, float]:
    """STEP4B: tip-bazli pusu karnesi. Gecmis karar URETMEZ; yeni pusu riskini
    yalniz yeterli ornek + Wilson alt-sinir kotuyse kisar. Donus: (n, hedef, stop, wilson_alt)."""
    hist = (_plan_yukle().get(symbol) or {}).get("hist", [])
    ates = [h for h in hist if h.get("tip") == tip and h.get("sonuc") in ("HEDEF", "STOP")
            and h.get("olcum", 1)]
    n = len(ates)
    h = sum(1 for x in ates if x.get("sonuc") == "HEDEF")
    stp = sum(1 for x in ates if x.get("sonuc") == "STOP")
    return n, h, stp, _wilson_lower(h, n) if n else 0.0


def pusu_karne_riskli(symbol: str, tip: str, cfg: Config) -> Tuple[bool, str]:
    """Tip-bazli + genel pusu risk kapisi. Canli yon degistirmez, market karari uretmez;
    yalniz bekleyen limit/pusu tekrarini kisar. Once ayni tipin karnesi yeterliyse tip-karnesi
    kullanilir; tip ornegi az ama sembolun GENEL pusu karnesi yeterince kotuyse genel risk
    kapisi uygulanir. Boylece SOL gibi 1/9 toplam pusu karnesi olan sembolde yeni pusu
    'ornegi az' bahanesiyle acik kalmaz. Config + Wilson; gomulu kar-esigi degil."""
    if not getattr(cfg, "pusu_karne_gate_enabled", True):
        return False, "pusu-karne kapisi kapali"
    n, h, s, wl = pusu_tip_karne(symbol, tip)
    if n >= cfg.pusu_karne_min_resolved:
        if wl < cfg.pusu_karne_bad_wilson:
            return True, (f"pusu-karne zayif: {tip} {h}/{n} HEDEF, {s} STOP; "
                          f"Wilson-alt={wl:.2f} < {cfg.pusu_karne_bad_wilson:.2f}")
        return False, f"pusu-karne yeterli: {tip} {h}/{n}, Wilson-alt={wl:.2f}"
    # Tip ornegi azsa GENEL pusu karnesini risk kapisi olarak kullan (direction degil, pusu riski).
    ng, hg, sg = pusu_karne(symbol)
    wlg = _wilson_lower(hg, ng) if ng else 0.0
    if ng >= cfg.pusu_karne_min_resolved and wlg < cfg.pusu_karne_bad_wilson:
        return True, (f"genel pusu-karne zayif: {hg}/{ng} HEDEF, {sg} STOP; "
                      f"Wilson-alt={wlg:.2f} < {cfg.pusu_karne_bad_wilson:.2f}; "
                      f"{tip} tip ornegi az {h}/{n}")
    return False, f"pusu-karne ornek az {h}/{n}; genel {hg}/{ng} Wilson-alt={wlg:.2f}"


def _signal_resolved_by_price(r: Dict, price: Optional[float]) -> Tuple[bool, str]:
    """STEP4G yardimci: logda henuz OPEN gorunen bir market sinyali, bu kosunun
    kapali/live fiyatinda hedef veya stop tarafina zaten ulasmissa yasam-dongusu
    kapisi onu 'acik' saymaz. Dosyayi burada degistirmez; takip_raporu/record katmani
    sonucu karneye yazar. Bu sadece karar icindeki stale-open blokajini engeller."""
    if price is None:
        return False, ""
    try:
        side = r.get("side")
        tgt = float(r.get("target"))
        inv = float(r.get("inval"))
        px = float(price)
    except Exception:
        return False, ""
    if side == "LONG":
        if px >= tgt:
            return True, f"hedef zaten goruldu (live/kapali {_fmt(px)} >= hedef {_fmt(tgt)})"
        if px <= inv:
            return True, f"stop zaten goruldu (live/kapali {_fmt(px)} <= stop {_fmt(inv)})"
    elif side == "SHORT":
        if px <= tgt:
            return True, f"hedef zaten goruldu (live/kapali {_fmt(px)} <= hedef {_fmt(tgt)})"
        if px >= inv:
            return True, f"stop zaten goruldu (live/kapali {_fmt(px)} >= stop {_fmt(inv)})"
    return False, ""


def acik_market_sinyali_var(symbol: str, cfg: Config, current_price: Optional[float] = None) -> Tuple[bool, str]:
    """STEP4C/STEP4G: ayni sembolde ufku dolmamis/open market sinyali varsa yeni market acma.
    Gecmis basari yon uretmez; bu yalniz yasam-dongusu/risk kapisidir.

    STEP4G duzeltmesi: Bu kosuda once takip_raporu sonradan yazildigi icin, hedef/stopu
    simdiki fiyatla zaten gorulmus eski OPEN satiri karar asamasinda bayat 'acik sinyal'
    gibi blokluyordu. Bu fonksiyon, fiyat hedef/stop tarafindaysa onu acik saymaz; sonuc
    kaydi yine takip/record katmaninda normal karneye yazilir."""
    if not getattr(cfg, "market_open_signal_gate_enabled", True):
        return (False, "")
    rows0 = [r for r in _load_signals() if r.get("symbol") == symbol and r.get("outcome") in (None, "OPEN")]
    rows = []
    atlanan: List[str] = []
    for r in rows0:
        if getattr(cfg, "open_signal_resolved_price_gate_enabled", True):
            resolved, why_res = _signal_resolved_by_price(r, current_price)
            if resolved:
                atlanan.append(why_res)
                continue
        rows.append(r)
    if not rows:
        if atlanan:
            return (False, "onceki OPEN sinyal bu kosuda cozulmus gorunuyor; " + atlanan[-1])
        return (False, "")
    r = rows[-1]
    side = r.get("side") or "?"
    ent, tgt, inv = r.get("entry"), r.get("target"), r.get("inval")
    return (True, f"acik market sinyali var ({side} @{_fmt(ent) if ent is not None else '-'}; hedef {_fmt(tgt) if tgt is not None else '-'} / stop {_fmt(inv) if inv is not None else '-'})")


def market_quality_kapisi(symbol: str, sc: Scenario, cfg: Config) -> Tuple[bool, str]:
    """STEP4E: market kalite/olasilik freni. Canli EV pozitif ve RR kabul edilebilir olsa
    bile hedef olasiligi dusuk, stop olasiligi yuksek veya hedef-stop farki dar ise marketi
    BEKLE'ye cevirir. Bu kapi yon URETMEZ ve gecmis winrate'i canli yone sokmaz; sadece
    bu barin MC ilk-temas olasiliklarindan bir risk kapisi kurar."""
    if not getattr(cfg, "market_quality_gate_enabled", True):
        return (False, "")
    if sc is None:
        return (False, "")
    reasons = []
    if sc.p_target < cfg.market_min_target_prob:
        reasons.append(f"MC hedef %{sc.p_target*100:.0f} < %{cfg.market_min_target_prob*100:.0f}")
    if sc.p_stop > cfg.market_max_stop_prob:
        reasons.append(f"MC stop %{sc.p_stop*100:.0f} > %{cfg.market_max_stop_prob*100:.0f}")
    gap = sc.p_target - sc.p_stop
    if gap < cfg.market_min_prob_gap:
        reasons.append(f"MC edge %{gap*100:.0f} < %{cfg.market_min_prob_gap*100:.0f}")
    if reasons:
        return (True, "Market kalite kapisi: " + "; ".join(reasons) + " — az ama emin, BEKLE")
    return (False, "")


def live_price_gap_info(snap: Snapshot, st: Optional[Structure], cfg: Config) -> Tuple[float, float, float, str]:
    """STEP4F: kapali mum fiyatini live mark ile capraz denetler.
    Doner: (gap_abs, gap_atr, age_min, rapor). Hicbiri yon URETMEZ; buyuk fark
    sadece yeni market/pusu kurulumunu engeller ve rapora saydamlik katar."""
    if st is None or not getattr(st, "valid", False) or st.atr <= 0:
        return 0.0, 0.0, 0.0, ""
    lp = getattr(snap, "live_price", None)
    if lp is None or lp <= 0:
        return 0.0, 0.0, 0.0, "live mark yok; kapali mum fiyati kullanildi"
    gap_abs = float(lp) - float(st.price)
    gap_atr = abs(gap_abs) / st.atr if st.atr > 0 else 0.0
    age_min = 0.0
    try:
        if snap.live_server_ms and snap.last_closed_ms:
            age_min = max(0.0, (snap.live_server_ms - snap.last_closed_ms) / 60000.0)
    except Exception:
        age_min = 0.0
    yön = "USTUNDE" if gap_abs > 0 else ("ALTINDA" if gap_abs < 0 else "AYNI")
    rap = (f"kapali={_fmt(st.price)} live-mark={_fmt(lp)} ({yön}, fark {_fmt(gap_abs)} = {gap_atr:.1f} ATR"
           + (f", kapali bar yasi {age_min:.0f}dk" if age_min else "") + ")")
    return gap_abs, gap_atr, age_min, rap


def live_price_gap_kapisi(snap: Snapshot, st: Optional[Structure], cfg: Config, kind: str = "market") -> Tuple[bool, str]:
    """STEP4F: kapali-mum sinyali ile live mark arasinda buyuk fark varsa yeni emir kurma.
    Kapali mumla analiz no-repaint icin dogru; fakat icra fiyati canlidir. Bu kapi,
    gerceklesmis dususu/yukselisi gecikmeli 'canli edge' gibi yazmayi engeller."""
    if not getattr(cfg, "live_price_audit_enabled", True):
        return False, ""
    if kind == "market" and not getattr(cfg, "live_gap_market_gate_enabled", True):
        return False, ""
    if kind == "pusu" and not getattr(cfg, "live_gap_pusu_gate_enabled", True):
        return False, ""
    _ga, gap_atr, age_min, rap = live_price_gap_info(snap, st, cfg)
    if not rap:
        return False, ""
    if rap.startswith("live mark yok"):
        if kind == "market" and getattr(cfg, "mark_live_required_for_market", True):
            return True, "MARK/LIVE kapisi: live mark dogrulanamadi; kapali mum fiyatiyla LIVE market emri yok"
        return False, rap
    if gap_atr >= getattr(cfg, "live_gap_block_atr", 0.60):
        return True, (f"Canli fiyat kapisi: {rap}; kapali mum sinyali live piyasadan uzak "
                      f">= {getattr(cfg, 'live_gap_block_atr', 0.60):.2f} ATR — yeni {kind} yok, taze kosu bekle")
    if age_min >= getattr(cfg, "live_age_warn_min", 18.0) and gap_atr >= getattr(cfg, "live_gap_warn_atr", 0.25):
        return True, (f"Canli fiyat kapisi: {rap}; bar yasi/fiyat farki yuksek — yeni {kind} yok")
    return False, ""



# ════════════════════════════════════════════════════════════════════════════
# STEP4.9 — MARK/LIVE DENETIMI + FORMAL ACIK SINYAL / PLAN STORE
# ════════════════════════════════════════════════════════════════════════════
def _step49_now_ms() -> int:
    try:
        return int(time.time() * 1000)
    except Exception:
        return 0


def _step49_iso(ms: Optional[int]) -> str:
    if not ms:
        return "UNKNOWN"
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(ms) / 1000.0))
    except Exception:
        return str(ms)


def _step49_safe_float(x, default=None):
    try:
        if x is None:
            return default
        y = float(x)
        if math.isnan(y) or math.isinf(y):
            return default
        return y
    except Exception:
        return default


def _step49_json_path(name: str) -> str:
    d = os.environ.get("YON_PANEL_DIR") or _kalici_klasor()
    try:
        os.makedirs(d, exist_ok=True)
    except Exception as exc:
        sys.stderr.write("[UYARI] panel klasoru olusturulamadi: " + str(exc)[:100] + "\n")
    return os.path.join(d, name)


def _step49_load_json(path: str, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, type(default)) else default
    except Exception as e:
        sys.stderr.write(f"[UYARI] step4.9 store okunamadi ({path}): {str(e)[:90]}\n")
        return default


def _step49_save_json(path: str, obj) -> None:
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, path)
    except Exception as e:
        sys.stderr.write(f"[UYARI] step4.9 store yazilamadi ({path}): {str(e)[:90]}\n")


def _open_signal_store_path() -> str:
    return os.environ.get("YON_OPEN_SIGNAL_STORE") or _step49_json_path("yon_open_signals.json")


def _plan_store_v2_path() -> str:
    return os.environ.get("YON_PLAN_STORE_V2") or _step49_json_path("yon_plan_store_v2.json")


def _open_signal_store_load() -> Dict:
    return _step49_load_json(_open_signal_store_path(), {})


def _open_signal_store_save(obj: Dict) -> None:
    _step49_save_json(_open_signal_store_path(), obj)


def _plan_store_v2_load() -> Dict:
    return _step49_load_json(_plan_store_v2_path(), {})


def _plan_store_v2_save(obj: Dict) -> None:
    _step49_save_json(_plan_store_v2_path(), obj)


def _step49_audit(row: Dict, msg: str, cfg: Optional[Config] = None) -> None:
    if row is None:
        return
    cap = getattr(cfg, "plan_store_v2_audit_cap", 120) if cfg else 120
    log = row.setdefault("audit_log", [])
    log.append({"ts": _step49_now_ms(), "time": _step49_iso(_step49_now_ms()), "msg": str(msg)[:220]})
    if len(log) > cap:
        del log[:-cap]


def mark_live_denetime(symbol: str, snap: Optional[Snapshot], st: Optional[Structure], cfg: Optional[Config] = None,
                       mode: Optional[str] = None, data_source: str = "fapi.binance.com",
                       timeframe: str = "15m") -> Dict:
    """STEP5 mark/live denetimi.

    4.9 hatasi: data_freshness_seconds kapali mumun yasini olcuyordu; bu, mark price
    orneginin tazeligi degildi. 5.0'da:
      - data_freshness_seconds = mark/REST orneginin yerel kosu anina gore yasi,
      - last_closed_bar_age_seconds = son kapali mumun server/yerel saate gore yasi,
      - spread order book'taki dogru spread alanindan okunur.
    """
    cfg = cfg or Config()
    now_ms = _step49_now_ms()
    price_src = "close"
    cur = None
    if snap is not None and _step49_safe_float(getattr(snap, "live_price", None)):
        price_src = "mark price"
        cur = _step49_safe_float(getattr(snap, "live_price", None))
    elif st is not None:
        cur = _step49_safe_float(getattr(st, "price", None))
    elif snap is not None and getattr(snap, "candles", None):
        cur = _step49_safe_float(snap.candles[-1].close)
    last_ms = None
    if snap is not None:
        last_ms = getattr(snap, "last_closed_ms", None)
        if not last_ms and getattr(snap, "candles", None):
            last_ms = getattr(snap.candles[-1], "close_ms", None)
    live_ms = getattr(snap, "live_server_ms", None) if snap is not None else None
    fetched_ms = getattr(snap, "live_fetched_ms", None) if snap is not None else None
    freshness = None
    # REST/mark orneginin tazeligi: mum yasi degil, verinin kosu anina gore yasi.
    try:
        if fetched_ms:
            freshness = max(0, int((now_ms - int(fetched_ms)) / 1000))
        elif live_ms:
            freshness = max(0, int((now_ms - int(live_ms)) / 1000))
    except Exception:
        freshness = None
    bar_age = None
    try:
        ref_ms = int(live_ms or now_ms)
        if last_ms:
            bar_age = max(0, int((ref_ms - int(last_ms)) / 1000))
    except Exception:
        bar_age = None
    spread = None
    spread_pct = None
    try:
        if snap is not None and snap.book:
            spread = _step49_safe_float(snap.book.get("spread"))
            spread_pct = _step49_safe_float(snap.book.get("spread_pct"))
            if spread is None:
                bid = _step49_safe_float(snap.book.get("bid"))
                ask = _step49_safe_float(snap.book.get("ask"))
                if bid is not None and ask is not None and ask >= bid:
                    spread = ask - bid
                    mid = (ask + bid) / 2.0
                    spread_pct = spread / mid if mid > 0 else None
    except Exception:
        spread = None
        spread_pct = None
    is_live = bool(price_src == "mark price" and (live_ms or fetched_ms))
    is_closed = bool(last_ms)
    warn = "sorun yok"
    max_age = getattr(cfg, "mark_live_max_data_age_seconds", getattr(cfg, "mark_live_warn_stale_seconds", 60))
    if not is_live:
        warn = "canli mark price dogrulanamadi; market emir PAPER/WAIT"
    elif freshness is not None and freshness > max_age:
        warn = f"veri eski / mark price ornegi {freshness}s > {max_age}s"
    if getattr(snap, "stale", False):
        warn = "veri eski / kaynak stale"
    return {
        "mode": mode or ("LIVE" if is_live else "UNKNOWN"),
        "data_source": data_source,
        "symbol": symbol,
        "timeframe": timeframe,
        "last_candle_time": _step49_iso(last_ms),
        "current_price_source": price_src,
        "current_price": cur,
        "data_freshness_seconds": freshness,
        "last_closed_bar_age_seconds": bar_age,
        "is_live_data": is_live,
        "is_closed_candle": is_closed,
        "spread": spread,
        "spread_pct": spread_pct,
        "slippage_assumption": getattr(cfg, "slip_default_1w", None),
        "commission_assumption": {"maker": getattr(cfg, "maker_fee", None), "taker": getattr(cfg, "taker_fee", None)},
        "warning": warn,
    }

def render_mark_live_denetime(a: Dict) -> List[str]:
    return [
        "MARK/LIVE DENETİM:",
        f"- mode: {a.get('mode')}",
        f"- data_source: {a.get('data_source')}",
        f"- symbol: {a.get('symbol')}",
        f"- timeframe: {a.get('timeframe')}",
        f"- last_candle_time: {a.get('last_candle_time')}",
        f"- current_price_source: {a.get('current_price_source')}",
        f"- current_price: {_fmt(a.get('current_price')) if a.get('current_price') is not None else 'UNKNOWN'}",
        f"- data_freshness_seconds: {a.get('data_freshness_seconds') if a.get('data_freshness_seconds') is not None else 'UNKNOWN'}",
        f"- is_live_data: {str(bool(a.get('is_live_data'))).lower()}",
        f"- is_closed_candle: {str(bool(a.get('is_closed_candle'))).lower()}",
        f"- spread: {_fmt(a.get('spread')) if a.get('spread') is not None else 'UNKNOWN'}",
        f"- slippage_assumption: {a.get('slippage_assumption')}",
        f"- commission_assumption: {a.get('commission_assumption')}",
        f"- warning: {a.get('warning')}",
        f"- last_closed_bar_age_seconds: {a.get('last_closed_bar_age_seconds') if a.get('last_closed_bar_age_seconds') is not None else 'UNKNOWN'}",
        f"- spread_pct: {a.get('spread_pct') if a.get('spread_pct') is not None else 'UNKNOWN'}",
    ]

def market_live_data_kapisi(symbol: str, snap: Snapshot, st: Optional[Structure], cfg: Config) -> Tuple[bool, str]:
    a = mark_live_denetime(symbol, snap, st, cfg)
    if getattr(cfg, "mark_live_required_for_market", True) and not a.get("is_live_data"):
        return True, "MARK/LIVE DENETIM: canli mark price dogrulanamadi; LIVE market emir yok"
    if str(a.get("warning", "")).startswith("veri eski"):
        return True, "MARK/LIVE DENETIM: veri eski; taze kosu bekle"
    return False, ""

def _step49_side(d: Decision) -> Optional[str]:
    if getattr(d, "karar", None) in ("LONG", "SHORT"):
        return d.karar
    return None


def _candidate_open_signal(symbol: str, snap: Snapshot, st: Optional[Structure], d: Decision, cfg: Config) -> Optional[Dict]:
    side = _step49_side(d)
    if not side or st is None or not getattr(st, "valid", False):
        return None
    now = _step49_now_ms()
    px = _step49_safe_float(getattr(snap, "live_price", None), getattr(st, "price", None))
    return {
        "signal_id": f"{symbol}-15m-{side}-{int(getattr(snap, 'last_closed_ms', 0) or now)}",
        "symbol": symbol, "timeframe": "15m", "direction": side, "status": "OPEN",
        "created_at": now, "updated_at": now, "entry_type": "MARKET",
        "entry_price": _step49_safe_float(getattr(d, "entry", None), px),
        "trigger_price": _step49_safe_float(getattr(d, "entry", None), px),
        "stop_price": _step49_safe_float(getattr(d, "stop", None)),
        "target_1": _step49_safe_float(getattr(d, "target", None)),
        "target_2": None, "target_3": None,
        "invalidation_price": _step49_safe_float(getattr(d, "stop", None)),
        # F8 (FABLE6_5): giris bandi + karar maliyeti store'a acik alan olarak yazilir
        "entry_band_low": (_step49_safe_float(getattr(d, "entry", None), px) or 0.0)
                          - getattr(cfg, "entry_buffer_atr", 0.2) * getattr(st, "atr", 0.0),
        "entry_band_high": (_step49_safe_float(getattr(d, "entry", None), px) or 0.0)
                           + getattr(cfg, "entry_buffer_atr", 0.2) * getattr(st, "atr", 0.0),
        "cost_abs": _step49_safe_float(getattr(d, "cost_abs", None)),
        "confidence_score": _step49_safe_float(getattr(d, "prob", None)),
        "scenario_type": getattr(d, "regime", "UNKNOWN"),
        "reason_summary": str(getattr(d, "sebep", ""))[:240],
        "risk_reward": _step49_safe_float(getattr(d, "rr", None)),
        "expected_value": _step49_safe_float(getattr(d, "ev", None)),
        "source_mode": "LIVE" if getattr(snap, "live_price", None) else "UNKNOWN",
        "last_checked_price": px,
        "last_checked_time": now,
        "audit_log": [],
    }


def _candidate_plan_v2(symbol: str, snap: Snapshot, st: Optional[Structure], d: Decision, cfg: Config) -> Optional[Dict]:
    if st is None or not getattr(st, "valid", False):
        return None
    now = _step49_now_ms()
    px = _step49_safe_float(getattr(snap, "live_price", None), getattr(st, "price", None))
    atr = max(_step49_safe_float(getattr(st, "atr", None), 0.0), 1e-12)
    long_trigger = _step49_safe_float(getattr(st, "range_low", None))
    short_trigger = _step49_safe_float(getattr(st, "range_high", None))
    if isinstance(getattr(d, "plan", None), dict):
        long_trigger = _step49_safe_float(d.plan.get("alt_bant"), long_trigger)
        short_trigger = _step49_safe_float(d.plan.get("ust_bant"), short_trigger)
    no_trade_zone = [long_trigger, short_trigger] if long_trigger is not None and short_trigger is not None else None
    long_stop = (long_trigger - cfg.inval_pad_atr * atr) if long_trigger is not None else None
    short_stop = (short_trigger + cfg.inval_pad_atr * atr) if short_trigger is not None else None
    return {
        "schema_version": "fable5_plan_store_v2",
        "plan_id": f"{symbol}-15m-plan-{int(getattr(snap, 'last_closed_ms', 0) or now)}",
        "parent_signal_id": None,
        "symbol": symbol,
        "timeframe": "15m",
        "plan_status": "WAITING",
        "active_scenario": getattr(d, "karar", "BEKLE"),
        "alternative_scenario": "LONG/SHORT_PUSU",
        "no_trade_zone": no_trade_zone,
        "long_trigger": long_trigger,
        "short_trigger": short_trigger,
        "long_invalidation": long_stop,
        "short_invalidation": short_stop,
        "long_stop": long_stop,
        "short_stop": short_stop,
        "long_target_1": short_trigger,
        "short_target_1": long_trigger,
        "plan_created_at": now,
        "plan_updated_at": now,
        "expiration_rule": f"{getattr(cfg, 'plan_store_v2_expire_bars', 16)} bars or invalidation",
        "cancellation_rule": "opposite signal only after invalidation/supersede evidence",
        "update_reason": str(getattr(d, "sebep", ""))[:240],
        "last_checked_price": px,
        "last_checked_time": now,
        "audit_log": [],
    }

def _price_hits_signal(sig: Dict, price: Optional[float]) -> Tuple[str, str]:
    if price is None or not sig:
        return sig.get("status", "OPEN"), "price yok"
    side = sig.get("direction")
    stop = _step49_safe_float(sig.get("stop_price"))
    t1 = _step49_safe_float(sig.get("target_1"))
    if side == "LONG":
        if stop is not None and price <= stop:
            return "CLOSED", "STOP goruldu"
        if t1 is not None and price >= t1:
            return "CLOSED", "TARGET_1 goruldu"
    if side == "SHORT":
        if stop is not None and price >= stop:
            return "CLOSED", "STOP goruldu"
        if t1 is not None and price <= t1:
            return "CLOSED", "TARGET_1 goruldu"
    return sig.get("status", "OPEN"), "plan yasiyor"


def _price_hits_plan_v2(plan: Dict, price: Optional[float],
                        reclaim_close: Optional[float] = None) -> Tuple[str, str]:
    """F6 (FABLE6_5): v2 tetik sozlesmesi legacy _plan_degerlendir ile ESITLENDI.
    Salt fiyat-dokunusu (igne) artik TRIGGERED degil TOUCHED'dir; TRIGGERED yalniz
    KAPANMIS 15m mumun geri-alisi (reclaim_close dogru tarafta) ile verilir. Boylece
    store telemetrisi ile kullaniciya gosterilen tetik davranisi ayrisamaz."""
    if price is None or not plan:
        return plan.get("plan_status", "WAITING"), "price yok"
    li = _step49_safe_float(plan.get("long_invalidation"))
    si = _step49_safe_float(plan.get("short_invalidation"))
    lt = _step49_safe_float(plan.get("long_trigger"))
    stt = _step49_safe_float(plan.get("short_trigger"))
    status = plan.get("plan_status", "WAITING")
    # CLOSED/INVALIDATED gibi terminal durumlar tekrar TRIGGERED'a donmez.
    if status in ("CLOSED", "INVALIDATED", "CANCELLED", "EXPIRED", "SUPERSEDED"):
        return status, "terminal plan korundu"
    if status in ("ACTIVE", "TRIGGERED"):
        side = plan.get("triggered_side")
        if side == "LONG":
            stop = _step49_safe_float(plan.get("long_stop"), li)
            tgt = _step49_safe_float(plan.get("long_target_1"), stt)
            if stop is not None and price <= stop:
                return "CLOSED", "LONG stop/invalidation goruldu"
            if tgt is not None and price >= tgt:
                return "CLOSED", "LONG target_1 goruldu"
        if side == "SHORT":
            stop = _step49_safe_float(plan.get("short_stop"), si)
            tgt = _step49_safe_float(plan.get("short_target_1"), lt)
            if stop is not None and price >= stop:
                return "CLOSED", "SHORT stop/invalidation goruldu"
            if tgt is not None and price <= tgt:
                return "CLOSED", "SHORT target_1 goruldu"
    if status in ("WAITING", "TOUCHED") and li is not None and \
            (price <= li or (reclaim_close is not None and reclaim_close <= li)):
        return "INVALIDATED", "long invalidation goruldu"
    if status in ("WAITING", "TOUCHED") and si is not None and \
            (price >= si or (reclaim_close is not None and reclaim_close >= si)):
        return "INVALIDATED", "short invalidation goruldu"
    if status == "TOUCHED":
        side_t = plan.get("touched_side")
        if side_t == "LONG" and reclaim_close is not None and lt is not None \
                and reclaim_close > lt:
            plan["triggered_side"] = "LONG"
            return "TRIGGERED", "long igne sonrasi kapanmis-mum geri-alisi teyitli"
        if side_t == "SHORT" and reclaim_close is not None and stt is not None \
                and reclaim_close < stt:
            plan["triggered_side"] = "SHORT"
            return "TRIGGERED", "short igne sonrasi kapanmis-mum geri-alisi teyitli"
        return "TOUCHED", "geri-alis kapanisi bekleniyor (F6)"
    if status == "WAITING" and lt is not None and price <= lt:
        plan["touched_side"] = "LONG"
        return "TOUCHED", "long seviyeye igne; kapanmis-mum geri-alisi bekleniyor (F6)"
    if status == "WAITING" and stt is not None and price >= stt:
        plan["touched_side"] = "SHORT"
        return "TOUCHED", "short seviyeye igne; kapanmis-mum geri-alisi bekleniyor (F6)"
    return status, "plan korundu"

def _step49_terminal_status(status: Optional[str]) -> bool:
    return status in ("CLOSED", "INVALIDATED", "CANCELLED", "EXPIRED", "SUPERSEDED")


def _step49_open_status(status: Optional[str]) -> bool:
    return status in ("OPEN", "ACTIVE", "WAITING", "TOUCHED", "TRIGGERED")


def step49_store_denetimi(symbol: str, snap: Snapshot, st: Optional[Structure], d: Decision, cfg: Config) -> Dict:
    now = _step49_now_ms()
    px = _step49_safe_float(getattr(snap, "live_price", None), getattr(st, "price", None) if st else None)
    key = f"{symbol}:15m"
    sigs = _open_signal_store_load() if getattr(cfg, "open_signal_store_enabled", True) else {}
    plans = _plan_store_v2_load() if getattr(cfg, "plan_store_v2_enabled", True) else {}
    existing_sig = sigs.get(key)
    existing_plan = plans.get(key)
    pre_sig = dict(existing_sig) if isinstance(existing_sig, dict) else None
    pre_plan = dict(existing_plan) if isinstance(existing_plan, dict) else None
    action = "CREATE_NEW_PLAN"
    reason = "acik plan yok"
    plan_terminal_this_run = False
    signal_terminal_this_run = False

    # 1) Once mevcut sinyal/plan fiyatla kapanir mi guncelle.
    if existing_sig:
        new_status, why = _price_hits_signal(existing_sig, px)
        existing_sig["last_checked_price"] = px
        existing_sig["last_checked_time"] = now
        if new_status != existing_sig.get("status"):
            existing_sig["status"] = new_status
            existing_sig["updated_at"] = now
            _step49_audit(existing_sig, why, cfg)
            if _step49_terminal_status(new_status):
                signal_terminal_this_run = True
                action = "CLOSE_EXISTING_PLAN" if new_status == "CLOSED" else "INVALIDATE_EXISTING_PLAN"
                reason = why
        sigs[key] = existing_sig
    if existing_plan:
        # F6: geri-alis teyidi icin son KAPANMIS 15m mumun kapanisi da verilir.
        _rc49 = (snap.candles[-1].close if getattr(snap, "candles", None) else None)
        newp, why2 = _price_hits_plan_v2(existing_plan, px, reclaim_close=_rc49)
        existing_plan["last_checked_price"] = px
        existing_plan["last_checked_time"] = now
        if newp != existing_plan.get("plan_status"):
            existing_plan["plan_status"] = newp
            existing_plan["plan_updated_at"] = now
            existing_plan["update_reason"] = why2
            _step49_audit(existing_plan, why2, cfg)
            if _step49_terminal_status(newp):
                plan_terminal_this_run = True
                action = "CLOSE_EXISTING_PLAN" if newp == "CLOSED" else "INVALIDATE_EXISTING_PLAN"
                reason = why2
        plans[key] = existing_plan

    cand_sig = _candidate_open_signal(symbol, snap, st, d, cfg)
    cand_plan = _candidate_plan_v2(symbol, snap, st, d, cfg)
    # Bir plan/sinyal bu kosuda yeni kapanmis/gecersizlesmisse ayni kosuda yerine yenisini
    # otomatik kurma: once kapanis gerekcesi store/audit'e yazilsin, kullanici bir sonraki
    # taze kosuda yeni sozlesmeyi gorsun.
    if plan_terminal_this_run:
        cand_plan = None
    if signal_terminal_this_run:
        cand_sig = None
    audit = mark_live_denetime(symbol, snap, st, cfg)
    if cand_sig and cand_sig.get("entry_type") == "MARKET" and getattr(cfg, "mark_live_required_for_market", True) and not audit.get("is_live_data"):
        cand_sig = None
        action = "KEEP_EXISTING_PLAN" if existing_plan else "CANCEL_EXISTING_PLAN"
        reason = "canli mark/live dogrulanmadigi icin yeni market sinyali kaydedilmedi"

    # 2) Mevcut acik market sinyali varsa: zıt sinyal gecersizlik olmadan yasak; ayni yon guncellenir.
    if existing_sig and _step49_open_status(existing_sig.get("status")):
        if cand_sig and cand_sig.get("direction") != existing_sig.get("direction"):
            status, why = _price_hits_signal(existing_sig, px)
            if not _step49_terminal_status(status):
                action = "KEEP_EXISTING_PLAN"
                reason = f"zit {cand_sig.get('direction')} sinyal geldi ama mevcut {existing_sig.get('direction')} gecersiz degil"
                cand_sig = None
                cand_plan = None
            else:
                existing_sig["status"] = "SUPERSEDED"
                _step49_audit(existing_sig, f"zit sinyal icin supersede: {why}", cfg)
                action = "CREATE_NEW_PLAN_AFTER_SUPERSEDE"
                reason = f"eski sinyal {status}: {why}"
        elif cand_sig and cand_sig.get("direction") == existing_sig.get("direction"):
            action = "UPDATE_EXISTING_PLAN"
            reason = "ayni yon sinyal tazelendi"
            for k in ("entry_price", "trigger_price", "stop_price", "target_1", "confidence_score", "risk_reward", "expected_value", "last_checked_price", "last_checked_time", "reason_summary"):
                if cand_sig.get(k) is not None:
                    existing_sig[k] = cand_sig[k]
            existing_sig["updated_at"] = now
            _step49_audit(existing_sig, reason, cfg)
            sigs[key] = existing_sig
            cand_sig = None
            cand_plan = None

    if cand_sig:
        _step49_audit(cand_sig, "yeni market sinyali kaydedildi", cfg)
        sigs[key] = cand_sig
        action = "CREATE_NEW_PLAN_AFTER_SUPERSEDE" if existing_sig else "CREATE_NEW_PLAN"
        reason = "yeni market sinyali"

    # 3) Plan-store v2: acik WAITING/TRIGGERED/ACTIVE plan varken kor-kurulum yok.
    final_plan_candidate = None
    if cand_plan:
        live_status = (existing_plan or {}).get("plan_status")
        if existing_plan and _step49_open_status(live_status):
            action = "KEEP_EXISTING_PLAN" if action == "CREATE_NEW_PLAN" else action
            reason = "mevcut plan acik; kor-kurulum yok"
        else:
            _step49_audit(cand_plan, "yeni plan sozlesmesi olusturuldu", cfg)
            plans[key] = cand_plan
            final_plan_candidate = cand_plan
            action = "CREATE_NEW_PLAN_AFTER_SUPERSEDE" if existing_plan else "CREATE_NEW_PLAN"
            reason = "acik plan yok veya onceki plan kapali"

    if getattr(cfg, "open_signal_store_enabled", True):
        _open_signal_store_save(sigs)
    if getattr(cfg, "plan_store_v2_enabled", True):
        _plan_store_v2_save(plans)
    final_sig = sigs.get(key)
    final_plan = plans.get(key)
    pre_open = bool((pre_sig and _step49_open_status(pre_sig.get("status"))) or
                    (pre_plan and _step49_open_status(pre_plan.get("plan_status"))))
    pre_dir = (pre_sig or {}).get("direction") or (pre_plan or {}).get("active_scenario")
    pre_status = (pre_sig or {}).get("status") or (pre_plan or {}).get("plan_status")
    pre_inval = (pre_sig or {}).get("invalidation_price") or (pre_plan or {}).get("long_invalidation")
    return {
        "existing_open_signal": pre_open,
        "existing_plan_id": (pre_plan or {}).get("plan_id"),
        "result_plan_id": (final_plan or {}).get("plan_id"),
        "existing_direction": pre_dir,
        "existing_status": pre_status,
        "existing_entry": (pre_sig or {}).get("entry_price"),
        "existing_stop": (pre_sig or {}).get("stop_price"),
        "existing_targets": [(pre_sig or {}).get("target_1"), (pre_sig or {}).get("target_2"), (pre_sig or {}).get("target_3")],
        "existing_invalidation": pre_inval,
        "current_price_vs_plan": px,
        "plan_action": action,
        "plan_action_reason": reason,
        "updated_plan_store": bool(final_plan),
        "audit_log": (final_plan or final_sig or {}).get("audit_log", [])[-5:],
    }

def render_step49_store_denetime(x: Dict) -> List[str]:
    return [
        "AÇIK SİNYAL / PLAN STORE DENETİMİ:",
        f"- existing_open_signal: {str(bool(x.get('existing_open_signal'))).lower()}",
        f"- existing_plan_id: {x.get('existing_plan_id')}",
        f"- result_plan_id: {x.get('result_plan_id')}",
        f"- existing_direction: {x.get('existing_direction')}",
        f"- existing_status: {x.get('existing_status')}",
        f"- existing_entry: {_fmt(x.get('existing_entry')) if x.get('existing_entry') is not None else 'UNKNOWN'}",
        f"- existing_stop: {_fmt(x.get('existing_stop')) if x.get('existing_stop') is not None else 'UNKNOWN'}",
        f"- existing_targets: {x.get('existing_targets')}",
        f"- existing_invalidation: {_fmt(x.get('existing_invalidation')) if x.get('existing_invalidation') is not None else 'UNKNOWN'}",
        f"- current_price_vs_plan: {_fmt(x.get('current_price_vs_plan')) if x.get('current_price_vs_plan') is not None else 'UNKNOWN'}",
        f"- plan_action: {x.get('plan_action')}",
        f"- plan_action_reason: {x.get('plan_action_reason')}",
        f"- updated_plan_store: {str(bool(x.get('updated_plan_store'))).lower()}",
        f"- audit_log: {x.get('audit_log')}",
    ]

def market_risk_kapisi(symbol: str, sc: Scenario, cfg: Config) -> Tuple[bool, str]:
    """STEP4C: market icin yapisal risk freni. Canli EV/MC pozitif olsa bile cok asimetrik
    RR, kullanicinin 'tek stop cok kazanci siler' riskini buyutur. Bu kapi yon URETMEZ;
    yalniz marketi BEKLE'ye cevirir. Gecmis winrate/PBO canli yon uretmek icin kullanilmaz."""
    if not getattr(cfg, "market_risk_gate_enabled", True):
        return (False, "")
    if sc is None:
        return (False, "")
    if sc.rr < cfg.market_rr_min:
        mult = (1.0 / sc.rr) if sc.rr > 1e-9 else float("inf")
        mtxt = (f"~1 stop {mult:.1f} hedefi silebilir" if math.isfinite(mult) else "risk/odul tanimsiz")
        return (True, f"RR asimetrik {sc.rr:.2f} < {cfg.market_rr_min:.2f} ({mtxt}); market yerine BEKLE/pusu-teyit")
    return (False, "")


def open_signal_risk_audit(r: Dict, price: float, atr: Optional[float], cfg: Config) -> str:
    """STEP4D: onceki kosulardan kalan ACIK market sinyalini bugunku risk kapilariyla
    raporda etiketle. Bu fonksiyon outcome/karar DEGISTIRMEZ, yon URETMEZ ve stop/exit
    emri vermez; yalniz dusuk-RR veya belirgin aleyhte ilerleyen eski sinyali 'normal izle'
    olmaktan cikarip riskli olarak gorunur yapar."""
    if not getattr(cfg, "open_signal_audit_enabled", True):
        return ""
    try:
        side = r.get("side")
        ent = float(r.get("entry"))
        tgt = float(r.get("target"))
        inv = float(r.get("inval"))
        sgn = 1.0 if side == "LONG" else -1.0
        reward = (tgt - ent) * sgn
        risk = (ent - inv) * sgn
        notes: List[str] = []
        try:
            pt = float(r.get("p_target"))
            ps = float(r.get("p_stop"))
            pg = pt - ps
            if getattr(cfg, "market_quality_gate_enabled", True) and (
                    pt < getattr(cfg, "market_min_target_prob", 0.50) or
                    ps > getattr(cfg, "market_max_stop_prob", 0.30) or
                    pg < getattr(cfg, "market_min_prob_gap", 0.15)):
                notes.append("eski/acik sinyal bugunku market kalite kapisindan gecmezdi: "
                             f"MC hedef %{pt*100:.0f}, stop %{ps*100:.0f}, edge %{pg*100:.0f}")
        except Exception as exc:
            notes.append("kayitli p_target/p_stop okunamadi: " + str(exc)[:80])
        if reward > 0 and risk > 0:
            rr = reward / risk
            if rr < getattr(cfg, "open_signal_rr_min", cfg.market_rr_min):
                mult = 1.0 / rr if rr > 1e-9 else float("inf")
                notes.append(f"eski/acik sinyal bugunku RR kapisindan gecmezdi: RR {rr:.2f} < {getattr(cfg, 'open_signal_rr_min', cfg.market_rr_min):.2f} (~1 stop {mult:.1f} hedef)")
        if atr and atr > 0:
            pnl_atr = (price - ent) * sgn / atr
            if pnl_atr <= -getattr(cfg, "open_signal_adverse_atr_warn", 1.0):
                notes.append(f"aleyhte ilerleme {pnl_atr:+.1f} ATR; yeni emir degil, riskli acik sinyal izlemi")
        if notes:
            return "STEP4D ACIK-SINYAL RISK: " + "; ".join(notes)
    except Exception:
        return ""
    return ""


def plan_takip(symbol: str, snap: Snapshot, cfg: Config,
               d: Optional[Decision] = None) -> List[str]:
    """ONCEKI calistirmalarin pusu/aktif planlari SIMDI ne durumda? Satir listesi
    doner. Bu, pusu katmaninin COZUM adimidir (record_and_resolve'un plan esdegeri):
    ateslenen-ve-suren plan 'aktif'e tasinir (taze pusu onu EZEMEZ), sonuclanan
    plan 'hist'e yazilir (PUSU KARNESI = olculen isabet). plan_kur'dan ONCE cagrilir."""
    cs = snap.candles
    if not cs or cs[-1].close_ms is None:
        return []
    kayit = _plan_yukle().get(symbol) or {}
    pusu, aktif, hist = kayit.get("pusu", []), kayit.get("aktif", []), kayit.get("hist", [])

    def _ters_uyari(tip: str) -> str:
        # MOTOR-CELISKI UYARISI (3.tur, canli ETH bulgusu): aktif plan motorun GUNCEL
        # karariyla ters dusunce ekran iki zit oneriyi yorumsuz basiyordu (SHORT plani
        # 'makul bolgede' + KARAR: LONG). Acik-sinyal takibindeki 'TERS DONDU' dilinin
        # plan esdegeri: yalniz uyari, plan olcumu/karnesi DEGISMEZ.
        if d is None or d.karar not in ("LONG", "SHORT"):
            return ""
        if tip.startswith("LONG") != (d.karar == "LONG"):
            return f" | UYARI: motor su an {d.karar} diyor (TERS yon) -> bu plana YENI giris ADAYI DEGIL"
        return ""
    out: List[str] = []
    yeni_aktif: List[Dict] = []
    degisti = False
    bar_sp = (cs[-1].close_ms - cs[-2].close_ms) if len(cs) >= 2 and cs[-2].close_ms else 900_000
    # ── 0) CIFT-AKTIF TEKILLESTIRME (canli BTC kalintisi): S1 yeni cift OLUSUMUNU engeller
    # ama eski surumden store'a yazilmis ayni-seviye cift AKTIF kayitlari yasamaya devam
    # ediyordu (canli: @62796.2 x2). Ayni tip + tasima toleransi icindeki kopyalardan yalniz
    # EN ESKI (ilk ateslenen) tutulur; dusurulen kopya karneye HIC yazilmaz (cift sayim yok)
    # ve gorunur satirla raporlanir.
    if len(aktif) > 1:
        try:
            _atr_pt = atr_series(cs, cfg.atr_period)[-1]
        except Exception:
            _atr_pt = 0.0
        _tekil: List[Dict] = []
        _n_dus = 0
        for p in sorted(aktif, key=lambda q: q.get("fire_ms", 0)):
            _tol = (cfg.plan_tasima_atr * _atr_pt if _atr_pt > 0
                    else abs(p.get("seviye", 0.0)) * 1e-4)
            if any(q.get("tip") == p.get("tip")
                   and abs(q.get("seviye", 0.0) - p.get("seviye", 0.0)) <= _tol
                   for q in _tekil):
                _n_dus += 1
                continue
            _tekil.append(p)
        if _n_dus:
            aktif = _tekil
            degisti = True
            out.append(f"[TEKILLESTIRME] ayni seviyedeki {_n_dus} kopya AKTIF plan dusuruldu "
                       f"(eski surum kalintisi; ilk ateslenen korundu, karne cift sayilmaz)")
    # ── 1) AKTIF (onceden ateslenmis) planlar: hedef/stop/suruyor ──
    for p in aktif:
        try:
            sonra = [c for c in cs if c.close_ms and c.close_ms > p["fire_ms"]]
            ad = f"{p['tip']} @{_fmt(p['seviye'])} (giris ~{_fmt(p['entry'])})"
            olcumsuz = bool(sonra) and sonra[0].close_ms - p["fire_ms"] > 1.5 * bar_sp
            if olcumsuz:
                ad += " [ateslenme veri-penceresi disinda kaldi: ara donem OLCULEMEDI]"
            if not sonra:
                # SESSIZLIK-FIX (denetci R1: 'OZET pusu:N AKTIF! diyor ama blokta satir yok'):
                # ayni 15m bar icinde ikinci kosu -> degerlendirilecek yeni mum yok; bunu
                # GORUNUR soyle ki OZET ile sembol blogu celismesin.
                out.append(f"[AKTIF] {ad}: yeni 15m mum henuz kapanmadi -> degerlendirme "
                           f"SONRAKI kosuda (hedef {_fmt(p['hedef'])} / stop {_fmt(p['stop'])})")
                yeni_aktif.append(p)
                continue
            sonuc, prog = _aktif_degerlendir(p, sonra)
            if sonuc == "SURUYOR":
                gecen_mum = int((cs[-1].close_ms - p["fire_ms"]) / bar_sp) if bar_sp > 0 else 0
                if gecen_mum >= cfg.plan_aktif_max_bars:
                    # ZAMAN-ASIMI (denetci bulgusu): temassiz plan sonsuza dek 'AKTIF!' kalir,
                    # haftalar sonraki alakasiz temas karneyi kirletirdi -> kapat, karneye sayma.
                    degisti = True
                    hist.append({"tip": p["tip"], "seviye": p["seviye"], "sonuc": "ZAMAN-ASIMI",
                                 "ts": cs[-1].close_ms})
                    out.append(f"[ZAMAN ASIMI] {ad}: {gecen_mum} mum gecti, hedef/stop'a temas yok "
                               f"-> plan kapatildi (karneye SAYILMAZ; taze haritaya bak)")
                else:
                    gec = prog > cfg.plan_gec_prog
                    out.append(f"[AKTIF] {ad}: hedef yolunun %{int(prog*100)}'i "
                               f"(hedef {_fmt(p['hedef'])} / stop {_fmt(p['stop'])}) — "
                               + ("GIRMEDIYSEN GEC KALINDI: kovalamak yasak, yeni tetigi bekle"
                                  if gec else "giris hala makul bolgede (yolun ilk kismi)")
                               + _ters_uyari(p["tip"]))
                    yeni_aktif.append(p)
            else:
                degisti = True
                # F4 (FABLE6_5): maliyet-sonrasi NET R (plan sozlesmesindeki maliyetle)
                _nr_ak = None
                try:
                    _risk_ak = abs(float(p.get("entry", p["seviye"])) - float(p["stop"]))
                    _gross_ak = (abs(float(p["hedef"]) - float(p.get("entry", p["seviye"])))
                                 if sonuc == "HEDEF" else
                                 (-_risk_ak if sonuc == "STOP" else 0.0))
                    _, _nr_ak = _net_r(_gross_ak, p.get("maliyet"), _risk_ak)
                except (TypeError, ValueError, KeyError):
                    _nr_ak = None
                hist.append({"tip": p["tip"], "seviye": p["seviye"], "sonuc": sonuc,
                             "olcum": 0 if olcumsuz else 1, "ts": cs[-1].close_ms,
                             "net_r": (round(_nr_ak, 4) if _nr_ak is not None else None)})
                _s_txt = ("HEDEF VURULDU (+R)" if sonuc == "HEDEF" else
                          ("STOP (-1R)" if sonuc == "STOP" else
                           "GEC-KACTI (giris hedef otesi; karne-disi)"))
                if _nr_ak is not None and sonuc in ("HEDEF", "STOP"):
                    _s_txt += f" | NET(maliyet-sonrasi) {_nr_ak:+.2f}R"
                out.append(f"[SONUC] {ad} -> {_s_txt}"
                           + (" [ara donem OLCULEMEDI -> karneye sayilmadi]" if olcumsuz else ""))
        except Exception:
            # BOZUK KAYIT plani SILDIRMEZ (denetci bulgusu: sessiz silme+yutma yasak)
            yeni_aktif.append(p)
            out.append("[UYARI] bir AKTIF plan kaydi okunamadi (bozuk?) — plan KORUNDU, satiri atlandi")
            continue
    # ── 2) PUSU (kurulu tetikler): ateslendi/iptal/beklemede/sure-doldu ──
    # Sonuclanan/ateslenen pusu store'dan DUSER (yeni_pusu'ya girmez) — yoksa plan-tasima
    # bar_ms'i korudugu icin ayni tetik bir SONRAKI kosuda IKINCI kez ateslenirdi.
    yeni_pusu: List[Dict] = []
    for p in pusu:
        try:
            sonra = [c for c in cs if c.close_ms and c.close_ms > p["bar_ms"]]
            if not sonra:
                yeni_pusu.append(p)
                continue
            ev = _plan_degerlendir(p, sonra, cfg.sweep_reclaim_bars, cfg.signal_horizon_bars)
            kur_saat = time.strftime("%d.%m %H:%M", time.localtime(p["bar_ms"] / 1000.0))
            ad = f"{p['tip']} @{_fmt(p['seviye'])} (kurulus {kur_saat})"
            olcumsuz_p = sonra[0].close_ms - p["bar_ms"] > 1.5 * bar_sp
            if olcumsuz_p:
                ad += " [kurulus veri-penceresi disinda: ara donem OLCULEMEDI]"
            if ev["durum"] == "ATESLENDI":
                saat = time.strftime("%H:%M", time.localtime(sonra[ev["i"]].close_ms / 1000.0))
                if ev["sonuc"] == "SURUYOR":
                    degisti = True
                    gec = ev["prog"] > cfg.plan_gec_prog
                    yeni_aktif.append({"tip": p["tip"], "seviye": p["seviye"], "stop": p["stop"],
                                       "hedef": p["hedef"], "entry": ev["entry"],
                                       "maliyet": p.get("maliyet"),
                                       "fire_ms": sonra[ev["i"]].close_ms})
                    out.append(f"[ATESLENDI] {ad}: igne+geri alis {saat} mumunda GELDI, "
                               f"giris ~{_fmt(ev['entry'])} | hedef yolunun %{int(ev['prog']*100)}'i "
                               f"(hedef {_fmt(p['hedef'])} / stop {_fmt(p['stop'])}) — "
                               + ("GEC KALINDI: kovalamak yasak" if gec
                                  else "giris hala makul bolgede") + " | plan AKTIF olarak izlenecek"
                               + _ters_uyari(p["tip"]))
                    # F5 (FABLE6_5): teyit sonrasi CANLI fiyat/spread/slip ile giris onerisi
                    if not gec and not _ters_uyari(p["tip"]):
                        _cg_ln = _pusu_canli_giris_onerisi(symbol, snap, p, cfg)
                        if _cg_ln:
                            out.append(_cg_ln)
                elif ev["sonuc"] == "GEC-KACTI":
                    degisti = True
                    hist.append({"tip": p["tip"], "seviye": p["seviye"], "sonuc": "GEC-KACTI",
                                 "ts": cs[-1].close_ms})
                    out.append(f"[ATESLENDI->GEC-KACTI] {ad}: geri-alis kapanisi (~{_fmt(ev['entry'])}) "
                               f"hedefin ({_fmt(p['hedef'])}) OTESINDE geldi -> islem penceresi kacti; "
                               f"karneye SAYILMADI (kovalamak yasak)")
                else:
                    degisti = True
                    # F4 (FABLE6_5): pusu sonucu icin maliyet-sonrasi NET R
                    _nr_pu = None
                    try:
                        _risk_pu = abs(float(ev["entry"]) - float(p["stop"]))
                        _gross_pu = (float(ev["r"]) * _risk_pu if ev["sonuc"] == "HEDEF"
                                     else -_risk_pu)
                        _, _nr_pu = _net_r(_gross_pu, p.get("maliyet"), _risk_pu)
                    except (TypeError, ValueError, KeyError):
                        _nr_pu = None
                    hist.append({"tip": p["tip"], "seviye": p["seviye"], "sonuc": ev["sonuc"],
                                 "olcum": 0 if olcumsuz_p else 1, "ts": cs[-1].close_ms,
                                 "net_r": (round(_nr_pu, 4) if _nr_pu is not None else None)})
                    _ek = " [ara donem OLCULEMEDI -> karneye sayilmadi]" if olcumsuz_p else ""
                    if _nr_pu is not None:
                        _ek += f" | NET(maliyet-sonrasi) {_nr_pu:+.2f}R"
                    if ev["sonuc"] == "HEDEF":
                        out.append(f"[ATESLENDI->HEDEF] {ad}: tetik {saat} mumunda geldi, giris "
                                   f"~{_fmt(ev['entry'])} -> HEDEF {_fmt(p['hedef'])} VURULDU "
                                   f"(+{ev['r']:.1f}R). Sen yokken plan tamamlandi." + _ek)
                    else:
                        out.append(f"[ATESLENDI->STOP] {ad}: tetik {saat} mumunda geldi, giris "
                                   f"~{_fmt(ev['entry'])} -> STOP {_fmt(p['stop'])} kesildi (-1R). "
                                   f"Supurme payi yetmedi; yeni haritaya bak." + _ek)
            elif ev["durum"] == "IPTAL":
                degisti = True
                hist.append({"tip": p["tip"], "seviye": p["seviye"], "sonuc": "IPTAL",
                             "ts": cs[-1].close_ms})
                yon_txt = "altinda" if p["tip"].startswith("LONG") else "ustunde"
                dev = "asagi devam" if p["tip"].startswith("LONG") else "yukari devam"
                out.append(f"[IPTAL] {ad}: seviye {yon_txt} 15m KAPANIS(lar) geldi, geri alinmadi "
                           f"-> '{dev}' senaryosu gerceklesti; bu tepki plani OLDU")
            elif ev["durum"] == "SURE-DOLDU":
                degisti = True
                hist.append({"tip": p["tip"], "seviye": p["seviye"], "sonuc": "TETIKSIZ",
                             "ts": cs[-1].close_ms})
                out.append(f"[SURE DOLDU] {ad}: {ev['gecen']} mum gecti, tetik hic gelmedi "
                           f"(taze seviyelerle yeni pusu kurulacak)")
            else:
                yeni_pusu.append(p)
                # ETIKET-FIX (denetim): igne gelmis ama geri-alis penceresi yarimken
                # "seviye henuz test edilmedi" yaziyordu — olculen gercekle celisir.
                _tst = ("seviyeye IGNE GELDI, geri-alis penceresi henuz tamamlanmadi"
                        if ev.get("test") else "seviye henuz test edilmedi")
                out.append(f"[BEKLEMEDE] {ad}: {ev['gecen']} mum gecti, {_tst} "
                           f"(hedef {_fmt(p['hedef'])} / stop {_fmt(p['stop'])})")
        except Exception:
            yeni_pusu.append(p)
            out.append("[UYARI] bir PUSU kaydi okunamadi (bozuk?) — korunuyor; "
                       "sonraki kosuda taze pusu ile degisecek")
            continue
    # ── 3) kalici durum + OLCULEN karne satiri ──
    if degisti or len(yeni_aktif) != len(aktif) or len(yeni_pusu) != len(pusu):
        _plan_kaydet(symbol, {"pusu": yeni_pusu, "aktif": yeni_aktif,
                              "hist": hist[-cfg.plan_hist_cap:]})
    n_at, n_h, n_s = pusu_karne(symbol)
    if n_at > 0:
        out.append(f"PUSU KARNESI (olculen, {symbol}): ateslenen {n_at} tetik -> "
                   f"{n_h} HEDEF / {n_s} STOP (isabet %{round(100*n_h/max(1,n_at))})")
    return out


# ════════════════════════════════════════════════════════════════════════════
# ACIK SINYAL YASAM-DONGUSU TAKIBI (saat-basi kullanici icin)
# Soru: "onceki calistirmanin sinyali 10-30-60 dk sonra TERS donerse / GUC
# kaybederse / hedefe varmadan GERI donerse / hedefi DELIP gecerse — panel
# bunu bir SONRAKI calistirmada soyluyor mu?" Bu katman o cevabi verir:
# acik + yeni-cozulen sinyalleri fiyat yoluna ve GUNCEL motor gorusune karsi
# yeniden degerlendirir. record_and_resolve'dan SONRA cagrilmali (outcome
# guncel). YALNIZ raporlar; karara/loga DOKUNMAZ. Oneriler ADAY dilindedir.
# ════════════════════════════════════════════════════════════════════════════
def takip_raporu(symbol: str, snap: Snapshot, d: Decision,
                 st: Optional[Structure], cfg: Config) -> List[str]:
    """Onceki calistirmalarin sinyalleri SIMDI ne durumda? Satir listesi doner."""
    cs = snap.candles
    if not cs or cs[-1].close_ms is None:
        return []
    now_ms = cs[-1].close_ms
    price = cs[-1].close                  # kapali 15m fiyat (no-repaint)
    # STEP4H: ACIK sinyal takibinde "simdi" degeri icra gercegine yakin olmalidir.
    # Yeni sinyal uretimi kapali mumla yapilir; fakat acik pozisyonun lehte/aleyhte
    # durumu live mark varsa onunla raporlanir. Aksi halde kapali fiyat fallback olur.
    status_price = price
    try:
        _lp = getattr(snap, "live_price", None)
        if _lp is not None and math.isfinite(float(_lp)) and float(_lp) > 0:
            status_price = float(_lp)
    except Exception:
        status_price = price
    atr = st.atr if (st is not None and st.valid and st.atr > 0) else None
    recent_ms = now_ms - cfg.takip_goster_bar * 900_000
    _detay = os.environ.get("YON_DETAY", "") == "1"   # ADAY-oneri kuyruklari yalniz detayda
    # ESIK-BIRLIGI FIX (denetim): 'radar yone karsi' burada sabit 0.5 ile olculuyordu,
    # decide ise KALIBRELI flip esigi kullanir — ayni kavram iki katmanda farkli esikti.
    _flip_thr = reversal_calib(symbol, cfg)[0]
    lines: List[str] = []
    for r in _load_signals():
        if r.get("symbol") != symbol:
            continue
        bar = r.get("bar_ms")
        side = r.get("side")
        entry, tgt, inv = r.get("entry"), r.get("target"), r.get("inval")
        oc = r.get("outcome") or "OPEN"
        if bar is None or side not in ("LONG", "SHORT") or not entry or not tgt or not inv:
            continue
        if oc == "EXPIRED" or (oc != "OPEN" and bar < recent_ms):
            continue
        if bar >= now_ms:
            continue                     # bu calistirmada acilan sinyal KARAR bolumunde zaten var
        sgn = 1 if side == "LONG" else -1
        span_t = (tgt - entry) * sgn
        if span_t <= 0:
            continue
        age = int((now_ms - bar) // 900_000)
        after = [c for c in cs if c.close_ms is not None and c.close_ms > bar]
        if side == "LONG":
            best = max((c.high for c in after), default=price)
        else:
            best = min((c.low for c in after), default=price)
        prog_max = (best - entry) * sgn / span_t
        cur_prog = (status_price - entry) * sgn / span_t
        pnl_atr = ((status_price - entry) * sgn / atr) if atr else 0.0
        head = f"{side} @{_fmt(entry)} (hedef {_fmt(tgt)} / stop {_fmt(inv)}; {age} mum once)"
        if oc == "HIT":
            over = (price - tgt) * sgn
            if atr and over > cfg.takip_overshoot_atr * atr:
                lines.append(f"[SONUC] {head} -> HEDEF VURULDU ve DELIP GECTI "
                             f"(hedef otesi {over/atr:+.1f} ATR): momentum guclu; "
                             f"yeni seviye icin asagidaki GUNCEL KARAR'a bak")
            else:
                lines.append(f"[SONUC] {head} -> HEDEF VURULDU")
        elif oc == "STOP":
            lines.append(f"[SONUC] {head} -> STOP OLDU"
                         + (" [ayni mumda hedef+stop -> konservatif STOP]" if r.get("ambig") else "")
                         + ": plan ters dondu, gecersiz (motorun yeni gorusu icin asagidaki KARAR'a bak)")
        elif oc == "AMBIG":
            lines.append(f"[SONUC] {head} -> ayni mumda hedef+stop (belirsiz; sayilmadi)")
        elif oc in ("DIR_OK", "DIR_BAD"):
            lines.append(f"[SONUC] {head} -> SURE DOLDU: yon "
                         f"{'DOGRU cikti' if oc == 'DIR_OK' else 'YANLIS cikti'} ({pnl_atr:+.1f} ATR)")
        else:   # OPEN — yasayan plan: guncel motor gorusune karsi yeniden degerlendir
            durum: List[str] = []
            karsi = "SHORT" if side == "LONG" else "LONG"
            if d.karar == karsi:
                durum.append(f"TERS DONDU: motor SU AN {karsi} diyor -> bu plan GECERSIZ sayilmali")
            else:
                rev_against = (d.rev_sign != 0 and d.rev_sign != sgn
                               and getattr(d, "rev_str", 0.0) >= _flip_thr)
                ev_side = d.ev_long if side == "LONG" else d.ev_short
                span_s = (entry - inv) * sgn
                stop_yol = ((entry - status_price) * sgn / span_s) if span_s > 0 else 0.0
                if prog_max >= cfg.takip_yakin_prog and cur_prog <= cfg.takip_dondu_prog:
                    # HUKUM-MODU FIX (denetim): ADAY-oneri kuyruklari yalniz DETAY'da;
                    # hukum modunda yalniz OLCULEN durum tespiti kalir (acik-uclu dil yok).
                    durum.append(f"hedefin %{int(prog_max*100)}'ine ULASIP GERI DONDU -> guc kaybi"
                                 + ("; cikis veya stop-girise dusunulebilir (ADAY)"
                                    if _detay else " (olculen geri-donus)"))
                elif stop_yol >= cfg.takip_stop_yakin:
                    durum.append(f"STOPA YAKLASIYOR (stop yolunun %{int(stop_yol*100)}'i): plan zayif"
                                 + ("; kucultme/cikis dusunulebilir (ADAY)" if _detay else ""))
                elif rev_against:
                    durum.append("ZAYIFLADI: tick radari su an bu yonun TERSINI isaret ediyor")
                elif (d.ev_long != 0.0 or d.ev_short != 0.0) and ev_side < 0:
                    durum.append(f"GUC KAYBI: {side} kenari su an negatif (EV=%{ev_side*100:.0f}·ATR)")
                elif d.karar == side:
                    durum.append("GECERLI: motor ayni yonu hala teyit ediyor")
                else:
                    durum.append("izleniyor: motor su an BEKLE'de (plan bozulmadi ama teyit de yok)")
                if cur_prog >= cfg.takip_be_prog and prog_max < 1.0:
                    durum.append("stop GIRISE cekilebilir (breakeven korumasi, ADAY)" if _detay
                                 else f"breakeven esigi gecildi (yol %{int(cur_prog*100)} >= "
                                      f"%{int(cfg.takip_be_prog*100)})")
                kalan = cfg.signal_horizon_bars - age
                if kalan <= 4:
                    durum.append(f"sure dolmak uzere ({max(kalan, 0)} mum kaldi)")
                _audit = open_signal_risk_audit(r, status_price, atr, cfg)
                if _audit:
                    durum.append(_audit)
            lines.append(f"[ACIK] {head} | simdi {_fmt(status_price)} ({pnl_atr:+.1f} ATR, "
                         f"yol %{int(_clip(cur_prog, -9, 9)*100)}) | " + "; ".join(durum))
    return lines


def _fmt(x):
    if x is None:
        return "?"
    ax = abs(x)
    if ax >= 1000:
        return f"{x:.1f}"
    if ax >= 100:
        return f"{x:.2f}"
    if ax >= 1:
        return f"{x:.4f}"
    if ax >= 0.01:
        return f"{x:.5f}"
    return f"{x:.7f}"


def giris_zamanlama(symbol: str, snap: Snapshot, st: Optional[Structure],
                    d: Decision, cfg: Config) -> str:
    """S2: 'tepeden red -> SIMDI market short mu, yoksa pusu ile mi' belirsizligini AYRI
    bir satirla acikca soyler. YENI KARAR/YON URETMEZ — d.karar (market: tum teyit/kalite/
    veto kapilari GECTI demektir -> SIMDI MARKET) ile store'daki bekleyen pusu okunur.
    Market karari zaten teyide-baglidir; pusu ise teyit BEKLER (igne+supurme+kapanmis-15m
    geri-alis). Bos str = satir yok."""
    if d.karar in ("LONG", "SHORT") and d.entry and d.target and d.stop:
        return (f"GIRIS ZAMANLAMASI: red/onay TEYITLI -> SIMDI MARKET {d.karar} @{_fmt(d.entry)} "
                f"(canli fiyatla; hedef {_fmt(d.target)} / stop {_fmt(d.stop)})")
    # BEKLE: o sembolde bekleyen pusu var mi? (islem_plani ile AYNI store okumasi)
    yon = None
    try:
        kyt = _plan_yukle().get(symbol) or {}
        tipler = [str(p.get("tip", "")) for p in kyt.get("pusu", [])]
        if any(t.startswith("LONG") for t in tipler):
            yon = "LONG"
        elif any(t.startswith("SHORT") for t in tipler):
            yon = "SHORT"
    except Exception:
        yon = None
    if yon is None and getattr(d, "scen_side", None) in ("LONG", "SHORT"):
        yon = d.scen_side
    if yon in ("LONG", "SHORT"):
        return (f"GIRIS ZAMANLAMASI: teyit YOK -> PUSU bekle ({yon} kenari); seviye test + "
                f"supurme/fitil + kapanmis-15m geri-alis TEYIDINDE market (kor market YOK)")
    return "GIRIS ZAMANLAMASI: uygun kenar yok -> islem yok (BEKLE)"


def islem_plani(symbol, snap: Snapshot, st: Optional[Structure], d: Decision,
                micros: List[MicroScen], cfg: Config) -> List[str]:
    """NET ISLEM PLANI (kullanici direktifi + ekran goruntuleri):
    - Fiyat UCTA + kenar VARSA -> 'MARKET GIR: LONG/SHORT' (giris/hedef/stop, canli MC hedef %).
    - Anlik yon/giris yoksa -> PUSU/LIMIT: LONG-gir (alt) ve SHORT-gir (ust) seviyeleri +
      stop/hedef + CANLI MC ilk-temas: once %X ust mu %Y alt mi vurulur (hangi limit once tetiklenir).
    Tum sayilar SU ANKI barin verisinden; gecmis kalibrasyon DEGIL. Seviye kaynagi net_okuma/
    plan_kur ile BIREBIR ayni (_tetik_seviyeleri) -> celiski olmaz. Karari DEGISTIRMEZ."""
    L: List[str] = []
    if st is None or not st.valid or st.atr <= 0:
        return L
    a, price = st.atr, st.price
    try:
        ust, alt, hedef_long, hedef_short, pay_lo, pay_hi, _ = \
            _tetik_seviyeleri(snap, st, micros, cfg)
    except Exception:
        return L
    dar = (ust - alt) < cfg.min_target_atr * a
    _pusu_live_block, _pusu_live_why = live_price_gap_kapisi(snap, st, cfg, kind="pusu")
    # ── STORE SOZLESMESI ESAS (canli bulgu F1/F2, 06.07 14:14 kosusu) ──
    # F1: tasima eski sozlesmeyi korurken ekran TAZE hesabi basiyordu (SOL: ekran
    #     stop 81.1667/hedef 80.00 vs store sozlesmesi 81.1995/80.11) -> kullanici
    #     yanlis emir koyar, makine baska sozlesmeyi olcer. F2: kenarda ATESLENMIS
    #     AKTIF plan varken ayni kenara yeni limit oneriliyordu (DOGE SHORT) ->
    #     cift maruziyet (S1 korumasinin ekran karsiligi yoktu).
    # Kural: pusu sozlesmesi varsa ONU bas; pusu yok ama AKTIF varsa 'YENI LIMIT
    # KOYMA' de; ikisi de yoksa taze hesap (yedek). Ilk-temas da BASILAN seviyede.
    p_l = p_s = a_l = a_s = None
    try:
        _kyt = _plan_yukle().get(symbol) or {}
        for q in _kyt.get("pusu", []):
            if str(q.get("tip", "")).startswith("LONG"):
                p_l = q
            elif str(q.get("tip", "")).startswith("SHORT"):
                p_s = q
        for q in _kyt.get("aktif", []):
            if str(q.get("tip", "")).startswith("LONG"):
                a_l = q
            elif str(q.get("tip", "")).startswith("SHORT"):
                a_s = q
    except Exception:
        p_l = p_s = a_l = a_s = None
    try:
        lvl_alt = float(p_l["seviye"]) if p_l else (float(a_l["seviye"]) if a_l else alt)
        lvl_ust = float(p_s["seviye"]) if p_s else (float(a_s["seviye"]) if a_s else ust)
    except Exception:
        lvl_alt, lvl_ust = alt, ust
    L.append("== ISLEM PLANI (NET; CANLI — yalniz bu barin verisi, kehanet degil) ==")
    if d.karar in ("LONG", "SHORT") and d.entry and d.target and d.stop:
        pt = int(round(d.p_target * 100))
        L.append(f"-> MARKET GIR: {d.karar}{'  [ZAYIF]' if d.weak else ''}  @{_fmt(d.entry)}"
                 f"  |  HEDEF {_fmt(d.target)}  |  STOP {_fmt(d.stop)}")
        _rr_tag = ("komisyon/spread/slip/gecikme/kismi-dolum+funding-ust-siniri-dahil" if d.funding_bound_atr > 0
                   else "komisyon/spread/slip/gecikme/kismi-dolum-dahil; funding-haric")
        L.append(f"   canli MC: hedef once vurma %{pt} / stop once vurma %{d.reversal_risk}  "
                 f"(RR {_rr_tag} {d.rr:.2f})")
        # F8 (FABLE6_5): giris bandi + ayrik maliyet/gecersizlik bilgisi kartta da
        _b_ip8 = cfg.entry_buffer_atr * a
        L.append(f"   giris bandi {_fmt(d.entry - _b_ip8)}-{_fmt(d.entry + _b_ip8)}  |  "
                 f"gecersizlik: stop otesinde 15m KAPANIS  |  maliyet ~{_fmt(getattr(d, 'cost_abs', 0.0))}")
    else:
        if _pusu_live_block:
            L.append(f"-> MARKET GIR YOK (su an kenar yok: {(d.sebep or '')[:70]})  ->  "
                     f"PUSU/LIMIT KURULMAZ: {_pusu_live_why}")
        else:
            L.append(f"-> MARKET GIR YOK (su an kenar yok: {(d.sebep or '')[:70]})  ->  "
                     + ("PUSU KURULMAZ (bant dar):" if dar else "PUSU/LIMIT kur:"))
        # Ilk-temas olasiligi TAM BASILAN seviyelerde olculur: decide'in MC yollari
        # yeniden kullanilir (ek maliyet yok). Havuz seviyesi bant ucundan farkliysa
        # bant-ucu olasiligini basmak yazilan seviyeyle CELISIRDI (denetim: madde-1).
        _pu = _pl = _pn = None
        if d.plan:
            try:
                _pp = d.plan.get("paths")
                _pr0 = float(d.plan.get("price0") or 0.0)
                if _pp and _pr0 > 0:
                    _u2, _a2, _n2 = mc_ilk_temas(
                        _pp, _pr0, lvl_ust, lvl_alt,
                        wick_sig=float(d.plan.get("wick_sig", 0.0) or 0.0),
                        rng=(random.Random(int(d.plan["it_seed"]))
                             if d.plan.get("it_seed") is not None else None))
                else:   # yol tasinamadiysa bant-ucu sayilari (kaynagi acikca yazilir)
                    _u2, _a2, _n2 = (d.plan.get("p_ust", 0.0), d.plan.get("p_alt", 0.0),
                                     d.plan.get("p_yok", 1.0))
                _pu, _pl, _pn = (int(round(_u2 * 100)), int(round(_a2 * 100)),
                                 int(round(_n2 * 100)))
            except Exception:
                _pu = None
        if _pu is not None:
            hangi = ("ONCE UST daha olasi (emir onerisi degil; kurulu kenar varsa tetik sirasi)"
                     if _pu > _pl else
                     ("ONCE ALT daha olasi (emir onerisi degil; kurulu kenar varsa tetik sirasi)"
                      if _pl > _pu else "iki taraf basabas"))
            L.append(f"   canli MC ilk-temas (ufuk {cfg.horizon} mum; {_fmt(lvl_ust)}/{_fmt(lvl_alt)} "
                     f"seviyelerinde): once %{_pu} UST / %{_pl} ALT"
                     + (f" / %{_pn} ikisine de degmez" if _pn > 0 else "") + f"  ->  {hangi}")
        else:
            L.append("   (canli MC ilk-temas uretilemedi: veri bayat/yetersiz)")
    if _pusu_live_block:
        L.append("   !! CANLI-FIYAT/PUSU KAPISI: yeni bekleyen emir yazma; mevcut eski emir varsa sadece panelde izlenir/iptal edilir.")
    elif dar:
        L.append(f"   !! BANT DAR ({(ust - alt) / a:.2f} ATR < {cfg.min_target_atr:.1f} ATR): "
                 f"kenar-tepki limiti KURULMAZ; 15m KAPANISLA kirilim teyidi bekle.")
    else:
        def _saat_ip(ms):
            try:
                return time.strftime("%H:%M", time.localtime(int(ms) / 1000.0))
            except Exception:
                return "?"
        # LONG kenari: sozlesme > aktif-uyarisi > taze hesap
        if p_l:
            try:
                L.append(f"   > LONG-gir  (ALT {_fmt(float(p_l['seviye']))}): buraya igne + geri alis -> "
                         f"LIMIT AL  |  stop {_fmt(float(p_l['stop']))}  |  hedef {_fmt(float(p_l['hedef']))}"
                         f"  [sozlesme {_saat_ip(p_l.get('bar_ms', 0))} kurulusundan]"
                         + (f"  (ayni kenarda AKTIF plan da izleniyor @{_fmt(float(a_l['seviye']))})"
                            if a_l else ""))
            except Exception:
                p_l = None
        _tdir_ip, _tstrong_ip = htf_trend(snap.htf, cfg)
        if not p_l and a_l:
            L.append(f"   > LONG kenari: ZATEN ATESLENMIS PLAN AKTIF @{_fmt(float(a_l.get('seviye', 0.0)))} "
                     f"(giris ~{_fmt(float(a_l.get('entry', 0.0)))}) -> YENI LIMIT KOYMA (cift maruziyet); "
                     f"takip 'KOSULLU PLAN TAKIBI'nde")
        elif not p_l and not a_l and _tstrong_ip and _tdir_ip < 0:
            # trend-yonu filtresi (plan_kur ile AYNI kosul): ekran kurulmayan plani oneremez
            L.append(f"   > LONG kenari (ALT {_fmt(alt)}): PUSU KURULMADI — guclu 4s ASAGI trendine "
                     f"KARSI kenar-tepki (olculen karsi-trend karnesi zayif); kapanisla donus "
                     f"teyidi gelmeden limit koyma")
        elif not p_l and not a_l and getattr(cfg, "pusu_tek_kenar", True) and (p_s or a_s):
            # F2 (FABLE6_5): tek-kenar kurali — secilmeyen kenar icin taze oneri URETILMEZ
            L.append(f"   > LONG kenari (ALT {_fmt(alt)}): PUSU KURULMADI — F2 tek-kenar kurali "
                     f"(bu kosuda secilen kenar SHORT-TEPKI; iki zit bekleyen plan kurulmaz)")
        elif not p_l and not a_l:
            _blok_l, _neden_l = pusu_karne_riskli(symbol, "LONG-TEPKI", cfg)
            if _blok_l:
                L.append(f"   > LONG kenari (ALT {_fmt(alt)}): PUSU KURULMADI — {_neden_l}")
            else:
                L.append(f"   > LONG-gir  (ALT {_fmt(alt)}): buraya igne + geri alis -> LIMIT AL  |  "
                         f"stop {_fmt(alt - pay_lo)}  |  hedef {_fmt(hedef_long)}")
        # SHORT kenari (ayna)
        if p_s:
            try:
                L.append(f"   > SHORT-gir (UST {_fmt(float(p_s['seviye']))}): buraya igne + geri donus -> "
                         f"LIMIT SAT  |  stop {_fmt(float(p_s['stop']))}  |  hedef {_fmt(float(p_s['hedef']))}"
                         f"  [sozlesme {_saat_ip(p_s.get('bar_ms', 0))} kurulusundan]"
                         + (f"  (ayni kenarda AKTIF plan da izleniyor @{_fmt(float(a_s['seviye']))})"
                            if a_s else ""))
            except Exception:
                p_s = None
        if not p_s and a_s:
            L.append(f"   > SHORT kenari: ZATEN ATESLENMIS PLAN AKTIF @{_fmt(float(a_s.get('seviye', 0.0)))} "
                     f"(giris ~{_fmt(float(a_s.get('entry', 0.0)))}) -> YENI LIMIT KOYMA (cift maruziyet); "
                     f"takip 'KOSULLU PLAN TAKIBI'nde")
        elif not p_s and not a_s and _tstrong_ip and _tdir_ip > 0:
            L.append(f"   > SHORT kenari (UST {_fmt(ust)}): PUSU KURULMADI — guclu 4s YUKARI trendine "
                     f"KARSI kenar-tepki (olculen karsi-trend karnesi zayif); kapanisla donus "
                     f"teyidi gelmeden limit koyma")
        elif not p_s and not a_s and getattr(cfg, "pusu_tek_kenar", True) and (p_l or a_l):
            # F2 (FABLE6_5): tek-kenar kurali — secilmeyen kenar icin taze oneri URETILMEZ
            L.append(f"   > SHORT kenari (UST {_fmt(ust)}): PUSU KURULMADI — F2 tek-kenar kurali "
                     f"(bu kosuda secilen kenar LONG-TEPKI; iki zit bekleyen plan kurulmaz)")
        elif not p_s and not a_s:
            _blok_s, _neden_s = pusu_karne_riskli(symbol, "SHORT-TEPKI", cfg)
            if _blok_s:
                L.append(f"   > SHORT kenari (UST {_fmt(ust)}): PUSU KURULMADI — {_neden_s}")
            else:
                L.append(f"   > SHORT-gir (UST {_fmt(ust)}): buraya igne + geri donus -> LIMIT SAT  |  "
                         f"stop {_fmt(ust + pay_hi)}  |  hedef {_fmt(hedef_short)}")
        L.append("   NOT: tetik 15m KAPANISLA teyit ister; limit fiyati bilerek seviyenin ICINE koy "
                 "(igne supurmesi paya dahil).")
    return L


_SADE_HOLDER: Dict[str, List[str]] = {}   # render -> run: kosu-sonu SADE OZET kartlari
_NIHAI_HOLDER: Dict[str, List[str]] = {}  # render -> run: kosu-sonu NIHAI RAPOR (zorunlu format)


def sade_ozet_karti(symbol, snap: Snapshot, st: Optional[Structure], d: Decision,
                    cfg: Config) -> List[str]:
    """SADE OZET (kullanici isteri: 'ciktilari senin gibi okuyamiyorum'): her kosuda
    duruma gore yeniden yazilan, teknik-dil-siz eylem karti. YENI SAYI URETMEZ —
    karar (d), store'daki pusu/aktif SOZLESMELERI ve ust-zaman trendi okunur; ust
    bloklarla AYNI kaynak = celiski uretemez. run() en sonda basar (telefonda
    kaydirmadan ilk gorunen yer)."""
    if st is None or not st.valid or st.atr <= 0:
        return [f"{symbol}: veri yetersiz — bu kosuda okuma yok"]
    L: List[str] = []
    def _sade_error(tag: str, exc: Exception) -> None:
        msg = f"  [UYARI] {tag} hesaplanamadi: {str(exc)[:80]}"
        L.append(msg)
        sys.stderr.write(msg.strip() + "\n")
    yon_tr = {1: "YUKARI", -1: "ASAGI", 0: "YATAY/belirsiz"}
    hdir, hstrong = htf_trend(snap.htf, cfg)
    try:
        aile = rejim_ailesi(snap, cfg)
    except Exception as exc:
        aile = "?"
        _sade_error("rejim ailesi", exc)
    try:
        _scn = classify_scenario(snap, st, cfg)
        scen_txt = scenario_turkce(_scn).split("  ·  ")[0]
    except Exception as exc:
        scen_txt = "belirsiz"
        _sade_error("senaryo metni", exc)
    _lp_txt = ""
    try:
        if getattr(snap, "live_price", None):
            _lp_txt = f" | live-mark {_fmt(float(snap.live_price))}"
    except Exception as exc:
        _lp_txt = ""
        _sade_error("live fiyat metni", exc)
    L.append(f"{symbol}  (kapali fiyat {_fmt(st.price)}{_lp_txt})")
    L.append(f"  TREND     : 4 saatlik {yon_tr[hdir]}{' (guclu)' if hstrong else ''}"
             f" | genel faz: {aile}   (KARAR 4 saatlik + 15 dakikaya gore verilir)")
    # Opus-11: ' x ' ayraci carpi gibi okunuyor -> ' + '
    L.append(f"  SENARYO   : {scen_txt.replace(' x ', ' + ')}  (baglam/etiket; karar kapisi degil)")
    # ── MARKET hukmu: KARAR blogunun sade cevirisi (ayni d alanlari -> ayni sayilar) ──
    market_var = d.karar in ("LONG", "SHORT") and d.entry and d.target and d.stop
    if market_var:
        _pt_i = int(round(d.p_target * 100))
        _ps_i = int(d.reversal_risk)
        _py_i = max(0, 100 - _pt_i - _ps_i)          # Opus-2: uc kalem 100'e tamamlanir
        _rew = abs(d.target - d.entry)
        _rsk = abs(d.stop - d.entry)
        L.append(f"  MARKET YON: SIMDI {d.karar} GIRILEBILIR{' [ZAYIF]' if d.weak else ''}")
        L.append(f"  MARKET    : giris {_fmt(d.entry)} | hedef {_fmt(d.target)} | stop {_fmt(d.stop)}")
        # Opus-9: yuzdenin kaynagi ve 'garanti degil' etiketi satirin ICINDE
        L.append(f"              canli olcum (bu barin simulasyonu; gecmis isabet DEGIL, garanti"
                 f" DEGIL): hedef %{_pt_i} / stop %{_ps_i} / ikisi de degmez-sure dolar %{_py_i}")
        # Opus-5: risk/odul GIZLI kalmasin — mesafeler ve ters oran acik yazilir
        if _rew > 0 and d.rr < 0.35:
            _oran = _rsk / _rew
            L.append(f"              DIKKAT: kar YAKIN ({_fmt(_rew)} mesafe), stop UZAK"
                     f" ({_fmt(_rsk)} mesafe) ~ 1'e {_oran:.0f} ters -> tek stop"
                     f" ~{max(1, int(round(_oran)))} kazanci siler; boyut kucuk")
        # F11 (YÖNTEM): p yerine E_net/Kelly — sade kartta da R-birimi beklenti gorunur
        try:
            _bek_so = _yontem_beklenti_satiri(d, cfg, prefix="              ")
            if _bek_so:
                L.append(_bek_so)
        except Exception as exc:
            _sade_error("yontem beklenti", exc)
    else:
        L.append(f"  MARKET YON: GIRIS YOK — {(d.sebep or 'kenar yok')[:64]}")
    # S2: SIMDI-market mi PUSU-bekle mi ayrimi (sade dil)
    try:
        L.append("  ZAMANLAMA : " + giris_zamanlama(symbol, snap, st, d, cfg)
                 .replace("GIRIS ZAMANLAMASI: ", ""))
    except Exception as exc:
        _sade_error("giris zamanlama", exc)
    # ── PUSU/AKTIF: store sozlesmesi esas (islem_plani ile AYNI kaynak) ──
    p_l = p_s = a_l = a_s = None
    try:
        _kk = _plan_yukle().get(symbol) or {}
        for q in _kk.get("pusu", []):
            if str(q.get("tip", "")).startswith("LONG"):
                p_l = q
            elif str(q.get("tip", "")).startswith("SHORT"):
                p_s = q
        for q in _kk.get("aktif", []):
            if str(q.get("tip", "")).startswith("LONG"):
                a_l = q
            elif str(q.get("tip", "")).startswith("SHORT"):
                a_s = q
    except Exception as exc:
        _sade_error("plan store", exc)
    # ONCELIK: once hangi seviye vurulur (yalniz market yokken anlamli; ayni MC yollari)
    if not market_var and d.plan:
        try:
            _pp = d.plan.get("paths")
            _pr0 = float(d.plan.get("price0") or 0.0)
            _lu = float(p_s["seviye"]) if p_s else (float(a_s["seviye"]) if a_s else st.range_high)
            _la = float(p_l["seviye"]) if p_l else (float(a_l["seviye"]) if a_l else st.range_low)
            if _pp and _pr0 > 0 and _lu > _la:
                _u9, _a9, _ = mc_ilk_temas(
                    _pp, _pr0, _lu, _la,
                    wick_sig=float(d.plan.get("wick_sig", 0.0) or 0.0),
                    rng=(random.Random(int(d.plan["it_seed"]))
                         if d.plan.get("it_seed") is not None else None))
                _once = ("UST (satis tarafi) once" if _u9 > _a9 else
                         ("ALT (alis tarafi) once" if _a9 > _u9 else "basabas"))
                L.append(f"  ONCELIK   : once %{int(round(_u9 * 100))} ustteki /"
                         f" %{int(round(_a9 * 100))} alttaki seviye vurulur -> {_once}")
        except Exception as exc:
            _sade_error("ilk-temas onceligi", exc)

    def _saat_so(ms):
        try:
            return time.strftime("%H:%M", time.localtime(int(ms) / 1000.0))
        except Exception:
            return "?"
    _tdir_so, _tstr_so = htf_trend(snap.htf, cfg)
    _pusu_live_block_so, _pusu_live_why_so = (False, "")
    try:
        if st is not None and getattr(st, "valid", False):
            _pusu_live_block_so, _pusu_live_why_so = live_price_gap_kapisi(snap, st, cfg, kind="pusu")
    except Exception as exc:
        _pusu_live_block_so, _pusu_live_why_so = (False, "")
        _sade_error("pusu live-gap kapisi", exc)
    if _pusu_live_block_so and getattr(cfg, "pusu_live_gap_blocks_existing_advice", True):
        p_l = p_s = None
    # Opus-6: 'geri donerse' bir limit emrinin bekleyebilecegi sey degil -> uygulanabilir
    # talimat: emir SIMDI konur; teyit/IPTAL isini panel yapar, IPTAL derse emir GERI cekilir.
    # Opus-10: alan sirasi her yerde ayni (hedef | stop). Opus-1: saat = plan KURULUS saati.
    if p_l:
        try:
            L.append(f"  PUSU AL   : SIMDI konabilir -> {_fmt(float(p_l['seviye']))} fiyatina AL"
                     f" limit emri | hedef {_fmt(float(p_l['hedef']))} | stop"
                     f" {_fmt(float(p_l['stop']))} (plan kurulus saati {_saat_so(p_l.get('bar_ms', 0))})")
        except Exception as exc:
            p_l = None
            _sade_error("LONG pusu satiri", exc)
    if _pusu_live_block_so:
        L.append(f"  PUSU AL   : KOYMA — {_pusu_live_why_so}")
    elif not p_l and a_l:
        L.append(f"  PUSU AL   : KOYMA — LONG tarafinda ateslenmis plan zaten var"
                 f" (giris ~{_fmt(float(a_l.get('entry', 0.0)))}); panel izliyor")
    elif not p_l and not a_l and _tstr_so and _tdir_so < 0:
        L.append("  PUSU AL   : kurulmadi — dusus trendine KARSI islem olurdu; bu taraftan uzak dur")
    elif not p_l and not a_l:
        L.append("  PUSU AL   : yok (uygun kenar yok / bant dar / F2 tek-kenar kurali)")
    if _pusu_live_block_so:
        L.append(f"  PUSU SAT  : KOYMA — {_pusu_live_why_so}")
    elif p_s:
        try:
            L.append(f"  PUSU SAT  : SIMDI konabilir -> {_fmt(float(p_s['seviye']))} fiyatina SAT"
                     f" limit emri | hedef {_fmt(float(p_s['hedef']))} | stop"
                     f" {_fmt(float(p_s['stop']))} (plan kurulus saati {_saat_so(p_s.get('bar_ms', 0))})")
        except Exception as exc:
            p_s = None
            _sade_error("SHORT pusu satiri", exc)
    if not p_s and a_s:
        L.append(f"  PUSU SAT  : KOYMA — SHORT tarafinda ateslenmis plan zaten var"
                 f" (giris ~{_fmt(float(a_s.get('entry', 0.0)))}); panel izliyor")
    elif not p_s and not a_s and _tstr_so and _tdir_so > 0:
        L.append("  PUSU SAT  : kurulmadi — yukselis trendine KARSI islem olurdu; bu taraftan uzak dur")
    elif not p_s and not a_s:
        L.append("  PUSU SAT  : yok (uygun kenar yok / bant dar / F2 tek-kenar kurali)")
    if p_l or p_s:
        L.append("              (panel tetigi 15dk KAPANISLA teyit eder ve her kosuda durum bildirir;"
                 " panel 'IPTAL' derse emri GERI CEK)")
    # Opus-4: market islemi ile pusu ARDISIK senaryodur, ayni anda iki pozisyon degil —
    # pusu seviyesine fiyat ancak market stopu gectikten sonra ulasabiliyorsa acikca soyle.
    try:
        if market_var and d.karar == "SHORT" and p_s and float(p_s["seviye"]) >= float(d.stop):
            L.append(f"  SIRA NOTU : ayni anda iki pozisyon DEGIL — fiyat {_fmt(float(p_s['seviye']))}"
                     f" seviyesine ancak market SHORT stop olduktan sonra ulasir;"
                     f" PUSU SAT ikinci sanstir")
        elif market_var and d.karar == "LONG" and p_l and float(p_l["seviye"]) <= float(d.stop):
            L.append(f"  SIRA NOTU : ayni anda iki pozisyon DEGIL — fiyat {_fmt(float(p_l['seviye']))}"
                     f" seviyesine ancak market LONG stop olduktan sonra ulasir;"
                     f" PUSU AL ikinci sanstir")
    except Exception as exc:
        _sade_error("market/pusu sira notu", exc)
    # ── ACIK ISLEMLER (bu kosuda acilan haric — o zaten MARKET satiri) ──
    try:
        _now_ms = snap.candles[-1].close_ms
        _opens = [r for r in _load_signals()
                  if r.get("symbol") == symbol and r.get("outcome") in (None, "OPEN")
                  and r.get("side") in ("LONG", "SHORT") and r.get("bar_ms") != _now_ms
                  and r.get("entry") and r.get("target") and r.get("inval")]
        for r in _opens[-2:]:
            _pa = (st.price - float(r["entry"])) * (1 if r["side"] == "LONG" else -1) / st.atr
            L.append(f"  ACIK ISLEM: {r['side']} @{_fmt(float(r['entry']))} su an {_pa:+.1f} ATR "
                     f"{'LEHTE' if _pa >= 0 else 'ALEYHTE'} | hedef {_fmt(float(r['target']))}"
                     f" / stop {_fmt(float(r['inval']))}")
            _aud = open_signal_risk_audit(r, st.price, st.atr, cfg)
            if _aud:
                L.append("              " + _aud)
    except Exception as exc:
        _sade_error("acik islem ozeti", exc)
    # ── TEK CUMLE HUKUM ──
    yap: List[str] = []
    if market_var:
        yap.append(f"kucuk boyutla {d.karar} girilebilir (stop {_fmt(d.stop)} SART)")
    if p_s:
        yap.append(f"{_fmt(float(p_s['seviye']))} seviyesine SAT limiti kurulabilir")
    if p_l:
        yap.append(f"{_fmt(float(p_l['seviye']))} seviyesine AL limiti kurulabilir")
    if not yap:
        yap.append("bu sembolde yeni emir YOK; bekle ve izle")
    L.append("  NE YAPMALI: " + "; ".join(yap) + ". Tetiklenmeyen limit = islem yok.")
    return L


def nihai_rapor_karti(symbol, snap: Snapshot, st: Optional[Structure], d: Decision,
                      cfg: Config) -> List[str]:
    """NIHAI RAPOR (kullanici nihai_uygulama_sirasi BOLUM 10+17+18): 9 zorunlu bolum +
    kesin NET SONUC cumlesi ('Market emirle long/short uygundur.' / 'Market emir uygun
    değildir; limit pusu planı aşağıdadır.'). TASARIM KURALI (H18): kart YENI SAYI
    URETMEZ — yalniz d (bu kosunun karari), store sozlesmeleri (plan_takip/plan_kur
    SONRASI ayni okuma), olculen karneler ve snap veri-envanteri okunur; ust bloklarla
    celisemez. run() en sonda basar."""
    L: List[str] = []
    def _nihai_error(tag: str, exc: Exception) -> None:
        msg = f"   [UYARI] {tag} hesaplanamadi: {str(exc)[:80]}"
        L.append(msg)
        sys.stderr.write(msg.strip() + "\n")
    if st is None or not st.valid or st.atr <= 0:
        return [f"{symbol}: NIHAI RAPOR uretilemedi (veri yetersiz)",
                "9. NET SONUC", "   Karar kanitlanamadi, islem yok."]
    L.append("== NIHAI RAPOR (zorunlu format; kaynak: ayni kosunun d/store olcumleri) ==")
    L.append(f"[{symbol}]  fiyat {_fmt(st.price)}  ATR {_fmt(st.atr)}")
    market_var = d.karar in ("LONG", "SHORT") and d.entry and d.target and d.stop
    # store sozlesmeleri: islem_plani/sade_ozet ile AYNI okuma (H18 — ekran=sozlesme)
    p_l = p_s = a_l = a_s = None
    try:
        _kn = _plan_yukle().get(symbol) or {}
        for q in _kn.get("pusu", []):
            if str(q.get("tip", "")).startswith("LONG"):
                p_l = q
            elif str(q.get("tip", "")).startswith("SHORT"):
                p_s = q
        for q in _kn.get("aktif", []):
            if str(q.get("tip", "")).startswith("LONG"):
                a_l = q
            elif str(q.get("tip", "")).startswith("SHORT"):
                a_s = q
    except Exception as exc:
        _nihai_error("plan store", exc)
    # ── 1. ONCEKI PLAN DURUMU (B17: devam/iptal/guncelleme + eski planla celiski) ──
    L.append("1. ONCEKI PLAN DURUMU")
    _onceki = 0
    try:
        _now_ms = snap.candles[-1].close_ms
        for r in [x for x in _load_signals()
                  if x.get("symbol") == symbol and x.get("outcome") in (None, "OPEN")
                  and x.get("side") in ("LONG", "SHORT") and x.get("bar_ms") != _now_ms
                  and x.get("entry") and x.get("target") and x.get("inval")][-2:]:
            _onceki += 1
            _pa = (st.price - float(r["entry"])) * (1 if r["side"] == "LONG" else -1) / st.atr
            if d.karar in ("LONG", "SHORT") and d.karar != r["side"]:
                _hkm = "IPTAL ADAYI (motor su an TERS yonde) — ESKI PLANLA CELISKI"
            elif d.karar == r["side"]:
                _hkm = "DEVAM (motor ayni yonu teyit ediyor)"
            else:
                _hkm = "IZLE (motor BEKLE'de; plan bozulmadi ama teyit de yok)"
            _aud = open_signal_risk_audit(r, st.price, st.atr, cfg)
            L.append(f"   onceki yon {r['side']} @{_fmt(float(r['entry']))}"
                     f" | stop {_fmt(float(r['inval']))} | hedef {_fmt(float(r['target']))}"
                     f" | su an {_pa:+.1f} ATR {'LEHTE' if _pa >= 0 else 'ALEYHTE'} -> {_hkm}"
                     + ((" | " + _aud) if _aud else ""))
    except Exception as exc:
        _nihai_error("onceki planlar", exc)
    for _ap, _ky in ((a_l, "LONG"), (a_s, "SHORT")):
        if _ap:
            _onceki += 1
            try:
                L.append(f"   ateslenmis PUSU plani AKTIF: {_ky} @{_fmt(float(_ap.get('seviye', 0.0)))}"
                         f" (giris ~{_fmt(float(_ap.get('entry', 0.0)))}) — takip KOSULLU PLAN blogunda")
            except Exception as exc:
                _nihai_error("aktif plan", exc)
    if not _onceki:
        L.append("   acik onceki plan yok (kanit: yon_signals/yon_plans store bu kosuda cozuldu)")
    # ── 2. ANLIK MARKET EMIR KARARI ──
    L.append("2. ANLIK MARKET EMIR KARARI")
    if market_var:
        _h2 = None
        try:
            if d.fc:
                _h2 = d.fc.get("q90") if d.karar == "LONG" else d.fc.get("q10")
        except Exception as exc:
            _h2 = None
            _nihai_error("ikinci hedef bandi", exc)
        L.append(f"   market emir uygun: EVET | yon {d.karar}{' [ZAYIF]' if d.weak else ''}")
        L.append(f"   giris {_fmt(d.entry)} | stop {_fmt(d.stop)} | hedef 1 {_fmt(d.target)}"
                 + (f" | hedef 2 {_fmt(_h2)} (bilgi: MC p90 bandi; ayri emir DEGIL)" if _h2 else
                    " | hedef 2: uretilmiyor (tek-hedef tasarim; uydurma sayi yazilmaz)"))
        L.append(f"   cikis: hedef/stop temasi; {cfg.signal_horizon_bars} mumda temas yoksa sure-dolumu olcumu")
        L.append(f"   gecersizlesme: stop {_fmt(d.stop)} otesinde 15m kapanis / yapisal veto")
        L.append(f"   kanit/hesap: canli MC hedef %{int(round(d.p_target * 100))} / stop %{d.reversal_risk}"
                 f" | EV L=%{d.ev_long * 100:.0f} S=%{d.ev_short * 100:.0f}·ATR "
                 f"(komisyon/spread/slip/gecikme/kismi-dolum-sonrasi; funding-haric) | RR {d.rr:.2f}"
                 + (" (funding-ust-siniri dahil)" if d.funding_bound_atr > 0 else ""))
        try:
            _bek_nr = _yontem_beklenti_satiri(d, cfg)
            if _bek_nr:
                L.append(_bek_nr)
        except Exception as exc:
            _nihai_error("yontem beklenti", exc)
    else:
        L.append(f"   anlik market emir uygun degil — {(d.sebep or 'kenar yok')[:90]}")
        L.append(f"   kanit/hesap: EV L=%{d.ev_long * 100:.0f} S=%{d.ev_short * 100:.0f}·ATR"
                 f" | uzlasmazlik std {d.disagree:.2f} | vol rejimi {d.regime}")
    # S2: SIMDI-market mi PUSU-bekle mi ayrimi (acik satir)
    try:
        L.append("   " + giris_zamanlama(symbol, snap, st, d, cfg))
    except Exception as exc:
        _nihai_error("giris zamanlama", exc)
    # ── 3. LIMIT PUSU PLANI (store sozlesmesi esas — H18) ──
    L.append("3. LIMIT PUSU PLANI")
    _pvar = False
    for _pp, _ad3 in ((p_l, "LONG pusu (AL limiti)"), (p_s, "SHORT pusu (SAT limiti)")):
        if _pp:
            try:
                L.append(f"   {_ad3}: seviye {_fmt(float(_pp['seviye']))}"
                         f" | hedef {_fmt(float(_pp['hedef']))} | stop {_fmt(float(_pp['stop']))}")
                _pvar = True
            except Exception as exc:
                _nihai_error("limit pusu satiri", exc)
    if _pvar:
        L.append(f"   bolgeye gelirse aranan sart: seviyeye igne + {cfg.sweep_reclaim_bars} mum icinde"
                 " 15m KAPANISLA geri alis (panel olcer)")
        L.append("   iptal sarti: seviyenin arka tarafinda teyitli 15m kapanis -> plan IPTAL"
                 " (panel bildirir; bekleyen emri GERI CEK)")
    else:
        for _apx, _kx in ((a_l, "LONG"), (a_s, "SHORT")):
            if _apx:
                _pvar = True
                L.append(f"   {_kx} kenari: yeni limit KONMAZ — ateslenmis AKTIF plan izleniyor"
                         " (cift maruziyet yasak)")
        if not _pvar:
            try:
                _td3, _ts3 = htf_trend(snap.htf, cfg)
            except Exception as exc:
                _td3, _ts3 = 0, False
                _nihai_error("pusu trend filtresi", exc)
            if _ts3 and _td3 != 0:
                L.append(f"   pusu kurulmadi: guclu 4s {'ASAGI' if _td3 < 0 else 'YUKARI'} trendine KARSI"
                         " kenar-tepki filtrelendi (olculen karsi-trend karnesi zayif)")
            else:
                L.append("   pusu kurulmadi (uygun kenar yok / bant dar) — yeni bekleyen emir YOK")
    try:
        _na3, _nh3, _ns3 = pusu_karne(symbol)
        if _na3:
            L.append(f"   kanit: pusu karnesi (olculen) {_nh3}/{_na3} HEDEF, {_ns3} STOP")
    except Exception as exc:
        _nihai_error("pusu karnesi", exc)
    # ── 4. KULLANILAN VERILER ──
    _of4 = snap.orderflow
    L.append("4. KULLANILAN VERILER")
    L.append(f"   15m mum {len(snap.candles)} (karar/pusu) | 4h mum {len(snap.htf)} (ust-zaman trend)"
             f" | tick {('var n=' + str(_of4.n)) if _of4 else 'yok'}"
             f" | emir defteri {'var' if snap.book else 'yok'}")
    # dusman-denetim bulgusu (spread_pct OLU VERIYDI: cekilip hic tuketilmiyordu) +
    # B18 zorunlu alt-alanlari: fiyat/hacim/open-interest envanteri acikca yazilir.
    _oi4 = sum(1 for c in snap.candles if c.oi is not None)
    try:
        _sp4 = float(snap.book.get("spread_pct")) if snap.book else None
    except Exception as exc:
        _sp4 = None
        _nihai_error("spread olcumu", exc)
    L.append(f"   fiyat {_fmt(st.price)} | ATR {_fmt(st.atr)} | hacim: 15m mum hacmi var"
             f" | open interest {('var n=' + str(_oi4)) if _oi4 else 'yok'}"
             + (f" | spread %{_sp4 * 100:.4f}" if _sp4 is not None else " | spread olcumu yok"))
    L.append(f"   funding {'var' if snap.funding is not None else 'yok'}"
             f" | taker {'var' if snap.taker_ratio is not None else 'yok'}"
             f" | spot {'var' if snap.spot else 'yok'}"
             f" | L/S {'var' if (snap.ls_top is not None or snap.ls_global is not None) else 'yok'}"
             f" | premium/settle {'var' if snap.premium else 'yok'}")
    L.append(f"   karar bloklari: {', '.join(sorted(d.block_p)) if d.block_p else 'yok'}"
             f" | MC {cfg.mc_paths} yol (bu barin dagilimi)")
    # ── 5. DISLANAN / SUSTURULAN VERILER ──
    L.append("5. DISLANAN / SUSTURULAN VERILER")
    if getattr(cfg, "canli_only", False):
        L.append("   5 kalibrasyon kumesi (ev_gate/reversal/skor/uzlasmazlik-esigi/scen_cell)"
                 " KARARA GIRMEZ (canli-only H17) — yalniz telemetri/karne olarak yazilir")
    _sus5 = [f"{e.name} ({e.note or 'kenarsiz/veri yok'})" for e in d.estimates
             if e.weight <= 0 or e.n <= 0]
    if _sus5:
        L.append(("   agirliksiz tahminciler (karara etkisi 0): " + "; ".join(_sus5))[:200])
    for _e5 in d.estimates:
        if _e5.note and "ATLANDI" in _e5.note:
            L.append(("   " + _e5.note)[:160])
    # ── 6. SENARYO-AJAN KARARI ──
    L.append("6. SENARYO-AJAN KARARI")
    L.append(f"   LONG senaryosu EV=%{d.ev_long * 100:.0f}·ATR | SHORT senaryosu"
             f" EV=%{d.ev_short * 100:.0f}·ATR | islem-yok senaryosu: EV/kapi gecmezse BEKLE")
    try:
        _sc6 = classify_scenario(snap, st, cfg)
        _uy6 = ("AYNI YON (ortak girdi; bagimsiz teyit DEGIL)" if _sc6.side_hint == d.karar
                else ("CELISKI -> endpoint3 motoru oncelikli"
                      if _sc6.side_hint in ("LONG", "SHORT") and d.karar in ("LONG", "SHORT")
                      else "notr/izleme"))
        L.append(f"   senaryo hucre#{_sc6.cell} ipucu={_sc6.side_hint} -> {_uy6}")
    except Exception as exc:
        _nihai_error("senaryo telemetrisi", exc)
    L.append(f"   celiski olcumu: blok uzlasmazligi std={d.disagree:.2f} | NIHAI KARAR: {d.karar}")
    # ── 7. KANIT / HESAP ──
    L.append("7. KANIT / HESAP")
    L.append(f"   calistirilan: bu kosunun kendisi (python fable6.py) | {signals_summary(symbol)}")
    try:
        _fn7, _fh7, _fbi7, _fbn7 = fc_karne(symbol, cfg)
        if _fn7 or _fbn7:
            L.append(f"   tahmin karnesi (olculen): yon {_fh7}/{_fn7} | bant kapsama {_fbi7}/{_fbn7}")
    except Exception as exc:
        _nihai_error("forward tahmin karnesi", exc)
    L.append("   test kaniti: selftest/mutasyon ciktilari repo fable/ altinda; kod degisiminde sart (H20)")
    # ── 8. GECERSIZLESME VE RISK ──
    L.append("8. GECERSIZLESME VE RISK")
    L.append("   plani bozan sart: " + (f"stop {_fmt(d.stop)} otesinde 15m kapanis" if market_var
             else "pusu seviyesinin arkasinda teyitli kapanis (IPTAL) / yeni kosuda taze harita"))
    _rsk8 = [w for w in (d.warn or "").split(" | ") if w]
    if market_var and d.rr < 0.35:
        _rsk8.append(f"INCE KAR: RR {d.rr:.2f} — tek stop birden cok kazanci siler; boyut kucuk")
    L.append(("   en buyuk risk: " + ("; ".join(_rsk8) if _rsk8
              else "belirgin ek uyari yok (standart piyasa riski)"))[:220])
    L.append("   manipulasyon riski: stop-avi/likidite supurmesi olasi — stop paylari OLCULEN"
             " supurme derinligiyle av bolgesi disina konur (garanti DEGIL)")
    L.append("   kalan risk: ulasilabilir gercek isabet HENUZ BILINMIYOR; kesinlik vaadi YOK")
    try:
        _eu8 = d.erken if isinstance(d.erken, dict) else None
        if _eu8 is not None and _eu8.get("risk_var"):
            L.append(f"   erken uyari (kanitlanmamis): {_eu8.get('tur')} riski, olasi yon "
                     f"{_eu8.get('yon_egilim','NEUTRAL')}, guc %{int(round(float(_eu8.get('guc',0.0))*100))} "
                     f"— KESIN DEGIL, salt uyari (karar kapisi degil)")
    except Exception as exc:
        _nihai_error("erken uyari", exc)
    # ── 9. NET SONUC (kesin cumleler — nihai_uygulama_sirasi BOLUM 10 sozlesmesi) ──
    L.append("9. NET SONUC")
    if market_var and d.karar == "LONG":
        L.append("   Market emirle long uygundur.")
    elif market_var and d.karar == "SHORT":
        L.append("   Market emirle short uygundur.")
    else:
        L.append("   Market emir uygun değildir; limit pusu planı aşağıdadır.")
        L.append("   (limit pusu plani: " + ("bolum 3'te — GECERLIDIR" if _pvar
                 else "bu kosuda KURULMADI — bolum 3 gerekcesi; yeni bekleyen emir YOK") + ")")
        L.append(f"   islem yoksa neden: {(d.sebep or 'kenar yok')[:90]}")
    return L


def karar_tablosu_karti(symbol, snap: Snapshot, st: Optional[Structure], d: Decision,
                        cfg: Config) -> List[str]:
    """KARAR TABLOSU (kullanici onayi: Varyant B — her sembolun karar ciktisinin
    EN ALTINA ayri kart). TASARIM KURALI (H18): kart YENI SAYI URETMEZ — d (karar),
    store pusu/aktif SOZLESMELERI (plan_takip/plan_kur SONRASI ayni okuma) ve
    trend/senaryo okumalari; ust bloklarla ayni kaynak -> celisemez. Satirlar
    ~55 kolon tutulur (Pydroid ekraninda kirilmasin)."""
    L: List[str] = []
    def _kart_error(tag: str, exc: Exception) -> None:
        msg = f"  [UYARI] {tag} hesaplanamadi: {str(exc)[:80]}"
        L.append(msg)
        sys.stderr.write(msg.strip() + "\n")
    if st is None or not st.valid or st.atr <= 0:
        return L                      # veri yoksa kart yok (ust bloklar zaten uyardi)
    L.append("── KARAR TABLOSU ──")
    yon_tr = {1: "YUKARI", -1: "ASAGI", 0: "YATAY"}
    try:
        _hd, _hs = htf_trend(snap.htf, cfg)
    except Exception as exc:
        _hd, _hs = 0, False
        _kart_error("4s trend", exc)
    try:
        _aile = rejim_ailesi(snap, cfg)
    except Exception as exc:
        _aile = "?"
        _kart_error("rejim ailesi", exc)
    L.append(f"{symbol} | TREND: 4s {yon_tr[_hd]}{' (guclu)' if _hs else ''}"
             f" | rejim {d.regime} | faz {_aile}")
    try:
        _sct = scenario_turkce(classify_scenario(snap, st, cfg)).split("  ·  ")[0]
        _sct = _sct.replace(" x ", " + ")
    except Exception as exc:
        _sct = "belirsiz"
        _kart_error("senaryo metni", exc)
    L.append(f"  SENARYO : {_sct[:52]}  (baglam; endpoint3 karari onceklidir)")
    if d.karar in ("LONG", "SHORT") and d.entry and d.target and d.stop:
        L.append(f"  MARKET  : {d.karar}{' [ZAYIF]' if d.weak else ''} gir {_fmt(d.entry)}"
                 f" | hedef {_fmt(d.target)} | stop {_fmt(d.stop)}")
    else:
        L.append(f"  MARKET  : YOK — {(d.sebep or 'kenar yok')[:44]}")
    # store sozlesmeleri: islem_plani / sade_ozet / nihai_rapor ile AYNI okuma (H18)
    p_l = p_s = a_l = a_s = None
    try:
        _kk = _plan_yukle().get(symbol) or {}
        for q in _kk.get("pusu", []):
            if str(q.get("tip", "")).startswith("LONG"):
                p_l = q
            elif str(q.get("tip", "")).startswith("SHORT"):
                p_s = q
        for q in _kk.get("aktif", []):
            if str(q.get("tip", "")).startswith("LONG"):
                a_l = q
            elif str(q.get("tip", "")).startswith("SHORT"):
                a_s = q
    except Exception as exc:
        _kart_error("plan store", exc)
    try:
        if p_l:
            L.append(f"  PUSU AL : LONG  {_fmt(float(p_l['seviye']))}"
                     f" | hedef {_fmt(float(p_l['hedef']))} | stop {_fmt(float(p_l['stop']))}")
        elif a_l:
            L.append("  PUSU AL : KOYMA — ayni kenarda ATESLENMIS plan izlemede")
        else:
            L.append("  PUSU AL : yok (kenar yok / bant dar / trend filtresi / F2 tek-kenar)")
        if p_s:
            L.append(f"  PUSU SAT: SHORT {_fmt(float(p_s['seviye']))}"
                     f" | hedef {_fmt(float(p_s['hedef']))} | stop {_fmt(float(p_s['stop']))}")
        elif a_s:
            L.append("  PUSU SAT: KOYMA — ayni kenarda ATESLENMIS plan izlemede")
        else:
            L.append("  PUSU SAT: yok (kenar yok / bant dar / trend filtresi / F2 tek-kenar)")
    except Exception as exc:
        _kart_error("pusu satirlari", exc)
    for _ap, _ky in ((a_l, "LONG"), (a_s, "SHORT")):
        if _ap:
            try:
                L.append(f"  AKTIF   : {_ky} @{_fmt(float(_ap.get('seviye', 0.0)))}"
                         f" (giris ~{_fmt(float(_ap.get('entry', 0.0)))}) izlemede")
            except Exception as exc:
                _kart_error("aktif plan satiri", exc)
    return L


# ════════════════════════════════════════════════════════════════════════════
# INSAN-OKUNUR KARAR PANELI (Sablon-2) — kullanici direktifi.
#   * SALT GORUNUM: yeni sayi/karar URETMEZ; d (karar), snap ve store pusu
#     SOZLESMESINDEN okur (karar_tablosu_karti ile AYNI kaynak -> celisemez).
#   * TEKNIK DENETIM SATIRLARI (PIT/hash/HAM-ALAN/veri/MARK-LIVE/STORE-DENETIM/
#     CANLI-FIYAT) ekrandan CIKARILDI (kullanici secimi: "tamamen kaldir"). O
#     satirlarin yan-etkileri (ledger/plan/forecast/mark-live store yazimlari)
#     render() icinde AYNEN calismaya devam eder; yalniz EKRANA basilmaz.
#   * Yon mantigi/kapilar/store sozlesmesi DEGISMEDI — bu yalniz sunum katmanidir.
# ════════════════════════════════════════════════════════════════════════════
def _panel_wrap(text: str, width: int, indent: str) -> List[str]:
    """Basit kelime-sarmasi (stdlib textwrap'e bagimlilik eklemeden)."""
    words = str(text or "").split()
    if not words:
        return [indent.rstrip()]
    out, cur = [], words[0]
    for w in words[1:]:
        if len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            out.append(cur)
            cur = w
    out.append(cur)
    return [out[0]] + [indent + ln for ln in out[1:]]


def panel_karti(symbol, snap: Snapshot, st: Optional[Structure], d: Decision,
                cfg: Config) -> List[str]:
    """Sablon-2 insan-okunur panel (List[str]). Salt-gorunum; hesap/store yazmaz."""
    W = 44  # sebep/senaryo sarma genisligi (Pydroid ekraninda kirilmasin)
    ok = {1: "▲", -1: "▼", 0: "●"}     # ▲ ▼ ●
    L: List[str] = []
    # ── BASLIK ──
    _saat = ""
    try:
        _ms = snap.last_closed_ms or (snap.candles[-1].close_ms if snap.candles else None)
        if _ms:
            _saat = " · " + time.strftime("%H:%M", time.localtime(_ms / 1000.0))
    except Exception:
        _saat = ""
    L.append(f"════ {symbol} · 15m{_saat} ════")
    # ── KARAR + NEDEN ──
    _kmark = {"LONG": ok[1] + " LONG", "SHORT": ok[1].replace(ok[1], ok[-1]) + " SHORT",
              "BEKLE": "⏸ BEKLE"}.get(d.karar, "⏸ " + str(d.karar))
    if d.karar == "SHORT":
        _kmark = ok[-1] + " SHORT"
    L.append(f"KARAR     {_kmark}{'  [ZAYIF]' if getattr(d, 'weak', False) and d.karar in ('LONG','SHORT') else ''}")
    _sebep = (d.sebep or "").strip()
    if _sebep:
        _wr = _panel_wrap(_sebep[:200], W, " " * 10)
        L.append("NEDEN     " + _wr[0])
        L.extend(_wr[1:])
    # ── S2: SIMDI-market mi PUSU-bekle mi (zamanlama ayrimi) ──
    try:
        _zt = giris_zamanlama(symbol, snap, st, d, cfg).replace("GIRIS ZAMANLAMASI: ", "")
        _zw = _panel_wrap(_zt, W, " " * 10)
        L.append("ZAMANLAMA " + _zw[0])
        L.extend(_zw[1:])
    except Exception:
        pass
    # ── S3: ERKEN UYARI (kanitlanmamis; karar kapisi DEGIL) ──
    try:
        _eu = d.erken if isinstance(d.erken, dict) else None
        if _eu is not None and _eu.get("risk_var"):
            _euw = _panel_wrap(f"{_eu.get('tur')} (olasi yon {_eu.get('yon_egilim','NEUTRAL')}) "
                               f"güç %{int(round(float(_eu.get('guc',0.0))*100))} — kanıtlanmamış, kesin değil",
                               W, " " * 10)
            L.append("⚠ ERKEN  " + _euw[0])
            L.extend(_euw[1:])
    except Exception:
        pass
    # ── DURUM ──
    L.append("──────── DURUM ────────")
    if st is not None and getattr(st, "valid", False) and st.atr > 0:
        _live = snap.live_price if snap.live_price is not None else st.price
        _gap = (_live - st.price) / st.atr if st.atr > 0 else 0.0
        L.append(f"Fiyat     {_fmt(_live)}  (kapanış {_fmt(st.price)} · {_gap:+.1f} ATR)")
        try:
            _aile = rejim_ailesi(snap, cfg)
        except Exception:
            _aile = "?"
        L.append(f"Rejim     {d.regime} · faz {_aile} · ATR {_fmt(st.atr)}")
        L.append(f"Bant      {_fmt(st.range_low)} – {_fmt(st.range_high)}")
        try:
            _hd, _hs = htf_trend(snap.htf, cfg)
        except Exception:
            _hd, _hs = 0, False
        _tlab = {1: "YUKARI", -1: "ASAGI", 0: "YATAY/belirsiz"}[_hd]
        L.append(f"4s trend  {ok[_hd]} {_tlab}{' (güçlü)' if _hs else ''}")
        try:
            _sct = scenario_turkce(classify_scenario(snap, st, cfg)).split("  ·  ")[0].replace(" x ", " + ")
            _sw = _panel_wrap(_sct[:120], W, " " * 10)
            L.append("Senaryo   " + _sw[0])
            L.extend(_sw[1:])
        except Exception:
            pass
    else:
        L.append("Fiyat     (yapisal veri yetersiz — bant/ATR hesaplanamadi)")
    # ── TAHMIN (4 saat) ──
    L.append("───── TAHMİN (%d saat) ─────" % (cfg.horizon // 4))
    if d.fc:
        _f = d.fc
        _ylab = {1: "YUKARI", -1: "ASAGI",
                 0: "NOTR (medyan < %.2f ATR)" % cfg.fc_notr_atr}[_f["dir"]]
        _gv = round(float(_f.get("p_selected",
                                 max(_f.get("pup", 1/3), _f.get("pdown", 1/3),
                                     _f.get("pflat", 1/3)))) * 100)
        L.append(f"Yön       {ok[_f['dir']]} {_ylab}   güven %{_gv} (model, ölçülmemiş)"
                 + ("  ⚠ MC↔topluluk çelişki" if _f.get("celiski") else ""))
        L.append(f"Olasılık  DOWN %{d.p_down*100:.0f} · FLAT %{d.p_flat*100:.0f} · UP %{d.p_up*100:.0f}")
        L.append(f"Bant      {_fmt(_f['q10'])} / {_fmt(_f['q50'])} / {_fmt(_f['q90'])}  (p10/50/90)")
    else:
        L.append("Yön       tahmin üretilemedi (veri bayat/yetersiz)")
        L.append(f"Olasılık  DOWN %{d.p_down*100:.0f} · FLAT %{d.p_flat*100:.0f} · UP %{d.p_up*100:.0f}")
    # ── PLAN ──
    L.append("──────── PLAN ────────")
    if d.karar in ("LONG", "SHORT") and d.entry and d.target and d.stop:
        L.append(f"İŞLEM     {ok[1 if d.karar=='LONG' else -1]} {d.karar} gir {_fmt(d.entry)}"
                 f" → {_fmt(d.target)} · stop {_fmt(d.stop)}")
    p_l = p_s = a_l = a_s = None
    try:
        _kk = _plan_yukle().get(symbol) or {}
        for q in _kk.get("pusu", []):
            if str(q.get("tip", "")).startswith("LONG"):
                p_l = q
            elif str(q.get("tip", "")).startswith("SHORT"):
                p_s = q
        for q in _kk.get("aktif", []):
            if str(q.get("tip", "")).startswith("LONG"):
                a_l = q
            elif str(q.get("tip", "")).startswith("SHORT"):
                a_s = q
    except Exception:
        pass
    try:
        if p_l:
            L.append(f"AL  pusu  {_fmt(float(p_l['seviye']))} → {_fmt(float(p_l['hedef']))}"
                     f" · stop {_fmt(float(p_l['stop']))}")
        elif a_l:
            L.append("AL  pusu  — ateşlenmiş plan izlemede")
        else:
            L.append("AL  pusu  yok (kenar yok / trend filtresi / F2)")
        if p_s:
            L.append(f"SAT pusu  {_fmt(float(p_s['seviye']))} → {_fmt(float(p_s['hedef']))}"
                     f" · stop {_fmt(float(p_s['stop']))}")
        elif a_s:
            L.append("SAT pusu  — ateşlenmiş plan izlemede")
        else:
            L.append("SAT pusu  yok (kenar yok / trend filtresi / F2)")
    except Exception:
        pass
    if isinstance(d.plan, dict) and d.plan.get("p_ust") is not None:
        _pl = d.plan
        L.append(f"Temas     %{_pl.get('p_ust',0)*100:.0f} üst · %{_pl.get('p_alt',0)*100:.0f} alt"
                 f" · %{_pl.get('p_yok',0)*100:.0f} değmez")
    for _ap, _ky in ((a_l, "LONG"), (a_s, "SHORT")):
        if _ap:
            try:
                L.append(f"AKTİF     {_ky} @{_fmt(float(_ap.get('seviye', 0.0)))} izlemede")
            except Exception:
                pass
    L.append("═" * 30)
    # DURUSTLUK: her modda kisa uyari (teknik degil, sorumluluk).
    L.append("Not: yüzdeler bu 15dk barının canlı ölçümü — garanti değil,")
    L.append("     yatırım tavsiyesi değildir. Stop'suz işlem açma.")
    return L


def render(symbol, snap: Snapshot, d: Decision, cfg: Config) -> str:
    L = []
    of = snap.orderflow
    # HUKUM MODU (kullanici isteri: "'su olursa bu olur' dilini KAZI"): varsayilan cikti
    # hukum dilidir — YON + BANT + ISLEM VAR/YOK + OLCULEN karneler. Kosullu-dil bloklari
    # (SENARYO/MIKRO/NET-OKUMA/tetik haritasi) yalniz YON_DETAY=1 ile basilir; pusu/tahmin
    # OLCUM makineleri her modda calismaya devam eder (sonuclari gecmis-zaman olcumu olarak akar).
    detay = os.environ.get("YON_DETAY", "") == "1" or getattr(cfg, "detay_mod", False)
    # REPORT_4 #6a: OFFLINE/sentetik snapshot canli kaynak etiketi tasimaz (durust etiket).
    _kaynak = "fapi.binance.com" if d.mode == "LIVE" else "OFFLINE/yerel veri (fapi degil)"
    L.append(f"=== {symbol}  (kaynak: {_kaynak}) ===")
    L.append(f"BAGLAM={d.mode} | p(DOWN/FLAT/UP)="
             f"%{d.p_down*100:.1f}/%{d.p_flat*100:.1f}/%{d.p_up*100:.1f} | "
             f"kapi={d.gate_code} | protokol={d.protocol_id}")
    if d.predicted_at_ms is not None:
        L.append(f"PIT predicted_at={d.predicted_at_ms} target_end={d.target_end_ms} "
                 f"watermark={d.data_watermark_ms} code={d.code_hash[:10]} "
                 f"model={d.model_hash[:10]} feature={d.feature_hash[:10]}")
    if d.diagnostics:
        L.append("VERI/DEFTER UYARISI: " + " | ".join(d.diagnostics[:4]))
    L.append(f"veri[15m:{len(snap.candles)} 4h:{len(snap.htf)}] "
             f"tick:{'var('+str(of.n)+')' if of else 'yok'} "
             f"ob:{'var' if snap.book else 'yok'} "
             f"funding:{_fmt(snap.funding) if snap.funding is not None else 'yok'} "
             f"taker:{_fmt(snap.taker_ratio) if snap.taker_ratio is not None else 'yok'}")
    if snap.candles:
        _lc = snap.candles[-1]
        L.append("HAM-ALAN ENVANTERI: "
                 f"quoteVol={_fmt(_lc.quote_volume)} trades={_lc.trade_count} "
                 f"klineTakerBuy={_fmt(_lc.taker_buy_base)}/{_fmt(_lc.taker_buy_quote)} "
                 f"OI={_fmt(_lc.oi)} OI-notional={_fmt(_lc.oi_value)} "
                 f"takerVol(B/S)={_fmt(_lc.taker_buy_vol)}/{_fmt(_lc.taker_sell_vol)}")
    # ── YON9-EK: yeni veri katmani (predicted funding/settle + L/S + spoof + tasfiye vekili) ──
    try:
        _yv = []
        if snap.premium:
            _pr = snap.premium
            if _pr.get("next_funding_ms") and _pr.get("server_ms"):
                _dk = max(0, int((_pr["next_funding_ms"] - _pr["server_ms"]) / 60000))
                _yv.append(f"settle {_dk}dk (predicted %{_pr.get('last_funding', 0.0)*100:.4f})")
            if _pr.get("mark") and _pr.get("index"):
                _bps = (_pr["mark"] - _pr["index"]) / _pr["index"] * 10000.0
                _yv.append(f"prem {_bps:+.1f}bps")
                _oi_dus = (len(snap.candles) >= 3 and snap.candles[-1].oi is not None
                           and snap.candles[-3].oi is not None
                           and snap.candles[-1].oi < snap.candles[-3].oi)
                if abs(_bps) > cfg.tasfiye_prem_bps and _oi_dus:
                    _yv.append("TASFIYE-VEKILI: premium sapmasi + OI dusuyor (gercek likidasyon "
                               "akisi REST'te yok — bu VEKIL olcum)")
        if snap.ls_top is not None:
            _yv.append(f"topL/S {snap.ls_top:.2f}")
        if snap.ls_global is not None:
            _yv.append(f"glbL/S {snap.ls_global:.2f}")
        _sp_taraf, _sp_kayip = spoof_kontrol(snap.book, snap.book2, cfg.spoof_kayip_oran)
        if _sp_taraf:
            _yv.append(f"SPOOF SUPHESI: {_sp_taraf} duvarinin %{int(_sp_kayip*100)}'i "
                       f"{cfg.spoof_bekle_sn:.1f} sn icinde kayboldu -> imbalance'a guvenme")
        if _yv:
            L.append("yeni-veri: " + " | ".join(_yv))
    except Exception as exc:
        L.append("YENI-VERI KATMANI HATASI: " + str(exc)[:100])
    st = build_structure(snap.candles, cfg) if len(snap.candles) > cfg.atr_period else None
    try:
        L.extend(render_mark_live_denetime(mark_live_denetime(symbol, snap, st, cfg)))
    except Exception as _e49:
        L.append("MARK/LIVE DENETİM: URETILEMEDI — " + str(_e49)[:80])
    try:
        L.extend(render_step49_store_denetime(step49_store_denetimi(symbol, snap, st, d, cfg)))
    except Exception as _e49s:
        L.append("AÇIK SİNYAL / PLAN STORE DENETİMİ: URETILEMEDI — " + str(_e49s)[:80])
    # ── HESAP SIRASI (canli bulgu F1/F2): plan_takip ONCE calisir (ateslenen pusu 'aktif'e,
    # sonuclanan 'hist'e gecer), sonra plan_kur NIHAI sozlesmeleri (tasima dahil) store'a yazar;
    # ISLEM PLANI de store'daki O sozlesmeyi basar. EKRAN SIRASI DEGISMEZ (satirlar asagida
    # eski yerlerinde basilir) — yalniz hesap one alindi ki ekran ile makine birebir olsun.
    try:
        _pusu_hazir = plan_takip(symbol, snap, cfg, d)
    except Exception as exc:
        _pusu_hazir = ["[UYARI] plan takip hesaplanamadi: " + str(exc)[:100]]
    _npl_hazir = []
    _mic_ip: List[MicroScen] = []
    if st and st.valid:
        try:
            _mic_ip = classify_micro(snap, st, cfg)
        except Exception as exc:
            _mic_ip = []
            L.append("[UYARI] mikro katalog hesaplanamadi: " + str(exc)[:100])
        try:
            if getattr(cfg, "single_exposure_gate_enabled", True) and getattr(cfg, "no_pusu_when_market_signal", True) \
               and d.karar in ("LONG", "SHORT"):
                _clear_pending_pusu_keep_active(symbol)
                _npl_hazir = []
            else:
                # F2 (FABLE6_5): MC ilk-temas olasiligi (d.plan) tek-kenar secimine verilir
                _npl_hazir = plan_kur(symbol, snap, st, _mic_ip, cfg,
                                      mc_ilk=(d.plan if isinstance(d.plan, dict) else None),
                                      oncu=(d.oncu if isinstance(getattr(d, "oncu", None), dict)
                                            else _ONCU_HOLDER.get("v")))
        except Exception as exc:
            _npl_hazir = ["[UYARI] plan kurulumu hesaplanamadi: " + str(exc)[:100]]
    if st and st.valid:
        _gap_abs, _gap_atr, _age_min, _live_rap = live_price_gap_info(snap, st, cfg)
        if _live_rap:
            _etik = "BLOK" if _gap_atr >= getattr(cfg, "live_gap_block_atr", 0.60) else ("UYARI" if _gap_atr >= getattr(cfg, "live_gap_warn_atr", 0.25) else "OK")
            L.append(f"CANLI-FIYAT DENETIMI [{_etik}]: {_live_rap}")
        # ── SENARYO ONCE (kullanici direktifi: "ilk once senaryo okunmali"; HUKUM
        # modunda da gorunur). Okuma sirasi: (1) SENARYO, (2) 1s+15m yapisal trend,
        # (3) 15m giris/cikis (ISLEM PLANI). 144-hucre TELEMETRIDIR (karar kapisi
        # DEGIL; R4/R8) -> endpoint3 yon2 karari onceklidir; bu satir yon URETMEZ.
        _scn_top = getattr(d, "scen144", None)
        if _scn_top is None:
            try:
                _scn_top = classify_scenario(snap, st, cfg)
            except Exception:
                _scn_top = None
        if _scn_top is not None:
            L.append("SENARYO (once): " + scenario_turkce(_scn_top).replace(" x ", " + ")
                     + "  (baglam/telemetri; karar kapisi degil, endpoint3 onceklidir)")
            # UZLASTIRMA: "geri cekilme" + "guclu yukselis" CELISKI DEGIL — ayni yonu
            # gosterir (trendde dip-alim/tepki-satis bolgesi). Ters ise DIKKAT notu.
            _htd_s, _hts_s = htf_trend(snap.htf, cfg)
            _shint_s = getattr(_scn_top, "side_hint", "NEUTRAL")
            if _shint_s in ("LONG", "SHORT") and _htd_s != 0:
                _trd_s = "YUKARI" if _htd_s > 0 else "ASAGI"
                _guc_s = " (guclu)" if _hts_s else ""
                if (_shint_s == "LONG") == (_htd_s > 0):
                    _bolge_s = ("guclu trendde geri cekilme = dip-alim bolgesi"
                                if _htd_s > 0 else "trend yonunde tepki-satis bolgesi")
                    L.append(f"  SENARYO<->4S: senaryo {_shint_s} egilimli, 4s {_trd_s}{_guc_s}"
                             f" -> UYUMLU (celiski DEGIL; {_bolge_s})")
                else:
                    L.append(f"  SENARYO<->4S: senaryo {_shint_s} egilimli ama 4s {_trd_s}{_guc_s}"
                             f" -> DIKKAT (karsi-yon; endpoint3 karari onceklidir)")
        L.append(f"fiyat {_fmt(st.price)} (kapali 15m) | bant {_fmt(st.range_low)}-{_fmt(st.range_high)} | "
                 f"ATR {_fmt(st.atr)} | rejim {d.regime}")
        _hdir, _hstrong = htf_trend(snap.htf, cfg)
        _hlabel = {1: "YUKARI", -1: "ASAGI", 0: "YATAY/belirsiz"}[_hdir]
        L.append(f"4S TREND (ust-zaman): {_hlabel}{' (guclu)' if _hstrong else ''}  |  "
                 f"hesap: 4s+15m  ·  giris/cikis: 15m")
        if d.btc_leader is not None:
            _bl = d.btc_leader
            _bdir = "LONG-tempo" if _bl.side > 0 else ("SHORT-tempo" if _bl.side < 0 else "NOTR")
            _met = []
            if _bl.corr is not None:
                _met.append(f"corr={_bl.corr:+.2f}" + (f" z={_bl.corr_z:+.1f}" if _bl.corr_z is not None else ""))
            if _bl.beta is not None:
                _met.append(f"beta={_bl.beta:+.2f}" + (f" z={_bl.beta_z:+.1f}" if _bl.beta_z is not None else ""))
            if _bl.leadlag is not None:
                _met.append(f"leadlag={_bl.leadlag:+.2f}" + (f" q={_bl.leadlag_q:.2f}" if _bl.leadlag_q is not None else ""))
            if _bl.decorrelation_risk > 0:
                _met.append(f"decor-risk={_bl.decorrelation_risk:.2f}")
            L.append("BTC BAS-AT (STEP4): " + f"{_bl.mode} | {_bdir} | guc={_bl.strength:.2f} kalite={_bl.quality:.2f}"
                     + (" | " + " ".join(_met) if _met else "")
                     + (" | " + "; ".join(_bl.reasons[:3]) if _bl.reasons else ""))
        # ── ISLEM PLANI (NET; her modda EN BASTA — kullanicinin istedigi dogrudan sinyal)
        # _mic_ip yukarida hesaplandi; plan_takip+plan_kur de calisti -> store NIHAI sozlesme.
        try:
            L.extend(islem_plani(symbol, snap, st, d, _mic_ip, cfg))
        except Exception as exc:
            L.append("[UYARI] islem plani render edilemedi: " + str(exc)[:100])
    # ── REJIM AILESI + TAZE DONUS + KAYMA (rejim-dinamik durum; BEKLE'de de gorunur) ──
    # R5: senaryo siniflandirmasi one alinir ki tek-kaynak rejim satiri family6'yi
    # ayni nesneden okusun (asagida SENARYO KATALOGU ayni 'scen'i kullanir; cift hesap yok).
    # F3 (FABLE6_5): karar-oncesi siniflandirma d.scen144 ile gelir; ekran ayni nesneyi
    # kullanir (karar, log ve ekran AYNI hucreyi soyler). Yoksa eski yol fallback.
    scen = getattr(d, "scen144", None)
    if scen is None:
        scen = classify_scenario(snap, st, cfg) if (st and st.valid) else None
    try:
        _aile_r = rejim_ailesi(snap, cfg)
        _rgv = rejim_gorunumu(snap, cfg, scen)
        L.append("REJIM (tek-kaynak, R5): vol=" + _rgv.vol
                 + " [KARAR: yalniz EXTREME->guven kismasi] | aile=" + _rgv.aile
                 + " [gosterim+mikro-sira] | 6-aile=" + _rgv.family6
                 + " [yalniz gosterim] -> " + _rgv.karar_etkisi)
        _oncelik = {"YUKARI-TREND": "devam kaliplari (retest/spot-oncu); trend-karsiti donusler ekstra teyit ister",
                    "ASAGI-TREND": "devam kaliplari + flush/iskonto dip-avi; V-dip aceleciligi kisildi",
                    "YATAY": "bant-kenari/likidite kaliplari (esit dip-tepe, VWAP); kirilim tuzaklarina dikkat",
                    "ASIRI-VOL": "fitil/absorpsiyon/temizlik kaliplari; sikisma kaliplari kapali"}[_aile_r]
        L.append("REJIM AILESI: " + _aile_r + "  ->  oncelik: " + _oncelik)
        _tdr, _tdr_msg = taze_donus(snap.candles, snap.htf, cfg)
        if _tdr:
            L.append("!! TAZE DONUS PENCERESI: " + _tdr_msg + " — bu calistirma donus penceresinde: "
                     "guven kisildi; bir sonraki calistirmada motor yeni rejime oturmus olacak")
        _kyr, _kyr_rate, _kyr_n = kayma_alarmi(symbol, cfg)
        if _kyr:
            L.append("!! KAYMA ALARMI: son %d cozulmus sinyalde isabet %%%d — motor su rejimde "
                     "tutmuyor, guven otomatik kisildi (temkin)" % (_kyr_n, round(_kyr_rate * 100)))
        _mk, _mk_yon, _mk_pay, _mk_n = yon_monokultur(symbol, cfg)
        if _mk:
            L.append("!! TEK-YON UYARISI: son %d sinyalin %%%d'i %s — motor tek tarafa "
                     "kilitlenmis olabilir (rejim korlugu belirtisi); karsi-yon kanitlarini kontrol et"
                     % (_mk_n, round(_mk_pay * 100), _mk_yon))
    except Exception as exc:
        L.append("[UYARI] rejim/kayma telemetrisi hesaplanamadi: " + str(exc)[:100])
    # ── S3 ERKEN UYARI (AYRI katman; KANITLANMAMIS; karar kapisi DEGIL) ──
    try:
        _eu = d.erken if isinstance(d.erken, dict) else None
        if _eu is not None:
            L.append("── ERKEN UYARI (kanitlanmamis; 15-30dk risk; karar kapisi DEGIL) ──")
            if _eu.get("risk_var"):
                _guc_pct = int(round(float(_eu.get("guc", 0.0)) * 100))
                _yon_eu = _eu.get("yon_egilim", "NEUTRAL")
                L.append(f"RISK: {_eu.get('tur')} (olasi yon {_yon_eu}) | guc %{_guc_pct} "
                         f"(kanit x{len(_eu.get('kanitlar', []))}) — KESIN DEGIL, UYARI")
                for _k in (_eu.get("kanitlar") or [])[:6]:
                    L.append("  · " + str(_k))
            else:
                L.append("RISK: belirgin erken-uyari yok (yeterli bagimsiz kanit toplanmadi)")
            _en, _eh, _em = erken_uyari_karne(symbol)
            if _en:
                L.append(f"ERKEN-UYARI KARNESI (olculen): {_eh}/{_en} isabet "
                         f"(%{round(100 * _eh / max(1, _en))}); {_em} kacirilan — kanitlanmamis kenar")
            for _ln in (_eu.get("rapor") or [])[:4]:
                L.append("  " + str(_ln))
    except Exception as exc:
        L.append("[UYARI] erken-uyari katmani basilamadi: " + str(exc)[:100])
    # ── ONCU TAHMIN (YON9-EK): her kosuda KOSULSUZ yon+bant — 'su olursa bu olur' DEGIL.
    # Sicili olculur: onceki tahminlerin cozumu + karne asagida. Tahmin != islem emri.
    try:
        L.append("── HUKUM — ONCU TAHMIN (ufuk %d mum = %d saat) ──"
                 % (cfg.horizon, cfg.horizon // 4))
        if d.fc:
            _f = d.fc
            _ytxt_raw = {1: "YUKARI", -1: "ASAGI", 0: "NOTR (medyan hareket < %.2f ATR)" % cfg.fc_notr_atr}[_f["dir"]]
            _gv_raw = round(float(_f.get("p_selected",
                                         max(_f.get("pup", 1/3),
                                             _f.get("pdown", 1/3),
                                             _f.get("pflat", 1/3)))) * 100)
            _truth = forecast_truth_state(symbol, cfg)
            _cap = (_truth.get("cap") if not cfg.canli_only else None)
            _ytxt = _ytxt_raw
            if (not cfg.canli_only and getattr(cfg, "forecast_red_quarantine_enabled", True)
                    and _truth.get("state") == "KIRMIZI"):
                _ytxt = f"NOTR/KARANTINA (ham yön: {_ytxt_raw}; sicil kırmızı)"
                _cap = min(int(_cap) if _cap is not None else 100, int(getattr(cfg, "forecast_red_quarantine_conf_cap", 45)))
            _gv = min(_gv_raw, int(_cap)) if _cap is not None else _gv_raw
            _gv_note = f"; ham %{_gv_raw}, sicil-kirpilmis" if _gv != _gv_raw else ""
            L.append(f"YON TAHMINI: {_ytxt}  |  guven: model-tahmini %{_gv}{_gv_note} "
                     f"(olculmus DEGIL; olculen sicil asagida)"
                     + ("  |  UYARI: MC-medyan ile topluluk CELISIYOR -> dusuk guven"
                        if _f.get("celiski") else ""))
            _tn = forecast_truth_note(symbol, cfg)
            if _tn:
                L.append("  " + _tn)
            L.append(f"BEKLENEN BANT (MC p10/p50/p90): {_fmt(_f['q10'])} / {_fmt(_f['q50'])} / {_fmt(_f['q90'])}")
        else:
            L.append("YON TAHMINI: uretilemedi (MC kurulamadan kapi kesti: veri bayat/yetersiz)")
        for _ln in (d.fc_rapor or []):
            L.append("  " + _ln)
        _fn, _fh, _fbi, _fbn = fc_karne(symbol, cfg)
        if _fn or _fbn:
            L.append(f"TAHMIN KARNESI (olculen): yon {_fh}/{_fn} (%{round(100*_fh/max(1,_fn))}) | "
                     f"bant kapsama {_fbi}/{_fbn} (%{round(100*_fbi/max(1,_fbn))}, ideal ~%80)")
            _lmh = forward_ledger_metrics(symbol, cfg)
            _cih = _lmh.get("accuracy_ci", (None, None))
            _cit = (f" | %95 blok-GA %{_cih[0]*100:.1f}-%{_cih[1]*100:.1f}"
                    if _cih and _cih[0] is not None else " | GA yetersiz")
            L.append(f"  ENDPOINT3 PROPER: Brier={_lmh['brier']:.4f} log-loss={_lmh['logloss']:.4f} "
                     f"balanced=%{(_lmh['balanced_accuracy'] or 0)*100:.1f}{_cit} | "
                     f"operasyonel={_lmh['n_operational']} sabit-faz-kohort={_lmh['n']}")
            L.append(f"  TRADE SECICI: kapsam=%{_lmh['coverage']*100:.1f} | "
                     + (f"isabet=%{_lmh['selective_acc']*100:.1f} n={_lmh['selective_n']}"
                        if _lmh.get("selective_acc") is not None else "yonlu karar yok"))
        else:
            L.append("TAHMIN KARNESI: henuz cozulmus tahmin yok (ufuk %d mum sonra dolar)" % cfg.horizon)
        # ISLEM hukmu (kosulsuz, tek satir): var/yok + rakamlar. 'Olursa' dili yok.
        if d.karar in ("LONG", "SHORT"):
            L.append(f"ISLEM: {d.karar}{' [ZAYIF]' if d.weak else ''} | giris {_fmt(d.entry)} | "
                     f"stop {_fmt(d.stop)} | hedef {_fmt(d.target)} | "
                     f"canli MC hedef %{int(round(d.p_target*100))} / stop %{d.reversal_risk}")
        else:
            L.append("ISLEM: YOK — " + (d.sebep or "")[:100])
    except Exception as exc:
        msg = "[UYARI] HUKUM/oncu-tahmin karti hesaplanamadi: " + str(exc)[:120]
        L.append(msg)
        sys.stderr.write(msg + "\n")
    # ── ACIK SINYAL TAKIBI: onceki calistirmalarin plani SIMDI ne durumda? ──
    try:
        _takip = takip_raporu(symbol, snap, d, st, cfg)
    except Exception as exc:
        _takip = []
        L.append("[UYARI] acik sinyal takibi hesaplanamadi: " + str(exc)[:100])
    if _takip:
        L.append("── ACIK SINYAL TAKIBI (onceki calistirmalar) ──")
        L.extend(_takip)
    # ── KOSULLU PLAN TAKIBI: gecen calistirmanin pususu ateslendi mi/iptal mi? ──
    # (HESAP yukarida yapildi: plan_takip -> plan_kur -> islem_plani sirasi; burada yalniz basim)
    if _pusu_hazir:
        L.append("── KOSULLU PLAN TAKIBI (gecen calistirmanin tetikleri) ──")
        L.extend(_pusu_hazir)
    # ── SENARYO KATALOGU: 6 ust aile + 12 ayrintili durum x 12 olay ID alani ──
    if scen is not None and detay:
        L.append("── SENARYO KATALOGU (telemetri; karar etkisi YOK) ──")
        L.append(f"6-AILE={scen.family6} | ID #{scen.cell}: {scen.regime} x {scen.event}   [{scen.dims}]")
        L.append("NOT: #1-144 bir KIMLIK ALANIDIR (144 ayri davranis DEGIL): 15 hucre yapisal "
                 "olarak ULASILAMAZ (SCEN_IMKANSIZ_HUCRELER), pratik cesitlilik ~75 hucre; "
                 "OOS katkisi kanitlanmadi ve nadir hucre telemetrisi olgunlasamaz (R4/R8).")
        if not scen.oi_var:
            L.append("NOT: OI verisi YOK -> ACCUMULATION/DISTRIBUTION rejimleri bu kosuda "
                     "olculemez (veri-erisilebilirlik kisiti; REPORT_3 S2).")
        L.append(f"TURKCESI: {scenario_turkce(scen)}")
        _shint = scen.side_hint if scen.side_hint in ("LONG", "SHORT") else None
        L.append(f"HUCRE BETIMSEL SICIL: {scen_cell_validation_tag(symbol, scen.cell, cfg, side=_shint)}")
        L.append(f">> SINYAL: {scenario_headline(scen, d)}")
        L.append(f">> NE OLUYOR: {scenario_explanation(scen)}")
        if scen.heralds:
            L.append(f"GOZLEM ({scen.herald_n}/6 kalip, {gozlem_validation_tag(symbol, scen, cfg)}): "
                     f"{', '.join(scen.heralds)}")
        if len(scen.events_all) > 1:
            L.append(f"coklu-olay: {', '.join(scen.events_all)} (manset: {scen.event})")
    # ── MIKRO-SENARYO (29 kalip; vadeli+spot kombine): "15m'de NE YAPABILIR" ──
    try:
        micros = classify_micro(snap, st, cfg) if (st and st.valid) else []
    except Exception as exc:
        micros = []
        L.append("[UYARI] mikro-senaryo taramasi hesaplanamadi: " + str(exc)[:100])
    if detay:
        L.append("── MIKRO-SENARYO (vadeli+spot kombine) ──")
        if snap.spot is None:
            L.append("(spot verisi yok -> basis/spot-onculuk kaliplari kapali)")
        if micros:
            for m in micros[:cfg.micro_top_n]:
                yon = {"LONG": "LONG-egilim", "SHORT": "SHORT-egilim", "NEUTRAL": "yon-notr"}[m.side]
                L.append(f"#{m.mid} {m.ad}  [{yon} | guven-kati {m.tier} | guc {m.guc:.2f} | "
                         f"{micro_tag(symbol, m, cfg)}]  ({m.kanit})")
                L.append(f"   BEKLENEN (ADAY, kehanet degil): {m.beklenen}")
            if len(micros) > cfg.micro_top_n:
                kalan = ", ".join(f"#{m.mid}{m.ad.split('(')[0]}" for m in micros[cfg.micro_top_n:])
                L.append(f"   diger kaliplar: {kalan}")
            if any(m.tier == "C" for m in micros[:cfg.micro_top_n]):
                L.append("   NOT: C-kati kaliplar tek basina sinyal DEGIL, baglamdir; seviyeler daima yon2'den.")
        else:
            L.append("belirgin mikro-kalip yok (sakin/karisik akis)")
    # ── NET OKUMA (yalniz DETAY modunda: kosullu dil) ──
    if st and st.valid:
        if detay:
            try:
                L.append("── NET OKUMA (insan dili) ──")
                L.extend(net_okuma(symbol, snap, st, d, micros, cfg))
            except Exception as exc:
                L.append("[UYARI] net okuma hesaplanamadi: " + str(exc)[:100])
        try:
            # PUSU makinesi HER modda kurulur (olcum surer); KURULUM yukarida yapildi
            # (islem_plani store sozlesmesini basabilsin diye) — burada yalniz basim.
            _npl = _npl_hazir
            if _npl:
                if detay:
                    L.append(f"PUSU KURULDU: {len(_npl)} kosullu plan kaydedildi (yukaridaki tetik "
                             "haritasinin makine-okur hali) — bir SONRAKI calistirma ateslenme/iptal/"
                             "hedef-stop durumunu OLCUP raporlayacak")
                else:
                    L.append(f"PUSU KURULDU: {len(_npl)} plan sessiz izlemede — sonuclari sonraki "
                             "kosularda karneyle raporlanir (ayrintili harita icin YON_DETAY=1)")
        except Exception as exc:
            L.append("[UYARI] pusu plani raporlanamadi: " + str(exc)[:100])
    L.append("── KARAR ──")
    if d.karar in ("LONG", "SHORT") and st:
        b = cfg.entry_buffer_atr * st.atr
        L.append(f"KARAR: {d.karar}{'  [ZAYIF]' if d.weak else ''}")
        L.append(f"GIRIS: {_fmt(d.entry)}  (bant {_fmt(d.entry - b)}-{_fmt(d.entry + b)})")
        L.append(f"HEDEF: {_fmt(d.target)}")
        L.append(f"STOP:  {_fmt(d.stop)}")
        # F8 (FABLE6_5): gecersizlik ve maliyet AYRI satir (kullanici sozlesmesi)
        L.append(f"GECERSIZLIK: {_fmt(d.stop)} otesinde 15m KAPANIS -> plan gecersiz "
                 f"(stop=fiyat siniri; gecersizlik=kapanis kosulu + yapisal veto)")
        if getattr(d, "cost_abs", 0.0) > 0 and st.atr > 0:
            L.append(f"MALIYET (komisyon+spread+slip+gecikme+kismi-dolum"
                     f"{'+funding-ust-siniri' if d.funding_bound_atr > 0 else ''}): "
                     f"~{_fmt(d.cost_abs)} = %{d.cost_abs / st.atr * 100:.0f}·ATR "
                     f"(EV/RR bu maliyetin SONRASIDIR)")
        L.append(f"EV(tradeability; yon secmez): LONG=%{d.ev_long*100:.0f}·ATR  SHORT=%{d.ev_short*100:.0f}·ATR  "
                 f"-> secilen %{d.ev*100:.0f}·ATR")
        _rr_tag8 = ("komisyon/spread/slip/gecikme/kismi-dolum+funding-ust-siniri-dahil" if d.funding_bound_atr > 0
                    else "komisyon/spread/slip/gecikme/kismi-dolum-dahil; funding-haric")
        L.append(f"{d.score_label}   |   RR({_rr_tag8}): {d.rr:.2f}")
        L.append(f"MC hedef: %{d.p_target*100:.0f}   |   TERS-DONME (stop) riski: %{d.reversal_risk}")
        L.append(f"SEBEP: {d.sebep}")
    else:
        L.append("KARAR: BEKLE")
        L.append(f"SEBEP: {d.sebep}")
    if d.estimates:
        parts = " ".join(f"{e.name}={e.p_up*100:.0f}%" + (f"(w{e.weight:.1f})" if e.weight else "(w0)")
                         for e in d.estimates)
        bp = " ".join(f"{k}={v*100:.0f}%" for k, v in d.block_p.items())
        L.append(f"TAHMINCILER: {parts}")
        L.append(f"BLOKLAR: {bp} | uzlasmazlik(std)={d.disagree:.2f}")
        if "mc" in d.block_p and "flow" in d.block_p:
            L.append("  (R7 not: mc ile flow ortak delta_z girdisi paylasir — uyum bagimsiz teyit degil)")
        # NOT-GORUNURLUGU FIX (denetim): Estimate.note tanilar tasiyordu ("OB-imbalance
        # ATLANDI (spoof suphesi)", L/S kalabalik, OI hucresi...) ama canli ciktida hic
        # basilmiyordu — susturulmus tani. Rutin/bos notlar elenir, tanilar gosterilir.
        _rutin = ("yetersiz", "yok", "veri yok", "az-ornek", "hucre-seyrek", "canli-tick")
        _notlar = [f"{e.name}: {e.note}" for e in d.estimates if e.note and e.note not in _rutin]
        if _notlar:
            L.append(("TAHMINCI NOTLARI: " + " | ".join(_notlar))[:220])
    if d.warn:
        L.append(f"DONUS RADARI [oncu, tick]: {d.warn}")
    elif d.rev_sign != 0:
        yon = "DIP->YUKARI" if d.rev_sign > 0 else "TEPE->ASAGI"
        L.append(f"DONUS RADARI [oncu, tick]: {yon} | {', '.join(d.rev_reasons)}")
    elif of is not None and of.n >= 40:
        L.append(f"DONUS RADARI: net sinyal yok (CVDz={of.delta_z:.1f} CVD={of.cvd:+.0f})")
    # ── KARAR TABLOSU (kullanici onayi: Varyant B) — sembol ciktisinin EN SON blogu.
    # Store bu noktada NIHAI (plan_takip -> plan_kur yukarida kostu); kart ayni
    # sozlesmeyi okur (H18). Hata kart uretimini degil yalniz karti dusurur.
    try:
        L.extend(karar_tablosu_karti(symbol, snap, st, d, cfg))
    except Exception as exc:
        msg = "[UYARI] karar tablosu karti hesaplanamadi: " + str(exc)[:120]
        L.append(msg)
        sys.stderr.write(msg + "\n")
    # SADE OZET karti: run() kosu SONUNDA basar (store sozlesmeleri bu noktada NIHAI)
    try:
        _SADE_HOLDER[symbol] = sade_ozet_karti(symbol, snap, st, d, cfg)
    except Exception as exc:
        _SADE_HOLDER[symbol] = []
        sys.stderr.write("[UYARI] sade ozet karti hesaplanamadi: " + str(exc)[:120] + "\n")
    # NIHAI RAPOR (zorunlu format): ayni NIHAI store/d kaynagindan; run() en sonda basar
    try:
        _NIHAI_HOLDER[symbol] = nihai_rapor_karti(symbol, snap, st, d, cfg)
    except Exception as exc:
        _NIHAI_HOLDER[symbol] = []
        sys.stderr.write("[UYARI] nihai rapor karti hesaplanamadi: " + str(exc)[:120] + "\n")
    return "\n".join(L)


def analyze(symbol, cfg=None, btc_bias=None, btc_snap: Optional[Snapshot] = None):
    cfg = cfg or Config()
    snap = build_snapshot(symbol, cfg)
    btc_leader = build_btc_leader_state(snap, btc_snap, cfg) if btc_snap is not None else None
    d = decide(snap, cfg, btc_bias=btc_bias, btc_leader=btc_leader)
    # Ledger kaydindan ONCE: interval/median alanlari kanonik PREDICTION eventine
    # girebilsin. Eski sirada atama append'den sonraydi ve tum bantlar None oluyordu.
    d.fc = _FC_HOLDER.get("v")
    d.plan = _PLAN_HOLDER.get("v")
    # S3: ERKEN UYARI (ayri katman; karar kapisi DEGIL). forecast_kaydet_ve_coz'dan ONCE
    # hesaplanir ki 'onceki kosu' tespiti bu barin taze forecast'ini ONCEKI sanmasin.
    try:
        _st_eu = build_structure(snap.candles, cfg) if len(snap.candles) > cfg.atr_period else None
        d.erken = asdict(erken_uyari(symbol, snap, _st_eu, getattr(d, "scen144", None), cfg))
    except Exception as e:
        d.erken = None
        sys.stderr.write(f"[UYARI] {symbol} erken-uyari hesaplanamadi: {str(e)[:120]}\n")
    try:
        resolve_forward_predictions(symbol, snap.candles, cfg)
        if record_forward_prediction(symbol, snap, d, cfg) is None:
            d.diagnostics.append("ileri-test defterine tahmin yazilamadi/tekrar kayit")
    except Exception as e:
        d.diagnostics.append("ileri-test defteri: " + str(e)[:100])
        sys.stderr.write(f"[DEFTER-UYARI] {symbol}: {str(e)[:120]}\n")
    try:
        d.fc_rapor = forecast_kaydet_ve_coz(symbol, snap, d, cfg)
    except Exception as e:
        d.fc_rapor = []
        sys.stderr.write(f"[UYARI] {symbol} tahmin-sicili hatasi: {str(e)[:120]}\n")
    try:
        record_and_resolve(symbol, d, snap, cfg)
    except Exception as e:
        # kazanc/kayip takibi + kalibrasyon girdisi sessizce durmasin -> gorunur yap (davranis korunur)
        sys.stderr.write(f"[UYARI] {symbol} kayit/cozumleme hatasi: {str(e)[:120]}\n")
    # S3: erken-uyariyi sicile yaz + acik uyarilari MEKANIK coz (onceden yaz -> sonra olc)
    try:
        _eu_rapor = erken_uyari_kaydet_ve_coz(symbol, snap, d, cfg)
        if isinstance(d.erken, dict):
            d.erken["rapor"] = _eu_rapor
    except Exception as e:
        sys.stderr.write(f"[UYARI] {symbol} erken-uyari sicili hatasi: {str(e)[:120]}\n")
    # SUNUM (kullanici direktifi): teknik denetim satirlari ekrandan cikarildi ve karar
    # ciktisi insan-okunur PANEL'e (Sablon-2) cevrildi. render() YINE cagrilir cunku tum
    # store/ledger/mark-live yazimlari ve _SADE/_NIHAI holder'lari onun YAN-ETKILERIDIR
    # (yapisi/kapilar DEGISMEDI); ciktisi ekrana basilmaz. YON_RAW=1 eski tam teknik dokumu
    # geri getirir (hata ayiklama/denetim icin).
    _full = render(symbol, snap, d, cfg)   # <- yan-etkiler (store/ledger/holder) burada olusur
    if os.environ.get("YON_RAW", "") == "1":
        return _full, d, snap
    _st_panel = build_structure(snap.candles, cfg) if len(snap.candles) > cfg.atr_period else None
    return "\n".join(panel_karti(symbol, snap, _st_panel, d, cfg)), d, snap


def run(symbols, cfg=None, hizala=True):
    cfg = cfg or Config()
    # ── F1 fix (kadans): tek-atim kosu, 15m kapanisindan latency butcesi (120sn) icinde
    # degilse bir SONRAKI 15m kapanisina otomatik hizalanir (en fazla ~15dk bekleme).
    # Eski durum: saat-basi (:05) kosu %100 LIVE-LATENCY-BEKLE uretiyordu; sinira hizali
    # kosuda bile 4 karar noktasindan 3'u atlaniyordu (run_loop tam cozumdur ve degismedi;
    # bu hizalama tek-atim kosuyu en azindan HER zaman gecerli bir karar noktasina getirir).
    # YON_HIZALA=0 ile kapatilir.
    # KADANS NOTU: run_loop kendi kuyruk-uykusuyla (_secs_to_next_15m) hizalar; bu yuzden
    # loop ilk atisi ANINDA ciksin diye run'i hizala=False ile cagirir (ilk kosu bayat mum
    # nedeniyle BEKLE verebilir ama tum analiz gorunur; 2. turdan itibaren taze kapanista).
    if hizala and os.environ.get("YON_HIZALA", "1") != "0":
        _butce_s = cfg.ledger_max_latency_ms / 1000.0
        _fetch_payi_s = 30.0            # snapshot kurulumu icin butceden ayrilan pay
        _gecen_s = time.time() % 900.0  # son 15m kapanisindan bu yana (epoch 15m-hizali)
        if _gecen_s > max(10.0, _butce_s - _fetch_payi_s):
            _bekle_s = _secs_to_next_15m()
            print(f"[HIZALAMA] son 15m kapanisindan {int(_gecen_s)}sn gecmis; latency kapisi "
                  f"(izin {int(_butce_s)}sn) bu kosuyu BEKLE'ye cevirirdi. Sonraki kapanisa "
                  f"~{int(_bekle_s // 60)}dk {int(_bekle_s % 60)}sn bekleniyor (YON_HIZALA=0 kapatir).")
            try:
                time.sleep(_bekle_s)
            except KeyboardInterrupt:
                print("[HIZALAMA] bekleme kesildi; mevcut anla devam (latency kapisi calisabilir).")
    ozet = []
    btc_lead = None
    btc_snap = None
    _SADE_HOLDER.clear()   # loop modunda onceki kosunun bayat karti basilmasin
    _NIHAI_HOLDER.clear()
    for s in symbols:
        s = s.strip().upper()
        lead = btc_lead if s != "BTCUSDT" else None
        try:
            # STEP4: BTCUSDT disi sembollerde zengin BTC leader_state gerekir.
            # Liste BTC ile baslamiyorsa tek kez BTC snapshot cekilir; basarisizsa katman susar.
            if s != "BTCUSDT" and getattr(cfg, "btc_leader_enabled", True) and btc_snap is None:
                try:
                    btc_snap = build_snapshot(cfg.btc_core_symbol, cfg)
                    btc_lead = market_bias(btc_snap.candles, cfg) if btc_snap and btc_snap.candles else btc_lead
                except Exception as _be:
                    sys.stderr.write(f"[UYARI] BTC bas-at snapshot alinamadi: {str(_be)[:100]}\n")
                    btc_snap = None
            text, d, snap = analyze(s, cfg, btc_bias=lead, btc_snap=(btc_snap if s != "BTCUSDT" else None))
            if s == "BTCUSDT" and snap.candles:
                btc_snap = snap
                btc_lead = market_bias(snap.candles, cfg)
        except Exception as e:
            text = f"=== {s} (HATA) ===\nKARAR: BEKLE\nSEBEP: {str(e)[:100]}"
            d = _wait("hata")
            sys.stderr.write(f"{s}: {str(e)[:120]}\n")
        print(text)
        print()
        ozet.append((s, d.karar, d.prob))
    print("=" * 52)
    print("OZET")
    print("=" * 52)
    for s, k, g in ozet:
        # PUSU durumu OZET'te: kullanici once buraya bakar — ateslenmis plan gozden kacmasin
        try:
            _pk = _plan_yukle().get(s) or {}
            n_ak = len(_pk.get("aktif", []))
            n_pu = len(_pk.get("pusu", []))
            n_at, n_h, _ns = pusu_karne(s)
            p_txt = (f"pusu:{n_ak} AKTIF!" if n_ak else (f"pusu:{n_pu} kurulu" if n_pu else "pusu:-"))
            if n_at:
                p_txt += f" karne:{n_h}/{n_at}"
        except Exception:
            p_txt = ""
        print(f"  {s:12s} {k:6s} olasilik={g if k in ('LONG', 'SHORT') else '-'}  {p_txt}")
    print("=" * 52)
    for s, _, _ in ozet:
        print(f"  {s:12s} {signals_summary(s)}")
        print(f"  {'':12s} {dsr_report(s, cfg)}")
    print(f"  {'GENEL':12s} {signals_summary(None)}")
    print("=" * 52)
    print("Not: her calistirma o anki KAPANMIS mumlari okur; sinyaller sonraki mumlarla olculur.")
    print(f"Log: {_log_path()}  (YON_PANEL_LOG ile degistirilir). Yatirim tavsiyesi degildir.")
    print("MODEL KARTI (durustluk): parametreler elle-ayarli (panel4->8); walk-forward/OOS ile DOGRULANMADI.")
    print("  fable birlesim: (yon5) mutlak 'sihirli' esikler -> robust-z/quantile veri-goreli olcum")
    print("  (cold-start'ta eski sabite duser); 4s+15m MTF, market/market maliyet modeli + slip,")
    print("  zaman-azalimli ogrenme ve Wilson secim-fix.")
    print("  DSR=N/A: dogrulanmis net-getiri serisi ve tam trial registry yok.")
    print("  KADANS (F1/FABLE6_5): ARGUMANSIZ baslatma artik 15m kapanisina hizali LOOP'tur.")
    print("  Bu tek-atim kosu (sembol argumani veya YON_LOOP=0) F1-hizalamasiyla gecerli TEK")
    print("  karar noktasina cekilir ama 4 kurulumdan 3'unu gormez; kalibrasyon 4x yavas dolar.")
    # ── SADE OZET: teknik ciktiyi okuyamayan kullanici icin kosu-sonu eylem kartlari ──
    # (kullanici isteri; icerik ust bloklarla AYNI kaynaktan gelir -> celisemez)
    print()
    print("=" * 52)
    print("SADE OZET — BU KOSUDA NE YAPMALI? (sade dil)")
    print("Sozluk: LONG=yukselisten kazanc | SHORT=dususten kazanc | PUSU=onceden")
    print("konan bekleyen limit emri | stop=zarar kesme | hedef=kar alma fiyati")
    print("=" * 52)
    for s, _, _ in ozet:
        for ln in (_SADE_HOLDER.get(s) or [f"{s}: ozet uretilemedi (hata/veri yok)"]):
            print(ln)
        print("-" * 52)
    print("Hatirlatma: yuzdeler BU 15dk barinin canli olcumudur (gecmis isabet DEGIL,")
    print("garanti DEGIL). Boyut karari senindir; stop'suz islem ACMA. Tavsiye degildir.")
    # ── NIHAI RAPOR: kullanicinin zorunlu 9-bolum formati (nihai_uygulama_sirasi B18).
    # Icerik ayni kosunun d/store olcumlerinden (H18) -> ust bloklarla celisemez.
    print()
    print("=" * 52)
    print("NIHAI RAPOR — ZORUNLU FORMAT (9 bolum + NET SONUC)")
    print("=" * 52)
    for s, _, _ in ozet:
        for ln in (_NIHAI_HOLDER.get(s) or [f"{s}: nihai rapor uretilemedi (hata/veri yok)"]):
            print(ln)
        print("-" * 52)


# ════════════════════════════════════════════════════════════════════════════
# HIZALI OTOMATIK DONGU (15m mum kapanisina bagli) — CADENCE FIX
# Sorun: motoru saat basi (:05) tek-atim calistirmak 15m motorda kurulumlarin 4'te
# 3'unu atlar (yalniz :00 mumu degerlendirilir) VE kalibrasyon ornekelemi 4x yavas
# ve yanli dolar. Cozum: bir kez baslat, her :00/:15/:30/:45 kapanisindan ~8sn sonra
# (kapanan mum yayimlaninca) otomatik calis. Boylece TUM 15m kurulumlari degerlendirilir
# ve motorun oz-kalibrasyonu duzgun olgunlasir. Yon mantigi DEGISMEZ.
# ════════════════════════════════════════════════════════════════════════════
def _secs_to_next_15m(buffer_s: float = 8.0) -> float:
    """Bir sonraki 15m mum kapanisina (+ kucuk tampon) kalan saniye. Tampon: kapanan
    mumun borsada yayimlanmasi icin ~8sn bekler (motor forming mumu zaten atar)."""
    now = time.time()
    period = 15 * 60
    nxt = (int(now // period) + 1) * period + buffer_s
    return max(1.0, nxt - now)


def run_loop(symbols, cfg=None):
    """Her 15m mum kapanisina hizali surekli calisma. Ctrl+C ile cikis."""
    cfg = cfg or Config()
    print("[LOOP] 15m mum kapanisina hizali otomatik calisma aktif (:00/:15/:30/:45).")
    print("[LOOP] Durdurmak icin Ctrl+C. Ilk calisma simdi (son kapanmis mum ile).")
    while True:
        try:
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print("\n" + "#" * 52)
            print(f"# CALISMA @ {stamp} (son KAPANMIS 15m mum)")
            print("#" * 52)
            # Loop kendi kuyruk-uykusuyla hizalanir; run icindeki hizalama-beklemesini
            # ATLA ki ilk atis ANINDA ciksin (2. turdan itibaren taze kapanis+8sn'de zaten).
            run(symbols, cfg, hizala=False)
        except KeyboardInterrupt:
            print("\n[LOOP] durduruldu.")
            return
        except Exception as e:
            sys.stderr.write(f"[LOOP] hata: {str(e)[:160]}\n")
        wait = _secs_to_next_15m()
        m, s = int(wait // 60), int(wait % 60)
        print(f"\n[LOOP] sonraki 15m kapanisina ~{m}dk {s}sn bekleniyor... (Ctrl+C ile cikis)")
        try:
            time.sleep(wait)
        except KeyboardInterrupt:
            print("\n[LOOP] durduruldu.")
            return


# ════════════════════════════════════════════════════════════════════════════
# WALK-FORWARD BACKTEST (ayni dosya icinde — import gerekmez)
# Her sabit-UTC-fazli origin t'de karar YALNIZ candles[:t+1]'den; sonuc tam t+16
# endpoint DOWN/FLAT/UP etiketiyle olculur. OHLCV+1s cekirdek backtestidir:
# canli execution/orderflow katmanlarinin tam LIVE motor performansini dogrulamaz.
# Kullanim (internet gerekli):  python fable6.py backtest BTCUSDT
#                               python fable6.py backtest BTCUSDT ETHUSDT SOLUSDT DOGEUSDT 800
#                               python fable6.py backtest BTCUSDT 800 fast
# Agsiz harness testi:          python fable6.py btselfcheck
# ════════════════════════════════════════════════════════════════════════════
def _bt_resample_4h(cs):
    """15m -> 4h (no-lookahead; henuz kapanmamis son 4-saat ATILIR)."""
    if not cs:
        return []
    groups: Dict[int, List[Tuple[int, Candle]]] = {}
    for c in cs:
        if c.close_ms is None:
            continue
        open_ms = c.close_ms - 900_000 + 1
        groups.setdefault(open_ms // 14_400_000, []).append((open_ms, c))
    out = []
    for hk in sorted(groups):
        seg = sorted(groups[hk], key=lambda x: x[0])
        expected = [hk * 14_400_000 + j * 900_000 for j in range(16)]
        if len(seg) != 16 or [x[0] for x in seg] != expected:
            continue
        bars = [x[1] for x in seg]
        out.append(Candle(open=bars[0].open, high=max(x.high for x in bars),
                          low=min(x.low for x in bars), close=bars[-1].close,
                          volume=sum(x.volume for x in bars), close_ms=bars[-1].close_ms,
                          quote_volume=sum(x.quote_volume for x in bars),
                          trade_count=sum(x.trade_count for x in bars),
                          taker_buy_base=sum(x.taker_buy_base for x in bars),
                          taker_buy_quote=sum(x.taker_buy_quote for x in bars)))
    return out


def _bt_htf_upto(htf_full, close_ms):
    if close_ms is None:
        return list(htf_full)
    return [h for h in htf_full if h.close_ms is not None and h.close_ms <= close_ms]


# ═══ Bug 1/7: tek ortak bar-ici first-touch motoru (backtest ve LIVE ayni kodu kullanir) ═══
@dataclass
class FillResult:
    """Bar-ici dolus sonucu."""
    filled: bool = False
    fill_price: float = 0.0
    fill_type: str = ""  # "SL", "TP", "TIMEOUT"
    fill_bar_index: int = 0
    bars_elapsed: int = 0


def resolve_first_touch(entry_price: float, stop_loss: float, take_profit: float,
                        side: str, bars: List[Candle], max_bars: int = 10000,
                        gap_slip: bool = False) -> FillResult:
    """Bug 1 & 7: SL-ONCE kotumser tie-break — ayni bar'da hem TP hem SL dokunursa SL kazanir.
    Backtest ve LIVE bit-ozdes bu motoru kullanir (icra tutarsizligi ortadan kalkar).
    Sorun8 ONARIM: gap_slip=True iken mum stop'un OTESINDE acildiysa (bosluk-gecisi)
    dolum stop'ta degil bar.open'da (daha kotu) yazilir; kuyruk riski hafife alinmaz."""
    if side not in ("LONG", "SHORT"):
        raise ValueError(f"resolve_first_touch: side '{side}' gecersiz")
    result = FillResult()
    for i, bar in enumerate(bars[:max_bars]):
        if side == "LONG":
            tp_touched = bar.high >= take_profit
            sl_touched = bar.low <= stop_loss
        else:
            tp_touched = bar.low <= take_profit
            sl_touched = bar.high >= stop_loss
        if sl_touched:  # SL-once (tp+sl ayni bar dahil): kotumser
            result.filled = True
            _fp = stop_loss
            if gap_slip:
                if side == "LONG" and bar.open < stop_loss:
                    _fp = bar.open
                elif side == "SHORT" and bar.open > stop_loss:
                    _fp = bar.open
            result.fill_price = _fp
            result.fill_type = "SL"
            result.fill_bar_index = i
            result.bars_elapsed = i + 1
            return result
        if tp_touched:
            result.filled = True
            result.fill_price = take_profit
            result.fill_type = "TP"
            result.fill_bar_index = i
            result.bars_elapsed = i + 1
            return result
    result.fill_type = "TIMEOUT"
    result.bars_elapsed = min(len(bars), max_bars)
    return result


def calculate_net_pnl(entry_price: float, exit_price: float, side: str, quantity: float,
                      fee_rate: float, spread_bps: float = 0.0,
                      funding_rate: float = 0.0, holding_bars: int = 0) -> float:
    """Net PnL: komisyon + spread + funding dahil (Bug 1)."""
    if side == "LONG":
        gross_pnl = (exit_price - entry_price) * quantity
    else:
        gross_pnl = (entry_price - exit_price) * quantity
    notional_entry = entry_price * quantity
    notional_exit = exit_price * quantity
    fee = (notional_entry + notional_exit) * fee_rate
    spread_cost = (notional_entry + notional_exit) * (spread_bps / 10000)
    funding_cost = 0.0
    if holding_bars > 0 and funding_rate != 0:
        funding_cost = (notional_entry * funding_rate * holding_bars
                        if side == "LONG" else -notional_entry * funding_rate * holding_bars)
    return gross_pnl - fee - spread_cost - funding_cost


def _bt_resolve(cs, t, entry, target, stop, side, H):
    """t+1..t+H: resolve_first_touch (SL-once kotumser tie-break). 1=kazanc,0=kayip."""
    bars = cs[t + 1:min(t + H + 1, len(cs))]
    if not bars:
        return 0, "veri-yok"
    fr = resolve_first_touch(entry, stop, target, side, bars)
    if fr.filled:
        if fr.fill_type == "TP":
            return 1, "hedef"
        if fr.fill_type == "SL":
            return 0, "stop"
    fin = bars[-1].close
    s = sign_eps(fin - entry, entry)
    if s == 0:
        return 0, "sure-doldu-flat"
    if side == "LONG":
        return (1 if s > 0 else 0), "sure-doldu"
    return (1 if s < 0 else 0), "sure-doldu"


def _bt_walk_forward(symbol, candles, cfg, limit_bars=None):
    validate_config(cfg)
    H = cfg.horizon
    N = len(candles)
    htf_full = _bt_resample_4h(candles)
    min_hist = cfg.min_train // 2 + cfg.horizon + 5
    start = max(min_hist, N - limit_bars) if limit_bars else min_hist
    stride = cfg.offline_nonoverlap_stride
    phase_label = (f"UTC-{stride * cfg.interval_ms // 3_600_000}h-grid"
                   if (stride * cfg.interval_ms) % 3_600_000 == 0
                   else f"UTC-{stride * cfg.interval_ms // 60_000}m-grid")
    st = {"symbol": symbol, "n_bar": 0, "signals": 0, "wins": 0, "losses": 0,
          "long": 0, "short": 0, "bekle": 0, "by_regime": {},
          "scen_pusu_long": 0, "scen_pusu_short": 0,  # F9: yon uretildi ama MARKET gate'lendi -> PUSU
          "brier_sum": 0.0, "logloss_sum": 0.0,
          "prob_class_hit": {c: [0, 0] for c in CLASSES},
          "selective_class_hit": {c: [0, 0] for c in CLASSES},
          "confusion": {t: {p: 0 for p in CLASSES} for t in CLASSES},
          "hit_seq": [], "paired_momentum_diff": [], "records": [], "cohort_times": [],
          "benchmarks": {k: {"n": 0, "hit": 0, "class_hit": {c: [0, 0] for c in CLASSES}}
                         for k in ("no_change", "momentum", "past_majority")},
          "stride": stride, "phase": phase_label, "errors": 0}
    last = N - 1 - H
    atrs_full = atr_series(candles, cfg.atr_period)
    past_truths: List[int] = []

    def _cohort(i: int) -> bool:
        cm = candles[i].close_ms
        return (((cm + 1) % (st["stride"] * cfg.interval_ms) == 0)
                if cm is not None else (i % st["stride"] == 0))

    for t in range(start, last + 1):
        if not _cohort(t):
            continue
        # Yalniz bu tahmin aninda sonucu olgunlasmis sabit-faz kohortlari.
        past_truths = []
        for i in range(H, t - H + 1):
            if _cohort(i):
                yy_prev = endpoint_label(candles, i, atrs_full, cfg)
                if yy_prev in CLASSES:
                    past_truths.append(yy_prev)
        sub = candles[:t + 1]
        snap = Snapshot(symbol=symbol, candles=sub,
                        htf=_bt_htf_upto(htf_full, candles[t].close_ms),
                        orderflow=None, book=None, funding=None,
                        funding_hist=None, taker_ratio=None, stale=False,
                        last_closed_ms=candles[t].close_ms,
                        data_watermark_ms=candles[t].close_ms)
        try:
            d = decide(snap, cfg, context=DecisionContext.offline(candles[t].close_ms))
        except Exception as e:
            st["errors"] += 1
            sys.stderr.write(f"[bar {t}] decide hata: {str(e)[:80]}\n"); continue
        truth = endpoint_label(candles, t, atrs_full, cfg)
        if truth is None:
            continue
        st["n_bar"] += 1
        st["cohort_times"].append(candles[t].close_ms)
        ps = normalize_probs(d.p_down, d.p_flat, d.p_up)
        st["brier_sum"] += sum((ps[k] - (1.0 if truth == CLASSES[k] else 0.0)) ** 2
                                for k in range(3))
        st["logloss_sum"] += -math.log(max(1e-12, ps[CLASSES.index(truth)]))
        prob_pred = argmax_class(ps, cfg.tie_eps_rel)
        st["prob_class_hit"][truth][1] += 1
        st["prob_class_hit"][truth][0] += int(prob_pred == truth)
        st["confusion"][truth][prob_pred] += 1

        mom_move = candles[t].close - candles[max(0, t - H)].close
        mom_pred = sign_eps(mom_move, candles[t].close, cfg.tie_eps_rel,
                            cfg.label_neutral_atr * atrs_full[t])
        counts = {c: past_truths.count(c) for c in CLASSES}
        mx = max(counts.values()) if counts else 0
        winners = [c for c in CLASSES if counts.get(c, 0) == mx]
        prior_pred = winners[0] if len(winners) == 1 else 0
        for name, bp in (("no_change", 0), ("momentum", mom_pred),
                         ("past_majority", prior_pred)):
            b = st["benchmarks"][name]
            bh = int(bp == truth)
            b["n"] += 1; b["hit"] += bh
            b["class_hit"][truth][1] += 1
            b["class_hit"][truth][0] += bh
        if d.karar not in ("LONG", "SHORT"):
            st["bekle"] += 1
            # F9: senaryo-yon yonu URETTI ama MARKET kapisi kesti -> o yonde PUSU (kor BEKLE degil)
            if getattr(d, "scen_driven", False) and getattr(d, "scen_side", None) in ("LONG", "SHORT"):
                st["scen_pusu_long" if d.scen_side == "LONG" else "scen_pusu_short"] += 1
            continue
        pred = 1 if d.karar == "LONG" else -1
        win = int(pred == truth)
        st["signals"] += 1
        st["long" if d.karar == "LONG" else "short"] += 1
        st["wins" if win else "losses"] += 1
        st["hit_seq"].append(win)
        st["records"].append({"time": candles[t].close_ms, "hit": win,
                              "truth": truth, "pred": pred,
                              "momentum_hit": int(mom_pred == truth),
                              "paired_diff": win - int(mom_pred == truth)})
        st["paired_momentum_diff"].append(win - int(mom_pred == truth))
        st["selective_class_hit"][truth][1] += 1
        st["selective_class_hit"][truth][0] += win
        br = st["by_regime"].setdefault(d.regime or "NORMAL", {"n": 0, "w": 0})
        br["n"] += 1; br["w"] += win
    st["coverage"] = st["signals"] / max(1, st["n_bar"])
    st["min_coverage"] = cfg.min_directional_coverage
    st["coverage_ok"] = st["coverage"] >= cfg.min_directional_coverage
    st["accuracy"] = st["wins"] / max(1, st["signals"])
    recalls = [w / n for w, n in st["prob_class_hit"].values() if n > 0]
    st["balanced_accuracy"] = mean(recalls) if recalls else 0.0
    srecalls = [w / n for w, n in st["selective_class_hit"].values() if n > 0]
    st["selective_balanced_accuracy"] = mean(srecalls) if srecalls else 0.0
    st["class_hit"] = st["prob_class_hit"]  # eski okuyucular icin dogru semantik alias
    st["brier"] = st["brier_sum"] / max(1, st["n_bar"])
    st["logloss"] = st["logloss_sum"] / max(1, st["n_bar"])
    st["effective_n"] = st["n_bar"]
    st["min_effective"] = cfg.backtest_min_effective
    st["effective_ok"] = st["effective_n"] >= cfg.backtest_min_effective
    for b in st["benchmarks"].values():
        b["accuracy"] = b["hit"] / max(1, b["n"])
        br = [w / n for w, n in b["class_hit"].values() if n]
        b["balanced_accuracy"] = mean(br) if br else 0.0
    st["accuracy_ci"] = _moving_block_ci(st["hit_seq"], cfg.bootstrap_reps,
                                          seed=_sha256_obj(symbol)[:8])
    st["paired_momentum_ci"] = _moving_block_ci(st["paired_momentum_diff"],
                                                  cfg.bootstrap_reps,
                                                  seed=symbol + "-paired-momentum")
    plo, phi = st["paired_momentum_ci"]
    st["superiority_vs_momentum"] = bool(
        st["effective_ok"] and st["coverage_ok"]
        and st["signals"] >= cfg.backtest_min_effective
        and plo is not None and plo > 0.0)
    return st


def _moving_block_ci(xs: List[float], reps: int = 1000, block: Optional[int] = None,
                     seed: Any = 1) -> Tuple[Optional[float], Optional[float]]:
    """Kucuk, deterministik moving-block bootstrap ortalama %95 araligi.
    F16 fix: blok uzunlugu verilmezse n^(1/3) kurali (taban 2) — sabit blok=2,
    lag-2 otesi seri bagimliligi yok sayip CI'yi asiri daraltiyordu."""
    if len(xs) < 4 or reps <= 0:
        return None, None
    n = len(xs)
    if block is None:
        block = max(2, int(round(n ** (1.0 / 3.0))))
    b = max(1, min(block, n))
    starts = list(range(0, n - b + 1))
    rng = random.Random(str(seed))
    vals = []
    for _ in range(reps):
        sample = []
        while len(sample) < n:
            j = rng.choice(starts)
            sample.extend(xs[j:j + b])
        vals.append(mean(sample[:n]))
    vals.sort()
    return vals[int(0.025 * (reps - 1))], vals[int(0.975 * (reps - 1))]


def _bt_print(st):
    n = st["signals"]
    print("=" * 56)
    print(f"  {st['symbol']} — {st['n_bar']} ortusmeyen 4s kohort "
          f"(faz={st['phase']}, min-N {st['min_effective']}: "
          f"{'GECTI' if st['effective_ok'] else 'KALDI'})")
    print("-" * 56)
    print(f"  Sinyal: {n}   (LONG={st['long']} SHORT={st['short']} | BEKLE={st['bekle']})")
    _spl, _sps = st.get("scen_pusu_long", 0), st.get("scen_pusu_short", 0)
    if _spl or _sps:
        print(f"  F9 SENARYO-YON (yon uretildi, MARKET gate'lendi -> PUSU; KANITLANMAMIS kenar): "
              f"PUSU-LONG={_spl} PUSU-SHORT={_sps}")
    if n:
        lo, hi = st["accuracy_ci"]
        ci = (f" [%95 blok-bootstrap {lo*100:.1f}-{hi*100:.1f}]"
              if lo is not None else " [GA yetersiz]")
        print(f"  SECICI YON ISABETI: %{st['accuracy']*100:.1f}{ci} "
              f"(dogru={st['wins']} yanlis={st['losses']})")
        print(f"  KAPSAM: %{st['coverage']*100:.1f} "
              f"[min %{st['min_coverage']*100:.0f}: {'GECTI' if st['coverage_ok'] else 'KALDI'}] "
              f"| secici balanced-accuracy=%{st['selective_balanced_accuracy']*100:.1f}")
        if st["by_regime"]:
            print("  Rejim bazinda isabet:")
            for rg, v in sorted(st["by_regime"].items(), key=lambda kv: -kv[1]["n"]):
                print(f"    {rg:22s} n={v['n']:4d}  isabet=%{v['w']/v['n']*100:.0f}")
    else:
        print("  Sinyal uretilmedi (motor bu pencerede hep BEKLE — cok secici).")
    print(f"  TUM KOHORT endpoint3: balanced-accuracy=%{st['balanced_accuracy']*100:.1f} "
          f"| Brier={st['brier']:.4f} log-loss={st['logloss']:.4f}")
    print("  Onceden tanimli endpoint referanslari:")
    for name, label in (("no_change", "no-change/FLAT"),
                        ("momentum", "4s momentum"),
                        ("past_majority", "gecmis sinif-cogunlugu")):
        b = st["benchmarks"][name]
        print(f"    {label:24s} accuracy=%{b['accuracy']*100:.1f} "
              f"balanced=%{b['balanced_accuracy']*100:.1f} n={b['n']}")
    plo, phi = st["paired_momentum_ci"]
    if plo is None:
        print("  SECICI KARAR - MOMENTUM: paired blok-GA yetersiz; ustunluk KANITLANMADI")
    else:
        print(f"  SECICI KARAR - MOMENTUM: ort fark "
              f"%{mean(st['paired_momentum_diff'])*100:+.1f}, %95 blok-GA "
              f"[%{plo*100:+.1f}, %{phi*100:+.1f}] -> "
              f"{'USTUNLUK KAPISI GECTI' if st['superiority_vs_momentum'] else 'USTUNLUK KANITLANMADI'}")
    if st.get("errors"):
        print(f"  GECERSIZ: {st['errors']} karar hatasi (nakit/0 getiri sayilmadi)")
    print("=" * 56)


def run_backtest(symbols, limit_bars=None, fast=False):
    cfg = Config()
    if fast:
        cfg.mc_paths = 800
        print("[FAST] mc_paths=800 (hizli on-tarama; kesin olcum icin 'fast'siz calistir)")
    print("FABLE6 WALK-FORWARD — ortusmeyen 4s endpoint kohortu (OFFLINE saf baglam)")
    print("Bu rapor maliyet-sonrasi ekonomik edge veya canli mikro-katman katkisi kaniti degildir.\n")
    g = {"n": 0, "w": 0, "eligible": 0, "records": []}
    for s in symbols:
        s = s.strip().upper()
        try:
            candles = fetch_klines(s, "15m", cfg.kline_limit)
        except Exception as e:
            print(f"  {s}: veri cekilemedi — {str(e)[:80]}"); continue
        if len(candles) < cfg.min_train:
            print(f"  {s}: yetersiz mum ({len(candles)})"); continue
        st = _bt_walk_forward(s, candles, cfg, limit_bars)
        _bt_print(st)
        g["n"] += st["signals"]; g["w"] += st["wins"]; g["eligible"] += st["n_bar"]
        g["records"].extend(st["records"])
    if g["n"]:
        by_time: Dict[int, List[int]] = {}
        for r in g["records"]:
            by_time.setdefault(r["time"], []).append(r["hit"])
        time_scores = [mean(by_time[t]) for t in sorted(by_time)]
        lo, hi = _moving_block_ci(time_scores, cfg.bootstrap_reps, seed="multi-asset")
        ci = f", zaman-kumeli GA %{lo*100:.1f}-%{hi*100:.1f}" if lo is not None else ", GA yetersiz"
        print(f"\nGENEL SECICI ISABET: %{g['w']/g['n']*100:.1f} "
              f"(sinyal={g['n']}, kapsam=%{g['n']/max(1,g['eligible'])*100:.1f}{ci})")


def bt_selfcheck():
    """Agsiz: sentetik mumlarda backtest harness'inin calistigini dogrular."""
    print("BACKTEST SELF-CHECK (agsiz, sentetik) — harness boru hatti\n")
    cfg = Config(); cfg.mc_paths = 400
    for name, tr, vol in [("UPTREND", 0.004, 0.012), ("DOWNTREND", -0.004, 0.012),
                          ("CHOP", 0.0, 0.010), ("VOLATILE", 0.001, 0.03)]:
        cs = _synthetic_candles(400, seed=_SAHNE_SEED[name], trend=tr, vol=vol)  # sabit seed (hash tuzlanir)
        for i, c in enumerate(cs):
            if c.close_ms is None:
                c.close_ms = 1_700_000_000_000 + i * 900_000
        _bt_print(_bt_walk_forward(name, cs, cfg, limit_bars=None))
    print("\nBACKTEST SELF-CHECK bitti. Gercek olcum: python fable6.py backtest BTCUSDT")


# ════════════════════════════════════════════════════════════════════════════
# CPCV OAT-KISMI TANI — OFFLINE OVERFIT GOSTERGESI
# Tam model/trial registry olmadigi icin formal PBO iddiasi YOKTUR:
#   1) (satir x varyant) getiri matrisi: her satir bir karar-bari; her varyant
#      anahtar Config sabitlerinin OAT carpani; hucre = o kararin R-katsayi getirisi
#      (decide no-lookahead, cozum _bt_resolve mekanigiyle t+1..t+H).
#   2) CSCV: donem S esit bloga bolunur; TUM C(S,S/2) egitim/test bolunmesinde
#      egitimde argmax varyant secilir, testte o varyantin rank'i bulunur;
#      lambda = logit(rank/(N+1)); PBO = P(lambda < 0).
#   3) PURGE: egitim/test blok sinirlarinda etiket-penceresi kadar egitim satiri
#      atilir (gerekce: _cscv_split_rows docstring; mekanik kanit selftest [CPCV]).
# Kullanim:  python fable6.py cpcv BTCUSDT         (internet; tam olcum)
#            python fable6.py cpcv BTCUSDT fast    (kaba on-olcum)
#            python fable6.py cpcv sentetik fast   (AGSIZ kanit/regresyon)
# Sonuc kucuk JSON cache'e yazilir ve raporda "OAT-PBO-tani" etiketiyle gosterilir;
# cache yoksa PBO=N/A kalir.
# ════════════════════════════════════════════════════════════════════════════
def _cpcv_cache_path():
    """CPCV sonuc onbellegi: YON_CPCV_CACHE ile tasinabilir; yoksa sinyal logunun
    YANINDA ayri dosya (sinyal loguna KARISMAZ). Dosya yoksa dsr_report eski
    'PBO=N/A' davranisinda kalir (cold-start korunur)."""
    p = os.environ.get("YON_CPCV_CACHE")
    if p:
        return p
    d = os.path.dirname(_log_path())
    return os.path.join(d, "yon_cpcv.json") if d else "yon_cpcv.json"


_CPCV_CACHE_CORRUPT = False


def _cpcv_cache_load():
    # KORUMA-SIMETRISI FIX (denetim): sessiz {} donusu, sonraki kayitta DIGER
    # sembollerin OLCULMUS PBO'sunu uyarisiz siliyordu (plan/uzlasmazlik/sinyal
    # store'lariyla ayni kusur sinifi; onlar korunmustu, bu dosya unutulmustu).
    global _CPCV_CACHE_CORRUPT
    try:
        if not os.path.exists(_cpcv_cache_path()):
            _CPCV_CACHE_CORRUPT = False
            return {}
        with open(_cpcv_cache_path(), "r", encoding="utf-8") as f:
            obj = json.load(f)
        if not isinstance(obj, dict):
            raise ValueError("cpcv cache dict degil")
        _CPCV_CACHE_CORRUPT = False
        return obj
    except Exception as e:
        sys.stderr.write(f"[UYARI] cpcv cache okunamadi/bozuk ({_cpcv_cache_path()}): {str(e)[:80]}\n")
        _CPCV_CACHE_CORRUPT = True
        return {}


def _cpcv_cache_save(symbol, rec):
    try:
        obj = _cpcv_cache_load()
        yol = _cpcv_cache_path()
        if _CPCV_CACHE_CORRUPT and os.path.exists(yol):
            try:
                os.replace(yol, yol + ".bozuk")
                sys.stderr.write(f"[UYARI] bozuk cpcv cache yedeklendi: {yol}.bozuk\n")
            except Exception as exc:
                raise OSError("bozuk cpcv cache yedeklenemedi; yazma reddedildi") from exc
        obj[symbol] = rec
        tmp = yol + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
        os.replace(tmp, yol)   # ATOMIK (plan/sinyal/tahmin store'lariyla ayni koruma)
    except Exception as e:
        sys.stderr.write(f"[UYARI] cpcv cache yazilamadi: {str(e)[:80]}\n")


def cpcv_compat_hash(mod: str, cfg: Optional[Config] = None) -> str:
    """FAST/TAM tanisinin karar+arama uzayi imzasi; hesap-yolu sayisi moda gore kurulur."""
    cfg = cfg or Config()
    m = str(mod).lower()
    if m not in ("fast", "tam"):
        raise ValueError("cpcv mod fast veya tam olmali")
    diag = replace(cfg, mc_paths=(cfg.cpcv_mc_paths_fast if m == "fast"
                                  else cfg.cpcv_mc_paths))
    return _sha256_obj({"model_hash": model_hash(diag), "feature_hash": feature_hash(),
                        "scope": "OAT-partial-diagnostic", "mod": m,
                        "S": (diag.cpcv_blocks_fast if m == "fast" else diag.cpcv_blocks),
                        "rows_per_block": (diag.cpcv_rows_per_block_fast if m == "fast"
                                           else diag.cpcv_rows_per_block),
                        "knobs": diag.cpcv_knobs, "mults": diag.cpcv_mults,
                        "stride": diag.cpcv_stride, "protocol": diag.protocol_id})


def _cpcv_pbo_txt(symbol):
    """Kayitli kismi OAT-CPCV tanisini okur; yok/eski nesilde PBO=N/A."""
    try:
        e = _cpcv_cache_load().get(symbol)
        if not e or e.get("pbo") is None:
            return "PBO=N/A"
        mod = str(e.get("mod", "")).lower()
        if (e.get("feature_hash") != feature_hash()
                or e.get("protocol_id") != Config().protocol_id
                or e.get("scope") != "OAT-partial-diagnostic"
                or e.get("compat_hash") != cpcv_compat_hash(mod, Config())):
            return "PBO=N/A [cache nesli eski]"
        gun = max(0.0, (time.time() - float(e.get("ts", 0.0))) / 86400.0)
        ek = "" if e.get("guvenilir") else " KALIBRE-DEGIL"
        return ("OAT-PBO-tani=%.2f [kismi cpcv %s S=%d bolunme=%d sinyal=%d %.0fg once%s]"
                % (float(e["pbo"]), e.get("mod", "?"), int(e.get("S", 0)),
                   int(e.get("n_split_gecerli", 0)), int(e.get("n_sinyal", 0)), gun, ek))
    except Exception:
        return "PBO=N/A"


def _cpcv_variants(cfg, knobs=None):
    """Varyant kumesi: taban + anahtar sabitlerde tek-faktor (OAT) x cpcv_mults.
    4 knob x 2 carpan + taban = 9 varyant. Kartezyen 81 BILEREK yoktur:
    OAT yalniz eksen-bazli kismi duyarlilik ornekler; kombinasyon uzayini temsil etmez."""
    from dataclasses import replace as _rep
    if knobs is None:
        knobs = cfg.cpcv_knobs
    out = [("taban", cfg)]
    for k in knobs:
        for m in cfg.cpcv_mults:
            out.append((f"{k}x{m:g}", _rep(cfg, **{k: getattr(cfg, k) * m})))
    return out


def _cpcv_purge_rows(cfg):
    """Satir-olceginde purge genisligi. Satir t'nin etiketi candles(t, t+H]
    penceresinden cozulur; iki satirin pencereleri ancak bar-mesafesi <= H ise
    kesisir. Satir adimi 'stride' bar oldugundan satir-mesafesi ceil(H/stride)
    yeterli VE gereklidir."""
    return (cfg.horizon + cfg.cpcv_stride - 1) // cfg.cpcv_stride


def _cpcv_r_multiple(cs, t, d, H):
    """Kararin R-katsayi getirisi (_bt_resolve ile AYNI vurulma onceligi).
    F4 (FABLE6_5): R artik MALIYET-SONRASIDIR (d.cost_abs; yoksa 0 = eski davranis):
    hedef -> (odul-maliyet)/risk, stop/ayni-bar -> -(risk+maliyet)/risk,
    sure-doldu -> (isaretli yol - maliyet)/risk [alt/ust sinira kirpilir].
    BEKLE/gecersiz -> None."""
    if d.karar not in ("LONG", "SHORT") or d.entry is None or d.target is None or d.stop is None:
        return None
    risk = (d.entry - d.stop) if d.karar == "LONG" else (d.stop - d.entry)
    if risk <= 0:
        return None
    cost = max(0.0, float(getattr(d, "cost_abs", 0.0) or 0.0))
    reward = (d.target - d.entry) if d.karar == "LONG" else (d.entry - d.target)
    rr_net = (reward - cost) / risk
    loss_net = -(risk + cost) / risk
    _win, how = _bt_resolve(cs, t, d.entry, d.target, d.stop, d.karar, H)
    if how == "hedef":
        return rr_net
    if how in ("stop", "ayni-bar"):
        return loss_net
    end = min(t + H, len(cs) - 1)                       # sure-doldu
    fin = cs[end].close
    r = (((fin - d.entry) if d.karar == "LONG" else (d.entry - fin)) - cost) / risk
    return _clip(r, loss_net, rr_net)


def _cpcv_matrix(symbol, candles, cfg, variants, n_rows, progress=False):
    """(satir x varyant) getiri matrisi. Her satir bir karar-bari t: decide()
    YALNIZ candles[..t]'yi gorur (no-lookahead; cpcv_hist_cap yalniz GECMISI
    kisaltir, gelecege dokunmaz), sonuc candles[t+1..t+H] ile cozulur. Satirlar
    cpcv_stride bar aralikli ve serinin SONUNDAN geriye yerlesir. Deterministik:
    decide ayni girdiyle ayni cikti (DUSMAN-4 kanitli), burada RNG yok."""
    H, stride = cfg.horizon, cfg.cpcv_stride
    N = len(candles)
    warm = cfg.min_train // 2 + H + 5                   # _bt_walk_forward ile ayni isinma
    last = N - 1 - H
    max_rows = (last - warm) // stride + 1 if last >= warm else 0
    n_rows = min(n_rows, max_rows)
    if n_rows < 2:
        return None
    rows_t = [last - stride * (n_rows - 1 - i) for i in range(n_rows)]
    htf_full = _bt_resample_4h(candles)
    M = []
    stats = [{"ad": ad, "sinyal": 0, "kazanc": 0, "r_top": 0.0, "hata": 0}
             for ad, _ in variants]
    t_bas = time.time()
    for i, t in enumerate(rows_t):
        lo = max(0, t + 1 - cfg.cpcv_hist_cap)
        sub = candles[lo:t + 1]
        htf = _bt_htf_upto(htf_full, candles[t].close_ms)
        row = []
        row_invalid = False
        for vi, (_ad, vcfg) in enumerate(variants):
            r = None
            try:
                d = decide(Snapshot(symbol=symbol, candles=sub, htf=htf, stale=False,
                                    last_closed_ms=candles[t].close_ms,
                                    data_watermark_ms=candles[t].close_ms), vcfg,
                           context=DecisionContext.offline(candles[t].close_ms))
                r = _cpcv_r_multiple(candles, t, d, H)
            except Exception as e:
                stats[vi]["hata"] += 1
                row_invalid = True
                sys.stderr.write(f"[cpcv satir {i}] decide hata: {str(e)[:60]}\n")
            if r is None:
                row.append(0.0)
            else:
                row.append(r)
                stats[vi]["sinyal"] += 1
                stats[vi]["kazanc"] += 1 if r > 0 else 0
                stats[vi]["r_top"] += r
        if not row_invalid:
            M.append(row)
        if progress and (i + 1) % max(1, n_rows // 8) == 0:
            gecen = time.time() - t_bas
            kalan = gecen / (i + 1) * (n_rows - i - 1)
            print(f"  ... satir {i + 1}/{n_rows} ({len(variants) * (i + 1)} decide, "
                  f"{gecen:.0f} sn; kalan ~{kalan:.0f} sn)")
    return {"M": M, "stats": stats, "rows_t": rows_t,
            "invalid_rows": n_rows - len(M)}


# ═══ Bug 2: CPCV aday-manifest muhru + PBO DURUST etiket (formal CSCV vs heuristik yaklasim) ═══
@dataclass
class CandidateManifest:
    """OOS oncesi dondurulmus aday manifest'i. SHA-256 ile muhurlenir (seal-before-test)."""
    candidates: List[Any] = field(default_factory=list)
    frozen_at_ms: int = 0
    sha256: str = ""

    def seal(self) -> str:
        self.frozen_at_ms = int(time.time() * 1000)
        payload = json.dumps({"candidates": self.candidates, "frozen_at_ms": self.frozen_at_ms},
                             sort_keys=True, default=str)
        self.sha256 = hashlib.sha256(payload.encode()).hexdigest()
        return self.sha256

    def verify(self) -> bool:
        if not self.sha256:
            return False
        payload = json.dumps({"candidates": self.candidates, "frozen_at_ms": self.frozen_at_ms},
                             sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest() == self.sha256


@dataclass
class PBOAssessment:
    """PBO degerlendirme sonucu; durust etiketleme (formal CSCV mi, heuristik yaklasim mi)."""
    pbo_value: float
    is_formal_pbo: bool
    manifest_sha256: str
    n_candidates: int
    n_paths: int
    method: str  # "CSCV" veya "HEURISTIC_APPROX"
    assessed_at_ms: int
    notes: str = ""

    @property
    def label(self) -> str:
        if self.is_formal_pbo:
            return f"FORMAL_CSCV_PBO={self.pbo_value:.4f}"
        return f"HEURISTIC_PBO={self.pbo_value:.4f} (formal_degil)"


def freeze_candidates(candidates: List[Any]) -> CandidateManifest:
    """OOS oncesi aday listesini dondur ve muhurle (Bug 2)."""
    manifest = CandidateManifest(candidates=list(candidates))
    manifest.seal()
    return manifest


def _cscv_split_rows(T, S, test_blocks, purge_rows):
    """Blok sinirlari + PURGE (NO-LOOKAHEAD gerekcesi): satir t'nin etiketi
    GELECEK (t, t+H] penceresinden cozulur. Egitim satiri ile test satirinin
    satir-mesafesi <= purge_rows (~H) ise etiket pencereleri KESISIR -> test
    donemine ait fiyat bilgisi egitimdeki varyant-secimine sizar (Lopez de
    Prado'nun 'purged CV' gerekcesi). Bu yuzden her test blogunun IKI yaninda
    purge_rows satir egitimden atilir (simetrik atma = purge + embargo tek
    hamlede; sonraki blok da onceki blogun etiketini gorur cunku kesisim
    simetriktir). Mekanik kanit: selftest [CPCV] purge testi."""
    bounds = [(b * T // S, (b + 1) * T // S) for b in range(S)]
    tset = set(test_blocks)
    train_rows, test_rows = [], []
    for b, (lo, hi) in enumerate(bounds):
        (test_rows if b in tset else train_rows).extend(range(lo, hi))
    tb = [bounds[b] for b in sorted(tset)]
    keep = [r for r in train_rows
            if all(r < lo - purge_rows or r >= hi + purge_rows for lo, hi in tb)]
    return keep, test_rows


def _cscv_pbo(M, S, purge_rows):
    """CSCV cekirdegi (Bailey–Borwein–Lopez de Prado–Zhu 2015, 'The Probability
    of Backtest Overfitting'): S blok, TUM C(S,S/2) egitim/test bolunmesi.
    Performans olcusu: satir-basi ortalama R (sinyalsiz satir 0; varyantlar
    ayni satir-kumesinde kiyaslanir -> olcek adil). Egitimde argmax varyant
    (esitlikte en dusuk indeks = deterministik), testte o varyantin ortalama-rank'i
    (beraberlik = ortalama rank); omega = rank/(N+1), lambda = logit(omega),
    PBO = P(lambda < 0). Testte TUM varyantlar esitse bolunme BILGISIZ ->
    sayilir ama PBO'ya girmez (durust: rapor eder)."""
    T = len(M)
    N = len(M[0]) if T else 0
    if T < 2 * S or N < 2 or S % 2 or S < 2:
        return None
    from itertools import combinations as _comb
    lams = []
    n_secimsiz = n_tie = n_split = 0
    sel_cnt = [0] * N
    is_sum = [0.0] * N
    oos_sum = [0.0] * N
    sec_is, sec_oos = [], []
    for test_blocks in _comb(range(S), S // 2):
        train_rows, test_rows = _cscv_split_rows(T, S, test_blocks, purge_rows)
        if not train_rows or not test_rows:
            n_secimsiz += 1
            continue
        p_is = [sum(M[r][v] for r in train_rows) / len(train_rows) for v in range(N)]
        p_oos = [sum(M[r][v] for r in test_rows) / len(test_rows) for v in range(N)]
        n_split += 1
        for v in range(N):
            is_sum[v] += p_is[v]
            oos_sum[v] += p_oos[v]
        mx = max(p_is)
        if mx <= min(p_is):                     # egitimde herkes esit -> secim anlamsiz
            n_secimsiz += 1
            continue
        best = p_is.index(mx)
        sel_cnt[best] += 1
        sec_is.append(p_is[best])
        sec_oos.append(p_oos[best])
        if max(p_oos) <= min(p_oos):            # test tamamen esit -> rank bilgisiz
            n_tie += 1
            continue
        pb = p_oos[best]
        rank = (1.0 + sum(1 for v in range(N) if p_oos[v] < pb)
                + 0.5 * sum(1 for v in range(N) if v != best and p_oos[v] == pb))
        omega = rank / (N + 1.0)
        lams.append(math.log(omega / (1.0 - omega)))
    ort = lambda xs: (sum(xs) / len(xs)) if xs else 0.0
    return {"pbo": (sum(1 for l in lams if l < 0) / len(lams)) if lams else None,
            "lambdas": lams, "S": S, "N": N,
            "n_split_toplam": math.comb(S, S // 2), "n_split_gecerli": len(lams),
            "n_tie": n_tie, "n_secimsiz": n_secimsiz, "sel_cnt": sel_cnt,
            "is_ort": [x / max(1, n_split) for x in is_sum],
            "oos_ort": [x / max(1, n_split) for x in oos_sum],
            "sec_is_ort": ort(sec_is), "sec_oos_ort": ort(sec_oos)}


def run_cpcv(target, fast=False):
    """OAT varyantlari icin kismi CPCV tanisi; tam trial-registry PBO iddiasi degildir."""
    from dataclasses import replace as _rep
    taban = Config()
    cfg = _rep(taban, mc_paths=(taban.cpcv_mc_paths_fast if fast else taban.cpcv_mc_paths))
    S = cfg.cpcv_blocks_fast if fast else cfg.cpcv_blocks
    rpb = cfg.cpcv_rows_per_block_fast if fast else cfg.cpcv_rows_per_block
    n_rows = S * rpb
    variants = _cpcv_variants(cfg)
    purge = _cpcv_purge_rows(cfg)
    sym = (target or "SENTETIK").strip().upper()
    sentetik = sym in ("SENTETIK", "SYNTH")
    if sentetik:
        sym = "SENTETIK"
    warm = cfg.min_train // 2 + cfg.horizon + 5
    gerek = warm + cfg.cpcv_stride * n_rows + cfg.horizon + cfg.cpcv_stride
    print("=" * 64)
    print(f"CPCV OAT-KISMI TANI — {sym} mod={'FAST' if fast else 'TAM'} [FORMAL PBO DEGIL]")
    print(f"PLAN (kosumdan ONCE): {len(variants)} varyant x {n_rows} satir "
          f"(stride={cfg.cpcv_stride} bar) = {len(variants) * n_rows} decide cagrisi")
    print(f"      S={S} blok -> C({S},{S // 2})={math.comb(S, S // 2)} bolunme; "
          f"purge={purge} satir (~horizon {cfg.horizon} bar); mc_paths={cfg.mc_paths}")
    print(f"VERI: {gerek} mum (isinma {warm} + {cfg.cpcv_stride}x{n_rows} satir + ufuk {cfg.horizon})")
    if sentetik:
        candles = _synthetic_candles(gerek, cfg.cpcv_sent_seed,
                                     cfg.cpcv_sent_trend, cfg.cpcv_sent_vol)
        print(f"SENTETIK seri: seed={cfg.cpcv_sent_seed} trend={cfg.cpcv_sent_trend:+g} "
              f"vol={cfg.cpcv_sent_vol:g} (agsiz, deterministik)")
    else:
        try:
            candles = fetch_klines(sym, "15m", gerek + 2)
        except Exception as e:
            print(f"HATA: veri cekilemedi — {str(e)[:80]}")
            return None
        if len(candles) < gerek:
            print(f"HATA: {sym} icin {len(candles)} mum geldi, {gerek} gerekli "
                  f"(internet yok / sembol yanlis?). Agsiz kanit: python fable6.py cpcv sentetik fast")
            return None
    t0 = time.time()
    mres = _cpcv_matrix(sym, candles, cfg, variants, n_rows, progress=True)
    if mres is None:
        print("HATA: yeterli bar yok (matris kurulamadi).")
        return None
    res = _cscv_pbo(mres["M"], S, purge)
    _cpcv_report(sym, cfg, variants, mres, res, fast, time.time() - t0)
    return {"matris": mres, "cscv": res}


def _cpcv_report(sym, cfg, variants, mres, res, fast, sure):
    """CPCV raporu + cache kaydi. Etiketler DURUST: az sinyal / az gecerli
    bolunme -> KALIBRE DEGIL (sayi yine basilir ama 'gosterge' damgasi yer)."""
    stats = mres["stats"]
    n_sinyal = max(s["sinyal"] for s in stats)
    print("-" * 64)
    print(f"KOSUM: {sure:.0f} sn | satir={len(mres['M'])} | en-aktif varyant sinyali={n_sinyal}")
    print(f"  {'varyant':>18s} {'sinyal':>6s} {'isabet%':>7s} {'ortR':>6s} "
          f"{'IS-ortR':>8s} {'OOS-ortR':>9s} {'IS-sec':>6s}")
    for vi, (ad, _) in enumerate(variants):
        s = stats[vi]
        hit = 100.0 * s["kazanc"] / s["sinyal"] if s["sinyal"] else 0.0
        ortr = s["r_top"] / s["sinyal"] if s["sinyal"] else 0.0
        is_o = res["is_ort"][vi] if res else float("nan")
        oos_o = res["oos_ort"][vi] if res else float("nan")
        sec = res["sel_cnt"][vi] if res else 0
        print(f"  {ad:>18s} {s['sinyal']:6d} {hit:7.0f} {ortr:6.2f} {is_o:8.4f} "
              f"{oos_o:9.4f} {sec:6d}" + (f"  ({s['hata']} decide hatasi)" if s["hata"] else ""))
    if res is None or res["pbo"] is None:
        print("=" * 64)
        print("PBO: HESAPLANAMADI — tum bolunmeler bilgisiz (sinyal yok/hep esit "
              "veya purge sonrasi egitim bos). Bu durum 'olculemedi' demektir; "
              "cache'e YAZILMAZ, dsr_report 'PBO=N/A' kalir.")
        return
    lams = sorted(res["lambdas"])
    med = lams[len(lams) // 2]
    print("-" * 64)
    print(f"LAMBDA: min={lams[0]:+.2f} med={med:+.2f} max={lams[-1]:+.2f} | "
          f"gecerli bolunme={res['n_split_gecerli']}/{res['n_split_toplam']} "
          f"(test-esit atlanan={res['n_tie']}, secimsiz/bos={res['n_secimsiz']})")
    print(f"IS->OOS (egitim-birincisi): egitim ortR/satir {res['sec_is_ort']:+.4f} "
          f"-> test {res['sec_oos_ort']:+.4f}"
          + ("  [IS>OOS: bozulma var]" if res["sec_is_ort"] > res["sec_oos_ort"] else ""))
    etik = []
    if n_sinyal < cfg.cpcv_min_sinyal:
        etik.append(f"islem az (en-aktif {n_sinyal} < {cfg.cpcv_min_sinyal})")
    if res["n_split_gecerli"] < cfg.cpcv_min_split:
        etik.append(f"gecerli bolunme az ({res['n_split_gecerli']} < {cfg.cpcv_min_split})")
    guvenilir = not etik
    # Bug 2: formal CSCV mi heuristik yaklasim mi — aday seti OOS oncesi muhurlenir (seal-before-test).
    _manifest = freeze_candidates([{"variant": i, "sel": res["sel_cnt"][i]}
                                   for i in range(res["N"])])
    _pbo_assess = PBOAssessment(
        pbo_value=res["pbo"], is_formal_pbo=guvenilir,
        manifest_sha256=_manifest.sha256, n_candidates=res["N"],
        n_paths=res["n_split_gecerli"],
        method="CSCV" if guvenilir else "HEURISTIC_APPROX",
        assessed_at_ms=int(time.time() * 1000),
        notes="; ".join(etik) if etik else "n yeterli")
    print("=" * 64)
    print(f"PBO ETIKET (Bug 2): {_pbo_assess.label} | method={_pbo_assess.method} | "
          f"manifest={_manifest.sha256[:12]} | aday={_pbo_assess.n_candidates} yol={_pbo_assess.n_paths}")
    print(f"PBO = {res['pbo']:.2f}   (P(lambda<0): egitim-birincisinin testte medyan-alti "
          f"kalma olasiligi; 0=saglam, ~0.5=gurultu, 1=tam asiri-uyum)")
    if guvenilir:
        print("ETIKET: OLCULDU (n yeterli). Yorum: PBO>0.5 -> varyant secimi gurultuye "
              "uyuyor; <0.2 -> secim OOS'ta da tutuyor.")
    else:
        print("ETIKET: KALIBRE DEGIL / GUVENILMEZ — " + "; ".join(etik)
              + ". Sayi gosterge niteliginde; 'fast'siz ve daha uzun seriyle tekrarla.")
    print("KAPSAM (durust): matris CEKIRDEK motoru olcer; canli-only katmanlar "
          "(orderflow/funding/book/spot) matriste YOK — canli secicilik olculmedi.")
    _cpcv_cache_save(sym, {"pbo": res["pbo"], "S": res["S"],
                           "n_split_gecerli": res["n_split_gecerli"],
                           "n_sinyal": n_sinyal, "guvenilir": guvenilir,
                           "mod": ("fast" if fast else "tam"), "ts": time.time(),
                           "n_variant": res["N"], "n_satir": len(mres["M"]),
                           "lambda_med": med, "model_hash": model_hash(cfg),
                           "feature_hash": feature_hash(),
                           "config_hash": config_hash(cfg),
                           "protocol_id": cfg.protocol_id,
                           "scope": "OAT-partial-diagnostic",
                           "compat_hash": cpcv_compat_hash(("fast" if fast else "tam"), Config()),
                           "code_hash": code_hash(),
                           "is_formal_pbo": _pbo_assess.is_formal_pbo,
                           "pbo_method": _pbo_assess.method,
                           "manifest_sha256": _manifest.sha256,
                           "invalid_rows": mres.get("invalid_rows", 0)})
    print(f"cache: {_cpcv_cache_path()} — dsr_report artik {sym} icin bu PBO'yu gosterir.")


# ════════════════════════════════════════════════════════════════════════════
# SELF-TEST (ag YOK)
# ════════════════════════════════════════════════════════════════════════════
def _synthetic_candles(n, seed, trend, vol, t0=1_700_000_000_000):
    rng = random.Random(seed)
    price = 100.0
    out = []
    base_open = (t0 // 900_000) * 900_000
    for i in range(n):
        r = trend + rng.gauss(0, vol)
        o = price
        price = max(0.01, price * (1 + r))
        hi = max(o, price) * (1 + abs(rng.gauss(0, vol / 2)))
        lo = min(o, price) * (1 - abs(rng.gauss(0, vol / 2)))
        out.append(Candle(open=o, high=hi, low=lo, close=price,
                          volume=abs(rng.gauss(1000, 300)),
                          close_ms=base_open + (i + 1) * 900_000 - 1))
    return out


def _vdip_candles(n, seed):
    """Sert dususun DIBINDE, TAZE kapitulasyon dibi (hammer): fiyat destekte, uzun alt fitil,
    kapanis ust yaride (reddedilis). dip-short REGRESYON testi -> SHORT ASLA."""
    rng = random.Random(seed)
    price = 100.0
    out = []
    t0 = 1_700_000_000_000
    for i in range(n):
        r = -0.004 + rng.gauss(0, 0.010)              # sureklı dusus (fiyat surekli dipte)
        o = price
        price = max(0.01, price * (1 + r))
        if i == n - 1:
            # TAZE kapitulasyon HAMMER: yeni dip fitili + kapanis fitilin ust yarisinda
            lo = min(o, price) * (1 - 0.03)
            price = lo * 1.02                          # kapanis dipten ~%2 yukari (reddedilis)
            hi = max(o, price) * (1 + 0.002)
        else:
            hi = max(o, price) * (1 + abs(rng.gauss(0, 0.005)))
            lo = min(o, price) * (1 - abs(rng.gauss(0, 0.005)))
        out.append(Candle(open=o, high=hi, low=lo, close=price,
                          volume=abs(rng.gauss(1200, 300)), close_ms=t0 + i * 900_000))
    return out


def _vtop_candles(n, seed):
    """Sert yukselisin TEPESINDE, TAZE euforya tepesi (shooting-star): fiyat direncte,
    uzun ust fitil, kapanis alt yaride. tepe-long REGRESYON testi -> LONG ASLA."""
    rng = random.Random(seed)
    price = 100.0
    out = []
    t0 = 1_700_000_000_000
    for i in range(n):
        r = +0.004 + rng.gauss(0, 0.010)              # surekli yukselis (fiyat surekli tepede)
        o = price
        price = max(0.01, price * (1 + r))
        if i == n - 1:
            hi = max(o, price) * (1 + 0.03)            # yeni tepe fitili
            price = hi * 0.98                          # kapanis tepeden ~%2 asagi (reddedilis)
            lo = min(o, price) * (1 - 0.002)
        else:
            hi = max(o, price) * (1 + abs(rng.gauss(0, 0.005)))
            lo = min(o, price) * (1 - abs(rng.gauss(0, 0.005)))
        out.append(Candle(open=o, high=hi, low=lo, close=price,
                          volume=abs(rng.gauss(1200, 300)), close_ms=t0 + i * 900_000))
    return out


def _synth_snapshot(name, cs, cfg, trend=0.0):
    rng = random.Random(1)
    trades = []
    t0 = cs[-1].close_ms or 0
    base = cs[-1].close
    for i in range(400):
        maker = rng.random() < (0.55 if trend < 0 else 0.45)
        trades.append((base * (1 + rng.gauss(0, 0.0005)), abs(rng.gauss(5, 3)), t0 + i * 100, maker))
    of = compute_orderflow(trades, cfg)
    for k, c in enumerate(cs):
        c.oi = 1_000_000 * (1 + 0.001 * k)
        c.taker = 1.0
    # sentetik SPOT: vadeliyle ayni yol, kucuk rastgele basis (mikro-katman testi icin)
    spot = [Candle(open=c.open * 0.9995, high=c.high * 0.9995, low=c.low * 0.9995,
                   close=c.close * (0.9995 + rng.gauss(0, 0.0002)), volume=c.volume,
                   close_ms=c.close_ms) for c in cs]
    return Snapshot(symbol=name, candles=cs, htf=cs[::16][-60:], orderflow=of,
                    book={"imbalance": 0.0, "spread": base * 0.0002, "spread_pct": 0.0002},
                    funding=0.0001, funding_hist=[0.0001] * 50, taker_ratio=1.0,
                    spot=spot, stale=False)


def _stopavi_candles(n, seed, yon="ASAGI"):
    """YATAY bantta STOP-AVI (likidite supurmesi), IKI YONLU (H4: ayna kopyasiz test yok):
    yon=ASAGI -> son mum bant dibinin altina ~1.5 ATR igne atar ve bant ICINE geri
    kapanir (reclaim) -> supurme mumunda SHORT YASAK (dibin fitiline short = av kurbani).
    yon=YUKARI -> bant tepesinin ustune igne + geri kapanis -> LONG YASAK (squeeze avi)."""
    rng = random.Random(seed)
    out = []
    t0 = 1_700_000_000_000
    base = 100.0
    p = base
    for i in range(n):
        merkez = base * (1 + 0.02 * math.sin(i / 9.0))       # yatay salinim (bant)
        r = (merkez - p) / p * 0.3 + rng.gauss(0, 0.006)     # ortalamaya donus + gurultu
        o = p
        p = max(0.01, p * (1 + r))
        hi = max(o, p) * (1 + abs(rng.gauss(0, 0.002)))
        lo = min(o, p) * (1 - abs(rng.gauss(0, 0.002)))
        out.append(Candle(open=o, high=hi, low=lo, close=p,
                          volume=abs(rng.gauss(1000, 250)), close_ms=t0 + i * 900_000))
    a = max(1e-9, atr_series(out, 14)[-1])
    son = out[-1]
    son.open = out[-2].close
    if yon == "ASAGI":
        ref_lo = min(c.low for c in out[-41:-1])             # onceki 40-bar dibi (avlanan seviye)
        son.low = ref_lo - 1.5 * a                           # dibin altina igne (stop-avi)
        son.close = ref_lo + 0.4 * a                         # bant icine geri kapanis (reclaim)
        son.high = max(son.open, son.close) * (1 + 0.0005)
    else:
        ref_hi = max(c.high for c in out[-41:-1])            # onceki 40-bar tepesi
        son.high = ref_hi + 1.5 * a                          # tepenin ustune igne (squeeze avi)
        son.close = ref_hi - 0.4 * a                         # bant icine geri kapanis
        son.low = min(son.open, son.close) * (1 - 0.0005)
    return out


def _squeeze_candles(n, seed, yon="YUKARI"):
    """SIKISMA -> PATLAMA, IKI YONLU: normal vol sonrasi son ~20 mum asiri dusuk vol,
    SON mum 40-bar ekstreminin otesine DEV govdeyle kopar (yon=YUKARI tepe ustune /
    yon=ASAGI dip altina = kapitulasyon). Dusman-regresyon: (a) sikisma patlamadan
    ONCE vol_regime'de gorunmeli (COMPRESSED/LOW), (b) patlama aninda ya rejim okur
    ya ofori/kapitulasyon korumasi devrede; uc KOVALANMAZ (yukari->LONG, asagi->SHORT yasak)."""
    rng = random.Random(seed)
    out = []
    t0 = 1_700_000_000_000
    p = 100.0
    for i in range(n):
        vol = 0.010 if i < n - 20 else 0.0015                # son 20 mum: sikisma
        r = rng.gauss(0, vol)
        o = p
        p = max(0.01, p * (1 + r))
        hi = max(o, p) * (1 + abs(rng.gauss(0, vol / 2)))
        lo = min(o, p) * (1 - abs(rng.gauss(0, vol / 2)))
        out.append(Candle(open=o, high=hi, low=lo, close=p,
                          volume=abs(rng.gauss(1000, 250)), close_ms=t0 + i * 900_000))
    a = max(1e-9, atr_series(out, 14)[-1])
    son = out[-1]
    son.open = out[-2].close
    if yon == "YUKARI":
        ref_hi = max(c.high for c in out[-41:-1])            # kirilan sikisma tepesi
        son.close = max(ref_hi, son.open) + 3.0 * a          # dev govdeyle yeni tepeye kopus
        son.high = son.close * (1 + 0.0005)
        son.low = min(son.open, son.close) * (1 - 0.0005)
    else:
        ref_lo = min(c.low for c in out[-41:-1])             # kirilan sikisma dibi
        son.close = min(ref_lo, son.open) - 3.0 * a          # dev govdeyle yeni dibe kopus
        son.low = son.close * (1 - 0.0005)
        son.high = max(son.open, son.close) * (1 + 0.0005)
    return out


def _gap_candles(n, seed, yon="ASAGI"):
    """BOSLUKLU (gap) seri, IKI YONLU: ortada ve SON mumda %5 bosluklu acilis
    (yon=ASAGI onceki kapanisin altinda / yon=YUKARI ustunde; bosluk kapanmaz).
    Dusman-regresyon: motor cokmemeli, seviye/olasilik degismezleri bozulmamali
    (gap TR/ATR ve z-gecmislerini sismanlatir)."""
    rng = random.Random(seed)
    out = []
    t0 = 1_700_000_000_000
    p = 100.0
    carpan = 0.95 if yon == "ASAGI" else 1.05
    for i in range(n):
        o = p * (carpan if i in (n // 2, n - 1) else 1.0)    # bosluklu acilis
        p = max(0.01, o * (1 + rng.gauss(0, 0.008)))
        hi = max(o, p) * (1 + abs(rng.gauss(0, 0.003)))
        lo = min(o, p) * (1 - abs(rng.gauss(0, 0.003)))
        out.append(Candle(open=o, high=hi, low=lo, close=p,
                          volume=abs(rng.gauss(1000, 250)), close_ms=t0 + i * 900_000))
    return out


def _karar_degismezleri(d, cfg) -> List[str]:
    """OZELLIK-TABANLI karar degismezleri: girdi NE OLURSA OLSUN ihlal edilemez.
    Doner: ihlal listesi (bos = saglikli). Dusman ureteclerin ortak kapisi."""
    ihlal = []
    if d.karar not in ("LONG", "SHORT", "BEKLE"):
        ihlal.append(f"karar tanimsiz: {d.karar}")
    if d.karar in ("LONG", "SHORT"):
        for ad, v in (("giris", d.entry), ("hedef", d.target), ("stop", d.stop)):
            if v is None or not math.isfinite(v) or v <= 0:
                ihlal.append(f"{ad} gecersiz: {v}")
        if all(v is not None and math.isfinite(v) for v in (d.entry, d.target, d.stop)):
            if d.karar == "LONG" and not (d.stop < d.entry < d.target):
                ihlal.append(f"LONG sira bozuk: stop={d.stop:.4g} giris={d.entry:.4g} hedef={d.target:.4g}")
            if d.karar == "SHORT" and not (d.target < d.entry < d.stop):
                ihlal.append(f"SHORT sira bozuk: hedef={d.target:.4g} giris={d.entry:.4g} stop={d.stop:.4g}")
        if not (0 <= d.prob <= max(cfg.prob_cap, cfg.calib_prob_ceiling)):
            ihlal.append(f"prob sinir disi: {d.prob}")
        if not (0.0 <= d.p_target <= 1.0):
            ihlal.append(f"p_target sinir disi: {d.p_target}")
    for ad, v in (("ev_long", d.ev_long), ("ev_short", d.ev_short)):
        if not math.isfinite(v):
            ihlal.append(f"{ad} sonlu degil")
    return ihlal


# Sahne seed'leri SABIT SAYI: hash(str) Python'da surec-basina rastgele TUZLANIR
# (PYTHONHASHSEED) -> ayni selftest her kosuda FARKLI seri uretiyordu (olculdu:
# UPTREND bir kosuda BEKLE, digerinde LONG). Deterministik regresyon sabit seed ister.
_SAHNE_SEED = {"UPTREND": 11, "DOWNTREND": 1, "CHOP": 303, "VOLATILE": 404}




def _step4_btc_repairtest(cfg: Config) -> bool:
    """Agsiz STEP4 BTC bas-at birim bekcisi.
    Kapsam: hard/soft veto, ETH major profil, decorrelation-risk, confidence cap ve
    veri-yetersizligi. Canli karlilik testi DEGIL; pusu/market kapisinin mekanik
    sozlesmesini korur."""
    ok = True
    print("\n" + "-" * 52)
    print("[STEP4 BTC BAS-AT] veto/confirm/ignore/risk mekanik repairtest:")
    l4_long_bad = {"dir": -1, "wick_against_long": 0.6, "wick_against_short": 0.0}
    st_hard = BtcLeaderState(mode="BTC_CONFIRM", side=-1, strength=0.95, quality=1.0,
                             corr=0.85, corr_z=1.8, beta=1.4, beta_z=1.6,
                             leadlag=0.5, leadlag_q=0.9, confirm_adj=-cfg.btc_confirm_cap,
                             reasons=["sentetik ters lider"])
    m1, why1 = btc_veto_mode_for_side(st_hard, "LONG", l4_long_bad, "SOLUSDT", cfg)
    t1 = m1 == "HARD"
    ok = ok and t1
    print(f"  ters BTC + son4 aleyhte -> {m1}: " + ("OK" if t1 else "!!! HARD olmadi") + f" ({why1[:55]})")

    m2, _ = btc_veto_mode_for_side(st_hard, "SHORT", {"dir": -1}, "SOLUSDT", cfg)
    t2 = m2 == "CONFIRM"
    ok = ok and t2
    print(f"  ayni yon BTC -> {m2}: " + ("OK (emir degil, skor teyidi)" if t2 else "!!! CONFIRM olmadi"))

    st_eth = BtcLeaderState(mode="BTC_CONFIRM", side=-1, strength=0.9, quality=0.90,
                            corr=0.8, beta=1.2, leadlag=0.3, leadlag_q=0.85,
                            reasons=["ETH major profil"])
    m3a, _ = btc_veto_mode_for_side(st_eth, "LONG", l4_long_bad, "SOLUSDT", cfg)
    m3b, _ = btc_veto_mode_for_side(st_eth, "LONG", l4_long_bad, "ETHUSDT", cfg)
    t3 = (m3a == "HARD") and (m3b != "HARD")
    ok = ok and t3
    print(f"  ETH major profil daha kosullu: SOL={m3a}, ETH={m3b}: " + ("OK" if t3 else "!!! profil ayrimi yok"))

    st_risk = BtcLeaderState(mode="DECORRELATION_RISK", side=0, quality=0.2,
                             decorrelation_risk=1.0, risk_penalty=cfg.btc_risk_penalty_cap,
                             reasons=["corr kopusu + vol/OI stresi"])
    m4, _ = btc_veto_mode_for_side(st_risk, "LONG", {"dir": 0}, "DOGEUSDT", cfg)
    t4 = m4 == "RISK"
    ok = ok and t4
    print(f"  dusuk corr + stres -> {m4}: " + ("OK" if t4 else "!!! risk etiketi yok"))

    st_low = BtcLeaderState(mode="BTC_IGNORE", side=-1, quality=0.0, strength=0.1, reasons=["zayif"])
    m5, _ = btc_veto_mode_for_side(st_low, "LONG", l4_long_bad, "DOGEUSDT", cfg)
    t5 = m5 == "NONE"
    ok = ok and t5
    print(f"  liderlik zayif -> {m5}: " + ("OK (BTC ignore)" if t5 else "!!! zayif lider vetoledi"))

    e = est_btc_leader_state(st_hard, cfg)
    t6 = (0.5 - cfg.btc_confirm_cap - 1e-9) <= e.p_up <= (0.5 + cfg.btc_confirm_cap + 1e-9) and e.p_up < 0.5
    ok = ok and t6
    print(f"  BTC katkisi cap icinde ve SHORT yonlu p_up={e.p_up:.2f} cap=±{cfg.btc_confirm_cap:.2f}: " + ("OK" if t6 else "!!! cap/yon hatali"))

    snap_a = Snapshot(symbol="ALTUSDT", candles=_synthetic_candles(20, 1, 0.0, 0.01))
    snap_b = Snapshot(symbol="BTCUSDT", candles=_synthetic_candles(20, 2, 0.0, 0.01))
    st_ins = build_btc_leader_state(snap_a, snap_b, cfg)
    t7 = st_ins is not None and st_ins.mode == "BTC_DATA_INSUFFICIENT"
    ok = ok and t7
    print(f"  veri yetersiz -> {st_ins.mode if st_ins else None}: " + ("OK" if t7 else "!!! cold-start hatali"))

    # STEP4B: pusu karnesi kotu tip yeni pusu kurdurmaz (gecmis yon uretmez; risk kapisi).
    import tempfile as _tmp_pusu
    _old_plan_env = os.environ.get("YON_PLAN_LOG")
    _tmp_plan = _tmp_pusu.mktemp(suffix="_step4b_pusu_gate.json")
    try:
        os.environ["YON_PLAN_LOG"] = _tmp_plan
        with open(_tmp_plan, "w", encoding="utf-8") as _f:
            json.dump({"PKT": {"pusu": [], "aktif": [], "hist": [
                {"tip": "SHORT-TEPKI", "sonuc": "STOP", "olcum": 1, "ts": i} for i in range(9)
            ]}}, _f)
        _cfgp = Config()
        _blk, _why = pusu_karne_riskli("PKT", "SHORT-TEPKI", _cfgp)
        t8 = _blk and "Wilson" in _why
    finally:
        if _old_plan_env is None:
            os.environ.pop("YON_PLAN_LOG", None)
        else:
            os.environ["YON_PLAN_LOG"] = _old_plan_env
        try:
            os.remove(_tmp_plan)
        except Exception:
            pass
    ok = ok and t8
    print(f"  pusu karnesi zayif -> yeni pusu risk kapisi: " + ("OK" if t8 else "!!! pusu gate hatali"))

    # STEP4C: asimetrik RR market sinyalini BEKLE'ye cevirir; yon uretmez.
    sc_low = Scenario("SHORT", 100.0, 99.0, 104.0, 0.80, 0.10, 0.2, 0.24)
    blk_rr, why_rr = market_risk_kapisi("RRT", sc_low, cfg)
    t9 = blk_rr and "RR asimetrik" in why_rr
    ok = ok and t9
    print("  RR asimetrik -> market risk kapisi: " + ("OK" if t9 else "!!! RR gate hatali"))

    # STEP4D: eski/acik sinyal bugunku RR ve aleyhte-ATR denetimiyle RAPORDA isaretlenir.
    _r_old = {"side": "SHORT", "entry": 100.0, "target": 99.0, "inval": 104.0, "outcome": "OPEN"}
    _aud = open_signal_risk_audit(_r_old, 101.2, 1.0, cfg)
    t10 = "STEP4D ACIK-SINYAL RISK" in _aud and "RR" in _aud and "aleyhte" in _aud
    ok = ok and t10
    print("  acik/eski sinyal risk denetimi: " + ("OK" if t10 else "!!! open-audit hatali"))

    # STEP4E: DOGE saha bulgusu (MC hedef %45 / stop %33 / edge %12) markete gecmemeli.
    sc_weak = Scenario("SHORT", 0.07184, 0.07110, 0.07238425, 0.452, 0.33, 0.20, 1.05)
    blk_q, why_q = market_quality_kapisi("DOGEUSDT", sc_weak, cfg)
    t11 = blk_q and "Market kalite kapisi" in why_q and "MC hedef" in why_q
    ok = ok and t11
    print("  dusuk hedef/yuksek stop MC -> market kalite kapisi: " + ("OK" if t11 else "!!! kalite gate hatali"))

    _r_doge = {"side": "SHORT", "entry": 0.07184, "target": 0.07110, "inval": 0.07238425,
               "outcome": "OPEN", "p_target": 0.452, "p_stop": 0.33}
    _aud2 = open_signal_risk_audit(_r_doge, 0.07184, 0.000355, cfg)
    t12 = "market kalite" in _aud2
    ok = ok and t12
    print("  acik zayif-MC sinyal audit etiketi: " + ("OK" if t12 else "!!! kalite audit yok"))

    # STEP4G: Eski OPEN sinyal hedefe/stopa bu kosuda ulasmissa yasam-dongusu kapisi
    # onu acik sayip yeni karari bayat nedenle bloklamamali.
    import tempfile as _tmp_sig_g
    _old_sig_env = os.environ.get("YON_PANEL_LOG")
    _tmp_sig = _tmp_sig_g.mktemp(suffix="_step4g_open_resolved.jsonl")
    try:
        os.environ["YON_PANEL_LOG"] = _tmp_sig
        _SIG_CACHE.update(yol=None, imza=None, rows=None)
        with open(_tmp_sig, "w", encoding="utf-8") as _f:
            _f.write(json.dumps({"symbol": "OPN", "bar_ms": 1, "side": "SHORT",
                                 "entry": 100.0, "target": 99.0, "inval": 104.0,
                                 "outcome": "OPEN"}) + "\n")
        _blk_hit, _why_hit = acik_market_sinyali_var("OPN", cfg, 98.9)
        _blk_open, _why_open = acik_market_sinyali_var("OPN", cfg, 100.5)
        t13 = (not _blk_hit) and _blk_open and "acik market" in _why_open
    finally:
        if _old_sig_env is None:
            os.environ.pop("YON_PANEL_LOG", None)
        else:
            os.environ["YON_PANEL_LOG"] = _old_sig_env
        _SIG_CACHE.update(yol=None, imza=None, rows=None)
        try:
            os.remove(_tmp_sig)
        except Exception:
            pass
    ok = ok and t13
    print("  cozulmus OPEN sinyal stale-blokaj yapmaz: " + ("OK" if t13 else "!!! STEP4G open gate hatali"))
    # STEP4H: Acik sinyal raporundaki "simdi/lehte-aleyhte" kapali mumla degil,
    # live mark varsa onunla hesaplanmali. Saha bulgusu: DOGE kapali fiyat lehte,
    # live mark aleyhteyken rapor yanlis "lehte" diyordu.
    import tempfile as _tmp_sig_h
    _old_sig_env_h = os.environ.get("YON_PANEL_LOG")
    _tmp_sig_h_path = _tmp_sig_h.mktemp(suffix="_step4h_live_status.jsonl")
    try:
        os.environ["YON_PANEL_LOG"] = _tmp_sig_h_path
        _SIG_CACHE.update(yol=None, imza=None, rows=None)
        with open(_tmp_sig_h_path, "w", encoding="utf-8") as _f:
            _f.write(json.dumps({"symbol": "LIV", "bar_ms": 1, "side": "SHORT",
                                 "entry": 100.0, "target": 99.0, "inval": 104.0,
                                 "outcome": "OPEN", "p_target": 0.45, "p_stop": 0.33}) + "\n")
        _cs_live = [Candle(100.0, 100.2, 99.8, 99.8, close_ms=1),
                    Candle(99.8, 100.1, 99.5, 99.6, close_ms=900001)]
        _snap_live = Snapshot("LIV", _cs_live, live_price=101.0)
        _st_live = Structure(99.6, 1.0, 99.0, 101.0, [], [], True)
        _d_live = Decision("BEKLE", 0, None, None, None, 0.0, 0.0, 0, False, "test", [], 0, [], 0.0, "NORMAL", 0.0, "", 0.0, 0.0, {})
        _lines_live = takip_raporu("LIV", _snap_live, _d_live, _st_live, cfg)
        _txt_live = "\n".join(_lines_live)
        t14 = ("simdi 101.0" in _txt_live or "simdi 101" in _txt_live) and "-1.0 ATR" in _txt_live
    finally:
        if _old_sig_env_h is None:
            os.environ.pop("YON_PANEL_LOG", None)
        else:
            os.environ["YON_PANEL_LOG"] = _old_sig_env_h
        _SIG_CACHE.update(yol=None, imza=None, rows=None)
        try:
            os.remove(_tmp_sig_h_path)
        except Exception:
            pass
    ok = ok and t14
    print("  acik sinyal takip live-mark durum fiyati: " + ("OK" if t14 else "!!! STEP4H live status hatali"))
    return ok


# ════════════════════════════════════════════════════════════════════════════
# F11 (YÖNTEM.txt §6/§14) — KIRMIZI TEST KAPILARI (offline; decide()'a DOKUNMAZ)
# KT-1 random-entry null, KT-2 p-yeterlilik, KT-4 shift+shuffle sizinti. Karar
# motorunu DEGISTIRMEZ; ayri offline yol + GEC/KAL telemetrisi. YÖNTEM ilkesi:
# "reddedememe basari degildir; yalniz reddetme basaridir" -> sentetik/kenarsiz seride
# beklenen sonuc KAL'dir ve bu kapinin lastik-damga OLMADIGINI kanitlar.
# ════════════════════════════════════════════════════════════════════════════
def _red_collect_trades(candles, cfg, max_rows=None):
    """Offline decide() ile karar barlarindan gercek islemleri topla (no-lookahead;
    _cpcv_matrix ile AYNI cagri sozlesmesi). Doner list of dict."""
    H, stride, hist_cap = cfg.horizon, cfg.cpcv_stride, cfg.cpcv_hist_cap
    warm = cfg.min_train // 2 + H + 5
    N = len(candles)
    last = N - 1 - H
    if last < warm:
        return []
    atrs = atr_series(candles, cfg.atr_period)
    htf_full = _bt_resample_4h(candles)
    ts = list(range(warm, last + 1, stride))
    if max_rows:
        ts = ts[-max_rows:]
    out = []
    for t in ts:
        lo = max(0, t + 1 - hist_cap)
        sub = candles[lo:t + 1]
        htf = _bt_htf_upto(htf_full, candles[t].close_ms)
        try:
            d = decide(Snapshot(symbol="RED", candles=sub, htf=htf, stale=False,
                                last_closed_ms=candles[t].close_ms,
                                data_watermark_ms=candles[t].close_ms), cfg,
                       context=DecisionContext.offline(candles[t].close_ms))
        except Exception:
            continue
        if d.karar not in ("LONG", "SHORT") or d.entry is None:
            continue
        r = _cpcv_r_multiple(candles, t, d, H)
        if r is None:
            continue
        risk = abs(d.entry - d.stop)
        reward = abs(d.target - d.entry)
        a = atrs[t] if atrs[t] > 0 else risk
        out.append({"t": t, "side": d.karar, "b": (reward / risk) if risk > 0 else 0.0,
                    "risk_atr": (risk / a) if a > 0 else 1.0,
                    "cost_r": (max(0.0, getattr(d, "cost_abs", 0.0) or 0.0) / risk) if risk > 0 else 0.0,
                    "net_r": r, "p": d.p_target})
    return out


def _red_bracket_r(candles, t, side, entry, b, risk, cost_r, H):
    """Verili bar/yon/bracket icin maliyet-sonrasi R (_cpcv_r_multiple ile ayni semantik)."""
    if risk <= 0 or b <= 0:
        return None
    reward = b * risk
    target = (entry + reward) if side == "LONG" else (entry - reward)
    stop = (entry - risk) if side == "LONG" else (entry + risk)
    _win, how = _bt_resolve(candles, t, entry, target, stop, side, H)
    rr_net, loss_net = b - cost_r, -(1.0 + cost_r)
    if how == "hedef":
        return rr_net
    if how in ("stop", "ayni-bar"):
        return loss_net
    end = min(t + H, len(candles) - 1)
    fin = candles[end].close
    r = (((fin - entry) if side == "LONG" else (entry - fin)) / risk) - cost_r
    return _clip(r, loss_net, rr_net)


def _red_random_entry_null(candles, trades, cfg, rng):
    """KT-1: ayni islem sayisi/bracket/maliyet, RASTGELE bar+yon. Null E_net dagilimi.
    risk ATR-oraniyla tasinir -> rastgele barda o barin ATR'siyle yeniden olceklenir."""
    H = cfg.horizon
    warm = cfg.min_train // 2 + H + 5
    atrs = atr_series(candles, cfg.atr_period)
    valid = [t for t in range(warm, len(candles) - H) if atrs[t] > 0]
    if not valid or not trades:
        return []
    means = []
    for _ in range(cfg.kirmizi_n_perm):
        rs = []
        for tr in trades:
            t = valid[rng.randrange(len(valid))]
            side = "LONG" if rng.random() < 0.5 else "SHORT"
            r = _red_bracket_r(candles, t, side, candles[t].close, tr["b"],
                               tr["risk_atr"] * atrs[t], tr["cost_r"], H)
            if r is not None:
                rs.append(r)
        if rs:
            means.append(mean(rs))
    return means


def kirmizi_test(target="sentetik", fast=False):
    """YÖNTEM §14 KT-1/KT-2/KT-4 offline kapilari. decide()'a DOKUNMAZ (ayri yol).
    Ciktisi GEC/KAL telemetrisidir; kar vaadi degildir."""
    cfg = Config(mc_paths=(300 if fast else 800), kline_limit=1000)
    if fast:
        cfg = replace(cfg, kirmizi_n_perm=200)
    print("=" * 60)
    print("KIRMIZI TEST (YÖNTEM §14) — H0: sistemin net edge'i YOK")
    print("=" * 60)
    if str(target).lower() in ("sentetik", "synthetic", ""):
        # DETERMINISTIK offline seri: hafif trend + gurultu (kenar GARANTI DEGIL).
        cs = _synthetic_candles(cfg.kirmizi_sent_n, cfg.kirmizi_sent_seed,
                                trend=0.0006, vol=0.010)
        print(f"kaynak: sentetik (n={len(cs)}, seed={cfg.kirmizi_sent_seed}; kenar garanti DEGIL)")
    else:
        sym = target.upper()
        print(f"kaynak: CANLI {sym} (Binance; ag gerekir)")
        cs = fetch_klines(sym, "15m", cfg.kline_limit)
        if not cs or len(cs) < 300:
            print("VERI YETERSIZ -> kirmizi test kosulamadi (ag/veri).")
            return False
    trades = _red_collect_trades(cs, cfg, max_rows=(120 if fast else None))
    n = len(trades)
    print(f"toplanan gercek islem (offline decide, no-lookahead): n={n}")
    if n < 12:
        print(f"UNDERPOWERED (n={n} < 12): guc yetersiz -> edge DOGRULANAMAZ "
              "(YÖNTEM §13-6 MinTRL: underpowered isaretlenir). SONUC: KAL (kanit yok).")
        return False
    reals = [tr["net_r"] for tr in trades]
    real_E = mean(reals)
    rng = random.Random(cfg.kirmizi_sent_seed ^ 0x5eed)
    # ── KT-1 random-entry null ──
    null_means = _red_random_entry_null(cs, trades, cfg, rng)
    if null_means:
        null_sorted = sorted(null_means)
        pctl = null_sorted[min(len(null_sorted) - 1, int(cfg.kirmizi_pctl * len(null_sorted)))]
        kt1 = real_E > pctl
        print(f"KT-1 random-entry: gercek E_net={real_E:+.3f}R vs null %{int(cfg.kirmizi_pctl*100)} "
              f"persantil={pctl:+.3f}R (n_perm={len(null_means)}) -> {'GEC' if kt1 else 'KAL (H0 reddedilemedi)'}")
    else:
        kt1 = False
        print("KT-1: null uretilrmedi -> KAL")
    # ── KT-2 p-yeterlilik: E_net p'ye mi (p,b)'ye mi bagli; p<0.5 karli konfig var mi ──
    lo_p = [tr["net_r"] for tr in trades if tr["p"] < 0.5]
    corr_p = _corr([tr["p"] for tr in trades], reals)
    corr_b = _corr([tr["b"] for tr in trades], reals)
    lo_E = mean(lo_p) if lo_p else None
    # KT-2 GECME (YÖNTEM §14): p<0.5 iken net-pozitif konfig VAR -> 'yon-makinesi degil'.
    # p<0.5 hic islem yoksa bu KANITLANAMAZ (motor temkinli) -> NA; GEC verilemez ama
    # bu bir 'sizinti/red' de degildir (durust ayrim).
    if lo_E is None:
        kt2_edge_beyond_p = False
        kt2_txt = "p<0.5 islem YOK -> KT-2 kaniti YETERSIZ (yon-makinesi olmadigi kanitlanamadi)"
    else:
        kt2_edge_beyond_p = lo_E > 0
        kt2_txt = (f"p<0.5 alt-kume E_net={lo_E:+.3f} (n={len(lo_p)}) -> "
                   + ("p-yeterli DEGIL (RR de kenar tasiyor; GEC adayi)" if kt2_edge_beyond_p
                      else "p-baskin (RR tek basina kurtarmiyor)"))
    print(f"KT-2 p-yeterlilik: corr(net_r,p)={('%.2f'%corr_p) if corr_p is not None else 'NA'} "
          f"corr(net_r,b)={('%.2f'%corr_b) if corr_b is not None else 'NA'} | {kt2_txt}")
    # ── KT-4 sizinti: (a) 1-bar shift, (b) yon-shuffle placebo ──
    atrs = atr_series(cs, cfg.atr_period)
    shift_rs = []
    for tr in trades:
        risk = tr["risk_atr"] * (atrs[tr["t"]] if atrs[tr["t"]] > 0 else 1.0)
        r = _red_bracket_r(cs, tr["t"] + 1, tr["side"], cs[tr["t"] + 1].close if tr["t"] + 1 < len(cs) else cs[tr["t"]].close,
                           tr["b"], risk, tr["cost_r"], cfg.horizon)
        if r is not None:
            shift_rs.append(r)
    shift_E = mean(shift_rs) if shift_rs else None
    shuf_rs = []
    for tr in trades:
        risk = tr["risk_atr"] * (atrs[tr["t"]] if atrs[tr["t"]] > 0 else 1.0)
        side = "LONG" if rng.random() < 0.5 else "SHORT"
        r = _red_bracket_r(cs, tr["t"], side, cs[tr["t"]].close, tr["b"], risk, tr["cost_r"], cfg.horizon)
        if r is not None:
            shuf_rs.append(r)
    shuf_E = mean(shuf_rs) if shuf_rs else None
    # Sizinti bayragi: yon-shuffle placebo hala gercekle ~ayni E_net -> yon kenar TASIMIYOR
    kt4_leak = (shuf_E is not None and real_E > 0 and shuf_E >= real_E - 1e-9)
    print(f"KT-4 sizinti: 1-bar-shift E_net={('%+.3f'%shift_E) if shift_E is not None else 'NA'} | "
          f"yon-shuffle placebo E_net={('%+.3f'%shuf_E) if shuf_E is not None else 'NA'} "
          f"(gercek {real_E:+.3f}) -> {'SIZINTI/yon kenarsiz SUPHESI' if kt4_leak else 'placebo gercekten dusuk (temiz)'}")
    gecti = bool(kt1 and kt2_edge_beyond_p and not kt4_leak)
    print("-" * 60)
    print("SONUC: " + ("GEC (KT-1&KT-2&KT-4 gecti; yine de DSR/PBO + canli dogrulama SART)"
                       if gecti else
                       "KAL — H0 reddedilemedi (edge KANITLANMADI). YÖNTEM: reddedememe basari DEGILDIR."))
    print("Not: bu offline kapi kar vaadi degildir; DSR=N/A + canli maliyet + kalibrasyon SART.")
    return gecti


def yontem_tests():
    """F11 (YÖNTEM.txt tamiri) kanit harness'i: her eklentiyi FALSIFIYE eder + KARAR-
    DEGISMEZLIGINI (decide ciktisi yontem bayraklarindan bagimsiz) kanitlar. Ag YOK."""
    res = []

    def chk(ad, ok):
        res.append((ad, bool(ok)))
        print(f"  {ad}: {'PASS' if ok else 'FAIL'}")

    print("=" * 52)
    print("[YONTEM] F11 BEKLENTI KATMANI KANIT HARNESS'I (ag yok)")
    print("=" * 52)
    # 1) YÖNTEM §1.2 capalari — expectancy_kelly (ikili: p_stop=1-p, c=0)
    a = expectancy_kelly(0.40, 0.60, 3.0, 1.0, 0.0)
    b = expectancy_kelly(0.58, 0.42, 0.5, 1.0, 0.0)
    chk("y1_capa_A_0.40x3.0_=+0.60R_gecilir", abs(a["E_R"] - 0.60) < 1e-9 and a["gecilir"] is True)
    chk("y2_capa_B_0.58x0.5_=-0.13R_girme", abs(b["E_R"] + 0.13) < 1e-9 and b["gecilir"] is False)
    chk("y3_kelly_isaret_=_beklenti", (a["f_star"] > 0) == (a["E_net"] > 0)
        and (b["f_star"] > 0) == (b["E_net"] > 0))
    # 2) maliyetli basabas p*_c=(1+c)/(1+b)
    c = expectancy_kelly(0.40, 0.60, 3.0, 1.0, 0.10)
    chk("y4_p_star_c_=(1+c)/(1+b)", abs(c["p_star_c"] - (1.10 / 4.0)) < 1e-9)
    # 3) Wilson iki-tarafli (7/10 -> 0.5 kapsanir; genislik>0)
    lo, hi = _wilson_ci(7, 10)
    chk("y5_wilson_iki_tarafli", 0.0 < lo < 0.7 < hi < 1.0)
    chk("y6_wilson_bos_guvenli", _wilson_ci(0, 0) == (0.0, 1.0))
    # 4) realize E_net + tanimlayici Sharpe + net-win
    re = realized_expectancy([2.0, -1.0, 2.0, -1.0])
    chk("y7_realize_E_net", abs(re["E_net"] - 0.5) < 1e-9 and re["n"] == 4 and re["win"] == 2)
    chk("y8_realize_sharpe", re["sharpe"] is not None and re["sharpe"] > 0)
    chk("y9_realize_bos", realized_expectancy([]) is None)
    # 5) ECE (guven 0.9, isabet 0.5 -> ECE 0.4)
    e = ece_reliability([(0.9, 1), (0.9, 0), (0.9, 1), (0.9, 0)], bins=10)
    chk("y10_ece_kalibresiz_0.4", abs(e["ece"] - 0.4) < 1e-9)
    e2 = ece_reliability([(0.5, 1), (0.5, 0)], bins=10)
    chk("y11_ece_mukemmel_0", e2 is not None and abs(e2["ece"]) < 1e-9)
    # 6) ORTOGONALLIK: tam-korele iki blok bayraklanir (izole store)
    import tempfile as _tf
    _bd = _tf.mkdtemp()
    _old_bs = os.environ.get("YON_BLOCK_SERIES_LOG")
    os.environ["YON_BLOCK_SERIES_LOG"] = os.path.join(_bd, "bs.json")
    try:
        _store = {"TST": []}
        for i in range(30):
            v = round(0.5 + 0.1 * math.sin(i), 4)
            _store["TST"].append([1000 + i, {"flow": v, "mc": v,
                                             "macro": round(0.5 + 0.1 * math.cos(i), 4)}])
        with open(os.environ["YON_BLOCK_SERIES_LOG"], "w") as _f:
            json.dump(_store, _f)
        o = block_orthogonality("TST", Config())
        chk("y12_ortho_korele_blok_bayrak", o["pairs"] == 3
            and any(set(h[:2]) == {"flow", "mc"} for h in o["hi"]))
    finally:
        if _old_bs is None:
            os.environ.pop("YON_BLOCK_SERIES_LOG", None)
        else:
            os.environ["YON_BLOCK_SERIES_LOG"] = _old_bs
    # 7) KIRMIZI TEST null-makinesi + verdikt-mantigi discriminate ediyor (lastik-damga
    # DEGIL). Motor sentetik gurultude skill=0 -> cogu BEKLE oldugundan null makinesi ELLE
    # kurulan islemlerle sinanir (RR=2, risk 1 ATR). _red_random_entry_null gercek MC/
    # decide gerektirmez -> deterministik null dagilimi uretir.
    cfgk = replace(Config(kline_limit=1000), kirmizi_n_perm=200)
    cs_k = _synthetic_candles(700, 4242, trend=0.0004, vol=0.010)
    man_trades = [{"t": 0, "side": "LONG", "b": 2.0, "risk_atr": 1.0, "cost_r": 0.02,
                   "net_r": 2.0, "p": 0.6} for _ in range(30)]
    null_means = _red_random_entry_null(cs_k, man_trades, cfgk, random.Random(99))
    chk("y13_KT1_null_uretildi", len(null_means) >= 50)
    if len(null_means) >= 50:
        ns = sorted(null_means)
        p95 = ns[min(len(ns) - 1, int(0.95 * len(ns)))]
        # DISCRIMINATE (tautoloji DEGIL): null dagilimi GERCEKTEN yayilmis (dejenere degil)
        # ve KT-1 verdikt predikati (real_E > p95) GERCEK null-uc degerlerinde dogru yon
        # veriyor: ust-uc (max) GEC, alt-uc (min) KAL. Dagilim degeriyle sinanir, literalle degil.
        _verdikt = lambda real_E: real_E > p95
        chk("y14_KT1_discriminate_gercek_null",
            max(null_means) > min(null_means)          # null non-dejenere (kapi ayirt edebilir)
            and _verdikt(max(null_means))              # ust-uc -> GEC
            and not _verdikt(min(null_means)))         # alt-uc -> KAL
    # 8) KARAR-DEGISMEZLIGI: decide ciktisi yontem bayraklarindan BAGIMSIZ (SALT telemetri)
    cfg_on = Config(mc_paths=300, kline_limit=400)
    cfg_off = replace(cfg_on, yontem_expectancy_enabled=False, yontem_regime_enet_enabled=False,
                      yontem_ece_enabled=False, yontem_ortho_enabled=False)
    inv_ok = True
    for _seed, _tr in ((2, 0.004), (1, -0.004), (7, 0.0)):
        _cs = _synthetic_candles(360, _seed, trend=_tr, vol=0.010)
        _snap = _synth_snapshot("INV", _cs, cfg_on)
        d_on = decide(_snap, cfg_on, context=DecisionContext.offline(_cs[-1].close_ms))
        d_off = decide(_snap, cfg_off, context=DecisionContext.offline(_cs[-1].close_ms))
        if (d_on.karar != d_off.karar or d_on.entry != d_off.entry
                or d_on.target != d_off.target or d_on.stop != d_off.stop
                or d_on.prob != d_off.prob):
            inv_ok = False
    chk("y15_KARAR_DEGISMEZLIGI_yontem_bayraklari_inert", inv_ok)

    ok = all(v for _, v in res)
    print("-" * 52)
    print(f"[YONTEM] {sum(v for _, v in res)}/{len(res)} PASSED"
          + ("" if ok else "  <-- FAIL VAR"))
    return ok


# ═══ Bug 10: selftest cikis kodlari (CI/mutasyon harness'i icin acik sozlesme) ═══
EXIT_PASS = 0
EXIT_INVARIANT_FAIL = 1
EXIT_INCONCLUSIVE = 2


def selftest():
    print("SELF-TEST (sentetik veri, ag yok)\n" + "=" * 52)
    # Uretim kline_limit=1000 etkin-OOS icindir; sentetik regresyonlarin yapisal
    # kapsami 500 mumla aynidir ve test suresini yaklasik yariya indirir.
    cfg = Config(mc_paths=800, kline_limit=500)
    ok_all = True
    # Sahne render'lari plan_kur cagirir -> kullanicinin GERCEK yon_plans.json'i
    # kirlenmesin: tum selftest boyunca plan deposu gecici dosyaya yonlendirilir.
    import tempfile as _tmpG
    _eski_plan_env = os.environ.get("YON_PLAN_LOG")
    os.environ["YON_PLAN_LOG"] = _tmpG.mktemp(suffix="_st_plan.json")
    sahne_karar: Dict[str, str] = {}     # KILIT-YOK / YON-TUTARLILIK regresyonu icin
    for name, trend, vol in [("UPTREND", 0.004, 0.012), ("DOWNTREND", -0.004, 0.012),
                             ("CHOP", 0.0, 0.010), ("VOLATILE", 0.001, 0.03)]:
        cs = _synthetic_candles(cfg.kline_limit, _SAHNE_SEED[name], trend, vol)
        snap = _synth_snapshot(name, cs, cfg, trend)
        d = decide(snap, cfg, context=DecisionContext.offline(cs[-1].close_ms))
        sahne_karar[name] = d.karar
        scen = classify_scenario(snap, build_structure(cs, cfg), cfg)
        print(f"\n[{name}] trend={trend:+.3f} vol={vol}")
        print(f"  bloklar: {' '.join(f'{k}={v*100:.0f}%' for k,v in d.block_p.items())} std={d.disagree:.2f}")
        print(f"  SENARYO #{scen.cell} {scen.regime} x {scen.event} | {scen.signal} | haberci={scen.herald_n}")
        if d.karar in ("LONG", "SHORT"):
            print(f"  KARAR={d.karar} %{d.prob} EV(L={d.ev_long*100:.0f} S={d.ev_short*100:.0f})·ATR "
                  f"MC-hedef=%{d.p_target*100:.0f} ters=%{d.reversal_risk} | {d.sebep[:60]}")
        else:
            print(f"  KARAR=BEKLE | {d.sebep[:70]}")
    # DIP-SHORT REGRESYON TESTI (makro-senaryo + MIKRO-katman birlikte)
    print("\n" + "-" * 52)
    print("[V-DIP REGRESYON] taze fitil-dipte SHORT URETILMEMELI (yon2+senaryo+mikro):")
    for seed in (7, 21, 99, 123, 555):
        cs = _vdip_candles(Config().kline_limit, seed)
        snap = _synth_snapshot("VDIP", cs, cfg, trend=-0.004)
        d = decide(snap, cfg, context=DecisionContext.offline(cs[-1].close_ms))
        stv = build_structure(cs, cfg)
        scen = classify_scenario(snap, stv, cfg)
        mics = classify_micro(snap, stv, cfg)
        mic_bad = any(m.side == "SHORT" for m in mics)
        bad = (d.karar == "SHORT") or (scen.side_hint == "SHORT") or mic_bad
        ok_all = ok_all and not bad
        print(f"  seed={seed:4d} -> KARAR={d.karar:5s} senaryo=#{scen.cell}/{scen.side_hint:7s} "
              f"mikro-short={'VAR!' if mic_bad else 'yok'} "
              f"EV(L={d.ev_long*100:+.0f} S={d.ev_short*100:+.0f})  {'!!! SHORT (HATA)' if bad else 'OK'}")
    # TEPE-LONG REGRESYON TESTI (veto simetrisinin kaniti — saha: 24/24 LONG biasi)
    print("\n" + "-" * 52)
    print("[V-TEPE REGRESYON] taze fitil-tepede LONG URETILMEMELI:")
    for seed in (7, 21, 99, 123, 555):
        cs = _vtop_candles(Config().kline_limit, seed)
        snap = _synth_snapshot("VTOP", cs, cfg, trend=+0.004)
        d = decide(snap, cfg, context=DecisionContext.offline(cs[-1].close_ms))
        stv = build_structure(cs, cfg)
        scen = classify_scenario(snap, stv, cfg)
        mics = classify_micro(snap, stv, cfg)
        mic_bad = any(m.side == "LONG" for m in mics)
        bad = (d.karar == "LONG") or (scen.side_hint == "LONG") or mic_bad
        ok_all = ok_all and not bad
        print(f"  seed={seed:4d} -> KARAR={d.karar:5s} senaryo=#{scen.cell}/{scen.side_hint:7s} "
              f"mikro-long={'VAR!' if mic_bad else 'yok'} "
              f"EV(L={d.ev_long*100:+.0f} S={d.ev_short*100:+.0f})  {'!!! LONG (HATA)' if bad else 'OK'}")
    # TAZE DONUS TESTI: ralli sonrasi sert donusun ILK mumlarinda uyari cikmali
    print("\n" + "-" * 52)
    print("[TAZE DONUS] ralli->sert dusus kirilmasinin ilk 3 mumunda uyari:")
    rngT = random.Random(77)
    csT = []
    p = 100.0
    t0 = 1_700_000_000_000
    for i in range(400):
        r = (+0.004 if i < 397 else -0.02) + rngT.gauss(0, 0.006)
        o = p; p = max(0.01, p * (1 + r))
        hi = max(o, p) * 1.003; lo = min(o, p) * 0.997
        csT.append(Candle(open=o, high=hi, low=lo, close=p, volume=1000.0,
                          close_ms=t0 + i * 900_000))
    snapT = _synth_snapshot("TDON", csT, cfg, trend=-0.02)
    tdf, tdm = taze_donus(csT, snapT.htf, cfg)
    ok_all = ok_all and tdf
    print(f"  taze_donus -> {tdf} ({tdm})  {'OK' if tdf else '!!! UYARI CIKMADI'}")
    dT = decide(snapT, cfg, context=DecisionContext.offline(csT[-1].close_ms))
    # HUKUM MODU (varsayilan): kosullu bloklar YOK, hukum satirlari VAR
    rT0 = render("TDON", snapT, dT, cfg)
    _hm_ok = ("HUKUM" in rT0 and "ISLEM:" in rT0
              and "TETIK HARITASI" not in rT0 and "MIKRO-SENARYO" not in rT0
              and "NET OKUMA" not in rT0)
    ok_all = ok_all and _hm_ok
    print(f"  HUKUM modu (varsayilan): hukum VAR + kosullu bloklar YOK: {'OK' if _hm_ok else '!!! KALDI'}")
    # DETAY MODU: eski tam cikti (kosullu haritalar) korunur
    os.environ["YON_DETAY"] = "1"
    try:
        rT = render("TDON", snapT, dT, cfg)
    finally:
        os.environ.pop("YON_DETAY", None)
    ok_all = ok_all and ("TAZE DONUS" in rT) and ("REJIM AILESI" in rT) and ("NET OKUMA" in rT) \
        and ("TETIK HARITASI" in rT) and ("TURKCESI: " in rT)
    print(f"  render(DETAY)'da TAZE DONUS satiri: {'VAR' if 'TAZE DONUS' in rT else '!!! YOK'} | "
          f"REJIM AILESI: {'VAR' if 'REJIM AILESI' in rT else '!!! YOK'} | "
          f"NET OKUMA+TETIK HARITASI: {'VAR' if ('NET OKUMA' in rT and 'TETIK HARITASI' in rT) else '!!! YOK'}")

    # MIKRO-SENARYO KATALOG TARAMASI (29 kalip; coker mi + ne buluyor)
    print("\n" + "-" * 52)
    print("[MIKRO-SENARYO] 29-kalip taramasi (4 sentetik rejim, spot dahil):")
    for name, trend, vol in [("UPTREND", 0.004, 0.012), ("DOWNTREND", -0.004, 0.012),
                             ("CHOP", 0.0, 0.010), ("VOLATILE", 0.001, 0.03)]:
        cs = _synthetic_candles(cfg.kline_limit, _SAHNE_SEED[name], trend, vol)
        snap = _synth_snapshot(name, cs, cfg, trend)
        try:
            mics = classify_micro(snap, build_structure(cs, cfg), cfg)
            ozet_m = ", ".join(f"#{m.mid}{m.ad.split('(')[0]}/{m.side[0]}({m.tier})"
                               for m in mics[:5]) or "kalip yok"
            print(f"  [{name:9s}] {len(mics)} kalip: {ozet_m}")
        except Exception as e:
            ok_all = False
            print(f"  [{name:9s}] !!! HATA: {str(e)[:60]}")
    # ── YASAM-DONGUSU TESTI: onceki sinyaller sonraki calistirmada dogru raporlaniyor mu? ──
    print("\n" + "-" * 52)
    print("[YASAM-DONGUSU] acik-sinyal takibi (HIT/DELIP-GECTI/STOP/GERI-DONDU/TERS/BE):")
    import tempfile as _tmp
    _old_log = os.environ.get("YON_PANEL_LOG")
    os.environ["YON_PANEL_LOG"] = _tmp.mktemp(suffix="_lc.jsonl")
    try:
        t0 = 1_700_000_000_000
        path_close = [100.0] * 45 + [101, 102, 103, 104, 105, 105,
                                     104.5, 103.8, 103.1, 102.4, 101.7, 101.4, 100.9, 100.5]
        lc = [Candle(open=c, high=c + 0.2, low=c - 0.4, close=c, volume=1000.0,
                     close_ms=t0 + i * 900_000) for i, c in enumerate(path_close)]
        ms = lambda i: t0 + i * 900_000
        rows = [
            # HIT + DELIP GECTI: SHORT @105, hedef 102 vuruldu, fiyat 100.5'e devam
            {"symbol": "LC", "bar_ms": ms(50), "side": "SHORT", "entry": 105.0,
             "target": 102.0, "inval": 107.5, "outcome": "OPEN"},
            # STOP: LONG @105, stop 103 kesildi
            {"symbol": "LC", "bar_ms": ms(49), "side": "LONG", "entry": 105.0,
             "target": 109.0, "inval": 103.0, "outcome": "OPEN"},
            # GERI DONDU (acik): LONG @100 hedef 106.5; %80'e ulasip 100.5'e dondu
            {"symbol": "LC", "bar_ms": ms(44), "side": "LONG", "entry": 100.0,
             "target": 106.5, "inval": 97.0, "outcome": "OPEN"},
            # BREAKEVEN (acik): SHORT @103.8 hedef 100.0; yolun %87'sinde
            {"symbol": "LC", "bar_ms": ms(52), "side": "SHORT", "entry": 103.8,
             "target": 100.0, "inval": 106.0, "outcome": "OPEN"},
            # STOPA YAKLASIYOR (acik): LONG @103.1, stop 99; fiyat stop yolunun %63'unde
            {"symbol": "LC", "bar_ms": ms(53), "side": "LONG", "entry": 103.1,
             "target": 108.0, "inval": 99.0, "outcome": "OPEN"},
            # GUC KAYBI adayi (acik): LONG @101.7; fiyat yerinde ama EV negatife dondu
            {"symbol": "LC", "bar_ms": ms(55), "side": "LONG", "entry": 101.7,
             "target": 107.0, "inval": 95.0, "outcome": "OPEN"},
        ]
        _save_signals(rows, cfg)
        snap_lc = Snapshot(symbol="LC", candles=lc, htf=lc[::16], stale=False)
        d_wait = _wait("test")
        record_and_resolve("LC", d_wait, snap_lc, cfg)
        st_lc = build_structure(lc, cfg)
        os.environ["YON_DETAY"] = "1"      # ADAY-oneri kuyruklari yalniz DETAY'da basilir
        try:
            rep = takip_raporu("LC", snap_lc, d_wait, st_lc, cfg)
            metin = "\n".join(rep)
            d_ters = _wait("test")
            d_ters.karar = "SHORT"      # motor ters yone dondu senaryosu
            metin_ters = "\n".join(takip_raporu("LC", snap_lc, d_ters, st_lc, cfg))
            d_guc = _wait("test", ev_long=-0.25, ev_short=0.05)   # BEKLE ama EV'ler hesaplanmis
            metin_guc = "\n".join(takip_raporu("LC", snap_lc, d_guc, st_lc, cfg))
        finally:
            os.environ.pop("YON_DETAY", None)
        # HUKUM modu (varsayilan): ayni takip OLCUMLERI basilir ama ADAY-oneri dili YOK
        metin_hukum = "\n".join(takip_raporu("LC", snap_lc, d_wait, st_lc, cfg))
        for etiket, kosul in [
            ("HEDEF+DELIP GECTI", "DELIP GECTI" in metin),
            ("STOP raporu", "STOP OLDU" in metin),
            ("hedefe yaklasip GERI DONDU", "GERI DONDU" in metin),
            ("breakeven onerisi", "GIRISE cekilebilir" in metin),
            ("STOPA-YAKLASIYOR uyarisi", "STOPA YAKLASIYOR" in metin),
            ("TERS DONDU uyarisi", "TERS DONDU" in metin_ters),
            ("GUC KAYBI (BEKLE'de EV ile)", "GUC KAYBI" in metin_guc),
            ("HUKUM modunda ADAY-oneri yok", "(ADAY)" not in metin_hukum
             and "breakeven esigi gecildi" in metin_hukum
             and "STOPA YAKLASIYOR" in metin_hukum),
        ]:
            ok_all = ok_all and kosul
            print(f"  {etiket:32s} {'OK' if kosul else '!!! EKSIK'}")
        for satir in rep:
            print(f"    {satir[:110]}")
    except Exception as e:
        ok_all = False
        print(f"  !!! YASAM-DONGUSU HATASI: {str(e)[:80]}")
    finally:
        try:
            os.remove(os.environ["YON_PANEL_LOG"])
        except Exception:
            pass
        if _old_log is None:
            os.environ.pop("YON_PANEL_LOG", None)
        else:
            os.environ["YON_PANEL_LOG"] = _old_log

    # ── SUPURME-KALIBRASYON TESTI: pay olculuyor mu + stop av-bolgesi DISINA cikiyor mu? ──
    print("\n" + "-" * 52)
    print("[SUPURME-KALIBRASYON] pay sabit degil OLCULEN derinlik olmali:")
    rngS = random.Random(31)
    csS = []
    pS, t0S = 100.0, 1_700_000_000_000
    for i in range(480):
        r = rngS.gauss(0, 0.006)
        oS = pS; pS = max(0.01, pS * (1 + r))
        hi = max(oS, pS) * (1 + abs(rngS.gauss(0, 0.002)))
        lo = min(oS, pS) * (1 - abs(rngS.gauss(0, 0.002)))
        csS.append(Candle(open=oS, high=hi, low=lo, close=pS, volume=1000.0,
                          close_ms=t0S + i * 900_000))
    # BILINEN-derinlikli supurmeler enjekte et: her 24 mumda ~1.2 ATR asagi igne + geri alis
    _a0 = atr_series(csS, cfg.atr_period)
    for i in range(80, 470, 24):
        ref_lo_i = min(c.low for c in csS[i - 40:i])
        csS[i].low = min(csS[i].low, ref_lo_i - 1.2 * _a0[i])
    atrsS = atr_series(csS, cfg.atr_period)
    pl, ph, nl, nh, pcal = supurme_olcumu(csS, atrsS, cfg)
    stS = build_structure(csS, cfg)
    _, _, stop_eski = scenario_levels(stS, "LONG", cfg)                    # sabit pad (0.30)
    _, _, stop_yeni = scenario_levels(stS, "LONG", cfg, pad_atr=pl)        # olculen pad
    derin_ok = pcal and pl > cfg.inval_pad_atr + 0.05 and pl <= cfg.sweep_pad_cap
    genis_ok = stop_yeni < stop_eski - 1e-9
    ok_all = ok_all and derin_ok and genis_ok
    print(f"  olculen pay: asagi {pl:.2f} ATR (n={nl}), yukari {ph:.2f} ATR (n={nh}) "
          f"{'OK' if derin_ok else '!!! olcum hatasi'}")
    print(f"  LONG stop: sabit-pad {_fmt(stop_eski)} -> olculen-pad {_fmt(stop_yeni)} "
          f"(DAHA DERIN) {'OK' if genis_ok else '!!! genislemedi'}")
    # fitil-hayatta-kalma: stopun DEMIRLENDIGI seviyenin 0.6 ATR supurulmesi
    # (scenario_levels ile ayni capa: fiyat altindaki en yuksek destek)
    aS = stS.atr
    _sup = [p for p in stS.swing_lows if p < stS.price] + [stS.range_low]
    capa = max(_sup)
    sup_dibi = capa - 0.6 * aS
    eski_yenir = sup_dibi <= stop_eski
    yeni_yasar = sup_dibi > stop_yeni
    ok_all = ok_all and eski_yenir and yeni_yasar
    print(f"  0.6-ATR supurme senaryosu: eski stop {'YENIR' if eski_yenir else '?'} / "
          f"yeni stop {'YASAR' if yeni_yasar else '!!! YENIR'}  "
          f"{'OK' if (eski_yenir and yeni_yasar) else '!!! HATA'}")

    # ── BAR-ICI KOPRU TESTI: fitil riski fiyatlaniyor mu? (p_stop artmali) ──
    print("\n" + "-" * 52)
    print("[KOPRU] bar-ici fitil simulasyonu (p_stop kapanis-yalniza gore ARTMALI):")
    csK = _synthetic_candles(400, 4242, 0.0, 0.012)
    stK = build_structure(csK, cfg)
    rngK = random.Random(7)
    pathsK, _ = mc_simulate(csK, stK, 0.0, cfg, rngK, paths_n=800)
    e_, t_, s_ = scenario_levels(stK, "LONG", cfg)
    pt0, ps0 = mc_first_passage(pathsK, e_, t_, s_, "LONG")                      # kopru KAPALI
    wsig = (stK.atr / stK.price) / cfg.bridge_range_div
    pt1, ps1 = mc_first_passage(pathsK, e_, t_, s_, "LONG",
                                wick_sig=wsig, rng=random.Random(11))            # kopru ACIK
    pt1b, ps1b = mc_first_passage(pathsK, e_, t_, s_, "LONG",
                                  wick_sig=wsig, rng=random.Random(11))          # determinizm
    kopru_ok = (ps1 > ps0) and (pt1 >= pt0 * 0.5) and (pt1b == pt1 and ps1b == ps1)
    ok_all = ok_all and kopru_ok
    print(f"  kapanis-yalniz: hedef %{pt0*100:.0f} stop %{ps0*100:.0f}   |   "
          f"koprulu: hedef %{pt1*100:.0f} stop %{ps1*100:.0f}   "
          f"{'OK (fitil riski gorunur + deterministik)' if kopru_ok else '!!! HATA'}")
    # ── OZ-ANALIZ smoke: rejim-fazi tablosu logdan uretiliyor mu? ──
    print("\n" + "-" * 52)
    print("[OZ-ANALIZ] analiz_metni logdan tablo uretimi:")
    _oldA = os.environ.get("YON_PANEL_LOG")
    os.environ["YON_PANEL_LOG"] = _tmp.mktemp(suffix="_an.jsonl")
    _oldAP = os.environ.get("YON_PLAN_LOG")
    os.environ["YON_PLAN_LOG"] = _tmp.mktemp(suffix="_an_plan.json")
    try:
        _save_signals([
            {"symbol": "T", "bar_ms": 1, "side": "LONG", "aile": "YUKARI-TREND",
             "taze": 0, "outcome": "HIT", "scen_cell": 13,
             "vol_rejim": "NORMAL", "htf_dir": 1},
            {"symbol": "T", "bar_ms": 2, "side": "LONG", "aile": "ASAGI-TREND",
             "taze": 1, "outcome": "STOP", "scen_cell": 13,
             "vol_rejim": "EXPANDING", "htf_dir": -1},
            {"symbol": "T", "bar_ms": 3, "side": "SHORT", "aile": "ASAGI-TREND",
             "taze": 0, "outcome": "HIT", "scen_cell": 13,
             "vol_rejim": "NORMAL", "htf_dir": -1},
        ], cfg)
        # pusu envanter regresyonu: ZAMAN-ASIMI kaydi tabloda GORUNMELI (envanter-fix)
        with open(os.environ["YON_PLAN_LOG"], "w", encoding="utf-8") as _fpl:
            json.dump({"T": {"pusu": [], "aktif": [], "hist": [
                {"tip": "LONG-TEPKI", "seviye": 1.0, "sonuc": "HEDEF", "olcum": 1, "ts": 1},
                {"tip": "SHORT-TEPKI", "seviye": 2.0, "sonuc": "ZAMAN-ASIMI", "ts": 2},
            ]}}, _fpl)
        _am = analiz_metni()
        an_ok = ("REJIM-FAZI" in _am and "ASAGI-TREND" in _am and "TAZE-DONUS" in _am
                 and "OZ-ANALIZ" in _am and "VOL-REJIM" in _am and "4S-UYUM" in _am
                 and "4s-KARSI" in _am and "zaman-asimi 1" in _am)
        ok_all = ok_all and an_ok
        print(f"  tablo uretimi (+vol-rejim/4s-uyum/zaman-asimi envanteri): "
              f"{'OK' if an_ok else '!!! HATA'}")
    except Exception as e:
        ok_all = False
        print(f"  !!! OZ-ANALIZ HATASI: {str(e)[:80]}")
    finally:
        for _evA in ("YON_PANEL_LOG", "YON_PLAN_LOG"):
            try:
                os.remove(os.environ[_evA])
            except Exception:
                pass
        if _oldA is None:
            os.environ.pop("YON_PANEL_LOG", None)
        else:
            os.environ["YON_PANEL_LOG"] = _oldA
        if _oldAP is None:
            os.environ.pop("YON_PLAN_LOG", None)
        else:
            os.environ["YON_PLAN_LOG"] = _oldAP

    # ── [MAKRO-OI-FUNDING] KAZANC-1 regresyonu: OI+/fiyat- hucresi funding-KOSULLU ──
    print("\n" + "-" * 52)
    print("[MAKRO-OI-FUNDING] OI+/fiyat-: funding normal->ASAGI, asiri-negatif->YUKARI, veri yok->eski:")
    rngMF = random.Random(41)
    t0MF = 1_700_000_000_000
    csMF = []
    pMF = 100.0
    for i in range(60):
        oMF = pMF
        pMF = pMF * (0.996 if i >= 56 else 1.0 + rngMF.gauss(0, 0.0008))
        csMF.append(Candle(open=oMF, high=max(oMF, pMF) * 1.0005, low=min(oMF, pMF) * 0.9995,
                           close=pMF, volume=1000.0, close_ms=t0MF + i * 900_000))
    for i, cMF in enumerate(csMF):        # OI: sakin gecmis + son 4 barda kademeli siskinlik
        cMF.oi = 1_000_000.0 * (1.0 + 0.0004 * math.sin(i)) * (1.0 + (0.01 * (i - 55) if i >= 56 else 0.0))
    fhMF = [0.0001 + 0.00003 * math.sin(i) for i in range(50)]
    snapMF = Snapshot(symbol="MOF", candles=csMF, htf=[], stale=False,
                      funding=0.0001, funding_hist=list(fhMF))
    eMA = macro_leading_estimate(snapMF, cfg)
    snapMF.funding = -0.004
    eMB = macro_leading_estimate(snapMF, cfg)
    snapMF.funding = None
    snapMF.funding_hist = None
    eMC = macro_leading_estimate(snapMF, cfg)
    okMA = eMA.p_up < 0.5 and "saglikli short devami" in eMA.note
    okMB = eMB.p_up > 0.5 and "sikisma" in eMB.note
    okMC = eMC.p_up > 0.5 and "sikisma" in eMC.note
    ok_all = ok_all and okMA and okMB and okMC
    print(f"  funding NORMAL   -> p_up={eMA.p_up:.2f} ({eMA.note[:42]}) {'OK' if okMA else '!!! HATA'}")
    print(f"  funding ASIRI(-) -> p_up={eMB.p_up:.2f} ({eMB.note[:42]}) {'OK' if okMB else '!!! HATA'}")
    print(f"  funding YOK      -> p_up={eMC.p_up:.2f} (eski davranis korunur) {'OK' if okMC else '!!! HATA'}")

    # ── [MIKRO-TUZAK] KAZANC-2 regresyonu: #28/#29 yem-yutulma-tuzak kombolari ──
    print("\n" + "-" * 52)
    print("[MIKRO-TUZAK] bant ucunda emilen agresif akis + OI siskin -> #28 SHORT / #29 LONG:")
    for _yonT, _midT, _dzT in (("TEPE", 28, +2.5), ("DIP", 29, -2.5)):
        csT9 = _synthetic_candles(220, 77 if _yonT == "TEPE" else 78, 0.0, 0.006)
        stT9 = build_structure(csT9, cfg)
        hedefT = stT9.range_high if _yonT == "TEPE" else stT9.range_low
        for j in (-3, -2, -1):            # son 3 mum bant ucunda DUZ kapanis (mom~0, konum uc)
            baseT = hedefT * (0.999 if _yonT == "TEPE" else 1.001)
            csT9[j] = Candle(open=baseT, high=baseT * 1.0008, low=baseT * 0.9992,
                             close=baseT, volume=1000.0, close_ms=csT9[j].close_ms)
        for i, cT9 in enumerate(csT9):
            cT9.oi = 1_000_000.0 * (1.0 + 0.0004 * math.sin(i)) * (1.0 + (0.01 * (i - 215) if i >= 216 else 0.0))
        ofT = OrderFlow(cvd=0.0, delta_z=_dzT, buckets_delta=[1.0] * 8,
                        buckets_price=[csT9[-1].close] * 8, whale_delta=0.0,
                        sell_climax_z=0.0, buy_climax_z=0.0, n=400)
        snT9 = Snapshot(symbol="TZK", candles=csT9, htf=csT9[::16][-60:], orderflow=ofT, stale=False)
        micsT = classify_micro(snT9, build_structure(csT9, cfg), cfg)
        mT = next((m for m in micsT if m.mid == _midT), None)
        beklenenT = "SHORT" if _midT == 28 else "LONG"
        okT = mT is not None and mT.side == beklenenT
        ok_all = ok_all and okT
        print(f"  {_yonT:4s} -> #{_midT} " + (f"bulundu side={mT.side} guc={mT.guc:.2f}" if mT else "BULUNAMADI")
              + f"  {'OK' if okT else '!!! HATA'}")

    # ── NO-LOOKAHEAD PREFIX TESTI: bar-i degeri GELECEK mumlar eklenince DEGISMEMELI ──
    # Mekanik kanit: ayni bar icin 'kesik seri' ile 'tam seri' birebir ayni sonucu
    # vermeli; vermezse ozellik hattina gelecek sizmis demektir (soz degil, olcum).
    print("\n" + "-" * 52)
    print("[NO-LOOKAHEAD] prefix-degismezligi (ATR + ozellik + markov, mekanik):")
    csP = _synthetic_candles(420, 909, 0.001, 0.012)
    atrsP = atr_series(csP, cfg.atr_period)
    pref_bad = []
    for iP in (120, 200, 300, 400):
        kes = csP[:iP + 1]
        atrsK = atr_series(kes, cfg.atr_period)
        if abs(atrsK[iP] - atrsP[iP]) > 1e-9 * max(1.0, atrsP[iP]):
            pref_bad.append(f"ATR@{iP}")
        fK = bar_features(kes, iP, atrsK, cfg)
        fF = bar_features(csP, iP, atrsP, cfg)
        if (fK is None) != (fF is None) or (fK is not None and any(
                abs(x - y) > 1e-9 * max(1.0, abs(y)) for x, y in zip(fK, fF))):
            pref_bad.append(f"ozellik@{iP}")
        mK, mF = _markov_pred_at(kes, iP), _markov_pred_at(csP, iP)
        if ((mK is None) != (mF is None) or
                (mK is not None and any(abs(a-b) > 1e-12 for a, b in zip(mK, mF)))):
            pref_bad.append(f"markov@{iP}")
    ok_all = ok_all and not pref_bad
    print(f"  4 kesit x (ATR, {len(FEATURES)} ozellik, markov) birebir ayni: "
          + ("OK (gelecek sizintisi yok)" if not pref_bad
             else "!!! SIZINTI: " + ", ".join(pref_bad)))

    # ── DUSMAN URETECLER: stop-avi / squeeze / gap + ozellik-tabanli degismezler ──
    print("\n" + "-" * 52)
    print("[DUSMAN-1 STOP-AVI] bant ekstremine 1.5-ATR igne + reclaim -> ters yonde islem YASAK:")
    for yonA, yasakA in (("ASAGI", "SHORT"), ("YUKARI", "LONG")):   # H4: iki yon birlikte
        for seedA in (11, 47, 202):
            csA = _stopavi_candles(cfg.kline_limit, seedA, yon=yonA)
            snapA = _synth_snapshot("SAV", csA, cfg, trend=0.0)
            dA = decide(snapA, cfg, context=DecisionContext.offline(csA[-1].close_ms))
            ihlA = _karar_degismezleri(dA, cfg)
            badA = (dA.karar == yasakA) or bool(ihlA)
            ok_all = ok_all and not badA
            print(f"  {yonA:6s} seed={seedA:3d} -> KARAR={dA.karar:5s} "
                  + ("OK" if not badA
                     else "!!! " + (f"{yasakA} (ava kurban); " if dA.karar == yasakA else "")
                     + "; ".join(ihlA)))
    print("\n[DUSMAN-2 SQUEEZE] sikisma once GORUNMELI, patlama aninda KORUMA olmali:")
    # Guvenlik ozelligi: patlama mumunda YA vol_regime patlamayi okur (EXPANDING/EXTREME)
    # YA ofori/kapitulasyon korumasi devrededir (TR > ext_bar_atr x ATR -> uc kovalanmaz).
    # Etiket mean(son3)/median yumusatmasiyla tek-mum sokunu OLCULDU +1 mumda yakalar
    # (bilincli); tehlike aninin bekcisi ext_bar'dir. Patlama ucunda yukari->LONG,
    # asagi->SHORT YASAK (H4: kapitulasyon dibi de ayni turda test edilir).
    for yonQ, yasakQ in (("YUKARI", "LONG"), ("ASAGI", "SHORT")):
        for seedQ in (5, 83):
            csQ = _squeeze_candles(cfg.kline_limit, seedQ, yon=yonQ)
            rej_on = vol_regime(csQ[:-1], cfg)
            rej_son = vol_regime(csQ, cfg)
            stQ = build_structure(csQ, cfg)
            korunma = (rej_son in ("EXPANDING", "EXTREME")) or \
                      (true_range(csQ[-1], csQ[-2]) >
                       cfg.ext_bar_atr * atr_series(csQ, cfg.atr_period)[-2])
            snapQ = _synth_snapshot("SQZ", csQ, cfg, trend=0.0)
            dQ = decide(snapQ, cfg, context=DecisionContext.offline(csQ[-1].close_ms))
            ihlQ = _karar_degismezleri(dQ, cfg)
            sik_ok = rej_on in ("COMPRESSED", "LOW")
            badQ = (dQ.karar == yasakQ) or (not sik_ok) or (not korunma) or bool(ihlQ)
            ok_all = ok_all and not badQ
            print(f"  {yonQ:6s} seed={seedQ:3d} -> oncesi={rej_on:10s} patlama={rej_son:9s}"
                  f"{'+uc-korumasi' if korunma and rej_son not in ('EXPANDING', 'EXTREME') else ''} "
                  f"KARAR={dQ.karar:5s} "
                  + ("OK" if not badQ
                     else "!!! " + (f"{yasakQ} (ucu kovaladi); " if dQ.karar == yasakQ else "")
                     + ("sikisma gorunmedi; " if not sik_ok else "")
                     + ("patlama korumasiz; " if not korunma else "") + "; ".join(ihlQ)))
    print("\n[DUSMAN-2b ASIRI-MUM PENCERESI] fitilsiz dev mum dipte, TR ~2.0x ONCEKI ATR:")
    # ATR-KIRLENME regresyonu (denetim): esik sok-mum-DAHIL ATR'ye olculdugunde etkin
    # esik ~2.17x ONCEKI ATR olur ve TR/ATR_onceki=2.01 fitilsiz dev kirmizi mum yeni
    # dipte SHORT'a izin veriyordu (dip kovalandi). Taban artik SON MUM HARIC ATR.
    csW = _synthetic_candles(cfg.kline_limit, 3, -0.003, 0.008)
    _oW = csW[-2].close
    _cW = _oW * (1 - 0.035)  # fixture, varsayilan 1000-mum ATR'de >2x on-sarti garanti eder
    csW[-1].open, csW[-1].close = _oW, _cW
    csW[-1].high = _oW * (1 + 1e-4)
    csW[-1].low = _cW * (1 - 1e-4)
    _aW = atr_series(csW[:-1], cfg.atr_period)[-1]
    _trW = true_range(csW[-1], csW[-2])
    snapW = _synth_snapshot("EXTW", csW, cfg, trend=-1.0)
    dWX = decide(snapW, cfg, context=DecisionContext.offline(csW[-1].close_ms))
    onsartW = _trW > cfg.ext_bar_atr * _aW           # pencere gercekten vuruluyor mu
    okW = onsartW and dWX.karar != "SHORT"
    ok_all = ok_all and okW
    print(f"  TR/ATR_onceki={_trW/_aW:.2f} (esik {cfg.ext_bar_atr:.1f}) -> KARAR={dWX.karar:5s}  "
          + ("OK (dip kovalanmadi)" if okW else
             ("!!! ON-SART tutmadi" if not onsartW else "!!! SHORT (dip kovalandi)")))

    # ── EXEC-YOL: KORUMA-BAGLAYICI ICRA REGRESYONLARI (mutasyon olcumu bulgusu) ──
    # Varsayilan esiklerde motor sentetik sahnelerde hep BEKLE dediginden dip/tepe
    # vetosu, EV kilidi ve ext_bar korumasi end-karar asserti uzerinden OLCULEMIYORDU:
    # koruma kaldirilinca da karar BEKLE kaliyor, mutant HAYATTA kaliyordu. Asagida
    # TEST-YEREL serbest esiklerle (urun Config'i degismez) korumanin BAGLAYICI kapi
    # oldugu sahneler kurulur: koruma kalkarsa motor fiilen sinyal/ters-yon uretir.
    _pcfg = replace(cfg, abstain_prob=0.34, disagree_max=2.0, ev_min_atr=0.0,
                    zero_skill_abstain=False,   # R3 kapisi test-yerel kapali: bu blok
                    #  EV/veto icra-yolunu olcer; sifir-skill kapisi ayri blokta olculur
                    dir_edge_min=0.0, market_rr_min=0.0, market_min_target_prob=0.0,
                    market_max_stop_prob=1.0, market_counter_wick_gate_enabled=False,
                    flip_thresh=9.9, veto_thresh=9.9)
    print("\n[KILIT-YOK EXEC-YOL] serbest esikte trend sahnesi SINYAL uretmeli (EV kapisi kilitli degil):")
    csE1 = _synthetic_candles(900, 2, 0.002, 0.004)
    snapE1 = _synth_snapshot("EXY", csE1, _pcfg)
    dE1 = decide(snapE1, _pcfg, context=DecisionContext.offline(csE1[-1].close_ms))
    okE1 = dE1.karar == "LONG"
    ok_all = ok_all and okE1
    print(f"  yukari-trend seed=2 -> KARAR={dE1.karar:5s}  "
          + ("OK (icra yolu acik)" if okE1 else "!!! LONG BEKLENIYORDU — EV kapisi kilitli/icra yolu olu"))
    csE1b = _synthetic_candles(900, 2, 0.002, 0.004)
    snapE1b = _synth_snapshot("EXY", csE1b, _pcfg)
    snapE1b.premium = {"next_funding_ms": csE1b[-1].close_ms + 30 * 60_000,
                       "server_ms": csE1b[-1].close_ms, "last_funding": 0.01,
                       "mark": csE1b[-1].close, "index": csE1b[-1].close}
    snapE1b.funding = 0.01
    dE1b = decide(snapE1b, _pcfg, context=DecisionContext.offline(csE1b[-1].close_ms))
    okE1b = (dE1b.karar == "BEKLE"
             and any("funding ust-siniri" in x for x in snapE1b.source_errors))
    ok_all = ok_all and okE1b
    print(f"  + settle 30dk & funding %1 -> KARAR={dE1b.karar:5s}  "
          + ("OK (funding ust-siniri EV/RR kapisinda)" if okE1b
             else "!!! FUNDING UST-SINIRI KARARI KESMEDI"))
    print("\n[V-DIP EXEC-YOL] dip-alti igne + cekic: SHORT vetosu BAGLAYICI olmali:")
    csE2 = _synthetic_candles(1000, 2, -0.0025, 0.004)  # sahne 1000-mum seriye kilitli (kline_limit'ten bagimsiz)
    _aE2s = atr_series(csE2, _pcfg.atr_period)
    _aE2 = _aE2s[-2] if len(_aE2s) >= 2 and _aE2s[-2] > 0 else _aE2s[-1]
    _pmE2 = min(c.low for c in csE2[-40:-1])
    _oE2 = csE2[-2].close
    _cE2 = _oE2 * (1 - 0.0005)
    csE2[-1].open, csE2[-1].close = _oE2, _cE2
    csE2[-1].low = min(_pmE2 - 0.10 * _aE2, _cE2 - 0.8 * _aE2)
    csE2[-1].high = max(_oE2, _cE2) * (1 + 1e-4)
    snapE2 = _synth_snapshot("EXD", csE2, _pcfg, trend=-1.0)
    dE2 = decide(snapE2, _pcfg, context=DecisionContext.offline(csE2[-1].close_ms))
    _onE2 = "SHORT yasak" in (dE2.sebep or "")
    okE2 = dE2.karar != "SHORT" and _onE2
    ok_all = ok_all and okE2
    print(f"  KARAR={dE2.karar:5s}  "
          + ("OK (dip short'lanmadi; veto baglayici)" if okE2 else
             ("!!! SHORT CIKTI (dip kovalandi)" if dE2.karar == "SHORT"
              else "!!! ON-SART tutmadi (veto baglayici degil): " + (dE2.sebep or "")[:60]))
          )
    print("\n[V-TEPE EXEC-YOL] taze tepe: LONG vetosu BAGLAYICI olmali:")
    csE3 = _vtop_candles(_pcfg.kline_limit, 7)
    snapE3 = _synth_snapshot("EXT", csE3, _pcfg, trend=1.0)
    dE3 = decide(snapE3, _pcfg, context=DecisionContext.offline(csE3[-1].close_ms))
    _onE3 = "LONG yasak" in (dE3.sebep or "")
    okE3 = dE3.karar != "LONG" and _onE3
    ok_all = ok_all and okE3
    print(f"  KARAR={dE3.karar:5s}  "
          + ("OK (tepe long'lanmadi; veto baglayici)" if okE3 else
             ("!!! LONG CIKTI (tepe kovalandi)" if dE3.karar == "LONG"
              else "!!! ON-SART tutmadi (veto baglayici degil): " + (dE3.sebep or "")[:60]))
          )
    print("\n[DUSMAN-2b EXEC-YOL] fitilsiz dev mum dipte: ext_bar korumasi BAGLAYICI olmali:")
    csE4 = _synthetic_candles(1000, 3, -0.003, 0.008)  # sahne 1000-mum seriye kilitli (kline_limit'ten bagimsiz)
    _oE4 = csE4[-2].close
    _cE4 = _oE4 * (1 - 0.035)
    csE4[-1].open, csE4[-1].close = _oE4, _cE4
    csE4[-1].high = _oE4 * (1 + 1e-4)
    csE4[-1].low = _cE4 * (1 - 1e-4)
    _aE4 = atr_series(csE4[:-1], _pcfg.atr_period)[-1]
    _onE4 = (true_range(csE4[-1], csE4[-2]) > _pcfg.ext_bar_atr * _aE4)
    snapE4 = _synth_snapshot("EXW", csE4, _pcfg, trend=-1.0)
    dE4 = decide(snapE4, _pcfg, context=DecisionContext.offline(csE4[-1].close_ms))
    _onE4 = _onE4 and "SHORT yasak" in (dE4.sebep or "")
    okE4 = dE4.karar != "SHORT" and _onE4
    ok_all = ok_all and okE4
    print(f"  KARAR={dE4.karar:5s}  "
          + ("OK (ASIRI-MUM vetosu baglayici)" if okE4 else
             ("!!! SHORT CIKTI (dip kovalandi)" if dE4.karar == "SHORT"
              else "!!! ON-SART tutmadi: " + (dE4.sebep or "")[:60]))
          )

    # ── [VARSAYILAN-SINYAL] (REPORT_4 #1/#2): URUN varsayilanlariyla iki yon de URETILMELI ──
    # Onceki bagimsiz denetim (Report 4): varsayilan esikler altinda ~520 sentetik sahnede
    # sifir LONG/SHORT; motor-uretimi SHORT hicbir kosulda gozlenmemisti. Asagidaki iki sahne
    # HICBIR ESIK SERBESTLESTIRMEDEN (Config() aynen: mc_paths=3000, kline_limit=1000, tum
    # kapilar acik) motorun uc karari da uretebildigini OLCER: gurultulu kalici trend
    # ogrenilebilir OOS kenar verir -> skill>0 -> abstain/uzlasi/EV/yon-dogrulugu/kalite/RR
    # kapilarinin TAMAMI sinyalle gecilir. Tick tape YOK (orderflow=None): karar contrarian
    # overlay'e degil OGRENEN kenara dayanir. Sahne secimi 120-sahnelik varsayilan-esik
    # taramasindan (7 LONG / 4 SHORT) deterministik iki temsilcidir; seed sabit, MC tohumu
    # veriden turetilir -> kosudan kosuya birebir ayni sonuc.
    print("\n" + "-" * 52)
    print("[VARSAYILAN-SINYAL] urun Config() ile LONG ve SHORT uretimi (serbestlestirme YOK):")
    _cfgVS = Config()          # urun varsayilanlari — bilerek selftest cfg'sinden bagimsiz
    # F3 (FABLE6_5) FIKSTUR NOTU: eski yukari-trend temsilcisi seed=3 artik DURUST BEKLE'dir —
    # sahnenin 144-hucre okumasi #18 'yukselis trendinde geri cekilme x likidite avi'
    # (side_hint=SHORT, haberci=2) ve SENARYO RISK KAPISI bant tepesinde LONG kovalatmaz
    # (asagida ayri regresyonla OLCULUR). 'Varsayilanla LONG uretilir' kaniti icin temsilci
    # sahne seed=5'tir (#13 TREND-UP-PULLBACK/NEUTRAL: senaryo karara karsi degil).
    for _adVS, _sdVS, _trVS, _vlVS, _wantVS in (
            ("yukari-trend", 5, +0.004, 0.008, "LONG"),
            ("asagi-trend", 1, -0.004, 0.008, "SHORT")):
        _csVS = _synthetic_candles(_cfgVS.kline_limit, _sdVS, _trVS, _vlVS)
        _snVS = _synth_snapshot("VSY", _csVS, _cfgVS, trend=0.0)
        _snVS.orderflow = None
        _dVS = decide(_snVS, _cfgVS, context=DecisionContext.offline(_csVS[-1].close_ms))
        _geoVS = (_dVS.entry is not None and _dVS.target is not None and _dVS.stop is not None
                  and ((_dVS.stop < _dVS.entry < _dVS.target) if _wantVS == "LONG"
                       else (_dVS.target < _dVS.entry < _dVS.stop)))
        okVS = _dVS.karar == _wantVS and _geoVS
        ok_all = ok_all and okVS
        print(f"  {_adVS} seed={_sdVS} -> KARAR={_dVS.karar:5s} EV=%{_dVS.ev*100:.0f}·ATR "
              f"RR={_dVS.rr:.2f} kapi={_dVS.gate_code}  "
              + ("OK (varsayilanla uretildi; geometri tutarli)" if okVS else
                 f"!!! {_wantVS} BEKLENIYORDU (REPORT_4 #1/#2 regresyonu)"))
    # ── F3 (FABLE6_5) SENARYO RISK KAPISI regresyonu: bant tepesinde likidite-avi okumasi
    # (hucre #18, hint=SHORT, haberci=2) varken URUN varsayilanlariyla LONG market ACILMAZ;
    # gerekce gorunur olmali. (Ayni sahne eski surumde LONG uretiyordu — davranis degisikligi
    # BILINCLI ve kullanici sozlesmesidir; kapi kapatilirsa [scen_risk_gate_enabled=False]
    # eski davranis geri gelir.)
    _csF3 = _synthetic_candles(_cfgVS.kline_limit, 3, +0.004, 0.008)
    _snF3 = _synth_snapshot("VSY", _csF3, _cfgVS, trend=0.0)
    _snF3.orderflow = None
    _dF3 = decide(_snF3, _cfgVS, context=DecisionContext.offline(_csF3[-1].close_ms))
    _cfgF3k = replace(_cfgVS, scen_risk_gate_enabled=False)
    _dF3k = decide(_snF3, _cfgF3k, context=DecisionContext.offline(_csF3[-1].close_ms))
    okF3 = (_dF3.karar == "BEKLE" and "SENARYO RISK KAPISI" in (_dF3.sebep or "")
            and _dF3k.karar == "LONG")
    ok_all = ok_all and okF3
    print(f"  F3 senaryo-kapisi (seed=3, hucre likidite-avi/SHORT): kapi ACIK -> "
          f"KARAR={_dF3.karar} | kapi KAPALI -> KARAR={_dF3k.karar}  "
          + ("OK (ters hucre okumasi marketi kesti; fark kapidan)" if okF3
             else "!!! F3 kapisi beklendigi gibi calismadi"))

    print("\n[DUSMAN-3 GAP] %5 bosluklu acilis (iki yon) -> cokme yok, degismezler saglam:")
    for yonG in ("ASAGI", "YUKARI"):
        for seedG in (9, 314):
            csG = _gap_candles(cfg.kline_limit, seedG, yon=yonG)
            snapG = _synth_snapshot("GAP", csG, cfg, trend=0.0)
            try:
                dG = decide(snapG, cfg, context=DecisionContext.offline(csG[-1].close_ms))
                ihlG = _karar_degismezleri(dG, cfg)
                kararG = dG.karar
            except Exception as e:
                ihlG = [f"COKME: {str(e)[:60]}"]
                kararG = "?"
            ok_all = ok_all and not ihlG
            print(f"  {yonG:6s} seed={seedG:3d} -> KARAR={kararG:5s} "
                  + ("OK" if not ihlG else "!!! " + "; ".join(ihlG)))

    # ── DEGISMEZLER: determinizm + fiyat-olcek bagimsizligi (sihirli-sayi bekcisi) ──
    # x1000 olcek DOGE(0.07)–BTC(100k) araligini temsil eder: veri-goreli katmanlar
    # (ozellik/rejim/veto/supurme) fiyat olceginden BAGIMSIZ olmali. Karar-duzeyi
    # birebir KARSILASTIRILMAZ: MC seed'i mutlak fiyattan turetilir (bilincli).
    print("\n[DUSMAN-4 DEGISMEZLER] determinizm + fiyat-olcek bagimsizligi:")
    csD = _synthetic_candles(cfg.kline_limit, 4242, 0.002, 0.012)
    snapD = _synth_snapshot("DET", csD, cfg, trend=0.002)
    _ctxD = DecisionContext.offline(csD[-1].close_ms)
    dD1, dD2 = decide(snapD, cfg, context=_ctxD), decide(snapD, cfg, context=_ctxD)
    det_ok = (dD1.karar, dD1.entry, dD1.target, dD1.stop, dD1.prob) == \
             (dD2.karar, dD2.entry, dD2.target, dD2.stop, dD2.prob)
    ok_all = ok_all and det_ok
    print(f"  determinizm (ayni girdi -> ayni karar/seviye): {'OK' if det_ok else '!!! FARKLI CIKTI'}")
    _K = 1000.0
    csDk = [Candle(open=c.open * _K, high=c.high * _K, low=c.low * _K, close=c.close * _K,
                   volume=c.volume, close_ms=c.close_ms) for c in csD]
    atrsD1 = atr_series(csD, cfg.atr_period)
    atrsDk = atr_series(csDk, cfg.atr_period)
    fD1 = bar_features(csD, len(csD) - 1, atrsD1, cfg)
    fDk = bar_features(csDk, len(csDk) - 1, atrsDk, cfg)
    olc_bad = []
    if fD1 is None or fDk is None or any(abs(x - y) > 1e-6 * max(1.0, abs(y))
                                         for x, y in zip(fDk, fD1)):
        olc_bad.append("ozellikler")
    if vol_regime(csD, cfg) != vol_regime(csDk, cfg):
        olc_bad.append("vol_regime")
    pads1 = supurme_olcumu(csD, atrsD1, cfg)
    padsk = supurme_olcumu(csDk, atrsDk, cfg)
    if any(abs(a - b) > 1e-6 for a, b in zip(pads1[:2], padsk[:2])) or pads1[2:] != padsk[2:]:
        olc_bad.append("supurme_olcumu")
    csV = _vdip_candles(cfg.kline_limit, 7)
    csVk = [Candle(open=c.open * _K, high=c.high * _K, low=c.low * _K, close=c.close * _K,
                   volume=c.volume, close_ms=c.close_ms) for c in csV]
    if _dip_rejection(csV, cfg) != _dip_rejection(csVk, cfg):
        olc_bad.append("_dip_rejection")
    csT2 = _vtop_candles(cfg.kline_limit, 7)
    csT2k = [Candle(open=c.open * _K, high=c.high * _K, low=c.low * _K, close=c.close * _K,
                    volume=c.volume, close_ms=c.close_ms) for c in csT2]
    if _top_rejection(csT2, cfg) != _top_rejection(csT2k, cfg):
        olc_bad.append("_top_rejection")
    stD1, stDk = build_structure(csD, cfg), build_structure(csDk, cfg)
    if stD1.valid and stDk.valid and stD1.atr > 0 and stDk.atr > 0:
        r1 = (stD1.price - stD1.range_low) / stD1.atr
        rk = (stDk.price - stDk.range_low) / stDk.atr
        if abs(r1 - rk) > 1e-6 * max(1.0, abs(r1)):
            olc_bad.append("yapi(range/ATR)")
    ok_all = ok_all and not olc_bad
    print("  x1000 fiyat olcegi (ozellik/rejim/veto/supurme/yapi ayni): "
          + ("OK (mutlak-fiyat sihirli sayisi yok)" if not olc_bad
             else "!!! OLCEK BAGIMLI: " + ", ".join(olc_bad)))

    # ── SECICILIK + YON-TUTARLILIK REGRESYONU ──
    # FABLE6 dusuk guvende zorla islem acmaz; sentetik sahnede sinyal sayisi asgari
    # kosul degildir. Korunan degismez: bariz yukseliste SHORT, dususte LONG kovalanmaz.
    print("\n" + "-" * 52)
    print("[SECICILIK/YON-TUTARLILIK] tahmin-yok serbest + ters trend kovalamak yasak:")
    sinyal_n = sum(1 for v in sahne_karar.values() if v in ("LONG", "SHORT"))
    kilit_ok = all(v in ("LONG", "SHORT", "BEKLE") for v in sahne_karar.values())
    yon_ok = sahne_karar.get("DOWNTREND") != "LONG" and sahne_karar.get("UPTREND") != "SHORT"
    ok_all = ok_all and kilit_ok and yon_ok
    print("  sahneler: " + ", ".join(f"{a}={b}" for a, b in sahne_karar.items()))
    print(f"  sinyal={sinyal_n}/4; tahmin-yok zorlanmadi: {'OK' if kilit_ok else '!!! GECERSIZ KARAR'}")
    print(f"  UPTREND!=SHORT ve DOWNTREND!=LONG: {'OK' if yon_ok else '!!! TERS-YON BIASI'}")

    # ── [SIFIR-SKILL] R3 (REPORT_3): skill=0 iken overlay bloklari market ACAMAZ ──
    # Sahne 0.45-0.4667 acik araligini bilerek vurur: 500 mumluk rastgele yuruyus
    # (etkin-OOS kohortu ~13 < skill_min_oos=20 -> skill YAPISAL olarak 0) + guclu
    # flow/macro overlay (p~0.70 -> pooled max sinif ~0.4666 >= 0.45). Kapi ACIKKEN
    # kesin gerekceyle BEKLE; kapi KAPALIYKEN ayni sahne baska gerekceye/karara akar.
    print("\n" + "-" * 52)
    print("[SIFIR-SKILL] sifir-skill + guclu overlay: R3 kapisi baglayici mi:")
    csZ = _synthetic_candles(500, 9091, 0.0, 0.011)
    for _cZ in csZ:
        _cZ.taker = 1.0
    _pZ = csZ[-5].close
    for _j in range(4):                     # son 4 mum: hafif dusus (OI+/fiyat- hucresi)
        _iZ = len(csZ) - 4 + _j
        _oZ = _pZ
        _pZ = _pZ * (1 - 0.0012)
        csZ[_iZ] = Candle(open=_oZ, high=_oZ * 1.0004, low=_pZ * 0.9996, close=_pZ,
                          volume=1000.0, taker=1.0, close_ms=csZ[_iZ].close_ms)
    for _i, _cZ in enumerate(csZ):          # OI: sakin gecmis + son 4 barda siskinlik
        _cZ.oi = 1_000_000.0 * (1.0 + 0.0004 * math.sin(_i)) * \
            (1.0 + (0.012 * (_i - (len(csZ) - 5)) if _i >= len(csZ) - 4 else 0.0))
    _bpZ = [csZ[-1].close * (1.0 + 1e-5 * (_k * _k)) for _k in range(8)]  # ivmelenen bp -> radar susar
    _ofZ = OrderFlow(cvd=500.0, delta_z=8.0, buckets_delta=[1.0] * 8,
                     buckets_price=_bpZ, whale_delta=0.0,
                     sell_climax_z=0.0, buy_climax_z=0.0, n=400)
    snapZ = Snapshot(symbol="ZSK", candles=csZ, htf=csZ[::16][-60:], orderflow=_ofZ,
                     funding=-0.005, funding_hist=[0.0001 * math.sin(_i) for _i in range(50)],
                     taker_ratio=1.5, stale=False)
    _atrsZ = atr_series(csZ, cfg.atr_period)
    _XZ, _yZ, _iZs = build_training(csZ, _atrsZ, cfg)
    _skZ = skill_weights(_XZ, _yZ, _iZs, csZ, _atrsZ, cfg,
                         random.Random(_mirror_invariant_seed(csZ) ^ 0x5f3759df))
    _onZ1 = max(_skZ.values()) <= 0.0
    dZon = decide(snapZ, cfg, context=DecisionContext.offline(csZ[-1].close_ms))
    _onZ2 = max(dZon.p_down, dZon.p_flat, dZon.p_up) >= cfg.abstain_prob - 1e-9
    okZ1 = _onZ1 and _onZ2 and "SIFIR-SKILL" in (dZon.sebep or "")
    dZoff = decide(snapZ, replace(cfg, zero_skill_abstain=False),
                   context=DecisionContext.offline(csZ[-1].close_ms))
    okZ2 = "SIFIR-SKILL" not in (dZoff.sebep or "")
    ok_all = ok_all and okZ1 and okZ2
    print(f"  on-sart: skill agirliklari hepsi 0: {'OK' if _onZ1 else '!!! TUTMADI'} | "
          f"max sinif %{max(dZon.p_down, dZon.p_flat, dZon.p_up)*100:.1f} >= "
          f"%{cfg.abstain_prob*100:.0f}: {'OK' if _onZ2 else '!!! TUTMADI'} "
          f"(acik 0.45-0.4667 araligi vuruldu)")
    print(f"  kapi ACIK  -> {dZon.karar}: {(dZon.sebep or '')[:62]}  "
          f"{'OK' if okZ1 else '!!! KAPI ISLEMEDI'}")
    print(f"  kapi KAPALI-> {dZoff.karar}: {(dZoff.sebep or '')[:62]}  "
          f"{'OK (fark kapidan)' if okZ2 else '!!! HATA'}")

    # ── [IMKANSIZ-HUCRE] R4 (REPORT_3): belgelenen 15 hucre uretilmemeli + formul ──
    print("\n" + "-" * 52)
    print("[IMKANSIZ-HUCRE] SCEN_IMKANSIZ_HUCRELER taramasi + hucre-formul degismezi:")
    _ih_kotu: List[str] = []
    _ih_setler: List[Tuple[str, List[Candle]]] = []
    for _nmH, _trH, _vlH in (("UP", 0.004, 0.012), ("DN", -0.004, 0.012),
                             ("CH", 0.0, 0.010), ("VO", 0.001, 0.03)):
        for _sdH in (1, 7, 42):
            _ih_setler.append((f"{_nmH}{_sdH}", _synthetic_candles(400, _sdH, _trH, _vlH)))
    for _sdH in (7, 21):
        _ih_setler.append((f"VDIP{_sdH}", _vdip_candles(400, _sdH)))
        _ih_setler.append((f"VTOP{_sdH}", _vtop_candles(400, _sdH)))
    for _ynH in ("ASAGI", "YUKARI"):
        _ih_setler.append((f"SAV-{_ynH}", _stopavi_candles(400, 11, yon=_ynH)))
        _ih_setler.append((f"SQZ-{_ynH}", _squeeze_candles(400, 5, yon=_ynH)))
        _ih_setler.append((f"GAP-{_ynH}", _gap_candles(400, 9, yon=_ynH)))
    for _adH, _csH in _ih_setler:
        _snH = _synth_snapshot(_adH, _csH, cfg, trend=0.0)
        _scH = classify_scenario(_snH, build_structure(_csH, cfg), cfg)
        if _scH.cell in SCEN_IMKANSIZ_HUCRELER:
            _ih_kotu.append(f"{_adH}:#{_scH.cell}")
        if _scH.regime_idx >= 1 and _scH.cell != (_scH.regime_idx - 1) * 12 + _scH.event_idx:
            _ih_kotu.append(f"{_adH}:formul")
    okH = (not _ih_kotu) and len(SCEN_IMKANSIZ_HUCRELER) == 15
    ok_all = ok_all and okH
    print(f"  {len(_ih_setler)} siniflandirma tarandi; 15 belgeli hucre + formul ihlali: "
          + ("YOK — OK" if okH else "!!! " + ", ".join(_ih_kotu[:6])))

    # ── [R5 REJIM-GORUNUMU] uc taksonomi tek-kaynak nesnede + ekranda ──
    print("\n" + "-" * 52)
    print("[R5 REJIM-GORUNUMU] kanonik gorunum alt-fonksiyonlarla birebir + render satiri:")
    _scT5 = classify_scenario(snapT, build_structure(csT, cfg), cfg)
    _rgv5 = rejim_gorunumu(snapT, cfg, _scT5)
    ok5a = (_rgv5.vol == vol_regime(csT, cfg) and _rgv5.aile == rejim_ailesi(snapT, cfg)
            and _rgv5.family6 == _scT5.family6)
    ok5b = "REJIM (tek-kaynak" in rT0
    ok_all = ok_all and ok5a and ok5b
    print(f"  alan esitligi (vol/aile/family6): {'OK' if ok5a else '!!! HATA'}")
    print(f"  render'da tek-kaynak satiri (hukum modunda da): {'OK' if ok5b else '!!! YOK'}")

    # ── REJIM-AILESI REGRESYONU (canli SOL d68a547 + BTC 9b7abb3 bulgulari) ──
    # Tek-mum tepki sicramasi aileyi CEVIRMEZ (hem tb==0 yedek yol hem 15m-oncelik
    # yolu); surdurulmus 15m egilimi (1s yatayken) CEVIRIR. Kosul on-sartlari (mb /
    # mb_once) olculup yazdirilir ki test hedef kod yolunu GERCEKTEN vurdugu gorulsun.
    print("\n" + "-" * 52)
    print("[REJIM-AILESI] tek-mum tepki cevirmez / surdurulmus egilim cevirir:")
    t0R = 1_700_000_000_000

    def _duzseri(n, seed, drift=0.0):
        rngR = random.Random(seed)
        outR, pR = [], 100.0
        for i in range(n):
            oR = pR
            rR = drift + (100.0 - pR) / pR * 0.3 + rngR.gauss(0, 0.002)  # ort-donuslu yatay
            pR = max(0.01, pR * (1 + rR))
            outR.append(Candle(open=oR, high=max(oR, pR) * 1.001, low=min(oR, pR) * 0.999,
                               close=pR, volume=1000.0, close_ms=t0R + i * 900_000))
        return outR
    htf_duz = [Candle(open=100.0, high=100.1, low=99.9, close=100.0, volume=1.0,
                      close_ms=t0R + i * 3_600_000) for i in range(60)]
    _rngH = random.Random(4)
    htf_inen, _pH = [], 100.0
    for i in range(60):
        _oH = _pH
        _pH *= (1 - 0.003)
        htf_inen.append(Candle(open=_oH, high=_oH * 1.0005, low=_pH * 0.9995,
                               close=_pH, volume=1.0, close_ms=t0R + i * 3_600_000))
    # A: 1s YATAY + 15m TEK-MUM sicrama -> aile YUKARI-TREND OLMAMALI (tb==0 yedek yol)
    # sicrama market_bias'in kendi penceresine (c[-1]-c[-6]) gore kurulur; c[-2]'ye gore
    # kurulunca 5-bar drift sicramayi iptal edip on-sarti dusurebiliyordu (olculdu)
    csRA = _duzseri(300, seed=3)
    aRA = atr_series(csRA, cfg.atr_period)[-1]
    csRA[-1].close = csRA[-6].close + 1.2 * aRA
    csRA[-1].high = max(csRA[-1].open, csRA[-1].close) * 1.0005
    mbA = market_bias(csRA, cfg)
    mbA_once = market_bias(csRA[:-cfg.taze_donus_bars], cfg)
    onsartA = mbA >= 0.3 and abs(mbA_once) < 0.3       # yedek yolun tam vurulan dali
    aileA = rejim_ailesi(Snapshot(symbol="RA", candles=csRA, htf=htf_duz, stale=False), cfg)
    okA = onsartA and aileA != "YUKARI-TREND"
    ok_all = ok_all and okA
    print(f"  A tek-mum (1s yatay, mb={mbA:+.2f} once={mbA_once:+.2f}) -> aile={aileA:12s} "
          + ("OK (cevirmedi)" if okA else ("!!! ON-SART tutmadi" if not onsartA else "!!! CEVIRDI")))
    # B: 1s YATAY + SURDURULMUS 15m egilim (16 mum) -> YUKARI-TREND OLMALI (yedek yol)
    csRB = _duzseri(300, seed=5)
    _pB = csRB[-17].close
    for j in range(16):
        i = len(csRB) - 16 + j
        _oB = _pB
        _pB *= 1.004
        csRB[i] = Candle(open=_oB, high=_pB * 1.0005, low=_oB * 0.9995, close=_pB,
                         volume=1000.0, close_ms=csRB[i].close_ms)
    mbB = market_bias(csRB, cfg)
    mbB_once = market_bias(csRB[:-cfg.taze_donus_bars], cfg)
    aileB = rejim_ailesi(Snapshot(symbol="RB", candles=csRB, htf=htf_duz, stale=False), cfg)
    okB = aileB == "YUKARI-TREND"
    ok_all = ok_all and okB
    print(f"  B surdurulmus (1s yatay, mb={mbB:+.2f} once={mbB_once:+.2f}) -> aile={aileB:12s} "
          + ("OK (cevirdi)" if okB else "!!! CEVIRMEDI"))
    # C: 1s ASAGI + 15m TEK-MUM sicrama -> aile ASAGI-TREND KALMALI (15m-oncelik yolu)
    csRC = _duzseri(300, seed=8)
    aRC = atr_series(csRC, cfg.atr_period)[-1]
    csRC[-1].close = csRC[-6].close + 1.2 * aRC
    csRC[-1].high = max(csRC[-1].open, csRC[-1].close) * 1.0005
    mbC = market_bias(csRC, cfg)
    mbC_once = market_bias(csRC[:-cfg.taze_donus_bars], cfg)
    onsartC = mbC >= 0.35 and abs(mbC_once) < 0.35     # oncelik yolunun tam vurulan dali
    aileC = rejim_ailesi(Snapshot(symbol="RC", candles=csRC, htf=htf_inen, stale=False), cfg)
    okC = onsartC and aileC == "ASAGI-TREND"
    ok_all = ok_all and okC
    print(f"  C tek-mum (1s ASAGI, mb={mbC:+.2f} once={mbC_once:+.2f}) -> aile={aileC:12s} "
          + ("OK (1s ezilmedi)" if okC else ("!!! ON-SART tutmadi" if not onsartC else "!!! CEVIRDI")))

    # ── KABUL-BAYRAGI BIRIM REGRESYONU (T8 kok nedeninin ilkel-duzey bekcisi) ──
    # 'Kabul edilmis kirilim' (k+ kapanis seviyenin otesinde) True; 'taze supurme'
    # (fitil gecti, kapanislar geri icerde) False OLMALI — dort yon/durum birlikte.
    # Karar-duzeyi olcum (40 seed): duz dusus sahnesindeki SHORT bu bayraga dayanmiyor;
    # bu yuzden bekci ILKELIN KENDISIDIR, dolayli sahne degil.
    print("\n" + "-" * 52)
    print("[KABUL-BAYRAGI] kabul edilmis kirilim=True / taze supurme=False (dn+up):")
    t0K2 = 1_700_000_000_000

    def _mumK(o, h, l, c, i):
        return Candle(open=o, high=h, low=l, close=c, volume=1000.0,
                      close_ms=t0K2 + i * 900_000)
    lvl = 100.0
    kabul_dn = [_mumK(101, 101.5, 100.5, 101, 0), _mumK(101, 101.2, 98.8, 99.2, 1),
                _mumK(99.2, 99.6, 98.5, 99.0, 2), _mumK(99.0, 99.4, 98.2, 98.6, 3),
                _mumK(98.6, 99.1, 98.0, 98.4, 4)]                     # 4 kapanis ALTINDA
    taze_dn = [_mumK(101, 101.5, 100.5, 101, 0), _mumK(101, 101.2, 100.4, 100.8, 1),
               _mumK(100.8, 101.0, 98.5, 100.6, 2),                   # fitil alta, kapanis ustte
               _mumK(100.6, 101.1, 100.2, 100.9, 3), _mumK(100.9, 101.3, 100.5, 101.1, 4)]
    kabul_up = [_mumK(99, 99.5, 98.5, 99, 0), _mumK(99, 101.2, 98.8, 100.8, 1),
                _mumK(100.8, 101.5, 100.4, 101.0, 2), _mumK(101.0, 101.8, 100.6, 101.4, 3),
                _mumK(101.4, 102.0, 101.0, 101.6, 4)]                 # 4 kapanis USTUNDE
    taze_up = [_mumK(99, 99.5, 98.5, 99, 0), _mumK(99, 99.6, 98.6, 99.2, 1),
               _mumK(99.2, 101.5, 98.9, 99.4, 2),                     # fitil uste, kapanis altta
               _mumK(99.4, 99.8, 98.9, 99.1, 3), _mumK(99.1, 99.5, 98.7, 99.3, 4)]
    kb_durum = [
        ("dn kabul edilmis kirilim", _accepted_break(kabul_dn, lvl, "dn", 5, 3), True),
        ("dn taze supurme",          _accepted_break(taze_dn, lvl, "dn", 5, 3), False),
        ("up kabul edilmis kirilim", _accepted_break(kabul_up, lvl, "up", 5, 3), True),
        ("up taze supurme",          _accepted_break(taze_up, lvl, "up", 5, 3), False),
    ]
    for adK, gozlem, beklenenK in kb_durum:
        okK = gozlem is beklenenK
        ok_all = ok_all and okK
        print(f"  {adK:26s} -> {str(gozlem):5s} (beklenen {beklenenK})  "
              f"{'OK' if okK else '!!! HATA'}")

    # ── KOSULLU PLAN (PUSU): tetik haritasi artik SOZLESME — 5 durum + 2-calistirma e2e ──
    print("\n" + "-" * 52)
    print("[KOSULLU-PLAN] igne+geri alis tetigi mekanik olculuyor mu (5 durum + e2e):")
    t0P = 1_700_000_000_000
    _mumP = lambda h, l, c, i, o=100.0: Candle(open=o, high=h, low=l, close=c,
                                               volume=1000.0, close_ms=t0P + (i + 1) * 900_000)
    planL = {"tip": "LONG-TEPKI", "seviye": 100.0, "stop": 99.5, "hedef": 101.5, "bar_ms": t0P}
    planS = {"tip": "SHORT-TEPKI", "seviye": 100.0, "stop": 100.5, "hedef": 98.5, "bar_ms": t0P}
    kP, HP = cfg.sweep_reclaim_bars, cfg.signal_horizon_bars
    d1 = _plan_degerlendir(planL, [_mumP(100.4, 99.4, 100.3, 0), _mumP(101.6, 100.2, 101.4, 1)], kP, HP)
    d2 = _plan_degerlendir(planL, [_mumP(100.1, 99.6, 99.7, 0), _mumP(100.5, 99.8, 100.4, 1),
                                   _mumP(100.6, 99.4, 99.6, 2)], kP, HP)
    d3 = _plan_degerlendir(planL, [_mumP(100.1, 99.3, 99.7, 0)] +
                           [_mumP(99.9, 99.4, 99.6, j) for j in range(1, 2 + kP)], kP, HP)
    d4 = _plan_degerlendir(planL, [_mumP(100.8, 100.2, 100.5, j) for j in range(3)], kP, HP)
    d5 = _plan_degerlendir(planL, [_mumP(100.8, 100.2, 100.5, j) for j in range(HP + 1)], kP, HP)
    dS = _plan_degerlendir(planS, [_mumP(100.6, 99.9, 99.8, 0), _mumP(100.0, 98.4, 98.6, 1)], kP, HP)
    # GEC-KACTI: geri-alis kapanisi hedefin OTESINDE -> islem penceresi kacti, karne-disi
    planG = {"tip": "LONG-TEPKI", "seviye": 100.0, "stop": 99.5, "hedef": 100.6, "bar_ms": t0P}
    dGK = _plan_degerlendir(planG, [_mumP(100.9, 99.4, 100.8, 0)], kP, HP)
    plan_durumlar = [
        ("ayni-mum reclaim -> ATESLENDI+HEDEF (+1.5R)",
         d1["durum"] == "ATESLENDI" and d1["sonuc"] == "HEDEF" and abs(d1["r"] - 1.5) < 1e-9),
        ("alt kapanis + k icinde geri alis -> ATESLENDI, sonra STOP",
         d2["durum"] == "ATESLENDI" and d2["sonuc"] == "STOP"),
        ("k penceresi boyunca altta kapanis -> IPTAL (teyitli kirilim)",
         d3["durum"] == "IPTAL"),
        ("seviye test edilmedi -> BEKLEMEDE", d4["durum"] == "BEKLEMEDE"),
        (f"{HP}+ mum tetiksiz -> SURE-DOLDU", d5["durum"] == "SURE-DOLDU"),
        ("SHORT simetri: ust igne+geri alis -> ATESLENDI+HEDEF",
         dS["durum"] == "ATESLENDI" and dS["sonuc"] == "HEDEF"),
        ("giris hedefin otesinde -> GEC-KACTI (karne-disi)",
         dGK["durum"] == "ATESLENDI" and dGK["sonuc"] == "GEC-KACTI"),
    ]
    for adP, kosulP in plan_durumlar:
        ok_all = ok_all and kosulP
        print(f"  {adP:52s} {'OK' if kosulP else '!!! HATA'}")
    # e2e: calistirma-1 pusu kurar; arada igne+geri alis olur; calistirma-2 RAPORLAR
    _oldPL = os.environ.get("YON_PLAN_LOG")
    _pl_temps = [_tmp.mktemp(suffix="_plan.json")]
    os.environ["YON_PLAN_LOG"] = _pl_temps[0]
    try:
        csE = _stopavi_candles(cfg.kline_limit, 11)[:-1]          # supurme HENUZ yok
        snapE1 = _synth_snapshot("PLE", csE, cfg, trend=0.0)
        stE = build_structure(csE, cfg)
        micE = classify_micro(snapE1, stE, cfg)
        kurulan = plan_kur("PLE", snapE1, stE, micE, cfg,
                           mc_ilk={"p_ust": 0.1, "p_alt": 0.6})   # F2: LONG kenari sec
        sevE = next(p["seviye"] for p in kurulan if p["tip"] == "LONG-TEPKI")
        aE = stE.atr
        tE = csE[-1].close_ms
        csE2 = csE + [Candle(open=csE[-1].close, high=csE[-1].close + 0.1 * aE,
                             low=sevE - 1.2 * aE, close=sevE + 0.5 * aE,   # igne + geri alis
                             volume=1000.0, close_ms=tE + 900_000),
                      Candle(open=sevE + 0.5 * aE, high=sevE + 0.9 * aE,
                             low=sevE + 0.3 * aE, close=sevE + 0.8 * aE,
                             volume=1000.0, close_ms=tE + 1_800_000)]
        snapE2 = _synth_snapshot("PLE", csE2, cfg, trend=0.0)
        rapE = "\n".join(plan_takip("PLE", snapE2, cfg))
        e2e_ok = ("ATESLENDI" in rapE) and ("LONG-TEPKI" in rapE)
        ok_all = ok_all and e2e_ok
        print(f"  e2e: kur -> arada igne+geri alis -> sonraki calistirma ATESLENDI raporlar: "
              f"{'OK' if e2e_ok else '!!! RAPORLANMADI'}")
        rE1 = render("PLE", snapE2, _wait("plan-testi"), cfg)
        rnd_ok = "ISLEM PLANI" in rE1 and ("PUSU" in rE1 or "BEKLE" in rE1)
        ok_all = ok_all and rnd_ok
        print(f"  render: ISLEM PLANI + acik PUSU/BEKLE hukmu basiliyor: "
              f"{'OK' if rnd_ok else '!!! EKSIK'}")
        # ateslenen plan AKTIF olarak yasamali (taze pusu ezemez), hedefe varinca
        # SONUC + OLCULEN KARNE satiri gelmeli (kullanicinin 'kanitla' talebi)
        hedE = next(p["hedef"] for p in kurulan if p["tip"] == "LONG-TEPKI")
        csE3 = csE2 + [Candle(open=csE2[-1].close, high=hedE * 1.002,
                              low=csE2[-1].close * 0.999, close=hedE * 0.999,
                              volume=1000.0, close_ms=tE + 2_700_000)]
        snapE3 = _synth_snapshot("PLE", csE3, cfg, trend=0.0)
        rapE2 = "\n".join(plan_takip("PLE", snapE3, cfg))
        aktif_ok = ("[SONUC]" in rapE2 and "HEDEF VURULDU" in rapE2
                    and "PUSU KARNESI" in rapE2)
        ok_all = ok_all and aktif_ok
        print(f"  aktif yasam: ateslenen plan sonraki kosuda cozulur + KARNE satiri: "
              f"{'OK' if aktif_ok else '!!! EKSIK'}")
        # 3-KOSU tasima: ayni seviyeli pusu yeniden kurulunca bar_ms KORUNMALI
        # (yoksa SURE-DOLDU olu kod olur: her kosu sayaci sifirlar)
        _pl_temps.append(_tmp.mktemp(suffix="_plan3.json"))
        os.environ["YON_PLAN_LOG"] = _pl_temps[-1]
        k1 = plan_kur("PL3", snapE1, stE, micE, cfg,
                      mc_ilk={"p_ust": 0.1, "p_alt": 0.6})
        bar1 = next(p["bar_ms"] for p in k1 if p["tip"] == "LONG-TEPKI")
        csT3 = csE + [Candle(open=csE[-1].close, high=csE[-1].close * 1.001,
                             low=csE[-1].close * 0.999, close=csE[-1].close,
                             volume=1000.0, close_ms=tE + 900_000)]
        snapT3 = _synth_snapshot("PL3", csT3, cfg, trend=0.0)
        stT3 = build_structure(csT3, cfg)
        k2 = plan_kur("PL3", snapT3, stT3, classify_micro(snapT3, stT3, cfg), cfg,
                      mc_ilk={"p_ust": 0.1, "p_alt": 0.6})
        bar2 = next(p["bar_ms"] for p in k2 if p["tip"] == "LONG-TEPKI")
        sv1 = next(p["seviye"] for p in k1 if p["tip"] == "LONG-TEPKI")
        sv2 = next(p["seviye"] for p in k2 if p["tip"] == "LONG-TEPKI")
        # HAYALET-TETIK regresyonu: tasima planin TAMAMINI korur (seviye dahil) —
        # seviye guncellenirse gecmis mumlar yeni seviyeyi retroaktif tetikleyebilirdi
        tasima_ok = (bar2 == bar1) and abs(sv2 - sv1) < 1e-12
        ok_all = ok_all and tasima_ok
        print(f"  plan tasima: ayni pusuda kurulus zamani VE seviye korunur: "
              f"{'OK' if tasima_ok else f'!!! sozlesme bozuldu (bar {bar1}->{bar2}, sv {sv1}->{sv2})'}")
        pfl = csT3[-1].close
        csT4 = csT3 + [Candle(open=pfl, high=pfl * 1.0005, low=pfl * 0.9995, close=pfl,
                              volume=1000.0, close_ms=tE + 900_000 * (2 + j))
                       for j in range(cfg.signal_horizon_bars + 2)]
        rap3 = "\n".join(plan_takip("PL3", _synth_snapshot("PL3", csT4, cfg, trend=0.0), cfg))
        sure_ok = "SURE DOLDU" in rap3
        ok_all = ok_all and sure_ok
        print(f"  {cfg.signal_horizon_bars}+ mum tetiksiz (tasima sonrasi) -> SURE DOLDU raporu: "
              f"{'OK' if sure_ok else '!!! GELMEDI'}")
        # DAR-BANT kapisi: havuzlar min_target_atr*ATR'den yakinsa pusu KURULMAZ
        # (SURE-DOLDU blogundan SONRA: kendi izole plan-store'unu acar)
        _pl_temps.append(_tmp.mktemp(suffix="_dar.json"))
        os.environ["YON_PLAN_LOG"] = _pl_temps[-1]
        micDB = [MicroScen(6, MICRO_ADLAR[6], "NEUTRAL", 0.5, "", "", "B",
                           stE.price + 0.2 * stE.atr),
                 MicroScen(7, MICRO_ADLAR[7], "NEUTRAL", 0.5, "", "", "B",
                           stE.price - 0.2 * stE.atr)]
        dar_k = plan_kur("DARB", snapE1, stE, micDB, cfg)
        genis_k = plan_kur("DARB2", snapE1, stE, [], cfg)
        # F2 (FABLE6_5): genis bantta artik TEK kenar kurulur; beklenen kenar deterministik
        # fallback kuralindan (fiyatin bant-ortasina gore konumu) hesaplanir.
        _ustD, _altD = _tetik_seviyeleri(snapE1, stE, [], cfg)[0:2]
        _bekD = ("SHORT-TEPKI" if csE[-1].close > (_ustD + _altD) / 2.0 else "LONG-TEPKI")
        dar_ok = (dar_k == []) and ([p["tip"] for p in genis_k] == [_bekD])
        ok_all = ok_all and dar_ok
        print(f"  dar-bant -> pusu KURULMAZ; genis bantta TEK kenar ({_bekD}): "
              f"{'OK' if dar_ok else '!!! HATA'}")
        # F2 tek-kenar MC-secimi: canli MC ilk-temas olasiligi kenari deterministik secer
        _pl_temps.append(_tmp.mktemp(suffix="_tek.json"))
        os.environ["YON_PLAN_LOG"] = _pl_temps[-1]
        _kU = plan_kur("TEKU", snapE1, stE, [], cfg, mc_ilk={"p_ust": 0.7, "p_alt": 0.1})
        _kA = plan_kur("TEKA", snapE1, stE, [], cfg, mc_ilk={"p_ust": 0.1, "p_alt": 0.7})
        tek_ok = ([p["tip"] for p in _kU] == ["SHORT-TEPKI"]
                  and [p["tip"] for p in _kA] == ["LONG-TEPKI"])
        ok_all = ok_all and tek_ok
        print(f"  F2 tek-kenar MC-secimi: p_ust>p_alt->SHORT / p_alt>p_ust->LONG: "
              f"{'OK' if tek_ok else '!!! HATA'}")
        # TREND-YONU FILTRESI (canli 06-07.07 olcumu: karsi-trend LONG-TEPKI 1/11 HEDEF):
        # guclu 1s ASAGI -> LONG-TEPKI kurulmaz; guclu YUKARI -> SHORT-TEPKI kurulmaz;
        # YATAY -> 2 plan (genis_k yukarida kanitladi). htf_inen REJIM-AILESI blogundan.
        _pl_temps.append(_tmp.mktemp(suffix="_tf.json"))
        os.environ["YON_PLAN_LOG"] = _pl_temps[-1]
        _htf_yukTF, _pTF = [], 100.0
        for _iTF in range(60):
            _oTF = _pTF
            _pTF *= 1.003
            _htf_yukTF.append(Candle(open=_oTF, high=_pTF * 1.0005, low=_oTF * 0.9995,
                                     close=_pTF, volume=1.0, close_ms=t0R + _iTF * 3_600_000))
        _k_dn = plan_kur("TFD", Snapshot(symbol="TFD", candles=csE, htf=htf_inen, stale=False),
                         stE, [], cfg)
        _k_up = plan_kur("TFU", Snapshot(symbol="TFU", candles=csE, htf=_htf_yukTF, stale=False),
                         stE, [], cfg)
        tf_ok = ([p["tip"] for p in _k_dn] == ["SHORT-TEPKI"]
                 and [p["tip"] for p in _k_up] == ["LONG-TEPKI"])
        ok_all = ok_all and tf_ok
        print(f"  trend-yonu filtresi: 4s ASAGI->{[p['tip'] for p in _k_dn]} / "
              f"1s YUKARI->{[p['tip'] for p in _k_up]}: "
              f"{'OK' if tf_ok else '!!! KARSI-TREND PUSU KURULDU'}")
    except Exception as e:
        ok_all = False
        print(f"  !!! KOSULLU-PLAN e2e HATASI: {str(e)[:90]}")
    finally:
        for _plt in _pl_temps:
            try:
                os.remove(_plt)
            except Exception:
                pass
        if _oldPL is None:
            os.environ.pop("YON_PLAN_LOG", None)
        else:
            os.environ["YON_PLAN_LOG"] = _oldPL

    # ── CPCV MEKANIGI: purge kurali + R-cozumu + PBO uc-durumlari + dsr_report kablosu ──
    # decide CAGIRMAZ (milisaniyelik): CSCV matematigi sentetik matrislerle mekanik test
    # edilir. Tam olcum ayri komuttur (python fable6.py cpcv ...) — selftest'i sismanlatmaz.
    print("\n" + "-" * 52)
    print("[CPCV] purge mekanigi + R-cozumu + PBO uc-durumlari + dsr kablosu:")
    _prgC = _cpcv_purge_rows(cfg)
    _TC, _SC = 160, 8
    trC, teC = _cscv_split_rows(_TC, _SC, (0, 2, 5, 7), _prgC)
    trC0, _ = _cscv_split_rows(_TC, _SC, (0, 2, 5, 7), 0)
    _yakin = [r for r in trC if any(abs(r - t) <= _prgC for t in teC)]
    purge_ok = (not _yakin) and (len(trC) < len(trC0)) and teC
    ok_all = ok_all and purge_ok
    print(f"  purge: egitim satiri test'e <= {_prgC} satir yaklasamaz -> ihlal={len(_yakin)}, "
          f"atilan={len(trC0) - len(trC)} satir  {'OK' if purge_ok else '!!! SIZINTI'}")
    # R-cozumu birim testleri (hedef=+RR / stop=-1 / sure-doldu=kirpilmis isaretli R)
    t0R = 1_700_000_000_000
    _mumR = lambda h, l, c, i: Candle(open=100.0, high=h, low=l, close=c,
                                      volume=1000.0, close_ms=t0R + i * 900_000)
    dR = _wait("cpcv-test")
    dR.karar, dR.entry, dR.target, dR.stop = "LONG", 100.0, 102.0, 99.0
    cs_h = [_mumR(100.5, 99.5, 100.0, 0), _mumR(102.3, 99.8, 102.0, 1)]
    cs_s = [_mumR(100.5, 99.5, 100.0, 0), _mumR(100.4, 98.8, 99.0, 1)]
    cs_z = [_mumR(100.5, 99.5, 100.0, 0)] + [_mumR(101.0, 99.6, 100.5, i) for i in (1, 2)]
    r_h = _cpcv_r_multiple(cs_h, 0, dR, 2)
    r_s = _cpcv_r_multiple(cs_s, 0, dR, 2)
    r_z = _cpcv_r_multiple(cs_z, 0, dR, 2)
    r_ok = (abs(r_h - 2.0) < 1e-9) and (abs(r_s + 1.0) < 1e-9) and (abs(r_z - 0.5) < 1e-9)
    ok_all = ok_all and r_ok
    print(f"  R-cozumu: hedef={r_h:+.1f} (beklenen +2.0) stop={r_s:+.1f} (-1.0) "
          f"sure-doldu={r_z:+.1f} (+0.5)  {'OK' if r_ok else '!!! HATA'}")
    # PBO uc-durumlari: gercek-kenar dusuk / gurultu ~0.5 / yari-donen yuksek olmali
    rngC = random.Random(101)
    _NC = 9
    M_iyi = [[(0.30 if v == 2 else 0.0) + rngC.gauss(0, 0.05) for v in range(_NC)]
             for _ in range(_TC)]
    M_gur = [[rngC.gauss(0, 0.10) for _ in range(_NC)] for _ in range(_TC)]
    M_don = [[(0.20 if (v % 2 == 0) == (t < _TC // 2) else -0.20) + rngC.gauss(0, 0.02)
              for v in range(_NC)] for t in range(_TC)]
    p_iyi = _cscv_pbo(M_iyi, _SC, _prgC)["pbo"]
    p_gur = _cscv_pbo(M_gur, _SC, _prgC)["pbo"]
    p_don = _cscv_pbo(M_don, _SC, _prgC)["pbo"]
    pbo_ok = (p_iyi is not None and p_iyi <= 0.2) and \
             (p_gur is not None and 0.2 <= p_gur <= 0.8) and \
             (p_don is not None and p_don >= 0.5)
    ok_all = ok_all and pbo_ok
    print(f"  PBO: gercek-kenar={p_iyi:.2f} (<=0.2) gurultu={p_gur:.2f} (0.2-0.8) "
          f"yari-donen={p_don:.2f} (>=0.5)  {'OK' if pbo_ok else '!!! YANLIS SINIFLAMA'}")
    # dsr_report kablosu: cache yokken AYNEN 'PBO=N/A'; kayit sonrasi olculen deger
    _oldCC = os.environ.get("YON_CPCV_CACHE")
    _oldLL = os.environ.get("YON_PANEL_LOG")
    os.environ["YON_CPCV_CACHE"] = _tmp.mktemp(suffix="_cpcv.json")
    os.environ["YON_PANEL_LOG"] = _tmp.mktemp(suffix="_dsr.jsonl")
    try:
        na_txt = dsr_report("CPX", cfg)
        _cpcv_cache_save("CPX", {"pbo": 0.31, "S": 8, "n_split_gecerli": 70,
                                 "n_sinyal": 45, "guvenilir": True, "mod": "tam",
                                 "ts": time.time(), "model_hash": model_hash(cfg),
                                 "feature_hash": feature_hash(),
                                 "protocol_id": cfg.protocol_id,
                                 "scope": "OAT-partial-diagnostic",
                                 "compat_hash": cpcv_compat_hash("tam", Config()),
                                 "code_hash": code_hash()})
        olc_txt = dsr_report("CPX", cfg)
        kablo_ok = ("PBO=N/A" in na_txt) and ("OAT-PBO-tani=0.31" in olc_txt) and \
                   ("DSR=N/A" in olc_txt)
        ok_all = ok_all and kablo_ok
        print(f"  dsr kablosu: DSR=N/A korunur + kayit sonrasi kismi 'OAT-PBO-tani=0.31' "
              f"gorunur  {'OK' if kablo_ok else '!!! KABLO KOPUK'}")
    finally:
        for _e in ("YON_CPCV_CACHE", "YON_PANEL_LOG"):
            try:
                os.remove(os.environ[_e])
            except Exception:
                pass
        os.environ.pop("YON_CPCV_CACHE", None)
        os.environ.pop("YON_PANEL_LOG", None)
        if _oldCC is not None:
            os.environ["YON_CPCV_CACHE"] = _oldCC
        if _oldLL is not None:
            os.environ["YON_PANEL_LOG"] = _oldLL

    # ── [YON9-EK] yeni katman regresyonlari: ensemble kapisi, spoof, slip, karsi-fitil,
    # settle uyarisi, L/S tilt, kalici-klasor. Kendi env izolasyonunu kurar (gercek dosya kirletmez).
    print("\n" + "-" * 52)
    print("[YON9-EK] ensemble kapisi + yeni veri katmanlari:")
    _y9_ok = True
    import tempfile as _tf9
    _y9_tmp = _tf9.mkdtemp(prefix="yon9ek_")
    _y9_es = {k: os.environ.get(k) for k in ("YON_PANEL_LOG", "YON_DISAGREE_LOG", "YON_PLAN_LOG")}
    os.environ["YON_PANEL_LOG"] = os.path.join(_y9_tmp, "s.jsonl")
    os.environ["YON_DISAGREE_LOG"] = os.path.join(_y9_tmp, "d.json")
    os.environ["YON_PLAN_LOG"] = os.path.join(_y9_tmp, "p.json")
    try:
        # (2) spoof_kontrol saf fonksiyon: %70 kayip yakalanir, %30 yakalanmaz
        _b1 = {"bid_qty": 100.0, "ask_qty": 80.0}
        _c2 = spoof_kontrol(_b1, {"bid_qty": 30.0, "ask_qty": 80.0}, 0.5)[0] == "ALIS" and \
            spoof_kontrol(_b1, {"bid_qty": 70.0, "ask_qty": 80.0}, 0.5)[0] is None and \
            spoof_kontrol(None, _b1, 0.5)[0] is None
        print(f"  spoof kontrolu (%70 yakalar / %30 birakir / None sessiz): {'OK' if _c2 else 'KALDI'}")
        # (3) derinlikten slippage: ince defter > kalin defter; seviye yoksa None; maliyet tabani
        _ince = slip_olcum_frac({"asks": [(100.0, 0.1), (101.0, 99.0)], "bids": []}, 5000.0, "BUY")
        _kalin = slip_olcum_frac({"asks": [(100.0, 999.0)], "bids": []}, 5000.0, "BUY")
        _c3 = (_ince is not None and _kalin is not None and _ince > _kalin
               and slip_olcum_frac({"asks": [], "bids": []}, 5000.0, "BUY") is None
               and txn_cost_abs("BTCUSDT", 100.0, cfg,
                                book={"asks": [(100.0, 0.1), (101.0, 99.0)],
                                      "bids": [(99.9, 0.1), (99.0, 99.0)]})
               >= txn_cost_abs("BTCUSDT", 100.0, cfg) - 1e-12)
        print(f"  slippage olcumu (ince>{_ince and round(_ince,4)} kalin>{_kalin and round(_kalin,4)}; "
              f"maliyet tabani korunur): {'OK' if _c3 else 'KALDI'}")
        # (4) UC-SINIF ENSEMBLE KAPISI: secilen yonden daha olasi ters sinif frenler.
        _cs9 = _synthetic_candles(499, 3, +0.0015, 0.008)
        _sn9 = _synth_snapshot("Y9EK", _cs9, cfg, 0.0015)
        _c4 = (ensemble_side_conflict("LONG", (0.70, 0.10, 0.20), 3.0, cfg)
               and ensemble_side_conflict("SHORT", (0.20, 0.10, 0.70), 3.0, cfg)
               and not ensemble_side_conflict("LONG", (0.20, 0.10, 0.70), 3.0, cfg))
        print(f"  uc-sinif ensemble karsi-yon freni (LONG/SHORT ayna): {'OK' if _c4 else 'KALDI'}")
        # (5) KARSI-FITIL temkini: LONG sahnesinin son mumuna 1.2 ATR ust fitil enjekte ->
        # LONG kalirsa uyari tasimali (sozlesme: frensiz gecmez)
        import copy as _cp9
        _cs9b = _cp9.deepcopy(_cs9)
        _a9 = atr_series(_cs9b, cfg.atr_period)[-1]
        _cs9b[-1].high = max(_cs9b[-1].open, _cs9b[-1].close) + 1.2 * _a9
        _sn9b = _synth_snapshot("Y9EKW", _cs9b, cfg, 0.0015)
        _d2 = decide(_sn9b, cfg)
        _c5 = (_d2.karar != "LONG") or ("KARSI-FITIL" in (_d2.warn or ""))
        print(f"  karsi-fitil temkini (karar={_d2.karar}; LONG ise uyari sart): {'OK' if _c5 else 'KALDI'}")
        # (6) settle uyarisi: settle'a 10 dk kala sinyal uyari tasir
        _sn9.premium = {"mark": 0.0, "index": 0.0, "last_funding": 0.0002,
                        "next_funding_ms": 1_700_000_600_000, "server_ms": 1_700_000_000_000}
        _d3 = decide(_sn9, cfg)
        _c6 = (_d3.karar == "BEKLE") or ("FUNDING SETTLE" in (_d3.warn or ""))
        print(f"  settle sayaci uyarisi (karar={_d3.karar}): {'OK' if _c6 else 'KALDI'}")
        # (7) L/S tilt yalniz makro blokaj katmaninda ve yonu asagi ceker
        _sn9.ls_top = 1.40
        _pl = macro_leading_estimate(_sn9, cfg)
        _sn9.ls_top = None
        _p0 = macro_leading_estimate(_sn9, cfg)
        _c7 = _pl.p_up <= _p0.p_up and "kalabalik" in _pl.note
        print(f"  top-trader L/S kontra tilt (p {_p0.p_up:.3f}->{_pl.p_up:.3f}): {'OK' if _c7 else 'KALDI'}")
        # (8) kalici klasor: env yokken yol MUTLAK ve cwd'den bagimsiz
        _oldp = os.environ.pop("YON_PANEL_LOG")
        _yol9 = _log_path()
        os.environ["YON_PANEL_LOG"] = _oldp
        _c8 = os.path.isabs(_yol9)
        print(f"  kalici klasor (env yok -> mutlak yol {_yol9[:40]}...): {'OK' if _c8 else 'KALDI'}")
        ok_all = ok_all and all((_c2, _c3, _c4, _c5, _c6, _c7, _c8))
    finally:
        for _k9, _v9 in _y9_es.items():
            if _v9 is None:
                os.environ.pop(_k9, None)
            else:
                os.environ[_k9] = _v9
        try:
            import shutil as _sh9
            _sh9.rmtree(_y9_tmp, ignore_errors=True)
        except Exception:
            pass

    # ── [ONCU-TAHMIN] kosulsuz yon+bant tahmini ve OLCULEN sicil mekanigi ──
    print("\n" + "-" * 52)
    print("[ONCU-TAHMIN] kosulsuz tahmin + sicil cozumu:")
    import tempfile as _tf10
    _t10 = _tf10.mkdtemp(prefix="yon9fc_")
    _es10 = os.environ.get("YON_FORECAST_LOG")
    os.environ["YON_FORECAST_LOG"] = os.path.join(_t10, "f.jsonl")
    try:
        # (1) decide her kosuda fc uretir (BEKLE dahil): holder dolu + q10<=q50<=q90
        _cs10 = _synthetic_candles(499, 5, 0.0, 0.010)
        _sn10 = _synth_snapshot("FC10", _cs10, cfg)
        # LIVE fail-closed saat sozlesmesi: sentetik fixture gercek tahmin anini acik verir.
        _sn10.predicted_at_ms = _cs10[-1].close_ms
        _sn10.live_fetched_ms = _cs10[-1].close_ms
        _sn10.live_server_ms = _cs10[-1].close_ms
        _sn10.last_closed_ms = _cs10[-1].close_ms
        _sn10.data_watermark_ms = _cs10[-1].close_ms
        _d10 = decide(_sn10, cfg,
                      context=DecisionContext(predicted_at_ms=_cs10[-1].close_ms))
        _f10 = _FC_HOLDER.get("v")
        _k1 = (_f10 is not None and _f10["q10"] <= _f10["q50"] <= _f10["q90"]
               and _f10["dir"] in (-1, 0, 1) and _f10["price0"] > 0)
        print(f"  fc uretimi (karar={_d10.karar}; q10<=q50<=q90, dir gecerli): {'OK' if _k1 else 'KALDI'}")
        # (2) cozum mekanigi: dir=+1 tahmin, 4 mum sonra fiyat ustte -> HIT + bant ICINDE
        _t0 = 1_700_000_000_000
        _sp = 900_000
        _mumlar = [Candle(open=100, high=106, low=99, close=(105 if i >= 4 else 101),
                          volume=1.0, close_ms=_t0 + (i + 1) * _sp) for i in range(8)]
        _snF = Snapshot(symbol="FCTEST", candles=_mumlar, htf=[], stale=False)
        _dF = _wait("test")
        _dF.fc = None
        with open(os.environ["YON_FORECAST_LOG"], "w", encoding="utf-8") as _fh:
            for _dir, _sym in ((1, "FCTEST"), (-1, "FCTEST2")):
                _fh.write(json.dumps({"symbol": _sym, "bar_ms": _t0 + _sp, "dir": _dir,
                                      "pup": 0.6, "q10": 98.0, "q50": 103.0, "q90": 106.0,
                                      "price0": 100.0, "h": 4}) + "\n")
        _r1 = forecast_kaydet_ve_coz("FCTEST", _snF, _dF, cfg)
        _snF2 = Snapshot(symbol="FCTEST2", candles=_mumlar, htf=[], stale=False)
        _r2 = forecast_kaydet_ve_coz("FCTEST2", _snF2, _dF, cfg)
        def _legacy_test_karne(sym):
            _rr = [r for r in _fc_yukle() if r.get("symbol") == sym]
            _yy = [r for r in _rr if r.get("outcome") in ("HIT", "MISS")]
            _bb = [r for r in _rr if r.get("outcome") in ("HIT", "MISS", "NOTR")
                   and r.get("bant_ici") is not None]
            return (len(_yy), sum(r.get("outcome") == "HIT" for r in _yy),
                    sum(bool(r.get("bant_ici")) for r in _bb), len(_bb))
        _kar1 = _legacy_test_karne("FCTEST")
        _kar2 = _legacy_test_karne("FCTEST2")
        _k2 = (any("HIT" in s for s in _r1) and any("bant ICINDE" in s for s in _r1)
               and _kar1 == (1, 1, 1, 1) and any("MISS" in s for s in _r2)
               and _kar2[0] == 1 and _kar2[1] == 0)
        print(f"  cozum: dogru yon HIT+bant ({_kar1}), ters yon MISS ({_kar2}): {'OK' if _k2 else 'KALDI'}")
        # (3) EXPIRED: pencereden dusen tahmin karneye SAYILMAZ
        with open(os.environ["YON_FORECAST_LOG"], "a", encoding="utf-8") as _fh:
            _fh.write(json.dumps({"symbol": "FCTEST", "bar_ms": _t0 - 100 * _sp, "dir": 1,
                                  "pup": 0.6, "q10": 98.0, "q50": 103.0, "q90": 106.0,
                                  "price0": 100.0, "h": 4}) + "\n")
        forecast_kaydet_ve_coz("FCTEST", _snF, _dF, cfg)
        _k3 = _legacy_test_karne("FCTEST") == (1, 1, 1, 1) and any(
            r.get("outcome") == "EXPIRED" for r in _fc_yukle() if r["bar_ms"] == _t0 - 100 * _sp)
        print(f"  pencere-disi tahmin EXPIRED, karne degismedi: {'OK' if _k3 else 'KALDI'}")
        # (4) yeni tahmin kaydi + ayni bar'a cift kayit yok
        _dF.fc = {"dir": 1, "pup": 0.55, "q10": 99.0, "q50": 102.0, "q90": 104.0,
                  "price0": 101.0, "atr": 1.0, "h": 4, "celiski": 0}
        forecast_kaydet_ve_coz("FCTEST", _snF, _dF, cfg)
        forecast_kaydet_ve_coz("FCTEST", _snF, _dF, cfg)
        _n_yeni = sum(1 for r in _fc_yukle()
                      if r["symbol"] == "FCTEST" and r["bar_ms"] == _mumlar[-1].close_ms)
        _k4 = _n_yeni == 1
        print(f"  yeni tahmin tek kayit (cift kosuda duplicate yok, n={_n_yeni}): {'OK' if _k4 else 'KALDI'}")
        # (5) render blogu tahmini basar
        _d10.fc = _f10
        _d10.fc_rapor = ["[TAHMIN-COZUM] ornek"]
        _txt10 = render("FC10", _sn10, _d10, cfg)
        _k5 = "ONCU TAHMIN" in _txt10 and "YON TAHMINI:" in _txt10 and "BEKLENEN BANT" in _txt10
        print(f"  render 'ONCU TAHMIN' blogu (yon+bant satirlari): {'OK' if _k5 else 'KALDI'}")
        ok_all = ok_all and all((_k1, _k2, _k3, _k4, _k5))
    finally:
        if _es10 is None:
            os.environ.pop("YON_FORECAST_LOG", None)
        else:
            os.environ["YON_FORECAST_LOG"] = _es10
        try:
            import shutil as _sh10
            _sh10.rmtree(_t10, ignore_errors=True)
        except Exception:
            pass

    # ── [ISLEM-PLANI/CANLI-ONLY] net plan cikiyor mu + gecmis kalibrasyon karardan cikti mi? ──
    print("\n" + "-" * 52)
    print("[ISLEM-PLANI/CANLI-ONLY] net plan + canli MC ilk-temas + kalibrasyon karara girmez:")
    import tempfile as _tfIP
    from dataclasses import replace as _rep_ip
    # (1) NET PLAN varsayilan (HUKUM) modda gorunur: MARKET GIR veya LONG-gir/SHORT-gir seviyeleri
    csIP = _synthetic_candles(cfg.kline_limit, 11, 0.004, 0.012)
    snapIP = _synth_snapshot("IPBTC", csIP, cfg, 0.004)
    dIP = decide(snapIP, cfg)
    dIP.plan = _PLAN_HOLDER.get("v")
    dIP.fc = _FC_HOLDER.get("v")
    os.environ.pop("YON_DETAY", None)                       # HUKUM (varsayilan) mod
    txtIP = render("IPBTC", snapIP, dIP, cfg)
    # UPTREND sahnesinde 1s trend GUCLU YUKARI ise trend-yonu filtresi SHORT-TEPKI
    # pususunu kurmaz -> ekranda 'SHORT kenari ... PUSU KURULMADI' beklenir; trend
    # zayif/yataysa iki kenar da 'gir' satiri olmali. Kosul olculur ve dogru dal asserte edilir.
    _td_ip9, _ts_ip9 = htf_trend(snapIP.htf, cfg)
    if _ts_ip9 and _td_ip9 > 0:
        ip_ok = ("ISLEM PLANI" in txtIP and "LONG-gir" in txtIP
                 and "PUSU KURULMADI" in txtIP and "SHORT-gir" not in txtIP
                 and ("MARKET GIR" in txtIP or "ilk-temas" in txtIP))
        _ip_msg = "LONG-gir + SHORT kenari KURULMADI (trend filtresi)"
    else:
        ip_ok = ("ISLEM PLANI" in txtIP and "LONG-gir" in txtIP and "SHORT-gir" in txtIP
                 and ("MARKET GIR" in txtIP or "ilk-temas" in txtIP))
        _ip_msg = "LONG-gir/SHORT-gir"
    ok_all = ok_all and ip_ok
    print(f"  net plan varsayilan modda (ISLEM PLANI + {_ip_msg}): {'OK' if ip_ok else '!!! EKSIK'}")
    # (2) CANLI MC ILK-TEMAS: olasilik toplami ~1 ve p_dolu (holder BEKLE'de de dolu)
    stIP = build_structure(csIP, cfg)
    pathsIP, _ = mc_simulate(csIP, stIP, 0.0, cfg, random.Random(7), paths_n=800)
    _pu, _pd, _pn = mc_ilk_temas(pathsIP, stIP.price, stIP.range_high, stIP.range_low)
    it_ok = abs((_pu + _pd + _pn) - 1.0) < 1e-9 and 0.0 <= _pu <= 1.0 and 0.0 <= _pd <= 1.0
    ok_all = ok_all and it_ok
    print(f"  mc_ilk_temas toplam=1 (ust %{_pu*100:.0f} / alt %{_pd*100:.0f} / yok %{_pn*100:.0f}): "
          f"{'OK' if it_ok else '!!! HATA'}")
    # (2b) SEVIYE-TUTARLILIGI: BEKLE planinda BASILAN % tam BASILAN seviyenin MC'si olmali.
    # (Kusur-A regresyonu: havuz seviyesi bant ucundan farkliyken bant-ucu olasiligi basiliyordu
    #  -> yazilan sayi yazilan seviyeye ait degildi. Olculdu: ayni sahnede %0/32 vs gercek %33/53.)
    d_bk = _wait("plan-testi")
    d_bk.plan = {"p_ust": 0.0, "p_alt": 0.0, "p_yok": 1.0, "price0": stIP.price,
                 "atr": stIP.atr, "h": cfg.horizon, "paths": pathsIP}
    _mic2 = [MicroScen(6, MICRO_ADLAR[6], "NEUTRAL", 0.5, "", "", "B",
                       stIP.price + 1.5 * stIP.atr),
             MicroScen(7, MICRO_ADLAR[7], "NEUTRAL", 0.5, "", "", "B",
                       stIP.price - 1.5 * stIP.atr)]
    # sembol 'IPBK': store'da kaydi YOK -> taze-hesap yedegi test edilir (render yukarida
    # IPBTC icin plan_kur'la sozlesme yazdi; ayni sembol kullanilsa sozlesme basilirdi)
    _Lbk = islem_plani("IPBK", snapIP, stIP, d_bk, _mic2, cfg)
    _u3, _a3, _ = mc_ilk_temas(pathsIP, stIP.price,
                               stIP.price + 1.5 * stIP.atr, stIP.price - 1.5 * stIP.atr)
    _beklenen_sv = f"once %{int(round(_u3 * 100))} UST / %{int(round(_a3 * 100))} ALT"
    sv_ok = any(_beklenen_sv in ln for ln in _Lbk)
    ok_all = ok_all and sv_ok
    print(f"  seviye-tutarliligi (basilan % = basilan seviyenin MC'si): "
          f"{'OK' if sv_ok else '!!! CELISKI (bant-ucu sayisi basildi)'}")
    # (2c) F1-SOZLESME + (2d) F2-AKTIF-KENAR (canli 06.07 14:14 bulgulari):
    # F1: store pusu sozlesmesi taze hesaptan farkliysa EKRAN SOZLESMEYI basmali
    #     (canli SOL: ekran stop 81.1667 basti, makine 81.1995 sozlesmesini olcuyordu).
    # F2: kenarda ATESLENMIS AKTIF plan varken ayni kenara yeni limit ONERILMEZ
    #     (canli DOGE SHORT: cift maruziyet riski).
    _oldPL_ip = os.environ.get("YON_PLAN_LOG")
    os.environ["YON_PLAN_LOG"] = _tfIP.mktemp(suffix="_ipf.json")
    try:
        _sozl = {"tip": "SHORT-TEPKI", "seviye": stIP.range_high,
                 "stop": stIP.range_high + 9.99, "hedef": stIP.price,
                 "bar_ms": 1_700_000_000_000}
        _aktf = {"tip": "LONG-TEPKI", "seviye": stIP.range_low,
                 "stop": stIP.range_low - 1.0, "hedef": stIP.price,
                 "entry": stIP.range_low + 0.5, "fire_ms": 1_700_000_900_000}
        with open(os.environ["YON_PLAN_LOG"], "w", encoding="utf-8") as _fip:
            json.dump({"IPBTC": {"pusu": [_sozl], "aktif": [_aktf], "hist": []}}, _fip)
        _Lf = islem_plani("IPBTC", snapIP, stIP, d_bk, [], cfg)
        _mf = "\n".join(_Lf)
        f1_ok = (_fmt(stIP.range_high + 9.99) in _mf) and ("sozlesme" in _mf)
        f2_ok = ("YENI LIMIT KOYMA" in _mf) and ("LONG-gir" not in _mf)
        ok_all = ok_all and f1_ok and f2_ok
        print(f"  F1 sozlesme-esasli ekran (store stopu basildi): "
              f"{'OK' if f1_ok else '!!! TAZE HESAP BASILDI'}")
        print(f"  F2 aktif kenara yeni limit onerilmez: "
              f"{'OK' if f2_ok else '!!! CIFT MARUZIYET'}")
    finally:
        try:
            os.remove(os.environ["YON_PLAN_LOG"])
        except Exception:
            pass
        if _oldPL_ip is None:
            os.environ.pop("YON_PLAN_LOG", None)
        else:
            os.environ["YON_PLAN_LOG"] = _oldPL_ip
    # (3) CANLI-ONLY gecmis kalibrasyonu KARARDAN CIKARIR: 25 STOP kaydi ev esigini
    #     kalibre-modda YUKSELTIR (gecmis eser), canli-modda ESIK SABIT kalir (gecmis eremez).
    _oldIP = os.environ.get("YON_PANEL_LOG")
    os.environ["YON_PANEL_LOG"] = _tfIP.mktemp(suffix="_ip.jsonl")
    try:
        _rowsIP = [{"symbol": "IPX", "bar_ms": i, "side": "LONG", "entry": 100.0,
                    "target": 102.0, "inval": 99.0, "outcome": "STOP",
                    "p_target": 0.3, "edge": 0.1} for i in range(25)]
        _save_signals(_rowsIP, cfg)
        cfg_live = Config()                                # canli_only True (varsayilan)
        cfg_cal = _rep_ip(cfg_live, canli_only=False)      # eski kalibre davranis
        ev_live = ev_gate_calib("IPX", snapIP, stIP, cfg_live)[0]
        ev_cal = ev_gate_calib("IPX", snapIP, stIP, cfg_cal)[0]
        cal_ok = (abs(ev_live - cfg_live.ev_min_atr) < 1e-12) and (ev_cal > cfg_cal.ev_min_atr + 1e-6)
        # reversal_calib de canli-modda SABIT flip esigi dondurmeli
        rev_live = reversal_calib("IPX", cfg_live)[0]
        rev_ok = abs(rev_live - cfg_live.flip_thresh) < 1e-12
        ok_all = ok_all and cal_ok and rev_ok
        print(f"  ev esigi: CANLI={ev_live:.3f} (=varsayilan {cfg_live.ev_min_atr}) vs "
              f"KALIBRE={ev_cal:.3f} (gecmis STOP'lariyla yukseldi): "
              f"{'OK (gecmis karara girmiyor)' if cal_ok else '!!! GECMIS HALA KARARDA'}")
        print(f"  reversal_calib CANLI sabit flip esigi: {'OK' if rev_ok else '!!! HATA'}")
    finally:
        try:
            os.remove(os.environ["YON_PANEL_LOG"])
        except Exception:
            pass
        if _oldIP is None:
            os.environ.pop("YON_PANEL_LOG", None)
        else:
            os.environ["YON_PANEL_LOG"] = _oldIP
    # (2f) SADE OZET karti: teknik-dil-siz kosu-sonu karti uretiliyor mu + holder dolu mu?
    # Kart YENI SAYI uretmez (ayni d/store) -> yalniz varlik/yapi asserte edilir.
    _kartF = sade_ozet_karti("IPBTC", snapIP, stIP, dIP, cfg)
    _kmF = "\n".join(_kartF)
    kart_ok = ("TREND" in _kmF and "SENARYO" in _kmF and "NE YAPMALI" in _kmF
               and (("GIRILEBILIR" in _kmF) if dIP.karar in ("LONG", "SHORT")
                    else ("GIRIS YOK" in _kmF)))
    kart2_ok = bool(_SADE_HOLDER.get("IPBTC"))     # render() holder'i doldurdu mu
    ok_all = ok_all and kart_ok and kart2_ok
    print(f"  SADE OZET karti (TREND/SENARYO/NE YAPMALI + karar tutarli): "
          f"{'OK' if kart_ok else '!!! EKSIK'}")
    print(f"  SADE OZET render-holder (run sonu basimi icin dolu): "
          f"{'OK' if kart2_ok else '!!! BOS'}")

    # ── NIHAI RAPOR regresyonu (kullanici nihai_uygulama_sirasi B10+B18): 9 zorunlu
    # bolum + kesin NET SONUC cumlesi + karar tutarliligi. Kart yeni sayi uretmez.
    print("\n" + "-" * 52)
    print("[NIHAI-RAPOR] zorunlu 9-bolum format + kesin NET SONUC cumlesi:")
    _nrF = nihai_rapor_karti("IPBTC", snapIP, stIP, dIP, cfg)
    _nmF = "\n".join(_nrF)
    _nr_basliklar = ["1. ONCEKI PLAN DURUMU", "2. ANLIK MARKET EMIR KARARI",
                     "3. LIMIT PUSU PLANI", "4. KULLANILAN VERILER",
                     "5. DISLANAN / SUSTURULAN VERILER", "6. SENARYO-AJAN KARARI",
                     "7. KANIT / HESAP", "8. GECERSIZLESME VE RISK", "9. NET SONUC"]
    nr_ok = all(b in _nmF for b in _nr_basliklar)
    if dIP.karar == "LONG":
        nr_cumle = "Market emirle long uygundur." in _nmF
    elif dIP.karar == "SHORT":
        nr_cumle = "Market emirle short uygundur." in _nmF
    else:
        nr_cumle = "Market emir uygun değildir; limit pusu planı aşağıdadır." in _nmF
    nr_hold = bool(_NIHAI_HOLDER.get("IPBTC"))     # render() holder'i doldurdu mu
    ok_all = ok_all and nr_ok and nr_cumle and nr_hold
    print(f"  9 zorunlu bolum basligi tam: {'OK' if nr_ok else '!!! EKSIK'}")
    print(f"  kesin NET SONUC cumlesi karar ({dIP.karar}) ile tutarli: "
          f"{'OK' if nr_cumle else '!!! YOK/TUTARSIZ'}")
    print(f"  NIHAI RAPOR render-holder (run sonu basimi icin dolu): "
          f"{'OK' if nr_hold else '!!! BOS'}")

    # ── KARAR TABLOSU regresyonu (kullanici onayi: Varyant B, sembol-alti kart) ──
    print("\n" + "-" * 52)
    print("[KARAR-TABLOSU] sembol-alti Varyant-B kart + karar tutarliligi:")
    _ktF = karar_tablosu_karti("IPBTC", snapIP, stIP, dIP, cfg)
    _kmT = "\n".join(_ktF)
    kt_alan = all(a in _kmT for a in ("KARAR TABLOSU", "TREND:", "SENARYO :",
                                      "MARKET  :", "PUSU AL :", "PUSU SAT:"))
    if dIP.karar in ("LONG", "SHORT"):
        kt_karar = f"MARKET  : {dIP.karar}" in _kmT and _fmt(dIP.entry) in _kmT
    else:
        kt_karar = "MARKET  : YOK" in _kmT
    kt_rend = "KARAR TABLOSU" in txtIP          # render() sembol blogunun icinde basiyor mu
    ok_all = ok_all and kt_alan and kt_karar and kt_rend
    print(f"  alanlar tam (TREND/SENARYO/MARKET/PUSU-AL/PUSU-SAT): "
          f"{'OK' if kt_alan else '!!! EKSIK'}")
    print(f"  MARKET satiri karar ({dIP.karar}) ile birebir: {'OK' if kt_karar else '!!! TUTARSIZ'}")
    print(f"  render() ciktisinda sembol-alti kart var: {'OK' if kt_rend else '!!! YOK'}")

    # ── PERTURBATION KARARLILIK TESTI (arastirma: iyi parametre PLATO'da, tepe'de degil) ──
    # Anahtar TUNED sabitleri +/-%20 oynat; karar cok degisiyorsa o sabit kirilgan 'sweet-spot'.
    print("\n" + "-" * 52)
    print("[PERTURBATION] anahtar sabitler +/-%20 -> sinyal kararliligi (dusuk=saglam):")
    scenes = []
    for name, trend, vol in [("UPTREND", 0.004, 0.012), ("DOWNTREND", -0.004, 0.012),
                             ("CHOP", 0.0, 0.010), ("VOLATILE", 0.001, 0.03)]:
        cs = _synthetic_candles(cfg.kline_limit, _SAHNE_SEED[name], trend, vol)
        scenes.append(_synth_snapshot(name, cs, cfg, trend))
    base = [decide(sp, cfg, context=DecisionContext.offline(sp.candles[-1].close_ms)).karar
            for sp in scenes]
    from dataclasses import replace as _dc_replace
    total_flip = 0.0
    trials = 0
    for cname in ("barrier_atr", "mc_magnet_k", "ev_min_atr", "reversal_flag"):
        cflip = 0.0
        for mult in (0.8, 1.2):
            cfg2 = _dc_replace(cfg, **{cname: getattr(cfg, cname) * mult})
            out = [decide(sp, cfg2, context=DecisionContext.offline(sp.candles[-1].close_ms)).karar
                   for sp in scenes]
            frac = sum(1 for a, b in zip(base, out) if a != b) / max(1, len(base))
            cflip += frac
            total_flip += frac
            trials += 1
        print(f"  {cname:14s} +/-%20 -> sinyal degisim ~%{cflip / 2 * 100:.0f}"
              f"{'  [KIRILGAN]' if cflip / 2 > 0.15 else '  [plato]'}")
    instab = total_flip / max(1, trials)
    print(f"  GENEL kararsizlik (instability) = %{instab * 100:.0f}"
          f"  {'-> KIRILGAN (>%15)' if instab > 0.15 else '-> saglam (<=%15)'}")
    try:
        os.remove(os.environ["YON_PLAN_LOG"])
    except Exception:
        pass
    if _eski_plan_env is None:
        os.environ.pop("YON_PLAN_LOG", None)
    else:
        os.environ["YON_PLAN_LOG"] = _eski_plan_env

    # ── [GIRIS-ZAMANLAMA] (S2): market->SIMDI, BEKLE+pusu->PUSU-bekle, kenar yok->islem yok ──
    print("\n" + "-" * 52)
    print("[GIRIS-ZAMANLAMA] SIMDI-market vs PUSU-bekle ayrimi + render'da basiliyor mu:")
    _csGZ = _synthetic_candles(cfg.kline_limit, 11, 0.004, 0.012)
    _snGZ = _synth_snapshot("GZ", _csGZ, cfg, 0.004)
    _stGZ = build_structure(_csGZ, cfg)
    _dm_gz = Decision("LONG", 60, 100.0, 105.0, 98.0, 2.0, 0.6, 20, False, "t", [], 0, [],
                      0.0, "NORMAL", 0.2, "", 0.2, -0.1, {})
    _s_market = giris_zamanlama("GZ", _snGZ, _stGZ, _dm_gz, cfg)
    _d_bekle = _wait("t"); _d_bekle.scen_side = "SHORT"
    _s_pusu = giris_zamanlama("GZ", _snGZ, _stGZ, _d_bekle, cfg)
    _s_yok = giris_zamanlama("GZ", _snGZ, _stGZ, _wait("t"), cfg)
    gz_ok = ("SIMDI MARKET LONG" in _s_market and "PUSU bekle (SHORT" in _s_pusu
             and "kor market YOK" in _s_pusu and "islem yok" in _s_yok)
    # nihai + sade + panel'de basiliyor mu (market karari)
    _nr_gz = "\n".join(nihai_rapor_karti("GZ", _snGZ, _stGZ, _dm_gz, cfg))
    _sd_gz = "\n".join(sade_ozet_karti("GZ", _snGZ, _stGZ, _dm_gz, cfg))
    _pn_gz = "\n".join(panel_karti("GZ", _snGZ, _stGZ, _dm_gz, cfg))
    gz_render_ok = ("GIRIS ZAMANLAMASI" in _nr_gz and "ZAMANLAMA" in _sd_gz
                    and "ZAMANLAMA" in _pn_gz)
    ok_all = ok_all and gz_ok and gz_render_ok
    print(f"  market->SIMDI / BEKLE+scen->PUSU / kenar-yok->islem-yok: {'OK' if gz_ok else '!!! HATA'}")
    print(f"  nihai+sade+panel'de basiliyor: {'OK' if gz_render_ok else '!!! EKSIK'}")

    # ── [ERKEN-UYARI] (S3): ayri katman fire/sinif/determinizm/resolver + env-izole store ──
    print("\n" + "-" * 52)
    print("[ERKEN-UYARI] ayri uyari katmani (kanitlanmamis; karar kapisi degil):")
    # (a) squeeze/trend fixture default (min_kanit=2) FIRE etmeli
    _csEU = _squeeze_candles(cfg.kline_limit, 5, yon="YUKARI")
    _snEU = _synth_snapshot("EU", _csEU, cfg, 0.0); _stEU = build_structure(_csEU, cfg)
    _scEU = classify_scenario(_snEU, _stEU, cfg)
    _euA = erken_uyari("EU", _snEU, _stEU, _scEU, cfg)
    eu_fire = _euA.risk_var and len(_euA.kanitlar) >= cfg.erken_uyari_min_kanit
    # (b) min_kanit=1 ile temiz sinif: VDIP->V-DONUS/LONG (korunur); ONCU degisikligi:
    #     gecikmeli DUMP erken-uyari YON katmanindan CIKARILDI -> tur artik "DUMP" URETMEZ.
    _cfg1 = replace(cfg, erken_uyari_min_kanit=1)
    _csVD = _vdip_candles(cfg.kline_limit, 7); _snVD = _synth_snapshot("VD", _csVD, _cfg1, -0.004)
    _euVD = erken_uyari("VD", _snVD, build_structure(_csVD, _cfg1),
                        classify_scenario(_snVD, build_structure(_csVD, _cfg1), _cfg1), _cfg1)
    import random as _rndEU
    _rEU = _rndEU.Random(3); _csDM = []; _pDM = 100.0; _t0DM = 1_700_000_000_000
    for _i in range(cfg.kline_limit):
        _rr = (-0.05 if _i == cfg.kline_limit - 1 else _rEU.gauss(0, 0.006))
        _o = _pDM; _pDM = max(0.01, _pDM * (1 + _rr))
        _v = (8000.0 if _i == cfg.kline_limit - 1 else abs(_rEU.gauss(1000, 200)))
        _csDM.append(Candle(open=_o, high=max(_o, _pDM) * 1.001, low=min(_o, _pDM) * 0.999,
                            close=_pDM, volume=_v, close_ms=_t0DM + _i * 900_000))
    _snDM = _synth_snapshot("DM", _csDM, _cfg1, -0.01)
    _euDM = erken_uyari("DM", _snDM, build_structure(_csDM, _cfg1),
                        classify_scenario(_snDM, build_structure(_csDM, _cfg1), _cfg1), _cfg1)
    eu_sinif = (_euVD.risk_var and _euVD.tur == "V-DONUS" and _euVD.yon_egilim == "LONG"
                and _euDM.tur != "DUMP")   # ONCU: pump/dump erken-uyari YON oyu kaldirildi
    # (c) determinizm
    _euB = erken_uyari("EU", _snEU, _stEU, _scEU, cfg)
    eu_det = (_euA.risk_var, _euA.tur, _euA.yon_egilim) == (_euB.risk_var, _euB.tur, _euB.yon_egilim)
    # (d) resolver HIT/MISS/NOTR + env-izole store + karne
    import tempfile as _tmpEU
    _oldEU = os.environ.get("YON_ERKEN_UYARI_LOG")
    _euTmp = _tmpEU.mktemp(suffix="_eu.jsonl"); os.environ["YON_ERKEN_UYARI_LOG"] = _euTmp
    try:
        globals()["_ERKEN_READ_FAIL"] = False
        _t0 = 1_700_000_000_000; _sp = 900_000
        _mumEU = [Candle(open=100, high=104, low=99, close=(103.5 if i >= 1 else 101),
                         volume=1.0, close_ms=_t0 + (i + 1) * _sp) for i in range(4)]
        _snR = Snapshot(symbol="RSV", candles=_mumEU, htf=[], stale=False)
        _dR = _wait("t"); _dR.erken = {"risk_var": False}
        with open(_euTmp, "w", encoding="utf-8") as _f:
            for _sym, _yon, _thr in (("RSV", "LONG", 1.0), ("RSV2", "SHORT", 1.0), ("RSV3", "LONG", 99.0)):
                _f.write(json.dumps({"symbol": _sym, "bar_ms": _t0 + _sp, "tur": "PUMP", "yon": _yon,
                                     "guc": 0.66, "price0": 100.0, "atr": 1.0, "h": 2,
                                     "move_thr": _thr}) + "\n")
        _snR2 = Snapshot(symbol="RSV2", candles=_mumEU, htf=[], stale=False)
        _snR3 = Snapshot(symbol="RSV3", candles=_mumEU, htf=[], stale=False)
        erken_uyari_kaydet_ve_coz("RSV", _snR, _dR, cfg)      # LONG, fiyat yukari -> HIT
        erken_uyari_kaydet_ve_coz("RSV2", _snR2, _dR, cfg)    # SHORT, fiyat yukari -> MISS
        erken_uyari_kaydet_ve_coz("RSV3", _snR3, _dR, cfg)    # esik 99 ATR -> NOTR
        _rows_eu = _erken_yukle()
        _oc = {r["symbol"]: r.get("outcome") for r in _rows_eu}
        _kar = erken_uyari_karne("RSV")
        eu_resolve = (_oc.get("RSV") == "HIT" and _oc.get("RSV2") == "MISS"
                      and _oc.get("RSV3") == "NOTR" and _kar == (1, 1, 0))
        # (e) okuma-hatasi korumasi: _ERKEN_READ_FAIL iken kaydet EZMEZ
        globals()["_ERKEN_READ_FAIL"] = True
        eu_guard = _erken_kaydet([{"x": 1}], cfg) is None
        globals()["_ERKEN_READ_FAIL"] = False
    finally:
        try:
            os.remove(_euTmp)
        except Exception:
            pass
        if _oldEU is None:
            os.environ.pop("YON_ERKEN_UYARI_LOG", None)
        else:
            os.environ["YON_ERKEN_UYARI_LOG"] = _oldEU
    ok_all = ok_all and eu_fire and eu_sinif and eu_det and eu_resolve and eu_guard
    print(f"  squeeze fixture default (>=2 kanit) FIRE: {'OK' if eu_fire else '!!! ATESLENMEDI'} "
          f"(tur={_euA.tur} kanit={len(_euA.kanitlar)})")
    print(f"  sinif: VDIP->V-DONUS/LONG, DUMP artik DUMP-tur URETMEZ (oncu): {'OK' if eu_sinif else '!!! HATA'}")
    print(f"  determinizm: {'OK' if eu_det else '!!! FARKLI'}")
    print(f"  resolver HIT/MISS/NOTR + karne(1,1,0): {'OK' if eu_resolve else '!!! HATA'}")
    print(f"  okuma-hatasi korumasi (dosya EZILMEZ): {'OK' if eu_guard else '!!! HATA'}")

    print("\n" + "=" * 52)
    ok_all = ok_all and _step4_btc_repairtest(cfg)
    # F11 (YÖNTEM tamiri): beklenti katmani + KARAR-DEGISMEZLIGI kaniti regresyona dahil.
    print()
    ok_all = ok_all and yontem_tests()
    print(f"SELF-TEST bitti: boru hatti calisiyor. Regresyonlar (dip-short + yasam-dongusu + STEP4 BTC + YONTEM): {'GECTI' if ok_all else 'KALDI'}")
    # Bug 10: bool yerine ACIK cikis kodu (0=PASS, 1=INVARIANT_FAIL). Ozet satiri GECTI/KALDI
    # ile bittigi icin mutasyon harness'inin metin-parseri de bozulmadan calisir.
    return EXIT_PASS if ok_all else EXIT_INVARIANT_FAIL


def mutasyon_testi():
    """MUTASYON TESTI (dev modu, ag yok): kritik koruma hatlari KASITLI bozulur ve
    selftest'in yakaladigi KANITLANIR. 'Test var' demek yetmez — testin DISI oldugu
    olculur: her mutant ayri dosyaya yazilip ayri surecte `selftest` kosulur.
    Mutant 'KALDI' der ya da cokerse = OLDURULDU (dogru). 'GECTI' derse = HAYATTA
    (o koruma icin test KOR demektir -> ayni turda kapatilacak bulgu)."""
    import shutil
    import subprocess
    import tempfile
    mutasyonlar = [
        ("dip-veto kapali (dipte SHORT serbest)",
         "forbid_short = tested_sup and (_dip_rejection(cs, cfg) or ext_bar or _wick_lo)",
         "forbid_short = False",
         "V-DIP"),
        ("tepe-veto kapali (tepede LONG serbest)",
         "forbid_long = tested_res and (_top_rejection(cs, cfg) or ext_bar or _wick_hi)",
         "forbid_long = False",
         "V-TEPE"),
        ("taze_donus olu (donus penceresi kor)",
         "def taze_donus(cs: List[Candle], htf: List[Candle], cfg: Config) -> Tuple[bool, str]:",
         'def taze_donus(cs: List[Candle], htf: List[Candle], cfg: Config) -> Tuple[bool, str]:\n'
         '    return (False, "")',
         "TAZE DONUS"),
        ("supurme olcumu olu (stop payi sabite duser)",
         "def supurme_olcumu(cs: List[Candle], atrs: List[float], cfg: Config\n"
         "                   ) -> Tuple[float, float, int, int, bool]:",
         "def supurme_olcumu(cs: List[Candle], atrs: List[float], cfg: Config\n"
         "                   ) -> Tuple[float, float, int, int, bool]:\n"
         "    return (cfg.inval_pad_atr, cfg.inval_pad_atr, 0, 0, False)",
         "SUPURME-KALIBRASYON"),
        ("kopru olu (fitil riski gorunmez)",
         "def _bridge_cross(x0: float, x1: float, b: float, sig: float, ust: bool) -> float:",
         "def _bridge_cross(x0: float, x1: float, b: float, sig: float, ust: bool) -> float:\n"
         "    return 0.0",
         "KOPRU"),
        ("ozellik gelecege bakar (lookahead enjeksiyonu)",
         "win = cs[max(0, i - rw + 1):i + 1]",
         "win = cs[max(0, i - rw + 1):i + 2]",
         "NO-LOOKAHEAD"),
        ("kabul-bayragi olu-False (T8 kok neden: kirilim kabulu hic algilanmaz)",
         "def _accepted_break(cs: List[Candle], level: float, side: str, n: int, k: int) -> bool:",
         "def _accepted_break(cs: List[Candle], level: float, side: str, n: int, k: int) -> bool:\n"
         "    return False",
         "KABUL-BAYRAGI"),
        ("kabul-bayragi olu-True (taze supurme de 'kabul' sayilir)",
         "        return sum(1 for c in seg if c.close < level) >= k",
         "        return True",
         "KABUL-BAYRAGI"),
        ("rejim yedek-yolu tek-mumla doner (canli BTC bulgusu geri alinir)",
         "if mb >= 0.3 and _mb_once >= 0.3:",
         "if mb >= 0.3:",
         "REJIM-AILESI"),
        ("rejim 15m-oncelik yolu tek-mumla doner (canli SOL bulgusu geri alinir)",
         "abs(mb) >= 0.35 and abs(_mb_once) >= 0.35 and (mb > 0) == (_mb_once > 0)",
         "abs(mb) >= 0.35",
         "REJIM-AILESI"),
        ("ASIRI-MUM korumasi olu (ofori/kapitulasyon kovalanir)",
         "ext_bar_atr: float = 2.0",
         "ext_bar_atr: float = 1e9",
         "V-TEPE"),
        ("sifir-skill kapisi olu (overlay tek basina market acar; R3/REPORT_3 geri alinir)",
         '    if getattr(cfg, "zero_skill_abstain", True) and max(sk.values(), default=0.0) <= 0.0:',
         "    if False:",
         "SIFIR-SKILL"),
        ("EV kapisi kilitli (T3 regresyonu: motor yapisal BEKLE)",
         "ev_min_abs = ev_min_atr_eff * st.atr",
         "ev_min_abs = ev_min_atr_eff * st.atr + 1e18",
         "KILIT-YOK"),
        ("pusu takibi olu (tetikler hic ateslenmez)",
         "def _plan_degerlendir(plan: Dict, cands: List[Candle], k: int, H: int) -> Dict:",
         "def _plan_degerlendir(plan: Dict, cands: List[Candle], k: int, H: int) -> Dict:\n"
         '    return {"durum": "BEKLEMEDE", "gecen": 0}',
         "KOSULLU-PLAN"),
        ("pusu karnesi olu (olculen sicil kaybolur)",
         "def pusu_karne(symbol: str) -> Tuple[int, int, int]:",
         "def pusu_karne(symbol: str) -> Tuple[int, int, int]:\n"
         "    return (0, 0, 0)",
         "KOSULLU-PLAN"),
        ("ensemble kapisi olu (topluluk karsi durusta frenlemez)",
         '    if total_weight < cfg.ens_gate_minw or side not in ("LONG", "SHORT"):',
         "    if True:",
         "YON9-EK"),
        ("tahmin cozumu olu (oncu-tahmin sicili asla olculmez)",
         "def forecast_kaydet_ve_coz(symbol: str, snap: Snapshot, d: Decision, cfg: Config) -> List[str]:",
         "def forecast_kaydet_ve_coz(symbol: str, snap: Snapshot, d: Decision, cfg: Config) -> List[str]:\n"
         "    return []",
         "ONCU-TAHMIN"),
        ("dar-bant kapisi olu (dar bantta pusu yine kurulur)",
         "if ust - alt < cfg.min_target_atr * st.atr:",
         "if False and ust - alt < cfg.min_target_atr * st.atr:",
         "KOSULLU-PLAN"),
        ("ext_bar kirlenmis ATR'ye geri doner (2.0-2.17x dip penceresi acilir)",
         "_atr_onc = atrs[-2] if len(atrs) >= 2 and atrs[-2] > 0 else st.atr",
         "_atr_onc = st.atr",
         "DUSMAN-2b"),
        ("GEC-KACTI korumasi olu (negatif-R 'HEDEF' karneye girer)",
         "if (hedef - entry) * sgn <= 0:",
         "if False:",
         "KOSULLU-PLAN"),
        ("makro OI hucresi funding-koru (KAZANC-1 geri alinir: kosulsuz sikisma tilti)",
         "            if fund_neg_ext or _f is None:",
         "            if True:",
         "MAKRO-OI-FUNDING"),
        ("tuzak-kombo olu (#28/#29 hic ateslemez)",
         "        if (of28 is not None and of28.n >= 40 and abs(mom1) < cfg.absorb_flat_atr",
         "        if (False and of28 is not None and of28.n >= 40 and abs(mom1) < cfg.absorb_flat_atr",
         "MIKRO-TUZAK"),
        ("ISLEM PLANI olu (net plan basilmaz)",
         '    L.append("== ISLEM PLANI (NET; CANLI — yalniz bu barin verisi, kehanet degil) ==")',
         "    return L",
         "ISLEM-PLANI"),
        ("canli-only ev kapisi olu (gecmis kalibrasyon yine karara girer)",
         "        return (cfg.ev_min_atr, cfg.dir_edge_min, 'CANLI (kalibrasyon karara girmez)')",
         "        return (cfg.ev_min_atr * 5.0, cfg.dir_edge_min, 'CANLI (kalibrasyon karara girmez)')",
         "ISLEM-PLANI"),
        ("islem plani store-koru (sozlesme yerine taze hesap basar; F1/F2 geri gelir)",
         "        _kyt = _plan_yukle().get(symbol) or {}",
         "        _kyt = {}",
         "ISLEM-PLANI"),
        ("pusu trend-filtresi olu (karsi-trend kenar yine kurulur; LONG-tepki 1/11 geri gelir)",
         '        _yasak_tip = "LONG-TEPKI" if _tdir_pk < 0 else "SHORT-TEPKI"',
         '        _yasak_tip = "HICBIRI"',
         "KOSULLU-PLAN"),
        ("sade ozet olu (kullanici karti bos doner)",
         '    L.append(f"{symbol}  (kapali fiyat {_fmt(st.price)}{_lp_txt})")',
         "    return L",
         "ISLEM-PLANI"),
        ("nihai rapor olu (zorunlu 9-bolum format basilmaz)",
         '    L.append("== NIHAI RAPOR (zorunlu format; kaynak: ayni kosunun d/store olcumleri) ==")',
         "    return L",
         "NIHAI-RAPOR"),
        ("karar tablosu olu (sembol-alti Varyant-B kart basilmaz)",
         '    L.append("── KARAR TABLOSU ──")',
         "    return L",
         "KARAR-TABLOSU"),
        ("giris-zamanlama olu (S2: SIMDI-market/PUSU-bekle ayrimi basilmaz)",
         "def giris_zamanlama(symbol: str, snap: Snapshot, st: Optional[Structure],\n"
         "                    d: Decision, cfg: Config) -> str:",
         "def giris_zamanlama(symbol: str, snap: Snapshot, st: Optional[Structure],\n"
         "                    d: Decision, cfg: Config) -> str:\n"
         '    return ""',
         "GIRIS-ZAMANLAMA"),
        ("erken-uyari olu (S3: ayri uyari katmani hic ateslemez)",
         'def erken_uyari(symbol: str, snap: Snapshot, st: Optional[Structure],\n'
         '                scen: Optional["Scenario144"], cfg: Config) -> ErkenUyari:',
         'def erken_uyari(symbol: str, snap: Snapshot, st: Optional[Structure],\n'
         '                scen: Optional["Scenario144"], cfg: Config) -> ErkenUyari:\n'
         "    return ErkenUyari()",
         "ERKEN-UYARI"),
    ]
    with open(os.path.abspath(__file__), "r", encoding="utf-8") as f:
        kaynak = f.read()
    # Hedef metinler bu fonksiyonun mutasyon listesinde de GECIYOR -> sayim/degistirme
    # yalniz MOTOR GOVDESINDE (bu fonksiyonun tanimindan onceki kisim) yapilir.
    # ("\n"+"def ..." birlestirmesi: arama deseni bu satirin kendisiyle eslesmesin diye.)
    _sep = "\n" + "def mutasyon_testi("
    govde, _bul, kuyruk = kaynak.partition(_sep)
    if not _bul:
        print("!!! KURGU HATASI: motor govdesi ayristirilamiyor — mutasyon iptal")
        return False
    tmpd = tempfile.mkdtemp(prefix="fable_mut_")
    print("MUTASYON TESTI — regresyonlarin disi var mi? (mutant basina TAM selftest kosulur)")
    print(f"[NOT] dev modu: toplam ~{len(mutasyonlar) + 1} x selftest suresi surer "
          f"(telefonda 10-20+ dk, tam CPU). Gunluk kullanim icin GEREKMEZ.")
    print("=" * 72)
    hepsi_olduruldu = True
    try:
        # BASELINE: mutasyonsuz selftest bu ortamda GECMELI; gecmiyorsa 'olduruldu'
        # raporlari anlamsizdir (sahte guven). Suresi mutant timeout'unu da kalibre
        # eder (sabit 300 sn yavas telefonda sahte ZAMAN-ASIMI alarmi uretiyordu).
        byol = os.path.join(tmpd, "baseline.py")
        with open(byol, "w", encoding="utf-8") as f:
            f.write(kaynak)
        benv = dict(os.environ)
        benv["YON_PANEL_LOG"] = os.path.join(tmpd, "base_log.jsonl")
        benv["YON_DISAGREE_LOG"] = os.path.join(tmpd, "base_dis.json")
        tb0 = time.time()
        try:
            bpr = subprocess.run([sys.executable, byol, "selftest"],
                                 capture_output=True, text=True, timeout=1800, env=benv)
        except subprocess.TimeoutExpired:
            print("!!! BASELINE selftest 30 dk'da bitmedi — bu cihazda mutasyon testi kosulamaz")
            return False
        base_sure = time.time() - tb0
        if bpr.returncode != 0:
            print(f"!!! BASELINE selftest GECMEDI (rc={bpr.returncode}) — once selftest'i duzelt; "
                  f"mutasyon sonuclari ancak yesil baseline ustunde anlamlidir")
            return False
        mut_timeout = max(300, int(base_sure * 5))
        print(f"[BASELINE] selftest GECTI ({base_sure:.0f} sn) -> mutant timeout = {mut_timeout} sn")
        for mi, (ad, eski, yeni, beklenen) in enumerate(mutasyonlar, 1):
            n_hit = govde.count(eski)
            if n_hit != 1:
                # H6 dersi: eslesme sayisi dogrulanmadan replace YASAK
                hepsi_olduruldu = False
                print(f"[{mi}/{len(mutasyonlar)}] {ad}\n"
                      f"    !!! KURGU HATASI: hedef metin {n_hit} kez bulundu (1 olmali) — atlandi")
                continue
            myol = os.path.join(tmpd, f"mutant_{mi}.py")
            with open(myol, "w", encoding="utf-8") as f:
                f.write(govde.replace(eski, yeni) + _sep + kuyruk)
            env = dict(os.environ)
            env["YON_PANEL_LOG"] = os.path.join(tmpd, f"mut{mi}_log.jsonl")
            env["YON_DISAGREE_LOG"] = os.path.join(tmpd, f"mut{mi}_dis.json")
            t0 = time.time()
            try:
                pr = subprocess.run([sys.executable, myol, "selftest"],
                                    capture_output=True, text=True, timeout=mut_timeout, env=env)
                cikti = (pr.stdout or "") + (pr.stderr or "")
                # 'KALDI' alt-dizgisi YETMEZ (orn. 'KALDIRAC KOPUGU' icerir) -> yalniz
                # ozet satirinin sonundaki KALDI + selftest'in cikis kodu esas alinir.
                olduruldu = (pr.returncode != 0) or any(
                    ln.startswith("SELF-TEST bitti") and ln.rstrip().endswith("KALDI")
                    for ln in cikti.splitlines())
                durum_ek = "" if pr.returncode == 0 else f" (selftest rc={pr.returncode})"
            except subprocess.TimeoutExpired:
                cikti, olduruldu = "", False
                durum_ek = " (ZAMAN ASIMI: mutant kilitlendi, test yakalamadi sayilir)"
            # hangi bolumler bagirdi? ('!!!' iceren satirlarin bolum basligi)
            vuranlar: List[str] = []
            bolum = "?"
            for ln in cikti.splitlines():
                # bolum basligi SUTUN-0'da '[...]' ile baslar; girintili '[UPTREND ]'
                # gibi VERI satirlari baslik sayilmaz (denetci bulgusu)
                if ln.startswith("[") and "]" in ln:
                    bolum = ln[1:ln.index("]")]
                if "!!!" in ln and bolum not in vuranlar:
                    vuranlar.append(bolum)
            hepsi_olduruldu = hepsi_olduruldu and olduruldu
            if olduruldu:
                hedefte = any(beklenen in v for v in vuranlar)
                print(f"[{mi}/{len(mutasyonlar)}] {ad}\n"
                      f"    OLDURULDU ({time.time()-t0:.0f} sn){durum_ek} — vuran bolum(ler): "
                      f"{', '.join(vuranlar) if vuranlar else 'cokme'}"
                      + ("" if hedefte or not vuranlar
                         else f"  [NOT: beklenen {beklenen} degil — dolayli yakalandi]"))
            else:
                print(f"[{mi}/{len(mutasyonlar)}] {ad}\n"
                      f"    !!! HAYATTA ({time.time()-t0:.0f} sn){durum_ek} — selftest GECTI dedi; "
                      f"beklenen bekci: {beklenen}. BU KORUMA ICIN TEST KOR!")
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)
    print("=" * 72)
    print("MUTASYON TESTI: " + ("GECTI — tum mutantlar olduruldu (testlerin disi var)"
                                if hepsi_olduruldu else
                                "KALDI — hayatta mutant var: o koruma testsiz, kapatilmali"))
    return hepsi_olduruldu



# ════════════════════════════════════════════════════════════════════════════
# PYDROID KURULUM/KANIT MODU — fable6.py
# ════════════════════════════════════════════════════════════════════════════
def _pydroid_download_dir() -> str:
    """Android/Pydroid icin ilk yazilabilir Download klasorunu bul; yoksa script klasoru."""
    adaylar = [
        "/storage/emulated/0/Download",
        "/sdcard/Download",
        os.path.expanduser("~/Download"),
        os.path.dirname(os.path.abspath(__file__)) or os.getcwd(),
    ]
    for d in adaylar:
        try:
            if not os.path.isdir(d):
                continue
            t = os.path.join(d, ".fable4_yaz_testi")
            with open(t, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(t)
            return d
        except Exception:
            continue
    return os.getcwd()


def _sha256_file(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def _step4_static_checks(kaynak: str) -> List[Tuple[str, bool, str]]:
    """Kod calismadan once statik/sozlesme kontrolleri: sihirli esik ve katman sozlesmesi.

    Negatif aramalar (Granger/TE, _STEP3R sabitleri, BTC besinci-at adlari) bu
    fonksiyonun kendi metnini ve rapor stringlerini saymasin diye yalniz motor
    govdesinde yapilir.
    """
    motor = kaynak.partition("\ndef _step4_static_checks")[0]
    checks: List[Tuple[str, bool, str]] = []
    def ok(ad: str, kosul: bool, notu: str = ""):
        checks.append((ad, bool(kosul), notu))
    # Ana BTC bas-at sozlesmesi
    ok("BtcLeaderState veri yapisi var", "class BtcLeaderState" in kaynak)
    ok("build_btc_leader_state var", "def build_btc_leader_state" in kaynak)
    ok("btc_veto_mode_for_side var", "def btc_veto_mode_for_side" in kaynak)
    ok("leader tahminci yon uretmez, sinirli katkidir", "def est_btc_leader_state" in kaynak and "confirm_adj" in kaynak)
    ok("son 4 adet 15m kronoloji fonksiyonu var", "def _last4_chronology" in kaynak)
    ok("Step4 repairtest var", "def _step4_btc_repairtest" in kaynak)
    ok("Step4C market risk kapisi var", "def market_risk_kapisi" in kaynak and "def acik_market_sinyali_var" in kaynak)
    ok("Step4D acik sinyal risk denetimi var", "def open_signal_risk_audit" in kaynak)
    ok("Step4E market kalite kapisi var", "def market_quality_kapisi" in kaynak)
    ok("Step4F live fiyat kapisi var", "def live_price_gap_kapisi" in kaynak)
    ok("Step4G cozulmus OPEN sinyal kapisi var", "def _signal_resolved_by_price" in kaynak)
    ok("Step4H acik sinyal live-mark ile raporlanir", "status_price = float(_lp)" in kaynak and "open_signal_risk_audit(r, status_price" in kaynak)
    # Config disiplinleri
    for ad in [
        "btc_leader_enabled", "btc_core_symbol", "btc_corr_win", "btc_beta_win",
        "btc_leadlag_win", "btc_metric_norm_win", "btc_leader_z_hi", "btc_leader_q_hi",
        "btc_confirm_cap", "btc_hard_veto_min_confirm", "btc_soft_veto_min_confirm",
        "btc_decorrelation_min_confirm", "btc_risk_penalty_cap", "btc_eth_major_profile",
        "pusu_karne_gate_enabled", "pusu_karne_min_resolved", "pusu_karne_bad_wilson",
        "market_risk_gate_enabled", "market_rr_min", "market_open_signal_gate_enabled",
        "open_signal_audit_enabled", "open_signal_rr_min", "open_signal_adverse_atr_warn",
        "open_signal_resolved_price_gate_enabled",
        "market_quality_gate_enabled", "market_min_target_prob", "market_max_stop_prob",
        "market_min_prob_gap", "market_counter_wick_gate_enabled",
        "live_price_audit_enabled", "live_gap_market_gate_enabled", "live_gap_pusu_gate_enabled", "live_gap_block_atr",
        "market_counter_wick_min_target", "market_counter_wick_max_stop",
    ]:
        ok(f"Config.{ad} var", ad in kaynak)
    # Canli yön disiplini: agir nedensellik metodlari canli kapida yok.
    ok("Granger canli yon kapisi yok", "granger" not in motor.lower())
    ok("Transfer entropy canli yon kapisi yok", "transfer entropy" not in motor.lower() and "transfer_entropy" not in motor.lower())
    # Step3R sabitleri yeni nihai dosyada global halde kalmasin.
    ok("_STEP3R_MIN_SCORE gomulu sabiti yok", "_STEP3R_MIN_SCORE" not in motor)
    ok("_STEP3R_MIN_GAP gomulu sabiti yok", "_STEP3R_MIN_GAP" not in motor)
    # BTC karar atina degil, ust kapıya bagli: yeni LONG/SHORT rota adi uretmeyelim.
    ok("BTC besinci islem ati degil", "BTC_DEVAM" not in motor and "BTC_TEPKI" not in motor)
    return checks


def _capture_call(fn, *args, **kwargs) -> Tuple[bool, str]:
    import io as _io
    import contextlib as _contextlib
    buf = _io.StringIO()
    try:
        with _contextlib.redirect_stdout(buf), _contextlib.redirect_stderr(buf):
            r = fn(*args, **kwargs)
        return bool(r), buf.getvalue()
    except Exception:
        import traceback as _traceback
        return False, buf.getvalue() + _traceback.format_exc()


def pydroid_step4_kanit(full: bool = False) -> bool:
    """Pydroid icin tek komutluk kurulum + kanit raporu.

    Kullanim:
      python fable6.py pydroid       -> hizli, agsiz, zaman-asimsiz kanit
      python fable6.py pydroidfull   -> hizli kanit + tam selftest (telefonda uzun surebilir)

    Bu fonksiyon:
      1) Kendi dosyasini Download/fable6.py olarak yazar.
      2) Download/fable6_pydroid_kanit.txt raporu olusturur.
      3) py_compile, statik Step4 sozlesme kontrolleri ve BTC repairtest'i kosar.
      4) full=True ise ayrica tam selftest kosar; timeout koymaz.
    """
    import py_compile as _py_compile
    import shutil as _shutil
    import subprocess as _subprocess
    import time as _time

    basla = _time.time()
    src_path = os.path.abspath(__file__)
    dl = _pydroid_download_dir()
    dst_path = os.path.join(dl, "fable6.py")
    rapor_path = os.path.join(dl, "fable6_pydroid_kanit.txt")
    ok_all = True
    satirlar: List[str] = []

    def log(s: str = ""):
        print(s)
        satirlar.append(str(s))

    log("=" * 72)
    log("FABLE6 PYDROID KURULUM/KANIT RAPORU")
    log("=" * 72)
    log(f"zaman: {_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"kaynak: {src_path}")
    log(f"download: {dl}")
    log("komut: python fable6.py pydroid  |  python fable6.py pydroidfull")
    log("")

    # 1) Download kopyasi
    try:
        tmp = dst_path + ".tmp"
        with open(src_path, "rb") as fsrc, open(tmp, "wb") as fdst:
            _shutil.copyfileobj(fsrc, fdst)
        os.replace(tmp, dst_path)
        log(f"[✓] Download kopyasi yazildi: {dst_path}")
        log(f"[✓] SHA256: {_sha256_file(dst_path)}")
    except Exception as e:
        ok_all = False
        log(f"[✗] Download kopyasi yazilamadi: {e}")

    # 2) py_compile
    try:
        _py_compile.compile(src_path, doraise=True)
        log("[✓] py_compile OK: Python sozdizimi gecerli")
    except Exception as e:
        ok_all = False
        log(f"[✗] py_compile HATA: {e}")

    # 3) statik sozlesme kontrolleri
    try:
        with open(src_path, "r", encoding="utf-8") as f:
            kaynak = f.read()
        log("")
        log("STEP4 STATIK SOZLESME KONTROLLERI")
        for ad, passed, notu in _step4_static_checks(kaynak):
            ok_all = ok_all and passed
            log(("[✓] " if passed else "[✗] ") + ad + ((" — " + notu) if notu else ""))
    except Exception as e:
        ok_all = False
        log(f"[✗] statik kontrol okunamadi: {e}")

    # 4) hizli BTC mekanik repairtest
    log("")
    log("STEP4 BTC REPAIRTEST")
    r_ok, r_out = _capture_call(_step4_btc_repairtest, Config())
    ok_all = ok_all and r_ok
    for ln in r_out.rstrip().splitlines():
        log(ln)
    log("[✓] Step4 BTC repairtest GECTI" if r_ok else "[✗] Step4 BTC repairtest KALDI")

    # 5) full selftest opsiyonel: timeout yok; kullanici istemedikce kosulmaz.
    if full:
        log("")
        log("TAM SELFTEST BASLIYOR — timeout yok; telefonda uzun surebilir")
        try:
            env = dict(os.environ)
            env.setdefault("YON_PANEL_LOG", os.path.join(dl, "fable5_yon_signals.jsonl"))
            env.setdefault("YON_DISAGREE_LOG", os.path.join(dl, "fable5_yon_disagree.json"))
            pr = _subprocess.run([sys.executable, src_path, "selftest"], text=True,
                                 capture_output=True, env=env)
            log(pr.stdout[-12000:] if pr.stdout else "")
            if pr.stderr:
                log("--- STDERR ---")
                log(pr.stderr[-4000:])
            if pr.returncode == 0:
                log("[✓] Tam selftest GECTI")
            else:
                ok_all = False
                log(f"[✗] Tam selftest KALDI rc={pr.returncode}")
        except Exception as e:
            ok_all = False
            log(f"[✗] Tam selftest calistirilamadi: {e}")
    else:
        log("")
        log("[i] Tam selftest bu hizli modda kosulmadi. Kosmak icin: python fable6.py pydroidfull")

    log("")
    log("NIHAI DURUM: " + ("GECTI" if ok_all else "KALDI"))
    log(f"sure: {_time.time() - basla:.1f} sn")
    log(f"rapor: {rapor_path}")
    try:
        with open(rapor_path, "w", encoding="utf-8") as f:
            f.write("\n".join(satirlar) + "\n")
        print(f"[✓] Kanit raporu yazildi: {rapor_path}")
    except Exception as e:
        ok_all = False
        print(f"[✗] Kanit raporu yazilamadi: {e}")
    return ok_all

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]


def fable6_tests() -> bool:
    """Agsiz normal/sinir/hata + simetri + PIT-defter regresyon paketi."""
    import tempfile as _tmp
    import shutil as _sh
    tmp = _tmp.mkdtemp(prefix="fable6_tests_")
    old_env = {k: os.environ.get(k) for k in
               ("FABLE6_LEDGER", "YON_PANEL_LOG", "YON_FORECAST_LOG", "YON_PLAN_LOG",
                "YON_CPCV_CACHE")}
    os.environ["FABLE6_LEDGER"] = os.path.join(tmp, "forward.jsonl")
    os.environ["YON_PANEL_LOG"] = os.path.join(tmp, "signals.jsonl")
    os.environ["YON_FORECAST_LOG"] = os.path.join(tmp, "forecast.jsonl")
    os.environ["YON_PLAN_LOG"] = os.path.join(tmp, "plans.json")
    results: List[Tuple[str, bool]] = []

    def check(name: str, cond: bool):
        results.append((name, bool(cond)))
        print(f"{name}: {'PASS' if cond else 'FAIL'}")

    try:
        cfg = Config(mc_paths=60, min_train=60, knn_k=20, bootstrap_reps=40)
        # NORMAL: tam H endpoint, uc sinif ve saf OFFLINE karar.
        cs = _synthetic_candles(190, 606, 0.0002, 0.010)
        atrs = atr_series(cs, cfg.atr_period)
        X, y, idxs = build_training(cs, atrs, cfg)
        check("normal_mature_label_boundary",
              bool(X) and idxs[-1] == len(cs) - 1 - cfg.horizon)
        check("normal_three_classes_valid", set(y).issubset(set(CLASSES)))
        snap = Snapshot("TST", cs, last_closed_ms=cs[-1].close_ms,
                        data_watermark_ms=cs[-1].close_ms)
        old_loader = globals()["_load_signals"]
        globals()["_load_signals"] = lambda: (_ for _ in ()).throw(
            AssertionError("OFFLINE store okudu"))
        try:
            d = decide(snap, cfg, context=DecisionContext.offline(cs[-1].close_ms))
            offline_ok = d.mode == "OFFLINE"
        finally:
            globals()["_load_signals"] = old_loader
        check("normal_offline_store_isolation", offline_ok)
        check("normal_probability_simplex",
              abs(d.p_down + d.p_flat + d.p_up - 1.0) < 1e-12 and
              all(0 <= p <= 1 for p in (d.p_down, d.p_flat, d.p_up)))

        # SINIR: sabit endpoint FLAT; esit son fiyat iki yone de kazanc yazmaz.
        t0 = 1_699_999_200_000
        flat = [Candle(100, 101, 99, 100, close_ms=t0 + (i + 1) * cfg.interval_ms - 1)
                for i in range(40)]
        fa = atr_series(flat, cfg.atr_period)
        check("boundary_endpoint_flat", endpoint_label(flat, 20, fa, cfg) == 0)
        check("boundary_streak_flat", _streak_at(flat, len(flat) - 1) == 0)
        wl, _ = _bt_resolve(flat, 20, 100, 110, 90, "LONG", cfg.horizon)
        ws, _ = _bt_resolve(flat, 20, 100, 90, 110, "SHORT", cfg.horizon)
        check("boundary_flat_not_long_or_short_win", wl == 0 and ws == 0)
        check("boundary_mc_flat", mc_endpoint_probs([[1.0] * cfg.horizon], 100, 1, cfg)[1] > .999)
        _pt, _ps, _terminal = mc_first_passage([[1.005, 1.01]], 100, 110, 90, "LONG",
                                                return_terminal=True)
        check("boundary_no_hit_terminal_payoff_kept",
              _pt == 0 and _ps == 0 and abs(_terminal - 1.0) < 1e-12)

        check("boundary_six_regime_families",
              set(REGIME_FAMILY6.values()) - {"BELIRSIZ"} ==
              {"TREND-YUKARI", "TREND-ASAGI", "YATAY", "KIRILIM-VOL", "DONUS", "POZISYONLANMA"})

        # LONG/SHORT AYNA: log-fiyat yansimasi MC dagilimini ters cevirmeli.
        p0 = cs[0].close
        inv = lambda x: p0 * p0 / x
        mirror = [Candle(inv(c.open), inv(c.low), inv(c.high), inv(c.close), c.volume,
                         close_ms=c.close_ms) for c in cs]
        cfgm = replace(cfg, mc_paths=240, mc_magnet_k=0.0, label_neutral_atr=0.0)
        st1, st2 = build_structure(cs, cfgm), build_structure(mirror, cfgm)
        pa, _ = mc_simulate(cs, st1, 0.0, cfgm,
                            random.Random(_mirror_invariant_seed(cs)), paths_n=240)
        pb, _ = mc_simulate(mirror, st2, 0.0, cfgm,
                            random.Random(_mirror_invariant_seed(mirror)), paths_n=240)
        qa, qb = mc_endpoint_probs(pa, st1.price, st1.atr, cfgm), \
                 mc_endpoint_probs(pb, st2.price, st2.atr, cfgm)
        check("boundary_long_short_mc_mirror", abs(qa[0] - qb[2]) < .03 and abs(qa[2] - qb[0]) < .03)

        # Yon-farkindalikli icra + yetersiz derinlikte uydurma slip yok.
        book = {"bid": 99.9, "ask": 100.1,
                "asks": [(100.1, 1.0)], "bids": [(99.9, 1.0)]}
        live_snap = Snapshot("TST", cs, book=book, live_price=100.0)
        check("boundary_executable_bid_ask",
              executable_entry_price(live_snap, "LONG", 100, DecisionContext()) == 100.1 and
              executable_entry_price(live_snap, "SHORT", 100, DecisionContext()) == 99.9)
        check("boundary_insufficient_depth_is_infinite",
              math.isinf(slip_olcum_frac(book, 100_000, "BUY")))

        # Esit p_down/p_up hicbir API'de SHORT/DOWN'a dusmez.
        tiep = (0.45, 0.10, 0.45)
        check("boundary_directional_tie_is_flat",
              argmax_class(tiep, cfg.tie_eps_rel) == 0)
        check("boundary_directional_tie_conflicts_both_sides",
              ensemble_side_conflict("LONG", tiep, cfg.ens_gate_minw + 1, cfg) and
              ensemble_side_conflict("SHORT", tiep, cfg.ens_gate_minw + 1, cfg))

        # PIT: origin-sonrasi yon verisi, ileri watermark, last_closed uyusmazligi
        # ve gecmisin ortasindaki tek mum boslugu gorunur bicimde reddedilir.
        origin, predt = cs[-1].close_ms, cs[-1].close_ms + 10_000
        late_src = Snapshot("PIT", cs, last_closed_ms=origin,
                            data_watermark_ms=origin,
                            source_times={"late": {"event_time": origin + 1,
                                                   "available_time": predt,
                                                   "role": "direction"}})
        wm_src = Snapshot("PIT", cs, last_closed_ms=origin,
                          data_watermark_ms=predt + 1)
        lc_src = Snapshot("PIT", cs, last_closed_ms=cs[-2].close_ms,
                          data_watermark_ms=origin)
        gap_cs = cs[:100] + cs[101:]
        gap_src = Snapshot("PIT", gap_cs, last_closed_ms=gap_cs[-1].close_ms,
                           data_watermark_ms=gap_cs[-1].close_ms)
        check("error_pit_origin_event_rejected",
              any("origininden sonra" in x for x in snapshot_pit_violations(late_src, cfg, predt)))
        check("error_pit_future_watermark_rejected",
              any("watermark" in x for x in snapshot_pit_violations(wm_src, cfg, predt)))
        check("error_pit_last_closed_mismatch_rejected",
              any("last_closed" in x for x in snapshot_pit_violations(lc_src, cfg, predt)))
        check("error_pit_mid_history_gap_rejected",
              any("zaman boslugu" in x for x in snapshot_pit_violations(gap_src, cfg, gap_src.last_closed_ms)))
        late_pred = origin + cfg.ledger_max_latency_ms + 1
        late_live = Snapshot("LATE", cs, last_closed_ms=origin,
                             data_watermark_ms=origin, predicted_at_ms=late_pred,
                             live_fetched_ms=late_pred, stale=False)
        late_d = decide(late_live, cfg,
                        context=DecisionContext(predicted_at_ms=late_pred))
        check("error_live_origin_latency_blocks_execution",
              late_d.karar == "BEKLE" and late_d.gate_code == "LATENCY_GATE"
              and "LATENCY" in late_d.sebep)
        server_late = Snapshot("SERVERLATE", cs, last_closed_ms=origin,
                               data_watermark_ms=origin, live_server_ms=late_pred,
                               live_price=cs[-1].close, stale=False)
        server_late_d = decide(server_late, cfg, context=DecisionContext())
        no_clock_d = decide(Snapshot("NOCLOCK", cs, last_closed_ms=origin,
                                     data_watermark_ms=origin, stale=False),
                            cfg, context=DecisionContext())
        check("error_live_server_time_cannot_fallback_to_origin",
              server_late_d.gate_code == "LATENCY_GATE" and
              no_clock_d.gate_code == "LATENCY_GATE")

        # Origin-sonrasi execution book'u makro yonu degistiremez.
        bmeta = {"book": {"event_time": None, "available_time": predt,
                           "role": "execution"}}
        bm = []
        for imb in (-1.0, 1.0):
            ss = Snapshot("BOOK", cs, book={"imbalance": imb},
                          last_closed_ms=origin, data_watermark_ms=origin,
                          source_times=bmeta)
            ee = macro_leading_estimate(ss, cfg)
            bm.append((ee.p_up, ee.weight, ee.note))
        check("normal_execution_book_cannot_tilt_direction",
              bm[0][0] == bm[1][0] == 0.5 and bm[0][1] == bm[1][1] == 0.0 and
              all("ATLANDI" in x[2] for x in bm))

        # Etkin-OOS min-N: ham 15m sayisi agirlik acamaz.
        sk_hi = skill_weights(X, y, idxs, cs, atrs,
                              replace(cfg, skill_min_oos=999, skill_mc_min_oos=999),
                              random.Random(77))
        check("boundary_skill_requires_effective_oos_n", all(v == 0.0 for v in sk_hi.values()))

        # HATA: bozuk zaman ve kilitli olmayan fiyat turu gorunur bicimde reddedilir.
        bad = list(cs)
        bad[-1] = replace(bad[-1], close_ms=bad[-2].close_ms)
        bd = decide(Snapshot("BAD", bad, last_closed_ms=bad[-1].close_ms), cfg,
                    context=DecisionContext.offline(bad[-1].close_ms))
        check("error_bad_timestamp_rejected", bd.karar == "BEKLE" and "PIT" in bd.sebep)
        try:
            decide(snap, replace(cfg, price_type="MARK"),
                   context=DecisionContext.offline(cs[-1].close_ms))
            invalid_cfg = False
        except ValueError:
            invalid_cfg = True
        check("error_unlocked_price_type_rejected", invalid_cfg)

        # Append-only hash zinciri: prediction + olgun outcome; oynama tespit edilir.
        prefix = cs[:-cfg.horizon]
        pred_ms = prefix[-1].close_ms + 10_000
        lsnap = Snapshot("LEDGER", prefix, live_price=prefix[-1].close,
                         live_server_ms=pred_ms, live_fetched_ms=pred_ms,
                         last_closed_ms=prefix[-1].close_ms,
                         data_watermark_ms=prefix[-1].close_ms,
                         predicted_at_ms=pred_ms)
        ld = decide(lsnap, cfg, context=DecisionContext(predicted_at_ms=pred_ms))
        eh = record_forward_prediction("LEDGER", lsnap, ld, cfg)
        nr = resolve_forward_predictions("LEDGER", cs, cfg)
        vok, _ = verify_forward_ledger()
        check("normal_append_only_prediction_outcome", eh is not None and nr == 1 and vok)

        # 16 eszamanli yazar: exclusive flock altinda zincir ve satir sayisi korunur.
        import multiprocessing as _mp
        before_n = len(_ledger_rows())
        def _ledger_worker(i):
            _append_ledger_event({"event_type": "CONCURRENCY_TEST", "worker": i})
        ctx = _mp.get_context("fork")
        procs = [ctx.Process(target=_ledger_worker, args=(i,)) for i in range(16)]
        for p in procs:
            p.start()
        for p in procs:
            p.join(10)
        cv, _ = verify_forward_ledger()
        check("normal_ledger_concurrent_writers",
              all(p.exitcode == 0 for p in procs) and cv and
              len(_ledger_rows()) == before_n + 16)

        with open(_ledger_path(), "r", encoding="utf-8") as f:
            lines = f.readlines()
        tampered = json.loads(lines[0]); tampered["symbol"] = "TAMPER"
        lines[0] = _stable_json(tampered) + "\n"
        with open(_ledger_path(), "w", encoding="utf-8") as f:
            f.writelines(lines)
        tv, _ = verify_forward_ledger()
        refused = _append_ledger_event({"event_type": "TEST"}) is None
        check("error_ledger_tamper_detected_and_refused", (not tv) and refused)

        # Truncated JSON bos ledger gibi PASS olamaz ve ustune append edilemez.
        trunc_path = os.path.join(tmp, "truncated.jsonl")
        os.environ["FABLE6_LEDGER"] = trunc_path
        with open(trunc_path, "w", encoding="utf-8") as f:
            f.write('{"event_type":"PREDICTION"')
        tr_ok, _ = verify_forward_ledger()
        tr_ref = _append_ledger_event({"event_type": "TEST"})
        check("error_ledger_truncated_json_rejected", (not tr_ok) and tr_ref is None)

        # Kanonik metrik yalniz current-generation, protocol-valid, sabit-fazli
        # kohortu kullanir; operasyonel 15m kayitlari etkin N'yi sisirmez.
        metric_path = os.path.join(tmp, "metrics.jsonl")
        os.environ["FABLE6_LEDGER"] = metric_path
        period = cfg.horizon * cfg.interval_ms
        te = ((cs[-1].close_ms + 1) // period + 1) * period - 1
        def _metric_pair(target_end, model, valid, truth, key):
            ph = _append_ledger_event({"event_type": "PREDICTION", "symbol": "MET",
                                       "protocol_id": cfg.protocol_id,
                                       "model_hash": model, "protocol_valid": valid,
                                       "prediction_key": key, "target_end": target_end,
                                       "p_down": .10, "p_flat": .15, "p_up": .75,
                                       "decision": "LONG", "trade_decision": "LONG",
                                       "interval_low": 90.0, "interval_high": 110.0})
            _append_ledger_event({"event_type": "OUTCOME", "symbol": "MET",
                                  "protocol_id": cfg.protocol_id,
                                  "prediction_event": ph, "outcome_class": truth,
                                  "outcome_price": 105.0})
            return ph
        _first_target_hash = _metric_pair(te, model_hash(cfg), True, 1, "cohort")
        _duplicate_target_hash = _metric_pair(te, model_hash(cfg), True, -1, "cohort-rerun")
        _metric_pair(te + cfg.interval_ms, model_hash(cfg), True, -1, "overlap")
        _metric_pair(te + 2 * cfg.interval_ms, "STALE", True, 1, "stale")
        _metric_pair(te + 3 * cfg.interval_ms, model_hash(cfg), False, 1, "invalid")
        fm = forward_ledger_metrics("MET", cfg)
        check("normal_forward_metrics_generation_protocol_cohort",
              _first_target_hash == _duplicate_target_hash and fm["valid"] and
              fm["n_operational"] == 2 and fm["n"] == 1 and
              fm["hit"] == 1 and fm["band_n"] == 1 and fm["band_hit"] == 1)

        # CPCV cache yanlis model/config imzasi ile kabul edilmez.
        os.environ["YON_CPCV_CACHE"] = os.path.join(tmp, "cpcv.json")
        base_cpcv = {"pbo": .2, "S": cfg.cpcv_blocks, "n_split_gecerli": 20,
                     "n_sinyal": 40, "guvenilir": True, "mod": "tam",
                     "ts": time.time(), "feature_hash": feature_hash(),
                     "protocol_id": cfg.protocol_id, "scope": "OAT-partial-diagnostic"}
        _cpcv_cache_save("BADHASH", dict(base_cpcv, compat_hash="WRONG"))
        check("error_cpcv_wrong_hash_rejected", "cache nesli eski" in _cpcv_pbo_txt("BADHASH"))

        # Backtest ana kohortu H-adimli, proper skorlar sonlu, istisna nakit sayilmiyor.
        bt = _bt_walk_forward("TST", cs, cfg, limit_bars=80)
        check("normal_backtest_nonoverlap",
              bt["stride"] == cfg.horizon and bt["n_bar"] > 0 and
              all((t + 1) % period == 0 for t in bt["cohort_times"]))
        check("normal_backtest_metrics", bt["errors"] == 0 and math.isfinite(bt["brier"]) and
              math.isfinite(bt["logloss"]) and 0 <= bt["coverage"] <= 1 and
              set(bt["benchmarks"]) == {"no_change", "momentum", "past_majority"} and
              0 <= bt["balanced_accuracy"] <= 1)
        check("boundary_backtest_min_effective_gate",
              bt["effective_ok"] == (bt["n_bar"] >= cfg.backtest_min_effective))
        bt32 = _bt_walk_forward("TST32", cs,
                                replace(cfg, offline_nonoverlap_stride=32), limit_bars=100)
        gaps32 = [b - a for a, b in zip(bt32["cohort_times"], bt32["cohort_times"][1:])]
        check("boundary_backtest_configured_stride_honored",
              bt32["stride"] == 32 and len(gaps32) >= 1 and
              all(g == 32 * cfg.interval_ms for g in gaps32))

        # ── FABLE6_5 onarim regresyonlari (Anapront denetimi F1-F7; TDD: once RED) ──
        check("f3_scenario_market_engeli",
              scenario_market_engeli("SHORT", "LONG") and scenario_market_engeli("LONG", "SHORT")
              and not scenario_market_engeli("NEUTRAL", "LONG")
              and not scenario_market_engeli("LONG", "LONG")
              and not scenario_market_engeli(None, "SHORT"))
        _na1, _nr1 = _net_r(2.0, 0.5, 1.0)
        _na0, _nr0 = _net_r(1.0, None, 1.0)
        check("f4_net_r_matematigi",
              _na1 == 1.5 and _nr1 == 1.5 and _na0 is None and _nr0 is None)
        _cpcv_d = Decision("LONG", 60, 100.0, 106.0, 98.0, 3.0, .6, 20, False, "t", [], 0, [],
                           0.0, "NORMAL", .2, "", .2, -.1, {}, cost_abs=1.0)
        _cs_cp = [Candle(100, 100.5, 99.5, 100, close_ms=t0 + (i + 1) * cfg.interval_ms - 1)
                  for i in range(8)] + \
                 [Candle(100, 107, 99, 106, close_ms=t0 + 9 * cfg.interval_ms - 1)]
        _rr_cp = _cpcv_r_multiple(_cs_cp, 0, _cpcv_d, cfg.horizon)
        check("f4_cpcv_r_maliyet_dusuldu",
              _rr_cp is not None and abs(_rr_cp - (6.0 - 1.0) / 2.0) < 1e-9)
        _ra_f7, _rb_f7 = _aligned_returns(
            [Candle(100, 101, 99, 100 + i * 0.1, close_ms=1_700_000_000_000 + i * 900_000)
             for i in range(8)],
            [Candle(100, 101, 99, 100 + i * 0.1, close_ms=1_800_000_000_000 + i * 900_000)
             for i in range(8)])
        check("f7_hizalama_pozisyonel_fallback_yok", _ra_f7 == [] and _rb_f7 == [])
        _src_f1 = open(os.path.abspath(__file__), "r", encoding="utf-8").read()
        check("f1_argumansiz_loop_statik",
              "\n    elif not args:\n" in _src_f1
              and 'os.environ.get("YON_LOOP", "1") == "0"' in _src_f1)
        _v2p = {"plan_status": "WAITING", "long_trigger": 99.0, "short_trigger": 101.0,
                "long_invalidation": 97.0, "short_invalidation": 103.0,
                "long_stop": 97.0, "short_stop": 103.0,
                "long_target_1": 101.0, "short_target_1": 99.0}
        _s1, _ = _price_hits_plan_v2(_v2p, 98.9, reclaim_close=98.5)
        _v2p["plan_status"] = _s1
        _s2, _ = _price_hits_plan_v2(_v2p, 99.2, reclaim_close=99.5)
        check("f6_v2_dokunus_touched_geri_alis_triggered",
              _s1 == "TOUCHED" and _s2 == "TRIGGERED"
              and _v2p.get("triggered_side") == "LONG")

        # ── F10c REGRESYON: cagrilar-arasi holder kirlenmesi (canli DOGE<-SOL sizintisi) ──
        # LIVE erken-kapi (LATENCY/PIT/eksik-zaman) _decide_core'u atlar; onceki sembolun
        # _FC_HOLDER/_PLAN_HOLDER/_SCEN_YON_HOLDER degeri sizmamali (analyze d.fc=_FC_HOLDER
        # okur). Bir onceki sembol (SOL benzeri) holder'lari doldurur; latency-kapili sembol
        # (DOGE benzeri) BEKLE doner ve holder'lar SIFIRLANMIS olmali.
        _FC_HOLDER["v"] = {"price0": 77.15, "q10": 76.08, "q50": 77.12, "q90": 78.48,
                           "atr": 0.384, "dir": -1, "pup": 0.47, "h": 16}
        _PLAN_HOLDER["v"] = {"marker": "PREV_SYM"}
        _SCEN_YON_HOLDER["v"] = {"side": "SHORT", "cell": 42}
        _lat_cfg = Config()
        _origin = 1_784_051_999_999
        _late_cs = [Candle(0.0745, 0.0746, 0.0744, 0.0745, 1000.0, close_ms=_origin - 900_000),
                    Candle(0.0745, 0.0746, 0.0744, 0.0745, 1000.0, close_ms=_origin)]
        _late_pred = _origin + _lat_cfg.ledger_max_latency_ms + 600_000
        _late_snap = Snapshot("BBB", _late_cs, last_closed_ms=_origin,
                              predicted_at_ms=_late_pred, live_fetched_ms=_late_pred)
        _late_art = decide_with_artifacts(_late_snap, _lat_cfg, context=DecisionContext())
        check("f10c_latency_gate_fired",
              _late_art.decision.karar == "BEKLE"
              and "LATENCY" in (_late_art.decision.gate_code or ""))
        check("f10c_holderlar_onceki_sembolden_temiz",
              _FC_HOLDER.get("v") is None and _PLAN_HOLDER.get("v") is None
              and _SCEN_YON_HOLDER.get("v") is None and _late_art.fuel_cell is None)

        # ── PANEL (Sablon-2) REGRESYON: insan-okunur panel bolumleri var; TEKNIK denetim
        # jetonlari (PIT/HAM-ALAN/MARK-LIVE/STORE-DENETIM) EKRANDA YOK; render() ise o
        # yan-etkili satirlari HALA uretir (side-effect yolu bozulmadi) ve holder doldurur.
        _pan_cfg = Config(mc_paths=60, min_train=60, knn_k=20, bootstrap_reps=40)
        _pan_cs = _synthetic_candles(190, 606, 0.0004, 0.008)
        _pan_snap = Snapshot("PAN", _pan_cs, htf=_pan_cs[::16][-60:],
                             last_closed_ms=_pan_cs[-1].close_ms,
                             data_watermark_ms=_pan_cs[-1].close_ms)
        _pan_d = decide(_pan_snap, _pan_cfg, context=DecisionContext.offline(_pan_cs[-1].close_ms))
        _pan_d.fc = _FC_HOLDER.get("v"); _pan_d.plan = _PLAN_HOLDER.get("v")
        _pan_st = build_structure(_pan_snap.candles, _pan_cfg)
        _pan_txt = "\n".join(panel_karti("PAN", _pan_snap, _pan_st, _pan_d, _pan_cfg))
        check("panel_bolumleri_var",
              all(t in _pan_txt for t in ("KARAR", "DURUM", "TAHMİN", "PLAN")))
        check("panel_teknik_jeton_yok",
              not any(t in _pan_txt for t in
                      ("PIT predicted_at", "HAM-ALAN", "MARK/LIVE DENET", "STORE DENET",
                       "code=", "model=", "feature=")))
        _rnd_txt = render("PAN", _pan_snap, _pan_d, _pan_cfg)   # side-effect yolu bozulmadi mi
        check("render_teknik_yolu_korundu", "KARAR TABLOSU" in _rnd_txt)

        # ── S2/S3 regresyonlari ──
        # giris_zamanlama: uc dal (market / pusu / kenar-yok)
        _dz = Decision("SHORT", 55, 100.0, 96.0, 103.0, 1.3, 0.6, 20, False, "t", [], 0, [],
                       0.0, "NORMAL", 0.2, "", 0.2, -0.1, {})
        _stz = build_structure(cs, cfg)
        check("s2_giris_zamanlama_market",
              "SIMDI MARKET SHORT" in giris_zamanlama("Z", snap, _stz, _dz, cfg))
        _dzb = _wait("t"); _dzb.scen_side = "LONG"
        check("s2_giris_zamanlama_pusu",
              "PUSU bekle (LONG" in giris_zamanlama("Z", snap, _stz, _dzb, cfg))
        check("s2_giris_zamanlama_yok",
              "islem yok" in giris_zamanlama("Z", snap, _stz, _wait("t"), cfg))
        # ErkenUyari varsayilan + Decision.erken alani
        _eu0 = ErkenUyari()
        check("s3_erken_uyari_defaults",
              _eu0.risk_var is False and _eu0.tur == "YOK" and _eu0.yon_egilim == "NEUTRAL"
              and _eu0.kanitlar == [])
        check("s3_decision_erken_field", hasattr(Decision("BEKLE", 0, None, None, None, 0.0,
              0.0, 0, False, "t", [], 0, [], 0.0, "NORMAL", 0.0, "", 0.0, 0.0, {}), "erken"))
        # erken-uyari store R4-korumasi: okuma-hatasi bayragi iken dosya EZILMEZ
        _eu_old = os.environ.get("YON_ERKEN_UYARI_LOG")
        os.environ["YON_ERKEN_UYARI_LOG"] = os.path.join(tmp, "eu_guard.jsonl")
        try:
            globals()["_ERKEN_READ_FAIL"] = True
            _guard_ok = _erken_kaydet([{"x": 1}], cfg) is None and not os.path.exists(
                os.environ["YON_ERKEN_UYARI_LOG"])
            globals()["_ERKEN_READ_FAIL"] = False
        finally:
            if _eu_old is None:
                os.environ.pop("YON_ERKEN_UYARI_LOG", None)
            else:
                os.environ["YON_ERKEN_UYARI_LOG"] = _eu_old
        check("s3_erken_store_read_fail_guard", _guard_ok)

        passed = all(v for _, v in results)
        print(f"FABLE6 TESTS: {sum(v for _, v in results)}/{len(results)} "
              + ("PASSED" if passed else "FAILED"))
        return passed
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        _sh.rmtree(tmp, ignore_errors=True)



def fable5_tests():
    """Fable5 Step5 regresyon testleri: ag yok, gecici store."""
    import tempfile, os as _os, shutil as _shutil
    tmp = tempfile.mkdtemp(prefix="fable5_tests_")
    old_env = {k: _os.environ.get(k) for k in ("YON_PANEL_DIR", "YON_OPEN_SIGNAL_STORE", "YON_PLAN_STORE_V2")}
    _os.environ["YON_PANEL_DIR"] = tmp
    _os.environ.pop("YON_OPEN_SIGNAL_STORE", None)
    _os.environ.pop("YON_PLAN_STORE_V2", None)
    try:
        cfg = Config(mc_paths=20)
        cfg.mark_live_required_for_market = True
        now = _step49_now_ms()
        cs = [Candle(100, 101, 99, 100, close_ms=now - 900000), Candle(100, 102, 98, 100, close_ms=now - 1)]
        st = Structure(100.0, 1.0, 99.0, 101.0, [], [], True)
        def snap(px=100.0, live=True, book=True):
            return Snapshot("TST", cs, htf=cs, book={"spread":0.01, "spread_pct":0.0001, "bid":99.995, "ask":100.005} if book else None,
                            live_price=px if live else None, live_server_ms=now, live_fetched_ms=now, last_closed_ms=now-1, stale=False)
        def dec(side="BEKLE"):
            target = 98.0 if side == "SHORT" else 102.0
            stop = 101.0 if side == "SHORT" else 99.0
            return Decision(side, 60, 100.0, target, stop, 2.0, 0.6, 20, False, "test", [], 0, [], 0.0, "NORMAL", 0.2, "", 0.2, -0.1, {}, plan={"alt_bant":99.0,"ust_bant":101.0})
        results=[]
        def check(name, cond):
            results.append((name, bool(cond)))
            print(f"{name}: {'PASS' if cond else 'FAIL'}")
        # 1 açık plan yokken yeni plan
        r1 = step49_store_denetimi("TST", snap(), st, dec("BEKLE"), cfg)
        check("open_plan_yokken_create", r1["plan_action"] == "CREATE_NEW_PLAN" and r1.get("result_plan_id"))
        # 2 mevcut plan varken kor-kurulum yok
        r2 = step49_store_denetimi("TST", snap(), st, dec("BEKLE"), cfg)
        check("mevcut_waiting_plan_korunur", r2["existing_open_signal"] is True and r2["plan_action"] == "KEEP_EXISTING_PLAN")
        # market açık sinyal testleri için temiz store
        _open_signal_store_save({}) ; _plan_store_v2_save({})
        r3 = step49_store_denetimi("TST", snap(), st, dec("LONG"), cfg)
        r4 = step49_store_denetimi("TST", snap(), st, dec("LONG"), cfg)
        check("acik_long_ayni_yon_update", r4["plan_action"] == "UPDATE_EXISTING_PLAN")
        r5 = step49_store_denetimi("TST", snap(), st, dec("SHORT"), cfg)
        check("acik_long_varken_short_blok", r5["plan_action"] == "KEEP_EXISTING_PLAN")
        _open_signal_store_save({"TST:15m": dict(_candidate_open_signal("TST", snap(), st, dec("SHORT"), cfg))}) ; _plan_store_v2_save({})
        r6 = step49_store_denetimi("TST", snap(), st, dec("LONG"), cfg)
        check("acik_short_varken_long_blok", r6["plan_action"] == "KEEP_EXISTING_PLAN")
        # 5 pusu tetiklenme (F6/FABLE6_5: salt dokunus=TOUCHED; TRIGGERED ancak kapanmis
        # mumun geri-alisiyla — legacy _plan_degerlendir sozlesmesiyle esitlendi)
        _open_signal_store_save({}) ; _plan_store_v2_save({})
        step49_store_denetimi("TST", snap(100.0), st, dec("BEKLE"), cfg)
        r7 = step49_store_denetimi("TST", snap(98.9), st, dec("BEKLE"), cfg)
        check("pusu_igne_touched", r7["existing_status"] == "WAITING" and _plan_store_v2_load()["TST:15m"]["plan_status"] == "TOUCHED")
        r7b = step49_store_denetimi("TST", snap(99.6), st, dec("BEKLE"), cfg)
        check("pusu_geri_alis_tetikler", _plan_store_v2_load()["TST:15m"]["plan_status"] == "TRIGGERED"
              and _plan_store_v2_load()["TST:15m"].get("triggered_side") == "LONG")
        # 6 stop/invalidation ile kapanış
        plans=_plan_store_v2_load(); plans["TST:15m"]["plan_status"]="TRIGGERED"; plans["TST:15m"]["triggered_side"]="LONG"; _plan_store_v2_save(plans)
        r8 = step49_store_denetimi("TST", snap(98.6), st, dec("BEKLE"), cfg)
        check("stop_invalidation_close", _plan_store_v2_load()["TST:15m"]["plan_status"] == "CLOSED")
        # 7 eksik veri => candidate yok / DATA_INSUFFICIENT benzeri koruma
        bad_st = Structure(100.0, 0.0, 99.0, 101.0, [], [], False)
        _open_signal_store_save({}) ; _plan_store_v2_save({})
        r9 = step49_store_denetimi("TST", snap(), bad_st, dec("BEKLE"), cfg)
        check("eksik_veri_plan_uretmez", r9["updated_plan_store"] is False)
        # 8 live olmayan veriyle market emir kaydedilmez
        _open_signal_store_save({}) ; _plan_store_v2_save({})
        r10 = step49_store_denetimi("TST", snap(live=False), st, dec("LONG"), cfg)
        check("live_olmayan_market_engel", not _open_signal_store_load())
        # Ek: mark freshness bar yasi degil ve spread okunur
        a = mark_live_denetime("TST", snap(), st, cfg)
        check("mark_freshness_bar_yasi_degildir", a["data_freshness_seconds"] <= 2 and a["last_closed_bar_age_seconds"] is not None)
        check("spread_unknown_degildir", a["spread"] == 0.01)
        ok = all(v for _, v in results)
        print(f"FABLE5 UYUMLULUK TESTLERI: {sum(v for _, v in results)}/{len(results)} PASSED"
              if ok else "FABLE5 UYUMLULUK TESTLERI FAILED")
        return ok
    finally:
        for k, v in old_env.items():
            if v is None:
                _os.environ.pop(k, None)
            else:
                _os.environ[k] = v
        try:
            _shutil.rmtree(tmp)
        except Exception:
            pass

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    low = [a.lower() for a in args]
    if args and low[0] in ("fable6test", "fable6_tests", "test"):
        sys.exit(0 if fable6_tests() else 1)
    if args and low[0] in ("yontemtest", "yontem", "yontem_tests"):
        sys.exit(0 if yontem_tests() else 1)
    if args and low[0] in ("kirmizitest", "redtest", "kirmizi"):
        rest = [a for a in args[1:] if a]
        fastk = any(a.lower() == "fast" for a in rest)
        hedefk = next((a for a in rest if a.lower() != "fast"), "sentetik")
        sys.exit(0 if kirmizi_test(hedefk, fast=fastk) else 1)
    if args and low[0] in ("fable5test", "fable5_tests", "step5test"):
        sys.exit(0 if fable5_tests() else 1)
    if args and low[0] in ("pydroid", "pydroidkanit", "kurulum", "install"): 
        sys.exit(0 if pydroid_step4_kanit(full=False) else 1)
    elif args and low[0] in ("pydroidfull", "pydroidtam", "tamkanit"): 
        sys.exit(0 if pydroid_step4_kanit(full=True) else 1)
    elif args and low[0] == "selftest":
        # Bug 10: selftest artik int doner (0=PASS,1=INVARIANT_FAIL,2=INCONCLUSIVE);
        # CI'da 1 ve 2 fail sayilir. Eski bool donuse karsi da guvenli.
        _st_res = selftest()
        sys.exit(int(_st_res) if isinstance(_st_res, int) else (0 if _st_res else 1))
    elif args and low[0] == "btselfcheck":
        bt_selfcheck()
    elif args and low[0] == "mutasyon":
        sys.exit(0 if mutasyon_testi() else 1)
    elif args and low[0] == "cpcv":
        rest = [a for a in args[1:] if a]
        fastc = any(a.lower() == "fast" for a in rest)
        hedef = next((a for a in rest if a.lower() != "fast"), "sentetik")
        run_cpcv(hedef, fast=fastc)
    elif args and low[0] == "backtest":
        rest = args[1:]
        rlow = [a.lower() for a in rest]
        fast = "fast" in rlow
        nums = [int(a) for a in rest if a.isdigit()]
        syms = [a for a in rest if not a.isdigit() and a.lower() != "fast"]
        run_backtest(syms if syms else SYMBOLS,
                     limit_bars=(nums[0] if nums else None), fast=fast)
    elif args and low[0] == "analiz":
        syms = [a.upper() for a in args[1:] if a] or None
        print(analiz_metni(syms))
    elif "loop" in low or "--loop" in low:
        syms = [a for a in args if a.lower() not in ("loop", "--loop")]
        run_loop(syms if syms else SYMBOLS)
    elif not args:
        # F1 (FABLE6_5): ARGUMANSIZ VARSAYILAN = SUREKLI MOD — telefon/Pydroid'de tek
        # dokunusla 15m kapanisina hizali loop (kullanici sozlesmesi: "argumansiz
        # baslatildiginda surekli calismali"). Eski tek-atim: YON_LOOP=0.
        if os.environ.get("YON_LOOP", "1") == "0":
            run(SYMBOLS)
        else:
            run_loop(SYMBOLS)
    else:
        # ── REPORT_4 #4: BILINMEYEN-KOMUT BEKCISI (fail-closed) ──
        # Eski davranis: her taninmayan ilk arguman (or. 'sefltest' yazim hatasi)
        # SESSIZCE canli Binance veri yoluna dusuyordu. Simdi canli run() yalniz
        # (a) argumansiz cagri (belgelenmis varsayilan) veya (b) sembol GIBI gorunen
        # argumanlarla acilir: 'usdt' ile biten YA DA kullanicinin BUYUK harfle
        # yazdigi alfasayisal ad (BTCUSDT, ETHBTC, 1000PEPEUSDT...). Kucuk-harf
        # komut yazim hatalari kullanim metni + exit 2 alir; canli yol acilmaz.
        def _sembol_gibi(a: str) -> bool:
            return a.lower().endswith("usdt") or (a.isupper() and a.isalnum())
        _taninmayan = [a for a in args if not _sembol_gibi(a)]
        if _taninmayan:
            sys.stderr.write(
                "BILINMEYEN KOMUT/ARGUMAN: " + " ".join(_taninmayan[:4]) + "\n"
                "Canli veri yolu SESSIZCE acilmaz (REPORT_4 #4 korumasi).\n"
                "Komutlar: fable6test | fable5test | pydroid | pydroidfull | selftest | "
                "btselfcheck | mutasyon | cpcv | backtest | analiz | loop\n"
                "Canli analiz icin sembol verin (or. BTCUSDT; tek-atim) veya argumansiz\n"
                "calistirin (F1: argumansiz = 15m'e hizali SUREKLI mod; tek-atim YON_LOOP=0).\n")
            sys.exit(2)
        run(args)
