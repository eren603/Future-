# BAĞ HARİTASI — ASTRA v1.3 bulguları arasındaki ilişkiler (bag-kurma)

Yöntem grupları: **G1 nedensel zincir** + **G3 düğüm-bağ haritası** (≥2 grup; tünel yasağı).
Kanıt aileleri: OKUMA (orkestratörün satır-satır okuması, BULGULAR_kendi_okuma.md),
AJAN (8 izole tarayıcı, bulgular_ham_isakisi.json — hasım çürütme sürüyor, sonucu
bulgular_hukum.json'a yazılacak), ÖLÇÜM (OLCUM_FAZ3.md + probes/). Tek aileye dayanan
bağ "TEK-KAYNAK" etiketlidir.

## Düğümler (bulgu kümeleri)

| Düğüm | İçerik | Bulgular (AJAN / OKUMA) | Kanıt |
|---|---|---|---|
| N1 Host'suz host | A.1 gereksinim kaydı, TASK_STATUS, CAPABILITY_NEED, TOOL_ROUTE "host tarafında" — kodda yok, çıktıda yeri yok | eksiklik-1/2/3/10, kacis_yolu-3, celiski-12, makyaj-5/6/13 / K-11 | ÖLÇÜLDÜ (grep 0) |
| N2 Varsayılan mod tanımsız | SINGLE_MODEL/ANALYSIS_ONLY izin diliyle; zorunlu artefakt yok | kacis_yolu-2, prompt_muh-2 / K-04 | DOKÜMAN |
| N3 Soru sorma üç sürüm | 39/185/309 farklı ön koşul; "maddi biçimde" tanımsız | celiski-6, prompt_muh-1, kacis_yolu-5, eksiklik-13 / K-02 | DOKÜMAN |
| N4 Ucuz BLOCKED | Tek cümle bütün çalışmayı bitirir; deneme kanıtı yok; kısmi teslim yasak | kacis_yolu-1, eksiklik-14, prompt_muh-4, test_kapsam-6, celiski-3 / K-03 | ÖLÇÜLDÜ |
| N5 Belirsizlik cezası | Kritik olmayan uncertain kart bile kapıyı kapatır | celiski-2, kod_hata-3 / K-01 | ÖLÇÜLDÜ (probe) |
| N6 Fixture totolojisi → "gerçek" dili | pass modu stance→verdict kopyalar; testler adının vaat ettiğini kanıtlamaz; EXTERNAL_MODEL başarı yolu hiç sınanmamış | test_kapsam-1/2/8/12, makyaj-2/3/6/9 / K-10 | ÖLÇÜLDÜ |
| N7 Canlı API doğrulanmamış | strict şema anahtar kelimeleri, model alias/snapshot, HTTP hata çökmesi, proxy, 16384 tavanı | api_uyum-1/3/4/6/8/12/13, kod_hata-1, celiski-9 / K-12, K-13, K-14 | ÖLÇÜLDÜ + VERİ YOK |
| N8 Yeniden oynatma | finalize iki kez aynı digest ile geçer; nonce yok | celiski-1 | ÖLÇÜLDÜ (AJAN) — TEK-KAYNAK, çürütme bekliyor |
| N9 Mimari fixture'a bağlı | işçi zarfı kaynak İÇERİĞİ taşımıyor; karar kartlardan ÖNCE config'te | celiski-7, celiski-8 | DOKÜMAN |
| N10 Şişkinlik/tekrar/otorite | aynı ilke 3-5 yerde; "üst öncelikli" tanımsız; 55 KB | prompt_muh-5/10/12, makyaj-10 / K-05, K-16 | ÖLÇÜLDÜ (114× "gerçek") |
| N11 Güvenlik/kod kenarları | TEST_FIXTURE'a anahtar sızması; yorumlu ifade kanıt sayılır; Unicode eksi; symlink; TOOL etiketi bağsız; owner yer tutucu | kod_hata-2/5/6/7, eksiklik-6 / K-06 | ÖLÇÜLDÜ |
| N12 Kapasite iddiası | 320 kaynak/iddia şeması vs 131072 bayt tel + 16384 token | api_uyum-3, eksiklik-5/9 / K-07 | ÖLÇÜLDÜ |

## G1 — Nedensel zincirler (her ok: zaman önceliği · müdahale · karşı-olgu)

**Z1. "Host'a yaslanma" → N1 → N2 → N6.** Protokol, denetim kayıtlarını var olmayan bir host'a
havale etti (zaman: tasarım kararı bulgulardan önce); müdahale: "host yoksa host sensin —
kayıtlar çıktıda JSON blok" kuralı eklenince N1 ve N2'nin kaçışı kapanır; karşı-olgu: gerçek bir
host kodu olsaydı N1 doğmazdı ama N2 (tek model varsayılan yol) yine tanımlanmalıydı → N2
kısmen bağımsız. PM: kural eklenir ama model bloğu üretmez → rubrik/test bloğun yokluğunu
PARTIAL sayar. SM: "kayıt zihinde tutulur" alternatifi → çürür: doğrulanamaz (satır 31'in
kendi ilkesi). RT: JSON blok da uydurulabilir → bu yüzden blokta kanıt olarak yalnız
teslimat konumu+hash ve komut çıktısı kabul edilir. **Hüküm: SAĞLAM.**

**Z2. "Çelişkili/tekrarlı metin" → N3, N10 → reasoning bütçesi kaybı → N2'nin izin dili
tercih edilir.** Zaman: tekrarlar sürüm sürüm birikti (v1.2→v1.3 ekleri). Müdahale: tek
otorite sırası + tek "soru sorma" kuralı → N3 kapanır. Karşı-olgu: rehber (ARASTIRMA §4)
çelişkinin modeli uzlaştırma aramasına soktuğunu söylüyor; çelişki olmasaydı bütçe
kaybı olmazdı — mekanizma DOKÜMAN kanıtlı, ölçüm yok (canlı model yok). PM: sadeleştirme
dürüstlük cümlelerini siler → koruma listesi + test. SM: "tekrar pekiştirir" → çürür:
rehber tersini söylüyor ve tekrarlar birbirinden farklı koşullar taşıyor (39/185/309).
**Hüküm: SAĞLAM (mekanizma DOKÜMAN, etki ölçülmedi → etki için ZAYIF).**

**Z3. "Belirsizlik = başarısızlık" (N5) → dürüstlük-karşıtı teşvik → N6'daki fixture
totolojisi tek geçer yol.** Zaman: kapı tasarımı önce; müdahale: yalnız kritik/karara giren
belirsizlik kapıyı kapatır → dürüst uncertain kart yaşar; karşı-olgu: fixture 'pass' modu
uncertain kartla da düşer (probe ölçtü) → "valid" senaryosu ancak belirsizliksiz kartla
geçer. PM: kritik olmayan belirsizlik gizlenir → SEMANTIC_POLICY "belirsizliği dürüstçe
işaretle" cümlesi + host kabulü. SM: "yayında belirsiz kart olmasın" alternatifi (belgeyi
koda uydur) → çürür: 6.1/8 ilkeleri ve rehber (yön korunur) tersini emreder. **Hüküm: SAĞLAM.**

