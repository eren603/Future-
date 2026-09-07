# ARAŞTIRMA NOTLARI — ASTRA v1.3 tamiri için dış kaynak durumu (2026-09-07)

Etiketler: [DOKÜMAN] doğrudan açılan kaynak · [İKİNCİL] arama özeti / üçüncü taraf ·
[VERİ YOK] açılamadı, doğrulanamadı.

## 1. Erişim durumu (gerçek — bu ortamdan)

| Kaynak | Sonuç |
|---|---|
| developers.openai.com (model sayfası, reasoning, structured-outputs, latest-model, evaluation-best-practices) | EGRESS_BLOCKED — açılamadı → belgenin bu URL'lere dayandırdığı 3 "SUPPORTED" hükmü bu oturumda **yeniden doğrulanamadı** |
| platform.openai.com, openai.com, community.openai.com, learn.microsoft.com, deploymentsafety.openai.com | EGRESS_BLOCKED |
| raw.githubusercontent.com (openai-cookbook, openai-python, openai-agents-python) | AÇILDI |
| WebSearch (arama özetleri) | Çalışıyor; özet ikincil kanıttır |

## 2. gpt-6-astra hakkında toplanan bilgi

- [İKİNCİL] `reasoning.effort` desteklenen değerler: low, medium, high, xhigh, max.
  `none` → HTTP 400; `minimal` yok. Kaynak: arama özeti (developers.openai.com model sayfası
  + reasoning rehberi + litellm/felo/apidog özetleri). Paketteki `ReviewerEndpoint`'in
  {"low","medium","high","xhigh","max"} kümesi bununla UYUMLU.
- [İKİNCİL] Responses API'de alan adı iç içe `reasoning.effort` (Chat Completions'ta düz
  `reasoning_effort`). Paket Responses API kullanıyor — UYUMLU.
- [VERİ YOK] Sıcaklık/top_p desteği, bağlam penceresi, max_output_tokens tavanı, snapshot
  kimlikleri, fiyat: birincil sayfa açılamadı. Paket `max_output_tokens=16384` gönderiyor —
  bu değerin modelin tavanı içinde olduğu DOĞRULANMADI.
- [İKİNCİL] Sistem kartı (deploymentsafety.openai.com/gpt-6-astra) var ama açılamadı.

## 3. Structured Outputs (strict) anahtar kelime desteği

- [DOKÜMAN] openai-python `to_strict_json_schema` ve openai-agents-python `strict_schema.py`
  (raw GitHub): `additionalProperties:false` zorunlu, tüm `properties` `required`;
  `minLength/maxLength/pattern/format/minItems/maxItems/enum` bu istemci kodunda
  ne siliniyor ne reddediliyor (geçiriliyor) — sunucu tarafı kabulünü KANITLAMAZ.
- [İKİNCİL] Arama özetleri çelişkili: bir kaynak "minLength/maxLength artık destekleniyor"
  (community.openai.com "nifty improvements" başlığı), diğeri "API yoluna/modele göre strict
  bazı kısıtları reddedebilir; minLength/maxLength/pattern/format tuzaktır — doğrulamayı
  uygulama tarafında yap" diyor.
- SONUÇ: Paketin `ASSESSMENT_SCHEMA`'sı `minLength`, `maxLength`, `minItems`, `maxItems`,
  `enum` kullanıyor ve `strict:true` ile gönderiliyor. Bu şemanın **gpt-6-astra strict
  modunda kabul edildiği hiçbir artefaktla gösterilmemiş** (canlı çağrı yok; HTTP fixture
  opener şemayı hiç denetlemiyor). Bu bir [VERİ YOK] + tasarım riskidir: canlı ilk çağrı
  400 ile kapanabilir. Onarım: (a) sunucuya gönderilen şemadan sunucu-bağımlı kısıtları
  ayırıp (transport şeması) doğrulamayı host tarafında tutmak, (b) bunu README'de açıkça
  "canlı doğrulanmadı" diye etiketlemek.

## 4. Prompt tasarımı — resmî/yarı-resmî rehberlerden alınan ilkeler

[DOKÜMAN] GPT-5 prompting guide (openai-cookbook, raw):
- "Poorly-constructed prompts containing contradictory or vague instructions can be more
  damaging to GPT-5 than to other models" — model "expends reasoning tokens searching for a
  way to reconcile the contradictions rather than picking one instruction at random".
- Israr için: "keep going until the user's query is completely resolved, before ending your
  turn"; "Never stop or hand back to the user when you encounter uncertainty — research or
  deduce the most reasonable approach."
