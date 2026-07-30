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
