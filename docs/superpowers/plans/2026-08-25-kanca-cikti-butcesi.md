# Kanca Çıktı Bütçesi — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `UserPromptSubmit` kancasının bastığı koşu özetinin (YÖN / İŞLEM KALİTESİ / EMİR / GÖZLEMCİ) harness kesmesine kurban gitmeden bağlama ulaşmasını garanti etmek.

**Architecture:** İki bağımsız korkuluk. (A) **Sıra**: dinamik özet ÖNCE, sabit kural bloğu SONRA basılır — kesme olursa tekrarlanan kural kaybolur, karar değil; `main()` gövdesi `_akis()`e taşınıp sabit blok `finally`de basılarak bütün erken `return` yolları kapsanır. (B) **Bütçe**: sabit DURAN GÖREV bloğu her istemde değil, `engine/gorev.json` içeriği ya da oturum değiştiğinde tam basılır; aksi halde tek satırlık işaretçi. Damga okunamazsa TAM basılır (fail-open: duran görev asla sessizce kaybolmaz).

**Tech Stack:** Python 3.11, stdlib (`hashlib`, `os`, `json`), bağımlılık eklenmez. Test: mevcut `.claude/skills/piramit-sistem/scripts/self_test.py` içindeki `kontrol(ad, kosul, ayrinti)` deseni.

## Global Constraints

- Kanca **istemi asla bloklamaz**: çıkış kodu DAİMA 0, her yeni kod `try/except` ile sarılır (`piramit_auto.py` mevcut sözleşmesi).
- **Uydurma yok**: yeni basılan hiçbir satır ölçülmemiş sayı içermez; damga okunamazsa "VERİ YOK" yönünde değil, TAM BASMA yönünde fail-open olunur (duran görev kaybı EKSİK_AKTARIM ihlalidir).
- **Sabit dize sayı yasağı**: rapor satırındaki bayt/sayı değerleri ölçülerek basılır, elle yazılmaz (`saglik.py` SAYIM sözleşmesiyle aynı ilke).
- Değişiklik yalnız iki dosyada: `.claude/hooks/piramit_auto.py`, `.claude/hooks/session-start.sh`. Test dosyası: `.claude/skills/piramit-sistem/scripts/self_test.py`.
- Öz-testler `SELF_TEST_OK` basmalı; `saglik.py --tam` 12/12 GEÇTİ kalmalı.

---

## File Structure

| Dosya | Sorumluluk | Değişim |
|---|---|---|
| `.claude/hooks/piramit_auto.py` | Kanca akışı + çıktı sırası + damga | `main()` → `_akis()`; yeni `_sabit_bas()`, `_gorev_damgasi()`, `_oturum_kimligi()`; `_gorev_bas()` ikiye ayrılır (sabit / dinamik) |
| `.claude/hooks/session-start.sh` | Oturum açılışı | Damga dosyasını siler (ikinci emniyet) |
| `.claude/skills/piramit-sistem/scripts/self_test.py` | Regresyon kilidi | T35 (sıra), T36 (damga), T37 (bayt tavanı), T38 (çökme sırası) |
| `.claude/skills/piramit-sistem/state/gorev_damga.json` | Damga durumu (üretilen) | yeni, git'e girmez (state) |

---

### Task 1: Sıra ters çevrilir (A)

**Files:**
- Modify: `.claude/hooks/piramit_auto.py:898-900` (`main()` başı), dosya sonu (`main` sarmalayıcısı)
- Test: `.claude/skills/piramit-sistem/scripts/self_test.py` (T35)

**Interfaces:**
- Consumes: mevcut `KURAL` sabiti, `_gorev_bas()`
- Produces: `_akis() -> int` (eski `main()` gövdesi), `_sabit_bas() -> None`, `main() -> int` (sarmalayıcı)

- [ ] **Step 1: Failing test yaz** — `self_test.py` içine T30

