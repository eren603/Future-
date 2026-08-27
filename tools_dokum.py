"""Bu penceredeki TUM kullanici girdisi + asistan ciktisini tek dosyaya doker.

DURUSTLUK NOTLARI (dosyanin basina da yazilir):
- Kaynak: Claude Code'un kendi oturum kaydi (.jsonl). Uydurma yok.
- Kancalarin (hook) enjekte ettigi metin ve <system-reminder> bloklari
  KULLANICI GIRDISI DEGILDIR - ayiklanir, ama ayiklandigi BEYAN edilir.
- Alt-ajan (sidechain) mesajlari bu konusmaya ait degildir - ayiklanir.
- Arac cagrilari (Bash/Read/Edit...) metin degildir; SAYILARI raporlanir,
  govdeleri dokume alinmaz (aksi halde 24 MB'lik bir dosya cikar).
"""
import glob
import io
import json
import os
import re

KAYNAKLAR = sorted(glob.glob(
    "/root/.claude/projects/*/4056c135-aef4-5d4b-804f-5f0dd0c8f598.jsonl"))
CIKTI = ("/tmp/claude-0/-home-user-Future-/4056c135-aef4-5d4b-804f-5f0dd0c8f598/"
         "scratchpad/OTURUM_DOKUMU.md")

KANCA_DESENLERI = (
    "UserPromptSubmit hook success", "SessionStart hook", "Stop hook feedback",
    "[PİRAMİT", "[PIRAMIT", "[KONTROL AJANLARI", "[SAĞLIK", "[SAGLIK",
)


# Bu isaretlerle BASLAYAN "kullanici" mesajlari SIZIN YAZDIGINIZ metin
# degildir: kanca ciktisi, beceri govdesi, alt-ajan bildirimi, oturum
# devri. Silinmezler - SISTEM OLAYI olarak tek satirda ozetlenirler.
SISTEM_ISARETLERI = (
    "[~/.claude/", "<task-notification>", "Base directory for this skill:",
    "A session-scoped Stop hook", "This session is being continued",
    "Continue from where you left off", "Caveat:", "<local-command",
)


def metin_cikar(icerik):
    """Mesaj govdesinden YALNIZ metin parcalarini toplar."""
    if isinstance(icerik, str):
        return icerik
    parcalar = []
    for p in icerik or []:
        if isinstance(p, dict) and p.get("type") == "text":
            parcalar.append(p.get("text", ""))
    return "\n".join(parcalar)


SECIM_ONEKLERI = ("The user answered:", "Your questions have been answered:")


def secim_cikar(icerik, secim_kimlikleri):
    """AskUserQuestion cevaplarini cikarir.

    Bu cevaplar tool_result icinde gelir ama SIZIN kararinizdir - girdi
    sayilir. IKI kapi: (1) tool_use_id GERCEKTEN bir AskUserQuestion
    cagrisina ait olmali, (2) metin cevap onekiyle BASLAMALI. Yalniz
    metin araninca kendi tesbih ciktim bile yakalaniyordu (yanlis
    pozitif) - kimlik eslesmesi bunu keser.
    """
    if not isinstance(icerik, list):
        return []
    cevaplar = []
    for p in icerik:
        if not (isinstance(p, dict) and p.get("type") == "tool_result"):
            continue
        kimlik = p.get("tool_use_id")
        if kimlik is not None and kimlik not in secim_kimlikleri:
            continue
        icerik_ic = p.get("content")
        metin = (icerik_ic if isinstance(icerik_ic, str) else
                 " ".join(x.get("text", "") for x in icerik_ic or []
                          if isinstance(x, dict))).strip()
        if not metin.startswith(SECIM_ONEKLERI):
            continue
        kes = metin.find("Read the answers carefully")
        cevaplar.append(metin[:kes if kes > 0 else len(metin)].strip())
    return cevaplar


def arac_sayisi(icerik):
    if not isinstance(icerik, list):
        return 0
    return sum(1 for p in icerik
               if isinstance(p, dict) and p.get("type") == "tool_use")


def temizle(metin):
    """system-reminder ve kanca enjeksiyonlarini ayiklar."""
    metin = re.sub(r"<system-reminder>.*?</system-reminder>", "", metin, flags=re.S)
    metin = re.sub(r"<command-name>.*?</command-message>", "", metin, flags=re.S)
    satirlar, atlanan = [], 0
    kanca_icinde = False
    for satir in metin.split("\n"):
        if any(d in satir for d in KANCA_DESENLERI):
            kanca_icinde = True
            atlanan += 1
            continue
        if kanca_icinde:
            # Kanca bloklari genelde bos satira kadar surer; basit kural:
            # "====" cizgileri ve girintili kanca ciktisi da atlanir.
            if satir.strip() == "" or satir.startswith(("=", "-", " ", "✔", "✖",
                                                        "①", "②", "⚠", "·", "↻")):
                atlanan += 1
                continue
            kanca_icinde = False
        satirlar.append(satir)
    return "\n".join(satirlar).strip(), atlanan


