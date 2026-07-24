---
name: piramit-sistem
description: >-
  Piramit sistemi — depodaki BÜTÜN motorları piramidin en altından (LLM) en
  üstüne (SI) tırmandıran tek çalışan orkestratör. Bir soru nihai karar, tam
  analiz, "bütün becerileri çalıştır", "piramidi koştur", "en alttan en üste",
  çok katmanlı değerlendirme, tam boru hattı ya da 15M+4H kline + türev paneli
  birlikte değerlendirme gerektirdiğinde OTOMATİK devreye girer — slash komutu
  gerekmez. Katmanlar: K1 LLM (ham veri + bütünlük) → K2 AI AJAN (tek ajan +
  araç) → K3 ÇOKLU-AJAN (danışman kurulu) → K4 AGI (çelişki + fail-closed
  doğrulama + şişirilmiş-R + 5 mercek) → K5 SI (güven-ağırlıklı sentez, SONRA
  geçmiş akıbetten kendini kalibre eden geri besleme). Çalışan motor:
  scripts/piramit.py (subprocess ile gerçek motor çağrıları; öz-test:
  scripts/self_test.py). Tetikleyici kelimeler (TR/EN): piramit, katman, tam
  analiz, bütün motorlar, hepsini çalıştır, en alttan en üste, zirve, SI, AGI,
  çoklu ajan, multi-agent, orkestrasyon, pipeline, full stack karar.
  ⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.
---

# Piramit Sistemi — LLM → AI AJAN → ÇOKLU-AJAN → AGI → SI

Depodaki 25 motoru **tek koşuda, sırayla ve kapılı** çalıştırır. Piramidin
**en altından başlar, en üstüne çıkar.** Her katman bir öncekinin *veremediği*
bilgiyi ekler; eklemiyorsa katman değildir (kutu tiyatrosu yasak).

```
            ┌─────────┐
            │   SI    │  K5  sentez (güven-ağırlıklı)  →  SONRA kalibrasyon
            ├─────────┤      geri beslemesi (agirlik.json → sonraki koşu)
            │   AGI   │  K4  çelişki + fail-closed doğrulama + şişirilmiş-R
            ├─────────┤      + 5 danışman merceği (her biri bir motora bağlı)
            │Çoklu-Aj.│  K3  motorlar → danışman kurulu (ağırlıklı güven)
            ├─────────┤
            │ AI AJAN │  K2  tek ajan + ARAÇ: her motor birbirini görmeden koşar
            ├─────────┤
            │   LLM   │  K1  ham veri + bütünlük denetimi (çıkarım YOK)
            └─────────┘
```

## Çalıştırma

```bash
python .claude/skills/piramit-sistem/scripts/piramit.py \
    --job ornek/ornek_job.json --out rapor.json --ozet
```

Öz-test (7 iddia, 7 kanıt):

```bash
python .claude/skills/piramit-sistem/scripts/self_test.py
```

## Job şeması

```json
{
  "soru": "BTCUSDT — nihai yön ve işlem kalitesi?",
  "sembol": "BTCUSDT",
  "veri": {
    "m15": "engine/girdi/m15.json",      // karar-motoru + SMC girdisi
    "h4":  "engine/girdi/h4.json",       // 4H bağlam
    "ohlcv_csv": null,                   // ops. (m15 yerine tablo kaynağı)
    "turev": { "price_series": [...], "oi_series": [...], "funding": 0.0025,
               "cvd_series": [...], "taker_lsr": 0.79,
               "liq_long": 1.0, "liq_short": 8.6 },   // ops. CoinGlass paneli
    "video": null,                       // ops. → kareler çıkarılır (okuma ELLE)
    "veri_sozlesmesi": null,             // ops. verify_data.py sözleşmesi
    "returns_csv": null                  // ops. portföy getirileri
  },
  "backtest": { "input": "...", "strategy": {...}, "dogrular": "grafik-calisma" },
  "risk":     { "op": "position_size", "method": "fixed_fractional",
                "equity": 10000, "risk_pct": 1.0, "seviye_kaynagi": "karar-motoru" },
  "portfoy":  { "op": "optimize", "returns_csv": "...", "method": "hrp" },
  "mercekler": { "muhalif": {"motor": "turev-akis", "not": "..."} },  // ops. elle bağlama
  "state_dir": "engine/state"            // karar-motoru hafızası (gerçek defter)
}
```

