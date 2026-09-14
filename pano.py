"""Tarama sonuçlarından tek dosyalık, kendi kendine yeten bir HTML pano üretir."""
from datetime import datetime

SINYAL_RENK = {"AL": "al", "NÖTR": "notr", "SAT": "sat"}


def _h(v, suffix="", dash="—"):
    return dash if v is None else f"{v}{suffix}"


def _oran_etiket(v, medyan):
    if v is None or medyan is None:
        return ""
    return "ucuz" if v < medyan else "pahali"


def pano_uret(sonuclar, ornek=False, uyari=None):
    tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
    al_sayisi = sum(1 for s in sonuclar if s["sinyal"] == "AL")
    guclu_sayisi = sum(1 for s in sonuclar if s.get("guclu"))
    toplam = len(sonuclar)

    fk_list = sorted(s["fk"] for s in sonuclar if s.get("fk"))
    pddd_list = sorted(s["pddd"] for s in sonuclar if s.get("pddd"))
    fk_med = fk_list[len(fk_list) // 2] if fk_list else None
    pddd_med = pddd_list[len(pddd_list) // 2] if pddd_list else None

    oncelik = {"AL": 0, "NÖTR": 1, "SAT": 2}
    sonuclar = sorted(sonuclar, key=lambda s: (oncelik[s["sinyal"]], not s.get("guclu"), -s["puan"]))

    satirlar = []
    for s in sonuclar:
        renk = SINYAL_RENK[s["sinyal"]]
        deg = s.get("degisim")
        deg_cls = "pos" if (deg or 0) >= 0 else "neg"
        deg_txt = f"{'+' if (deg or 0) >= 0 else ''}{deg}%" if deg is not None else "—"
        fk_cls = _oran_etiket(s.get("fk"), fk_med)
        pddd_cls = _oran_etiket(s.get("pddd"), pddd_med)
        fk_ok = {"ucuz": "▼", "pahali": "▲", "": ""}[fk_cls]
        pddd_ok = {"ucuz": "▼", "pahali": "▲", "": ""}[pddd_cls]
        yildiz = ' <span class="yildiz" title="Teknik + temel birlikte güçlü">★</span>' if s.get("guclu") else ""
        lot = s.get("lot")
        lot_txt = f"{lot}" if (lot and s["sinyal"] == "AL") else "—"
        gerekce = " · ".join(s.get("gerekce", []))
        satirlar.append(f"""<tr>
  <td class="kod">{s['kod']}</td>
  <td class="num">{_h(s.get('fiyat'))}</td>
  <td class="num {deg_cls}">{deg_txt}</td>
  <td><span class="pill {renk}">{s['sinyal']}</span>{yildiz}</td>
  <td class="num">{_h(s.get('rsi'))}</td>
  <td class="num">{_h(s.get('fk'))}<span class="tag {fk_cls}">{fk_ok}</span></td>
  <td class="num">{_h(s.get('pddd'))}<span class="tag {pddd_cls}">{pddd_ok}</span></td>
  <td class="num stop">{_h(s.get('stop'))}</td>
  <td class="num lot">{lot_txt}</td>
  <td class="gerekce">{gerekce}</td>
</tr>""")

    banner = ('<div class="banner ornek">ÖRNEK VERİ — sistemin görünümünü gösterir; gerçek sürüm her akşam canlı fiyatla dolar.</div>'
              if ornek else "")
    if uyari:
        banner += f'<div class="banner uyari-b">⚠️ {uyari}</div>'

    return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BIST Sinyal Panosu</title>
<style>
:root{{--bg:#FAFAF8;--ink:#16181D;--muted:#6B7079;--line:#E6E7E4;--accent:#0E4D45;
--al:#1B7F4B;--notr:#9A7A12;--sat:#B4362E;--pos:#1B7F4B;--neg:#B4362E;--panel:#FFF}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
font-feature-settings:"tnum" 1;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1180px;margin:0 auto;padding:28px 20px 60px}}
header{{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:16px;
border-bottom:1px solid var(--line);padding-bottom:20px}}
h1{{font-size:20px;letter-spacing:-.01em;margin:0;font-weight:650}}
.tarih{{color:var(--muted);font-size:13px;margin-top:4px}}
.ozet{{display:flex;gap:26px;text-align:right}}
.ozet .buyuk{{font-size:42px;font-weight:680;line-height:1;color:var(--accent);letter-spacing:-.02em}}
.ozet .buyuk.g{{color:var(--al)}}
.ozet .alt{{color:var(--muted);font-size:12.5px;margin-top:3px}}
.banner{{margin:16px 0 0;padding:10px 14px;border-radius:8px;font-size:13px}}
.banner.ornek{{background:#FBF3E4;border:1px solid #EBD9B0;color:#7A5B10}}
.banner.uyari-b{{background:#FBECEA;border:1px solid #E6C3BD;color:#8A2F26}}
.tablo-sar{{margin-top:22px;overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--panel)}}
table{{width:100%;border-collapse:collapse;font-size:13.5px;min-width:900px}}
th,td{{padding:11px 12px;text-align:left;white-space:nowrap}}
th{{position:sticky;top:0;background:var(--panel);color:var(--muted);font-weight:600;font-size:12px;
border-bottom:1px solid var(--line);cursor:pointer;user-select:none}}
th:hover{{color:var(--ink)}}
tbody tr{{border-bottom:1px solid var(--line)}}tbody tr:last-child{{border-bottom:none}}
tbody tr:hover{{background:#F6F6F3}}
.kod{{font-weight:650}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.gerekce{{color:var(--muted);white-space:normal;min-width:250px;font-size:12.5px}}
.stop{{color:var(--sat)}}.lot{{font-weight:650}}
.pos{{color:var(--pos)}}.neg{{color:var(--neg)}}
.pill{{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:650}}
.pill.al{{background:#E4F2E9;color:var(--al)}}
.pill.notr{{background:#F1EFE8;color:var(--notr)}}
.pill.sat{{background:#F7E7E5;color:var(--sat)}}
.yildiz{{color:#C7962B;font-size:13px}}
.tag{{font-size:10px;margin-left:5px}}.tag.ucuz{{color:var(--al)}}.tag.pahali{{color:var(--sat)}}
.aciklama{{margin-top:36px;display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}}
.kart{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
.kart h3{{margin:0 0 6px;font-size:14px}}.kart p{{margin:0;color:var(--muted);font-size:13px;line-height:1.55}}
.uyari{{margin-top:34px;padding:14px 16px;border:1px solid var(--line);border-radius:10px;
background:#fff;color:var(--muted);font-size:12.5px;line-height:1.6}}
@media(max-width:560px){{.ozet .buyuk{{font-size:32px}}}}
</style></head><body><div class="wrap">
<header><div><h1>BIST Sinyal Panosu</h1><div class="tarih">Son güncelleme: {tarih}</div></div>
<div class="ozet">
<div><div class="buyuk">{al_sayisi}</div><div class="alt">/ {toplam} hissede AL</div></div>
<div><div class="buyuk g">{guclu_sayisi}</div><div class="alt">★ AL+ (teknik+temel)</div></div>
</div></header>
{banner}
<div class="tablo-sar"><table id="t"><thead><tr>
<th data-t="s">Hisse</th><th data-t="n">Fiyat</th><th data-t="n">Değişim</th>
<th data-t="s">Sinyal</th><th data-t="n">RSI</th><th data-t="n">F/K</th>
<th data-t="n">PD/DD</th><th data-t="n">Stop</th><th data-t="n">Öneri lot</th><th data-t="s">Gerekçe</th>
</tr></thead><tbody>{''.join(satirlar)}</tbody></table></div>
<div class="aciklama">
<div class="kart"><h3>AL / AL+ / NÖTR / SAT</h3><p>Trend, ortalama dizilimi, MACD kesişimi ve RSI momentumundan bir puan. <b>★ AL+</b>: teknik AL ile birlikte F/K ve PD/DD de grup medyanının altında — yani hem grafik hem değerleme olumlu.</p></div>
<div class="kart"><h3>Öneri lot (risk yönetimi)</h3><p>Portföyünün belirlediğin küçük bir yüzdesini (örn. %1) riske atacak lot sayısı: (portföy × risk%) ÷ (fiyat − stop). Böylece stop yerse kaybın portföyünün sadece o yüzdesi kadar olur.</p></div>
<div class="kart"><h3>RSI</h3><p>0–100 momentum. 30 altı aşırı satım, 70 üstü aşırı alım. Sağlıklı yükseliş 45–68 bandında.</p></div>
<div class="kart"><h3>MACD</h3><p>İki ortalamanın farkı. MACD çizgisi sinyali yukarı keserse momentum boğaya döndü — klasik al tetiği.</p></div>
<div class="kart"><h3>F/K</h3><p>Fiyat ÷ hisse başı yıllık kâr. ▼ grup medyanının altında (görece ucuz). Sektöre göre yorumlanır.</p></div>
<div class="kart"><h3>PD/DD</h3><p>Borsa değeri ÷ defter (özkaynak) değeri. 1 = defter değerine eşit. ▼ görece ucuz.</p></div>
<div class="kart"><h3>Stop</h3><p>Zarar-kes seviyesi. Fiyat buranın altına inerse duygusuz çık — sermayeni korur.</p></div>
</div>
<div class="uyari">Yatırım tavsiyesi değildir. Göstergeler geçmişe bakar, geleceği garanti etmez; bu araç yalnızca sistemli karar vermeye yardımcı olur. Temel oranlar veri sağlayıcıdan gelir, bazı hisselerde eksik/gecikmeli olabilir. Kararların sorumluluğu sana aittir.</div>
</div>
<script>
const t=document.getElementById('t');
t.querySelectorAll('th').forEach((th,i)=>{{th.addEventListener('click',()=>{{
const tb=t.tBodies[0],rows=[...tb.rows],num=th.dataset.t==='n',asc=th._asc=!th._asc;
rows.sort((a,b)=>{{let x=a.cells[i].innerText.replace('%','').replace('+',''),y=b.cells[i].innerText.replace('%','').replace('+','');
if(num){{x=parseFloat(x)||-1e9;y=parseFloat(y)||-1e9;return asc?x-y:y-x;}}
return asc?x.localeCompare(y,'tr'):y.localeCompare(x,'tr');}});
rows.forEach(r=>tb.appendChild(r));}});}});
</script></body></html>"""