kayitlar, gorulen = [], set()
for yol in KAYNAKLAR:
    for satir in io.open(yol, encoding="utf-8", errors="replace"):
        try:
            k = json.loads(satir)
        except Exception:
            continue
        if k.get("isSidechain"):                 # alt-ajan konusmasi
            continue
        if k.get("type") not in ("user", "assistant"):
            continue
        kimlik = k.get("uuid")
        if kimlik in gorulen:
            continue
        gorulen.add(kimlik)
        kayitlar.append(k)

SECIM_KIMLIKLERI = set()
for k in kayitlar:
    ic = (k.get("message") or {}).get("content")
    if not isinstance(ic, list):
        continue
    for p in ic:
        if (isinstance(p, dict) and p.get("type") == "tool_use"
                and p.get("name") == "AskUserQuestion"):
            SECIM_KIMLIKLERI.add(p.get("id"))

kayitlar.sort(key=lambda k: k.get("timestamp", ""))

satirlar = []
sayac = {"kullanici": 0, "asistan": 0, "arac": 0,
         "atlanan_kanca": 0, "sistem": 0, "secim": 0}
for k in kayitlar:
    mesaj = k.get("message") or {}
    icerik = mesaj.get("content")
    metin = metin_cikar(icerik)
    sayac["arac"] += arac_sayisi(icerik)
    if k["type"] == "user":
        for secim in secim_cikar(icerik, SECIM_KIMLIKLERI):
            sayac["secim"] += 1
            satirlar.append("\n\n---\n\n## ▶ SİZ (seçim) #%d  (%s)\n\n%s"
                            % (sayac["secim"], k.get("timestamp", "")[:19], secim))
        metin, atlanan = temizle(metin)
        sayac["atlanan_kanca"] += atlanan
        if not metin:
            continue
        if metin.startswith(SISTEM_ISARETLERI):
            sayac["sistem"] += 1
            ozet = metin.split("\n")[0][:110]
            satirlar.append("\n\n> *(sistem olayi #%d — %s: `%s`)*"
                            % (sayac["sistem"], k.get("timestamp", "")[11:19], ozet))
            continue
        sayac["kullanici"] += 1
        satirlar.append("\n\n---\n\n## ▶ SİZ #%d  (%s)\n\n%s"
                        % (sayac["kullanici"], k.get("timestamp", "")[:19], metin))
    else:
        if not metin.strip():
            continue
        sayac["asistan"] += 1
        satirlar.append("\n\n### ◀ ASISTAN #%d  (%s)\n\n%s"
                        % (sayac["asistan"], k.get("timestamp", "")[:19], metin))

BASLIK = """# OTURUM DÖKÜMÜ — LLM → Trading sistemi

Bu dosya, bu penceredeki **tüm kullanıcı girdilerini** ve **tüm asistan
çıktılarını** kronolojik sırayla içerir.

## Kaynak ve dürüstlük notu

- **Kaynak:** Claude Code'un kendi oturum kaydı (`.jsonl`). Hiçbir satır
  yeniden yazılmadı, özetlenmedi veya uydurulmadı.
- **Ayıklananlar (ve nedeni):**
  - `<system-reminder>` blokları ve kanca (hook) enjeksiyonları —
    bunlar sizin yazdığınız metin DEĞİL, sistemin otomatik eklediği
    bağlamdır. Ayıklanan satır sayısı aşağıda raporlanmıştır.
  - Alt-ajan (denetçi, kod inceleyici, iş akışı ajanları) konuşmaları —
    bunlar bu pencerenin konuşması değildir.
  - Araç çağrılarının gövdeleri (Bash/Read/Edit çıktıları) — metin
    değil, iş kaydıdır; SAYISI raporlanır, gövdesi alınmaz (alınsaydı
    dosya ~24 MB olurdu).
- **Sayımlar:** aşağıdaki tabloda.

| Ölçüm | Değer |
|---|---|
| **Sizin yazdığınız mesaj** | %(kullanici)d |
| **Sizin seçiminiz** (AskUserQuestion cevabı) | %(secim)d |
| Sistem olayı (kanca/beceri/ajan bildirimi — tek satır özet) | %(sistem)d |
| Asistan mesajı | %(asistan)d |
| Araç çağrısı (gövdesi alınmadı) | %(arac)d |
| Ayıklanan kanca/hatırlatıcı satırı | %(atlanan_kanca)d |
| Kaynak dosya | %(kaynak)d |

⚠️ Bu depo yalnız karar-desteğidir; canlı/otomatik emir dahil değildir.
"""

govde = BASLIK % dict(sayac, kaynak=len(KAYNAKLAR)) + "".join(satirlar) + "\n"
io.open(CIKTI, "w", encoding="utf-8").write(govde)
print("yazildi:", CIKTI)
print("boyut  :", round(os.path.getsize(CIKTI) / 1024.0, 1), "KB")
print("sayim  :", sayac, "| kaynak dosya:", len(KAYNAKLAR))
