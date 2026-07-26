#!/usr/bin/env python3
"""KİMİ KONSOL — claude.ai sohbet sayfasının YERİNE geçen yerel web konsolu.

Tarayıcıda claude.ai yerine BU sayfa açılır:
  · Girişte KIMI API ANAHTARI girilir (claude.ai hesabı GEREKMEZ; anahtar
    yalnız tarayıcının localStorage'ında durur, sunucu diske YAZMAZ).
  · Soru sorulur → repo motorlarının (piramit K1→K5) ÖLÇÜLMÜŞ çıktıları
    kanıt olarak derlenir → KİMİ K3 (tez) cevap verir → KİMİ CODE (antitez)
    onu ÇÜRÜTMEYE çalışır → K3 kısa savunma yapar → HÜKÜM (uzlaşı/çelişki)
    → EN ALTTA MOTORUN BAĞLAYICI KARARI (YÖN + İŞLEM KALİTESİ + EMİR).
  · "Koşuyu Yenile" düğmesi kancayı (piramit_auto.py) çalıştırır — veri
    değişmediyse kanca kendisi koşmaz (hafıza kirletilmez).

Doğruluk sözleşmesi (CLAUDE.md) burada da geçerlidir:
  · Modellere YALNIZ motorların ölçtüğü sayılar verilir; SEVİYE/EMİR ÜRETMELERİ
    YASAKTIR — bağlayıcı emir DAİMA motorundur (emir_plani + rr_denetim).
  · Modellerin metni iddia_denetle.py'den geçirilir; rapora dayanmayan SAYI
    varsa KAYNAKSIZ diye AÇIKÇA işaretlenir (gizlenmez).
  · Anahtar/ağ yoksa LLM bölümü "VERİ YOK" der; motor kararı yine gösterilir
    (fail-closed — sohbet çöker, karar uydurulmaz).

SINIR: Bu konsol GÖRÜNTÜ OKUYAMAZ. CoinGlass ekran görüntüleri/likidasyon
elle (gorsel_okuma.json / likidasyon.json) ya da veri paketiyle girilmeye
devam eder. ⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.

Kullanım:
    python3 kimi_konsol.py            # http://127.0.0.1:8787
    KIMI_BASE_URL=https://api.kimi.com/coding python3 kimi_konsol.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent
SKILL = REPO / ".claude" / "skills" / "piramit-sistem"
STATE = SKILL / "state"
HOOK = REPO / ".claude" / "hooks" / "piramit_auto.py"
YOK = "VERİ YOK"

AYAR = {
    "port": int(os.environ.get("KIMI_KONSOL_PORT", "8787")),
    "taban_uc": os.environ.get("KIMI_BASE_URL",
                               "https://api.moonshot.ai/anthropic"),
    "model_tez": os.environ.get("KIMI_MODEL_TEZ", "kimi-k3"),
    "model_antitez": os.environ.get("KIMI_MODEL_ANTITEZ", "kimi-k2.7-code"),
    "zaman_asimi": 120,
    "azami_token": 1500,
}

KURAL_ORTAK = (
    "Türkçe cevap ver. SANA VERİLEN ÖLÇÜMLER dışında hiçbir sayı kullanma, "
    "üretme, tahmin etme. Fiyat seviyesi, giriş, stop, hedef ÜRETME — bağlayıcı "
    "emir motorundur ve sana zaten verildi; sen yalnız yorumlar ve sınarsın. "
    "Eksik olan şeye 'VERİ YOK' de. Hikâye anlatma. "
    "Cevabının EN SON satırı TEK BAŞINA şu JSON olsun: "
    '{"yon":"long|short|flat","guven":0.0-1.0}')

ROL_TEZ = ("Sen bu deponun piyasa analiz danışmanısın (TEZ). Kullanıcının "
           "SORUSUNA, sana verilen ölçülmüş motor çıktılarına dayanarak en "
           "fazla 10 cümlede cevap ver. " + KURAL_ORTAK)

ROL_ANTITEZ = ("Sen ŞÜPHECİ bir denetçisin (ANTİTEZ). Aynı ölçümler ve TEZ "
               "modelinin cevabı sana verildi. Görevin tezi ÇÜRÜTMEYE çalışmak: "
               "kanıtın desteklemediği her iddiayı yakala. Kanıt tezi gerçekten "
               "destekliyorsa katıl — muhalefet için muhalefet etme. En fazla "
               "8 cümle. " + KURAL_ORTAK)

ROL_SAVUNMA = ("Sen TEZ danışmanısın; antitezin eleştirisi sana verildi. En "
               "fazla 4 cümlede kapanış yap: haklı olduğu noktayı kabul et, "
               "haksız olduğu noktada kanıt göster, NİHAİ duruşunu bildir. "
               + KURAL_ORTAK)


# ---------------------------------------------------------------- yardımcılar
def _oku(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _kimi(model: str, sistem: str, kullanici: str, anahtar: str) -> str:
    """Anthropic-uyumlu /v1/messages çağrısı → ham metin. Hata → RuntimeError."""
    url = AYAR["taban_uc"].rstrip("/") + "/v1/messages"
    govde = json.dumps({"model": model, "max_tokens": AYAR["azami_token"],
                        "system": sistem,
                        "messages": [{"role": "user", "content": kullanici}]}
                       ).encode("utf-8")
    istek = urllib.request.Request(url, data=govde, method="POST", headers={
        "content-type": "application/json", "x-api-key": anahtar,
        "authorization": f"Bearer {anahtar}",
        "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(istek, timeout=AYAR["zaman_asimi"]) as r:
            ham = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: "
                           f"{e.read().decode('utf-8', 'replace')[:200]}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise RuntimeError(f"ağ: {type(e).__name__}: {e}") from e
    metin = "".join(b.get("text", "") for b in (ham.get("content") or [])
                    if isinstance(b, dict) and b.get("type") == "text").strip()
    if not metin:
        raise RuntimeError("model boş metin döndürdü")
    return metin


def _kuyruk_json(metin: str) -> dict | None:
    """Cevabın SON satırındaki {yon, guven} JSON'unu ayıkla; tutmazsa None."""
    s = metin.rfind("{")
    e = metin.rfind("}")
    if s < 0 or e <= s:
        return None
    try:
        d = json.loads(metin[s:e + 1])
    except json.JSONDecodeError:
        return None
    yon = str(d.get("yon", "")).lower()
    try:
        guven = float(d.get("guven"))
    except (TypeError, ValueError):
        return None
    if yon not in ("long", "short", "flat") or not 0.0 <= guven <= 1.0:
        return None
    return {"yon": yon, "guven": round(guven, 4)}


