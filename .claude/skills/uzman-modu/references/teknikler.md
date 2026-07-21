# Üst-akıl teknikleri — KAYNAKLI (hafızadan değil)

Bu dosya `uzman-modu` protokolünün dayanağıdır. Her teknik bir **doğrulanabilir
kaynağa** bağlıdır. İkinci-göz denetiminden geçmiştir (8 GEÇTİ / 1 uydurma
karantina). Kaynaksız iddia buraya girmez.

## Doğrulanmış teknikler

| Teknik | Ne yapar | Kaynak (doğrulandı) |
|--------|----------|---------------------|
| **Rol prompting** | Uzman kimliği vermek çıktıyı alana özgü keskinleştirir | Anthropic — prompt engineering best practices + platform docs ("en etkili yollardan biri") |
| **Chain-of-Thought** | Adım adım muhakeme | Wei et al. 2022, arXiv:2201.11903 |
| **Self-Consistency** | Çok muhakeme yolu → en tutarlıyı seç | Wang et al. 2022, arXiv:2203.11171 |
| **Tree-of-Thought** | Dallan, değerlendir, en iyi yolu seç | Yao et al. 2023, arXiv:2305.10601 |
| **ReAct** | Muhakeme + eylem (araç/veri) iç içe; halüsinasyonu azaltır | Yao et al. 2022, arXiv:2210.03629 |
| **Reflexion** | Öz-eleştiri / sözel pekiştirme ile düzeltme | Shinn et al. 2023 |
| **Fable 5 pratiği** | Tam görevi tek turda + niyetiyle ver; aşırı-reçete etme | Anthropic model-migration rehberi (claude-api skill, oturum içi birincil kaynak) |
| **Efor** | Ana zekâ ayarı; zor işte `xhigh` | Anthropic effort / adaptive-thinking dokümanı |

## Karşılık — bu teknikler depoda nerede kurulu
- Self-Consistency + ToT → `karar-kurulu` (5 mercek, güven-ağırlıklı sentez)
- ReAct → motorları çalıştırma (`backtest-motoru`, `data-analysis-deep-scan`, MCP verisi)
- Reflexion → `uzman-modu/scripts/iddia_denetim.py` (ikinci göz)
- Rol + niyet + tam-spec → aşağıdaki trade prompt şablonu

## Kayıt için düzeltme (dürüstlük)
Önceki bir cevapta "varsayılan ~%40, doğru kullanım ~%95 kapasite" gibi **sayısal
bir iddia** kullanılmıştı; bu **uydurmaydı** (kaynak yok) ve ikinci-göz
denetiminde KARANTİNA'ya alındı. Doğru çerçeve: bu teknikler model ağırlıklarını
değiştirmez, kapasitenin ne kadarının **fiilen kullanıldığını** değiştirir —
ama "ne kadar" için ölçülmüş sayı yoktur; öyle bir rakam verilmez.

## Sınır
Bu teknikler cevabı daha derin ve daha az hatalı yapar; modeli her şeyi bilen
yapmaz. "Bilmiyorum" ve "VERİ YOK" geçerli, doğru cevaplardır.
