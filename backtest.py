"""
Backtest — kuralların geçmişte gerçekten işe yarayıp yaramadığını ölçer.

Gerçekçi olması için:
- Sinyal günün kapanışında oluşur, işleme ERTESİ gün açılışında girilir
  (look-ahead / geleceği görme yanılgısını önler).
- Her işlemde çift yönlü KOMİSYON+kayma düşülür (aşırı işlemin maliyetini görürsün).
- Çıkış: stop tetiklenirse, sinyal SAT'a dönerse ya da en fazla MAX_GUN sonra.
- Strateji getirisi "al ve tut" ile kıyaslanır.
"""
import numpy as np
import pandas as pd

from sinyal import gostergeler

KOMISYON = 0.002   # tek yön %0.2 (komisyon + kayma varsayımı)
MAX_GUN = 40       # bir pozisyonu en fazla bu kadar gün tut


def tek_hisse_backtest(df, kod=""):
    """Bir hisse için işlemleri simüle eder, işlem listesi + özet döner."""
    d = gostergeler(df).dropna(subset=["SMA50", "RSI", "MACD_SIGNAL"])
    if len(d) < 60:
        return [], None
    o = d["Open"] if "Open" in d else d["Close"]
    low = d["Low"] if "Low" in d else d["Close"]
    close = d["Close"]
    sinyal = d["SINYAL"].values
    stop_ser = d["STOP"].values
    idx = d.index

    islemler = []
    i = 0
    n = len(d)
    while i < n - 1:
        if sinyal[i] == "AL":
            giris = float(o.iloc[i + 1])                 # ertesi gün açılış
            giris_stop = float(stop_ser[i])
            giris_tarih = idx[i + 1]
            cikis = None
            for j in range(i + 1, min(i + 1 + MAX_GUN, n)):
                if float(low.iloc[j]) <= giris_stop:     # stop yendi
                    cikis, sebep, ct = giris_stop, "stop", idx[j]
                    break
                if sinyal[j] == "SAT":                    # sinyal bozuldu
                    cikis, sebep, ct = float(close.iloc[j]), "sinyal", idx[j]
                    break
            if cikis is None:                             # süre doldu
                j = min(i + MAX_GUN, n - 1)
                cikis, sebep, ct = float(close.iloc[j]), "süre", idx[j]

            brut = cikis / giris - 1
            net = (1 - KOMISYON) * (cikis / giris) * (1 - KOMISYON) - 1
            islemler.append({
                "kod": kod, "giris_t": giris_tarih, "cikis_t": ct,
                "gun": (ct - giris_tarih).days, "giris": giris, "cikis": cikis,
                "brut": brut, "net": net, "sebep": sebep,
            })
            i = j + 1                                     # çıkıştan sonra devam
        else:
            i += 1

    # Al ve tut kıyası (ilk sinyalden dönemin sonuna)
    al_tut = float(close.iloc[-1]) / float(close.iloc[0]) - 1

    if not islemler:
        return [], {"kod": kod, "islem": 0, "al_tut": round(al_tut * 100, 1)}

    netler = np.array([t["net"] for t in islemler])
    equity = np.cumprod(1 + netler)
    tepe = np.maximum.accumulate(equity)
    max_dusus = float(((equity - tepe) / tepe).min())

    ozet = {
        "kod": kod,
        "islem": len(islemler),
        "isabet": round(float((netler > 0).mean()) * 100, 1),
        "ort_islem": round(float(netler.mean()) * 100, 2),
        "toplam": round(float(equity[-1] - 1) * 100, 1),
        "al_tut": round(al_tut * 100, 1),
        "max_dusus": round(max_dusus * 100, 1),
        "ort_gun": round(float(np.mean([t["gun"] for t in islemler])), 1),
    }
    return islemler, ozet


def toplu_backtest(veri_sozlugu):
    """veri_sozlugu: {kod: OHLC DataFrame}. Tüm evren için özet + birleşik istatistik."""
    ozetler, tum_islemler = [], []
    for kod, df in veri_sozlugu.items():
        islemler, ozet = tek_hisse_backtest(df, kod)
        if ozet:
            ozetler.append(ozet)
        tum_islemler.extend(islemler)

    if not tum_islemler:
        return ozetler, None
    netler = np.array([t["net"] for t in tum_islemler])
    genel = {
        "islem": len(tum_islemler),
        "isabet": round(float((netler > 0).mean()) * 100, 1),
        "ort_islem": round(float(netler.mean()) * 100, 2),
        "ort_kazanan": round(float(netler[netler > 0].mean()) * 100, 2) if (netler > 0).any() else 0,
        "ort_kaybeden": round(float(netler[netler <= 0].mean()) * 100, 2) if (netler <= 0).any() else 0,
        "medyan_altut": round(float(np.median([o["al_tut"] for o in ozetler])), 1),
    }
    return ozetler, genel


