# Bulgu → değişiklik tablosu (Task 13)

Bu tablo, bu oturumda ARTEFAKTTAN üretilen her bulgunun ne olduğunu gösterir. Kaynaklar:
`astra/bulgular_ham_isakisi.json` (109 ham bulgu, 8 boyut) ve `astra/BULGULAR_kendi_okuma.md`
(K-01..K-20, belgeyi satır satır kendi okumam). Sessiz bırakılan bulgu YOKTUR: her kimlik
ya bir göreve+commit'e bağlıdır ya da aşağıdaki "uygulanmadı" bölümünde gerekçelidir.

## ÇÜRÜTME TURUNUN DURUMU — DÜRÜST KAYIT

Plan Task 13, `astra/bulgular_hukum.json` (hasım çürütme iş akışının çıktısı) okunmasını
istiyordu. **BU DOSYA YOK.** Çürütme iş akışı bu oturumda İKİ KEZ oturum limitine takıldı:
ilk koşuda 28 çürütücü ajan düştü, ikinci koşuda 20 ajandan 10'u tamamlandı. Elde kalan
kısmi hükümler (oturum kaydından): `celiski-1` P0 → P1 (başka koşunun yanıtı zaten `run_id`
ile kapalıydı; nonce yine de eklendi — ihtiyaten), `celiski-2` için önerilen (a) şıkkının
belge satır 303 ile çeliştiği uyarısı (host tarafında (a) uygulandı, belge Task 10'da
hizalandı), `celiski-3` ÇÜRÜDÜ, `celiski-4` P2'ye indi. **Diğer bulgular için bağımsız
çürütme hükmü YOKTUR** — "çürütülmedi" demek "doğrulandı" demek değildir; bu bir VERİ
YOK'tur ve onarımların hepsi bulgunun kendi artefakt kanıtına dayanılarak yapılmıştır.

## Ham bulgular (109)

