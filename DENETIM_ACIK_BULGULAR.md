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

`karar_motoru.py:470-474` R totolojisi (T1 = giriş + 1.5×risk üretilip sonra
"R kapısı geçildi" denmesi) · `usd_hedef.py:161-180` belgelenmiş ama hiç
uygulanmayan 5. kapı · `self_test.py:68-73` üretim SI hafızasını silip
`finally` ile geri yazması (SIGKILL'de kaybolur) · `self_test.py:670`
oluşturulmayan `state_dir` · `analyze_data.py:693` sayısal zaman kolonunda
ms/ns birim körlüğü · `verify_data.py:394` dar `except` · `turev_akis.py:186`
likidasyonda yalnız oran, büyüklük denetlenmiyor · `setup_dogrulama.py:224`
hesaplanan `rr_k` eşiğe hiç bağlanmıyor · `kalibrasyon.py:131` çıkış taraması
giriş barından başlıyor · `gozlemci.py:325` kapsam denetimi sonuca değil
anahtar varlığına bakıyor · `esik_kalibre.py:120` sıfır/negatif kapanışta
`math.log` patlaması · `video_isle.py:110` sınırsız `max_frames`.

## KAPANDI — tamir + ölçümle doğrulandı

`paket_ac` yol kaçışı ve ana slot · `gozlemci` DAIRESEL mührü · `iddia_denetle`
bağıl tolerans + beyaz liste · `emir_plani` r_min tabanı · `karar_motoru`
atomik yazım · `piramit.py` tazelik fail-OPEN, çelişki turu fail-OPEN,
doğrulayıcı ezme, `_verifier_confirmed` köprüsü · `esik_kalibre`
`min_side_weight` ölçek sadeleşmesi · `piramit_auto` `--sembol`, çıkış kodu,
dar `except`, kümülatif zaman aşımı · `turev_girdi` sözlük-panel sembol
süzgeci · `verify_data` sessiz payda değişimi + tanınmayan kural anahtarı ·
`gozlemci` sahte MEMNUN_ETME mührü (hakem bulgusu).
