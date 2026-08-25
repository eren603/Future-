# KANIT — kaynak → uygulama izlenebilirliği

Kaynak depo: `a-claude-code-monitoring-guide`
(`README.md`, `claude_code_roi_full.md`, `otel-collector-config.yaml`,
`prometheus.yml`, `grafana/dashboards/working-dashboard.json`,
`report-generation-prompt.md`, `sample-report-output.md`, `docker-compose.yml`)
— hepsi Read ile TAM okundu; alıntılar kopyala-yapıştırdır, parafraz değildir.

Bizim dosyalar: `.claude/skills/izleme-telemetri/` altındadır
(`SKILL.md`, `scripts/olcum.py`, `scripts/rapor.py`, `sunucu/*`, `ornek/*`).

---

## 1. BİREBİR ALINTI EŞLEME TABLOSU

| # | Kaynak dosya:satır | Kaynaktan BİREBİR alıntı | Bizim dosya:satır | Uygulama |
|---|---|---|---|---|
| 1 | claude_code_roi_full.md:33-38 | `descriptor: {`<br>`    name: 'claude_code.cost.usage',`<br>`    type: 'COUNTER',`<br>`    description: 'Cost of the Claude Code session',`<br>`    unit: 'USD',` | scripts/olcum.py:177-178 | Her JSONL satırı aynı `descriptor` dörtlüsünü taşır: `"descriptor": {"name": ad, "type": tip, "description": aciklama, "unit": birim}` — dış yığın kurulursa OTLP eşlemesi birebir olur. |
| 2 | claude_code_roi_full.md:41-49 | `dataPoints: [`<br>`    {`<br>`      attributes: {`<br>`        'user.id': …, 'session.id': …, 'model': …`<br>`      },`<br>`      value: 0.000297` | scripts/olcum.py:175-186 | Veri noktası `attributes` + `value` ile yazılır; niteliklerimiz `kosu_id` (session.id karşılığı), `sembol`, `katman`, `motor`, `danisman`, `kod`. |
| 3 | claude_code_roi_full.md:20-22 | `export CLAUDE_CODE_ENABLE_TELEMETRY=1`<br>`export OTEL_METRICS_EXPORTER=console`<br>`export OTEL_METRIC_EXPORT_INTERVAL=1000` | scripts/olcum.py:127-136 (`dosya_yolu`) | Ortam değişkeniyle yapılandırma deseni korundu: `IZLEME_OLCUM_DOSYA` ölçüm hedefini belirler. OTel değişkenleri UYGULANAMAZ (OTel yok — SAPMALAR §1). |
| 4 | claude_code_roi_full.md:201-205 | `\| Metric \| What It Measures \| Reliability & Interpretation \|` … `\| `claude_code.pull_request.count` \| PRs created during Claude sessions \| **High reliability** …` | KANIT.md §2 (metrik eşleme) | Üretkenlik metrikleri tek tek ele alındı; karşılığı olmayanlar `uygulanamaz` gerekçesiyle işaretlendi. |
| 5 | claude_code_roi_full.md:213 | `\| `claude_code.session.count` \| Number of CLI sessions started \| Track overall tool adoption and usage frequency \|` | scripts/olcum.py:76-77 | `piramit.kosu.sayisi` — "başlatılan piramit koşusu sayısı" (COUNTER). |
| 6 | claude_code_roi_full.md:214 | `\| `claude_code.code_edit_tool.decision` \| Code editing tool permission decisions \| Monitor how often developers accept/reject suggested changes \|` | scripts/olcum.py:82-85 | `piramit.danisman.dogrulandi` / `piramit.danisman.dogrulanmadi` — kabul/ret ikilisinin karşılığı: K4 `verifier[danisman].confirmed`. |
| 7 | claude_code_roi_full.md:216 | `\| `claude_code.token.usage` \| Token consumption by type (input/output/cache) \| Understand usage patterns and optimize costs \|` | scripts/olcum.py:71-74 | Tür bazlı kaynak tüketimi = `piramit.katman.sure_ms{katman}` + `piramit.motor.sure_ms{motor}`. |
| 8 | claude_code_roi_full.md:180-182 | `### Session Duration Analysis`<br>`Understanding how long developers stay in Claude Code sessions helps identify engagement patterns:` | scripts/olcum.py:69-70 + rapor.py:517-538 | `piramit.kosu.sure_ms` ve raporun "Koşu Süresi Dağılımı" bölümü (kova tablosu + p50/p95). |
| 9 | claude_code_roi_full.md:189-192 | `    B --> C{< 5 minutes}`<br>`    B --> D{5-30 minutes}`<br>`    B --> E{\> 30 minutes}` | scripts/rapor.py:521-522 | Süre kovaları aynı fikirle ama BU boru hattının ölçeğinde: `< 0.5 sn / 0.5–1 / 1–2.5 / 2.5–5 / 5–10 / 10+ sn` (koşular saniyeler sürer, dakikalar değil). |
| 10 | claude_code_roi_full.md:301-305 | `  longUnproductiveSessions = filter(`<br>`    duration > 30min AND claude_code.commit.count == 0,`<br>`    group by (developerId, sessionId)` | scripts/rapor.py:202-262 (`_icgoruler`) | "Uzun ama çıktısız koşu" deseninin karşılığı: `piramit.kosu.sure_ms` + `piramit.emir.uretildi=0` + kapı durdurma birlikte raporlanır. |
| 11 | claude_code_roi_full.md:306-309 | `  toolRejectionHotspots = filter(`<br>`    claude_code.code_edit_tool.decision{decision="reject"} > 10,`<br>`    group by (developerId, tool)` | scripts/rapor.py:223-232 | "Zayıf doğrulanan danışman" içgörüsü: doğrulama oranı `dogrulama_orani` eşiğinin altındaki her danışman listelenir. |
| 12 | claude_code_roi_full.md:311-314 | `  apiErrorPatterns = group by (error, model) {`<br>`    count(claude_code.api_error)`<br>`  }` | scripts/olcum.py:95-96, 254-257 | `piramit.motor.hata{motor,sebep}` — hem K2 `hatalar[]` kaydından hem `zamanlayici` içindeki istisnadan üretilir. |
| 13 | claude_code_roi_full.md:263-264 | `acceptanceRates = sum(claude_code.code_edit_tool.decision{decision="accept"}) by (developerId) / `<br>`                 count(claude_code.code_edit_tool.decision) by (developerId)` | scripts/rapor.py:317, 355-357 | Aynı oran formülü: `dogrulandi / (dogrulandi + dogrulanmadi)`, hem toplam hem danışman bazında. |
| 14 | claude_code_roi_full.md:97 | `sum(claude_code_cost_usage_USD_total)` | sunucu/grafana-dashboard.json:84 | `sum(increase(piramit_kosu_sayisi_total[$__range]))` — aynı toplam-sayaç deseni, para birimi yerine koşu adedi. |
| 15 | claude_code_roi_full.md:101 | `sum(claude_code_token_usage_tokens_total) by (type)` | sunucu/grafana-dashboard.json:353 | `sum by (katman)(increase(piramit_katman_sure_ms_sum[$__range]))` — "tür bazında toplam" deseni katman bazına çevrildi. |
| 16 | claude_code_roi_full.md:112 | `sum(claude_code_cost_usage_USD_total) by (model)` | sunucu/grafana-dashboard.json:422 | `sum by (katman)(increase(piramit_kapi_durdu_total[$__range]))` — "boyuta göre kırılım" deseni. |
| 17 | working-dashboard.json:82 | `"expr": "sum(increase(claude_code_cost_usage_USD_total[$__range]))"` | sunucu/grafana-dashboard.json:84 | Panel 1 "Total Cost" → "Toplam Koşu"; `$__range` + `increase()` deseni korundu. |
| 18 | working-dashboard.json:149 | `"expr": "count(count by (user_id)(increase(claude_code_cost_usage_USD_total[$__range]) > 0))"` | sunucu/grafana-dashboard.json:152 | Panel 2 "Active Users" → "Aktif Sembol": `count(count by (sembol)(… > 0))`. |
| 19 | working-dashboard.json:212 | `"expr": "sum(increase(claude_code_token_usage_tokens_total[$__range]))"` | sunucu/grafana-dashboard.json:216 | Panel 3 "Total Tokens" → "Toplam Katman Süresi" (`unit: "ms"`). |
| 20 | working-dashboard.json:275 | `"expr": "sum(increase(claude_code_lines_of_code_count_total[$__range]))"` | sunucu/grafana-dashboard.json:284 | Panel 4 "Lines of Code" → "Gözlemci İhlali" (kırmızı eşik 80 → 1: bir ihlal bile kırmızıdır). |
| 21 | working-dashboard.json:343 | `"expr": "sum by (model)(increase(claude_code_cost_usage_USD_total[$__range]))"` | sunucu/grafana-dashboard.json:353 | Panel 5 "Cost by Model" (piechart/pie) → "Katman Süre Payı (K1…K5)". |
| 22 | working-dashboard.json:411 | `"expr": "sum by (type)(increase(claude_code_token_usage_tokens_total[$__range]))"` | sunucu/grafana-dashboard.json:422 | Panel 6 "Token Usage by Type" (donut) → "Kapı Durdurmaları". |
| 23 | working-dashboard.json:501 | `"expr": "sum by (user_id)(increase(claude_code_cost_usage_USD_total[$__range]))"` | sunucu/grafana-dashboard.json:513 | Panel 7 "Cost by User" (table + organize transformation) → "Motor Süresi". |
| 24 | working-dashboard.json:597 | `"expr": "sum by (type)(increase(claude_code_lines_of_code_count_total[$__range]))"` | sunucu/grafana-dashboard.json:610 | Panel 8 "Lines of Code by Type" (table) → "Doğrulanmayan Danışmanlar". |
| 25 | working-dashboard.json:627-629 | `  "refresh": "30s",`<br>`  "schemaVersion": 37,`<br>`  "style": "dark",` | sunucu/grafana-dashboard.json:640-642 | Pano iskeleti (refresh/schemaVersion/style/time/timepicker) birebir korundu; `uid` ve `title` bizimkine çevrildi. |
| 26 | otel-collector-config.yaml:17-22 | `exporters:`<br>`  prometheus:`<br>`    endpoint: "0.0.0.0:8889"`<br>`    send_timestamps: true`<br>`    metric_expiration: 180m`<br>`    enable_open_metrics: true` | sunucu/otel-collector-config.yaml:32-39 | Aynen alındı; `metric_expiration: 180m` gerekçelendirildi (piramit koşuları seyrektir, seri düşmemeli). |
| 27 | otel-collector-config.yaml:29-34 | `service:`<br>`  pipelines:`<br>`    metrics:`<br>`      receivers: [otlp]`<br>`      processors: [memory_limiter, batch]`<br>`      exporters: [prometheus, debug]` | sunucu/otel-collector-config.yaml:46-51 | Boru hattı birebir korundu (jenerik OTLP; Claude Code'a özgü alan içermiyordu). |
| 28 | prometheus.yml:1-3 | `global:`<br>`  scrape_interval: 15s`<br>`  evaluation_interval: 15s` | sunucu/prometheus.yml:7-9 | Birebir korundu. |
| 29 | prometheus.yml:20-23 | `  # Add additional scraping targets here if needed`<br>`  # - job_name: 'your-app'`<br>`  #   static_configs:`<br>`  #     - targets: ['your-app:8080']` | sunucu/prometheus.yml:26-30 | Yorum somutlaştırıldı: `piramit-olcum` job'ı (JSONL→OTLP köprüsü YAZILMADI, açıkça yazıldı). |
| 30 | sample-report-output.md:1-2 | `# Claude Code Productivity Report`<br>`## June 1, 2025 - June 7, 2025` | scripts/rapor.py:300-301 | `# Piramit Boru Hattı İzleme Raporu` + `## <ilk_ts> - <son_ts>` (tarih aralığı JSONL'den okunur). |
| 31 | sample-report-output.md:4-5 | `> **Note**: This is a sample report generated by Claude Code using the Linear MCP integration and telemetry metrics. ` | scripts/rapor.py:303-307 | Aynı konumda `> **Not**:` bloğu — kaynak dosya + veri noktası sayısı + "OTel/Prometheus/Grafana KURULU DEĞİL" uyarısı. |
| 32 | sample-report-output.md:7 | `## Executive Summary` | scripts/rapor.py:318 | `## Yönetici Özeti` |
| 33 | sample-report-output.md:9 | `This week's analysis shows a **17% improvement in commit velocity** for teams using Claude Code effectively.` | scripts/rapor.py:324-336 | Aynı "kalın vurgulu ana sayı" biçimi, ama sayı ÖLÇÜLÜR: koşu sayısı, kapı durdurma, mühür, doğrulama oranı, süre. |
| 34 | sample-report-output.md:13 | `## Usage Metrics` | scripts/rapor.py:338 | `## Kullanım Metrikleri` |
| 35 | sample-report-output.md:15-23 | ```` ```mermaid ````<br>`pie`<br>`    title Claude Code Tool Usage Distribution`<br>`    "Edit" : 356` | scripts/rapor.py:181-189 (`_mermaid_pie`), 340 | Aynı mermaid `pie` bloğu: "Katman Süre Dağılımı (ms)". |
| 36 | sample-report-output.md:25 | `### Key Metrics` | scripts/rapor.py:346 | `### Anahtar Metrikler` |
| 37 | sample-report-output.md:27-32 | `- **Session Count**: 42`<br>`- **Average Session Duration**: 28.5 minutes`<br>`- **Tool Acceptance Rate**: 78%`<br>`  - Edit: 81%` | scripts/rapor.py:348-357 | `- **Koşu Sayısı**` / `- **Ortalama Koşu Süresi**` (p50/p95 ile) / `- **Danışman Doğrulama Oranı**` + danışman bazında girintili kırılım — biçim birebir. |
| 38 | sample-report-output.md:34 | `## Linear Integration Metrics` | scripts/rapor.py:364 | `## Katman ve Kapı Dökümü` (Linear yok; boru hattının kendi artefaktı bu bölümü doldurur). |
| 39 | sample-report-output.md:38 | `### Issue Completion` | scripts/rapor.py:369 | `### Kapı Durumu` (katman × GEÇTİ/DURDU tablosu). |
| 40 | sample-report-output.md:46 | `### Active Development Tickets` | scripts/rapor.py:377 | `### Doğrulanmayan Danışmanlar` (dikkat isteyen açık kalemler). |
| 41 | sample-report-output.md:58 | `### Team Velocity` | scripts/rapor.py:397 | `### Katman Süre Eğilimi` (katman × ortalama/p95/en uzun/toplam). |
| 42 | sample-report-output.md:67 | `### Productivity Comparison` | scripts/rapor.py:406 | `### Boru Hattı Sağlığı Kıyası` (ilk yarı / son yarı). |
| 43 | sample-report-output.md:69-99 | ```` ```mermaid ````<br>`graph TD`<br>`    subgraph "Before Claude"`<br>`    B1["Commits/Week: 8.2"]`<br>… `    B1 --> I1`<br>`    A1 --> I1` | scripts/rapor.py:421-444 | Aynı `graph TD` + üç `subgraph` (İlk yarı / Son yarı / Değişim) + `B*/A* --> I*` kenarları; değerler ölçülen süre, ihlal, mühür, kapı durdurmadır. |
| 44 | sample-report-output.md:102 | `## Cost Analysis` | scripts/rapor.py:464 | `## Süre Analizi` + bölüm başında kaynak eşlemesinin açık notu (para/token yok → süre). |
| 45 | sample-report-output.md:111-114 | `- **Total Input Tokens**: 3,245,670 ($32.46)`<br>`- **Total Output Tokens**: 2,156,780 ($70.99)`<br>`- **Total Cost**: $103.45`<br>`- **Cost per Issue**: $2.46` | scripts/rapor.py:474-491 | Aynı madde dizilimi: Toplam Katman Süresi / Toplam Motor Süresi / Koşu Başına Süre / Türev Kapsamı / Determinizm. |
| 46 | sample-report-output.md:116 | `## Actionable Insights` | scripts/rapor.py:500 | `## Uygulanabilir İçgörüler` (numaralı, kalın başlıklı maddeler — kaynak biçimi). |
| 47 | sample-report-output.md:124 | `## Recommendations` | scripts/rapor.py:510 | `## Öneriler` |
| 48 | sample-report-output.md:132 | `## Session Duration Distribution` | scripts/rapor.py:517 | `## Koşu Süresi Dağılımı` |
| 49 | sample-report-output.md:147-153 | `    section Frequency`<br>`    ██         :milestone, 0, 5`<br>`    ████       :milestone, 0, 15` | scripts/rapor.py:528-530 | Sıklık çubuğu fikri korundu (`"█" * say`), ama bozuk `gantt` hilesi yerine düzgün Markdown tablosu kullanıldı (SAPMALAR §5). |
| 50 | sample-report-output.md:156-158 | `---`<br>`*This report was automatically generated using Claude Code metrics and Linear MCP integration.*` | scripts/rapor.py:545-549 | Aynı kapanış: `---` + italik üretim notu (+ gerçek/yorum/VERİ YOK ayrımı). |
| 51 | report-generation-prompt.md:44-51 | `1. Executive summary with velocity improvements`<br>`2. Usage patterns and engagement metrics`<br>… `7. Recommendations for optimization` | scripts/rapor.py:296-552 (`markdown`) | Rapor iskeleti bu 7 maddeyi karşılar; 3. madde (Linear issue) `uygulanamaz` → kapı/danışman dökümüyle değiştirildi. |
| 52 | report-generation-prompt.md:53 | `Use Mermaid diagrams for visualizations. Reference specific Linear ticket IDs where relevant."` | scripts/rapor.py:340, 421, 470 | Üç mermaid görselleştirme (2 pie + 1 graph TD); "ticket ID" yerine `kosu_id` referans verilir (Koşu Dökümü tablosu). |
| 53 | report-generation-prompt.md:62 | `- Adjust the metrics JSON to match your actual telemetry data` | scripts/olcum.py:67-104 (`METRIKLER`) | Metrik defteri tek kaynak; defterde olmayan ad `OlcumHatasi` ile REDDEDİLİR (uydurma metrik yasak). |
| 54 | report-generation-prompt.md:76-77 | `# Gather metrics from Prometheus`<br>`METRICS=$(curl -s "http://localhost:9090/api/v1/query?query=..." \| jq '...')` | scripts/rapor.py:554-562 (`uret`) | Otomasyon aynı fikirde ama yerel: Prometheus sorgusu yerine JSONL okuması; `curl`/`jq` gerekmez. |
| 55 | README.md:17-22 | `## Key Metrics Tracked`<br>`- **Cost Metrics**: Total spend, cost per session, cost by model`<br>`- **Token Usage**: Input/output tokens, cache efficiency`<br>`- **Productivity**: PR count, commit frequency, session duration`<br>`- **Team Analytics**: Usage by developer, adoption rates` | KANIT.md §2 | Dört metrik ailesinin tamamı §2'de tek tek ele alındı (karşılığı olmayanlar `uygulanamaz`). |
| 56 | claude_code_roi_full.md:534-537 | `1. **Enable telemetry immediately** - Even console output gives you basic insights`<br>`2. **Set up Prometheus for real measurement**` … | SKILL.md (Kullanım) | Sıra tersine çevrildi ve gerekçelendirildi: burada "console"un yerini kalıcı JSONL alır; Prometheus adımı OPSİYONELDİR (kurulu değil). |
| 57 | docker-compose.yml:16-30 | `  prometheus:`<br>`    image: prom/prometheus:latest`<br>`    container_name: prometheus`<br>`    ports:`<br>`      - "9090:9090"` | — (uygulanmadı) | Docker bu ortamda YOK; compose dosyası bilerek KOPYALANMADI — çalışmayacak bir kurulum dosyası "hazır" gibi sunulmaz. Gerekirse kaynaktaki dosya doğrudan kullanılabilir. |

---

## 2. METRİK EŞLEME TABLOSU

Kaynağın izlediği HER metrik tek tek ele alındı (atlama yok).

| # | Kaynak metrik / gösterge | Kaynak referansı | Bizdeki karşılık | Durum |
|---|---|---|---|---|
| M1 | `claude_code.cost.usage` (USD, COUNTER) | roi_full.md:34-38, 215 | `piramit.kosu.sure_ms` — koşunun "maliyeti" bu depoda paradır değil ZAMANDIR | çevrildi (para → süre) |
| M2 | `claude_code.token.usage` (type=input/output/cacheCreation/cacheRead) | roi_full.md:101-105, 216 | `piramit.katman.sure_ms{katman}` (K1…K5) — tür bazlı kaynak tüketimi kırılımı | çevrildi |
| M3 | `claude_code.session.count` | roi_full.md:213 | `piramit.kosu.sayisi{sembol,durum}` | doğrudan karşılık |
| M4 | `claude_code.code_edit_tool.decision{decision=accept/reject}` | roi_full.md:214, 263-264 | `piramit.danisman.dogrulandi` / `piramit.danisman.dogrulanmadi{danisman}` (K4 `verifier[].confirmed`) | doğrudan karşılık (kabul/ret → doğrulandı/doğrulanmadı) |
| M5 | `claude_code.api_error` (group by error, model) | roi_full.md:311-314 | `piramit.motor.hata{motor,sebep}` | doğrudan karşılık |
| M6 | `claude_code.pull_request.count` | roi_full.md:203 | **uygulanamaz** — bu depo kod/PR üretmez, karar-destek üretir. En yakın "tamamlanmış iş" göstergesi olarak `piramit.emir.uretildi` ayrı bir metrik olarak eklendi; PR ile EŞDEĞER sayılmaz (PR bir kod teslimidir, emir bir karar önerisidir). | uygulanamaz + ikame |
| M7 | `claude_code.commit.count` | roi_full.md:204 | **uygulanamaz** — commit sayısı bu boru hattının çıktısı değildir; koşu artefaktı `engine/state` sicilidir ve commit'i CLAUDE.md akışı yapar, motor değil. Sayılsaydı ölçtüğü şey Claude'un değil kullanıcının davranışı olurdu. | uygulanamaz |
| M8 | `claude_code.lines_of_code.count{type=added/removed}` | roi_full.md:205, dashboard:275,597 | **uygulanamaz** — kod satırı üretilmiyor. Panel yeri boş bırakılmadı: aynı gride `piramit.gozlemci.ihlal` kondu (kaynağın kendisi de bu metriği "**Low reliability**" diye işaretliyor). | uygulanamaz + ikame |
| M9 | "cost per session" | README.md:19, roi_full.md:394 | **uygulanamaz** — USD yok. Karşılığı koşu başına SÜREDİR (`piramit.kosu.sure_ms` ortalaması); rapordaki "Koşu Başına Süre" satırı. | uygulanamaz + ikame |
| M10 | "cost by model" / `by (model)` | roi_full.md:112, dashboard:343 | **uygulanamaz** — tek "model" yok. Boyut kırılımı olarak katman (K1…K5) ve motor kullanıldı: `sum by (katman)` / `sum by (motor)`. | uygulanamaz + ikame |
| M11 | "cache efficiency ratio" (cacheRead/cacheCreation) | roi_full.md:395 | **uygulanamaz** — prompt önbelleği yok. Kavramsal en yakın ölçüm `piramit.determinizm`'dir (aynı girdi aynı sonucu veriyor mu) ama önbellek verimliliği DEĞİLDİR; eşdeğer sunulmaz. | uygulanamaz |
| M12 | "Active users" / `count by (user_id)` | dashboard:149 | `count by (sembol)` — tek kullanıcılı depo; "aktif özne" sembol (BTCUSDT/ETHUSDT) düzeyindedir | çevrildi |
| M13 | `user.id` / `session.id` / `user_email` nitelikleri | roi_full.md:44-46, 108 | `kosu_id` (session.id), `sembol` (özne). Kullanıcı kimliği **uygulanamaz** — tek kullanıcı, kimlik toplamak gereksiz veri. | kısmen + uygulanamaz |
| M14 | Session duration distribution | sample-report:132-153, roi_full.md:180-193 | `piramit.kosu.sure_ms` + raporun "Koşu Süresi Dağılımı" kova tablosu | doğrudan karşılık |
| M15 | Tool usage distribution (Edit/Read/Bash sayıları) | sample-report:15-23, prompt:31-36 | `piramit.motor.sure_ms{motor}` ve `piramit.motor.hata{motor}` — "hangi araç ne kadar kullanıldı" → "hangi motor ne kadar sürdü / kaç kez düştü" | çevrildi |
| M16 | Tool acceptance rates (Edit 0.81 …) | prompt:37-41, sample-report:30-32 | Danışman doğrulama oranı (danışman bazında) | doğrudan karşılık |
| M17 | `claude_code.user_prompt` + `prompt_length` (OTEL_LOG_USER_PROMPTS=1) | roi_full.md:341-345 | **uygulanamaz** — kullanıcı istemi içeriği toplanmaz. İstem metni bu depoda güvenilmez girdi sınıfındadır (`guven-katmanlama`/`sema-dogrulama`); telemetriye kopyalanması sızıntı yüzeyi açardı. | uygulanamaz (bilinçli) |
| M18 | Linear issue completion / ticket ID'leri (KAS-10…KAS-15) | sample-report:38-56 | **uygulanamaz** — Linear MCP yok, issue yok. Bölüm boş bırakılmadı: kapı/danışman/ihlal dökümüyle değiştirildi. | uygulanamaz + ikame |
| M19 | MTTR / bug resolution join (Jira) | roi_full.md:319-331 | **uygulanamaz** — hata takip sistemi yok. En yakın ölçüm, koşunun kendi hesap-verme akışıdır (`kiyas.akibet_olc`), ama o bu becerinin değil piramidin işidir; kopyalanmadı. | uygulanamaz |
| M20 | Subscription/tier maliyet projeksiyonu (Pro/Max 5x/20x) | roi_full.md:274-295 | **uygulanamaz** — abonelik/fiyat modeli yok. | uygulanamaz |
| M21 | Developer tenure ↔ acceptance korelasyonu | roi_full.md:259-272 | **uygulanamaz** — geliştirici popülasyonu yok (tek kullanıcı). | uygulanamaz |
| M22 | — (kaynakta karşılığı YOK, bize özgü) | — | `piramit.kapi.gecti` / `piramit.kapi.durdu{katman}` — piramidin fail-closed kapıları | yeni (depoya özgü) |
| M23 | — | — | `piramit.gozlemci.ihlal{kod,kritik}` / `piramit.gozlemci.uyari` / `piramit.muhur` | yeni (depoya özgü) |
| M24 | — | — | `piramit.zorunlu_girdi.eksik{girdi}` (likidasyon / görsel okuma) | yeni (depoya özgü) |
| M25 | — | — | `piramit.turev.kapsam` (turev-akis `kapsam` alanı) | yeni (depoya özgü) |
| M26 | — | — | `piramit.determinizm{veri_imzasi,sonuc_imzasi}` | yeni (depoya özgü) |

**Sayım:** kaynağın 21 metrik/göstergesinden **9'u eşlendi** (M1-M5, M12, M14-M16),
**12'si uygulanamaz** (M6-M11, M13-kısmi, M17-M21) — 5'i ikame panel/metrikle
telafi edildi. Depoya özgü **5 yeni metrik ailesi** eklendi (M22-M26).
Toplam yazılabilir metrik: **16** (`olcum.py --defter`).

---

## 3. SAPMALAR

**§1 — OTel / Prometheus / Grafana KURULU DEĞİL.**
Kaynağın tüm ölçüm yolu OTLP → Collector → Prometheus → Grafana zinciridir
(`docker-compose up -d`, roi_full.md:62-63). Bu ortamda Docker da, bu üç bileşen
de yoktur. Bu yüzden **birincil yol yerel JSONL + Markdown rapordur**
(`scripts/olcum.py`, `scripts/rapor.py`, sıfır bağımlılık). Dış yığın
`sunucu/` altında **opsiyoneldir** ve SKILL.md'de "bu ortamda kurulu değil,
çalıştırılamaz" diye açıkça yazılmıştır. JSONL satırları OTel veri noktası
şeklinde tutulur ki köprü yazılırsa eşleme birebir olsun; **köprü YAZILMADI**
(bağımlılık gerektirir) ve yazılmış gibi sunulmaz.

**§2 — Token/maliyet metrikleri → süre/kapı metriklerine çevrildi.**
Bu depo Claude Code CLI'ı değil, kendi Python boru hattını koşturur; token da
USD da ölçülemez (ölçülseydi uydurma olurdu). "Harcanan kaynak" burada
**süredir**; "kabul/ret" burada **danışman doğrulamasıdır**; "hata" burada
**motorun sonuç üretememesidir**. Rapordaki "Süre Analizi" bölümü, kaynağın
"Cost Analysis" bölümünün karşılığı olduğunu ve USD'nin VERİ YOK olduğunu
bölümün ilk satırında söyler.

**§3 — Linear MCP entegrasyonu yok.**
Kaynağın rapor akışı Linear MCP'den issue/velocity çeker
(report-generation-prompt.md:9, 15). Burada issue takip sistemi yoktur; bölüm
boş bırakılmadı, boru hattının kendi artefaktıyla (kapı, danışman, ihlal)
dolduruldu. Uydurma ticket ID (KAS-10 gibi) ÜRETİLMEZ.

**§4 — Rapor sayıları LLM değil, kod üretir.**
Kaynakta rapor bir `claude -p "…"` istemiyle üretilir (roi_full.md:443). Burada
rapor deterministik Python'dur: her sayı JSONL'den okunur, hiçbir sayı üretim
sırasında "yorumlanmaz". Böylece rapor kendi kendini doğrulayabilir
(`rapor.py --self-test` sayıları ham satırlardan BAĞIMSIZ yeniden sayar).

**§5 — Bozuk `mermaid gantt` hilesi kopyalanmadı.**
Kaynağın "Session Duration Distribution" bloğu (sample-report:134-153) geçersiz
mermaid'dir (`gantt` içinde `██ :milestone` satırları). Sıklık-çubuğu fikri
korundu, gösterim Markdown tablosuna alındı. Aynı şekilde kaynağın
`mermaid bar` bloğu (sample-report:60-65) da geçerli mermaid değildir;
onun yerine `graph TD` kıyas bloğu (kaynağın kendi geçerli deseni) kullanıldı.

**§6 — Ölçüm dosyasının yeri değiştirildi.**
İstenen varsayılan `engine/state/olcum.jsonl` idi; depo denetlendi ve
`engine/state/` **git-takipli** bulundu (`durum.json`, `defter.jsonl`,
`onceki_kosu.json` commit edilmiş; `engine/.gitignore` yalnız `__pycache__`
içeriyor) — üstelik CLAUDE.md "koşu sonrası `engine/state/` değişiklikleri
commit+push edilir" diyor. Telemetri oraya yazılsaydı her koşu karar siciline
gürültü commit'i eklerdi. Varsayılan `izleme-telemetri/state/olcum.jsonl`
oldu (kendi `.gitignore`'umuzda); `--dosya` / `IZLEME_OLCUM_DOSYA` ile
`engine/state`'e yönlendirilebilir.

**§7 — `docker-compose.yml` kopyalanmadı.**
Docker yok; çalışmayacak bir kurulum dosyasını depoya koymak "kurulu" izlenimi
verirdi. Gerekirse kaynaktaki dosya doğrudan kullanılabilir (KANIT §1 no. 57).

**§8 — Depoya dokunulmadı.**
`piramit.py` sarmalanmadı (kod değişikliği gerekirdi ve görev sınırı yalnız
`.claude/skills/izleme-telemetri/`). Bu yüzden süre metrikleri, entegrasyonu
yapan kişinin `zamanlayici` ile sarmalamasıyla dolar; sayaç metrikleri ise
bitmiş rapordan `--rapor` ile geriye dönük çıkarılabilir (kod değişikliği
gerektirmez). Bu sınır SKILL.md'de açıkça yazılıdır.

---

## 4. DOĞRULAMA (`--self-test` çıktıları)

Komutlar depo kökünde koşuldu; ham çıktılar `ornek/` altındadır
(`ornek/self_test_olcum.json`, `ornek/self_test_rapor.json`).

### 4.1 `python3 .claude/skills/izleme-telemetri/scripts/olcum.py --self-test`

```
SONUÇ: GEÇTİ — 15/15 kontrol
dosya: .claude/skills/izleme-telemetri/ornek/olcum_ornek.jsonl
olay_sayisi: 72
metrik_adlari: 16 ad (piramit.determinizm … piramit.zorunlu_girdi.eksik)
sure_ozet_ms: {"n": 13, "ortalama": 31.602, "en_uzun": 49.151}   ← GERÇEK ölçüm
```

Geçen kontroller: bozuk satır yok · 3 koşu sayacı · 13 katman süresi (5+5+3) ·
6 motor hatası (3 sarmalama istisnası + 3 rapor kaydı) · 1 kapı durdurma
(ETH/K3-COKLU-AJAN) · 2 koşuda doğrulanmayan `grafik-calisma` · 1 UYDURMA
ihlali · 1 mühür · 6 zorunlu girdi eksiği (3×2) · 3 türev kapsam ölçümü ·
3 determinizm ölçümü · BTC ikinci koşusunda determinizm KIRIK (0.0) ·
süreler pozitif ve gerçek ölçüm · **defter dışı metrik reddedildi**
(`claude_code.cost.usage` yazılmaya çalışıldı → `OlcumHatasi`) ·
**sayısal olmayan değer reddedildi**.

Not: süreler `time.sleep` ile gerçekten harcanır ve `zamanlayici` ile ÖLÇÜLÜR —
JSONL'e sahte sayı ENJEKTE EDİLMEZ.

### 4.2 `python3 .claude/skills/izleme-telemetri/scripts/rapor.py --self-test`

```
SONUÇ: GEÇTİ — 12/12 kontrol
olcum_dosyasi: ornek/olcum_ornek.jsonl   (72 veri noktası)
rapor_dosyasi: ornek/rapor_ornek.md      (181 satır)
bagimsiz_sayim: {"kosu": 3, "kapi_durdu": 1, "muhur": 1, "ihlal": 1,
                 "zorunlu_eksik": 6, "dogrulanmadi": 4, "determinizm_kirik": 1}
```

Doğrulama **dairesel değildir**: beklenen sayılar `topla()` ile değil, ham JSONL
satırları tek tek okunarak hesaplanır ve üretilen Markdown metninde ARANIR
(`rapor.py:565-642`). Geçen kontroller: olcum öz-testi geçti · rapor dosyası
yazıldı · koşu sayısı raporda doğru · kapı durdurma doğru · mühür doğru · ihlal
doğru · zorunlu girdi eksiği doğru · doğrulanmayan danışman doğru · determinizm
kırığı raporlandı · **10 kaynak bölüm başlığının tamamı mevcut** · ≥2 mermaid
görselleştirme · tüm katman adları `KATMANLAR` defterinden (uydurma ad yok).

### 4.3 Üretilen örnek rapordan (gerçek sayılar)

```
Bu dönemde **3 piramit koşusu** ölçüldü; **1** koşu bir katman kapısında durdu,
**1** koşu gözlemci kritik ihlaliyle **mühürlendi** (işlem yok). Danışman
doğrulama oranı **%33** (2/6). Toplam katman süresi **392 ms**, koşu başına
ortalama **134 ms**.
```

### 4.4 Yapılandırma dosyaları ayrıştırılabilir

```
python3 -c "json.load(open('sunucu/grafana-dashboard.json'))"      → dashboard JSON OK (8 panel)
python3 -c "yaml.safe_load(open('sunucu/otel-collector-config.yaml'))" → YAML OK
python3 -c "yaml.safe_load(open('sunucu/prometheus.yml'))"             → YAML OK
```

(Ayrıştırma testi bu dosyaların **çalıştığını** kanıtlamaz — Grafana/Prometheus
kurulu değildir; yalnız biçimsel geçerliliği gösterir.)
