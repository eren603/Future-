# Açık bulgu defteri — kod/güvenlik denetimi

Kaynak: 2026-07-28 denetimi (11 bağımsız ajan + H-0 kanıt hakemi).
Toplam 66 ham bulgu; alıntı doğrulaması 66/66 geçti (TİYATRO yok).

**Bu defterin varlık sebebi:** açık bulgular commit mesajlarına gömülü kalırsa
bir sonraki oturumda bulunamaz — "AÇIK raporlandı" demek yeterli değildir.
Bir bulgu ya buradan silinir (tamir + doğrulama) ya da burada durur.

---

## AÇIK — tamir edilmedi

| # | Yer | Sınıf | Kusur | Neden açık |
|---|---|---|---|---|
| A1 | `akibet_etiketle.py:187-192` | B1 | LIMIT dolum barında hedef, pozisyon açılmadan önceki menzilden sayılabiliyor | Yama uygulandı, **T26'yı kırdı** (34/35 → 33/35). Protokol gereği geri alındı. Ölçüm ve tamir birlikte tasarlanmalı. |
| A2 | `gozlemci.py:305-308` | B1 | MEMNUN_ETME de KRITIK kümesinde ama yalnız UYARI üretiliyor → hiç mühürleyemiyor (DAIRESEL ile aynı ölü-kapı kusuru) | Ölçütü "tüm danışmanlar onaylı, hiç çürütme yok" — sağlıklı koşuda da doğru olabilir. İHLAL'e çekmek **her koşuyu mühürleyebilir**. Yarıçapı gerçek veriyle ölçülmeden yamamak tahminle yamadır. |
| A3 | `data_core.load_table` | S1 | Tek sütunlu CSV'de ayraç yanlış sezilebiliyor: `miktar` başlığı `mik`+`ar` diye bölündü (ayraç `t` seçilmiş) | Denetim sırasında rastlantıyla bulundu; K-F kapsamında, ayrı ele alınmalı. |
| A4 | `paket_ac._hedefler` ikinci korkuluk | — | `is_relative_to` kolu **ulaşılamaz**: doğrulama aynı satırda çağrıldığı için oraya ancak `a-z0-9` geçebilir | Zararsız ama ölü kod. Hakem TİYATRO (zararsız) dedi. Ya kaldırılmalı ya gerçekten bağımsız bir yola konmalı. |
| A5 | `paket_ac._kline_gecerli` | S1 | NaN'lı kline hâlâ geçiyor: `parse_constant` yalnız `main()` seviyesinde; kütüphane olarak çağrıldığında koruma yok | `main()` yolu fail-closed, ama API yolu değil. |
| A6 | `piramit_auto.py` | S1 | Kancanın kendi JSON okumalarında `parse_constant` yok — NaN'lı paket kancanın geri-sarma kapısını sessizce geçebilir | `paket_ac` çıkış kodu okunduğu için net sonuç fail-closed, ama kapı iddia edildiği yerde değil. |
| A7 | `turev_girdi.ham_oku` | S1 | `takerlongshortRatio` ve `likidasyon` panellerinde `symbol` alanı YOK (ölçüldü, her iki sembolde de) → sembol kanıtlanamıyor | Sembol zorunlu kılınırsa **zorunlu girdi #2 kırılır**. Şimdilik kabul ediliyor ama `hatalar`a "KANITLANMADI" notu düşüyor. Kalıcı çözüm: `veri_topla` panelleri yazarken sembolü damgalamalı. |
| A8 | `piramit.py` çelişki turu yeni kolları | — | "doğrulanmış danışman yok" ve "tur koşamadı" kolları **öz-testle kapsanmıyor** (T34 yalnız `kostu=True` kolunu sınıyor) | Test eklenmeli. |
| A9 | `piramit-sistem/self_test.py` T32 | — | `T32` kalıyor (34/35) | Bu denetimden **önce de** kalıyordu (`git stash` ve `c26a3a1` tabanıyla iki kez doğrulandı). Denetim kapsamı dışı, ayrı ele alınmalı. |

## KUYRUKTA — doğrulanmış, sırası gelmedi

`usd_hedef.py:161-180` belgelenmiş ama hiç uygulanmayan 5. kapı (stop karşı
yapının ötesinde mi) · `analyze_data.py:693` sayısal zaman kolonunda ms/ns
birim körlüğü (Binance kline ms, pandas ns sayar) · `turev_akis.py:186`
likidasyonda yalnız ORAN bakılıyor, büyüklük denetlenmiyor ·
`setup_dogrulama.py:224` hesaplanan `rr_k` yalnız rapora yazılıyor, confluence
eşiğine hiç bağlanmıyor · `kalibrasyon.py:131` çıkış taraması giriş barının
kendisinden başlıyor (ileriye bakış riski).

## AÇIK — kapanış hakem turunda bulundu (2026-07-28)

| # | Yer | Kusur | Not |
|---|---|---|---|
| Y2 | `paket_ac.py:122` | Yorum kodla çelişiyordu ("beyan yoksa ilk eleman sürer") | **KAPATILDI** — yorum kodla eşitlendi |
| Y3 | `self_test.py` hafıza taşıma | Kaza sonrası `agirlik.json.oztest_yedek` diskte kalıyor ama **hiçbir kod fark etmiyor**; sistem öğrenilmiş SI ağırlığı olmadan sessizce koşmaya devam eder, `saglik.py` uyarmıyor | AÇIK — `saglik.py`'ye "yetim yedek" denetimi eklenmeli |
| A7b | `turev_girdi` "KANITLANMADI" notu | Not `_ham_hatalari`'na yazılıyor ama **hiçbir kod okumuyor** — kayıt var, kapı yok | AÇIK — kalıcı çözüm: `veri_topla` panelleri yazarken sembolü damgalasın |

## KAPANDI — tamir + ölçümle doğrulandı

**Girdi hattı:** `paket_ac` yol kaçışı · ana slot (paketteki sıra artık ana
yuvayı seçemez, belirsizse fail-closed red) · `None`/tip hatası sembol reddi ·
NaN/Infinity yasağı (`main()` yolu) · `piramit_auto` `--sembol` geçilmesi,
türev üretecinin çıkış kodu, dar `except`, kümülatif zaman aşımı bütçesi ·
`turev_girdi` sözlük-panel sembol süzgeci.

**Karar hattı:** `piramit.py` tazelik fail-OPEN · çelişki turu fail-OPEN (iki
kol) · doğrulayıcı ezme (VE'leme) · `_verifier_confirmed` köprüsü ·
`esik_kalibre` `min_side_weight` ölçek sadeleşmesi + `math.log(0)` çökmesi ·
`karar_motoru` R totolojisi + atomik durum yazımı · `emir_plani` r_min tabanı.

**Denetim hattı:** `gozlemci` DAIRESEL mührü · sahte MEMNUN_ETME mührü (hakem
bulgusu) · kapsam denetimi (`verdict` varlığına bağlandı — "denetim
ÇALIŞMADI" kaydı da artık yakalanıyor) · `iddia_denetle` bağıl tolerans +
beyaz liste · `verify_data` sessiz payda değişimi, tanınmayan kural anahtarı,
dar `except`.

**Diğer:** `self_test` üretim hafızasını silmesi (artık taşınıyor) ·
oluşturulmayan `state_dir` · `video_isle` sınırsız `max_frames`.
