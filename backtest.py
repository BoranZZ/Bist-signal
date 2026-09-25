"""
Backtest — kuralların geçmişte gerçekten işe yarayıp yaramadığını ölçer.

Gerçekçi olması için:
- Sinyal günün kapanışında oluşur, işleme ERTESİ gün açılışında girilir
  (look-ahead / geleceği görme yanılgısını önler).
- Her işlemde çift yönlü KOMİSYON+kayma düşülür (aşırı işlemin maliyetini görürsün).
- Stop boşlukla (gap) aşılırsa çıkış stop fiyatından değil o günün açılışından yazılır.
- Her işlem, aynı günlerde BIST 100 endeksini tutmakla kıyaslanır ("endekse göre fark").

İki kural seti yan yana ölçülür:
- mevcut: AL olan her gün (boştaysan) gir; stop / SAT / MAX_GUN gün sonra çık.
- aday:   sadece AL'e DÖNÜŞ günü ve endeks 50 günlük ortalamasının üstündeyken gir;
          stop ya da 2 gün üst üste SAT gelince çık (süre sınırı yok, canlı sistem gibi).
          Giriş günü hacmi 20 günlük ortalamanın HACIM_ESIK katını aşan işlemler ayrıca raporlanır.
Sonuçlar düşük faiz (2023 Haziran öncesi) ve yüksek faiz dönemine ayrılır.
"""
import numpy as np
import pandas as pd

from sinyal import gostergeler, sma

KOMISYON = 0.002        # tek yön %0.2 (komisyon + kayma varsayımı)
MAX_GUN = 40            # mevcut kural: bir pozisyonu en fazla bu kadar gün tut
ADAY_MAX_GUN = 250      # aday kural: fiilen süre sınırı yok
HACIM_ESIK = 1.5        # hacim teyidi: giriş günü hacmi / 20 günlük ortalama
FAIZ_DONUM = pd.Timestamp("2023-06-01")   # TCMB'nin sert faiz artırımına başladığı ay
DONEMLER = [("Düşük faiz", None, FAIZ_DONUM), ("Yüksek faiz", FAIZ_DONUM, None)]


def piyasa_ust(xu):
    """Endeks 50 günlük ortalamasının üstünde mi (piyasa filtresi)."""
    return xu > sma(xu, 50)


def tek_hisse_backtest(df, kod="", kural="mevcut", xu_ust=None):
    """Bir hisse için işlemleri simüle eder, işlem listesi + özet döner."""
    d = gostergeler(df).dropna(subset=["SMA50", "RSI", "MACD_SIGNAL"])
    if len(d) < 60:
        return [], None
    o = (d["Open"] if "Open" in d else d["Close"]).values
    low = (d["Low"] if "Low" in d else d["Close"]).values
    close = d["Close"].values
    sinyal = d["SINYAL"].values
    stop_ser = d["STOP"].values
    idx = d.index
    n = len(d)
    aday = kural == "aday"
    if aday:
        ust = (xu_ust.reindex(idx, method="ffill").fillna(False).values if xu_ust is not None
               else np.ones(n, dtype=bool))
        vol = d["Volume"].values if "Volume" in d else np.full(n, np.nan)
        vol_ort = pd.Series(vol).rolling(20).mean().values
    max_gun = ADAY_MAX_GUN if aday else MAX_GUN

    islemler = []
    i = 0
    while i < n - 1:
        if aday:
            gir = sinyal[i] == "AL" and (i == 0 or sinyal[i - 1] != "AL") and bool(ust[i])
        else:
            gir = sinyal[i] == "AL"
        if not gir:
            i += 1
            continue
        giris = float(o[i + 1])                              # ertesi gün açılış
        giris_stop = float(stop_ser[i])
        giris_tarih = idx[i + 1]
        cikis, sat_say = None, 0
        for j in range(i + 1, min(i + 1 + max_gun, n)):
            if float(low[j]) <= giris_stop:                  # stop yendi (boşlukla açıldıysa açılıştan)
                cikis, sebep, ct = min(giris_stop, float(o[j])), "stop", idx[j]
                break
            if sinyal[j] == "SAT":                           # sinyal bozuldu
                sat_say += 1
                if not aday or sat_say >= 2:
                    cikis, sebep, ct = float(close[j]), "sinyal", idx[j]
                    break
            else:
                sat_say = 0
        if cikis is None:                                    # süre doldu / veri bitti
            j = min(i + max_gun, n - 1)
            cikis, sebep, ct = float(close[j]), "süre", idx[j]

        net = (1 - KOMISYON) * (cikis / giris) * (1 - KOMISYON) - 1
        islemler.append({
            "kod": kod, "giris_t": giris_tarih, "cikis_t": ct,
            "gun": (ct - giris_tarih).days, "giris": giris, "cikis": cikis,
            "brut": cikis / giris - 1, "net": net, "sebep": sebep,
            "hacim": bool(aday and vol_ort[i] > 0 and vol[i] > HACIM_ESIK * vol_ort[i]),
        })
        i = j + 1                                            # çıkıştan sonra devam

    # Al ve tut kıyası (dönemin başından sonuna)
    al_tut = float(close[-1]) / float(close[0]) - 1
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


