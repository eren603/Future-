# Soruşturma Raporu

6 kayıt → 1 kopya, 3 yanlış pozitif, 2 gerçek arıza (1 yüksek / 1 orta / 0 düşük), 1 elle inceleme gerektiriyor

Bağlam: auto; kapsam = Bilinmiyor. Boru hattının TAMAMI kapsam sayılır; hangi katman/motorun etkilendiği varsayımı gerekçede AÇIKÇA işaretlenir.; şiddet standardı = türetilmiş YÜKSEK/ORTA/DÜŞÜK (ön koşul + tekrar koşulu); 3 mercekli doğrulama; gürültü toleransı = kesinlik.

## Şunlarla ilgilen
### [YÜKSEK] Kıyas motoru koşmadı: hesap verme başlığı boş kaldı  (a001)
`ornek/ornek_rapor.json:K5-SI` | EKSIK_AKTARIM | iddia edilen İHLAL (hiza +2) | güven 7.0/10
**Sahip:** en çok katkı veren: Claude (1/1 son commit); CODEOWNERS kaydı yok
**Hüküm:** hafifletilmis, oylar {'gercek_ariza': 3, 'yanlis_pozitif': 0, 'dogrulanamadi': 0}
**Ön koşullar (0):** yok (kendiliğinden tekrar ediyor)
**Tekrar koşulu:** her_kosuda
**Etki modeli eşleşmesi:** yok
**Neden:** EKSIK_AKTARIM deponun KENDİ sözleşmesinde KRİTİK ihlaldir (gozlemci.py KRITIK kümesi, VERİ YOK) — kritik ihlalde işlem kalitesi mühürlenir

ETKİ: 0 ön koşul, tekrar koşulu her_kosuda → YÜKSEK; hafifletici kontrol devrede → gözlemci mührü: kritik ihlalde EMİR kapatılır ve işlem kalitesi MÜHÜRLENİR (piramit.py fail-closed korkuluğu)
**Kanıt izi:** 13 YP kuralı, ornek_rapor.json:10
**Yuttukları:** a002
**Öneri (girdiden):** piramit.py içinde kiyas.kiyasla çağrısı istisna yutuyor olabilir; try bloğunun gerekçesi rapora taşınmalı

### [ORTA] Kapanan karar defterde yeniden yazıldı, gerçekleşen R iptal edildi  (a003)
`ornek/ornek_defter.jsonl:duzeltme_notu` | SICIL_EZILME | iddia edilen İHLAL (hiza -3) | güven 6.0/10
**Sahip:** en çok katkı veren: Claude (1/1 son commit); CODEOWNERS kaydı yok
**Hüküm:** elle_inceleme_gerek, oylar {'gercek_ariza': 2, 'yanlis_pozitif': 0, 'dogrulanamadi': 1}
**Ön koşullar (2):** 
- ikinci sembol koşusu açık olmalı
- ikinci sembol koşusu gerekir
**Tekrar koşulu:** belirli_veride
**Etki modeli eşleşmesi:** yok
**Neden:** iddia artefaktta birebir bulundu: ornek_defter.jsonl:1 (2 isabet); belirti kaynaktan yeniden türetildi

ETKİ: 2 ön koşul, tekrar koşulu belirli_veride → ORTA
**Kanıt izi:** 13 YP kuralı, ornek_defter.jsonl:1

> Statik muhakeme sınırına dayandı; bu bulguyu ELLE tekrar üret (kontrollü koşu) — otomatik hüküm verilmedi.
## Düşenler

| id | başlık | dosya:konum | neden düştü |
|----|--------|-------------|-------------|
| a002 | Hesap verme satırı çıktının en üstünde görünmedi | ornek/ornek_rapor.json:K5-SI | a001 kopyası |
| a004 | Boru hattı K2'de durdu, zirve üretilmedi | ornek/ornek_rapor.json:K2-AI-AJAN | tasarim_geregi (YP kural 1) |
| a005 | Motor işlem vermedi | ornek/ornek_rapor.json:K5-SI | tasarim_geregi (YP kural 2) |
| a006 | Bir şeyler ters gitti | :— | yerelleştirilemez: girdi kaydında artefakt yolu yok |

_Düşen her kayıt gerekçesiyle listelenir; sessiz düşürme yoktur._