- "For complex, multi-step tasks, we recommend higher reasoning."
- Öz-değerlendirme rubriği: "create a rubric that has 5-7 categories" ve buna göre
  kendi çıktısını sına.
- Metaprompting: modele "what elements could be added to an unsuccessful prompt" sorulabilir.

[DOKÜMAN] GPT-5.2 prompting guide (openai-cookbook, raw):
- "Implement EXACTLY and ONLY what the user requests."
- "Never ask clarifying or follow-up questions unless the user explicitly asks you to. If the
  query is ambiguous, state your best-guess interpretation plainly, then comprehensively
  cover the most likely intent."
- "Never fabricate exact figures, line numbers, or external references when you are
  uncertain"; "Never invent citations".
- Yüksek-risk öz-denetim: "re-scan your own answer for: unstated assumptions, specific
  numbers or claims not grounded in context, overly strong language."
- Uzun bağlam: "Re-state the user's constraints explicitly before answering"; "Anchor claims
  to sections".
- "make one change at a time" / "adjust only after running evals".

[İKİNCİL] GPT-6 Astra model guidance (developers.openai.com/latest-model; arama özeti +
the-decoder.com özeti):
- Çelişkili/bulanık talimat (AGENTS.md / skill dosyaları) modeli DURDURABİLİR ya da
  beklenmedik yöne çevirebilir; OpenAI "authority explicit, obsolete/contradictory guidance
  removed" diyor.
- Model "additional input could materially change the result" durumunda soru sormaya
  DAHA yatkındır → kullanıcı ısrar bekliyorsa bu bir kaçış kapısıdır; açık "varsayım yaz,
  devam et" talimatı gerekir.
- Hata ayıklama istemi: modelden "hangi dosya/hangi talimat seni durdurdu" diye tam alıntı
  istenmesi öneriliyor.
- "Slop word" kara listesi yayımlanmış; makale açılamadı, içerik arama özetinden alındı → §6.

## 5. Bu tamirde kullanılacak yorum (VARSAYIM etiketli)

- Kaçış yolu = modelin işi yapmadan meşru görünen bir durumla (BLOCKED, ANALYSIS_ONLY,
  "tek soru sorarım", "kapsam dışı", "VERİ YOK") çıkabildiği her yer. Bunlar KALDIRILMAZ
  (dürüstlük sözleşmesi bunları gerektirir) ama her biri KANIT + MALİYET + ALTERNATİF
  zorunluluğuna bağlanır: BLOCKED demek için denenen yollar listelenir; VERİ YOK demek
  için arandığı yerler listelenir; soru sormak için önce bağımsız iş bitirilir ve varsayım
  altında taslak üretilir.
- Zorlama = daha fazla kelime değil, daha az çelişki + doğrulanabilir zorunlu artefakt.
  Rehberlerin ortak noktası: çelişki temizliği, açık otorite sırası, ısrar talimatı,
  öz-denetim rubriği, uydurma yasağı, tek seferde bir değişiklik.

## 6. Ek ikincil bulgular (arama özetleri — [İKİNCİL], canlı doğrulanmadı)

- gpt-6-astra bağlam penceresi 1.050.000 token; en çok çıktı 128.000 token (OpenRouter/llm-stats/CometAPI
  özetleri). Paketin `max_output_tokens=16384` değeri bu tavanın altında → 16384 tek başına
  hata üretmez; ancak uzun inceleme (320 iddia × alıntı) 16384'te kesilebilir → `status:
  incomplete` → kapı kapanır (fail-closed). Bu tasarım tercihi metinde açıkça yazılmalı.
- Fiyat: $10/M giriş, $50/M çıktı; 272K giriş üstünde uzun-bağlam tarifesi (2×). Reasoning
  token'ları çıktı olarak faturalanır. → effort=max + büyük inceleme isteği maliyet üretir;
  komut bunu "maliyet doğurur" diye söylüyor, sayı vermiyor (doğru — sayı VERİ YOK).
- OpenAI'nin GPT-6 Astra için yayımladığı "slop word" kara listesi (the-decoder/newmobilelife
  özetleri): "Conclusion:", "Bottom line", "delve", "leverage", "foster", "it's worth noting",
  "importantly", "what's important is", "game-changer", "seamlessly", "testament to",
  "really/truly", "In short:", "The simplest mental model is:", "X, not Y" karşıtlık
  kalıbı, uydurma tireli bileşik sıfatlar; "ne yapmadığını değil ne yaptığını söyle".
  Bu liste Türkçe komuta uyarlanacak (Türkçe karşılıkları VARSAYIM etiketli).