def _govdesiz(metin: str) -> str:
    """Kuyruk JSON'unu metinden çıkar (balonlarda iki kez görünmesin)."""
    s = metin.rfind("{")
    return metin[:s].rstrip() if s > 0 else metin


def _ozet() -> dict:
    """Son koşunun kararları — rapor dosyalarından OKUNUR, üretilmez."""
    cikti = {}
    for ad, et in (("son_rapor.json", "BTCUSDT"),
                   ("son_rapor_eth.json", "ETHUSDT")):
        d = _oku(STATE / ad)
        if not d:
            cikti[et] = {"durum": f"{YOK} — {ad} yok"}
            continue
        z = d.get("ZIRVE") or {}
        den = z.get("DENETIM") or {}
        cikti[et] = {
            "YON": z.get("YON_BIAS", YOK), "yon_skoru": z.get("yon_skoru"),
            "guven": z.get("guven_skoru"),
            "ISLEM_KALITESI": z.get("ISLEM_KALITESI", YOK),
            "EMIR": z.get("EMIR", YOK),
            "alternatifler": [
                f"{a.get('emir_tipi')} @{a.get('giris')} | stop {a.get('stop')}"
                f" | T1 {a.get('hedef')} | R {a.get('R')}"
                for a in (z.get("emir_adaylari") or [])[1:4]],
            "red_nedenleri": (z.get("emir_red_nedenleri") or [])[:3],
            "celiski_turu": z.get("CELISKI_TURU", YOK),
            "denetim": den.get("ozet", YOK),
            "muhurlendi": bool(den.get("muhurlendi")),
            "uyarilar": [u[:100] for u in (den.get("uyari") or [])],
        }
    return cikti


def _kanit() -> dict:
    """Modele giden kanıt — yalnız rapor/plan dosyalarındaki ölçülmüş değerler."""
    kanit = {"motor_karari": _ozet()}
    for ad, anahtar in (("son_rapor.json", "BTCUSDT_danismanlar"),
                        ("son_rapor_eth.json", "ETHUSDT_danismanlar")):
        d = _oku(STATE / ad)
        if not d:
            continue
        for L in d.get("katmanlar") or []:
            if L.get("katman") == "K3-COKLU-AJAN":
                kanit[anahtar] = [
                    {"ad": x.get("name"), "durus": x.get("stance"),
                     "guven": x.get("confidence")}
                    for x in (L.get("danismanlar") or [])]
        kanit.setdefault("KIYAS", {})[anahtar.split("_")[0]] = \
            (d.get("ZIRVE") or {}).get("KIYAS")
    plan = _oku(REPO / "engine" / "state" / "plan_kosullu.json")
    if plan:
        kanit["edge_olcumu"] = plan.get("edge_olcumu")
        kanit["portfoy_olcumu"] = plan.get("portfoy_olcumu")
    devir = _oku(REPO / "engine" / "state" / "devir_teslim.json")
    if devir:
        kanit["onceki_pencere"] = {k: devir.get(k)
                                   for k in ("BTCUSDT", "ETHUSDT")}
    return kanit


