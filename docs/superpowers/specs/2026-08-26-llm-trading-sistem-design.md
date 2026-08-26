# LLM İşlem Zinciri → Sayısal Trading Sistemi — Tasarım (spec)

> Tarih: 2026-08-26 · Dal: `worktree-llm-trading-sistem` · Durum: kullanıcı onaylı (3/3 bölüm)
> Hedef dosya: `llm_trading_v3.py` — tek dosya, yalnız Python standart kütüphanesi, Pydroid 3 uyumlu.
> ⚠️ Karar-destek + yerel kâğıt defteri. Canlı/otomatik emir, API anahtarı, imzalı uç, emir ucu DAHİL DEĞİL.

## 1. Amaç ve kabul ölçütü

LLM işlem zincirinin her halkasının sayısal trading karşılığını **çalışır** biçimde kurmak ve
matematiksel hedefi açıkça `E[log servet]` maksimizasyonu olarak tanımlamak.

Kabul ölçütü üç maddedir; üçü birden sağlanmadan iş bitmiş sayılmaz:

1. **Ölü halka yok.** Zincirdeki her halka için, o halka devre dışı bırakıldığında nihai çıktının
   ölçülebilir biçimde DEĞİŞTİĞİ bir test vardır.
2. **Kararı veren sayı ölçülür.** Yön kararını üreten olasılığın kalibrasyonu ve ayırt ediciliği
   ölçülür; ölçülmeyen bir olasılık stake hesabına giremez.
3. **Kanıt yoksa stake yok.** Kalibrasyon güvenilir değilse `f*` matematiğin kendisi tarafından
   0'a indirilir — ayrı bir "HOLD" sınıfı veya eşik kapısı ile değil.

## 2. Çözülen gerilim: HOLD yasağı vs Bayes-optimal karar

Kaynak belge (`LLM_Trading_Sistem_Dokuman.docx`) HOLD'u beş gerekçeyle yasaklıyor. **Bu doğru** ve
korunuyor: `argmax` tanım gereği daima bir eleman döndürür; sözlüğe "seçim yapmama" eklemek decoding
matematiğinin dışına çıkmaktır.

Belgenin atladığı ayrım: LLM'de **seçilen token** ile **o tokenin olasılığı** iki ayrı çıktıdır.
Sözlüğe "bilmiyorum" eklemek ≠ seçilen tokenin olasılığına göre aşağı akışta davranmak.

Trading karşılığı iki eksendir:

| Eksen | Karşılık | Değer kümesi | Ne zaman üretilir |
|---|---|---|---|
| **YÖN** | seçilen token | `V = {LONG, SHORT}` | HER barda, koşulsuz |
| **STAKE** | tokenin olasılığının aşağı-akış kullanımı | `f* ∈ [0, f_max]` sürekli | HER barda, koşulsuz |

`f* = 0` bir "karar vermeme" DEĞİLDİR — `f*(p, b, a)` fonksiyonunun doğal değeridir. Sözlük hâlâ
iki elemanlıdır, üçüncü sınıf eklenmemiştir, seviyeler koşulsuz hesaplanır. Belgenin beş gerekçesi
de ihlal edilmez.

## 3. Zincir — 12 halka, her biri ölçülebilir

