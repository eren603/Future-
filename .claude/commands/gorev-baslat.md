---
description: Kod/mühendislik görevini uçtan uca, otonom while-döngüsüyle yürütür (yalnız görevi yaz, gerisi otomatik)
---

Aşağıdaki görevi uçtan uca, sırasını bozmadan, hiçbir fazı atlamadan yürüt. Bu bir kod/mühendislik pipeline'ıdır (piyasa analizi DEĞİL — bu depoda piyasa analizi ayrı, `piramit-sistem` üzerinden otomatik yürür).

GÖREV: $ARGUMENTS

Görev boşsa, devam etmeden önce görevi sor ve bekle.

## FAZ 0 — İzolasyon
`using-git-worktrees` becerisini uygula: görev için ana çalışma alanından izole bir alan aç.

## FAZ 1 — Niyet
`brainstorming` becerisini uygula: gereksinim ve yaklaşım netleşmeden sonraki faza geçme.

## FAZ 2 — Plan
`writing-plans` ile çok-adımlı uygulama planı yaz. Ardından `executing-plans` ile planı gözden geçirme kontrol noktalarıyla yürüt.

## FAZ 3 — Kanıt (koşullu)
Görev sayısal bir iddia/hesap/veri içeriyorsa `data-analysis-deep-scan` ile doğrula. İçermiyorsa atla ve neden atladığını tek satırda belirt.

## FAZ 4-6 — WHILE DÖNGÜSÜ (bitiş koşulu sağlanana kadar tekrarla)
Bitiş koşulu: **tüm testler geçene VE `verification-before-completion` iki ardışık turda "GEÇTİ" diyene kadar** dur, aksi halde döngüye devam et.

Her turda:
1. `test-driven-development` — önce test yaz, sonra kodu yaz (özellik/bugfix ayrımı gözet).
2. Hata/başarısız test varsa `systematic-debugging` — kök nedene inmeden düzeltme YASAK, doğrudan yama yapma.
2.5. **DENETÇİ KATMANI** — adım 1-2'nin ürettiği değişiklik adım 3'e girmeden önce 6 kapıdan geçer (aşağıdaki bölüm). Herhangi biri FAIL ise CEZA + AYNI görev maddesiyle adım 1'e dön; hepsi PASS ise adım 3'e geç.
3. `verification-before-completion` — "tamamlandı/düzeldi" demeden ÖNCE taze doğrulama komutunu çalıştır ve çıktısını göster. Geçmezse 1'e dön; geçtiyse bu turu "GEÇTİ" say.
4. Bağımsız 2+ alt görev varsa (paralelleştirilebilir), döngü adımlarını `dispatching-parallel-agents` veya `subagent-driven-development` ile paralel ajanlara böl — sıralı çalıştırma yerine. **HER paralel alt-ajanın çıktısı da adım 2.5'teki 6 kapıdan geçmeden birleştirilmez/kabul edilmez** (bkz. "Parti toplama noktası").

İki ardışık turda "GEÇTİ" alınmadan döngüden çıkma.

### DENETÇİ KATMANI (her alt-ajanın önüne konan zorunlu kapı)

**Konum:** Ayrı bir faz DEĞİLDİR; adım 1-2'nin (ve adım 4'te paralel dağıtılan HER alt-ajanın) ürettiği değişikliğin adım 3'e (`verification-before-completion`) girmeden önce geçmesi GEREKEN bir kapıdır:

```
[Ajan görev maddesini yürütür: adım 1 TDD, gerekirse adım 2 debug]
        ↓ ajan "DONE / tamamladım" der
  DENETÇİ KATMANI — izole spawn, 6 bağımsız kapı, hepsi PASS olmalı
        ↓ PASS                                ↓ herhangi biri FAIL/DOĞRULANAMADI
  adım 3: verification-before-completion       CEZA (+1) → AYNI görev maddesiyle
        ↓                                      adım 1'den TAZE ajanla yeniden başla
  sıradaki madde / paralel birleştirme
```

Paralel dağıtımda (adım 4), her kardeş ajanın çıktısı önce KENDİ 1-5 kapılarından bağımsız geçer; 6. kapı (ÇARPIŞMA/KOPYA) yalnız PARTİ TOPLANDIKTAN sonra, tüm kardeşlerin diff'leri birlikteyken çalışır (bkz. "Parti toplama noktası").