```python
        # ---- T30: kanca — dinamik özet SABİT kuraldan ÖNCE basılır ---------
        import io, contextlib, importlib, os                       # noqa: PLC0415
        tmp_repo = tmp / "kanca_sira"
        (tmp_repo / "engine" / "girdi").mkdir(parents=True, exist_ok=True)
        os.environ["CLAUDE_PROJECT_DIR"] = str(tmp_repo)
        sys.path.insert(0, str(P.REPO / ".claude" / "hooks"))
        import piramit_auto as HOOK                                # noqa: PLC0415
        HOOK = importlib.reload(HOOK)          # REPO sabiti yeniden okunsun
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            HOOK.main()
        cikti = buf.getvalue()
        i_dinamik = cikti.find("Boru hattı dosyası bulunamadı")
        i_kural = cikti.find("[PİRAMİT — duran kural")
        kontrol("T35 kanca: dinamik özet sabit kuraldan ÖNCE basılır",
                i_dinamik >= 0 and i_kural >= 0 and i_dinamik < i_kural,
                f"dinamik@{i_dinamik} kural@{i_kural}")
```

- [ ] **Step 2: Testi koş, DÜŞTÜĞÜNÜ gör**

Run: `python3 .claude/skills/piramit-sistem/scripts/self_test.py 2>&1 | grep T35`
Expected: FAIL — `dinamik@<büyük> kural@0` (kural şu an EN ÜSTTE basılıyor)

- [ ] **Step 3: Asgari uygulamayı yaz**

`piramit_auto.py`: `def main() -> int:` satırını `def _akis() -> int:` yap, gövdenin ilk iki satırını (`print(KURAL)` ve `_gorev_bas()`) SİL. Dosya sonuna, `_sessiz_cik` tanımından ÖNCE ekle:

```python
def _sabit_bas() -> None:
    """Sabit bağlam (kural + duran görev) — akıştan SONRA basılır.

    Sıra bilerek terstir: harness çıktı üst sınırını aşarsa kesilen kuyruk
    TEKRARLANAN kural olur, o koşunun KARARI değil. Ölçüm (2026-08-25):
    kanca 14280 bayt basıyordu, bağlama ~2 KB giriyordu ve YÖN/İŞLEM/EMİR/
    GÖZLEMCİ satırlarının tamamı kesiliyordu.
    """
    try:
        print(KURAL)
        _gorev_bas()
    except (BrokenPipeError, ValueError, OSError):
        pass


def main() -> int:
    """Akış ÖNCE (dinamik), sabit bağlam SONRA — `finally` bütün erken
    `return 0` yollarını ve beklenmedik hatayı da kapsar."""
    try:
        return _akis()
    finally:
        _sabit_bas()
```

- [ ] **Step 4: Testi koş, GEÇTİĞİNİ gör**

Run: `python3 .claude/skills/piramit-sistem/scripts/self_test.py 2>&1 | grep -E "T35|SELF_TEST"`
Expected: `T35 ... ✔` ve `SELF_TEST_OK`

- [ ] **Step 5: Sağlık kontrolü + commit**

```bash
python3 .claude/skills/piramit-sistem/scripts/saglik.py --tam
git add .claude/hooks/piramit_auto.py .claude/skills/piramit-sistem/scripts/self_test.py
git commit -m "kanca: dinamik özet sabit kuraldan önce basılır (A)"
```

---

### Task 2: Sabit blok koşullu basılır (B)

**Files:**
- Modify: `.claude/hooks/piramit_auto.py:485-565` (`_gorev_bas`), sabitler bölümü (satır ~58)
- Modify: `.claude/hooks/session-start.sh` (damga silme)
- Test: `.claude/skills/piramit-sistem/scripts/self_test.py` (T36, T37, T38)

**Interfaces:**
- Consumes: `GOREV` (Path), `SKILL` (Path), Task 1'in `_sabit_bas()`i
- Produces: `DAMGA: Path`, `_oturum_kimligi() -> str`, `_gorev_damgasi() -> bool`
  (True = TAM bas, False = işaretçi bas), `_gorev_bas()` imzası değişmez

- [ ] **Step 1: Failing test yaz** — T36 + T37