def _endeks_getirisi(xu, g, c):
    if xu is None:
        return np.nan
    a, b = xu.asof(g), xu.asof(c)
    return b / a - 1 if (a and not np.isnan(a)) else np.nan


def istatistik(islemler, xu=None):
    """İşlem listesi için özet: isabet, ortalama, endekse göre fark, uç işlemlere bağımlılık."""
    if not islemler:
        return None
    netler = np.array([t["net"] for t in islemler])
    fazla = np.array([t["net"] - _endeks_getirisi(xu, t["giris_t"], t["cikis_t"]) for t in islemler])
    fazla = fazla[~np.isnan(fazla)]
    s = np.sort(fazla)
    return {
        "islem": len(islemler),
        "isabet": round(float((netler > 0).mean()) * 100, 1),
        "ort_islem": round(float(netler.mean()) * 100, 2),
        "ort_kazanan": round(float(netler[netler > 0].mean()) * 100, 2) if (netler > 0).any() else 0,
        "ort_kaybeden": round(float(netler[netler <= 0].mean()) * 100, 2) if (netler <= 0).any() else 0,
        "fazla": round(float(fazla.mean()) * 100, 2) if len(fazla) else None,
        "fazla_top10_haric": round(float(s[:-10].mean()) * 100, 2) if len(s) > 20 else None,
        "ort_gun": round(float(np.mean([t["gun"] for t in islemler])), 1),
    }


def toplu_backtest(veri_sozlugu, kural="mevcut", xu=None):
    """veri_sozlugu: {kod: OHLC DataFrame}. Evren için hisse özetleri + genel istatistik + işlemler."""
    xu_ust = piyasa_ust(xu) if xu is not None else None
    ozetler, tum = [], []
    for kod, df in veri_sozlugu.items():
        islemler, ozet = tek_hisse_backtest(df, kod, kural, xu_ust)
        if ozet:
            ozetler.append(ozet)
        tum.extend(islemler)
    genel = istatistik(tum, xu)
    if genel:
        genel["medyan_altut"] = round(float(np.median([o["al_tut"] for o in ozetler])), 1)
    return ozetler, genel, tum


def donem_tablosu(islem_setleri, xu=None):
    """{etiket: işlemler} -> dönemlere göre satırlar."""
    satir = []
    for ad, bas, son in DONEMLER:
        for et, isl in islem_setleri.items():
            sec = [t for t in isl if (bas is None or t["giris_t"] >= bas) and (son is None or t["giris_t"] < son)]
            st = istatistik(sec, xu)
            if st:
                satir.append({"donem": ad, "kural": et, **st})
    return satir


def _yuzde(x, isaret=True):
    if x is None:
        return "—"
    return f"{'+' if (isaret and x >= 0) else ''}{x}%".replace("-", "−")


