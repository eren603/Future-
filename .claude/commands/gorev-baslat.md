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
3. `verification-before-completion` — "tamamlandı/düzeldi" demeden ÖNCE taze doğrulama komutunu çalıştır ve çıktısını göster. Geçmezse 1'e dön; geçtiyse bu turu "GEÇTİ" say.
4. Bağımsız 2+ alt görev varsa (paralelleştirilebilir), döngü adımlarını `dispatching-parallel-agents` veya `subagent-driven-development` ile paralel ajanlara böl — sıralı çalıştırma yerine.

İki ardışık turda "GEÇTİ" alınmadan döngüden çıkma.

## FAZ 7 — İnceleme
`requesting-code-review` ile işini incelemeye sun. Geri bildirim gelirse `receiving-code-review` ile kanıtla değerlendir — körü körüne uygulama, teknik olarak doğrulanmadan kabul etme.

## FAZ 8 — Bitiş
`finishing-a-development-branch` ile entegrasyon kararını (merge/PR/vb.) ver.

## Kurallar
- Her fazın sonunda 1-2 cümlelik durum özeti ver (ne yapıldı, sıradaki faz ne).
- FAZ 4-6 döngüsünde kaç tur döndüğünü ve neden döndüğünü açıkça söyle — sessiz tekrar yok.
- Hiçbir fazı "gerekli değil" diye sessizce atlama; atlarsan gerekçesini yaz.