```python
        # ---- T31/T32: kanca — duran görev damgası + bayt tavanı ------------
        (tmp_repo / "engine").mkdir(parents=True, exist_ok=True)
        (tmp_repo / "engine" / "gorev.json").write_text(json.dumps(
            {"gorev": "test görevi", "sira": ["1) bir", "2) iki"],
             "strateji_kurali": "X" * 2000}, ensure_ascii=False), encoding="utf-8")
        HOOK = importlib.reload(HOOK)
        b1 = io.StringIO()
        with contextlib.redirect_stdout(b1):
            HOOK.main()
        b2 = io.StringIO()
        with contextlib.redirect_stdout(b2):
            HOOK.main()
        ilk, ikinci = b1.getvalue(), b2.getvalue()
        kontrol("T36 kanca: duran görev ilk istemde TAM, ikincide işaretçi",
                "sıra: " in ilk and "sıra: " not in ikinci
                and "engine/gorev.json" in ikinci,
                f"ilk={len(ilk)}B ikinci={len(ikinci)}B")
        kontrol("T37 kanca: değişmemiş görevde çıktı ≤ 2048 bayt",
                len(ikinci.encode("utf-8")) <= 2048,
                f"{len(ikinci.encode('utf-8'))} bayt")
```

- [ ] **Step 2: Testi koş, DÜŞTÜĞÜNÜ gör**

Run: `python3 .claude/skills/piramit-sistem/scripts/self_test.py 2>&1 | grep -E "T36|T37"`
Expected: ikisi de FAIL — ikinci koşu da tam metni basıyor (`sıra: ` var, >2048 bayt)

- [ ] **Step 3: Asgari uygulamayı yaz**

`piramit_auto.py` sabitler bölümüne (`GOREV = ...` satırının ardına):

```python
DAMGA = SKILL / "state" / "gorev_damga.json"   # duran görev tekrar-basım damgası
```

`_gorev_bas()` tanımından ÖNCE ekle:

```python
def _oturum_kimligi() -> str:
    """Oturum kimliği — yeni pencere duran görevi TEKRAR tam görmeli."""
    for ad in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID"):
        v = os.environ.get(ad)
        if v:
            return v
    return ""


def _gorev_damgasi() -> bool:
    """True = duran görev TAM basılmalı, False = tek satır işaretçi yeter.

    Fail-open: damga okunamaz/yazılamazsa TAM basılır. Duran görevin sessizce
    kaybolması EKSİK_AKTARIM ihlalidir; tekrar basmak yalnız bayt maliyetidir.
    """
    try:
        ham = GOREV.read_bytes() if GOREV.is_file() else b"YOK"
    except OSError:
        return True
    yeni = {"sha": hashlib.sha256(ham).hexdigest(), "oturum": _oturum_kimligi()}
    try:
        eski = json.loads(DAMGA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        eski = None
    try:
        DAMGA.parent.mkdir(parents=True, exist_ok=True)
        _atomik_yaz(DAMGA, json.dumps(yeni, ensure_ascii=False))
    except OSError:
        return True
    return not (isinstance(eski, dict) and eski == yeni)
```

`_gorev_bas()` içinde, `g = json.loads(...)` ve tip denetiminden SONRA, `prof = ...` satırından ÖNCE ekle:

```python
        if not _gorev_damgasi():
            print("[PİRAMİT — DURAN GÖREV] değişmedi (bu oturumda basıldı) → "
                  "tam metin: engine/gorev.json")
            _sunulan_karar_bas()      # açık/kapanan emir satırları DAİMA basılır
            return
```