def rapor_html(ozetler, genel, donem="", genel_aday=None, donem_satirlari=None):
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

    def kartlar(g, baslik):
        g = g or {}
        fz = g.get("fazla")
        return f"""<h2>{baslik}</h2><div class="kartlar">
<div class="k"><div class="b">{g.get('islem','—')}</div><div class="l">toplam işlem</div></div>
<div class="k"><div class="b">%{g.get('isabet','—')}</div><div class="l">isabet oranı (kazanan işlem)</div></div>
<div class="k"><div class="b {'pos' if (g.get('ort_islem') or 0)>=0 else 'neg'}">%{g.get('ort_islem','—')}</div><div class="l">işlem başı ortalama (net)</div></div>
<div class="k"><div class="b {'pos' if (fz or 0)>=0 else 'neg'}">{_yuzde(fz)}</div><div class="l">endekse göre fark (işlem başı)</div></div>
<div class="k"><div class="b">%{g.get('ort_kazanan','—')}</div><div class="l">kazananların ortalaması</div></div>
<div class="k"><div class="b neg">%{g.get('ort_kaybeden','—')}</div><div class="l">kaybedenlerin ortalaması</div></div>
</div>"""

    dtablo = ""
    if donem_satirlari:
        r = "".join(
            f"<tr><td>{s['donem']}</td><td>{s['kural']}</td><td class='num'>{s['islem']}</td>"
            f"<td class='num'>%{s['isabet']}</td><td class='num'>%{s['ort_islem']}</td>"
            f"<td class='num {'pos' if (s['fazla'] or 0)>=0 else 'neg'}'>{_yuzde(s['fazla'])}</td>"
            f"<td class='num {'pos' if (s['fazla_top10_haric'] or 0)>=0 else 'neg'}'>{_yuzde(s['fazla_top10_haric'])}</td>"
            f"<td class='num'>{s['ort_gun']}g</td></tr>" for s in donem_satirlari)
        dtablo = f"""<h2>Faiz dönemlerine göre</h2>
<div class="sar"><table><thead><tr><th>Dönem</th><th>Kural</th><th>İşlem</th><th>İsabet</th><th>İşlem başı</th>
<th>Endekse göre fark</th><th>En iyi 10 işlem hariç</th><th>Ort süre</th></tr></thead><tbody>{r}</tbody></table></div>
<div class="not">"En iyi 10 işlem hariç": sonuç birkaç uç işleme mi bağlı? Bu sütun da pozitifse kural daha sağlam demektir.
Düşük faiz dönemi 2023 Haziran öncesi; faiz indirimi beklentisi varsa o dönem daha yol göstericidir.</div>"""

    g = genel or {}
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Backtest Raporu</title>
<style>
:root{{--bg:#FAFAF8;--ink:#16181D;--muted:#6B7079;--line:#E6E7E4;--accent:#0E4D45;--pos:#1B7F4B;--neg:#B4362E;--panel:#fff}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;font-feature-settings:"tnum" 1}}
.wrap{{max-width:1080px;margin:0 auto;padding:28px 20px 60px}}
h1{{font-size:20px;margin:0;font-weight:650}}h2{{font-size:15px;margin:26px 0 0}}.tarih{{color:var(--muted);font-size:13px;margin-top:4px}}
.kartlar{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:12px 0 8px}}
.k{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
.k .b{{font-size:28px;font-weight:680;letter-spacing:-.02em}}.k .l{{color:var(--muted);font-size:12.5px;margin-top:3px}}
.pos{{color:var(--pos)}}.neg{{color:var(--neg)}}
table{{width:100%;border-collapse:collapse;font-size:13.5px;min-width:720px}}
.sar{{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--panel);margin-top:12px}}
th,td{{padding:10px 12px;text-align:right;white-space:nowrap}}th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){{text-align:left}}
th{{color:var(--muted);font-weight:600;font-size:12px;border-bottom:1px solid var(--line)}}
tbody tr{{border-bottom:1px solid var(--line)}}tbody tr:last-child{{border-bottom:none}}
.kod{{font-weight:650}}.num{{font-variant-numeric:tabular-nums}}
.not{{margin-top:14px;padding:14px 16px;border:1px solid var(--line);border-radius:10px;background:#fff;color:var(--muted);font-size:12.5px;line-height:1.65}}
</style></head><body><div class="wrap">
<h1>Backtest Raporu — şu anki kurallar vs aday</h1><div class="tarih">Dönem: {donem} · komisyon+kayma çift yön %{KOMISYON*100:g}</div>
{kartlar(genel, "Şu anki kurallar (AL'de gir; stop, SAT ya da " + str(MAX_GUN) + " gün sonra çık)")}
{kartlar(genel_aday, "Aday (AL'e dönüş + piyasa filtresi; stop ya da 2 gün SAT'ta çık)") if genel_aday else ""}
{dtablo}
<h2>Hisse bazında (şu anki kurallar)</h2>
<div class="sar"><table><thead><tr>
<th>Hisse</th><th>İşlem</th><th>İsabet</th><th>İşlem başı</th><th>Strateji %</th><th>Al-tut %</th><th>Fark</th><th>Maks düşüş</th><th>Ort süre</th>
</tr></thead><tbody>{''.join(satir)}</tbody></table></div>
<div class="not"><b>Nasıl okunur?</b> "Endekse göre fark": her işlemi, aynı günlerde BIST 100'ü tutmakla kıyaslar — enflasyonlu piyasada ham getiriden daha dürüst ölçüdür. Tek bir yüksek sayıya değil, <b>isabet + işlem başı ortalama + en iyi 10 işlem hariç sonuca birlikte</b> bak. Testte bugünün hisse listesi kullanıldığı için sonuçlar biraz iyimserdir; sonradan çöken şişirilmiş hisselerin (ör. TERA) uç kazançları ortalamayı yanıltabilir. Bu bir simülasyondur; gerçek sonuç kayma, likidite ve vergiyle değişir. Yatırım tavsiyesi değildir.</div>
</div></body></html>"""


def _gercek_veri(kodlar, period="5y"):
    import yfinance as yf
    tickers = [k + ".IS" for k in kodlar] + ["XU100.IS"]
    print(f"Backtest için {len(tickers)} seri indiriliyor ({period})...")
    data = yf.download(tickers, period=period, interval="1d", group_by="ticker",
                       auto_adjust=True, progress=False, threads=True)
    veri = {}
    for k in kodlar:
        try:
            df = data[k + ".IS"].dropna(subset=["Close"])
            if len(df) > 120:
                veri[k] = df
        except Exception:
            pass
    try:
        xu = data["XU100.IS"]["Close"].dropna()
    except Exception:
        xu = None
    return veri, xu


def _sentetik_veri(n_hisse=12):
    veri = {}
    for i in range(n_hisse):
        r = np.random.default_rng(i + 1)
        n = 500
        c = np.abs(np.linspace(r.uniform(20, 60), r.uniform(25, 130), n) + np.cumsum(r.normal(0, 0.9, n))) + 5
        veri[f"HISSE{i+1}"] = pd.DataFrame({
            "Open": c * (1 + r.normal(0, 0.003, n)), "High": c * 1.02,
            "Low": c * 0.98, "Close": c, "Volume": r.uniform(0.5e6, 2e6, n),
        }, index=pd.bdate_range("2022-01-03", periods=n))
    xu = pd.concat([df["Close"] / df["Close"].iloc[0] for df in veri.values()], axis=1).mean(axis=1) * 1000
    return veri, xu


if __name__ == "__main__":
    import os
    if os.environ.get("BT_TEST"):
        veri, xu = _sentetik_veri()
        donem = "örnek/sentetik"
    else:
        from tarama import KODLAR
        veri, xu = _gercek_veri(KODLAR)
        donem = "son 5 yıl (gerçek veri)"
    ozetler, genel, isl_m = toplu_backtest(veri, "mevcut", xu)
    _, genel_a, isl_a = toplu_backtest(veri, "aday", xu)
    setler = {"şu anki": isl_m, "aday": isl_a, "aday + hacim teyitli": [t for t in isl_a if t["hacim"]]}
    with open("backtest.html", "w", encoding="utf-8") as f:
        f.write(rapor_html(ozetler, genel, donem, genel_a, donem_tablosu(setler, xu)))
    print("backtest.html yazıldı.\n  şu anki:", genel, "\n  aday:   ", genel_a)
