# KİMİ KONSOL — Kurulum (adım adım, kopyala-yapıştır)

## YOL 0 — KURULUMSUZ (sadece tarayıcı, önerilen) ⭐

Hiçbir şey kurma. Telefonun tarayıcısında şu linki aç:

**https://raw.githack.com/eren603/Future-/claude/new-session-wtmu3n/kimi_web.html**

1. Üstteki kutuya Kimi anahtarını yapıştır → **Kaydet**
2. Soruyu yaz → **Sor** → tez ↔ antitez ↔ savunma → HÜKÜM → NİHAİ KARAR (motor)

Link açılmazsa yedek: şu adresi aç, sayfayı **indir**, Dosyalar'dan aça:
`https://raw.githubusercontent.com/eren603/Future-/claude/new-session-wtmu3n/kimi_web.html`

Not: Motor kararları depodaki SON koşudan gelir (sayfa kendisi koşu yapamaz).
Kimi'nin ucu tarayıcı çağrısına (CORS) izin vermezse sayfa bunu açıkça söyler —
o durumda YOL A/B gerekir.

---

Bu sayfa, claude.ai sohbetinin yerine geçen **Kimi Konsol**'u çalıştırmak
içindir. Konsol; kimi-k3 (tez) ↔ kimi-code (antitez) tartıştırır ve en altta
**motorun bağlayıcı kararını** (YÖN + İŞLEM KALİTESİ + EMİR) gösterir.

---

## 0) Kimi API anahtarı al (bir kez)

1. Tarayıcıda aç: **https://platform.moonshot.ai**
2. Kayıt ol / giriş yap → soldan **API Keys** → **Create API Key**
3. `sk-...` ile başlayan anahtarı kopyala (birazdan tarayıcıya yapıştıracaksın)

---

## YOL A — SADECE TELEFON (bilgisayar gerekmez, Termux ile)

1. **Termux** uygulamasını kur → https://f-droid.org/packages/com.termux/
   (Play Store'daki eski; F-Droid sürümünü kur)

2. Termux'u aç, aşağıdaki satırları SIRAYLA yapıştır (her satırdan sonra Enter):

```bash
pkg update -y
pkg install -y python git
git clone -b claude/new-session-wtmu3n https://github.com/eren603/Future-.git
cd Future-
python kimi_konsol.py
```

3. Ekranda `KİMİ KONSOL → http://127.0.0.1:8787` yazınca **Termux'u
   KAPATMADAN** telefonun tarayıcısına geç ve şunu aç:

```
http://127.0.0.1:8787
```

4. Sayfanın üstündeki kutuya **Kimi anahtarını** yapıştır → **Anahtarı Kaydet**
5. Soru kutusuna yaz (örn. `karar nedir, giriş çıkış ver`) → **Sor**

> Durdurmak: Termux'ta `Ctrl+C`. Tekrar başlatmak:
> `cd Future- && python kimi_konsol.py`
>
> Güncel dalı çekmek: `cd Future- && git pull`
>
> "Koşuyu Yenile" (motorları telefonda çalıştırmak) istersen ek paketler:
> `pkg install -y python-numpy python-scipy && pip install pandas`
> Kurmazsan konsol bunu açıkça söyler; son kayıtlı motor kararını gösterir,
> uydurmaz.

---

## YOL B — BİLGİSAYAR + TELEFON (aynı Wi-Fi)

Bilgisayarda (Python 3 kurulu olmalı):

```bash
git clone -b claude/new-session-wtmu3n https://github.com/eren603/Future-.git
cd Future-
KIMI_KONSOL_HOST=0.0.0.0 python3 kimi_konsol.py
```

Bilgisayarın yerel IP'sini öğren:
- Windows: `ipconfig` → "IPv4 Address" (örn. 192.168.1.34)
- Linux/Mac: `ip addr` ya da `ifconfig`

Telefonda aç (127.0.0.1 DEĞİL, bilgisayarın IP'si):

```
http://192.168.1.34:8787
```

---

## Sayfada ne göreceksin (sırayla)

| Kart | Ne |
|---|---|
| 🟦 Durum kartları | Son koşunun YÖN / EMİR / gözlemci özeti (motor dosyalarından) |
| sen | Sorun |
| 🟩 kimi-k3 · tez | Ölçümlere dayalı cevap |
| 🟥 kimi-code · antitez | Tezi çürütme denemesi |
| 🟩 kimi-k3 · savunma | Kapanış |
| 🟨 HÜKÜM | UZLAŞI / KISMİ AYRIŞMA / ÇELİŞKİ (mekanik) |
| 🟦 NİHAİ KARAR (motor — bağlayıcı) | `YÖN + İŞLEM KALİTESİ + EMİR` — LLM değil, motor yazar |
| 🟥 KAYNAKSIZ SAYI | Kimi rapora dayanmayan sayı söylerse burada ifşa edilir |

## Kurallar (değişmedi)

- Kimi'ler **seviye/emir üretemez** — bağlayıcı emir daima motordan.
- Anahtar yalnız **senin tarayıcında** durur; sunucu diske yazmaz, depoya girmez.
- Anahtar/ağ yoksa: LLM bölümü `VERİ YOK`, motor kararı yine gelir (fail-closed).
- Konsol **görüntü okuyamaz** — CoinGlass panelleri veri paketiyle/elle girilir.
- ⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.

## Sorun giderme

| Belirti | Sebep / Çözüm |
|---|---|
| `Bu siteye ulaşılamıyor / ERR_CONNECTION_REFUSED` | Sunucu ÇALIŞMIYOR. Önce Termux'ta `python kimi_konsol.py` başlat, terminali kapatma. |
| Telefondan PC'ye bağlanamıyorum | `KIMI_KONSOL_HOST=0.0.0.0` ile başlattın mı? Aynı Wi-Fi'da mısın? PC güvenlik duvarı 8787'yi açık mı? |
| `HTTP 401/403` hata kartı | Anahtar yanlış/bitmiş → platform.moonshot.ai'dan yenisini al |
| `ağ: URLError` hata kartı | İnternet yok ya da Moonshot'a erişim engelli |
| BTC/ETH kartı "VERİ YOK" | `git pull` yap — son motor raporları depoda |