| # | LLM aşaması | Trading karşılığı | Ölü-halka testi (bu halka kapatılınca çıktı değişmeli) |
|---|---|---|---|
| 0 | Ham girdi | Çift adaptör: Binance USD-M (ana) / OKX (yedek); kanal başına kapsam skoru | Kanal düşünce kapsam skoru ve `f*` değişir |
| 1 | Tokenizasyon | Özellik-token **sözlüğü**; kimlik `(sembol, zaman_dilimi, aile, gecikme)`; 4H ve 15M **ayrı** zaman dilimi tokenları | Bir aile çıkarılınca temsil ve karar değişir |
| 2 | Embedding | Yalnız TRAIN diliminden `μ/σ`; öğrenilen giriş izdüşümü | İzdüşüm sabitlenince (öğrenilmezse) test metriği düşer |
| 3 | Konum kodu | Zaman ekseni ve sembol ekseni **ayrı** kodlanır | Konum karıştırılınca çıktı değişir |
| 4 | Causal attention | `softmax(QK^T/√d_k)·V`, nedensel maske | QK terimi silinince VE maske kaldırılınca çıktı değişir (iki ayrı test) |
| 5 | FFN | Kapılı MLP + artık bağlantı + norm | Kapatılınca çıktı değişir |
| 6 | Logit başlığı | `V={LONG,SHORT}` üzerinde eğitilen başlık; kronolojik bölme + purge/embargo | Eğitilmemiş başlıkla metrik düşer |
| 7 | Temperature | AYRI holdout'ta, **dağıtılan dağılımın kendisinde** fit; izotonik alternatifi ile yarışır | T=1 sabitlenince kalibrasyon metriği bozulur |
| 8 | Softmax | **YÖN** ekseninde (sembol ekseninde değil) | — (halka 6/7 ile birlikte ölçülür) |
| 9 | Decoding | `argmax` → LONG/SHORT, HOLD yok, seviyeler koşulsuz | Beraberlikte `sign(z)` |
| 10 | Self-consistency | Bağımsız çekirdekli çoklu model; oylama + dağılım | Tek modele düşünce uzlaşı ölçüsü kaybolur |
| 11 | Otoregresif döngü | Bar bar durum taşınır; karar bağlama eklenir | Durum sıfırlanınca çıktı değişir |
| 12 | Detokenizasyon | Giriş / SL / TP + seçilen R + `f*` | — (nihai çıktı) |

## 4. Kalibrasyon ve stake — "en yüksek sonuç"un matematiği

### 4.1 Bölme
Kronolojik `train / kalibrasyon / test`. Bölmeler arasına **purge** (etiket ufku kadar bar atılır)
ve **embargo** eklenir. Amaç: bir örneğin etiket penceresi bir sonraki bölmenin girdi penceresiyle
kesişemesin.

### 4.2 Kalibrasyon
- Temperature ölçekleme, **dağıtılan dağılımın kendisinde** fit edilir (log-havuz ile olasılık-havuz
  uyuşmazlığı yapısal olarak kapatılır).
- İzotonik regresyon alternatif olarak fit edilir; ikisi arasından **holdout NLL**'e göre seçim yapılır.
- Grid sınırına dayanma denetlenir ve raporlanır.

### 4.3 Ölçüm
`ECE` (bin sayısına duyarlılık taramasıyla — tek bine çökme tespit edilir), `MCE`, `Brier` +
bileşen ayrışımı, `AUROC`. Ayrıca **grup bazında** (sembol / rejim / volatilite durumu / veri
kalitesi) ve **en kötü grup ECE**. Her metrikle birlikte örnek sayısı ve Wilson güven aralığı verilir.

### 4.4 Shrinkage — kanıt yoksa stake yok
```
p_kullanilan = 0.5 + s · (p_kalibre − 0.5)
```
`s ∈ [0,1]` kalibrasyon güvenilirliğinden **türetilir**, üç çarpanın çarpımı:
```
s = s_kanit · s_kalibrasyon · s_kapsam

s_kanit        = clamp( 2 · (wilson_alt(yonlu_dogruluk, n_holdout) − 0.5), 0, 1 )
s_kalibrasyon  = clamp( 1 − ECE_enkotu_grup / 0.10, 0, 1 )
s_kapsam       = dolu_kanal_sayisi / toplam_kanal_sayisi
```
Kanıt yoksa `s → 0` ⇒ `p → 0.5` ⇒ `f* → 0`. Sabit eşik yoktur; üç çarpan da veriden gelir.
`wilson_alt` 0.5'in altındaysa `s_kanit = 0` — yani şanstan ayırt edilemeyen bir model stake alamaz.

### 4.5 Stake
Asimetrik Kelly, **maliyet sonrası**:
```
f* = (p·b − q·a) / (a·b),   f* = max(0, f*),   uygulanan = λ · f*
b = R_secilen − cost_r      (net kazanç, R biriminde)
a = 1 + cost_r              (net kayıp, R biriminde)
cost_r = (komisyon + kayma + funding) / stop_mesafesi
```
`λ` kesirli-Kelly çarpanı. **Varsayılan `λ = 1.0` (tam Kelly)** — kullanıcı kararı gereği sabit
profil tavanı kaldırılmıştır. Çıktı, `λ ∈ {1.0, 0.5, 0.25}` için stake'i **yan yana** gösterir:
tam Kelly `p` tahmin hatasına karşı kırılgandır (hata varyansı servet büyüme oranını ikinci
dereceden cezalandırır), bu yüzden karar kullanıcıya bırakılır ama gizlenmez.

