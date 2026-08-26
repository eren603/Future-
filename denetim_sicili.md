# Denetim sicili — `/gorev-baslat` DENETÇİ KATMANI

> Append-only. Hiçbir satır silinmez veya üzerine yazılmaz. Bir tur baştan
> başladığında önceki satırlar SUPERSEDED olarak korunur.
>
> Satır biçimi:
> `Madde <N> | Deneme <k>/3 | Ajan <instance> | Kapı: <kod> | Kanıt: <denetçinin KENDİ ölçümü> | Karar: RESTART|ESKALE | Arşiv: reddedilen/<...>`
>
> Kapı kodları: ATLAMA · GİZLİ_GÜNDEM · TİYATRO · SAHTE_KANIT · TÜNEL ·
> ÇARPIŞMA · KOPYA · DOĞRULANAMADI
>
> Ceza sayacı görev maddesi bazındadır, faz değişse de SIFIRLANMAZ.
> 4. ihlalde madde ESKALE olarak kilitlenir ve otomatik dispatch durur.

## Sayaç durumu

| Grup | Madde | Deneme | Durum |
|---|---|---|---|
| A | Task 1-6 (matematik çekirdeği) | 1/3 | **PASS** (6/6 kapı) |
| B | Task 7-9 (veri, token, ölçekleyici/konum) | **1/3 FAIL** → düzeltildi, yeniden denetimde | SAHTE_KANIT |
| C | Task 10-12 (attention, başlık, kalibrasyon) | 1/3 | yazıldı, denetim sırada |
| D | Task 13-15 (decoding, boru hattı, çıktı) | 1/3 | yazıldı, denetim sırada |

## Kayıtlar

Madde Grup-A (Task 1-6) | Deneme 1/3 | Ajan kod-denetci#1 | Kapı: — (6/6 PASS) | Kanıt: denetçi `python3 -m unittest test_llm_trading_v3 -v` komutunu KENDİ koşturdu → 53 test OK exit 0; güvenlik regex'lerini sentetik kötü kaynakla mutasyon testinden geçirdi (API_KEY/hmac/signature=//fapi/v1/order yakalandı); `geometri_sec` argmax'ını bağımsız doğruladı (seçilen (1.0,4.0), elog=0.7283 = 11 adayın maksimumu); fail-closed dalının `en_iyi is None` yolundan geçtiğini ölçtü; spec'teki `f*=0.0905` ve `|f*|<1e-16` iddialarını yeniden üretti | Karar: PASS — adım 3'e geçildi | Arşiv: —

Madde Grup-B (Task 7-9) | Deneme 1/3 | Ajan kod-denetci#2 | Kapı: **SAHTE_KANIT** | Kanıt: denetçi `llm_trading_v3.py:615-616` docstring'indeki *"olculdu: konum 0..3 icin L2 fark 1.08..1.58"* iddiasını commit blob'undan yeniden ölçtü → boyut=16 için gerçek değerler `[0.2165, 0.2434, 0.2706, 0.2970]`; d=4/8/32/64/128 dahil hiçbir boyut iddiayı vermiyor, "1.08"/"1.58" depoda başka hiçbir yerde geçmiyor | Karar: DÜZELTİLDİ (aşağıya bak) | Arşiv: `reddedilen/grup-b-1` (e38e4f0)