`_gorev_bas()` içindeki `for _ad, _sk, _gd, _st in (...)` döngüsünü (satır ~530'dan `except`e kadar) `_sunulan_karar_bas()` adlı yeni bir fonksiyona AYNEN taşı ve `_gorev_bas()` içinde o noktada `_sunulan_karar_bas()` çağır. Gerekçe: açık/kapanan emir satırları `sunulan_karar.json`dan gelir — DİNAMİKtir, damgaya bağlanamaz (hesap verme kaybolur).

`session-start.sh` içinde `SAGLIK` bloğundan sonra ekle:

```bash
# Duran görev damgası: yeni pencere görevi TAM görmeli (ikinci emniyet —
# oturum kimliği ortam değişkeni yoksa damga burada sıfırlanır).
rm -f "${CLAUDE_PROJECT_DIR:-.}/.claude/skills/piramit-sistem/state/gorev_damga.json"
```

- [ ] **Step 4: Testi koş, GEÇTİĞİNİ gör**

Run: `python3 .claude/skills/piramit-sistem/scripts/self_test.py 2>&1 | grep -E "T35|T36|T37|T38|SELF_TEST"`
Expected: üçü de ✔, `SELF_TEST_OK`

- [ ] **Step 5: Gerçek depoda ölç (kanıt), sağlık, commit**

```bash
python3 .claude/hooks/piramit_auto.py | wc -c        # 1. koşu (tam)
python3 .claude/hooks/piramit_auto.py | wc -c        # 2. koşu (işaretçi)
python3 .claude/skills/piramit-sistem/scripts/saglik.py --tam
git add -A && git commit -m "kanca: duran görev damgası — sabit blok koşullu basılır (B)"
```

Expected: 2. koşu 1.'den en az 7000 bayt küçük; `saglik.py --tam` → 12/12 GEÇTİ.

---

### Task 3: Doğrulama ve push

**Files:**
- Modify: yok (yalnız doğrulama)

**Interfaces:**
- Consumes: Task 1 + Task 2 çıktıları

- [ ] **Step 1: Tam sağlık koşusu**

Run: `python3 .claude/skills/piramit-sistem/scripts/saglik.py --tam`
Expected: `SAĞLAM — motor 20/20 ... öz-test 12/12 GEÇTİ`, çıkış 0

- [ ] **Step 2: Kanca gerçek çıktısını ölç**

Run: `python3 .claude/hooks/piramit_auto.py | head -3`
Expected: İLK satır dinamik ([PİRAMİT] ile başlayan koşu/durum satırı), kural EN SONDA

- [ ] **Step 3: Push**

```bash
git push -u origin claude/weapon-commands-config-169rlo
```

---

## Self-Review

**1. Spec coverage:** A → Task 1. B → Task 2. "sonuca göre" doğrulama → Task 3. Boşluk yok.

**2. Placeholder scan:** TBD/TODO yok; her adımda gerçek kod var.

**3. Type consistency:** `_akis() -> int` (Task 1) Task 2'de değişmiyor. `_sabit_bas()` Task 1'de tanımlanıp Task 2'de değişmeden kullanılıyor. `_gorev_damgasi() -> bool` (True=TAM) Task 2 Step 3'te tek yerde tüketiliyor. `_sunulan_karar_bas()` Task 2'de tanımlanıp aynı task içinde iki yerden çağrılıyor. `_atomik_yaz` ve `hashlib` dosyada zaten mevcut (satır 53, import bölümü).

---

## Uygulama Sonucu (2026-08-25, ölçüldü)

| Ölçüm | Önce | Sonra | Kaynak |
|---|---|---|---|
| Kanca çıktısı (kararlı durum) | 14.280 B | **6.910 B** (−%51) | `piramit_auto.py \| wc -c` |
| Sabit blok payı | 8.871 B (%62) | 1.500 B (%22) | satır bölümlemesi |
| Dinamik özet konumu | çıktının sonunda (kesiliyordu) | **çıktının başında** | `head -6` |
| Öz-test | 37/37 | **40/40** | `self_test.py` |
| `saglik.py --tam` | 12/12 GEÇTİ | 12/12 GEÇTİ | taze koşu |
| Çıkış kodu sözleşmesi | 0 | 0 (şema dışı REPO + boru kırılması altında da) | doğrulama koşusu |

**Plandan sapma (kayda geçer):** T30–T32 numaraları `self_test.py`'de doluydu
(esik_kalibre / rejim / R testleri); yeni testler **T35, T36, T37** oldu.
Ayrıca planda olmayan **T38** eklendi: `_akis()` çökerse tanı mesajı
`__main__`'de, yani sabit bloğun ARDINDAN basılıyordu — kesme altında ilk
kaybolan o olurdu (düzeltilen kusurun aynısı). Tanı `main()` içine alındı,
çıkış kodu 0 sözleşmesi korundu.

**Açık kalan (dürüstlük):** harness kesme EŞİĞİ bilinmiyor (VERİ YOK —
gözlenen tek nokta 12,8 KB'ın aştığı). 6.910 bayt eşiğin altında mı, bir
sonraki istemde görülecek: kanca çıktısı bağlama TAM girerse eşik aşılmamış
demektir. Aşılsa bile (A) garantisi ayakta: kesilen kuyruk tekrarlanan
kuraldır, kararın kendisi değil.
