# -*- coding: utf-8 -*-
"""Etkileşimli pano: satıra tıkla -> grafik + o hisseye özel yorum + TradingView."""
import json
import pandas as pd

RENK = {"AL": "al", "NÖTR": "notr", "SAT": "sat"}


def _simdi():
    """Türkiye saati (Actions sunucusu UTC'de çalışır)."""
    return pd.Timestamp.now(tz="Europe/Istanbul").strftime("%d.%m.%Y %H:%M")


def _med(xs):
    xs = sorted(x for x in xs if x)
    return xs[len(xs) // 2] if xs else None


def pano_uret(sonuclar, ornek=False, uyari=None, portfoy=None):
    tarih = _simdi()
    al = sum(1 for s in sonuclar if s["sinyal"] == "AL")
    guclu = sum(1 for s in sonuclar if s.get("guclu"))
    fk_med = _med(s.get("fk") for s in sonuclar)
    pddd_med = _med(s.get("pddd") for s in sonuclar)

    oncelik = {"AL": 0, "NÖTR": 1, "SAT": 2}
    sonuclar = sorted(sonuclar, key=lambda s: (oncelik[s["sinyal"]], not s.get("yeni"), not s.get("guclu"), -s["puan"]))

    rows = []
    veri = {}
    for s in sonuclar:
        k = s["kod"]
        deg = s.get("degisim")
        dcls = "pos" if (deg or 0) >= 0 else "neg"
        dtxt = f"{'+' if (deg or 0) >= 0 else ''}{deg}%" if deg is not None else "—"
        fkm = "ucuz" if (s.get("fk") and fk_med and s["fk"] < fk_med) else ("pahali" if s.get("fk") else "")
        pdm = "ucuz" if (s.get("pddd") and pddd_med and s["pddd"] < pddd_med) else ("pahali" if s.get("pddd") else "")
        ok = {"ucuz": "▼", "pahali": "▲", "": ""}
        yildiz = ' <span class="yildiz">★</span>' if s.get("guclu") else ""
        ycls = {"AL": "yal", "SAT": "ysat", "NÖTR": "ynotr"}[s["sinyal"]]
        yenirz = f' <span class="yeni {ycls}">YENİ</span>' if s.get("yeni") else ""
        sdrz = ""
        if s.get("destek_tepki"):
            sdrz += ' <span class="sdb destek" title="Fiyat geçmiş bir desteğe indi ve yukarı dönmeye başladı">Destekten tepki</span>'
        if s.get("direnc_yakin"):
            sdrz += ' <span class="sdb direnc" title="Fiyat geçmişte satış gelen bir tepe seviyesine yakın">Dirence yaklaşıyor</span>'
        lot = s.get("lot")
        lott = f"{lot}" if (lot and s["sinyal"] == "AL") else "—"
        sgun = s.get("sinyal_gun")
        sgunt = f"{sgun}g" if sgun else "—"
        rows.append(
            f'<tr onclick="ac(\'{k}\')">'
            f'<td class="kod">{k}</td>'
            f'<td class="num">{s.get("fiyat","—")}</td>'
            f'<td class="num {dcls}">{dtxt}</td>'
            f'<td><span class="pill {RENK[s["sinyal"]]}">{s["sinyal"]}</span>{yildiz}{yenirz}{sdrz}</td>'
            f'<td class="num sgun">{sgunt}</td>'
            f'<td class="num uyum">{s.get("uyum","—")}</td>'
            f'<td class="num">{s.get("rsi") if s.get("rsi") is not None else "—"}</td>'
            f'<td class="num">{s.get("fk") if s.get("fk") is not None else "—"}<span class="tag {fkm}">{ok[fkm]}</span></td>'
            f'<td class="num">{s.get("pddd") if s.get("pddd") is not None else "—"}<span class="tag {pdm}">{ok[pdm]}</span></td>'
            f'<td class="num stop">{s.get("stop","—")}</td>'
            f'<td class="num lot">{lott}</td></tr>'
        )
        veri[k] = {
            "kod": k, "fiyat": s.get("fiyat"), "degisim": deg, "sinyal": s["sinyal"],
            "guclu": bool(s.get("guclu")), "yeni": bool(s.get("yeni")), "sd": s.get("sd"),
            "destek_tepki": bool(s.get("destek_tepki")), "direnc_yakin": bool(s.get("direnc_yakin")),
            "rsi": s.get("rsi"), "fk": s.get("fk"), "pddd": s.get("pddd"), "favok": s.get("favok"),
            "stop": s.get("stop"), "giris_stop": s.get("giris_stop"), "lot": s.get("lot"),
            "hedef": s.get("hedef"), "sinyal_gun": s.get("sinyal_gun"),
            "sinyal_tarih": s.get("sinyal_tarih"), "sinyal_degisim": s.get("sinyal_degisim"),
            "uyum": s.get("uyum"), "detay": s.get("detay", []), "ek": s.get("ek", []),
            "gerekce": s.get("gerekce", []), "yorum": s.get("yorum", ""),
            "spark": s.get("spark", {}),
        }

    banner = ""
    if ornek:
        banner += '<div class="banner ornek">ÖRNEK VERİ — gerçek sürüm piyasa saatinde ~15 dk\'da bir güncellenir.</div>'
    if uyari:
        banner += f'<div class="banner uy">⚠️ {uyari}</div>'

    html = _SABLON
    for a, b in [("__TARIH__", tarih), ("__AL__", str(al)), ("__GUCLU__", str(guclu)),
                 ("__TOPLAM__", str(len(sonuclar))), ("__BANNER__", banner),
                 ("__ROWS__", "".join(rows)), ("__DATA__", json.dumps(veri, ensure_ascii=False))]:
        html = html.replace(a, b)
    return html


def gecmis_uret(acik, kapali, ozet):
    """Sinyal geçmişi sayfası: açık pozisyonlar + kapanmış sinyaller + karne."""
    def satirlar(kayitlar, acikmi):
        out = []
        for r in sorted(kayitlar, key=lambda x: x.get("giris_tarih", ""), reverse=True):
            if acikmi:
                s = r.get("anlik")
                scls = "pos" if (s or 0) >= 0 else "neg"
                stxt = f"{'+' if (s or 0) >= 0 else ''}{s}%" if s is not None else "—"
                out.append(f'<tr><td class="kod">{r["kod"]}</td><td>{r["giris_tarih"]}</td>'
                           f'<td class="num">{r["giris_fiyat"]}</td><td class="num">{r.get("guncel","—")}</td>'
                           f'<td class="num {scls}">{stxt}</td><td class="num stop">{r["stop"]}</td></tr>')
            else:
                s = r.get("sonuc")
                scls = "pos" if (s or 0) >= 0 else "neg"
                stxt = f"{'+' if (s or 0) >= 0 else ''}{s}%" if s is not None else "—"
                out.append(f'<tr><td class="kod">{r["kod"]}</td><td>{r["giris_tarih"]}</td>'
                           f'<td class="num">{r["giris_fiyat"]}</td><td>{r.get("cikis_tarih","—")}</td>'
                           f'<td class="num">{r.get("cikis_fiyat","—")}</td>'
                           f'<td class="num {scls}">{stxt}</td><td>{r.get("sebep","—")}</td></tr>')
        return "".join(out) or '<tr><td colspan="7" style="color:#6B7079">Kayıt yok.</td></tr>'

    html = _GECMIS
    reps = {
        "__ISABET__": str(ozet.get("isabet", "—")), "__KAPANAN__": str(ozet.get("kapanan", 0)),
        "__ORT__": str(ozet.get("ort", "—")), "__ACIK__": str(ozet.get("acik", 0)),
        "__ACIKROWS__": satirlar(acik, True), "__KAPALIROWS__": satirlar(kapali, False),
        "__TARIH__": _simdi(),
    }
    for a, b in reps.items():
        html = html.replace(a, b)
    return html


_SABLON = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>BIST Sinyal Panosu</title>
<style>
:root{--bg:#FAFAF8;--ink:#16181D;--muted:#6B7079;--line:#E6E7E4;--accent:#0E4D45;
--al:#1B7F4B;--notr:#9A7A12;--sat:#B4362E;--pos:#1B7F4B;--neg:#B4362E;--panel:#FFF}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
font-feature-settings:"tnum" 1;-webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;padding:26px 18px 60px}
header{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:14px;
border-bottom:1px solid var(--line);padding-bottom:18px}
h1{font-size:19px;margin:0;font-weight:650}.tarih{color:var(--muted);font-size:12.5px;margin-top:4px}
.ozet{display:flex;gap:22px;text-align:right}
.ozet .b{font-size:38px;font-weight:680;line-height:1;color:var(--accent);letter-spacing:-.02em}
.ozet .b.g{color:var(--al)}.ozet .l{color:var(--muted);font-size:12px;margin-top:3px}
.ipucu{margin-top:14px;color:var(--muted);font-size:12.5px}
.banner{margin:14px 0 0;padding:10px 14px;border-radius:8px;font-size:13px}
.banner.ornek{background:#FBF3E4;border:1px solid #EBD9B0;color:#7A5B10}
.banner.uy{background:#FBECEA;border:1px solid #E6C3BD;color:#8A2F26}
.sar{margin-top:18px;overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--panel)}
table{width:100%;border-collapse:collapse;font-size:13.5px;min-width:720px}
th,td{padding:11px 12px;text-align:left;white-space:nowrap}
th{position:sticky;top:0;background:var(--panel);color:var(--muted);font-weight:600;font-size:12px;
border-bottom:1px solid var(--line);cursor:pointer;user-select:none}th:hover{color:var(--ink)}
tbody tr{border-bottom:1px solid var(--line);cursor:pointer}tbody tr:last-child{border-bottom:none}
tbody tr:hover{background:#F2F5F3}
.kod{font-weight:650}.num{text-align:right;font-variant-numeric:tabular-nums}
.stop{color:var(--sat)}.lot{font-weight:650}.pos{color:var(--pos)}.neg{color:var(--neg)}
.pill{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:650}
.pill.al{background:#E4F2E9;color:var(--al)}.pill.notr{background:#F1EFE8;color:var(--notr)}.pill.sat{background:#F7E7E5;color:var(--sat)}
.yildiz{color:#C7962B}.tag{font-size:10px;margin-left:5px}.tag.ucuz{color:var(--al)}.tag.pahali{color:var(--sat)}
.yeni{color:#fff;font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:5px;margin-left:6px;letter-spacing:.03em}
.yeni.yal{background:#1B7F4B}.yeni.ysat{background:#B4362E}.yeni.ynotr{background:#9A7A12}
.sdb{color:#fff;font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:5px;margin-left:5px}
.sdb.destek{background:#3A6EA5}.sdb.direnc{background:#B7791F}
.sdkutu{margin:0 0 14px;border:1px solid var(--line);border-radius:10px;padding:11px 14px;font-size:13px;line-height:1.55}
.sdsat+.sdsat{margin-top:4px}.sdnot{margin-top:8px;padding:8px 10px;border-radius:8px;font-size:12.5px}
.sdnot.destek{background:#EAF1F8;color:#28507A}.sdnot.direnc{background:#FBF3E4;color:#7A5B10}
.sdyok{margin-top:6px;color:var(--muted);font-size:12.5px}.sdyontem{margin-top:8px;color:var(--muted);font-size:11.5px}
.tarih a{color:var(--accent);font-weight:600;text-decoration:none}.tarih a:hover{text-decoration:underline}
.sgun{color:var(--muted)}
.tvwrap{height:380px;margin:6px 0 14px;border:1px solid var(--line);border-radius:10px;overflow:hidden}
#tvbox{height:100%}
.tvyok{padding:16px;color:var(--muted);font-size:12.5px}
.pfsag{display:flex;align-items:center;gap:12px}
.pfekle{border:1px solid var(--accent);background:var(--accent);color:#fff;font-weight:600;font-size:12.5px;padding:6px 12px;border-radius:8px;cursor:pointer}
.pfform{display:none;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.pfform input{border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:13px;font-family:inherit}
.pfform #pfkod{width:150px}.pfform #pfadet,.pfform #pfmal{width:120px}
.pfkaydet{border:none;background:var(--al);color:#fff;font-weight:600;padding:8px 14px;border-radius:8px;cursor:pointer}
.pfipt{border:1px solid var(--line);background:#fff;color:var(--muted);padding:8px 12px;border-radius:8px;cursor:pointer}
.pfsil{border:none;background:#F1EFEA;color:var(--sat);width:26px;height:26px;border-radius:6px;cursor:pointer;font-size:12px}
.zaman{margin:12px 0 4px;background:#F3F7F5;border:1px solid #DCE8E2;border-radius:10px;padding:11px 14px;font-size:13px;line-height:1.55}
.zaman .cikis{margin-top:6px;color:var(--muted);font-size:12.5px}
.aciklama{margin-top:32px;display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}
.kart{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:15px 17px}
.kart h3{margin:0 0 6px;font-size:13.5px}.kart p{margin:0;color:var(--muted);font-size:12.8px;line-height:1.55}
.uyari{margin-top:28px;padding:13px 16px;border:1px solid var(--line);border-radius:10px;background:#fff;color:var(--muted);font-size:12.2px;line-height:1.6}
.glink{color:var(--accent);font-weight:600;text-decoration:none}.glink:hover{text-decoration:underline}
.pfbox{margin-top:18px}
.pfbas{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:8px}
.pfbas h2{margin:0;font-size:16px}.pftop{font-weight:650;font-size:14px}.pftop.pos{color:var(--pos)}.pftop.neg{color:var(--neg)}
table.pf{min-width:640px}
.pfy.bos{padding:12px 14px;border:1px dashed var(--line);border-radius:10px;color:var(--muted);font-size:12.8px;background:#fff}
.pfy.bos code{background:#F1F1EE;padding:2px 5px;border-radius:4px;font-size:12px}
.pfuy{color:var(--sat);font-size:11px;font-weight:600;margin-left:6px}
/* modal */
.ust{position:fixed;inset:0;background:rgba(20,22,26,.45);display:none;align-items:center;justify-content:center;padding:16px;z-index:9}
.ust.acik{display:flex}
.modal{background:#fff;border-radius:16px;max-width:640px;width:100%;max-height:92vh;overflow:auto;padding:22px}
.mh{display:flex;align-items:center;justify-content:space-between;gap:12px}
.mh .sol{display:flex;align-items:center;gap:10px}.mh h2{margin:0;font-size:20px}
.kapa{border:none;background:#F1F1EE;width:32px;height:32px;border-radius:8px;font-size:18px;cursor:pointer;color:var(--muted)}
.mfiyat{margin-top:6px;font-size:14px;color:var(--muted)}
.grafik{margin:16px 0;border:1px solid var(--line);border-radius:10px;padding:8px;background:#FCFCFB}
.metr{display:grid;grid-template-columns:repeat(auto-fit,minmax(95px,1fr));gap:10px;margin:6px 0 14px}
.metr .m{background:#F7F7F4;border-radius:9px;padding:9px 11px}.metr .m .l{color:var(--muted);font-size:11px}.metr .m .v{font-weight:650;font-size:15px;margin-top:2px}
.yorum{background:#F3F7F5;border:1px solid #DCE8E2;border-radius:10px;padding:13px 15px;font-size:13.5px;line-height:1.6}
.btnler{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
.btn{display:inline-block;padding:10px 14px;border-radius:9px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid var(--line);color:var(--ink);background:#fff}
.btn.p{background:var(--accent);color:#fff;border-color:var(--accent)}
.leg{display:flex;gap:14px;font-size:11px;color:var(--muted);margin-top:4px;padding-left:8px}
.leg span::before{content:"";display:inline-block;width:10px;height:2px;margin-right:5px;vertical-align:middle}
.leg .c1::before{background:#16181D}.leg .c2::before{background:#0E4D45}.leg .c3::before{background:#C7962B}.leg .c4::before{background:#B4362E}
.leg .c5::before{background:#3A6EA5}.leg .c6::before{background:#B7791F}
.leg{flex-wrap:wrap}
.uyum{font-weight:650;color:var(--accent)}
.uyroz{background:#EEF4F1;color:var(--accent);font-size:11.5px;font-weight:650;padding:2px 8px;border-radius:999px}
.gbas{font-size:13px;font-weight:650;margin:4px 0 8px}
.gliste{display:grid;grid-template-columns:1fr;gap:7px;margin-bottom:12px}
.gi{display:flex;align-items:flex-start;gap:10px;background:#F7F7F4;border-radius:9px;padding:8px 11px}
.gi .pill{flex:none}.gt{display:flex;flex-direction:column;line-height:1.3}.gt b{font-size:12.5px}.gt span{font-size:11.5px;color:var(--muted)}
.ekler{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.ekb{background:#FBF7EE;border:1px solid #EADFC7;border-radius:8px;padding:5px 9px;font-size:11.5px;color:#7A5B10}
@media(max-width:560px){.ozet .b{font-size:30px}}
</style>
<script src="https://s3.tradingview.com/tv.js"></script>
</head><body><div class="wrap">
<header><div><h1>BIST Sinyal Panosu</h1><div class="tarih">Son güncelleme: __TARIH__ · <a href="#" onclick="yenile();return false" title="Sayfanın en son halini getirir (önbelleği atlar)">↻ Yenile</a> · <a href="https://github.com/BoranZZ/Bist-signal/actions/workflows/tarama.yml" target="_blank" rel="noopener" title="GitHub'da 'Run workflow' ile taramayı hemen başlat; 3-5 dk sonra Yenile'ye bas">Taramayı şimdi başlat ↗</a></div></div>
<div class="ozet">
<div><div class="b">__AL__</div><div class="l">/ __TOPLAM__ hissede AL</div></div>
<div><div class="b g">__GUCLU__</div><div class="l">★ AL+ (teknik+temel)</div></div>
</div></header>
<div class="ipucu">İncelemek için bir satıra tıkla → grafik, oranlar ve o hisseye özel yorum açılır. Sütun başlığına tıklayınca sıralanır. · <a class="glink" href="gecmis.html">Sinyal Geçmişi →</a></div>
__BANNER__
<div class="pfbox">
  <div class="pfbas"><h2>Portföyüm</h2><div class="pfsag"><span id="pftop" class="pftop"></span><button class="pfekle" onclick="pfFormAc()">+ Ekle</button></div></div>
  <div id="pfform" class="pfform">
    <input id="pfkod" placeholder="Hisse (örn. THYAO)" list="pfkodlar" autocomplete="off">
    <datalist id="pfkodlar"></datalist>
    <input id="pfadet" type="number" min="1" placeholder="Adet">
    <input id="pfmal" type="number" step="any" min="0" placeholder="Maliyet (TL)">
    <button class="pfkaydet" onclick="pfKaydet()">Ekle</button>
    <button class="pfipt" onclick="pfFormKapat()">İptal</button>
  </div>
  <div id="pflist"></div>
</div>
<div class="sar"><table id="t"><thead><tr>
<th data-t="s">Hisse</th><th class="num" data-t="n">Fiyat</th><th class="num" data-t="n">Değişim</th><th data-t="s">Sinyal</th>
<th class="num" data-t="n">Sinyalde</th><th class="num" data-t="n">Uyum</th><th class="num" data-t="n">RSI</th><th class="num" data-t="n">F/K</th><th class="num" data-t="n">PD/DD</th><th class="num" data-t="n">Stop</th><th class="num" data-t="n">Öneri lot</th>
</tr></thead><tbody>__ROWS__</tbody></table></div>
<div class="aciklama">
<div class="kart"><h3>AL / AL+ / NÖTR / SAT</h3><p>Trend, ortalama dizilimi, MACD kesişimi ve RSI momentumundan bir puan. <b>★ AL+</b>: teknik AL ile birlikte F/K ve PD/DD de grup medyanının altında.</p></div>
<div class="kart"><h3>Öneri lot (risk yönetimi)</h3><p>Stop yerse portföyünün sadece belirlediğin yüzdeyi (örn. %1) kaybedeceğin lot sayısı: (portföy×risk%)÷(fiyat−stop).</p></div>
<div class="kart"><h3>RSI</h3><p>0–100 momentum. 30 altı aşırı satım, 70 üstü aşırı alım. Sağlıklı yükseliş 45–68 bandında.</p></div>
<div class="kart"><h3>MACD</h3><p>İki ortalamanın farkı. MACD sinyali yukarı keserse momentum boğaya döndü — klasik al tetiği.</p></div>
<div class="kart"><h3>F/K</h3><p>Fiyat ÷ yıllık kâr. Mutlak eşik yok; ▼ grup medyanının altında (görece ucuz). Enflasyonda yanıltıcı olabilir, tek başına karar değil.</p></div>
<div class="kart"><h3>PD/DD</h3><p>Borsa değeri ÷ defter değeri. 1 = defter değerine eşit. ▼ görece ucuz.</p></div>
<div class="kart"><h3>FD/FAVÖK</h3><p>Şirketin toplam değeri (FD) ÷ FAVÖK. Şirketin faaliyet kârına göre kaç kat pahalı/ucuz fiyatlandığını gösterir. Düşükse görece ucuz.</p></div>
<div class="kart"><h3>Destek / Direnç</h3><p>Son 120 günün dip ve tepe noktaları. <b>Destekten tepki</b>: fiyat eski bir dibe indi ve yukarı dönüyor. <b>Dirence yaklaşıyor</b>: fiyat geçmişte satış gelen bir tepeye yakın, temkinli ol. Hisseye tıklayınca seviyeleri görürsün.</p></div>
</div>
<div class="uyari">Yatırım tavsiyesi değildir. Göstergeler geçmişe bakar, geleceği garanti etmez; bu araç yalnızca sistemli karar vermeye yardımcı olur. Veriler ~15 dk gecikmeli olabilir. Kararların sorumluluğu sana aittir.</div>
</div>

<div class="ust" id="ust" onclick="if(event.target===this)kapat()"><div class="modal" id="modal"></div></div>
<script>
const DATA=__DATA__;
const t=document.getElementById('t');
t.querySelectorAll('th').forEach((th,i)=>{th.addEventListener('click',()=>{
const tb=t.tBodies[0],rows=[...tb.rows],num=th.dataset.t==='n',asc=th._asc=!th._asc;
rows.sort((a,b)=>{let x=a.cells[i].innerText.replace('%','').replace('+',''),y=b.cells[i].innerText.replace('%','').replace('+','');
if(num){x=parseFloat(x)||-1e9;y=parseFloat(y)||-1e9;return asc?x-y:y-x;}return asc?x.localeCompare(y,'tr'):y.localeCompare(x,'tr');});
rows.forEach(r=>tb.appendChild(r));});});

function cizgi(vals,color,W,H,min,max,w){
 const pts=[];const n=vals.length;
 for(let i=0;i<n;i++){if(vals[i]==null)continue;
  const x=(i/(n-1))*(W-8)+4;const y=H-4-((vals[i]-min)/(max-min))*(H-8);pts.push(x.toFixed(1)+','+y.toFixed(1));}
 return '<polyline fill="none" stroke="'+color+'" stroke-width="'+w+'" points="'+pts.join(' ')+'"/>';
}
function yatay(v,color,W,H,min,max){
 const y=(H-4-((v-min)/(max-min))*(H-8)).toFixed(1);
 return '<line x1="4" x2="'+(W-4)+'" y1="'+y+'" y2="'+y+'" stroke="'+color+'" stroke-width="1.2" stroke-dasharray="5 4"/>';
}
function grafik(sp,sd){
 if(!sp||!sp.c) return '<div style="color:#6B7079;font-size:13px">Grafik verisi yok.</div>';
 const ds=sd&&sd.destek?sd.destek.fiyat:null,dr=sd&&sd.direnc?sd.direnc.fiyat:null;
 const W=580,H=180;const all=[...sp.c,...(sp.s20||[]),...(sp.s50||[]),ds,dr].filter(x=>x!=null);
 const min=Math.min(...all),max=Math.max(...all);
 let g='<svg viewBox="0 0 '+W+' '+H+'" width="100%" preserveAspectRatio="none" style="display:block">';
 if(ds!=null)g+=yatay(ds,'#3A6EA5',W,H,min,max);
 if(dr!=null)g+=yatay(dr,'#B7791F',W,H,min,max);
 g+=cizgi(sp.c,'#16181D',W,H,min,max,1.6);
 if(sp.s20)g+=cizgi(sp.s20,'#0E4D45',W,H,min,max,1.2);
 if(sp.s50)g+=cizgi(sp.s50,'#C7962B',W,H,min,max,1.2);
 if(sp.st)g+=cizgi(sp.st,'#B4362E',W,H,min,max,1.4);
 g+='</svg>';return g;
}
function sdHtml(d){
 const sd=d.sd;if(!sd)return '';
 const sat=(ad,s,tur)=>{
  if(!s)return '<div class="sdsat"><b>'+ad+':</b> son '+sd.gun+' günde fiyatın '+(tur==='dip'?'altında':'üstünde')+' belirgin bir '+tur+' yok.</div>';
  const yon=s.uzaklik<0?'altında':'üstünde';
  const test=s.test>1?' · bu bölge '+s.test+' kez test edildi ('+s.tarihler.join(', ')+')':'';
  return '<div class="sdsat"><b>'+ad+': '+s.fiyat+' TL</b> — '+s.tarih+' tarihli '+tur+', fiyatın %'+Math.abs(s.uzaklik)+' '+yon+test+'</div>';
 };
 let h='<div class="sdkutu"><div class="gbas">Destek / Direnç</div>'+sat('Destek',sd.destek,'dip')+sat('Direnç',sd.direnc,'tepe');
 if(sd.tepki)h+='<div class="sdnot destek"><b>Destekten tepki:</b> fiyat son 5 günde '+sd.destek.fiyat+' TL desteğine indi ve yukarı dönmeye başladı (bugünkü kapanış dünküden yüksek). Destek tutarsa olumlu; bu seviyenin altında kapanış gelirse bu okuma geçersiz olur.</div>';
 if(sd.yaklas)h+='<div class="sdnot direnc"><b>Dirence yaklaşıyor:</b> fiyat '+sd.direnc.fiyat+' TL direncine %'+sd.tol+'\'den daha yakın. Geçmişte bu seviyede satış geldi; aşamazsa geri dönebilir. Kapanışla net aşarsa direnç desteğe dönüşebilir.</div>';
 if(!sd.tepki&&!sd.yaklas)h+='<div class="sdyok">Fiyat şu an bir desteğe tepki vermiyor ve bir dirence yakın değil.</div>';
 h+='<div class="sdyontem">Nasıl bulunur: son '+sd.gun+' günün dip ve tepe noktaları (iki yanındaki 5 günün en düşüğü/en yükseği). Son 10 günde oluşanlar sayılmaz. Etiket için seviye en az '+(sd.min_test||2)+' kez test edilmiş olmalı. "Yakın" eşiği bu hisse için %'+sd.tol+' (hissenin oynaklığına göre).</div></div>';
 return h;
}
function yenile(){location.href=location.pathname+'?t='+Date.now();}
function ac(k){
 const d=DATA[k];if(!d)return;
 const dcls=(d.degisim||0)>=0?'pos':'neg';const dtxt=d.degisim==null?'—':((d.degisim>=0?'+':'')+d.degisim+'%');
 const pill='<span class="pill '+(d.sinyal==='AL'?'al':d.sinyal==='SAT'?'sat':'notr')+'">'+d.sinyal+'</span>'+(d.guclu?' <span class="yildiz">★</span>':'');
 const m=(l,v)=>'<div class="m"><div class="l">'+l+'</div><div class="v">'+(v==null?'—':v)+'</div></div>';
 const lot=(d.lot&&d.sinyal==='AL')?d.lot+' lot':'—';
 const tv='https://www.tradingview.com/chart/?symbol=BIST%3A'+k;
 let gost='';
 (d.detay||[]).forEach(x=>{const cls=x.sinyal==='AL'?'al':(x.sinyal==='SAT'?'sat':'notr');
   gost+='<div class="gi"><span class="pill '+cls+'">'+x.sinyal+'</span><div class="gt"><b>'+x.ad+'</b><span>'+x.aciklama+'</span></div></div>';});
 let ekh='';(d.ek||[]).forEach(e=>{ekh+='<span class="ekb"><b>'+e.ad+':</b> '+e.aciklama+'</span>';});
 const uyum=d.uyum?('<span class="uyroz">'+d.uyum+' gösterge AL</span>'):'';
 // zamanlama + çıkış kuralı
 let zaman='';
 if(d.sinyal_gun!=null){
   const sd=d.sinyal_degisim;const sdc=(sd||0)>=0?'pos':'neg';
   const sdt=sd==null?'':(' · başlangıçtan beri <span class="'+sdc+'">'+((sd>=0?'+':'')+sd+'%')+'</span>');
   const yenirz=(d.yeni&&d.sinyal==='AL')?' <span class="yeni">YENİ</span>':'';
   zaman='<div class="zaman"><div><b>'+d.sinyal+'</b> sinyali: '+d.sinyal_tarih+' ('+d.sinyal_gun+' gündür)'+yenirz+sdt+'</div>';
   if(d.sinyal==='AL'){
     const gs=(d.giris_stop!=null?d.giris_stop:d.stop);
     zaman+='<div class="cikis">Çıkış kuralı: sinyal <b>SAT</b>\'a dönerse ya da <b>giriş stopu '+gs+' TL</b> altına inerse.'+
       (d.hedef?' · Örnek hedef (2R, mekanik referans): <b>'+d.hedef+' TL</b>':'')+'</div>';
   }
   zaman+='</div>';
 }
 document.getElementById('modal').innerHTML=
 '<div class="mh"><div class="sol"><h2>'+k+'</h2>'+pill+uyum+'</div><button class="kapa" onclick="kapat()">✕</button></div>'+
 '<div class="mfiyat">'+(d.fiyat!=null?d.fiyat+' TL':'')+' <span class="'+dcls+'">'+dtxt+'</span></div>'+
 zaman+
 '<div class="grafik">'+grafik(d.spark,d.sd)+'<div class="leg"><span class="c1">Fiyat</span><span class="c2">SMA20</span><span class="c3">SMA50</span><span class="c4">SuperTrend</span>'+
   (d.sd&&d.sd.destek?'<span class="c5">Destek</span>':'')+(d.sd&&d.sd.direnc?'<span class="c6">Direnç</span>':'')+'</div></div>'+
 sdHtml(d)+
 '<div class="tvwrap"><div id="tvbox"></div></div>'+
 '<div class="metr">'+m('RSI',d.rsi)+m('F/K',d.fk)+m('PD/DD',d.pddd)+m('FD/FAVÖK',d.favok)+m('Giriş stopu',d.giris_stop!=null?d.giris_stop:d.stop)+m('Öneri lot',lot)+'</div>'+
 '<div class="gbas">Göstergeler</div><div class="gliste">'+gost+'</div>'+
 (ekh?'<div class="ekler">'+ekh+'</div>':'')+
 '<div class="yorum">'+(d.yorum||d.gerekce.join(' · '))+'</div>'+
 '<div class="btnler"><a class="btn p" href="'+tv+'" target="_blank" rel="noopener">TradingView\'de tam ekran ↗</a></div>';
 document.getElementById('ust').classList.add('acik');
 tvGoster(k);
}
function kapat(){document.getElementById('ust').classList.remove('acik');var b=document.getElementById('tvbox');if(b)b.innerHTML='';}
document.addEventListener('keydown',e=>{if(e.key==='Escape')kapat();});

function tvGoster(k){
 var box=document.getElementById('tvbox'); if(!box) return; box.innerHTML='';
 if(typeof TradingView==='undefined'){box.innerHTML='<div class="tvyok">Etkileşimli grafik yüklenemedi (internet gerekiyor). Yukarıdaki hızlı grafiği ya da TradingView butonunu kullan.</div>';return;}
 try{new TradingView.widget({autosize:true,symbol:'BIST:'+k,interval:'D',timezone:'Europe/Istanbul',theme:'light',style:'1',locale:'tr',allow_symbol_change:false,hide_side_toolbar:false,studies:['RSI@tv-basicstudies','MACD@tv-basicstudies'],container_id:'tvbox'});}
 catch(e){box.innerHTML='<div class="tvyok">Grafik açılamadı.</div>';}
}

var PF_KEY='portfoyum_v1';
function pfOku(){try{return JSON.parse(localStorage.getItem(PF_KEY))||[]}catch(e){return[]}}
function pfYaz(a){try{localStorage.setItem(PF_KEY,JSON.stringify(a))}catch(e){}}
function pfFormAc(){document.getElementById('pfform').style.display='flex';document.getElementById('pfkod').focus();}
function pfFormKapat(){document.getElementById('pfform').style.display='none';}
function pfKaydet(){
 var k=(document.getElementById('pfkod').value||'').trim().toUpperCase();
 var ad=parseFloat(document.getElementById('pfadet').value);
 var ma=parseFloat(document.getElementById('pfmal').value);
 if(!k||!(ad>0)||!(ma>0)){alert('Hisse kodu, adet ve maliyet gir.');return;}
 var a=pfOku();a.push({kod:k,adet:ad,maliyet:ma});pfYaz(a);
 document.getElementById('pfkod').value='';document.getElementById('pfadet').value='';document.getElementById('pfmal').value='';
 pfFormKapat();pfRender();
}
function pfSil(i){var a=pfOku();a.splice(i,1);pfYaz(a);pfRender();}
function pfRender(){
 var a=pfOku(),liste=document.getElementById('pflist'),top=document.getElementById('pftop');
 if(!a.length){liste.innerHTML='<div class="pfy bos">Henüz hisse yok. <b>+ Ekle</b> ile portföyünü oluştur (bu cihazda saklanır).</div>';top.textContent='';return;}
 var toplam=0;
 var r='<div class="sar"><table class="pf"><thead><tr><th>Hisse</th><th class="num">Adet</th><th class="num">Maliyet</th><th class="num">Güncel</th><th class="num">K/Z %</th><th class="num">K/Z TL</th><th>Sinyal</th><th></th></tr></thead><tbody>';
 a.forEach(function(p,i){
  var d=DATA[p.kod]||{},f=d.fiyat;
  var kzy=(f!=null)?((f/p.maliyet-1)*100):null, kzt=(f!=null)?((f-p.maliyet)*p.adet):null;
  if(kzt!=null)toplam+=kzt;
  var sn=d.sinyal||'—',scls=sn==='AL'?'al':(sn==='SAT'?'sat':'notr');
  var uy=(sn==='SAT')?' <span class="pfuy">SAT — gözden geçir</span>':'';
  var kzc=(kzy||0)>=0?'pos':'neg';
  r+='<tr onclick="ac(\''+p.kod+'\')"><td class="kod">'+p.kod+'</td><td class="num">'+p.adet+'</td><td class="num">'+p.maliyet+'</td>'+
     '<td class="num">'+(f!=null?f:'—')+'</td>'+
     '<td class="num '+kzc+'">'+(kzy!=null?((kzy>=0?'+':'')+kzy.toFixed(1)+'%'):'—')+'</td>'+
     '<td class="num '+kzc+'">'+(kzt!=null?((kzt>=0?'+':'')+Math.round(kzt).toLocaleString('tr-TR')+' TL'):'—')+'</td>'+
     '<td><span class="pill '+scls+'">'+sn+'</span>'+uy+'</td>'+
     '<td class="num"><button class="pfsil" onclick="event.stopPropagation();pfSil('+i+')">✕</button></td></tr>';
 });
 r+='</tbody></table></div>';liste.innerHTML=r;
 top.innerHTML='Toplam K/Z: <b class="'+(toplam>=0?'pos':'neg')+'">'+(toplam>=0?'+':'')+Math.round(toplam).toLocaleString('tr-TR')+' TL</b>';
}
(function(){var dl=document.getElementById('pfkodlar');if(dl){dl.innerHTML=Object.keys(DATA).sort().map(function(k){return '<option value="'+k+'"></option>';}).join('');}pfRender();})();
</script></body></html>"""


_GECMIS = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Sinyal Geçmişi</title>
<style>
:root{--bg:#FAFAF8;--ink:#16181D;--muted:#6B7079;--line:#E6E7E4;--accent:#0E4D45;--pos:#1B7F4B;--neg:#B4362E;--panel:#FFF}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;font-feature-settings:"tnum" 1}
.wrap{max-width:1000px;margin:0 auto;padding:26px 18px 60px}
a.geri{color:var(--accent);text-decoration:none;font-weight:600;font-size:13px}
h1{font-size:19px;margin:10px 0 2px}.tarih{color:var(--muted);font-size:12.5px}
.kartlar{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:20px 0}
.k{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.k .b{font-size:26px;font-weight:680}.k .l{color:var(--muted);font-size:12px;margin-top:3px}
h2{font-size:15px;margin:22px 0 8px}
.sar{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--panel)}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:560px}
th,td{padding:9px 11px;text-align:left;white-space:nowrap}th{color:var(--muted);font-weight:600;font-size:11.5px;border-bottom:1px solid var(--line)}
tbody tr{border-bottom:1px solid var(--line)}tbody tr:last-child{border-bottom:none}
.kod{font-weight:650}.num{text-align:right;font-variant-numeric:tabular-nums}.stop{color:var(--neg)}.pos{color:var(--pos)}.neg{color:var(--neg)}
.not{margin-top:22px;padding:13px 15px;border:1px solid var(--line);border-radius:10px;background:#fff;color:var(--muted);font-size:12px;line-height:1.6}
</style></head><body><div class="wrap">
<a class="geri" href="index.html">← Panoya dön</a>
<h1>Sinyal Geçmişi (canlı karne)</h1><div class="tarih">Güncelleme: __TARIH__</div>
<div class="kartlar">
<div class="k"><div class="b">%__ISABET__</div><div class="l">kapanan sinyallerde isabet</div></div>
<div class="k"><div class="b">__KAPANAN__</div><div class="l">kapanan sinyal sayısı</div></div>
<div class="k"><div class="b">%__ORT__</div><div class="l">kapananların ortalama sonucu</div></div>
<div class="k"><div class="b">__ACIK__</div><div class="l">şu an açık takip</div></div>
</div>
<h2>Açık pozisyonlar (takipte)</h2>
<div class="sar"><table><thead><tr><th>Hisse</th><th>Sinyal tarihi</th><th class="num">Giriş</th><th class="num">Güncel</th><th class="num">Anlık %</th><th class="num">Stop</th></tr></thead><tbody>__ACIKROWS__</tbody></table></div>
<h2>Kapanmış sinyaller</h2>
<div class="sar"><table><thead><tr><th>Hisse</th><th>Giriş tarihi</th><th class="num">Giriş</th><th>Çıkış tarihi</th><th class="num">Çıkış</th><th class="num">Sonuç %</th><th>Sebep</th></tr></thead><tbody>__KAPALIROWS__</tbody></table></div>
<div class="not">Bu sayfa <b>ileriye dönük gerçek</b> karnedir: sistem AL dediği anki fiyatı kaydeder, sonra stop yerse ya da sinyal SAT'a dönerse kapatıp sonucu yazar. Backtest geçmişi simüle eder; bu sayfa ise sistemin <b>bugünden itibaren</b> gerçek performansını biriktirir. Yatırım tavsiyesi değildir.</div>
</div></body></html>"""