def _motor_blok() -> str:
    """Bağlayıcı karar bloğu — DETERMİNİST, LLM'e yazdırılmaz."""
    satir = []
    for et, o in _ozet().items():
        if "durum" in o:
            satir.append(f"{et}: {o['durum']}")
            continue
        satir.append(f"{et} → YÖN {o['YON']} ({o['yon_skoru']}) | "
                     f"{o['ISLEM_KALITESI']}")
        satir.append(f"   EMİR: {o['EMIR']}")
        for a in o["alternatifler"]:
            satir.append(f"   ↳ {a}")
        satir.append(f"   Gözlemci: {o['denetim']}"
                     + ("  ⛔ MÜHÜRLÜ" if o["muhurlendi"] else ""))
    satir.append("⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.")
    return "\n".join(satir)


def _iddia_denetimi(metin: str) -> dict:
    """LLM metnindeki sayıları rapora karşı denetle (kaynaksız sayı = ifşa)."""
    arac = SKILL / "scripts" / "iddia_denetle.py"
    raporlar = [STATE / "son_rapor.json", STATE / "son_rapor_eth.json",
                REPO / "engine" / "state" / "plan_kosullu.json",
                REPO / "engine" / "state" / "devir_teslim.json"]
    argv = [sys.executable, str(arac)]
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as f:
            f.write(metin)
            yol = f.name
        argv += ["--metin", yol]
        for r in raporlar:
            if r.exists():
                argv += ["--rapor", str(r)]
        pr = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        os.unlink(yol)
        return json.loads(pr.stdout)
    except Exception as e:                                   # noqa: BLE001
        return {"durum": f"denetim koşamadı ({type(e).__name__})"}


def _tartisma(anahtar: str, soru: str) -> dict:
    """K3 (tez) → Kimi Code (antitez) → K3 (savunma) → hüküm. Fail-closed."""
    kanit = json.dumps(_kanit(), ensure_ascii=False)[:12000]
    taban = (f"ÖLÇÜLMÜŞ MOTOR ÇIKTILARI (tek kaynak budur):\n{kanit}\n\n"
             f"KULLANICININ SORUSU: {soru}")
    sonuc = {"tez": None, "antitez": None, "savunma": None,
             "hukum": YOK, "hatalar": []}

    tez_m = anti_m = None
    try:
        tez_m = _kimi(AYAR["model_tez"], ROL_TEZ, taban, anahtar)
        sonuc["tez"] = {"model": AYAR["model_tez"],
                        "metin": _govdesiz(tez_m),
                        "durus": _kuyruk_json(tez_m)}
    except RuntimeError as e:
        sonuc["hatalar"].append(f"{AYAR['model_tez']}: {e}")

    if tez_m:
        try:
            anti_m = _kimi(AYAR["model_antitez"], ROL_ANTITEZ,
                           taban + "\n\nTEZİN CEVABI (çürütmeye çalış):\n"
                           + tez_m, anahtar)
            sonuc["antitez"] = {"model": AYAR["model_antitez"],
                                "metin": _govdesiz(anti_m),
                                "durus": _kuyruk_json(anti_m)}
        except RuntimeError as e:
            sonuc["hatalar"].append(f"{AYAR['model_antitez']}: {e}")

    if tez_m and anti_m:
        try:
            sav_m = _kimi(AYAR["model_tez"], ROL_SAVUNMA,
                          taban + "\n\nSENİN TEZİN:\n" + tez_m
                          + "\n\nANTİTEZİN ELEŞTİRİSİ:\n" + anti_m, anahtar)
            sonuc["savunma"] = {"model": AYAR["model_tez"],
                                "metin": _govdesiz(sav_m),
                                "durus": _kuyruk_json(sav_m)}
        except RuntimeError as e:
            sonuc["hatalar"].append(f"savunma: {e}")

    d_tez = ((sonuc.get("savunma") or {}).get("durus")
             or (sonuc.get("tez") or {}).get("durus"))
    d_anti = (sonuc.get("antitez") or {}).get("durus")
    if d_tez and d_anti:
        if d_tez["yon"] == d_anti["yon"]:
            sonuc["hukum"] = f"UZLAŞI — iki model de {d_tez['yon']}"
        elif "flat" in (d_tez["yon"], d_anti["yon"]):
            sonuc["hukum"] = f"KISMİ AYRIŞMA — {d_tez['yon']} vs {d_anti['yon']}"
        else:
            sonuc["hukum"] = (f"ÇELİŞKİ — {d_tez['yon']} vs {d_anti['yon']}; "
                              "bağlayıcı olan motor kararıdır (fail-closed)")
    elif d_tez or d_anti:
        sonuc["hukum"] = "TEK TARAFLI — karşı model cevap veremedi"

    metinler = "\n".join((x or {}).get("metin", "")
                         for x in (sonuc["tez"], sonuc["antitez"],
                                   sonuc["savunma"]) if x)
    if metinler.strip():
        sonuc["iddia_denetimi"] = _iddia_denetimi(metinler)
    return sonuc