| Bulgu | Kategori | Görev (commit) |
|---|---|---|
| `celiski-1` | metin-kod çelişkisi / yeniden kullanım kapısı | Task 4 (76b53ae), Task 13 (-) |
| `celiski-2` | metin-kod çelişkisi / belirsizlik korunması | Task 2 (65d34d4) |
| `celiski-3` | komut içi çelişki / BLOCKED sonlandırıcılığı | Task 3 (ae80a2c), Task 14 (ce3d4b3 + 3c9d75a) |
| `celiski-4` | komut içi çelişki / FINAL_STATUS enum | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `celiski-5` | belge kendi ilkesiyle çelişiyor / durum ödünç alma | Task 14 (ce3d4b3 + 3c9d75a) |
| `celiski-6` | komut içi çelişki / soru sorma kaçış yolu | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `celiski-7` | metin-kod çelişkisi / akış sırası | Task 9 (2864d4b + 67df2bf + 4a121aa) |
| `celiski-8` | metin-kod çelişkisi / işçi kaynak erişimi | Task 7 (77e1878) |
| `celiski-9` | metin-kod çelişkisi / desteklenmeyen parametre | Task 14 (ce3d4b3 + 3c9d75a) |
| `celiski-10` | metin-kod çelişkisi / başarısızlık raporu | Task 14 (ce3d4b3 + 3c9d75a) |
| `celiski-11` | komut-README-kod tutarsızlığı / effort bağı | Task 14 (ce3d4b3 + 3c9d75a) |
| `celiski-12` | metin-kod çelişkisi / TASK_STATUS | Task 9 (2864d4b + 67df2bf + 4a121aa) |
| `celiski-13` | komut içi çelişki / oturuma özgü araç adı | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `celiski-14` | eski REVIEW_SCHEMA yolu / metin-README-kod | Task 14 (ce3d4b3 + 3c9d75a) |
| `eksiklik-1` | Metinde var, kodda yok — gereksinim kaydı + TASK_STATUS | Task 9 (2864d4b + 67df2bf + 4a121aa) |
| `eksiklik-2` | Metinde var, kodda yok — CAPABILITY_NEED | Task 14 (ce3d4b3 + 3c9d75a) |
| `eksiklik-3` | Metinde var, kodda yok — TOOL_ROUTE | Task 14 (ce3d4b3 + 3c9d75a) |
| `eksiklik-4` | Vaat edilen ama tanımsız — kalıcı görev kaydı ve bağlam devr | Task 14 (ce3d4b3 + 3c9d75a) |
| `eksiklik-5` | Ele alınmayan durum — çok parçalı görev | Task 14 (ce3d4b3 + 3c9d75a) |
| `eksiklik-6` | Ele alınmayan durum — araç çıktısının yalanı | Task 6 (3381a2e), Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `eksiklik-7` | Ele alınmayan durum — işçi sayısı 3-5 dışı | Task 14 (ce3d4b3 + 3c9d75a) |
| `eksiklik-8` | Ele alınmayan durum — effort düşürme | Task 14 (ce3d4b3 + 3c9d75a) |
| `eksiklik-9` | Ele alınmayan durum — maliyet / token bütçesi | Task 14 (ce3d4b3 + 3c9d75a) |
| `eksiklik-10` | Eksik zorlayıcı mekanizma — gereksinim→teslimat eşleme kanıt | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `eksiklik-11` | Eksik zorlayıcı mekanizma — öz-denetim rubriği | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `eksiklik-12` | Eksik zorlayıcı mekanizma — alternatifsiz karar | Task 14 (ce3d4b3 + 3c9d75a) |
| `eksiklik-13` | Eksik zorlayıcı mekanizma — sonlandırma koşulu ve soru kapıs | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `eksiklik-14` | Kaçış yolu — BLOCKED'ın denenen yolları listelemesi zorunlu  | Task 3 (ae80a2c) |
| `makyaj-1` | süsleme/kanıtsız-nihailik | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589), Task 11 (1121b25 + e58f539) |
| `makyaj-2` | tautolojik-fixture/olumsuz-inceleme iddiası | Task 11 (1121b25 + e58f539) |
| `makyaj-3` | sayısal iddia bileşimi (113 test ne kanıtlar) | Task 11 (1121b25 + e58f539) |
| `makyaj-4` | doğrulanamayan dış-kaynak iddiası | Task 11 (1121b25 + e58f539) |
| `makyaj-5` | dairesel VERIFIED | Task 9 (2864d4b + 67df2bf + 4a121aa) |
| `makyaj-6` | VERIFIED etiketinin kanıt türü etiketsiz | Task 9 (2864d4b + 67df2bf + 4a121aa) |
| `makyaj-7` | doğrulanamayan artefakt iddiası | Task 11 (1121b25 + e58f539), Task 12 (f0cd898) |
| `makyaj-8` | süsleme — 'gerçek alt süreç' | Task 14 (ce3d4b3 + 3c9d75a) |
| `makyaj-9` | yoğunlaştırıcı enflasyonu | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `makyaj-10` | tekrar/retorik yineleme | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `makyaj-11` | kayıtların yeniden üretilebilirliği | Task 11 (1121b25 + e58f539) |
| `makyaj-12` | 'doğrulanmış' kelimesinin kapsamı | Task 14 (ce3d4b3 + 3c9d75a) |
| `makyaj-13` | orijinal istek ile durum uyuşmazlığı | Task 9 (2864d4b + 67df2bf + 4a121aa) |
| `makyaj-14` | KORUNACAK DÜRÜSTLÜK CÜMLELERİ (bulgu değil, yanlış-pozitif k | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `kod_hata-1` | mantık hatası / canlı yol ölü | Task 8 (23adac6 + 0ac89da) |
| `kod_hata-2` | dürüstlük ihlali / kanıt kaçırma | Task 5 (b1288d8 + 559644f) |
| `kod_hata-3` | çelişkili kapı / ölü kod | Task 2 (65d34d4) |
| `kod_hata-4` | teşhis kaybı / gerekçe gizleme | Task 8 (23adac6 + 0ac89da) |
| `kod_hata-5` | güvenlik / kimlik sızıntısı | Task 5 (b1288d8 + 559644f) |
| `kod_hata-6` | mantık hatası / işaret düşürme | Task 5 (b1288d8 + 559644f) |
| `kod_hata-7` | güvenlik / sembolik link | Task 5 (b1288d8 + 559644f) |
| `kod_hata-8` | süreç yönetimi / PID yeniden kullanımı | Task 14 (ce3d4b3 + 3c9d75a) |
| `kod_hata-9` | şema doğrulayıcı boşlukları | Task 14 (ce3d4b3 + 3c9d75a) |
| `kod_hata-10` | zaman aşımı tutarsızlığı | Task 14 (ce3d4b3 + 3c9d75a) |
| `kod_hata-12` | hata yakalama / fail-closed kaydı yok | Task 4 (76b53ae), Task 9 (2864d4b + 67df2bf + 4a121aa) |
| `kod_hata-13` | kapı sırası / geç doğrulama | Task 14 (ce3d4b3 + 3c9d75a) |
| `kod_hata-14` | fiş dürüstlüğü / etiket karışması | Task 14 (ce3d4b3 + 3c9d75a) |
| `kacis_yolu-1` | KAÇIŞ YOLU / işçi BLOCKED — kanıtsız sonlandırıcı | Task 3 (ae80a2c) |
| `kacis_yolu-2` | KAÇIŞ YOLU / SINGLE_MODEL → ANALYSIS_ONLY derinliği tanımsız | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `kacis_yolu-3` | KAÇIŞ YOLU / 'host tarafında tut' kayıtlarının tek modelde a | Task 9 (2864d4b + 67df2bf + 4a121aa), Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `kacis_yolu-4` | KAÇIŞ YOLU / gereksinim envanterini kimse bağımsız denetlemi | Task 9 (2864d4b + 67df2bf + 4a121aa) |
| `kacis_yolu-5` | KAÇIŞ YOLU / 'tek odaklı soru sor' — ön-koşulsuz turu bitirm | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `kacis_yolu-6` | KAÇIŞ YOLU / görev-düzeyi engel ('engelin kapsamını kaydet') | Task 14 (ce3d4b3 + 3c9d75a) |
| `kacis_yolu-7` | KAÇIŞ YOLU / 'kısa gerekçe yeterlidir' — artefakt yerine kıs | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `kacis_yolu-8` | KAÇIŞ YOLU / turu bitirme koşulu tanımsız (ısrar talimatı yo | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `kacis_yolu-9` | KAÇIŞ YOLU / RUNTIME_UNAVAILABLE — çalıştırıcı envanteri ara | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `kacis_yolu-10` | KAÇIŞ YOLU / CAPACITY_EXCEEDED — bölme önerisi 'veya' ile is | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `kacis_yolu-11` | KAÇIŞ YOLU / READY araç kabulünde 'gerektiğinde' okuma kontr | Task 14 (ce3d4b3 + 3c9d75a) |
| `kacis_yolu-12` | KAÇIŞ YOLU / VERİ YOK — 'gidermeye çalış' arama kaydı istemi | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `kacis_yolu-13` | KAÇIŞ YOLU / karşı-kanıt araması yalnız 'kritik ve tartışmal | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `prompt_muh-1` | kaçış yolu / soru sorma | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `prompt_muh-2` | kaçış yolu / mod tablosu | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `prompt_muh-3` | ısrar / bitirme koşulu | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `prompt_muh-4` | kaçış yolu / kanıtsız BLOCKED-VERİ YOK | Task 3 (ae80a2c) |
| `prompt_muh-5` | otorite sırası | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `prompt_muh-6` | çelişkili ikili talimat / kısalık-eksiksizlik | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `prompt_muh-8` | prompt yüzeyi belirsizliği (hangi metin gpt-6-astra'ya gidiy | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `prompt_muh-9` | zorlamanın olumlu tanımı yok (yalnız yasak listesi) | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `prompt_muh-10` | şişkinlik / tekrar — reasoning bütçesi | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `prompt_muh-11` | prompt için ölçüm/test yok — tek değişiklik ilkesi | Task 14 (ce3d4b3 + 3c9d75a) |
| `prompt_muh-12` | eskimiş yönerge istemde tutuluyor | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `prompt_muh-13` | çelişkili ikili talimat / eklenti tavanı | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `prompt_muh-14` | effort=max doğrulanabilirliği ifadesi | Task 14 (ce3d4b3 + 3c9d75a) |
| `test_kapsam-1` | tautolojik-test / semantik kapı | Task 2 (65d34d4) |
| `test_kapsam-2` | test kapsamı / EXTERNAL_MODEL yolu | Task 8 (23adac6 + 0ac89da) |
| `test_kapsam-3` | test kapsamı / ret kodları | Task 14 (ce3d4b3 + 3c9d75a) |
| `test_kapsam-4` | zayıf assert / kod adı doğrulanmıyor | Task 14 (ce3d4b3 + 3c9d75a) |
| `test_kapsam-5` | test adı-davranış uyumsuzluğu | Task 14 (ce3d4b3 + 3c9d75a) |
| `test_kapsam-6` | kaçış yolu / BLOCKED serbest metin | Task 3 (ae80a2c) |
| `test_kapsam-7` | vaat edilen ama üretilmeyen durumlar | Task 14 (ce3d4b3 + 3c9d75a) |
| `test_kapsam-8` | 'valid' CLI senaryosunun kanıt değeri | Task 11 (1121b25 + e58f539) |
| `test_kapsam-9` | sahte opener'ın kanıtlamadıkları | Task 14 (ce3d4b3 + 3c9d75a) |
| `test_kapsam-10` | zaman sınırı tutarsızlığı / testsiz etkileşim | Task 14 (ce3d4b3 + 3c9d75a) |
| `test_kapsam-11` | ölü dal / erişilemeyen ret kodu | Task 14 (ce3d4b3 + 3c9d75a) |
| `test_kapsam-12` | aynalayan fixture / stance-verdict kapısı | Task 14 (ce3d4b3 + 3c9d75a) |
| `test_kapsam-13` | testsiz kaynak yakalama kapıları | Task 14 (ce3d4b3 + 3c9d75a) |
| `test_kapsam-14` | CLI giriş kapıları testsiz | Task 11 (1121b25 + e58f539) |
| `api_uyum-1` | API uyumu / strict şema | Task 8 (23adac6 + 0ac89da) |
| `api_uyum-2` | Kanıt disiplini / dış kaynak iddiası | Task 11 (1121b25 + e58f539) |
| `api_uyum-3` | Taşıma sınırı / şema-tavan çelişkisi | Task 8 (23adac6 + 0ac89da), Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `api_uyum-4` | Yanıt ayrıştırma / model kimliği | Task 14 (ce3d4b3 + 3c9d75a) |
| `api_uyum-5` | Dairesel doğrulama / effort yankısı | Task 14 (ce3d4b3 + 3c9d75a) |
| `api_uyum-6` | Teşhis körlüğü / hata gövdesi | Task 8 (23adac6 + 0ac89da) |
| `api_uyum-7` | Hata yayılımı / host katmanı | Task 14 (ce3d4b3 + 3c9d75a) |
| `api_uyum-8` | Ağ ortamı / proxy | Task 8 (23adac6 + 0ac89da) |
| `api_uyum-9` | Zaman aşımı tutarsızlığı | Task 14 (ce3d4b3 + 3c9d75a) |
| `api_uyum-10` | Geçici/kalıcı hata ayrımı ve yeniden koşu | Task 14 (ce3d4b3 + 3c9d75a) |
| `api_uyum-11` | Makbuz doğrulanabilirliği / store=false | Task 14 (ce3d4b3 + 3c9d75a) |
| `api_uyum-12` | Yanıt ayrıştırma / output item filtresi | Task 8 (23adac6 + 0ac89da) |
| `api_uyum-13` | Kesilme nedeninin kaybı | Task 8 (23adac6 + 0ac89da) |
| `api_uyum-14` | Tam kapasite zorlaması / effort kapısı ve preflight eksikliğ | Task 14 (ce3d4b3 + 3c9d75a) |

## Kendi okumam (K-01..K-20)

| Bulgu | Görev (commit) |
|---|---|
| `K-01` | Task 2 (65d34d4) |
| `K-02` | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `K-03` | Task 3 (ae80a2c) |
| `K-04` | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `K-05` | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `K-06` | Task 4 (76b53ae) |
| `K-07` | Task 7 (77e1878), Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `K-08` | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `K-09` | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `K-10` | Task 6 (3381a2e) |
| `K-11` | Task 9 (2864d4b + 67df2bf + 4a121aa) |
| `K-12` | Task 11 (1121b25 + e58f539) |
| `K-13` | Task 8 (23adac6 + 0ac89da) |
| `K-14` | Task 8 (23adac6 + 0ac89da) |
| `K-15` | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `K-16` | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589), Task 12 (f0cd898) |
| `K-17` | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |
| `K-18` | — |
| `K-19` | Task 11 (1121b25 + e58f539) |
| `K-20` | Task 10 (9079abe + 38a6d8c + 022f747 + 1b0e589) |

## Uygulanmadı / kapsam dışı

- `K-18` (aynı kabul-örneği türünün üç tabloda tekrarı) plan metninde AÇIKÇA anılmadı, ama
  yapısal olarak Task 10'da kapandı: v1.4'te iki tablo kaldı (genel kabul örnekleri ve
  yönlendirme kabul örnekleri) ve üçüncü tekrar yok. Kayıt burada, ki "anılmadı" ile
  "yapılmadı" karışmasın.
- `celiski-3` (BLOCKED sonlandırıcılığı ↔ kısmi teslim) ÇÜRÜDÜ hükmü aldı; davranış
  DEĞİŞTİRİLMEDİ. Yerine sınır Task 14C'de komut metnine yazıldı ("Kısmi teslim yoktur").
- Çürütme turu tamamlanamadığı için hiçbir bulgu "ÇÜRÜDÜ" gerekçesiyle atlanmadı; atlanan
  tek şey yukarıdaki iki kalemdir.

## Sayım

- Ham bulgu: 109 — göreve bağlanmayan: 0
- K bulgusu: 20 — göreve bağlanmayan: 1
