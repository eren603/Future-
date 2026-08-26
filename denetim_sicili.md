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
| A | Task 1-6 (matematik çekirdeği) | 1/3 | denetimde |
| B | Task 7-9 (veri, token, ölçekleyici/konum) | 0/3 | başlamadı |
| C | Task 10-12 (attention, başlık, kalibrasyon) | 0/3 | başlamadı |
| D | Task 13-15 (decoding, boru hattı, çıktı) | 0/3 | başlamadı |

## Kayıtlar

<!-- denetçi hükümleri buraya append edilir -->
