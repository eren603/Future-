# Ham türev yanıtları — tarayıcıdan yapıştırma

Ağ politikası `fapi.binance.com`'u kapattığı için bu kanallar otomatik
çekilemiyor. Adresi tarayıcıda açıp **JSON'un tamamını** aşağıdaki dosyaya
yapıştırmak yeterli; kanca bir sonraki istemde kendiliğinden okur.

| Dosya | Tarayıcıda açılacak adres |
|---|---|
| `openInterestHist.json` | `https://fapi.binance.com/futures/data/openInterestHist?symbol=BTCUSDT&period=15m&limit=48` |
| `premiumIndex.json` | `https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT` |
| `takerlongshortRatio.json` | `https://fapi.binance.com/futures/data/takerlongshortRatio?symbol=BTCUSDT&period=15m&limit=48` |
| `likidasyon.json` | REST ucu YOK — CoinGlass panelinden okunan değerler: `{"liq_long": 1.0, "liq_short": 8.6}` ($M) |

Kurallar:
- Sembol **BTCUSDT** olmalı; farklı sembol yanıtı REDDEDİLİR (karara giremez).
- Biçim API'nin kendisidir — düzenleme/kırpma yapmayın, olduğu gibi yapıştırın.
- Kline'ın son barından ±2 saatten uzak veri `[VARSAYIM] eşzamanlı değil`
  uyarısıyla işaretlenir.
- Dosya yoksa o kanal `VERİ YOK` kalır — **uydurulmaz** (fail-closed).
