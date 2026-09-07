# DENETİM SİCİLİ — ASTRA v1.4 (append-only; satır silinmez)

Biçim: Madde <N> | Deneme <k>/3 | Ajan <instance-id> | Kapı: <...> | Kanıt: <denetçinin kendi ölçümü> | Karar: PASS|RESTART|ESKALE | Arşiv: <dal>

Madde 1 | Deneme 1/3 | Ajan kod-denetci#1 | Kapı: 6 kapı PASS (ATLAMA/GİZLİ_GÜNDEM/TİYATRO/SAHTE_KANIT geçti; TÜNEL N/A; ÇARPIŞMA N/A) | Kanıt: git archive 76e5c8d → 113 test OK; ağaç diff boş; denetim_sicili.md beyan edilmiş kapsam | Karar: PASS | Arşiv: -
Madde 3 | Deneme 1/3 | Ajan kod-denetci#2 | Kapı: (bekliyor — sonuç gelince yazılır) | Kanıt: - | Karar: - | Arşiv: -
Madde 2 | Deneme 1/3 | Ajan kod-denetci#3 | Kapı: 6 kapı PASS (TÜNEL gerçek karar: spec §2 C + BAG Z3 alternatifleri kayıtlı) | Kanıt: git archive 65d34d4 → 118 test OK; BASE host + HEAD test → beklenen kırmızı (FAIL_CLOSED≠LOCAL_CHECKS_PASSED) | Karar: PASS | Arşiv: -
Madde 3 | Deneme 1/3 | Ajan kod-denetci#2 | Kapı: 6 kapı PASS (TÜNEL: PARTIAL alternatifi planda kayıtlı) | Kanıt: geçici worktree ae80a2c → 115 test OK; taban 113 OK; HEAD test + taban kod → beklenen kırmızı (SCHEMA_FIELDS) | Karar: PASS | Arşiv: - (önceki "bekliyor" satırı SUPERSEDED)