# ------------------------------------------------------------------ HTTP
SAYFA = """<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kimi Konsol — Piramit</title><style>
:root{color-scheme:dark}
body{margin:0;font:15px/1.5 system-ui,sans-serif;background:#101014;color:#e8e8ec}
header{display:flex;gap:8px;align-items:center;padding:10px 14px;background:#17171d;
 border-bottom:1px solid #2a2a33;position:sticky;top:0;flex-wrap:wrap}
header b{color:#9ecbff}
input,textarea,button{font:inherit;border-radius:8px;border:1px solid #33333d;
 background:#1d1d24;color:#e8e8ec;padding:8px 10px}
input{width:280px}
button{cursor:pointer;background:#24435f}button:hover{background:#2c527a}
#kutu{max-width:900px;margin:0 auto;padding:14px}
.kart{background:#17171d;border:1px solid #2a2a33;border-radius:10px;
 padding:10px 12px;margin:10px 0;white-space:pre-wrap;overflow-x:auto}
.k-soru{border-color:#3d5a80}.k-tez{border-color:#3a5f3a}
.k-anti{border-color:#7a4040}.k-sav{border-color:#3a5f3a}
.k-hukum{border-color:#8a7a2a}.k-motor{border-color:#9ecbff;background:#131a22}
.k-uyari{border-color:#aa4444;color:#ffb3b3}
.rozet{font-size:12px;color:#9aa0aa;margin-bottom:4px}
#durum{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media(max-width:640px){#durum{grid-template-columns:1fr}}
form{display:flex;gap:8px;margin:12px 0}
textarea{flex:1;min-height:64px;resize:vertical}
footer{color:#8a8f99;font-size:12px;text-align:center;padding:14px}
</style></head><body>
<header><b>KİMİ KONSOL</b> · kimi-k3 (tez) ↔ kimi-code (antitez)
 <input id="anahtar" type="password" placeholder="KIMI API anahtarı (sk-…)">
 <button onclick="anahtarKaydet()">Anahtarı Kaydet</button>
 <button onclick="kos()">Koşuyu Yenile (motorlar)</button>
</header>
<div id="kutu">
 <div id="durum"></div>
 <form onsubmit="sor(event)">
  <textarea id="soru" placeholder="Sorunu yaz — örn: karar nedir, giriş çıkış ver"></textarea>
  <button>Sor</button></form>
 <div id="akis"></div>
</div>
<footer>Anahtar yalnız bu tarayıcının localStorage'ında; sunucu diske yazmaz.
 · Görüntü okuma bu konsolda YOK (paneller elle girilir).
 · ⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.</footer>
<script>
const $=id=>document.getElementById(id);
$('anahtar').value=localStorage.getItem('kimi_anahtar')||'';
function anahtarKaydet(){localStorage.setItem('kimi_anahtar',$('anahtar').value.trim());
 kartEkle('k-hukum','','Anahtar bu tarayıcıya kaydedildi.')}
function kartEkle(cls,rozet,metin){const d=document.createElement('div');
 d.className='kart '+cls;d.innerHTML=(rozet?'<div class="rozet">'+rozet+'</div>':'')+
 metin.replace(/&/g,'&amp;').replace(/</g,'&lt;');$('akis').prepend(d);return d}
async function durum(){const r=await fetch('/durum');const d=await r.json();
 $('durum').innerHTML=Object.entries(d).map(([et,o])=>{
  if(o.durum)return `<div class="kart">${et}: ${o.durum}</div>`;
  return `<div class="kart k-motor"><div class="rozet">${et}</div>`+
   `YÖN <b>${o.YON}</b> (${o.yon_skoru}) — ${o.ISLEM_KALITESI}\\n`+
   `EMİR: <b>${o.EMIR}</b>\\n${o.denetim}${o.muhurlendi?' ⛔ MÜHÜRLÜ':''}</div>`}).join('')}
async function kos(){const k=kartEkle('k-hukum','motorlar','Koşu başladı — veri '+
 'değişmediyse kanca koşmaz (hafıza korunur)…');
 const r=await fetch('/kos',{method:'POST'});const d=await r.json();
 k.textContent=(d.cikti||'').slice(-1800)||('çıkış kodu '+d.kod);durum()}
async function sor(ev){ev.preventDefault();
 const soru=$('soru').value.trim();if(!soru)return;
 const anahtar=localStorage.getItem('kimi_anahtar')||'';
 kartEkle('k-soru','sen',soru);$('soru').value='';
 const bek=kartEkle('k-hukum','','Kimi kurulu tartışıyor…');
 const r=await fetch('/soru',{method:'POST',headers:{'content-type':'application/json'},
  body:JSON.stringify({anahtar,soru})});
 const d=await r.json();bek.remove();
 kartEkle('k-motor','NİHAİ KARAR — motor (bağlayıcı)',d.motor_blok||'VERİ YOK');
 const id=d.tartisma&&d.tartisma.iddia_denetimi;
 if(id&&id.KAYNAKSIZ&&id.KAYNAKSIZ.length)
  kartEkle('k-uyari','iddia denetimi','KAYNAKSIZ SAYI: '+
   id.KAYNAKSIZ.map(x=>x.deger).join(', ')+' — rapora dayanmıyor, dikkate alma');
 if(d.tartisma){const t=d.tartisma;
  if(t.hukum)kartEkle('k-hukum','HÜKÜM',t.hukum);
  if(t.savunma)kartEkle('k-sav','kimi-k3 · savunma',t.savunma.metin);
  if(t.antitez)kartEkle('k-anti','kimi-code · antitez',t.antitez.metin);
  if(t.tez)kartEkle('k-tez','kimi-k3 · tez',t.tez.metin);
  (t.hatalar||[]).forEach(h=>kartEkle('k-uyari','hata',h));}
 durum()}
durum();
</script></body></html>"""