`f_max` — stake'in mutlak üst sınırı, tercih değil **borsa fiziği**:
```
f_max = min( 1 / kaldirac_azami , (|giris − likidasyon_fiyati| / giris) · guvenlik_pay )
```
`f* · λ > f_max` ise stake `f_max`'a kırpılır ve kırpma çıktıda **açıkça** yazılır.
Likidasyon fiyatı okunamıyorsa `f_max` fail-closed olarak 0 alınır (uydurulmaz).

### 4.6 Başabaş kimliği (çıktıda daima gösterilir)
```
f* > 0  ⟺  p > a / (a + b)
```
Ölçülen değerler: `cost_r=0.60` ⇒ `p > 0.6857`; `cost_r=0.80` ⇒ `p > 0.7714`.
Bu, sabit 1.5/2.0 ATR geometrisinin (R=1.333) maliyet altında neden yaşayamadığının kanıtıdır.

## 5. Geometri araması — R sabit değil, karar değişkeni

Aday `(stop_k, hedef_k)` ızgarası kurulur. Her aday için ilk-geçiş olasılığı `p_hedef` **tarihsel
bar yürütmesiyle** ölçülür (Monte Carlo varsayımı değil, gerçek barlar; aynı barda iki bariyer
= muhafazakâr STOP). Her aday için `E[log]` hesaplanır:
```
E[log] = p_hedef · ln(1 + λf*·b) + (1 − p_hedef) · ln(1 − λf*·a)
```
En yüksek `E[log]` veren aday seçilir. Seçilen `R`, `p_hedef` ve örneklem büyüklüğü çıktıda gösterilir.
Hiçbir aday `E[log] > 0` vermiyorsa bu **gizlenmez**: yön ve seviyeler yine üretilir, `f*` 0 çıkar.

## 6. Hata yönetimi
- Kanal erişilemezse değeri **uydurulmaz**; kanal `YOK` işaretlenir, kapsam skoru düşer, `s` düşer,
  `f*` düşer. Nötr 0.0 enjeksiyonu yasaktır.
- Adaptör düşerse (Binance → OKX) bu **çıktıda açıkça yazılır**; sessiz düşüş yok.
- Tick/step filtreleri okunamazsa seviyeler yuvarlanmamış olarak işaretlenir; sessizce ham geçmez.
- Determinizm: aynı girdi + aynı tohum = aynı çıktı (test edilir).

## 7. Test stratejisi (stdlib `unittest`)
| Sınıf | Ne sınar |
|---|---|
| Sızıntı | purge/embargo etiket penceresini gerçekten kesiyor mu |
| Ölü katman | her halka kapatılınca çıktı değişiyor mu (halka başına bir test) |
| Kalibrasyon | shrinkage kanıt yokken `f*=0` veriyor mu; T fit edilen dağılım = dağıtılan dağılım mı |
| Maliyet | başabaş `p` aritmetiği; `cost_r` hesabı |
| Geometri | ilk-geçiş ölçümü muhafazakâr mı (aynı bar = STOP) |
| Determinizm | aynı girdi = aynı çıktı |
| Güvenlik | API anahtarı / imzalı uç / emir ucu kodda YOK |

## 8. Çıktı biçimi
Sembol başına: `YÖN` · `p_kalibre` · `s` (shrinkage) · seçilen `R` ve `p_hedef` ·
`giriş / SL / TP` · `f*` ve uygulanan stake · kanal kapsamı · kalibrasyon kalitesi
(ECE/MCE/Brier/AUROC + en kötü grup) · `pipeline_trace` (12 halkanın ölçülmüş izi) ·
başabaş `p` eşiği. Ayrıca yerel kâğıt defteri (JSON + CSV).

## 9. Kapsam dışı (açıkça)
Canlı emir, API anahtarı, imzalı uç, emir/iptal ucu, gerçek para. Likidasyon akışı bu sürümde
modele girmez ve bu çıktıda bayrakla beyan edilir.