**İzolasyon — spawn sözleşmesi (dairesel doğrulamayı yapısal olarak kapatan mekanizma):** Denetçi bir "kural" olarak değil bir SÜREÇ olarak izole edilir — "incelediği ajanla bağlamı paylaşmam" gibi bir öz-beyan yeterli sayılmaz, çünkü denetçi ÇALIŞAN ajanla AYNI oturumda/bağlam penceresinde koşarsa ajanın anlatısı zaten context'te mevcut olur ve "okumadım" demesi bunu garanti etmez. Bunun yerine orkestratör her seferinde `dispatching-parallel-agents`/`subagent-driven-development` ile AYNI spawn mekanizmasıyla **taze bir alt-ajan** başlatır (kalıcı rol tanımı `.claude/agents/kod-denetci.md`; araç seti `Read, Glob, Grep, Bash` — Bash yalnız `git diff`/`git log` ve doğrulama komutunu KENDİSİ yeniden çalıştırmak için, dosya YAZMAZ). Bu alt-ajanın konuşma geçmişi BOŞTUR; ilk ve tek mesajı sabit, minimal bir şemadır:

```json
{"gorev_maddesi": "<plan.md'deki maddenin BİREBİR metni + madde no>",
 "artefakt_yolu": ["<BASE→HEAD git diff komutu>", "<doğrulama komutu>"]}
```

**Negatif liste (sözleşme gereği verilmez; sızarsa denetim GEÇERSİZDİR ve yalnız yukarıdaki şablonla YENİDEN başlatılır):** çalışan ajanın sohbet dökümü, ajanın "GEÇTİ/yaptım" dediği cümleler, plan.md'nin gerekçe/anlatı bölümleri, diğer ajanların çıktısı, önceki denetim turlarının sonucu. Ajanın rapor/özet metni verilecekse bile o KANIT değil yalnız SINANACAK hipotez kümesidir — denetçinin hükmü ona değil, kendi ürettiği ölçüme dayanır.

**Girdi (hepsi artefakt — ajanın sözü hiçbirine kanıt olarak girmez):**
1. Görev maddesinin tam metni (`writing-plans` çıktısı — plan dosyasındaki "Task N").
2. O maddenin BASE→HEAD `git diff`'i (worktree'den, taze — ajanın "ne yaptım" açıklaması değil).
3. Ajanın rapor/özet metni — yalnız SINANACAK hipotez kümesi olarak; kanıt sayılmaz.
4. Varsa test/komut çalıştırma logu — denetçi bunu görmezden gelip komutu KENDİSİ yeniden çalıştırır (`verification-before-completion` ile aynı "taze doğrulama" ilkesi); loglanan exit kodu/hash değil, denetçinin kendi ürettiği sonuç esastır.
5. Paralel partideyse: partideki TÜM kardeş diff'ler (yalnız kapı 6 için) — `ajan_id`/gerekçe GİZLENEREK verilir (bkz. kapı 6).
6. Plan'ın Global Constraints bölümü + varsa `brainstorming` notlarındaki alternatif-değerlendirme kaydı (yalnız kapı 5 için).

**6 kapı — her biri bağımsız PASS/FAIL; tek bir FAIL tüm maddeyi reddeder (VE mantığı, kısmi kabul yok):**

