---
name: sorusturma
description: >-
  Kök-neden soruşturma protokolü. Bir boru hattı ARIZASI incelenecekse OTOMATİK
  devreye girer — slash komutu gerekmez: motor beklenmedik sonuç verdi, boru
  hattı bir katman kapısında durdu, sicil/defter ezildi, gözlemci ihlali çıktı
  (UYDURMA / HAFIZA / DAİRESEL / EKSİK_AKTARIM / TÜNEL / MEMNUN_ETME / SIRADAN /
  ÇARPIŞMA), akıbet ölçümü kararla tutarsız, "neden böyle çıktı", "nerede
  bozuldu", "bu ihlal gerçek mi". Ham arıza yığınını dört işten geçirir:
  her bulgunun gerçek olduğunu ARTEFAKTTAN doğrula, tekrarları topla, iddia
  edilen şiddete değil TÜRETİLEN etkiye göre sırala, sahibine yönlendir.
  Çalışan motor: scripts/sorusturma.py (SORUSTURMA.json + SORUSTURMA.md üretir;
  öz-test: --self-test). Tetikleyici kelimeler (TR/EN): soruşturma, kök neden,
  root cause, arıza, hata, bozuldu, neden durdu, kapı düştü, gözlemci ihlali,
  sicil ezildi, defter, akıbet tutarsız, postmortem, triyaj, incele, teşhis,
  debug, regresyon. ⚠️ Yalnız artefakt okur; boru hattını KOŞTURMAZ, motor
  çağırmaz, ağa çıkmaz.
argument-hint: "<ariza-yolu> [--auto] [--oy N] [--depo PATH] [--yp-kurallari FILE] [--taze]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Task
  - AskUserQuestion
  - Bash(git log:*)
  - Bash(ls:*)
  - Bash(wc:*)
  - Bash(find:*)
  - Bash(python3 .claude/skills/sorusturma/scripts/sorusturma.py:*)
---

# sorusturma

Boru hattı arızasının **adversarial** soruşturması. Dört iş yapar:
her bulgunun **gerçek olduğunu doğrula**, koşular ve kaynaklar arasındaki
**tekrarları topla**, hayatta kalanları gözlemcinin/kullanıcının iddia ettiği
şiddete değil **türetilmiş etkiye göre sırala**, ve her birini bir
**bileşen sahibine** etiketle. Çıktı ham dökümü değil; kısa, sıralı,
sahiplenilmiş bir listedir.

Çağrı: `/sorusturma <ariza-yolu> [--auto] [--oy N] [--depo PATH] [--yp-kurallari FILE]`

**Argümanlar** (`$ARGUMENTS`'tan ayrıştır; `$1`/`$2` genişletmesi çalışma
ortamları arasında güvenilir DEĞİLDİR):
- arıza yolu (ilk konumsal, zorunlu): bir JSON dosyası, bir JSON dizini,
  `piramit-sistem/state/son_rapor.json`, `gozlemci.py --rapor` çıktısı,
  `state/piramit_defter.jsonl`, `engine/state/defter.jsonl`, ya da serbest
  yazılmış bir arıza notu (markdown/metin).
- `--auto`: mülakatı atla, varsayılanları kullan. Varsayılan mod
  **interaktiftir**.
- `--oy N`: bulgu başına doğrulayıcı sayısı (varsayılan 3; hızlı geçiş için 1,
  yüksek bedelli soruşturmalar için 5).
- `--depo PATH`: artefaktların kökü, **salt-okunur** (varsayılan cwd).
  Doğrulama artefakt okumaya muhtaçtır; atıf yapılan dosyalar erişilemezse
  beceri hata ile durur.
- `--yp-kurallari FILE`: dosyanın içeriğini doğrulayıcının dışlama kuralı
  listesine EKLER (Faz 3a). Kuruma/koşuya özgü emsaller için: "bu haftaki
  ETH koşularında likidasyon paneli hiç gelmedi, kapsam düşüklüğü arıza
  değil" gibi. Düz metin (satır başına bir kural) ya da `kurallar:` anahtarlı
  YAML.
- `--taze`: `./.sorusturma-state/` içindeki kontrol noktasını yok say ve
  Faz 0'dan başla. Bu bayrak olmadan, kontrol noktası varsa beceri son
  tamamlanan fazdan devam eder.

**Araçlar:** Read, Glob, Grep, Write, Task, AskUserQuestion. Bash yalnız
`git log`, `find`, `wc`, `ls` ve `python3 .claude/skills/sorusturma/scripts/sorusturma.py`
için serbesttir.

**Boru hattını KOŞTURMA.** `piramit.py`, `karar_motoru.py` ya da başka bir
motor bu soruşturma sırasında çalıştırılmaz; `engine/girdi/` altına dosya
yazılmaz; sicil (`engine/state/`, `hafiza/`) DEĞİŞTİRİLMEZ. Bir arızayı
"yeniden koşarak" doğrulamak sicili kirletir ve soruşturmanın kendisi
kanıtı bozar. Her sonuç **okunan artefakttan** çıkar. Bu kısıt orkestratör
ve her alt-ajan için geçerlidir; her Task isteminde açıkça yazılır.
Yüksek güvenli YÜKSEK bulgular için, elle kontrollü bir yeniden üretim
takip işi olarak ÖNERİLİR — soruşturmanın parçası olarak yapılmaz.

**Ağa çıkma.** Borsa/API sorgusu, paket kaydı araması, uzak veri çekme yok.

---

## Kontrol noktası (Faz 0'dan önce ve her fazdan sonra koşar)

Büyük arıza yığınlarında tam bir koşu bağlamı tüketebilir ya da yarıda
kesilebilir — özellikle Faz 3, bulgu × oy kadar doğrulayıcı üretir. Faz
durumu `./.sorusturma-state/` altına yazılır; taze bir `/sorusturma`
oturumu mülakatı yeniden sormadan ve doğrulayıcıları yeniden üretmeden
kaldığı yerden devam eder.

Tüm kontrol noktası G/Ç'si `sorusturma.py`'nin içindedir (atomik yazım:
tmp + `os.replace`; JSON doğrulamalı). `ilerleme.json`'ı Write aracıyla
elle yazma.

`./.sorusturma-state/` içindeki durum dosyaları:
- `ilerleme.json` — devam konumunun **TEK GERÇEK KAYNAĞI**:
  `{"durum": "koşuyor"|"tamam", "faz_tamam": N, "parcalar_tamam": [...]}`.
  Devam kararı YALNIZ bu dosyadan okunur; `faz*.json` ya da parça dosyaları
  **glob'lanmaz** (önceki koşudan kalan bayat dosyalara güvenilmez).
- `fazN.json` — N. fazın veri yükü.
- `parca_<id>.json` — Faz 3'te bulgu başına tally (pahalı faz).

