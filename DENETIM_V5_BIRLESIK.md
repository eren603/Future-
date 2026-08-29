# DENETİM — `Claud_gllm_codellm_trading_v5_birlesik.py` (v5 birleşik)

Tarih: 2026-08-29 · Kapsam: birleşik dosya + sarmalayıcı + gömülü v4 karşılaştırması
Yöntem: iki çok-ajanlı denetim koşusu + **elle ikinci-göz** (her ağır bulgu bu oturumda
yeniden üretildi). ⚠️ Kod denetimidir; piyasa yönü/işlem hükmü DEĞİLDİR.

## HÜKÜM

Kod **doğru üretilmiş** (gömülü v4 = disk v4 birebir, md5 kapısı fail-closed, uydurma
sabit yok, emir/anahtar ucu yok) ama **ölçüm katmanında bir tanesi kararı çeviren
üç sessiz yanlış** var. Bu haliyle ne CI kapısı ne canlı boyutlandırma kaynağı olabilir.

## P0-1 — BAR-İÇİ SIRA VARSAYIMI KENDİ KENARINI ÜRETİYOR  ⛔

`_yaris_coz` (3327-3339): yön atandıktan sonra `continue` **YOK**. Akış doğrudan
**limitin dolduğu barın KENDİ `h`/`l`'siyle** hedef/stop kontrolüne düşer. LONG'da
dolum barın DİBİNDE (`alt`), hedef YUKARIDA — aynı barın tepesi hedefi görürse HEDEF
yazılıyor. Oysa dip ile tepenin bar içinde hangisinin önce geldiği bilinmiyor.
Stop tarafı bu asimetriden etkilenmiyor (dolumu tetikleyen dip zaten aşağıda).