def rapor_html(ozetler, genel, donem=""):
    ozetler = sorted(ozetler, key=lambda x: -(x.get("toplam") or -999))
    satir = []
    for o in ozetler:
        if o["islem"] == 0:
            continue
        fark = (o["toplam"] or 0) - (o["al_tut"] or 0)
        fcls = "pos" if fark >= 0 else "neg"
        satir.append(f"""<tr><td class="kod">{o['kod']}</td>
<td class="num">{o['islem']}</td><td class="num">%{o['isabet']}</td>
<td class="num">%{o['ort_islem']}</td>
<td class="num {'pos' if o['toplam']>=0 else 'neg'}">%{o['toplam']}</td>
<td class="num">%{o['al_tut']}</td>
<td class="num {fcls}">{'+' if fark>=0 else ''}{round(fark,1)}</td>
<td class="num neg">%{o['max_dusus']}</td><td class="num">{o['ort_gun']}g</td></tr>""")

    g = genel or {}
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Backtest Raporu</title>
<style>
:root{{--bg:#FAFAF8;--ink:#16181D;--muted:#6B7079;--line:#E6E7E4;--accent:#0E4D45;--pos:#1B7F4B;--neg:#B4362E;--panel:#fff}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;font-feature-settings:"tnum" 1}}
.wrap{{max-width:1080px;margin:0 auto;padding:28px 20px 60px}}
h1{{font-size:20px;margin:0;font-weight:650}}.tarih{{color:var(--muted);font-size:13px;margin-top:4px}}
.kartlar{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:24px 0}}
.k{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
.k .b{{font-size:30px;font-weight:680;letter-spacing:-.02em}}.k .l{{color:var(--muted);font-size:12.5px;margin-top:3px}}
.pos{{color:var(--pos)}}.neg{{color:var(--neg)}}
table{{width:100%;border-collapse:collapse;font-size:13.5px;min-width:720px}}
.sar{{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--panel)}}
th,td{{padding:10px 12px;text-align:right;white-space:nowrap}}th:first-child,td:first-child{{text-align:left}}
th{{color:var(--muted);font-weight:600;font-size:12px;border-bottom:1px solid var(--line)}}
tbody tr{{border-bottom:1px solid var(--line)}}tbody tr:last-child{{border-bottom:none}}
.kod{{font-weight:650}}.num{{font-variant-numeric:tabular-nums}}
.not{{margin-top:26px;padding:14px 16px;border:1px solid var(--line);border-radius:10px;background:#fff;color:var(--muted);font-size:12.5px;line-height:1.65}}
</style></head><body><div class="wrap">
<h1>Backtest Raporu — strateji vs al-tut</h1><div class="tarih">Dönem: {donem} · komisyon+kayma çift yön %{KOMISYON*100:g} · maks tutuş {MAX_GUN} gün</div>
<div class="kartlar">
<div class="k"><div class="b">{g.get('islem','—')}</div><div class="l">toplam işlem</div></div>
<div class="k"><div class="b">%{g.get('isabet','—')}</div><div class="l">isabet oranı (kazanan işlem)</div></div>
<div class="k"><div class="b {'pos' if (g.get('ort_islem',0) or 0)>=0 else 'neg'}">%{g.get('ort_islem','—')}</div><div class="l">işlem başı ortalama (net)</div></div>
<div class="k"><div class="b">%{g.get('ort_kazanan','—')}</div><div class="l">kazananların ortalaması</div></div>
<div class="k"><div class="b neg">%{g.get('ort_kaybeden','—')}</div><div class="l">kaybedenlerin ortalaması</div></div>
<div class="k"><div class="b">%{g.get('medyan_altut','—')}</div><div class="l">medyan al-tut (kıyas)</div></div>
</div>
<div class="sar"><table><thead><tr>
<th>Hisse</th><th>İşlem</th><th>İsabet</th><th>İşlem başı</th><th>Strateji %</th><th>Al-tut %</th><th>Fark</th><th>Maks düşüş</th><th>Ort süre</th>
</tr></thead><tbody>{''.join(satir)}</tbody></table></div>
<div class="not"><b>Nasıl okunur?</b> "Strateji %" bu kurallara uyup işlem yapsaydın dönem boyunca elde edeceğin bileşik getiri; "Al-tut %" hisseyi hiç satmadan tutsaydın. "Fark" pozitifse strateji o hissede işe yaramış. Tek bir yüksek sayıya değil, <b>isabet oranı + işlem başı ortalama + maksimum düşüşe birlikte</b> bak. Düşük isabetle bile ortalama pozitifse strateji kazananları büyütüp kaybedenleri erken kesiyor demektir. Bu bir simülasyondur; gerçek sonuç kayma, likidite ve vergiyle değişir. Yatırım tavsiyesi değildir.</div>
</div></body></html>"""


def _gercek_veri(kodlar, period="2y"):
    import yfinance as yf
    tickers = [k + ".IS" for k in kodlar]
    print(f"Backtest için {len(tickers)} hisse indiriliyor ({period})...")
    data = yf.download(tickers, period=period, interval="1d", group_by="ticker",
                       auto_adjust=True, progress=False, threads=True)
    veri = {}
    for k in kodlar:
        try:
            df = (data[k + ".IS"] if len(kodlar) > 1 else data).dropna(subset=["Close"])
            if len(df) > 120:
                veri[k] = df
        except Exception:
            pass
    return veri


def _sentetik_veri(n_hisse=12):
    veri = {}
    for i in range(n_hisse):
        r = np.random.default_rng(i + 1)
        n = 500
        c = np.abs(np.linspace(r.uniform(20, 60), r.uniform(25, 130), n) + np.cumsum(r.normal(0, 0.9, n))) + 5
        veri[f"HISSE{i+1}"] = pd.DataFrame({
            "Open": c * (1 + r.normal(0, 0.003, n)), "High": c * 1.02,
            "Low": c * 0.98, "Close": c, "Volume": 1e6,
        }, index=pd.bdate_range("2023-01-01", periods=n))
    return veri


if __name__ == "__main__":
    import os
    if os.environ.get("BT_TEST"):
        veri = _sentetik_veri()
        donem = "örnek/sentetik"
    else:
        from tarama import KODLAR
        veri = _gercek_veri(KODLAR)
        donem = "son 2 yıl (gerçek veri)"
    ozetler, genel = toplu_backtest(veri)
    with open("backtest.html", "w", encoding="utf-8") as f:
        f.write(rapor_html(ozetler, genel, donem))
    print("backtest.html yazıldı. Genel:", genel)