| Kapı | Sınar | Artefakt yöntemi |
|---|---|---|
| 1. ATLAMA | Plan maddesinin bir alt-kalemi hiç işlenmemiş mi | Her alt-kalem için diff'te karşılık gelen dosya/hunk aranır (Glob beklenen yol, Grep beklenen sembol/fonksiyon). Karşılıksız kalem = FAIL. Raporda "yaptım" denip diff'te hiç görünmeyen kalem de buraya girer; raporun "ilgili dosya", "gerekli testler" gibi GENEL/belirsiz referansı somut dosya yolu/komutla karşılanmıyorsa bu da ATLAMA sayılır (belirsizlik kanıt değildir). |
| 2. GİZLİ_GÜNDEM | Beyan etmediği bir gerekçeyle plan dışına çıkmış mı | Diff'in dokunduğu TÜM dosyalar maddenin beyan edilen kapsamıyla (brief + "başka kod değiştirme" kısıtı) karşılaştırılır. Kapsam dışı değişiklik VE raporda gerekçesi YOKSA = FAIL. Rapor gerekçeyi açıkça yazmışsa (ör. "X bozulduğu için Y'yi de değiştirdim") GİZLİ değildir — beyan edilmiş kapsam genişlemesi ayrı bir insan kararıdır, bu kapıyı düşürmez. |
| 3. TİYATRO | "Yaptım/geçti" dediği artefaktla doğrulanmıyor mu | Test dosyası gerçekten var mı, boş/anlamsız assertion (`expect(true).toBe(true)` türü) DEĞİL mi (Read ile). Doğrulama komutu denetçi tarafından KENDİSİ yeniden çalıştırılır — ajanın logu değil gerçek exit code/stdout esas alınır. Komut hiç çalıştırılmamışsa ya da FAIL veriyorken rapor "geçti" diyorsa = FAIL. Denetçi komutu ortam kısıtı yüzünden (izin/bağımlılık) KENDİSİ hiç çalıştıramıyorsa sonuç sessizce PASS'e düşürülmez — **DOĞRULANAMADI** olarak FAIL muamelesi görür (fail-closed); aynı ortam engeli 3 denemede de tekrarlarsa bu ajan ihlali değil altyapı sorunudur ve eskalasyon raporunda AYRICA "ortam/araç sorunu" diye etiketlenir. |
| 4. SAHTE_KANIT | Var olmayan dosya/ölçüm/sonuç iddia etmiş mi | Rapordaki HER somut referans (dosya yolu, fonksiyon adı, satır no, sayı/ölçüm) tek tek Read/Glob/Grep ile aranır. Bulunamayan referans = FAIL. Ayrım: kanıt hiç YOKSA/uydurmaysa SAHTE_KANIT; kanıt VAR ama iddiayı desteklemiyorsa (test var ama FAIL veriyor) TİYATRO'dur — ikisi karıştırılmaz. (CLAUDE.md'deki `iddia_denetle.py` disiplininin — "metindeki her sayı kaynağında birebir var mı" — kod alanına taşınmış hali.) |
| 5. TÜNEL | Tek yaklaşıma/kanıta saplanıp alternatif hiç değerlendirilmemiş mi | Yalnız madde GERÇEK bir tasarım/yaklaşım kararı içeriyorsa uygulanır (mekanik maddelerde N/A — yanlış-pozitif üretmemek için). Plan/brainstorm notlarında ve raporda alternatif/trade-off hiç anılmamışsa = FAIL. |
| 6. ÇARPIŞMA/KOPYA | Paralel ajanlar birbirinin işine çarpmış ya da birbirini kopyalamış mı | Yalnız parti toplandıktan sonra. Denetçiye iki diff **hangi `ajan_id`ye ait olduğu ve gerekçesi gizlenerek** verilir — yalnız içerik karşılaştırılır (taraf bilgisi hükmü etkilemesin diye). Aynı dosyanın aynı satır aralığına iki farklı içerik = ÇARPIŞMA (o bölge her iki diff'te de geçersiz). Farklı maddelere atanmış iki ajanın diff'i bayt-bayt/metinsel olarak neredeyse birebirse = KOPYA (izole bağlam ilkesi ihlal edilmiş demektir). Farklı aralığa düşüyor ve ikisi de temiz uyguluyorsa ihlal DEĞİLDİR — meşru paralel iş bölümü. **İstisna:** çakışma PLANLAMA hatasından doğduysa (iki maddeye baştan aynı dosya/scope verilmiş) ajan ihlali DEĞİLDİR — ceza işletilmez, doğrudan "PLAN DÜZELTMESİ GEREKİYOR" olarak insan operatöre eskale edilir. |

**Ceza + yeniden başlatma:**
- Herhangi bir kapı FAIL (DOĞRULANAMADI dahil) verdiğinde: (a) sicile bir satır yazılır (`denetim_sicili.md`, aşağıda), (b) o görev maddesinin sayacı +1 edilir, (c) worktree o maddenin BASE noktasına döndürülür — reddedilen diff KAYBOLMAZ, `git branch reddedilen/<madde-id>-<deneme-no>` ile arşivlenip SONRA worktree resetlenir, (d) TAZE bağlamlı bir alt-ajan (aynı brief + denetçinin somut bulgu listesi) aynı görev maddesiyle adım 1'den (TDD) yeniden dispatch edilir.
- Restart kapsamı ihlal türüne göre daralır: ATLAMA/TİYATRO/SAHTE_KANIT/TÜNEL/GİZLİ_GÜNDEM → yalnız o görev maddesi, adım 1'den (yukarıdaki akış). ÇARPIŞMA → çakışan İKİ ajanın işi TERK edilir, o alt-görev paralel değil SIRALI tek ajana yeniden dağıtılır (yarış koşulunu kökten kaldırmak için). KOPYA → yalnız kopyalayan ajanın işi TERK edilir, aynı izolasyon sözleşmesiyle (diğer ajanın çıktısını GÖRMEDEN) yeniden dağıtılır.
- Taze ajan kullanılır, önceki ajan RESUME edilmez: kanıt bütünlüğü ihlali (TİYATRO/SAHTE_KANIT/GİZLİ_GÜNDEM) bulunan bir ajanın kendi hafızası da şüphelidir; kirli bağlamdan devam ettirmek yeni bir dairesellik yaratır. Sayaç yine de görev maddesi bazında tutulur, faz değişse ya da instance değişse bile SIFIRLANMAZ ve aktarılır (izlenebilirlik + sonsuz-döngü karşıtı garantinin temeli — "her fazda temiz sayfa" YOKTUR).
- Bu ceza döngüsü `subagent-driven-development`'ın kendi 5-turluk düzeltme döngüsünden AYRIDIR: biri KANIT BÜTÜNLÜĞÜNÜ (dürüstlük), diğeri ŞARTNAME UYUMUNU (kalite) ölçer. DENETÇİ KATMANI PASS vermeden madde spec/kalite incelemesine (adım 3, SDD kullanılıyorsa onun task-reviewer'ı) hiç girmez — ucuzdan pahalıya kademe (`dogrulama-zinciri`deki "maliyet kademesi" ile aynı ilke).