**Ölçüm (bu oturumda, bar-içi yolu BİLİNEN sentetik veriyle, drift = 0, maliyet/ATR
gerçek BTC 2H'ye kalibre):**

| | n | HEDEF | edge | kapı |
|---|---|---|---|---|
| Motorun ölçtüğü | 1414 | 640 | **+0.0157R** | **AÇILIR** |
| Gerçek bar-içi yol | 1414 | 586 | **−0.0836R** | kapalı (doğru) |

Artefakt **+0.0993R** ve **+54 fazla HEDEF (%9.2)**. Kenarı OLMAYAN veride kapıyı
KAPALI'dan AÇIK'a çeviriyor. Rapordaki canlı iddia +0.2586R idi — artefakt onun
**%38'i büyüklüğünde**.

**T2 zehir testi bunu YAKALAYAMAZ**: bu bak-ileri değil, bar-içi sıra varsayımıdır;
gelecek barları ×10 çarpmak dolum barının kendi h/l ilişkisini değiştirmez.
**T3 fail-closed testi de yakalayamadı**: tekdüze kayıp trendi kullanıyor, rastgele
yürüyüş değil.

Düzeltme: dolum barında **yalnız stop** kontrol edilsin; hedef taraması `giris_idx+1`'den
başlasın (`yon` atandıktan sonra `j += 1; continue`).

## P0-2 — `--self-test` FAIL verse bile çıkış kodu 0

`_main` (3781) ve sarmalayıcı (751): koşulsuz `return 0`. FAIL hiç sayılmıyor.
Düzeltme: `hata = sum(1 for _,d,_ in R if d=="FAIL"); return 1 if hata else 0`.

## P1-1 — `kazan=0` iken kapı uydurma paydayla AÇILIYOR

`b = (sum_kaz_r/kazan) if kazan else R_FADE` (3295). Ölçüm:
`_kapi(n=50, kazan=0, sum_r=+5.0, sum_kaz_r=0.0)` → **`acik=True, p_hat=0.000,
b_win=1.5 (ölçülmedi), stake=%6.67`**. Sıfır kazanan, açık kapı.
Düzeltme: `if kazan == 0: return out` (kapalı).

## P1-2 — Kelly paydası eksik: stake yapısal olarak ŞİŞİK

Kod `stake = edge_hat / b_win`. Bu, kayıp bacağının **tam 1.0R** olduğunu varsayar.
Gerçek kayıp `a = 1 + maliyet/ATR ≥ 1.093` (STOP tek başına), ZAMAN kayıplarıyla daha
büyük. Doğru genel Kelly `edge/(a·b)`. Yani **kod = doğru × a**.
Bu oturumda ölçülen: `a = 1.151` → **stake %15.1 fazla**; taban şişme %9.3.

## P1-3 — `h2_barlar` sayfalamada tavan yok (sonsuz döngü)

3479-3497: tek çıkış `if not rows: break`. Sunucu boş-olmayan ama tümü görülmüş satır
dönerse `after` sabit kalır. Kardeş `okx_uyumlu_getir` (3267) bunu **doğru** yapıyor
(`for _ in range(80)` + `if not yeni: break`). Aynı dosyada iki disiplin.

## P1-4 — `v=0` barda "nötr dolgu" maksimum ayı sinyaline dönüyor

v5 `taker_alis = v/2.0` (3231) + v4 `cvd = kırp((2·taker−hacim)/hacim)`,
`hacim = bar["v"] or EPSILON` (v4:1852-53). Ölçüm: v=1000→`+0.0000` ✔ · v=1→`+0.0000` ✔ ·
**v=0→`−1.0000`** ✖. "Yön bilgisi taşımaz" beyanı sıfır hacimli barda geçersiz.

## P1-5 — Funding'in işareti kaynakta yok ediliyor

`abs(float(x["fundingRate"]))` (3501). Motor funding'i hiçbir koşulda gelir olarak
göremez; STRATEJI.md §4'ün "funding aleyhe döndü" filtresi bu boru hattından
türetilemiyor.

## P2 (seçilmiş)

- `islemler` listesi üretilip döndürülüyor ama rapor yolunda **hiç tüketilmiyor**
  (yalnız öz-testte) → boyutlandırılmış sermaye eğrisi hiç hesaplanmıyor.
- `YASAKLI` deseni yalnız öz-testte taranıyor (60, 3674); üretim çıktısında kontrol yok.
- R1 geri çekilme merdiveninin son basamağı (9.0 s) **ölü kod** — `raise` uykudan önce.
- Gömülü md5 **ham blobu** doğruluyor; `exec` edilen I13-yamalı metin korunmuyor.
- Ağsız koşuda 3 test (T2/T7/T9) **`[SKIP]` satırı basmadan** yok oluyor.

## ÇÜRÜTÜLEN İDDİA (dürüstlük kaydı)

"`fade_karar` ATR'yi koşulsuz kullanıp kenar yayınlıyor" → **YANLIŞ**: `kn = {...} if atr
else None` koruması var (3416).

## ÖLÇÜLEMEYEN (VERİ YOK)

- `E25/E26/E22/S14/S16` deney raporları depoda yok → `E_K=2.0 / T_K=1.5 / S_K=1.0`'ın
  "ÖLÇÜLEN" etiketi dayanaksız.
- `+238.3R, n=1092, GA [157.3, 320.8]`: bu boru hattında FADE R-toplamı üzerine GA
  hesaplayan kod yok; sayının kaynağı gösterilemedi.
- Canlı OKX yolu koşmadı (`Tunnel connection failed: 403`).

## DENETİM KOŞUSUNUN KENDİ KUSURU

İkinci (kronolojik) koşuda 536 ajanın 441'i oturum limitine takıldı; **doğrulayıcıların
tamamı ve final sentez düştü**. Sonuç `dogrulanan=0 / elenen=174` — bu "174 bulgu
çürütüldü" DEĞİL, "174 bulgu doğrulanamadı"dır (146'sı `0/0` oy). O liste ham/sınanmamış
kabul edilmelidir; yukarıdaki bulgular o listeden değil, **elle yeniden üretilenlerden**
seçilmiştir.
