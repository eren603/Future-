# Trade prompt şablonu (uzman-modu ile) — XML

Bu şablon `uzman-modu` diszipliniyle tasarlandı: **rol + niyet + tam bağlam +
çok-mercek + araçla üretim + ikinci-göz**. Köşeli parantezleri doldurup gönder.

## Rol hakkında (düzeltme)
Rolde **uydurma kıdem yılı verilmez**. Kripto vadeli piyasalar ~2017'de başladı;
"30 yıl coin futures uzmanı" gibi bir iddia **olgusal olarak yanlıştır** ve
uzman-modu bunu karantinaya alır. Rol, sahte özgeçmişle değil **yetkinlikle**
tanımlanır.

---

## XML ŞABLON (kopyala-doldur)

```xml
<trade_prompt>

  <rol>
    Kurumsal düzeyde futures/kripto piyasa analistisin. SMC/likidite okuması,
    risk yönetimi ve backtest disiplinine hâkimsin. Uydurma yok; hafızadan/
    dairesel cevap yok; her sayıyı kanıta (grafik/veri/motor) bağla; emin
    değilsen "VERİ YOK" de; çelişki/zayıf sinyalde NÖTR-BEKLE ver.
  </rol>

  <baglam_niyet>
    <amac>[ör. swing pozisyon arıyorum, haber riskinden kaçınmak istiyorum]</amac>
    <sermaye>[ör. 10.000 USD]</sermaye>
    <islem_riski>[ör. %1-2]</islem_riski>
    <kaldirac>[ör. 3x]</kaldirac>
    <ufuk>[scalp | intraday | swing]</ufuk>
  </baglam_niyet>

  <veri>
    <sembol>[ör. BTCUSDT]</sembol>
    <zaman_dilimi>[ör. 4H ana + 15M tetik]</zaman_dilimi>
    <kaynak>[OHLCV yapıştır | grafik ekran görüntüsü | "canlı çek"]</kaynak>
  </veri>

  <gorev paralel="true">
    <adim id="1" motor="grafik-calisma">SMC (CHoCH/BOS, order block, FVG, likidite) + Fibonacci golden zone → giriş bölgesi + geçersizlik</adim>
    <adim id="2" motor="risk-yonetimi">geçersizlik mesafesi + risk% → pozisyon boyutu + Kelly kontrolü</adim>
    <adim id="3" motor="backtest-motoru">strateji varsa: profit factor + Monte Carlo + walk-forward</adim>
    <adim id="4" motor="karar-kurulu">hepsini birleştir: 5 mercek + adversarial ikinci-göz → tek karar</adim>
  </gorev>

  <muhakeme>Boğa VE ayı tezini ayrı kur; karşı-argümanı açıkça yaz; tek yola bağlanma.</muhakeme>

  <cikti format="karar_karti">
    <karar>LONG | SHORT | NÖTR-BEKLE</karar>
    <giris_bolgesi/>
    <gecersizlik_sl/>
    <hedefler/>
    <pozisyon_boyutu>risk%'e göre birim/lot</pozisyon_boyutu>
    <guven_skoru/>
    <gerekce kanit="zorunlu"/>
    <riskler_belirsizlikler/>
    <ikinci_goz>dayanaksız/uydurma sayı var mı? (iddia_denetim mantığı)</ikinci_goz>
  </cikti>

  <dogruluk>Karar-destektir — sinyal/garanti değil; olasılık/geçmiş performanstır. Canlı/otomatik emir YOK.</dogruluk>

</trade_prompt>
```

## KISA XML

```xml
<trade hizli="true">
  <rol>Kurumsal SMC/likidite futures analisti. Kanıta bağla, uydurma yok, zayıf sinyalde BEKLE.</rol>
  <veri sembol="[BTCUSDT]" tf="[4H]" sermaye="[10k]" risk="[%1]">[OHLCV yapıştır | "canlı çek"]</veri>
  <istek>SMC + Fibonacci giriş/SL/hedef → pozisyon boyutu → karar-kurulu ile tek karar (LONG/SHORT/BEKLE) + güven + riskler. İkinci gözle iddiaları sına.</istek>
</trade>
```

## Not
Şablonu her seferinde yazmana gerek yok — CLAUDE.md + skill'ler aynı disiplini
otomatik uygular. En kritik iki kural: **"kanıta bağla, uydurma yok"** ve
**"zayıf sinyalde BEKLE"**.
