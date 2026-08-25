---
name: bag-kurma
description: Olaylar ve problemler arasında bağ kurma becerisi. Bir soru/analiz birden fazla olay, veri, problem ya da sinyal içerdiğinde OTOMATİK devreye girer — tetikleyici gerekmez. Dört grup yöntemle (nedensel zincir, analojik eşleme, düğüm-bağ haritası, zaman bağları) aday bağlar üretir; her bağı Pre-Mortem → Steelman → Red Team döngüsünden geçirir; hafızadan bağ, dairesel doğrulama, tünel görüş ve taraflılık yasaktır. Çıktı: kanıt-etiketli BAĞ HARİTASI.
---

# BAĞ-KURMA — olaylar/problemler arasında ilişki kurma disiplini

Amaç: dağınık olayları tek anlatıya ZORLAMADAN, her biri sınanmış bağlarla
birbirine bağlamak. Bağ bir İDDİADIR; sınanmadan rapora giremez.
Kaynak dökümü: `kaynaklar.md` (dört GitHub deposundan uyarlama, atıflı).

## Dört yöntem grubu (bir analizde EN AZ İKİSİ denenir — tünel görüş yasağı)

### G1 · NEDENSEL ZİNCİR  [kaynak: chendl02/Awesome-LLM-Causal-Reasoning]
Olay→sebep zinciri adım adım (CoT) kurulur; her nedensel ok üç testten geçer:
1. **Zaman önceliği:** sebep, sonuçtan ÖNCE mi? (önce gelmeyen açıklayamaz)
2. **Müdahale sorusu (intervention):** "bu değişken farklı olsaydı sonuç değişir miydi?"
3. **Karşı-olgu (counterfactual):** "olay X hiç olmasaydı ne olurdu?"
Sonuçtan geriye en-iyi-açıklama araması (abduction) serbesttir ama çıkan açıklama
yine 3 testten geçer. KORKULUK: korelasyon ≠ nedensellik; mekanizma yazılamayan
ok çizilmez.

### G2 · ANALOJİK EŞLEME  [kaynak: zjunlp/MKG_Analogy]
A:B :: C:? yapısı üç adımla kurulur: **Abduction** (bilinen olay çiftinden kural
çıkar) → **Mapping** (yapıyı yeni duruma eşle — hangi İLİŞKİ taşınıyor, açık yaz)
→ **Induction** (genelle). KORKULUK: yüzeysel benzerlik ≠ yapısal benzerlik;
analoji KANIT değil HİPOTEZ üretir — üretilen hipotez veriyle sınanır.

### G3 · DÜĞÜM-BAĞ HARİTASI  [kaynak: XiaoxinHe/Awesome-Graph-LLM]
Olaylar düğüm, ilişkiler ETİKETLİ kenar olarak metinle modellenir
(Graph-of-Thoughts / GraphRAG deseni). Her kenar bir kanıt sınıfı taşır:
[ÖLÇÜLDÜ] / [DOKÜMAN] / [VARSAYIM] — etiketsiz kenar çizilmez. Çok bağ alan
düğüm (merkezîlik) "kilit olay" adayıdır; ama merkezîlik nedensellik değildir.

### G4 · ZAMAN BAĞLARI  [kaynak: jiapuwang/Awesome-TKGC]
Olaylar zaman damgalı dörtlü yazılır: (özne, ilişki, nesne, zaman). İki görev
ayrılır: **interpolasyon** (geçmişteki eksik bağı doldurma) ve **ekstrapolasyon**
(ileriye tahmin — daima daha belirsiz, ayrı etiketlenir). Zamansal akıl yürütme
yolu (temporal reasoning path) açık yazılır. KORKULUK: eşzamanlılık ≠ öncülük;
öncülük iddiası ölçülmeden kabul edilmez (bkz. bu depodaki K6/öncülük testi
örneği: eşzamanlı ρ yüksekken 1-bar öncülük sıfır çıkabilir).

## Zorunlu sınama döngüsü (her bağ hipotezi için — kullanıcının komutları)

1. **Pre-Mortem:** "Bu bağ yanlış çıktı — neden?" Riskleri yaz.
2. **Steelman:** Bağın EN GÜÇLÜ alternatif açıklamasını kur (üçüncü değişken,
   ters yön, tesadüf, veri artefaktı).
3. **Red Team:** Bağa VE alternatifine birden saldır; ayakta kalanı raporla.
Sonuç üç etiketten biri: **SAĞLAM** (üç testten geçti) / **ZAYIF** (kısmen) /
**ÇÜRÜDÜ** (rapora "çürütüldü" olarak yazılır — sessizce silinmez).

## Sert yasaklar

- **HAFIZA YASAĞI:** kaynağı gösterilemeyen (dosya/koşu/ölçüm/doküman-atfı
  olmayan) bağ kurulamaz.
- **DAİRESEL YASAĞI:** bağ, kendisinden türetilen bir sonuçla doğrulanamaz;
  doğrulama bağımsız kanıtla yapılır.
- **TÜNEL YASAĞI:** tek yöntem grubuyla yetinilmez (≥2 grup); tek kanıt
  ailesine dayanan bağ "TEK-KAYNAK" diye işaretlenir.
- **TARAF YASAĞI:** beklenen/istenen sonuca göre bağ seçilmez; aleyhte bağlar
  da haritaya girer.

## Çıktı biçimi: BAĞ HARİTASI

| # | Olay/Problem A | ilişki | Olay/Problem B | Grup | Kanıt sınıfı | PM/SM/RT | Hüküm |
|---|---|---|---|---|---|---|---|
(+ altına: çürüyen bağlar listesi + "VERİ YOK" kalan sorular. Harita bir KARAR
değildir; karar, ilgili karar motorunun/kapıların işidir.)

## Örnekler

- "OI düşerken fiyat yükseldi, funding negatife döndü, likidasyonlar arttı —
  bunlar bağlantılı mı?" → G1 (zincir) + G4 (zaman sırası) + G3 (harita).
- "Bu hata deseni geçen ayki olaya benziyor" → G2 (analoji: hangi yapı
  taşınıyor?) + G1 (mekanizma aynı mı?).
- "İki sembol aynı anda düştü; biri diğerini mi sürükledi?" → G4 (öncülük ölç,
  varsayma) + G1 (müdahale/karşı-olgu).