**Koşu başında — devam denetimi.** `sorusturma.py` `ilerleme.json`'ı okur:
- `durum` yok / `tamam` / bozuk, ya da `--taze` verilmiş → **taze başlangıç**
  (durum dizini silinir, Faz 0'dan koşulur).
- `durum == "koşuyor"` ve `faz_tamam == N` → **devam**: `faz0.json` … `fazN.json`
  **sırayla** okunur ve çalışan duruma birleştirilir (sonraki dosya önceki
  anahtarı ezer — kontrol noktaları delta olabilir), stderr'e
  `Kontrol noktasından devam: Faz N tamam` basılır ve **doğrudan Faz N+1'e**
  atlanır.

**Koşu sonunda** `ilerleme.json` `durum: "tamam"` ile mühürlenir; bir sonraki
çağrının devam denetimi bunu görüp taze başlar.

---

## Faz 0: Mod seçimi ve mülakat

### 0a. Argümanları ayrıştır

`$ARGUMENTS`'tan: arıza yolu (ilk konumsal), `--auto`, `--oy N` (varsayılan 3),
`--depo PATH` (varsayılan `.`), `--yp-kurallari FILE` (varsayılan yok). Arıza
yolu verilmemişse iste ve dur. `--yp-kurallari` verilmişse dosyayı ŞİMDİ oku ve
içeriğini Faz 3a doğrulayıcı istemine enjekte edilmek üzere taşı (motor bunu
`--yp-kurallari` bayrağıyla kendisi de yükler).

### 0b. İnteraktif mod (varsayılan): kullanıcıyı mülakata al

`--auto` verilmedikçe **AskUserQuestion** ile doğrulamayı ve sıralamayı
şekillendiren bağlamı topla. En fazla dört soruluk bir-iki çağrıda topla.
Serbest metin cevap beklenir ("Diğer"); şıklar kısıt değil, uyarandır.

**Tur 1** (tek AskUserQuestion çağrısı):

1. **Kapsam ve etki sınırı** (başlık `Kapsam`, tek seçim)
   `Bu arıza hangi koşuda çıktı ve kararın hangi kısmına dokunuyor?`
   Şıklar: `Ana sembol koşusu (engine/girdi, engine/state)`,
   `İkinci sembol koşusu (engine/girdi/eth, engine/state/eth)`,
   `Kum havuzu / öz-test koşusu (gerçek sicil etkilenmiyor)`,
   `Boru hattı geneli (hangi koşu olduğu belirsiz)`,
   `Elle gelen zorunlu girdi (likidasyon paneli / görsel okuma)`.
   Ulaşılabilirlik bu sınıra göre yargılanır: kum havuzu artefaktındaki
   tutarsızlık YP kural 11'dir, aynı tutarsızlık `engine/state/` içinde
   gerçek arızadır.

2. **Etki modeli** (başlık `Etki modeli`, çok seçim)
   `Bu sistemde ASLA olmaması gereken nedir? Serbest metin en iyisidir.`
   Şıklar: `Sicil/defter kaybı veya ezilmesi`,
   `Kaynaksız (uydurma) sayının karara girmesi`,
   `Mühürlenmesi gereken koşuda emir yayınlanması`,
   `Yönün yanlış tarafa dönmesi`,
   `Bayat/eksik girdinin taze sayılması`.
   Faz 4, beyan edilen etkiye eşleşen bulguları **en fazla bir basamak**
   yükseltir.

3. **Şiddet standardı** (başlık `Şiddet`, tek seçim)
   `Şiddet çıktıda nasıl ifade edilsin?`
   Şıklar: `Ön koşullardan türetilmiş YÜKSEK/ORTA/DÜŞÜK (varsayılan)`,
   `Gözlemci kodlaması (İHLAL / UYARI / TEMİZ)`,
   `Koşu-engelleyici / karar-bozan / gürültü`,
   `Depo bug-bar'ı (Diğer'de tarif edin)`.
   Ön koşul kuralı HER DURUMDA hesaplanır; bu seçim yalnız
   `siddet_etiketi` alanının neyi ek olarak gösterdiğini belirler.

4. **Gürültü toleransı** (başlık `Gürültü toleransı`, tek seçim)
   `Doğrulayıcılar anlaşamazsa eşitlik hangi yöne bozulsun?`
   Şıklar:
   `Kesinlik: çoğunlukla doğrulanmayanı düşür (az yanlış alarm, gerçek arıza kaçabilir)`,
   `Kapsam: bölünmüş oyu elle_inceleme_gerek olarak tut (daha çok inceleme, daha az kaçak)`,
   `Olduğunda bana tek tek sor`.

**Tur 2** (koşullu): etki modeli cevabı boş/genelse ya da şiddet cevabı
"Depo bug-bar'ı" ise, tek bir hedefli takip sorusu sor.

Cevapları bir `baglam` sözlüğüne yaz, **Write ile `./.sorusturma-state/baglam.json`
dosyasına kaydet** ve motoru `--baglam ./.sorusturma-state/baglam.json` ile
çağır. Bağlam her fazda taşınır ve çıktıda `sorusturma_baglami` altında
yankılanır.

```json
{"kapsam": "...", "etki_modeli": ["..."], "siddet_standardi": "...",
 "gurultu_toleransi": "kesinlik|kapsam|sor"}
```

### 0c. Auto modu varsayılanları

`--auto` verildiğinde AskUserQuestion çağrılmaz. Kullanılan varsayılanlar:
- Kapsam: `Bilinmiyor. Boru hattının TAMAMI kapsam sayılır; hangi katman/
  motorun etkilendiği varsayımı gerekçede AÇIKÇA işaretlenir.`
- Etki modeli: boş (yükseltme yok).
- Şiddet: türetilmiş YÜKSEK/ORTA/DÜŞÜK.
- Gürültü toleransı: kesinlik.

Faz 0 sonunda `faz0.json` yazılır; devam edildiğinde mülakat **yeniden
sorulmaz**, `baglam` bu dosyadan geri yüklenir.

---

## Faz 1: Al ve normalize et

Girdiyi, kaynak biçimi ne olursa olsun, kararlı kimlikli düz bir
`bulgular[]` listesine çevir.

### 1a. Girdi şeklini tanı

- **Dizin**: `**/*.json`, `**/*.jsonl`, `**/*.md`, `**/*.txt` glob'lanır.
  Tanınan kapsayıcılar:
  - **Piramit raporu** (`son_rapor.json`, `piramit.py --out` çıktısı;
    `DENETIM`/`katmanlar` anahtarlarıyla tanınır):
    `DENETIM.ihlal[]` → İHLAL şiddetli bulgu, `DENETIM.uyari[]` → UYARI
    şiddetli bulgu (her satır `K5-SI/EKSIK_AKTARIM: gerekçe` biçiminde
    ayrıştırılır → `konum`=katman, `kategori`=ihlal kodu);
    `durum: "DURDU — <katman>"` → `KAPI` kategorili bulgu;
    `ZIRVE.ZORUNLU_EKSIK[]` → `ZORUNLU_GIRDI`; `ZIRVE.ONCEKI_AKIBET.durum`
    içinde "HATA" geçiyorsa → `AKIBET`. Raporun **kendisi artefakttır**:
    bu bulguların `dosya` alanı rapor yoludur.
  - **Gözlemci çıktısı** (`gozlemci.py --rapor`; `gozlemciler` anahtarı):
    aynı `ihlal`/`uyari` çıkarımı.
  - **`*defter*.jsonl`** (`engine/state/defter.jsonl`,
    `state/piramit_defter.jsonl`): `duzeltme_notu` ya da `r_iptal_nedeni`
    taşıyan satır → `SICIL_EZILME`; `durum` alanı `DURDU` ile başlayan
    satır → `KAPI`; diğerleri alan sözlüğüyle normalize edilir.
  - Üst düzeyi obje listesi olan ya da
    `arizalar`/`bulgular`/`ihlaller`/`kayitlar`/`findings` dizisi taşıyan
    her `*.json`: o dizi.
- **Tek `.json` / `.jsonl` dosyası**: yukarıdakiyle aynı tanıma.
- **Markdown / metin**: 2./3. seviye başlıklara ya da `---` çizgilerine
  bölünür; her bölümden `Dosya:`, `Katman:`, `Kod:`, `Şiddet:`, `Belirti:`
  etiketleriyle ya da `dosya.py:NN` kalıbıyla alan çıkarılır. En iyi çaba;
  `_bicim: "markdown_sezgisel"` işaretlenir.

Ayrıştırılabilir hiçbir şey yoksa dur ve ne görüldüğünü bildir — **uydurma
bulgu üretilmez.**

### 1b. Alanları normalize et

Her ham kayıt için bir bulgu sözlüğü kur. **Var olanı al; olmayanı ASLA
tahmin etme.** Alan sözlüğü (kaynak-anahtar takma adları → kanonik):

| Kanonik            | Ayrıca kabul edilen                                        |
|--------------------|------------------------------------------------------------|
| `dosya`            | `artefakt`, `file`, `path`, `kaynak_dosya`, `rapor`         |
| `konum`            | `katman`, `alan`, `satir`, `line`, `faz`, `motor`           |
| `kategori`         | `kod`, `ihlal_kodu`, `type`, `sinif`, `rule_id`             |
| `siddet`           | `durum`, `severity`, `seviye`, `level`, `risk`              |
| `baslik`           | `ozet`, `title`, `mesaj`, `summary`                         |
| `belirti`          | `kanit`, `description`, `detay`, `aciklama`, `evidence`     |
| `tekrar_senaryosu` | `senaryo`, `repro`, `nasil`, `adimlar`                      |
| `on_kosullar`      | `kosullar`, `preconditions`, `varsayimlar`                  |
| `oneri`            | `duzeltme`, `fix`, `remediation`, `recommendation`          |
| `tarayici_guveni`  | `guven`, `confidence`, `skor` (0.0-1.0'a normalize)         |

Her bulguya eklenir:
- `id`: `a001`, `a002`, … alım sırasına göre. Kayıtların çoğunda
  `tarayici_guveni` varsa alım bu değere göre azalan sıralanır — böylece
  yüksek sinyalli bulgular önce doğrulanır. Bu YALNIZ bir çizelgeleme
  önceliğidir; **hükmü etkilemez**.
- `kaynak`: kaydın geldiği dosya (artefakt yolundan AYRI tutulur —
  kapsayıcı dosyanın kendisi kanıt değildir).
- `eksik_alanlar`: bulunamayan kanonik alanların listesi.
- `dosya` yoksa ya da `--depo` altında çözülmüyorsa bulgu
  **yerelleştirilemez**: tekilleştirmeye ve doğrulamaya GİRMEZ, doğrudan
  `hukum: yanlis_pozitif`, `dogrulama_hukmu: elle_inceleme_gerek`,
  `guven: 0`, `curutme_nedenleri: ["kanit_yok"]` ve
  `gerekce: "girdide artefakt yolu yok; statik olarak doğrulanamaz, elle
  inceleme gerekir"` ile yayımlanır. Yerini bulamadığın bir bulguya asla
  kendinden emin hüküm verme; ne yutsun ne yutulsun.

### 1c. Artefakt kökünü bul

`--depo` çözülür (varsayılan cwd). `dosya` alanı olan ilk 5 bulgu için yol
şu sırayla denenir: (a) `depo/dosya`; (b) `dosya` mutlak ya da cwd-göreli;
(c) `dosya`dan yaygın önek soyularak (`src/`, `app/`, `./` veya deponun
kendi taban adı). Hangi çözüm tuttuysa kaydedilir ve tüm bulgulara
uygulanır. Hiçbiri çözülmezse **dur**: doğrulamanın artefakt okumaya
muhtaç olduğunu ve atıf yapılan dosyaların erişilemediğini söyle,
gördüğün en uzun ortak son-eke dayanan bir `--depo` değeri öner.

---

## Faz 2: Tekilleştir (doğrulamadan ÖNCE)

Tekrarları topla ki aynı kök neden N doğrulayıcıyı ayrı ayrı yakmasın.

> Kaynak protokolün tasarım notu, sıranın **kasıtlı** olduğunu söyler:
> *"**Dedupe runs before verify** to cut verifier spend by the duplication
> factor (often 2-4x on multi-scanner input) at the cost of one cheap
> subagent."* Bu depoda çoğaltma faktörü daha da yüksektir: aynı kök neden
> gözlemcinin `ihlal` listesinde, `gozlemciler` bloğunda ve `ZIRVE.DENETIM`
> özetinde ÜÇ KEZ görünür.

### 2a. Determinist geçiş (yerinde, alt-ajansız)

Şu ÜÇÜ birden tutan bulgular kümelenir:
- aynı `dosya` (yol normalizasyonundan sonra), VE
- aynı `kategori` (büyük/küçük harf ve noktalama duyarsız), VE
- `konum` birbirine yakın: iki taraf da sayıysa fark ≤ 10; metinse birebir
  eşit (katman adı gibi). **İki tarafta da eksikse eşleşir; tek tarafta
  eksikse EŞLEŞMEZ** (konumsuz bir kayıt, konumu bilinen bir kaydı
  yutamaz).

Her kümede kanonik, **en az `eksik_alanlar`** taşıyan kayıttır; eşitlikte
en küçük `id`. Diğer her üye `hukum: kopya`, `kopyasi: <kanonik id>` alır
ve çalışan kümeden çıkarılır. Kopya id'leri kanoniğe `yuttuklari: [...]`
olarak yazılır.

### 2b. Anlamsal geçiş (tek alt-ajan, yalnız >1 küme hayatta kaldıysa)

`subagent_type: "general-purpose"` ile TEK Task aç:

```
Pahalı doğrulamadan önce boru hattı arızası bulgularını tekilleştiriyorsun.
İki bulgu, BİRİNİ düzeltmek diğerini de düzeltiyorsa KOPYADIR. Kategori ya
da dosya paylaşsalar bile kök nedenleri gerçekten bağımsızsa AYRIDIR.

KOPYA say:
- Aynı kök neden, farklı sözcüklerle ya da farklı katmanın gözlemcisince
  yazılmış (ör. K3'te "danışman kurula girmedi", K5'te "sentezde eksik")
- Tek bir motorun düşmesinin her tüketicide ayrı ayrı raporlanması
- Bir eksik korkuluğun (kapı uygulanmaması) her etkilenen koşuda tekrarı
- Bir neden ("kıyas motoru koşmadı") ile sonucu ("hesap verme satırı boş")

AYRI say:
- Aynı katmanda farklı ihlal kodları (bir UYDURMA ile yanındaki TÜNEL,
  satırları yakın diye kopya değildir)
- Aynı kod, aynı katman, ama farklı motor/danışman kaynaklı
- Aynı dosyada birbirinden bağımsız iki hata
- Aynı korkuluğun iki ayrı sembolde (ana/ikinci) düşmesi, düzeltme
  sembol başına ayrıysa

Aşağıda adaylar var (satır başına bir tane: id | dosya:konum | kategori |
başlık). Grupla. YALNIZCA şu biçimde satırlar yaz:

  GRUP: <kanonik_id> <- <kopya_id>, <kopya_id>, ...

Kopyası olan her grup için bir satır. Tek başına kalanları yazma. En
spesifik / en iyi tarif edilmiş bulguyu kanonik seç. Düz metin YOK.

ADAYLAR:
{hayatta kalan her bulgu için bir satır: "a003 | state/son_rapor.json:K5-SI | EKSIK_AKTARIM | K3 danışmanı sentezе girmedi"}
```

`GRUP:` satırlarını ayrıştır, listelenen kopyaları işaretle ve çalışan
kümeden düşür. Sonucu motora `--oy-dosyasi` yerine doğrudan girdi
düzeltmesi olarak taşı (motorun determinist geçişi zaten koşmuştur;
anlamsal geçiş yalnız onun kaçırdığı kümeleri ekler).

`adaylar[]` = hayatta kalan kanonikler.

---

## Faz 3: Doğrula

Her aday için N bağımsız **adversarial** doğrulayıcı, iddiayı artefakttan
YENİDEN türetir ve oy verir. Her doğrulayıcının duruşu "bunun yanlış
olmasının herhangi bir nedenini bul"dur. Her biri gözlemcinin/kullanıcının
tarifinden değil **artefaktın kendisinden** başlar ve diğer doğrulayıcıların
muhakemesini **görmez** (paylaşılan bağlam kör noktayı çoğaltır).

Doğrulama iki kaynaktan gelir ve **birleştirilir**:

1. **Mekanik mercekler** (`sorusturma.py` içinde, her koşuda): `artefakt`
   (kanıt dosyada birebir var mı), `yp_kural` (yanlış-pozitif kuralları),
   `tasarim` (deponun KENDİ sözleşmesi ne diyor), `tekrar` (koşular boyunca
   yineleniyor mu), `celiski` (çürüten karşı artefakt var mı). `--oy N`
   bu sıradan ilk N merceği koşturur.
2. **LLM doğrulayıcıları** (aşağıdaki istem, Task ile): anlam gerektiren
   bulgular için. Oyları `{"a001": [{...}, {...}]}` biçiminde bir JSON'a
   Write ile yazılır ve motora `--oy-dosyasi` ile verilir; mekanik
   merceklerin oylarıyla AYNI havuzda sayılır.

### 3a. Doğrulayıcı istemi (bir kez kur, her spawn'da tekrar kullan)

```
Bir finans karar-destek boru hattının TEK bir arıza bulgusunu adversarial
olarak doğruluyorsun. Varsayılan varsayımın: RAPOR EDEN YANILIYOR. Görevin
iddiayı artefakttan kendin yeniden türetip GERCEK_ARIZA ya da
YANLIS_POZITIF demek.

Artefakt köküne SALT-OKUNUR erişimin var: {DEPO}
Read, Glob ve Grep kullanabilirsin, YALNIZ {DEPO} içindeki yollarda.
Bu kökün dışını okuma/grep'leme: dışarısı (başka depolar, geçmiş koşu
yedekleri) kapsam dışıdır ve oraya atıf vermek hükmünü kirletir. Bir
bulgunun `dosya` alanı {DEPO} dışına çözülüyorsa DOGRULANAMADI +
CURUTME_NEDENI: kanit_yok döndür.

HİÇBİR MOTORU ÇALIŞTIRMA. piramit.py, karar_motoru.py, sentez.py ya da
başka bir motoru koşturma; engine/girdi'ye yazma; engine/state ya da
hafiza altındaki hiçbir dosyayı DEĞİŞTİRME; ağa çıkma. Arızayı "yeniden
koşarak" doğrulamak sicili kirletir ve kanıtı bozar. Her sonucun okunan
artefakttan çıkmalı.

KAPSAM (operatörden; ulaşılabilirlik sınırını bu belirler):
{baglam.kapsam veya "Bilinmiyor. Boru hattının TAMAMI kapsam sayılır;
trust sınırı varsayımlarını gerekçede AÇIKÇA işaretle."}

────────────────────────────────────────────────────────────────────────
YORDAM: dört adımın hepsini uygula. Her biri, atlanınca belirli bir
yanlış-pozitif sınıfının içeri sızmasına izin verdiği için vardır.

1. ATIF YAPILAN ARTEFAKTI KENDİN OKU.
   {dosya} dosyasını {konum} noktasında aç. Değerlerin gerçekte ne
   olduğunu gör. Rapor edenin tarifine GÜVENME: gözlemci mesajları
   kısaltılmıştır ve özetten başlarsan onun okuma hatasını devralırsın.

2. ZİNCİRİ GERİYE, ÜRETİCİ MOTORA DOĞRU İZLE.
   Bu sayı/alan hangi motorun çıktısı? `piramit.py` içinde hangi katmanda
   üretildi, hangi kapıdan geçti? Alt katmanda kaynağı var mı? Kulağa
   makul gelen bir zincir YETMEZ: zincirin EN AZ İLK HALKASI için gerçek
   üretim noktasını OKU ve gerekçende `dosya:satır` olarak ALINTILA.
   Kaynaksız sayı (üst katmanda var, altta yok) bu depodaki en büyük
   gerçek-arıza sınıfıdır; tersine, kaynağı bulunan sayı en büyük
   yanlış-pozitif sınıfıdır.

3. KORKULUKLARI ARA.
   Bulgunun YANLIŞ olmasının nedenlerini etkin biçimde ara:
   - Kapı zaten düşürmüş mü (fail-closed davranış çalışmış mı)
   - Gözlemci mührü devrede mi (`muhurlendi: true` → emir kapanmış)
   - Eksik kanal "VERİ YOK" diye ETİKETLENMİŞ mi (sessizce düşmemiş mi)
   - `rr_denetim` / `usd_hedef` / `esik_kalibre` kapılarından geçmiş mi
   - Değer bir KONVANSİYON/yapı sabiti mi (kalibrasyon değil, beyan edilmiş)
   - Artefakt kum havuzu / öz-test koşusuna mı ait (gerçek sicil değil)

4. HER KORKULUĞU ZORLA.
   Bulduğun her korkuluk için: HER yolda mı uygulanıyor, yoksa yalnız
   raporun izlediği yolda mı? Mühür varken emir gerçekten kapandı mı,
   yoksa `ZIRVE.EMIR` hâlâ seviye taşıyor mu? "VERİ YOK" etiketi kararın
   ağırlığına gerçekten yansımış mı?

────────────────────────────────────────────────────────────────────────
DIŞLAMA KURALLARI: bulgu bunlardan birine uyuyorsa, TEKNİK OLARAK DOĞRU
OLSA BİLE YANLIS_POZITIF'tir. Hükmünde kural numarasını AN.

Kurallar `kurallar/yanlis_pozitif.yaml` dosyasındadır (13 kural). Özet:
  1 kapı düşmesi/DURDU = fail-closed TASARIM (istisna: motor çöktü)
  2 BEKLE = işlem-kalitesi hükmü, yön reddi değil (istisna: YÖN gizlendi)
  3 çelişki turu → NÖTR = fail-closed (istisna: karar yönlü kaldı)
  4 mühürün devreye girmesi korkuluğun ÇALIŞTIĞIDIR (mührü tetikleyen
    ihlal AYRI bulgudur)
  5 "VERİ YOK" beyanı dürüstlük sözleşmesidir (istisna: sessizce düştü)
  6 TÜNEL uyarısı tek başına VERİ EKSİKLİĞİDİR, kod arızası değil
  7 "bekleme penceresi henüz dolmadı" muhafazakâr ölçüm kuralıdır
  8 etiketli STATİK KORKULUK fail-closed'dur (istisna: etiketsiz gizli eşik)
  9 kayıt yokken kıyas yapılmaması dürüstlüktür (istisna: kayıt VAR)
 10 görsel okumanın 0.50 güven tavanı sözleşmedir
 11 kum havuzu / öz-test artefaktı gerçek sicili etkilemez
 12 R < 1.35 reddi depo risk kuralıdır (istisna: rr_denetim hiç koşmadı)
 13 damgasız/bayat okumanın reddi tazelik sözleşmesidir

{--yp-kurallari verilmişse buraya "KOŞUYA ÖZGÜ KURALLAR:" başlığı altında
 aynen eklenir}

────────────────────────────────────────────────────────────────────────
HÜKÜM: cevabın TAM OLARAK bu blokla bitmeli:

  HUKUM: GERCEK_ARIZA | YANLIS_POZITIF | DOGRULANAMADI
  GUVEN: <0-10>
  CURUTME_NEDENI: <şunlardan biri: kanit_yok, zaten_ele_alinmis,
    tekrarlanamaz, tasarim_geregi, artefakt_yanlis_okunmus, kopya,
    uygulanabilir_degil, yok>
  YP_KURALI: <1-13, koşuya özgü kural, ya da yok>
  ILK_KANIT: <okuduğun ilk üretim noktasının dosya:satır'ı, ya da "yok">
  GEREKCE: <2-5 cümle; ulaşılabilirlik, bulunan/bulunmayan korkuluklar ve
    her birinin neden tuttuğu/tutmadığı için dosya:satır alıntısı ver>

GERCEK_ARIZA için ŞUNLARIN HEPSİ gerekir: belirti artefaktta doğrulanıyor;
korkuluklar yetersiz ya da atlanabiliyor; arıza kararın kalitesini ya da
sicilin bütünlüğünü gerçekten bozuyor.

YANLIS_POZITIF için ŞUNLARDAN BİRİ yeter: artefakt iddiayı desteklemiyor;
korkuluk zaten devrede; rapor eden artefaktı yanlış okumuş; bir dışlama
kuralı tutuyor.

DOGRULANAMADI: statik muhakeme gerçekten sınırına dayandı (ör. davranış
okunamayan bir koşu-anı durumuna bağlı, ya da kanıt o koşunun veri
penceresinin dışında). İdareli kullan; VARSAYILAN HÂLİNE GELMEMELİ.
```

### 3b. Aday başına N doğrulayıcı, hepsi TEK mesajda

`adaylar[]` içindeki her bulgu için N Task çağrısı kur (N = `--oy`,
varsayılan 3), `subagent_type: "general-purpose"`,
`description: "doğrula {id} oy {k}/{N}"`.

**`subagent_type`'ı DAİMA ver; asla fork etme.** `subagent_type`
atlanırsa orkestratör fork edilir ve fork tüm konuşma bağlamını devralır:
diğer her bulgunun tarifi, gözlemcinin nesri, önceki doğrulayıcıların
sonuçları. Bu, doğrulayıcı bağımsızlığını yok eder ve bu fazın var olma
nedeni olan devralınmış-çerçeve arızasını geri getirir. Her doğrulayıcı
taze, boş bağlamla başlamalı ve YALNIZ 3a istemini + incelenen tek
bulguyu almalıdır. Aynısı 4a'daki sıralama alt-ajanları için de geçerlidir.

Her isteme 3a'nın sonuna şu blok eklenir:

```
────────────────────────────────────────────────────────────────────────
İNCELENEN BULGU (rapor edenden geldi; GERÇEK değil İDDİA say):

  id:        {id}
  dosya:     {dosya}
  konum:     {konum}
  kategori:  {kategori}
  iddia edilen şiddet: {siddet}
  başlık:    {baslik}

  belirti:
  {belirti}

  tekrar senaryosu:
  {tekrar_senaryosu ya da "(verilmedi)"}

  iddia edilen ön koşullar:
  {on_kosullar madde madde ya da "(verilmedi)"}

Sen {N} oydan {k}. numarasısın. Diğer doğrulayıcıların muhakemesini
GÖRMEDİN ve onu ARAMAMALISIN. Artefakttan bağımsız çalış.
```

**Tüm doğrulayıcı Task çağrılarını tek bir asistan mesajına koy** ki
eşzamanlı koşsunlar. `run_in_background` verme; async tutamaç değil nihai
metin gerekiyor. `len(adaylar) * N` ~40'ı aşarsa ~40'lık ardışık partilere
böl, ama her parti tek mesaj kalsın.

**Bir Task çağrısı doğrulayıcı metni yerine `status: "async_launched"`
dönerse**, çalışma ortamı onu arka plana almıştır. Bir kurtarma seç ve
tüm parti için onu uygula:
  - Tamamlanma bildirimleri konuşmaya düşüyorsa: her doğrulayıcının HUKUM
    bloğunu bildirimin `result` alanından ayrıştır. Her oy hesaba
    katılmadan turunu bitirme.
  - Bildirim gelmiyorsa: transkript dosyalarını yoklama. Eksik
    doğrulayıcıları taze ve daha küçük (ör. 10) bir Task partisinde
    yeniden üret ve senkron sonuçları kullan.
Aynı kurtarma 2b'deki tekilleştirme alt-ajanı ve 4a'daki sıralama
alt-ajanları için de geçerlidir.

Oyları `{"a001": [{"hukum": "...", "guven": 8, "curutme_nedeni": "...",
"yp_kurali": null, "ilk_kanit": "piramit.py:1024", "gerekce": "..."}]}`
biçiminde Write ile yaz ve motoru `--oy-dosyasi` ile çağır.

**`dosya`'sı olup `konum`'u olmayan bulgular `--oy` ne olursa olsun TEK
oy alır** (dosya düzeyinde tarama pahalıdır ve oylamadan fayda görmez).

### 3c. Oyları say

Her aday için her doğrulayıcının kuyruk bloğu ayrıştırılır (kod çiti ve
boşluğa tolerans). Bir doğrulayıcı hata verdiyse, zaman aşımına uğradıysa
ya da ayrıştırılabilir HUKUM bloğu üretmediyse bir kez yeniden üret.
Tekrar da başarısızsa o oy `dogrulanamadi`, `guven: 0` sayılır ve
`curutme_nedenleri`ne `"dogrulayici_hatasi"` yazılır. Kalan N-1 oy yine
karar verir.

Kurulan alanlar:
- `oy_dagilimi`: `{"gercek_ariza": x, "yanlis_pozitif": y, "dogrulanamadi": z}`
- `guven`: çoğunlukla aynı yönde oy verenlerin GUVEN ortalaması, bir ondalık
- `yp_kurali`: YANLIS_POZITIF oyları arasındaki modal YP_KURALI, yoksa `null`
- `curutme_nedenleri`: YANLIS_POZITIF oylarından sıralı benzersiz nedenler
- `ilk_kanitlar`: tüm oylardaki benzersiz ILK_KANIT değerleri (izlenebilirlik)
- `gerekce`: kazanan taraftaki en yüksek güvenli oyun GEREKCE'si, **birebir**

**`hukum` kararı:**
- Çoğunluk GERCEK_ARIZA → `hukum: gercek_ariza`. Faz 4'e geçer.
- Çoğunluk YANLIS_POZITIF → `hukum: yanlis_pozitif`. Faz 4'ü atlar.
- Çoğunluk yok (eşitlik ya da çoğunluk DOGRULANAMADI):
  - Gürültü toleransı `kesinlik` → `hukum: yanlis_pozitif`; gerekçeye
    `"(oy bölündü, kesinlik politikasıyla düşürüldü)"` eklenir.
  - `kapsam` → `hukum: gercek_ariza` + `dogrulama_hukmu: elle_inceleme_gerek`.
  - `sor` → bölünmüş bulgular toplanır ve Faz 3'ün sonunda TEK
    AskUserQuestion çağrısında sunulur (başlık: id + başlık; şıklar:
    tut / düşür), sonra kullanıcının seçimi uygulanır. (Motor `--auto`
    altında kesinliğe düşer ve bulguları `ozet.bolunmus_oylar` altında
    listeler.)

**YP KURALI VETOSU.** Kaynak sözleşmesinde dışlama kuralları HER
doğrulayıcının önündedir; yani bir kural tek bir oyla geçiştirilemez. Bir
YP kuralı (istisnası tutmadan) eşleşiyorsa motor TÜM oyları
YANLIS_POZITIF'e çevirir ve her merceğin kendi bulgusunu gerekçede korur
(`yp_veto` alanı kural numarasını taşır).

`onaylanan[]` = `hukum == gercek_ariza` olan adaylar.

Bu en pahalı fazdır: her aday tally'lenir tally'lenmez
`parca_<id>.json` yazılır ve `ilerleme.json:parcalar_tamam` güncellenir.
`faz_tamam == 2` iken devam edildiğinde motor YALNIZ `parcalar_tamam`
listesini okur (disktekі parça dosyalarını **glob'lamaz**; önceki koşudan
bayat parçalar kalmış olabilir) ve yalnız listede OLMAYAN adaylar için
doğrulayıcı üretir.

---

## Faz 4: Etkiye göre sırala (yalnız onaylanan bulgular)

Şiddeti kategori adından değil **ön koşullardan ve tekrar koşulundan**
yeniden hesapla; rapor edenin iddia ettiği şiddeti AYRICA yargıla.
Doğrulama ile şiddet bağımsız yargılardır: "bu gerçek" hükmü "bu kritik"e
şişmemelidir.

### 4a. Sıralama istemi

Onaylanan her bulgu için bir Task (`subagent_type: "general-purpose"`,
hepsi tek mesajda). Motor bu adımın **mekanik** karşılığını her koşuda
kendisi üretir (ön koşul çıkarımı + tablo + hiza puanı); LLM sıralaması
yalnız ön koşulların anlam gerektirdiği bulgular için eklenir.

```
DOĞRULANMIŞ bir boru hattı arızasına şiddet biçiyorsun. Doğrulama zaten
yapıldı; bulgunun gerçek olduğunu varsay. Tek işin, rapor edenin
iddiasından BAĞIMSIZ olarak bunun ne kadar kötü olduğunu türetmek.

Ön koşulları denetlemek için {DEPO} altındaki artefaktları Read/Grep
edebilirsin. HİÇBİR MOTORU ÇALIŞTIRMA, hiçbir sicil dosyasına YAZMA.

KAPSAM: {baglam.kapsam}
ETKİ MODELİ (operatör beyanı, boş olabilir):
{baglam.etki_modeli madde madde ya da "(verilmedi)"}
ŞİDDET STANDARDI: {baglam.siddet_standardi}

BULGU:
  id:        {id}
  dosya:     {dosya}:{konum}
  kategori:  {kategori}
  iddia edilen şiddet: {siddet}
  kanıt izi: {Faz 3'ten ilk_kanitlar}
  doğrulayıcı gerekçesi: {Faz 3'ten gerekce}

────────────────────────────────────────────────────────────────────────
ADIM 1: Bu arızanın TEKRARLAMASI için tutması gereken HER ön koşulu say.
Somut ol: hangi sembol koşusu, hangi girdi kombinasyonu, hangi elle
müdahale, hangi rejim. Sonra asgari TEKRAR KOŞULUNU belirt
(her_kosuda / belirli_veride / elle_mudahaleyle).

ADIM 2: Şiddeti ön koşul sayısı ve tekrar koşulundan türet:

  | Ön koşul | Tekrar koşulu       | Şiddet |
  |----------|---------------------|--------|
  | 0        | her koşuda          | YÜKSEK |
  | 1-2      | belirli veride      | ORTA   |
  | 3+       | elle müdahaleyle    | DÜŞÜK  |

  İki kolonu BAĞIMSIZ değerlendir ve DÜŞÜK olanı al. Örnek: 0 ön koşul
  ama yalnız elle müdahaleyle tekrarlıyorsa DÜŞÜK'tür, YÜKSEK değil.
  Çapraz kontrol: ön koşul listen 3+ maddeyse YÜKSEK neredeyse kesinlikle
  yanlıştır.

ADIM 3: Etki modeli eşleşmesi. ETKİ MODELİ boş değilse ve bu bulgu onun
bir maddesine oturuyorsa hangisi olduğunu yaz. Eşleşme şiddeti BİR
basamak yükseltebilir (DÜŞÜK→ORTA ya da ORTA→YÜKSEK), asla iki. Etki
modeli boşsa bu adımı atla.

ADIM 4: İddia edilen şiddeti yargıla. Bu hafta iki yüz gözlemci uyarısı
okumuş, şişirmeye alerjik bir mühendisin gözünden: İDDİA EDİLEN şiddet
alarm yorgunluğuna katkı yapar mı? Gerçekten karar kalitesini bozuyor mu?
Artefakt kum havuzu ya da öz-test koşusuna mı ait? -5..+5 arası puanla:
  +3..+5  iddia edilen şiddet haklı ya da OLDUĞUNDAN DÜŞÜK
   0..+2  aşağı yukarı doğru
  -1..-3  bir seviye şişirilmiş
  -4..-5  fena şişirilmiş (gürültü, İHLAL diye giydirilmiş)

ADIM 5: dogrulama_hukmu. Tam olarak biri:
  onarilabilir        kök neden kodda/veride, düzeltilebilir
  hafifletilmis       gerçek, ama devrede bir korkuluk (mühür, fail-closed
                      kapı) zararı türetilen şiddetin altına indiriyor —
                      KORKULUĞU ADIYLA YAZ
  elle_inceleme_gerek şiddet ancak kontrollü bir yeniden üretimle
                      belirlenebilir; bunu bir insanın elle üretmesini öner

ADIM 6: ŞİDDET STANDARDI türetilmiş HIGH/MED/LOW değilse, `siddet_etiketi`
alanını o standarda göre üret. Değilse türetilmiş şiddete eşitle.

────────────────────────────────────────────────────────────────────────
YALNIZCA şu blokla cevap ver:

  ON_KOSULLAR:
  - <satır başına bir tane>
  TEKRAR_KOSULU: <her_kosuda|belirli_veride|elle_mudahaleyle>
  SIDDET: <YÜKSEK|ORTA|DÜŞÜK>
  SIDDET_ETIKETI: <şiddet standardına göre>
  ETKI_ESLESMESI: <eşleşen etki modeli maddesi, ya da yok>
  SIDDET_HIZASI: <-5..+5>
  DOGRULAMA_HUKMU: <onarilabilir|hafifletilmis|elle_inceleme_gerek>
  SIRALAMA_GEREKCESI: <2-4 cümle>
```

### 4b. Birleştir

Onaylanan her bulguya `on_kosullar` (rapor edenin listesinin YERİNE),
`tekrar_kosulu`, `siddet` (yeniden hesaplanmış), `siddet_etiketi`,
`etki_eslesmesi`, `siddet_hizasi`, `dogrulama_hukmu` eklenir ve
SIRALAMA_GEREKCESI, Faz 3 gerekçesinden boş satırla ayrılarak
`gerekce`ye eklenir.

Faz 4'e ULAŞMAYAN bulgular (`yanlis_pozitif`, `kopya`, yerelleştirilemez):
`siddet: null`, `dogrulama_hukmu: null`, `siddet_hizasi: null`,
`on_kosullar: []`.

---

## Faz 5: Yönlendir

Doğrulanmış her gerçek arızayı çıkarılabilecek EN SPESİFİK bileşene ya da
sahibe etiketle. `onaylanan[]` içindeki her bulgu için ilk isabette dur:

1. **CODEOWNERS / OWNERS.** `--depo` içinde `CODEOWNERS`, `OWNERS`,
   `.github/CODEOWNERS`, `docs/CODEOWNERS` aranır. Bulunursa bulgunun
   `dosya` alanı desenlerle eşleştirilir (son eşleşme kazanır). İpucu:
   `"CODEOWNERS: <desen> → <sahip>"`.
2. **git log.** `--depo` bir git çalışma kopyasıysa:
   `git -C {DEPO} log --format='%an' -n 50 -- "{dosya}"` → en çok katkı
   veren. İpucu: `"en çok katkı veren: <ad> (<n>/<toplam> son commit);
   CODEOWNERS kaydı yok"`.
3. **Bileşen yedeği.** İpucu: `"bileşen: <dosyanın üst dizini>/;
   CODEOWNERS ya da git geçmişi yok"` (+ ilgili motor dosyası).

`sahip_ipucu` olarak eklenir. Kaynağını yaz ki güven seviyesi belli olsun;
çıplak bir isim, `"bileşen: piramit-sistem/scripts/; en çok katkı veren
Claude (14/20 son commit)"` kadar yararlı değildir. Gerçek arıza olmayan
bulgularda `sahip_ipucu: null`.

---

## Faz 6: Çıktı

### 6a. Sırala

Tüm bulgular şu sırayla dizilir:
1. `hukum`: `gercek_ariza`, sonra `kopya`, sonra `yanlis_pozitif`.
2. Gerçek arızalar içinde: `siddet` YÜKSEK > ORTA > DÜŞÜK, sonra `guven`
   azalan, sonra `siddet_hizasi` azalan.
3. Diğerleri içinde: özgün `id`.

### 6b. `SORUSTURMA.json` yaz

```json
{
  "sorusturma_tamam": true,
  "sorusturma_baglami": {"mod": "interaktif|auto", "kapsam": "...",
    "etki_modeli": ["..."], "siddet_standardi": "...",
    "gurultu_toleransi": "...", "oy_sayisi": 3, "depo": "...",
    "yp_kaynaklari": ["..."], "yp_kural_sayisi": 13},
  "ozet": {"girdi_sayisi": 0, "kopyalar": 0, "yanlis_pozitifler": 0,
    "gercek_arizalar": 0, "elle_inceleme_gerek": 0,
    "siddete_gore": {"YÜKSEK": 0, "ORTA": 0, "DÜŞÜK": 0},
    "bolunmus_oylar": []},
  "bulgular": [{
    "id": "a001", "kaynak": "state/son_rapor.json", "baslik": "...",
    "dosya": "...", "konum": "K5-SI", "kategori": "EKSIK_AKTARIM",
    "iddia_edilen_siddet": "İHLAL",
    "hukum": "gercek_ariza|yanlis_pozitif|kopya",
    "dogrulama_hukmu": "onarilabilir|hafifletilmis|elle_inceleme_gerek|null",
    "guven": 0.0, "siddet": "YÜKSEK|ORTA|DÜŞÜK|null",
    "siddet_etiketi": "...", "siddet_hizasi": 0,
    "on_kosullar": ["..."], "tekrar_kosulu": "...",
    "etki_eslesmesi": "...|null",
    "gerekce": "dosya:satır alıntılı gerekçe; sonra sıralama gerekçesi",
    "oy_dagilimi": {"gercek_ariza": 0, "yanlis_pozitif": 0, "dogrulanamadi": 0},
    "curutme_nedenleri": ["..."], "yp_kurali": null,
    "ilk_kanitlar": ["dosya:satır"], "kopyasi": null, "yuttuklari": ["..."],
    "sahip_ipucu": "...", "eksik_alanlar": ["..."]
  }]
}
```

Her girdi bulgusu çıktıda **tam olarak bir kez** görünür (kopyalar
`kopyasi` ile kanoniğe bağlanır). Hiçbir şey sessizce düşürülmez. Bu JSON
terminale BASILMAZ; yalnız dosyaya yazılır.

### 6c. `SORUSTURMA.md` yaz

İnceleyene dönük rapor. **Parça parça** kurulur; tek Write ile tüm dosya
basılmaz — takılan bir parça o tek bölümü kaybettirir, dosyayı değil.

**1. adım — başlık.** Başlık bloğu, özet satırı ve `## Şunlarla ilgilen`
başlığı yazılır.

**2. adım — bulgu başına.** Şiddet sırasındaki her gerçek arıza için bir
bölüm eklenir:

```
### [{siddet}] {baslik}  ({id})
`{dosya}:{konum}` | {kategori} | iddia edilen {iddia_edilen_siddet} (hiza {siddet_hizasi:+d}) | güven {guven}/10
**Sahip:** {sahip_ipucu}
**Hüküm:** {dogrulama_hukmu}, oylar {oy_dagilimi}
**Ön koşullar ({n}):** {madde madde}
**Tekrar koşulu:** {tekrar_kosulu}
**Etki modeli eşleşmesi:** {etki_eslesmesi ya da "yok"}
**Neden:** {gerekce}
**Kanıt izi:** {ilk_kanitlar}
{dogrulama_hukmu == elle_inceleme_gerek ise:}
> Statik muhakeme sınırına dayandı; bu bulguyu ELLE tekrar üret
> (kontrollü koşu) — otomatik hüküm verilmedi.
```

**3. adım — alt bilgi.** Düşenler tablosu eklenir:

```
## Düşenler

| id | başlık | dosya:konum | neden düştü |
{yanlis_pozitifler: curutme_nedenleri + YP kural numarası}
{kopyalar: "{kopyasi} kopyası"}
{yerelleştirilemezler: "girdide artefakt yolu yok"}
```

Sonunda `ilerleme.json` `durum: "tamam"` ile mühürlenir; bir sonraki
çağrının devam denetimi bunu görüp taze başlar.

### 6d. Terminal özeti

~12 satırın altında:

```
Soruşturma tamam: {N} kayıt → {G} gerçek arıza, {Y} yanlış pozitif, {K} kopya.

  YÜKSEK: {n}   {en üstteki bulgunun başlığı, sahip_ipucu}
  ORTA:   {n}
  DÜŞÜK:  {n}
  Elle inceleme gerek: {n}

  En sık çürütme nedeni: {ilk 3 neden, sayılarıyla}

Yazıldı: ./SORUSTURMA.md ve ./SORUSTURMA.json
```

---

## Motor

```bash
# tam koşu (mülakat cevapları baglam.json'da)
python3 .claude/skills/sorusturma/scripts/sorusturma.py \
    .claude/skills/piramit-sistem/state/son_rapor.json \
    --depo . --oy 3 --baglam ./.sorusturma-state/baglam.json

# mülakatsız hızlı geçiş
python3 .claude/skills/sorusturma/scripts/sorusturma.py <yol> --auto --oy 1 --depo .

# LLM doğrulayıcı oylarını birleştirerek
python3 .claude/skills/sorusturma/scripts/sorusturma.py <yol> --auto \
    --oy 5 --depo . --oy-dosyasi ./.sorusturma-state/oylar.json

# koşuya özgü YP kurallarıyla
python3 .claude/skills/sorusturma/scripts/sorusturma.py <yol> --auto \
    --depo . --yp-kurallari ./bu_koşu_kurallari.txt
```

---

## Bu beceriyi test etmek

Duman testi (altı bulgulu örnek: 2 gerçek, 1 kopya, 2 YP, 1
yerelleştirilemez):

```bash
python3 .claude/skills/sorusturma/scripts/sorusturma.py --self-test
```

Beklenen: a001 ve a003 onaylanır; a002, a001'in kopyasıdır; a004 düşer
(YP kural 1: kapı düşmesi fail-closed tasarımdır); a005 düşer (YP kural 2:
BEKLE bir işlem-kalitesi hükmüdür); a006 düşer (`kanit_yok`: girdide
artefakt yolu yok). Çıktılar `ornek/SORUSTURMA.{json,md}`.

Gerçek artefakta karşı:

```bash
python3 .claude/skills/sorusturma/scripts/sorusturma.py \
    .claude/skills/piramit-sistem/state/son_rapor.json --auto --oy 5 --depo .
```

GERCEK_ARIZA/YÜKSEK sonuçlarından bir örneklemi elle denetle
(`ilk_kanitlar` gerçek üretim noktalarını göstermeli) ve YANLIS_POZITIF
redlerinden bir örneklemi de (`yp_kurali` ya da `curutme_nedenleri`
savunulabilir olmalı).

---

## Tasarım notları

- **Kontrol noktaları faz başına JSON'dur**, konuşma durumu değil.
  Orkestratörün bağlam penceresi dolduğunda transkript geçmişi işe
  yaramaz; dosyaya yazılan kontrol noktaları bambaşka bir oturumun son
  tamamlanan fazdan devam etmesini sağlar. `./.sorusturma-state/` çöp
  dizinidir — `.gitignore`'a eklenmiştir.
- **Tekilleştirme doğrulamadan ÖNCE koşar**; doğrulayıcı harcamasını
  çoğaltma faktörü kadar keser. Bu depoda faktör yüksektir: aynı kök neden
  gözlemcinin `ihlal` listesinde, `gozlemciler` bloğunda ve
  `ZIRVE.DENETIM` özetinde üç kez görünür.
- **Anlamsal tekilleştirme tek ajandır** ve yalnız id/dosya/konum/kategori/
  başlık görür: kümelemeye yeter, bir bulgunun muhakemesini diğerinin
  doğrulamasına sızdırmaya yetmez.
- **Bash dar kapsamlıdır**: `git log` (sahip ipucu), `find`/`ls`/`wc`
  (alım) ve `sorusturma.py`. Korunan asıl güvenlik özelliği "boru hattı
  çalıştırılmaz, sicil değiştirilmez"dir.
- **`DOGRULANAMADI` vardır** ki doğrulayıcılar sahte bir ikiliğe
  zorlanmasın. Kapsam politikasında `elle_inceleme_gerek`e, kesinlik
  politikasında düşüşe eşlenir.
- **Etki modeli yükseltmesi tek basamakla sınırlıdır** ki beyan edilen bir
  etki, DÜŞÜK'ü YÜKSEK'e geri şişirip ön koşul kuralını boşa çıkarmasın.
- **`siddet_etiketi`, `siddet`ten ayrıdır.** Sıralama HER ZAMAN ön
  koşuldan türetilen YÜKSEK/ORTA/DÜŞÜK'ü kullanır; etiket, inceleyenin
  beklediği standart için sunum katmanıdır.
- **YP kuralı vetosu** kasıtlıdır: kaynak protokolde dışlama kuralları her
  doğrulayıcının önündedir, dolayısıyla oylamayla aşılamaz. Kural
  eşleşince tüm oylar çevrilir ama her merceğin kendi kanıtı gerekçede
  korunur (denetlenebilirlik).
- **Deponun KENDİ sözleşmesi bir doğrulayıcı merceğidir.** `tasarim`
  merceği `gozlemci.py`'nin `KRITIK` kümesini ve `piramit.py`'nin
  FAIL-CLOSED beyanını okur ve gerçek `dosya:satır` alıntılar — satır
  numarası sabit yazılmaz, her koşuda aranır.
- **Motorlar çalıştırılmaz, kasıtlı olarak.** Arızayı yeniden koşarak
  doğrulamak `engine/state/` sicilini ve `hafiza/` ağırlıklarını
  kirletirdi; soruşturma kendi kanıtını bozmuş olurdu. Bunun bedeli, bazı
  bulguların `elle_inceleme_gerek` ile bitmesidir — bu bir başarısızlık
  değil, dürüst bir sınır beyanıdır.