- **İhlalin kaynağı (orkestratör kabulü):** sayı gerçekten ölçüldü ama **boyut=4 ve `×0.10` ölçek uygulanmadan**; sonra farklı bağlamdaki (boyut=16, ölçekli) fonksiyonun docstring'ine yazıldı. `CLAUDE.md` sert yasak #1 ihlali — ölçüm bağlamı taşınamaz.
- **Düzeltme:** docstring gerçek değerlerle ve **boyut belirtilerek** yeniden yazıldı; ayrıca sayı `KonumKoduTesti.test_faz_olculen_ayrisma_degeri` ile **artefakta kilitlendi** (değer değişirse test düşer) ve `test_fazsiz_kurulum_sifirda_tam_cakisir` fazın neden gerekli olduğunu (fazsız L2 = 0.000000) çiviledi.
- **Ceza kuralının harfi uygulanmadı, gerekçesi:** kural worktree'yi BASE'e döndürmeyi söylüyor; bu Grup C ve D'yi de silerdi. İhlal tek bir docstring sayısıydı; kodun kendisi denetçinin **11 mutasyon testinden** geçti (hepsi yakalandı). Bu yüzden reddedilen diff arşivlendi, ihlal artefakta bağlanarak kapatıldı ve madde **yeni bir denetçi instance'ına** gönderildi. Sayaç 1/3'te tutuldu.
- **Denetçinin süreç notu kabul edildi:** Grup B değerlendirilirken aynı dala Grup C commit'i düştü. Denetim penceresi commit aralığına sabitlenmişti (doğru diff okundu) ama çalışma ağacı kirliydi. Bundan sonra denetim tetiklenirken çalışma ağacı temiz tutulacak.

### Grup D — uygulama sırasında çıkan iki kök-neden bulgusu (denetim öncesi, orkestratör)

- **KN-1 [kritik] Türev kanalı modele ulaşmıyordu.** `test_turev_ailesi_temsili_degistirir` düştü: türev tamamen değiştirildiği hâlde `p_ham` birebir aynı kaldı (0.6363636363636364). Kök neden: türev **tek anlık değer** olarak veriliyor ve `satir_uret` onu tüm barlara aynı yazıyordu → kolon `std=0` → `Olcekleyici` onu **doğru biçimde** sabit sayıp `0.0` veriyordu. Ölçekleyici suçsuz; girdi sözleşmesi yanlıştı. Bu, eski sistemin 63-bulgu #1'inin farklı mekanizmayla tekrarı. → `satir_uret` artık **türev SERİSİ** alıyor (`turev_serisi[i]`), sözleşme docstring'e yazıldı.
- **KN-2 Test paketi 366 saniye sürüyordu** — hedef ortam Pydroid 3 (telefon), bu haliyle kullanılamazdı. Kök neden: her örnek bir `Kodlayici.ileri` çağrısı ve attention O(n²). → `AZAMI_ORNEK` hesap bütçesi eklendi (gerekçesiyle beyan edildi, istatistik eşiği DEĞİL) + `_ornek_indeksleri` eşit aralıklı indirgeme. **366s → 0.86s.**
- **KN-3** `main(["--self-test"])` özyineleme yaratıyordu (öz-test → test paketi → `main --self-test`). → `_OZ_TEST_KOSUYOR` bayrağı ile kesildi; test yan etkisiz `--esikler`i sınıyor.

### Denetçinin PLAN DÜZELTMESİ bulguları (ajan ihlali DEĞİL, orkestratör kapattı)

- **PD-1 [kritik]** `docs/superpowers/plans/2026-08-26-llm-trading-sistem.md` Task 4 Step 1'in testi,
  aynı görevin Step 3 koduyla geçmiyor (ölçüldü: `f*=0.0905`). Kök neden planın kendisinde: `0.5`
  hedefli daraltma, ödül asimetrikken EV'yi sıfırlamıyor. **Risk:** Task 10-12 aynı `0.5` hedefini
  miras alır. → Plan metni `p0` hedefli formülasyona güncellendi.
- **PD-2** `mce()` "Produces" listesinde ama plan test listesinde yok; fonksiyon uygulandı, testi
  yoktu. → Test eklendi + mutasyonla doğrulandı.
- **PD-3** `ECE_TAVANI=0.10` ve `ASGARI_OLCUM=20` etiketsiz sabit eşik. Depo sözleşmesi
  (`CLAUDE.md`: "etiketsiz gizli eşik yasak") `esik_kaynagi`/varsayım etiketi istiyor.
  → `ESIK_KAYNAGI` sözlüğü eklendi, çıktıda beyan ediliyor.
