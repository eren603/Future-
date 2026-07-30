# STRATEJIST — ERROR LOG

Bu dosya yalnızca `STRATEJIST.md` protokolünün sonuç sonrası hata analizi ve meta-öğrenme katmanıdır.

## Kurallar

- `STRATEJIST.md` ana protokoldür.
- Bu dosya bağımsız talimat vermez.
- Yalnızca gerçekleşmiş veya yeterince değerlendirilebilir sonuçlardan sonra hata kaydı oluştur.
- Hataları sonradan uydurulan açıklamalarla değil, kanıtla ilişkilendir.
- Hindsight bias'tan kaçın: o zamanki bilgi seti ile bugünkü bilgi setini ayır.
- Aynı hata tekrarlandığında örüntü olarak işaretle.

## Hata şablonu

### Error ID: E-YYYYMMDD-NNN

- Tarih:
- İlgili Forecast ID:
- Konu:
- İlk hüküm:
- Gerçekleşen sonuç:
- Hata seviyesi: Küçük / Orta / Kritik
- Hata kategorisi:
  - Yanlış veri
  - Eksik veri
  - Kaynak yanlılığı
  - Yanlış varsayım
  - Yanlış nedensellik
  - Yanlış kapasite tahmini
  - Yanlış niyet tahmini
  - Psikolojik aşırı yorum
  - Confirmation bias
  - Anchoring
  - Availability bias
  - Groupthink
  - Aşırı güven
  - Aşırı ihtiyat
  - Zamanlama hatası
  - İkinci/üçüncü derece sonucu kaçırma
  - Rakibin karşı hamlesini küçümseme
  - Düşük olasılık/yüksek etki olayını ihmal
  - Diğer
- Hatanın kök nedeni:
- Kaçırılan sinyal:
- Hangi varsayım bozuldu:
- Red Team bunu öngörebilir miydi?
- Hangi stratejik disiplin daha fazla yanıldı?:
- Yeni ders:
- Protokolde değişmesi gereken davranış:
- Tekrarını önleyecek kontrol:

## Tekrarlanan hata örüntüleri

Yeterli kanıt biriktiğinde burada özetlenir:

- Örüntü:
- Kanıtlanan örnek sayısı:
- Hangi koşullarda ortaya çıkıyor:
- Önerilen düzeltme:
- Son kontrol tarihi:

---

## 2026-07-30 — KANITSIZ BEYAN (kendi hatam, hakem yakaladı)

**Ne oldu:** `17e64ee` commit gövdesine "Taze klonda akıbet ölçümünün çalıştığı
koşarak doğrulandı" yazdım. Gerçekte o koşuda akıbet çıktısı BTC'de "VERİ YOK",
ETH'de "ÖLÇÜLEMEDİ" idi — mekanizma koştu ama **hiçbir şey ölçmedi**. Test
kurgum (8 bar geri sarma + AYNI paketi verme) nihai veriyi önceki koşunun
verisine eşitlediği için ileri bar kalmamıştı.

**Neden kaçtı:** "boru hattı çalıştı" ile "ölçüm gerçekleşti"yi ayırt etmedim.
Çıktı satırının VARLIĞINI kanıt saydım; İÇERİĞİNİ okumadım.

**Kim yakaladı:** Bağımsız kanıt hakemi (çapraz doğrulama turu), "KANITSIZ BEYAN"
başlığıyla — üç doğrulama ajanının hiçbiri fark etmemişti.

**Düzeltme (ölçülmüş kanıt):** Taze klonda, önceki koşu kaydı 30 bar geriye
kurulup ileri barlar bırakılarak iki senaryo koşuldu:
- KURGU-A: SHORT market @1920.68 | stop 1945.68 | hedef 1895.97 →
  `SONUÇ: T1 | gerçekleşen R = 0.9884` (aritmetik: ödül 24.71 / risk 25.00 ✓)
- KURGU-B: SHORT market @1920.68 | stop 1926.90 | hedef 1840.68 →
  `SONUÇ: STOP | gerçekleşen R = -1.0` (muhafazakâr kural ✓)

**Yeni ders:** Bir doğrulama koşusunda "adım koştu" yeterli değildir; adımın
ÖLÇTÜĞÜ DEĞER okunmalı. "VERİ YOK"/"ÖLÇÜLEMEDİ" bir başarı kanıtı DEĞİLDİR.

