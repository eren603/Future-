#!/usr/bin/env python3
"""cizim.py — TradingView tarzı çizimli mum grafiği üretir (SVG, sıfır bağımlılık).

Kullanım:
    python3 cizim.py --job is.json          # iş dosyasından çiz
    python3 cizim.py --araclar              # desteklenen araçları listele

İş dosyası (job) şeması:
{
  "veri":   {"kline": "engine/girdi/h4.json"}      # Binance kline JSON/CSV
            | {"mumlar": [{"open":..,"high":..,"low":..,"close":..,"volume":..,"time":..}]},
  "son_bar": 200,                                   # yalnız son N mum
  "baslik": "BTCUSDT · 4H · Binance",
  "alt_baslik": "SMC + Fibonacci — ölçülen yapıdan çizildi",
  "tema": "koyu" | "acik",
  "genislik": 1600, "yukseklik": 900,
  "log_olcek": false, "sag_bosluk_bar": 30,
  "paneller": [{"tip":"hacim","yukseklik":0.14},{"tip":"rsi","period":14}],
  "cizimler": [ {"arac":"fib_retracement","p1":{"bar":-60,"fiyat":1.0}, ...} ],
  "otomatik": {"smc": true, "emir": {...}},         # otomatik_cizim.py katmanı
  "cikti": "grafik.svg"
}

Çıktı: SVG dosyası + stdout'a JSON özeti (çizilen araçlar, seviyeler, uyarılar).

DOĞRULUK: bu motor fiyat UYDURMAZ. Elle verilen çizimler kullanıcının/üst
motorun sayılarıdır; "otomatik" katmanı seviyeleri smc_tespit.py'nin ÖLÇTÜĞÜ
yapıdan alır. Okunamayan/eksik alan "VERİ YOK" olarak raporlanır.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

BURASI = Path(__file__).resolve().parent
if str(BURASI) not in sys.path:
    sys.path.insert(0, str(BURASI))
import araclar as A
from tuval import Tuval
import veri_sozlesmesi as V
import plan_sozlesmesi as P

KOK = BURASI.parents[3]
CizimError = V.VeriError


def mumlari_getir(job: dict, taban: Path) -> tuple[list, str]:
    """Return all eligible history; son_bar is a viewport, never a calculation filter."""
    candles, source, _ = V.load(job, taban, KOK)
    return candles, source


def _normalize(spec: dict) -> dict:
    s = copy.deepcopy(spec)
    ham = str(s.get('arac', '')).strip().lower()
    if ham in ('ema', 'sma'):
        s.setdefault('tip', ham)
    s['arac'] = A.coz(ham)
    s.pop('_position', None)
    # Timestamp points follow the same epoch normalization as source candles.
    for point in [s.get(k) for k in ('p1','p2','p3')] + list(s.get('noktalar') or []):
        if isinstance(point, dict) and point.get('zaman') is not None:
            point['zaman'] = V.timestamp_ms(point['zaman'])
    return s


def _remap_history(spec, offset, total):
    """Internal explicit index refs keep off-left anchors distinct from -1=last."""
    s = copy.deepcopy(spec)
    def ref(value):
        if isinstance(value, dict):
            return value
        number = float(value)
        if number < 0:
            number += total
        return {'index': number-offset}
    if s['arac'] == 'regresyon_kanali':
        a = s.get('bar_baslangic', 0); b = s.get('bar_bitis', total-1)
        a = total + int(a) if float(a) < 0 else int(a)
        b = total + int(b) if float(b) < 0 else int(b)
        s['_history_range'] = [a,b]
    for key in ('bar_baslangic','bar_bitis','bar'):
        if s.get(key) is not None:
            s[key] = ref(s[key])
    for point in [s.get(k) for k in ('p1','p2','p3')] + list(s.get('noktalar') or []):
        if isinstance(point, dict) and point.get('bar') is not None:
            point['bar'] = ref(point['bar'])
    return s


def _inkscape_png(svg_path, png_path, width):
    executable=shutil.which('inkscape')
    if executable is None:
        raise RuntimeError('PNG için cairosvg veya Inkscape gerekli')
    try:
        result=subprocess.run([executable,str(svg_path),'--export-type=png',
                               f'--export-filename={png_path}',f'--export-width={width}'],
                              capture_output=True,text=True,timeout=30,check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Inkscape PNG dönüşümü 30 saniyede tamamlanmadı') from exc
    if result.returncode!=0:
        detail=' '.join((result.stderr or '').split())[:240]
        raise RuntimeError(f'Inkscape PNG çıkış {result.returncode}: {detail}')
    if not png_path.exists() or png_path.stat().st_size<=8:
        raise RuntimeError('Inkscape başarılı PNG dosyası üretmedi')


def _export_png(svg,svg_path,width):
    # A fallback dependency must not hide invalid XML/SVG input.
    root=ET.fromstring(svg)
    if root.tag.rsplit('}',1)[-1]!='svg':
        raise ValueError('PNG kaynağı SVG değil')
    destination=svg_path.with_suffix('.png')
    with tempfile.TemporaryDirectory(prefix='chart-png-',dir=str(svg_path.parent)) as temp:
        pending=Path(temp)/'render.png'
        try:
            import cairosvg
        except ImportError:
            _inkscape_png(svg_path,pending,width)
            engine='inkscape'
        else:
            cairosvg.svg2png(bytestring=svg.encode(),write_to=str(pending),output_width=width)
            engine='cairosvg'
        if not pending.exists() or pending.read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n':
            raise RuntimeError('PNG çıktısı bulunamadı veya dosya imzası geçersiz')
        pending.replace(destination)
    return destination,engine


def uygula(job: dict, taban: Path) -> dict:
    history, kaynak, manifest = V.load(job, taban, KOK)
    count = int(job.get('son_bar', 0) or 0)
    if count < 0:
        raise CizimError('son_bar negatif olamaz')
    offset = max(0, len(history)-count) if count else 0
    mumlar = history[offset:]
    contract = manifest['time_contract']
    uyari = list(contract.get('warnings', []))
    if str(job.get('timezone', 'UTC')).upper() != 'UTC':
        raise CizimError('bu motor UTC çizer; farklı timezone etiketi kabul edilmez')
    if not job.get('price_unit'):
        uyari.append('fiyat birimi belirtilmedi; birim etiketi belirsiz')
    context = dict(manifest, final_decision=job.get('final_decision'),case_sha256=job.get('case_sha256'))
    cizimler = []
    for raw in job.get('cizimler') or []:
        spec = _normalize(raw)
        if spec.get('bar_space') == 'history':
            spec = _remap_history(spec, offset, len(history))
        else:
            spec.pop('_history_range', None)
        cizimler.append(spec)
    oto = job.get('otomatik')
    oto_rapor = None
    if oto:
        import otomatik_cizim as OC
        cfg = dict(oto) if isinstance(oto, dict) else {}
        cfg['_context'] = context
        for key in ('c0','cutoff','as_of','timeframe','interval_seconds'):
            if key in job:
                cfg[key] = job[key]
        oto_cizim, oto_rapor = OC.uret(history, cfg, taban=taban)
        cizimler = [_remap_history(_normalize(c), offset, len(history)) for c in oto_cizim] + cizimler
        uyari += oto_rapor.get('uyarilar', [])
    panels = copy.deepcopy(job.get('paneller') or [])
    for panel in panels:
        if isinstance(panel.get('deger'), list) and len(panel['deger']) == len(history):
            panel['deger'] = panel['deger'][offset:]
    status_label = 'C0 kapanmış mumlar' if contract.get('status') == 'verified' and contract.get('cutoff_ms') is not None else 'TASLAK · time_unverified'
    subtitle = ' · '.join(filter(None, (str(job.get('alt_baslik','')), status_label)))
    t = Tuval(mumlar, history=history, display_start=offset,
              genislik=int(job.get('genislik',1600)), yukseklik=int(job.get('yukseklik',900)),
              tema=str(job.get('tema','koyu')), log_olcek=bool(job.get('log_olcek',False)),
              sag_bosluk_bar=int(job.get('sag_bosluk_bar',25)), baslik=str(job.get('baslik','')),
              alt_baslik=subtitle, paneller=panels, dipnot=str(job.get('dipnot','')),
              price_unit=str(job.get('price_unit','birim belirtilmedi')),
              volume_unit=str(job.get('volume_unit','')), timezone='UTC')
    requested, skipped, valid = len(cizimler), [], []
    for index, spec in enumerate(cizimler):
        try:
            if spec['arac'] in ('long_pozisyon','short_pozisyon'):
                spec, messages = P.prepare(spec, context)
                uyari += messages
            int(spec.get('katman',A.katman(spec['arac'])))
            prices, _ = A.arac(spec['arac'])
            t.rezerve(prices(t,spec))
            valid.append((index,spec))
        except (ValueError,TypeError,KeyError,IndexError) as exc:
            reason = f"{spec.get('arac')}: atlandı — {exc}"
            uyari.append(reason); skipped.append({'index':index,'arac':spec.get('arac'),'reason':str(exc)})
    t.hazirla()
    arka, on, drawn, levels, positions = [], [], [], [], []
    for index, spec in sorted(valid,key=lambda item:int(item[1].get('katman',A.katman(item[1]['arac'])))):
        try:
            price_fn, draw_fn = A.arac(spec['arac'])
            fragment = draw_fn(t,spec)
            if not fragment:
                raise ValueError('görünür çizim üretilemedi (yetersiz veri/boş geometri)')
            (arka if int(spec.get('katman',A.katman(spec['arac']))) < 0 else on).append(fragment)
            drawn.append(spec['arac'])
            levels.extend(float(v) for v in price_fn(t,spec))
            if spec.get('_position'):
                positions.append(dict(spec['_position'],entry=spec['giris'],stop=spec['stop'],target=spec['hedef']))
        except (ValueError,TypeError,KeyError,IndexError) as exc:
            uyari.append(f"{spec['arac']}: çizilemedi — {exc}")
            skipped.append({'index':index,'arac':spec['arac'],'reason':str(exc)})
    svg = t.render(''.join(on),arka_svg=''.join(arka))
    uyari += t.uyarilar  # render() may add panel/layout warnings.
    output = Path(job.get('cikti') or 'grafik.svg')
    if not output.is_absolute():
        output = taban/output
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(svg,encoding='utf-8')
    manifest.update(display_start=offset, display_rows=len(mumlar), history_rows=len(history),
                    first_time_ms=mumlar[0].get('time'), last_close_time_ms=mumlar[-1].get('close_time_ms'),
                    price_unit=job.get('price_unit'), volume_unit=job.get('volume_unit'),
                    y_scale='log' if t.log else 'linear', x_scale='equally_spaced_bars',
                    formula_conventions={'ema':'SMA seed then alpha=2/(n+1); full eligible history',
                                         'rsi':'Wilder mean-of-first-n-changes seed; flat=50',
                                         'regression':'OLS price against bar index; residual std ddof=2'},
                    output_sha256=hashlib.sha256(svg.encode()).hexdigest(),
                    position_evidence=positions)
    report = {'cikti':str(output),'bicim':'svg','veri_kaynagi':kaynak,'bar_sayisi':len(mumlar),
              'son_fiyat':mumlar[-1]['close'],'fiyat_araligi':{'alt':t.lo,'ust':t.hi},
              'istenen_cizim_sayisi':requested,'cizim_sayisi':len(drawn),'atlanan_cizimler':skipped,
              'araclar':sorted(set(drawn)),'cizilen_seviyeler':sorted(set(levels)),
              'uyarilar':list(dict.fromkeys(uyari)),'manifest':manifest,
              'decision_verified':bool(positions) and all(p['decision_verified'] for p in positions),
              'not':'Grafik karar desteğidir. Koşul teyidi, tahmin doğruluğu veya başarı olasılığı değildir.'}
    if oto_rapor:
        report['otomatik'] = {k:v for k,v in oto_rapor.items() if k != 'uyarilar'}
    if job.get('png'):
        try:
            png,engine=_export_png(svg,output,t.W*2)
            report['png']=str(png)
            report['png_renderer']=engine
        except (ImportError,ValueError,OSError,RuntimeError,ET.ParseError) as exc:
            report['uyarilar'].append(f'PNG üretilemedi: {exc}')
    manifest_path = Path(str(output)+'.manifest.json')
    report['manifest_path']=str(manifest_path)
    manifest_path.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    return report


def main() -> int:
    ap=argparse.ArgumentParser(description='Denetlenebilir SVG mum grafiği')
    ap.add_argument('--job');ap.add_argument('--araclar',action='store_true')
    args=ap.parse_args()
    if args.araclar:
        print(json.dumps({'araclar':sorted(A.ARACLAR),'takma_adlar':A.TAKMA_AD},ensure_ascii=False,indent=2))
        return 0
    if not args.job:
        ap.error('--job gerekli')
    path=Path(args.job).expanduser().resolve()
    try:
        report=uygula(json.loads(path.read_text(encoding='utf-8')),path.parent)
    except (ValueError,TypeError,KeyError,OSError) as exc:
        print(json.dumps({'hata':str(exc)},ensure_ascii=False))
        return 2
    print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
