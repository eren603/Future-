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
| B | Task 7-9 (veri, token, ölçekleyici/konum) | 0/3 | başlamadı |
| C | Task 10-12 (attention, başlık, kalibrasyon) | 0/3 | başlamadı |
| D | Task 13-15 (decoding, boru hattı, çıktı) | 0/3 | başlamadı |

## Kayıtlar

Madde Grup-A (Task 1-6) | Deneme 1/3 | Ajan kod-denetci#1 | Kapı: — (6/6 PASS) | Kanıt: denetçi `python3 -m unittest test_llm_trading_v3 -v` komutunu KENDİ koşturdu → 53 test OK exit 0; güvenlik regex'lerini sentetik kötü kaynakla mutasyon testinden geçirdi (API_KEY/hmac/signature=//fapi/v1/order yakalandı); `geometri_sec` argmax'ını bağımsız doğruladı (seçilen (1.0,4.0), elog=0.7283 = 11 adayın maksimumu); fail-closed dalının `en_iyi is None` yolundan geçtiğini ölçtü; spec'teki `f*=0.0905` ve `|f*|<1e-16` iddialarını yeniden üretti | Karar: PASS — adım 3'e geçildi | Arşiv: —

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