**Eskalasyon — sonsuz döngü İMKÂNSIZ (yapısal garanti):**
- Sayaç 1, 2, 3'te → restart (yukarıdaki gibi, kapsamı ihlal türüne göre).
- Sayaç 3'ü GEÇERSE (4. ihlal) → restart YOK; madde `denetim_sicili.md`'de **ESKALE** olarak KİLİTLENİR (bir daha otomatik dispatch edilmez — bu kilit talimata değil sicildeki bayrağa dayanır, idempotenttir). FAZ 4-6 o madde için DURUR; döngünün bitiş koşulu ("tüm testler geçti + 2 ardışık GEÇTİ") bu madde ESKALE iken sağlanamaz, sessizce atlanmaz. İnsan operatöre bir eskalasyon dosyası sunulur: 4 denemenin TÜMÜ (hangi kapı, hangi kanıt, hangi ajan-instance, `reddedilen/*` arşiv dalları, varsa "ortam/araç sorunu" etiketi) tek raporda; onay/yön beklenmeden döngü otomatik 4. denemeye GEÇMEZ.
- Matematiksel sınır: her görev maddesi en fazla 3 restart hakkına sahiptir (sabit tavan, faz başına sıfırlanmaz) ve plan sonlu sayıda madde içerir (`writing-plans` çıktısı sonlu bir liste) → toplam olası restart sayısı ≤ 3 × madde_sayısı. Sonsuz döngü yapısal olarak İMKÂNSIZDIR; "makul davran" gibi bir talimata dayanmaz.

**Sicil dosyası:** `<FAZ 0'da açılan izole worktree>/denetim_sicili.md` (subagent-driven-development kullanılıyorsa onun `progress.md`'siyle aynı dizinde), append-only — hiçbir satır silinmez/üstüne yazılmaz; bir tur baştan başladığında önceki satırlar SUPERSEDED olarak korunur (ajan kendi ATLAMA/TİYATRO kanıtını silemez). Her satır:
`Madde <N> | Deneme <k>/3 | Ajan <instance-id> | Kapı: <ATLAMA|GİZLİ_GÜNDEM|TİYATRO|SAHTE_KANIT|TÜNEL|ÇARPIŞMA|KOPYA|DOĞRULANAMADI> | Kanıt: <tek satır — denetçinin KENDİ ürettiği ölçüm> | Karar: RESTART|ESKALE | Arşiv: reddedilen/<...>`

**Parti toplama noktası (adım 4, paralel dağıtımda):** Kardeş ajanlardan biri döndüğünde HEMEN 1-5 arası kapılardan geçirilir (bekletmeye gerek yok); 6. kapı partideki TÜM kardeşler döndükten sonra tek seferde, `ajan_id`/gerekçe gizlenmiş diff çiftleri karşılıklı taranarak çalışır. Bir kardeş 1-5 kapılarından FAIL alıp restart edilirse, 6. kapı o kardeşin YENİ diff'i geldiğinde partiyi yeniden tarar — eski/reddedilmiş diff 6. kapıya hiç girmez.

## FAZ 7 — İnceleme
`requesting-code-review` ile işini incelemeye sun. Geri bildirim gelirse `receiving-code-review` ile kanıtla değerlendir — körü körüne uygulama, teknik olarak doğrulanmadan kabul etme.

## FAZ 8 — Bitiş
`finishing-a-development-branch` ile entegrasyon kararını (merge/PR/vb.) ver.

## Kurallar
- Her fazın sonunda 1-2 cümlelik durum özeti ver (ne yapıldı, sıradaki faz ne).
- FAZ 4-6 döngüsünde kaç tur döndüğünü ve neden döndüğünü açıkça söyle — sessiz tekrar yok.
- Hiçbir fazı "gerekli değil" diye sessizce atlama; atlarsan gerekçesini yaz.
- FAZ 4-6'daki DENETÇİ KATMANI kapıları ve ceza/eskalasyon kuralı koşulsuz
  uygulanır; `denetim_sicili.md` kaydı olmayan bir "PASS" geçersizdir.