**Z4. "Çıkışların maliyeti yok" → N4, N3, N2.** Ortak mekanizma: bir durum adı (BLOCKED, soru,
ANALYSIS_ONLY, VERİ YOK) artefakt istemeden çıkış sağlıyor. Müdahale: her çıkışa ön koşul +
artefakt (denenen yollar, arama günlüğü, varsayım altında taslak). Karşı-olgu: artefakt
istenseydi model yine uydurabilir → bu yüzden artefakt doğrulanabilir tür (komut çıktısı,
dosya) olmalı. **Hüküm: SAĞLAM.**

**Z5. "Canlı doğrulama yok" (N7) → "gerçek" dili (N6) çürük temelde.** Zaman: canlı çağrı
hiç yapılmadı (belge kabul ediyor). Müdahale: kelime düzeltmesi yetmez; taşıma şeması +
snapshot toleransı + hata sınıflandırması + preflight eklenir ve "canlı doğrulanmadı" etiketi
kalır. Karşı-olgu: canlı çağrı yapılsaydı N7'nin yarısı ölçülürdü — bu ortamda anahtar yok
(VERİ YOK). **Hüküm: ZAYIF (onarım yapılır, doğrulama yapılamaz — açıkça yazılır).**

**Z6. N8 (yeniden oynatma) ↔ N9 (fixture mimarisi).** İkisi de "gerçek işçi/inceleyici
hiç koşmadı" kökünden: replay'i yakalayacak nonce ve zarfa kaynak içeriği koymak, fixture
ile fark yaratmadığı için eksik kalmış. Müdahale: nonce + kilit + zarf snapshot'ı. TEK-KAYNAK
(AJAN) — orkestratör N8'i bağımsız ölçmedi; plan maddesi "ölç, sonra düzelt". **Hüküm: ZAYIF
(çürütme bekliyor).**

