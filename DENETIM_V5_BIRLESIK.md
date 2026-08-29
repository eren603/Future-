# DENETİM — `Claud_gllm_codellm_trading_v5_birlesik.py`

Tarih: 2026-08-29 · Yöntem: 13 kronolojik/çapraz dilim + **mekanik repro doğrulaması**
Yayın kapısı: `KONSEY_ALL_IN_ONE.py audit` → **PUBLISH_FULL (exit 0)**, 17/17 kritik iddia kanıtlı
Kanıt defteri: `v5/DENETIM_konsey_gorev.json` (3 kaynak, 21 kanıt, 19 iddia)

⚠️ Kod denetimidir; piyasa yönü/işlem hükmü DEĞİLDİR.

## YÖNTEM NOTU — önceki koşu neden çöktü, bu koşu neden çökmedi

İlk kronolojik koşu 174 bulgu × 3 LLM doğrulayıcı = 536 ajanla oturum limitine çarptı;
**doğrulayıcıların tamamı ve final sentez düştü**. `elenen=174 / doğrulanan=0` sonucu
"çürütüldü" DEĞİL "doğrulanamadı" idi (146'sı sıfır oy). Bu koşuda LLM oy katmanı
tamamen kaldırıldı: 13 dilim + 1 birleştirici = 14 ajan, ve **her bulgu çalıştırılabilir
repro kodu taşımak zorunda** kılındı. **70 bulgunun 70'inin reprosu denetçi tarafından
koşturuldu, hepsi exit=0.** Doğrulama artık oy değil, koşum.

---

## P0 — TESLİMİ MÜHÜRLEYEN DÖRT BULGU

### P0-1 · Motor kendi kenarını üretiyor (bar-içi sıra varsayımı)
`_yaris_coz` 3326 + 3333-3344: yön atandıktan sonra `continue` yok → **limitin dolduğu
barın KENDİ fitili HEDEF sayılıyor**. LONG'da dolum barın dibinde, hedef yukarıda;
aynı barın tepesi hedefi görürse kazanç yazılıyor — oysa dip/tepe sırası bilinmiyor.
Stop tarafı bu asimetriden etkilenmiyor.

Sürüklenmesiz (kenar = 0) rassal yürüyüşte, gerçek tick yolu bilinerek:

| tohum | MOTOR | GERÇEK tick yolu |
|---|---|---|
| 7 | edge +0.0086 · **KAPI AÇIK** · stake 0.59% | edge −0.0522 · kapalı |
| 23 | edge +0.0598 · **KAPI AÇIK** · stake 4.09% | edge −0.0686 · kapalı |
| 42 | edge +0.0252 · **KAPI AÇIK** · stake 1.72% | edge −0.1646 · kapalı |
| 99 | edge +0.1663 · **KAPI AÇIK** · stake 11.37% | edge −0.0469 · kapalı |

4/4 tohumda kenarı OLMAYAN veride kapı AÇILIYOR. Denetçinin bağımsız 30-turluk ölçümü:
artefakt **+0.0993R**, +54 fazla HEDEF (%9.2) — canlı iddia edilen +0.2586R'nin %38'i.
**T2 zehir testi bunu yakalayamaz** (bak-ileri değil, bar-içi sıra); T3 de yakalayamadı
(tekdüze kayıp trendi kullanıyor).
→ Düzeltme: yön atandıktan sonra `j += 1; continue`; dolum barında yalnız stop kontrolü.

### P0-2 · OKX gövde hata kodu yutuluyor → 4H hizalaması LOOK-AHEAD'e dönüyor
`okx_uyumlu_getir` 3270-3275: iç sayfada `code` kontrolü YOK (ilk sayfada var, 3258-3262).
Docstring "code != '0' → kanal None düşer, uydurma YOK" diyor; iç sayfada düşmüyor.

| senaryo | 15M | 4H | düşen kanal | kapsam | gelecekten 4H okuyan 15M bar |
|---|---|---|---|---|---|
| hatasız | 4000 | 1200 | — | 1.00 | 0 (%0) |
| 2. iç sayfada `code=50011` | 4000 | **100** | **[]** | **1.00** | **3999 (%100), azami 604 saat** |

Tek geçici hız-sınırı hatası 4H serisini sessizce kırpıyor, kapsam yine 1.00 raporlanıyor
ve v4'ün indeks-tabanlı hizalaması **604 saat ileriden** veri okumaya başlıyor.

### P0-3 · FADE stake'i TEK BAHİS (korelasyon) kapısına hiç girmiyor
`3537-3539 / 3554-3557 / 3573-3575` — `portyof_karari` YALNIZ `k['karar']['stake']['f']`
okur; FADE stake'i o alana hiç yazılmaz. Ölçülen koşu:

```
PORTFÖY HÜKMÜ (ana sınıf f*): POZİSYON YOK
  ETHUSDT  rho=0.9851 >= 0.85  ->  KOPYA - ATLA
AYNI KOŞUDA AÇIK FADE BAHSİ : 2 sembol x 13.33% = 26.67% sermaye-riski
v4 kaynağında 'fade' geçişi          : 0
v5 kaynağında 'rho|korelasyon|TEK_BAHIS' : 0
```
Portföy "pozisyon yok" derken iki korelasyonlu FADE bahsi sermayenin **%26.67'sini**
riske atıyor. STRATEJI.md §1 "Tek bahis kuralı" doğrudan ihlal — iki sistem birbirini
tanımıyor.

### P0-4 · 4H/15M oranı 3.11, v4 sözleşmesi 16:1 → karar barı 173 GÜN bayat
v5 `hedef_i = 1200 (4H) / 4000 (15M)` (3263-3264) · v4 `_h4_hizala` indeks eşlemesi
16:1 varsayar (v4:2021-2028).
```
n15=4000 n4h=1288 oran=3.11   (v4 sözleşmesi: 16.00)
karar barı t=1699992000000 -> esl[-1]=249 -> kullanılan 4H t=1685044800000
DOĞRU 4H idx=1287                        -> SAPMA_GÜN = 173.0
```
Karar barının 4H öznitelik satırı **173 gün eski**. P0-2 ile birlikte: normalde bayat,
hata yutulunca gelecekten.

---

## P1 — 32 bulgu (hepsinin reprosu koştu). Öne çıkanlar

| Bulgu | Ölçülen |
|---|---|
| `kazan=0` iken `b_win` derleme-zamanı sabiti `R_FADE=1.5`'e düşüyor, kapı `p_hat=0.000` ile açılıyor | stake %6.67 |
| `stake=edge/b_win` kaybı 1.0R sayıyor; motorun kendi `net_r`'sinde STOP = **−1.1240R** | taban şişme ≥%9.3, ölçülen %15.1 |
| **Aynı koşuda aynı sembol için İKİ FARKLI stake** basılıyor | FADE_BLOK %10.62 vs DURUM ÖZETİ %5.03 |
| Öz-test FADE motorunun **TEK yolunu** koşuyor: 217 yarışın 217'si SHORT/STOP | HEDEF, ZAMAN, LONG hiç sınanmıyor |
| T8 kendi "8/8" iddiasını sınamıyor (`len(vaka) > 0` yeterli) | 7 test kaybolsa da PASS |
| Ağsız koşuda T2/T7/T9 sessizce düşüyor, `ATLANDI` satırı yok | basılan 14 satırın tamamı PASS |
| `--self-test` FAIL varken bile exit 0 | doğrulama kapısı sahte |
| `h2_barlar` sayfalamada tur sınırı yok → tekrarlı sayfada sonsuz döngü | kardeş sayfalayıcıda koruma VAR |
| `h2_barlar` kısmi çekimde BAYAT AMA TAM önbelleği SİLİYOR | 0 barı "canlı-çekim" diye dönüyor |
| oi/taker kanalları 8 sayfada tıkanıyor | istenenin %27.8'i geliyor |
| `fade_blok` SHORT tarafında hedef/stop işaretlerini TERS basıyor (`if True` ölü koşul) | raporlama hatası |
| SARMALAYICI'da v4 bütünlük kapısı YOK | CWD'deki herhangi bir v4 sessizce çalışır |
| İlk sembol düşerse ANA sembol sessizce kayıyor | korelasyon çapası değişir |
| `getir_fn` enjeksiyonu uçtan uca değil | 2H/FADE varsayılan ağ yoluna kaçıyor |
| v5 index 9'a `hacim/2` yazıyor, v4 bunu GERÇEK ölçüm sayıp CVD hesaplıyor; `v=0` → **−1.0** | maksimum ayı sinyali |
| funding işareti `abs()` ile kaynakta yok ediliyor | rejim filtresi türetilemez |

**P2:** 34 bulgu (ölü kod, beyan-kod ayrışması, sessiz yutma) — hepsi repro koştu.

---

## SAĞLAM ÇIKANLAR (pozitif, kanıtlı)

- Gömülü v4 = disk v4 **birebir**: `len=216129 karakter`, `md5=45e9f485d0db62aa9529a813ff502c6e`,
  bütünlük kapısı kendi sözleşmesiyle tutarlı, fail-closed.
- v5 katmanlarında **emir/imza/API-anahtar ucu YOK** (api_key/apiKey/secret/signature/hmac/
  /api/v5/trade/private → 0 eşleşme). Tek yazma: önbellek.
- Uydurma sabit yok: rapordaki `17.81/0.2586/238.3/77631/80726` kodda sıfır eşleşme.
- Limit rekonstrüksiyonu birebir: (77631.6+80726.2)/2=79178.90, yarı-genişlik 1547.30,
  `E_K=2` ⇒ ATR=773.65 → `c ± E_K×ATR` tutuyor.

## ÖLÇÜLEMEYEN (VERİ YOK — uydurulmadı)

- `E25/E26/E22/S14/S16` deney raporları depoda **yok** → `E_K=2.0/T_K=1.5/S_K=1.0`'ın
  "ÖLÇÜLEN" etiketi dayanaksız.
- `+238.3R, n=1092, GA[157.3,320.8]` bu boru hattında ne hesaplanıyor ne sabit olarak var.
- Canlı OKX yolu koşmadı (`Tunnel connection failed: 403`).

## DENETÇİ HATASI (dürüstlük izi)

`C10`'un ilk reprosu `V4_LEN`'i **bayt** sanıp diskin bayt uzunluğuyla karşılaştırdı ve
yanlışlıkla FAIL verdi. Kapı kodu (3100-3102) `V4_LEN`'i **karakter** tanımlıyor;
82 fark UTF-8 çoklu bayttan. Hata denetçideydi, kodda değil. (`C11`)
Ayrıca ilk turda "`fade_karar` ATR'yi koşulsuz kullanıyor" iddiası **çürütüldü** —
`kn = {...} if atr else None` koruması var (3416).

## HÜKÜM

Kod doğru üretilmiş (bütünlük, güvenlik, uydurma-sayı temizliği kanıtlı) ama **ölçüm ve
risk katmanında dört P0 var ve üçü karara/sermayeye doğrudan giriyor**: motor kenarını
kendi üretiyor, sessiz veri kırpması look-ahead'e dönüyor, FADE riski tek-bahis kapısını
atlıyor, 4H hizalaması 173 gün kayık. Bu haliyle **ne CI kapısı ne canlı boyutlandırma
kaynağı olabilir**.
