"""📅 takvim.json'u resmî sayfalarla karşılaştıran ARAÇ (taramada ÇALIŞMAZ; Claude 'takvimi yenile' denince elle çalıştırır).
Fed, BLS (istihdam + ABD TÜFE), ECB, TCMB PPK, TÜİK TÜFE sayfalarını okur; farkları yazar, takvim.json'a DOKUNMAZ.
Kaynak açılmazsa 'kontrol edilemedi' der. Gerekenler: requests, beautifulsoup4, lxml (requirements.txt'te değil — yerelde kur).
Kullanım: python takvim_kontrol.py [takvim.json]   (araştırma: Documents/Bist-arastirma/2026-11-14/takvim/RAPOR.md)"""
import json, re, sys, requests
from datetime import date
from bs4 import BeautifulSoup
sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
UA_BLS = {"User-Agent": "bist-sinyal-takvim iletisim@ornek.com"}   # BLS: e-posta içeren kimlik ister; tarayıcı kimliğine 403
MON = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
MA = {k[:3]: v for k, v in MON.items()}
AY = {"Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5, "Haziran": 6, "Temmuz": 7, "Ağustos": 8, "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12}
def al(u, h=UA):
    r = requests.get(u, headers=h, timeout=30); r.raise_for_status(); return r
def fed():
    s = BeautifulSoup(al("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm").content, "lxml"); out = set()
    for p in s.select("div.panel.panel-default"):
        h = p.select_one("div.panel-heading"); ym = h and re.match(r"(\d{4}) FOMC", h.get_text(strip=True))
        if not ym: continue
        for m in p.select("div.fomc-meeting"):
            ay = m.select_one(".fomc-meeting__month").get_text(strip=True).split("/")[-1]
            g = re.findall(r"\d+", m.select_one(".fomc-meeting__date").get_text())
            if g and ay in MON: out.add(f"{ym.group(1)}-{MON[ay]:02d}-{int(g[-1]):02d}")
    return out
def bls(sayfa):
    tx = BeautifulSoup(al(f"https://www.bls.gov/schedule/news_release/{sayfa}.htm", UA_BLS).content, "lxml").get_text(" ", strip=True)
    return {f"{y}-{MA[m]:02d}-{d}" for m, d, y in re.findall(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.? (\d{2}), (\d{4}) \d\d:\d\d [AP]M", tx)}
def ecb():
    tx = BeautifulSoup(al("https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html").content, "lxml").get_text("\n", strip=True)
    return {f"{y}-{mo}-{d}" for d, mo, y, a in re.findall(r"(\d{2})/(\d{2})/(\d{4})\n([^\n]*)", tx) if "press conference" in a.lower() and "monetary policy" in a.lower()}
def tcmb(yil):
    s = BeautifulSoup(al(f"https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Temel+Faaliyetler/Para+Politikasi/PPK/{yil}").content, "lxml"); out = set()
    for tr_ in s.find_all("tr"):
        td = tr_.find_all("td")
        if td:
            m = re.match(r"^(\d{1,2}) (\w+) (\d{4})", re.sub(r"\s+", " ", td[0].get_text(" ", strip=True).replace("\xa0", " ")))
            if m and m.group(2) in AY: out.add(f"{m.group(3)}-{AY[m.group(2)]:02d}-{int(m.group(1)):02d}")
    return out
def tuik(yil):
    h = dict(UA, Referer="https://www.tuik.gov.tr/Kurumsal/Veri_Takvimi", **{"X-Requested-With": "XMLHttpRequest"})
    d = al(f"https://www.tuik.gov.tr/Kurumsal/GetYillikHaberBulteniListesi?yil={yil}", h).json()
    return {x["gTarih"][:10] for x in d["yayindaOlanlarList"] + d["yayindaOlmayanlarList"]
            if x["sorumluKisaAd"] == "TÜİK" and x["adi"].startswith("Tüketici Fiyat Endeksi")}
def _yillar(f):
    y = date.today().year
    return f(y) | f(y + 1)
def kontrol(yol):
    J = json.load(open(yol, encoding="utf-8")); bugun = date.today().isoformat()
    K = {"FED": fed, "NFP": lambda: bls("empsit"), "ABD_TUFE": lambda: bls("cpi"), "ECB": ecb,
         "TCMB": lambda: _yillar(tcmb), "TUIK_TUFE": lambda: _yillar(tuik)}
    rapor = []
    for tur, f in K.items():
        bizde = {o["t"] for o in J["olaylar"] if o["tur"] == tur and o["t"] >= bugun}
        try:
            resmi = {t for t in f() if bugun <= t <= J["gecerli_son"]}
        except Exception as e:
            rapor.append(f"⚠️ {tur}: kontrol edilemedi ({type(e).__name__}) — takvim.json olduğu gibi kullanılıyor"); continue
        eksik, fazla = sorted(resmi - bizde), sorted(bizde - resmi)
        tahmini = {o["t"] for o in J["olaylar"] if o["tur"] == tur and not o.get("dogrulandi", True)}
        rapor.append(f"{'✅' if not eksik and not (set(fazla) - tahmini) else '📅'} {tur}: resmî {len(resmi)}, bizde {len(bizde)}"
                     + (f" | resmîde var bizde yok: {eksik}" if eksik else "")
                     + (f" | bizde var resmîde yok: {fazla}" if fazla else ""))
    return rapor
if __name__ == "__main__":
    print("\n".join(kontrol(sys.argv[1] if len(sys.argv) > 1 else "takvim.json")))
