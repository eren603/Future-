# harici/qwen-meta3 — Qwen Studio sohbetinden çıkarılan kod

**Kaynak (GERÇEK):** `c9b3b285-Qwen_Studio.mht` (Blink snapshot)
Snapshot-Content-Location: `https://chat.qwen.ai/c/9c646414-eb07-4342-9e7e-f7dd63afc120`
Snapshot tarihi: 2026-08-16 22:51:47 +0300

Sohbet sayfasındaki kod blokları Monaco editörüyle render edilmiş; MHT
kaydında **bütün satırlar** (virtualization yok) mevcut olduğu için kod
kayıpsız çıkarıldı. Çıkarma yöntemi: MIME `text/html` parçası → `<pre>`
blokları → `.view-line` div'leri `top` offsetine göre sıralanıp
etiketlerden arındırıldı, `&nbsp;` → boşluk.

## Dosyalar

| Dosya | Satır | Sohbette verilen ad | Not |
|---|---|---|---|
| `meta3_btc_karargah_v6.py` | 1414 | `meta3_btc_karargah_v6.py` | **ANA KOD** — "META³ BTC KARARGAH v6.0 — Tam Yenilenmiş Kod" |
| `btc_karargah_v6_0.py` | 390 | `btc_karargah_v6_0.py` | Sohbette daha ÖNCE verilen kısa/ilk v6.0 taslağı |

## Doğrulama (koşuldu)

- `python3 -m py_compile` → her iki dosya da **OK** (syntax temiz).
- v5.3.2 sürümünün bilinen bozuk token'ları (`s d`, `.ab s()`, `V_RE VERSAL`,
  `lob_i mbalance`, `if name==" main "`) kod gövdesinde **yok**; yalnızca
  başlıktaki değişiklik logunda anlatım olarak geçiyor → çıkarma sırasında
  span bölünmesinden kaynaklanan kelime kırılması olmadığının kanıtı.

## Çalıştırma bağımlılıkları (VERİ YOK — kurulu değil, denenmedi)

`ccxt`, `numpy`, `pandas`. Bu depoda kurulu olup olmadığı test EDİLMEDİ;
dosyalar yalnız syntax düzeyinde doğrulandı, **çalıştırılmadı**.

## Uyarı

Bu kod bu deponun motorlarının parçası DEĞİLDİR; dışarıdan alınmış
referans/arşiv koddur. `ccxt.binanceusdm` ile canlı borsa verisi çeker.
Kod içinde emir gönderimi olmadığı sohbette iddia ediliyor. Bu iddia
**grep ile denetlendi (GERÇEK):** her iki dosyada da `create_order` /
`createOrder` / `private_post` / `apiKey` / `secret` çağrısı YOK —
tek eşleşme başlıktaki açıklama satırının kendisi. Yani modül salt-okunur
piyasa verisi çeker. (Bu bir statik denetimdir; kod çalıştırılmadı.)