## G3 — Düğüm-bağ haritası (etiketli kenarlar)

- N1 —[sebep, ÖLÇÜLDÜ]→ N2; N1 —[sebep, DOKÜMAN]→ makyaj-5/6/13 (öz-beyan VERIFIED)
- N10 —[ortam, DOKÜMAN]→ N3; N10 —[ortam, DOKÜMAN]→ N2 (izin dili tekrarlarda korunmuş)
- N5 —[teşvik, ÖLÇÜLDÜ]→ N6; N6 —[maskeleme, ÖLÇÜLDÜ]→ N7 (fixture yeşil, canlı bilinmiyor)
- N4 —[aynı mekanizma, DOKÜMAN]→ N3, N2; N4 —[kısmi teslim yasağı, DOKÜMAN]→ celiski-3
- N9 —[önkoşul, DOKÜMAN]→ N6 (fixture'sız çalışamaz); N9 —[ortak kök, VARSAYIM]→ N8
- N12 —[sınır, ÖLÇÜLDÜ]→ N7 (16384/131072); N12 —[eksik, DOKÜMAN]→ eksiklik-5 (parçalama tanımsız)
- N11 —[bağımsız]→ (yalnız kod; metinle bağı zayıf) — TEK-KAYNAK değil (OKUMA+AJAN+ÖLÇÜM)

Merkezîlik (en çok bağ): N1, N6, N2. Merkezîlik nedensellik değildir; ama onarım sırası
için öncelik verir: önce N1+N2 (yerleşim + zorunlu artefakt), sonra N5/N4/N3 (kapılar),
sonra N7/N11 (kod), en son N10 (sadeleştirme; koruma listesiyle).

## Çürüyen / zayıf bağlar

- "Tekrar reasoning bütçesini yer" etkisi ÖLÇÜLMEDİ (canlı model yok) → yalnız DOKÜMAN.
- N8 yalnız AJAN ölçümü; orkestratör plan içinde yeniden ölçecek (probe eklenecek).
- "Süsleme = kelime" varsayımı ÇÜRÜDÜ: makyaj-14 doğru — 'kusursuz/gerçek/garanti' kelimeleri
  çoğu yerde OLUMSUZLAMA içinde (dürüstlük cümlesi); kelime bazlı temizlik yasak, cümle bazlı
  değerlendirme + koruma listesi zorunlu.

## VERİ YOK kalan sorular

1. gpt-6-astra strict modu min/maxLength/minItems/maxItems/enum kabul ediyor mu? (birincil
   doküman egress-bloklu; canlı anahtar yok)
2. Yanıttaki `model` alanı alias mı snapshot mı dönüyor? (GPT-4o örneği snapshot; Astra
   için VARSAYIM)
3. Sadeleştirilmiş komutun canlı Astra'da davranışı değişiyor mu? (model değerlendirmesi
   NOT_RUN — belge de bunu kabul ediyor; v1.4 bunu iddia etmeyecek)

Bu harita bir karar değildir; onarım kararları tasarım belgesinde (docs/superpowers/specs/)
ve plan maddelerinde verilir.