## Katmanlar, kapıları ve hangi beceriyi koştururlar

| Katman | Koşan beceri/motor | Kapı (fail-closed) |
|---|---|---|
| **K1 LLM** | `data-analysis-deep-scan` (`profile_data`/`verify_data`), `video-isleme`, kline parser (`engine/karar_motoru.parse_klines`) | (m15+h4) veya ohlcv_csv okunmalı — yoksa **üst katman koşmaz** |
| **K2 AI AJAN** | `karar-motoru`, `grafik-calisma` (`smc_tespit`→`confluence`, `setup_dogrulama`), `turev-akis`, `backtest-motoru` | ≥2 motor **gerçek sayısal** sonuç üretmeli — tek motor çoklu-ajan değildir |
| **K3 ÇOKLU-AJAN** | motorlar → `karar-kurulu` danışman şeması; güven × K5 ağırlığı | ≥2 danışman |
| **K4 AGI** | `karar-kurulu/rr_denetim`, `setup_dogrulama` (doğrulayıcı), `uzman-modu` 5 merceği, `forex-trading-expert` (SMC referansı) | bilgi katmanı: bulguları K5'e taşır, kararı bastırmaz |
| **K5 SI** | `karar-kurulu/sentez.py` → `risk-yonetimi` → `portfoy-optimizasyonu` → `grafik-calisma/kalibrasyon.wilson_lo` | sentez üretilmeli; üretilemezse **NÖTR-BEKLE** |

## K5 = SI: önce sentez, sonra kendini kalibre etme

1. **(a) Sentez** — `sentez.py` güven-ağırlıklı tek karar üretir (çoğunluk oyu
   değil). Çıktı **iki satır**: `YÖN (bias)` + `İŞLEM KALİTESİ`.
2. **(b) Geri besleme** — geçmiş kararların **ölçülmüş** akıbeti okunur
   (`defter.jsonl` → `gercek_r`), Wilson alt sınırıyla motor ağırlığı türetilir:

   ```
   agirlik = clamp(2 × wilson_lo(kazanan, n), 0.40, 1.00)
   n < n_taban (kalibrasyon.py = 10)  →  agirlik 1.0 (DEĞİŞTİRİLMEZ)
   ```

   `wilson_lo = 0.50` (yazı-tura alt sınırı) → ağırlık `1.00` (nötr). Ağırlıklar
   `state/agirlik.json`'a yazılır ve **bir sonraki koşunun K3 katmanında**
   uygulanır. Döngü böyle kapanır: karar → akıbet → ağırlık → daha iyi karar.

   **Fail-closed:** ölçülmemiş (`gercek_r` yok) satır istatistiğe **girmez**;
   kanıt yoksa "öğrendim" iddiası üretilmez.

## İki satır (CLAUDE.md sözleşmesi)

- **YÖN (bias):** `YON_BIAS` — ağırlıklı kanıtın yönü, kapıdan bağımsız.
  Motor BEKLE dese bile yön **açıkça** söylenir.
- **İŞLEM KALİTESİ:** dört koşulun hepsi gerekir — (1) YÖN ile hizalı, motordan
  okunan giriş/stop/hedef, (2) `rr_denetim` = TUTARLI, (3) `R_gercekci ≥ 1.35`,
  (4) doğrulama çürütülmemiş. Eksikse hüküm **"TEMİZ GİRİŞ YOK"** + hangi
  koşulun düştüğü tek tek yazılır.

## Doğruluk sözleşmesi

- Her sayı bir motorun **dosyadan okunan** çıktısıdır; boru hattı sayı üretmez.
- Kalibre edilemeyen her sabit `varsayimlar` defterine yazılır (gizli eşik yok).
- Eksik alan `VERİ YOK`; eksik veriyle üst katman **koşmaz**.
- Determinist: rastgelelik ve duvar-saati yok (zaman damgası veriden).
- 5 mercek **kanıta bağlanır**; bağlanamayan mercek `BAĞLANMADI` işaretlenir —
  anlatı için sayı uydurulmaz.

⚠️ Yalnız karar-destek. Canlı/otomatik emir (gerçek para) **DAHİL DEĞİL**.