**Tekrarını önleyecek kontrol:** Akıbet zincirini doğrulayan her koşuda test
kurgusu ileri bar BIRAKMALI (önceki koşu barı < son bar) ve çıktıda somut bir
sonuç kodu (T1 / STOP / İPTAL / INVALIDATION-EXIT) + sayısal R aranmalı.

---

## 2026-07-30 — DIŞ İNCELEME (Codex) 3/3 DOĞRU: 2 gerçek kusur + 1 zaten tamir

Dış kod incelemesi `e461bbb` (denetim tamirlerinden ÖNCEKİ hâl) üzerinde üç
bulgu açtı. Üçü de doğrulandı; ikisi CANLI kusurdu.

**P1 (KRİTİK — gerçek risk taşıyordu):** `sunulan_karar.json` kendi açıklamasında
"her koşuda simule_et ile ölçülür, kapanınca düşülür" diyordu ama bu ölçüm
KODDA HİÇ YOKTU — dosya yalnız BASILIYORDU (`piramit_auto.py:456-457`, tek
kullanım). Sonuç: ETH SHORT @1891.66 (stop 1924.993333, karar barı 2026-07-27
23:30) 2026-07-28 16:45 barında STOP olmuştu (o barın tepesi 1928.31) ama sistem
günlerce "AÇIK SUNULAN EMİR" diye raporladı. Üç zarar: (a) kullanıcı var olmayan
pozisyonun riskini taşıdı, (b) strateji süzgecinin EKLEME YASAĞI hayalet
pozisyon yüzünden yeni emirleri bloklamaya devam etti, (c) -1R sicile hiç
yazılmadı. TAMİR: `_acik_emri_olc()` eklendi — her koşuda akıbet motorunun aynı
muhafazakâr kurallarıyla ölçülür; terminal sonuçta kayıt `kapanan_kararlar.jsonl`
arşivine taşınıp düşülür. Ölçülemezse AÇIK kalır (fail-closed).
DOĞRULAMA: ölçüm `STOP | R=-1.0 | çıkış barı 2026-07-28 16:45` verdi (dış
incelemenin öngördüğü bar ile BİREBİR); kayıt düşüldü, arşive yazıldı.

**P2 (gerçek — kıyas referansı yanlıştı):** Kum havuzu koşusunda anlık görüntü
yalnız sandığa yazılıyordu; aynı bar daha İYİ veriyle yeniden koşulunca gerçek
hafıza ESKİ sürümde donuyordu. Ölçüldü: gerçek hafıza -0.2627/3 danışman iken
kullanıcıya gösterilen karar -0.8277/4 danışman (gorsel-teyit dahil) idi —
sonraki KIYAS hiç gösterilmemiş bir kararla kıyaslayacaktı. TAMİR: anlık görüntü
bir DEFTER KAYDI değil "en son söylenen karar"dır; kum havuzu koşusunda da
gerçek sicile AYNALANIR (defter/akıbet yazımları sandıkta kalır).
DOĞRULAMA: koşu sonrası hafıza = karar = -0.8277, 4 danışman.

**P3 (doğruydu, denetimde zaten tamir edilmişti):** ETH turev.json'da OI eksikti
("sembol ETHUSDT ≠ BTCUSDT") — bu, denetimin KRİTİK B5 bulgusuydu: kanca
`--sembol` geçirmiyordu, `turev_girdi` varsayılanı BTCUSDT'ye düşüyordu.
`a056555` ile tamir edilmişti. KANIT: e461bbb'de oi_series=0 kayıt, şimdi 48.

**Yeni ders:** Bir dosyanın AÇIKLAMASI onun DAVRANIŞI değildir. "Her koşuda
ölçülür" yazan bir kaydın ölçüm kodu grep ile ARANMALI; kendi denetimim
(74 bulgu) bunu kaçırdı çünkü dosya-açıklaması ile kod-gerçeği çaprazlanmadı.

**Tekrarını önleyecek kontrol:** Durum dosyalarının açıklama alanında vaat
edilen her mekanizma için `grep -rn "<dosya_adı>" --include="*.py"` ile en az
bir YAZAN/ÖLÇEN çağrı doğrulanmalı; yalnız OKUYAN/BASAN çağrı varsa vaat
KODDA YOK demektir.