class Istekci(BaseHTTPRequestHandler):
    def log_message(self, *a):                                # sessiz
        pass

    def _gonder(self, veri, tip="application/json; charset=utf-8", kod=200):
        govde = (veri if isinstance(veri, bytes)
                 else json.dumps(veri, ensure_ascii=False).encode("utf-8"))
        self.send_response(kod)
        self.send_header("content-type", tip)
        self.send_header("content-length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._gonder(SAYFA.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/durum":
            self._gonder(_ozet())
        else:
            self._gonder({"hata": "yok"}, kod=404)

    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        try:
            govde = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        except json.JSONDecodeError:
            self._gonder({"hata": "bozuk JSON"}, kod=400)
            return
        if self.path == "/kos":
            try:
                pr = subprocess.run([sys.executable, str(HOOK)],
                                    capture_output=True, text=True,
                                    timeout=900, cwd=str(REPO))
                self._gonder({"kod": pr.returncode,
                              "cikti": (pr.stdout or pr.stderr or "")[-4000:]})
            except subprocess.TimeoutExpired:
                self._gonder({"kod": 124, "cikti": "900 sn içinde bitmedi"})
        elif self.path == "/soru":
            soru = str(govde.get("soru") or "").strip()
            anahtar = str(govde.get("anahtar") or "").strip()
            if not soru:
                self._gonder({"hata": "soru boş"}, kod=400)
                return
            cevap = {"motor_blok": _motor_blok()}
            if not anahtar:
                cevap["tartisma"] = {
                    "hatalar": [f"{YOK} — API anahtarı girilmedi; motor kararı "
                                "yine geçerli (fail-closed)"]}
            else:
                cevap["tartisma"] = _tartisma(anahtar, soru)
            self._gonder(cevap)
        else:
            self._gonder({"hata": "yok"}, kod=404)


def main() -> int:
    adres = ("127.0.0.1", AYAR["port"])
    print(f"KİMİ KONSOL → http://{adres[0]}:{adres[1]}")
    print(f"  uç: {AYAR['taban_uc']} | tez: {AYAR['model_tez']}"
          f" | antitez: {AYAR['model_antitez']}")
    print("  Anahtar tarayıcıda girilir; sunucu diske yazmaz. Ctrl+C ile kapat.")
    ThreadingHTTPServer(adres, Istekci).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
