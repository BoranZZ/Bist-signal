# BIST Sinyal Sistemi — Proje Notları (Claude Code için)

Bu depo, Borsa İstanbul (BIST) hisseleri için günlük teknik/temel sinyal panosu üretir.
Amaç: karar-destek aracı. **Yatırım tavsiyesi değildir**; kullanıcı kararı kendi verir.
Arayüz ve tüm metinler **Türkçe**. Kullanıcı kod bilmiyor — ona sade anlat, terminal
komutlarını tek tek ver.

## Nasıl çalışır
- GitHub Actions (`.github/workflows/tarama.yml`) hafta içi piyasa saatinde ~15 dk'da bir
  `python tarama.py` çalıştırır → `index.html` (pano), `gecmis.html` (canlı karne) üretir,
  yeni AL sinyallerini Telegram'a yollar, dosyaları repoya geri commit'ler.
- GitHub Pages `index.html`'i yayınlar: https://boranzz.github.io/Bist-signal/
- `backtest.yml` elle çalışır → gerçek 2 yıl veriyle `backtest.html`.
- Veri kaynağı: yfinance (`KOD.IS`), ~15 dk gecikmeli, ücretsiz.
- GitHub'ın cron'u saatlerce gecikiyor/atlıyor; asıl tetik cron-job.org → workflow_dispatch (README).
- Telegram: tüm hisselerde yeni AL; SAT sadece portföyde. NÖTR ara geçişleri sayılmaz
  (`durum.json` → `son`). Portföy repo'nun `PORTFOY` **variable**'ından gelir (kullanıcı onayıyla
  secret yerine variable: cihazlar arası eşitleme için). Pano, kullanıcının cihazındaki
  fine-grained anahtarla (Variables: R/W) her değişiklikte yazar. Anahtar localStorage'da
  olduğu için sayfaya üçüncü taraf script ekleme (TradingView tv.js bu yüzden kaldırıldı).
  **Actions logları herkese açık: portföy içeriğini/kodlarını asla print etme.**
  **durum.json da herkese açık:** portföyü ele verebilecek her anahtar `_gizli()` (TELEGRAM_TOKEN ile HMAC) ile
  saklanır (`sat_teyit_g`, `karar_kirilim_g`, alarm özetleri); portföy hissesine ait FİYAT da yazılmaz (fiyat
  hisseyi ele verir — karar çizgisi dünkü veriden yeniden hesaplanır). 2026-09-25/26'da `sat_teyit` düz kodla
  yazılmıştı (5 portföy kodu herkese açık göründü) — düzeltildi; git geçmişinde duruyor.

## Arkadaş kopyaları (fork)
Başkası kendi portföyü/Telegram'ı için repo'yu fork'lar (adımlar `KENDI-KOPYAN.md`). Bu yüzden depo adı sabit yazılmaz:
`pano.REPO` / `tarama.PANO_URL` Actions'ın `GITHUB_REPOSITORY`'sinden, panodaki `GH_REPO` adres çubuğundan (`<kullanıcı>.github.io/<repo>`)
türetilir; yerelde `BoranZZ/Bist-signal`. Fork'ta `tarama.yml` her taramada ana projeden `*.py`, `requirements.txt`, `*.md`'yi
alır (`KOD_GUNCELLE=hayir` variable'ı kapatır); veri dosyaları (durum/gecmis/index) fork'un kendisinin. Workflow dosyaları
GITHUB_TOKEN ile güncellenemez → workflow değişirse arkadaşa elle güncellemesini söyle. Yeni veri dosyası eklerken
`*.py`/`*.md` dışında bırak (aksi halde ana projeninki fork'unkini ezer).

## Dosyalar
- `sinyal.py` — gösterge + sinyal çekirdeği. **Tek kural seti** (canlı tarama + backtest ortak).
  SuperTrend, MACD, EMA20/50, RSI, Stochastic oy verir; ADX/Bollinger bağlam. `analiz_et(df)`
  son gün özetini döndürür (sinyal, uyum, detay, sinyal_gun, giris_stop, hedef, spark...).
- `tarama.py` — evren (BIST100 + EK_HISSELER + izleme listesi), oran önbelleği (F/K, PD/DD, FD-FAVÖK günde 1),
  yorum üretimi, sinyal geçmişi (gecmis.json), Telegram. Ayarlar dosyanın başında.
- `pano.py` — `index.html` ve `gecmis.html` üretir. Portföy istemci tarafında (localStorage),
  modalda kendi SVG grafiğimiz + TradingView butonu.
- `backtest.py` — ertesi-gün girişli, komisyonlu, al-tut kıyaslı simülasyon.
- `gunici.py` — ⏱️ gün içi görünüm (15 dk / 1 s / 4 s durum bilgisi; aşağıda 'Vadeler').

## Önemli ilkeler
- Sinyal kuralları tek yerde (`sinyal.py`); backtest ve canlı aynı motoru kullanmalı.
- Backtest'te look-ahead yasak; işleme ertesi gün girilir; maliyet `backtest.KOMISYON = 0.002` alışta VE satışta ayrı ayrı
  düşülür (`net = (1−K)·çıkış/giriş·(1−K) − 1` → gidiş-dönüş ≈ %0,4; eskiden burada yanlışlıkla 'çift yön %0,2' yazıyordu, kod hep
  böyleydi — 2026-10 kontrolü). Tüm geçmiş kararlar bu düzenekle alındı; değiştirme. Bazı scratchpad araştırmaları %0,1/yön kullandı.
- Dürüstlük: "daha çok gösterge = daha isabetli" değil; pusula backtest + canlı karne.
- Finansal tavsiye verme; stop/pozisyon büyüklüğü/risk vurgusu koru.

## TradingView notu (bilinen kısıt)
Ücretsiz TradingView gömülü widget'ı BIST sembollerini gösteremiyor ("sadece TradingView'de
bulunabilir" deyip Apple'a düşüyor). Bu yüzden modaldaki gömülü TradingView güvenilir değil.
Plan: kendi SVG grafiğimizi asıl grafik yap (eksen değerleri, daha uzun geçmiş, hover ile
tarih/fiyat), TradingView'i sadece "tam ekran aç" butonu olarak bırak.

## BEKLEYEN İŞLER (öncelik sırası)
1. **Grafik:** YAPILDI (eksenler, 6 ay, AL/SAT dönüş işaretleri, fare/dokunma ile değer). Eski not: kendi SVG grafiğini büyüt, fiyat/tarih
   eksen değerleri ekle, daha uzun geçmiş + hover tooltip. "Tam ekran aç" butonu kalsın.
2. **Hacim/likidite filtresi:** TEST EDİLDİ, GEREKMİYOR (2026-09-28, bt/likidite1.py: 586 hisse, 2022-26, ~2.000 v3
   işlemi; 60g medyan TL hacmine göre borsa içi sıra ya da nominal eşikte düşük likiditeli AL'ler kötü değil, farklar
   birkaç uç işlemden; en iyi 10 hariç gruplar benzer). Liste zaten <50 mn TL küçükleri almıyor.
3. **Destek/direnç + DİP mantığı:** YAPILDI (`sinyal.destek_direnc`): son 120 günün
   dip/tepelerinden "Destekten tepki" ve "Dirence yaklaşıyor" etiketleri, modalda seviye +
   tarih açıklaması. Eski RSI/Bollinger DİP etiketi kaldırıldı. Eksik kalan: düşen trend
   çizgisi kırılımı ile "olası dip".
3b. Modalda **DİP açıklaması**: YAPILDI (destek/direnç kutusu).
4. **FAVÖK açıklaması:** YAPILDI (açıklama kartı eklendi).
5. **KAP/haber akışı:** hisse başına son bildirim/haber (ücretsiz kaynak); yorumlamayı
   abartma (haber çoğu zaman fiyata yansımıştır).
6. Sektör dağılımı + yoğunlaşma uyarısı, haftalık Telegram özeti ve fiyat alarmı YAPILDI.

## Kullanıcının okumayı bilmediği şeyler (öğretilecek)
RSI, MACD ve hacim panellerinin nasıl okunacağını sade anlat (grafik dersi).

## Periyodik bakım
`tarama.py`'deki `BIST100` listesi 1 Ekim – 31 Aralık 2026 dönemine göre. Borsa İstanbul bileşimi
3 ayda bir değiştirir (sonraki: Ocak 2027). Endeksten çıkanları silme, `EK_HISSELER`'e taşı
(portföy ve sinyal geçmişi kopmasın). Yeni kodları yfinance'ta şirket adıyla doğrula.
`HALKA_ARZ` (son 12 ayın arzları: işlem başlangıcı + arz fiyatı, kaynak halkarz.com) ayda bir
güncellenmeli (güncelleyince `BIST100_GECERLI` / `HALKA_ARZ_GUNCEL` tarihlerini de değiştir: haftalık özet bunlara göre
🔧 bakım hatırlatması yapar); yfinance BIST bedelsiz/bölünme kaydı tutmuyor, arzdan beri getiri bölünmede yanılır.
Fon krizinde çöken şişirilmiş hisseler (TERA, SMRTG, GENIL, MIATK) listeden çıkarıldı; kullanıcı
isteğiyle faiz yüzünden düşen eski büyükler (KONTR vb.) KALDI — tüm çökenleri çıkarma.
**2026-10-20 `tarama.MANIPULE` (32 hisse):** kullanıcı isteğiyle fon krizi (Tera/Pusula/Hedef… fonlarının topladığı) hisseleri
TÜM analizlerden çıktı: `KODLAR`'dan düşülür → pano, İşlem Odası (canlı + oda_replay), backtest.py görmez. Ölçüt: 01.09.2026'dan
beri ≥10 kilitli taban (yfinance, scratchpad `manipule/tara.py` + `tablo.csv`) + haberlerde fon yoğunlaşması/soruşturmada geçen ISKPL, MIATK, GENIL, GESAN, A1CAP.
SMRTG kullanıcı isteğiyle listede KALDI. Çıkarıldığında
karnede/oda.json'da açık pozisyonları yoktu. Yeni araştırmalarda da bu hisseleri dışla.

## Tahtacı (şişir-çak) uyarısı — `sinyal.tahta_riski`
Olay çalışması (2022-26, tüm hisseler, bölünme düzeltmeli): 20 günde ≥%25 çakılma taban oranı %2,3. 🎈 şişme
(10g ≥5 tavan %19 / 20g ≥%100 %15 / 50g ort +%70 ve 20g std ≥%6 %16 / ≥3 tavan + hacim 5g/60g ≥3x %19) ve ⚠️ dağıtım
(hacim 5g/60g >2x iken 10g zirvenin %8+ altı, %9,5). Küçük tahta (düşük TL hacim) tek başına risk artırmıyor.
v3 girişlerinin sadece 1/417'si uyarılı günde (şablon + oynaklık filtresi zaten eliyor) → 🎈'de AL mesajı gitmez.
'Dipten kaldırma' tahmin edilemedi: tepeden %50+ çöken 75 olayda 60 gün sonrası −%65…+%189, hacim artışı ayırmıyor.
Pano rozeti + modal kutusu, portföy özetinde not. (scratchpad bt/tahta1.py)

## 🪤 Düşen trend kırılımı tuzağı — `sinyal.trend_tuzagi` (kullanıcının 'tahtacı' tarifi)
Düşük seviyedeki hisse (120g zirvesinin ≥%25 altı, < SMA50) iki tepeden çizilen düşen trendi ≥%4 yükselişle kırınca
küçük yatırımcı 'AL' okur. Tüm borsa (KAP'tan 586 hisse, 2022-26, 1.209 olay; bt/tahta2-3.py): %56'sı 15 günde kırılım
kapanışının %5+ altına döndü, %29'u +%20'ye ulaştı. Kırılımda alıp 60 gün tutmak aynı hisselerde rastgele günden kötü
(ort +%12,9 / medyan +%2 vs +%16 / +%3,7). Hacim, fitil, piyasa, hisse büyüklüğü tuzağı ayırmıyor (%55-68). Tuzak
sonrası 'dipten topla' sadece geriye bakınca iyi; gerçekçi limit emirle (kırılımın %5-15 altı) avantaj yok. → Sadece
uyarı rozeti (son 5 gün), sinyal değil. Canlı fonksiyon olayları birebir buluyor (150/150).

## Güç puanı, ayın güçlüleri, küçük hisseler, işaret sözlüğü (2026-09-26)
- 💪 Güç (`sinyal.guc_puani`, 0-7): şablon, Ichimoku (bulut üstü + tenkan>kijun), 55g zirveye ≤%3, CMF>0.05, ADX>25 & +DI>-DI,
  EMA10>EMA30, RSI>50. Test (bt/guc1.py; 125 ve 586 hisse): sonraki 20 günde endekse göre getiri puanla artıyor (iki faiz
  döneminde); 60 günde düşük faizde ters; v3 girişlerini seçmiyor → tablo sütunu + modal, Telegram'a GİRMEZ.
- 📈 Ayın güçlüleri (`tarama.momentum_listesi`): 6 ay getiri (son ay hariç) ilk %20, fiyat > SMA200, SADECE BIST100+EK
  (küçük hisseler dahil edilince tepeye +%1000-2000 şişirilmiş hisseler çıkıyordu). `durum.json` → `mom_ay`;
  ayın ilk kesin kapanış taramasında Telegram listesi (ilk çalışma sessiz). Bilgi; gece testi: v3 ile yarı yarıya iyi.
- `KUCUK_HISSELER`: BIST100/EK dışı, 60g medyan işlem ≥ 50 mn TL (163 hisse, KAP kod listesi) — tahtacı uyarıları görünsün diye.
- Pano altında 'İşaretler ne demek?' sözlüğü (tüm rozetler tek yerde); eski tekrar eden 3 açıklama kartı kaldırıldı.

## 📈 RS puanı · 📊 bilanço tepkisi · 🧾 zarardaki şirket (2026-10-20, dal `pano-bilgi`; hepsi BİLGİ — AL/SAT, Telegram, İşlem Odası DEĞİŞMEZ)
Kaynak araştırmalar scratchpad `ucretli/RAPOR.md` (RS) ve `strateji2/RAPOR.md` (bilanço tepkisi, zarar); testler `panobilgi/`.
- **RS (0-99), `sinyal.rs_puanlari` → `s["rs"]` (tam sayı, `rs_tam`):** ham = 0,4·r63 + 0,2·r126 + 0,2·r189 + 0,2·r252; takvim = tüm taranan
  hisselerin + XU100'ün günleri, seriler takvimde ileri doldurulur, n gün = n TAKVİM günü geriye; son gün kapanışı olmayan / <252 gün geçmişli
  hisse puanlanmaz ve sıraya girmez; RS = evren (taranan tüm hisseler, `KODLAR`) içinde `rank(pct=True)·99`. `ucretli/hazirla.ibd_rs()` ile
  birebir: 10y 286 hisse, 2.282 günün HER günü (439.879 hisse-gün) 0 fark; canlıdaki gibi kesilmiş veri + o veriyle bölünme düzeltmesi 17.488
  hisse-gün 0 fark (`t1_rs.py`). Pano: tablo 'RS' sütunu (Güç'ten sonra, sıralanabilir, ≥80 yeşil), 🚀 kutusunda 'RS 85 — son 1 yılda …
  hisselerin %85'inden güçlü' (JS `rsEk`: Türkçe ek) + araştırma notu (RS ≥80 🚀 alımları ort. +%30, diğerleri +%19; filtre değil).
- **📊 Bilanço tepkisi, `sinyal.bilanco_tepkisi` / `bt_olaylar` → `s["bt"]` (SADECE ana liste BIST100 + EK):** j = KAP'taki ilk 'Finansal
  Rapor' yayınının tepki günü (`bt_gun`: 18:00 öncesi ve işlem günüyse o gün, değilse sonraki işlem günü; takvim = XU100 ∪ hisse);
  tepki = K[j+1]/K[j−1] − XU[j+1]/XU[j−1] (j−1, j, j+1 kapanışı olmalı; hisse j'de ≥200 günlük geçmişli); ≥ +%5 güçlü ('g'), ≤ −%5 zayıf
  ('z'), arası 'n'. j+1'den sonra 60 işlem günü görünür (araştırmadaki `ffill(limit=60)`); birden çoksa en son olay. j+1 kesin kapanışı yoksa
  (seans içinde j+1 = bugün dahil) tepki yok, `b` = bekleyen yayın (≤7 takvim günü). Alanlar: y (yayın), d ('2Ç26'), j, j1, r (%), s, g
  (j+1'den beri gün), b. Tablo rozeti sadece g/z ('📊 güçlü/zayıf tepki', `pano.BT_NOT` başlıkta), pencerede `btHtml` kutusu (bilanço kutusunun
  üstünde; normal tepki ve 'bekleniyor' da yazar), `modalOzet`'te rozet. **Metindeki oranlar canlı tanımla yeniden ölçüldü** (`t2_bt.py`, ana
  liste 2017-26, KAP tarihli 3.483 olay, alış j+2 açılış → j+61 kapanış, BIST 100'e göre): güçlü %56 endeksi geçti (ort. +7,8 puan), normal
  %49, zayıf %46; küçüklerde sıra yok (%49/%50/%46). Kullanıcıya önerilen metindeki '%53 / %47' strateji2 RAPOR'unun eski (≥200 gün
  düzeltmesinden önceki, ±3/±8 dilimli) tablosundandı — sayılar `BT_NOT`'ta (Python) ve JS `BT_NOT`'ta aynı (test). Doğrulama: strateji2 olay
  çalışması ile 7.130 olayda tepki 0 fark; 3 olayda (ISGSY 2018-19, 1 Mayıs / 29 Ekim tatilleri) strateji2 tepki gününü başka hissenin tatil
  satırına koymuştu (birleşik takvim) → canlı doğru işlem gününü alıyor. 60 gün görünürlüğü kesilmiş veriyle 32.465 hisse-günde son_ear ile 0 fark.
- **KAP 'Finansal Rapor' takibi (`kap.py`):** mevcut 7 günlük FR sorgusundan konu tam 'Finansal Rapor' olanlar (kod, yıl, dönem 1-4, yayın)
  `kap.json` → `fr` = {kod: [[yıl, dönem, ilk yayın]]}; her (kod, yıl, dönem) için EN ERKEN yayın (`fr_birlestir`), 400 gün (`FR_SAKLA_GUN`;
  düzeltilmiş raporun yeniden yayını 'ilk' sayılmasın). İlk kurulumda geçmiş her taramada 4 × 15 günlük ek sorguyla (1 sn arayla, 2000
  sınırında ikiye bölünür) ~7 taramada dolar (`fr_bas`/`fr_son`); taramalar 7 günden uzun kesilirse geçmiş yeniden doldurulur. Dolmadan
  (`tam` false) 📊 gösterilmez. `kap_guncelle` artık 3'lü döner (hisse, yeni, fr). kap.json ~258 → ~294 KB. Yeni veri dosyası/workflow yok.
- **🧾 Zarardaki şirket, `bilanco.zarar_guncelle` → `s["zr"]` = dönem adı (son 4 çeyrek ana ortaklık net kârı ≤ 0):** kaynak İş Yatırım
  MaliTablo (strateji2 ile aynı kalem '3Z'; banka/finans UFRS). Yahoo (bilanco.json `veri`) YETERSİZ çıktı: 2Ç26'da 274 hissenin 96'sında son
  4 çeyrek ardışık değil, PGSUS ve ADESE'de zarar işareti ters. Dönem KAP'tan (`kap.fr_son_donem`); hisse başına TEK istek (bu dönem kümülatif,
  geçen yıl 12 ay, geçen yıl aynı dönem → `isy_ttm`; strateji2'nin 8.698 çeyreğinin 8.562'sinde değer aynı, zarar işareti 9'unda farklı: strateji2
  eksik çeyrekte ardışık olmayan 4 satırı topluyordu; canlı 30 hissede strateji2 ile 30/30 aynı). Önbellek `bilanco.json` → `isy` = {kod: {g,
  p: [yıl, dönem], n, t, a}}; sadece YENİ dönem yayınlanınca ya da 45 günde bir çekilir, hata/boş sonuçta o gün tekrar denenmez (`a`). Süre
  sınırı seans içi 8 sn, seans dışı 30 sn (İş Yatırım 0,1-8 sn/istek, ort. ~1,7; zaman aşımı (4, 10) sn; hata → o taramada dur). İlk kurulum
  (~320 hisse, önce ana liste) ~1-2 günde dolar; veri yoksa not çıkmaz. `bilancolari_al` artık dosyadaki diğer anahtarları (isy) korur.
  Not SADECE panoda: 🚀 kutusunda 'Son 4 çeyrekte zarar … ort. +%17, kârlılarda +%23; filtre değil' (Telegram AL satırına girmez).
- **Gizlilik:** durum.json/oda.json'a yeni anahtar yok; kap.json/bilanco.json'daki veriler herkese açık KAP/İş Yatırım verisi.
- **Ölçümler (Telegram'sız kopya, seans içi):** kararlı durumda tarama ~42 sn önce/sonra aynı (42,7/41,5 → 42,4/42,3); ilk kurulum taramaları
  +~10 sn (KAP geçmişi + İş Yatırım 8 sn). index.html 3.535 → 3.586 KB (+51 KB, %1,4; RS hücreleri, 121 ana hissenin `bt`'si, 114 `zr`).
  backtest.py aynı veriyle backtest.html byte byte aynı; kapanış yolu (oda + Telegram) çalıştı, durum.json aynı, oda kararları aynı (Telegram
  farkı sadece iki çalıştırma arası fiyat oynaması). `node --check` tamam; CDP 390/1280 px (tablo, BIMAS güçlü, ENJSA zayıf, GMTAS zarar+🚀,
  GLYHO normal + yapay 'bekleniyor', EKDMR RS yok, sözlük): JS hatası yok, sayfa taşması yok, 📊 rozet sayısı = DATA (43/43), RS hücresi =
  DATA (316/316). Birim testleri `t4_birim.py` 29/29 (bekleme, 60/61. gün, 18:00, hafta sonu, KAP doldurma/kesinti/erişilemez, İş Yatırım bütçe/hata).

## Veri kalitesi: Yahoo günlük kapanışı yanlış / boş
Yahoo'nun BIST günlük barlarında kapanış çoğu zaman resmi kapanıştan farklı (Eylül 2026: günlerin ~%30'unda >%0,3; THYAO
24.09 günlük 288,5, resmi 289,5) ve son günün kapanışı NaN geliyor (dropna ile önceki gün gösteriliyordu: THYAO 288,5 vs
gerçek 290,75). Saatlik verinin gün sonu = resmi kapanış (fast_info.previous_close ile 16/16). `veri_cek`: son 3 günün
kapanışı gün içi veriden (2026-10'dan beri 15 dk'lık: 326 hissede 1.956 gün sonu kapanışı saatlikle birebir aynı; 15 dk alınamazsa
eski saatlik indirmeye düşer); kesin kapanış (18:30+/hafta sonu) sonrası son gün `fast_info.last_price` (kapanış seansı, 12 iş
parçacığı, ~10 sn). Günlük–saatlik farkı >%2 ise (temettü düzeltmesi) dokunulmaz. Eski backtest verisindeki bu küçük
rastgele hatalar (~%0,3) sonuçları yönlü etkilemez.

## Veri kalitesi: kaydedilmemiş bedelsiz/bölünme
yfinance BIST bölünmelerini çoğu zaman kaydetmiyor (5 yılda 125 hissede 12 olay: KONTR, FENER×3, CCOLA, HEKTS, TUKAS,
BSOKE, EUREN, CVKMD...). BIST günlük sınırı ±%10 olduğundan tek gün ≤−%25 / ≥+%35 kapanış değişimi bölünme sayılır:
`sinyal.bolunme_duzelt` önceki fiyatları düzeltir (analiz_et, backtest, karar çizgisi). Aksi halde göstergeler, iz stop
ve 'çöken hisse' sınıflaması bozulur, bedelsiz günü yanlış 'iz stop kırıldı' gelir. Düzeltilmiş veriyle v3/v2 kıyası
değişmedi. Son 30 günde bölünme olan portföy hissesinde 'maliyetini güncelle' notu (kullanıcının maliyeti eski fiyatla).

## Klasik grafik formasyonları — TEST EDİLDİ, EKLENMEDİ (2026-09-29)
3 paralel araştırma (125 + 586 hisse, 2022-09 → 2026-09, iki faiz dönemi, çökenler hariç; pivotlar `_pivotlar` ile, look-ahead
yok; aynı hisse/dönem/SMA200 trendindeki rastgele günlerle kıyas; sepet/portföy simülasyonu; parametre komşuları). Scriptler:
scratchpad `bt/formasyon/` (dip_ortak + dip1-5, tepe_ortak + tepe1-5, devam_ortak + devam1-4). Sonuç: **11 formasyonun hiçbiri
sinyal, filtre, etiket ya da çıkış olarak eklenmeye değmez.** Kullanıcı formasyon sorarsa bu sonucu anlat, baştan araştırma.
- **Dip (W, TOBO, üçlü dip) — yeni AL olarak:** rastgele günden ayrılmıyor (20g ±2 puan); hedef tutma taban oranıyla aynı
  (~%50). TOBO sadece 586'da zayıf + (60g rastgeleye göre +6/+4), 125'te yok; 60 gün tut sepeti rastgele günlerin aralığında
  (yüksek faiz +%195 vs rastgele 165..195), düşüşü daha derin. %45-67'si 15 günde tetik kapanışının %5+ altına indi (🪤 ile aynı tablo).
- **Tepe (OBO, ikili, üçlü tepe) — v3 çıkışı olarak:** %20 iz stop'u tutarlı yenmiyor. OBO çıkışı işlemlerin %67-86'sında iz
  stop'tan iyi ama büyük kazananları kesiyor (yüksek faizde ort. −5…−11 puan); sepet farkı komşu ayarlarda işaret değiştiriyor
  (586 yüksek faiz −25…0). Uyarı olarak: OBO/ikili sonrası 20g ~−1 puan göreli zayıflık, 60g kayboluyor; iz stop'a inme
  olasılığını artırmıyor, sadece biraz öne çekiyor. ("Erken çıkış yükselişte kazancı eritir" bulgusunun tekrarı.)
- **Devam (fincan-kulp, yükselen/simetrik üçgen, VCP, yatay kanal) — v3'e katkı:** olayların çoğu zaten v3 kırılımıyla aynı gün;
  formasyon etiketli v3 işlemleri etiketsizlerden 4 kıyasın 4'ünde KÖTÜ (586: +3,7 vs +8,0 / +1,2 vs +4,4) → etiket bile yanıltıcı.
  VCP'nin tek iyi sonucu (586, yüksek faiz sepet +311 vs v3 +239) en iyi 10 işlem çıkınca kayboluyor (197 vs 206), 125'te ve düşük
  faizde geride; komşu ayarlar dağınık. Bayrak (`bayrak_kirilimi`) ile aynı tablo: bilgiyi v3 şablonu zaten taşıyor.

## v3 — 🚀 trend kırılımı (2026-09 gece araştırması, canlı AL kuralı)
- AL mesajı artık gösterge oylamasından (SINYAL) DEĞİL: `sinyal.trend_kirilimi` — Minervini trend şablonu (fiyat > SMA50 >
  SMA150 > SMA200, SMA200 20 günde yükselmiş, 52h zirvesinin ≥%75'i, 52h dibinin ≥%30 üstü) iken önceki 20 günün en yüksek
  kapanışının ilk kez aşılması + XU100 > SMA50 + 60g oynaklık ≤ %5. Çıkış: girişten beri tepe kapanışın %20 altı (iz stop). **2026-10-19'dan beri + 🔐 kâr kilidi** (aşağıda).
  Pozisyon açıkken yeni kırılım sayılmaz. Canlı fonksiyon backtest işlemlerini birebir üretir (124 hisse, 467 işlem, 0 fark).
- Neden: 13 gösterge/strateji aynı düzenekle (sınırsız sepet, 3 evren × 2 faiz dönemi, 2022-09-26'dan) kıyaslandı
  (scratchpad bt/gece12-14). Minervini 6 hücrenin 6'sında v2'den iyi (çökenler hariç düşük/yüksek faiz +%83/+%263 vs
  +%73/+%215); komşu ayarlar (0.70-0.80, 1.2-1.5, 10-40g kırılım) neredeyse aynı; 200 rastgele yarım listede v2'yi
  %77-97, XU100'ü %88-100 yeniyor. Düşük faizde işlem isabeti %74 (v2 %47). backtest.py'de "düşük faiz" satırında v2
  işlem başı önde görünür: v3 250 günlük ısınma yüzünden Tem-Eyl 2022 rallisini kaçırıyor (adil değil).
- Örneklem dışı (2016-2021, 85 bugünkü hisse — hayatta kalan yanlılığı ikisine de eşit): sınırsız sepette v3 ≈ v2
  (+%46/+%50, +%232/+%232), 10 yuvalı portföyde v3 4 kıyasın 3'ünde önde (+%80 vs +%32, +%232 vs +%205); ikisi de
  BIST100'ü (+%29/+%109) yeniyor, eski canlı kurallar en kötü. v3 üstünlüğü son 4 yılda belirgin, eski dönemde küçük.
- Pratik: sınırsız sepette aynı anda ~35-45 pozisyon; 10 eşit yuva (dolunca atla) sonuçları çok bozmuyor.
- Aylık momentum rotasyonu (6 ay, üst %20): yüksek faizde çok güçlü, düşük faizde XU100 gerisinde; v3 ile yarı
  yarıya 4 yılda +%717 / maks düşüş −%21 (v3 +%562 / −%25) — uygulanmadı, kullanıcıya seçenek.
- Denenip v3'ten zayıf kalanlar: 55/100/250g zirve kırılımı, ADX/DI, Bollinger sıkışma, OBV, CMF, RSI 50, EMA10/30
  (yüksek faizde iyi, düşükte zayıf), Ichimoku (iyi ama Minervini'den geride), v2 VEYA Minervini birleşimi.
- Telegram: 17:30+ kırılımlar (`tk_gonderilen`, günde bir kez), 18:30 sonrası kapanışta tutmayan için "↩️ iptal".
  SINYAL AL'i artık mesaj değil (panoda gösterge bilgisi); SAT portföy bilgisi. Karne (gecmis.json, "kural": "v3")
  sadece kesin kapanışta kayıt açar. Portföy iz stop'u: en son giriş v3 kırılımıysa ondan (`analiz_et` iz override).
- Geç giriş (çökenler hariç, 2022-26): sinyalden 0/5/10/20/40 gün sonra (pozisyon hâlâ açıksa) girince ort +%20/+%19/
  +%18/+%15/+%8, isabet %52/51/50/47/35 → panoda ≤5 gün '🚀 AL Ng önce', sonrası 'trendde · Ng' (yeni alım değil).
- Pano: 🚀 KIRILIM (bugün) / 🚀 Ng (pozisyon) / 👀 kırılıma %x (şablonda, ≤%3) rozetleri; modalda tkHtml kutusu.
- **Veri penceresi (2026-10-19'dan beri 4 yıl, `tarama.VERI_DONEM`):** v3 zincirli durum makinesi (pozisyon açıkken yeni AL yok) +
  250 gün ısınma. Eskiden 2 yıl iniyordu → ilk yıl görünmüyor, daha önceden açık pozisyonlar grafikte/Sinyal geçmişinde 'hayalet'
  🚀 AL olarak çıkıyordu (denetim: son 1 yılda 41 fazladan + 78 eksik/farklı işlem, 77 hisse; TAVHL gerçek giriş 17.03.2025 sinyal /
  263,02 → grafikte 09.12.2025 287,45; GLYHO 03.03.2025 5,90 → 31.10.2025 11,67; ASELS 2024-04 → 2025-12). Ölçüm (scratchpad
  `veripencere/` p1-p6, 286 hisse, 10 yıllık veri = doğru kabul, grafikte görünen son 1 yıl: sinyali ya da çıkışı 16.10.2025+ veya açık):
  2y 41 hayalet / 78 eksik, 3y 3/3 (ASELS, ENKAI, ISKPL — 2+ yıl açık kalan pozisyonlar), **4y ve 5y 0 fark** (352/352); 4y'de açık
  pozisyonlar, iz stop, `tkg`, grafik `spark.tk/iz`, 🌱 durumu da 10y ile aynı — kalan farklar sadece 2,5+ yıl önce kapanmış işlemler
  (9 hissede `tk.durum` CIKTI 2022-23 ↔ yok, OTKAR'ın 2023 girişi, HEKTS 🌱 SAT 2023 ↔ yok) ve eski bölünme tarihi (`bolunme`).
  Diğer tüm `analiz_et` alanları (gösterge oyları, RSI/ADX/SuperTrend, güç puanı, vadeler, destek/direnç, hacim, 🔒, 🎈, 📏, 6A/1Y grafik
  serileri) 2y ile aynı (EWM ısınması 2 yılda zaten oturmuş). 2y → 4y geçişte değişenler: 4 açık pozisyonun giriş tarihi/fiyatı
  (BIMAS, GLYHO, RGYAS, TRGYO; iz stop aynı), 23 hissede son işlemin girişi, 51 hissede 'son 🚀 çıkış' bilgisi (2y'de yoktu), 21 hissede
  🌱 tarihi/durumu (16'sı yok → eski SAT; Telegram'a mesaj gitmez: `uv_son`'da önceki yoksa sessiz), EREGL/GSDDE/ULUUN grafik iz stop
  çizgisi. İşlem Odası `ozet_hazirla`: sadece `tk.durum` None→CIKTI (51) ve `uv.durum` None→SAT (16) — robot kararlarını değiştirmez
  (🌱 robotu elindeki hissede SAT'a bakar; o hisselerde durum aynı). Sayfa büyümesin diye: `tkg` sadece çıkışı son 2 yılda olan ya da
  açık işlemler (`sinyal.TKG_YIL`; 4y = 10y ile 0 fark), `spark.tk` pencerede işaret yoksa yazılmaz, `endeks_serisi` günlük kısmı
  yine son 2 yıl (`ENDEKS_GUNLUK_YIL`) → index.html 3.510 → 3.518 KB (+8 KB, %0,2; artış `tkg`/`tk`'deki doğru eski işlemler).
  Süre: yerel ölçümde indirme 2y ~5,8 sn → 4y ~6,2 sn, analiz ~6,0 → ~6,5 sn; Telegram'sız tam
  tarama.py (seans içi, 2'şer tur) 42-44 sn → 46-47 sn (~+3 sn, ~%7) → önbellek gerekmedi.
  Workflow değişmedi (fork'lar *.py ile otomatik alır). backtest.py (5y) ve oda_replay (5y + ısınma) ayrı indirir, etkilenmedi.
  **🔐 Kâr kilidiyle yeniden ölçüldü** (birleştirme 2026-10-19, scratchpad `birlesik/vp/`; canlı v3 artık kâr kilitli, aşağıdaki bölüm):
  son 1 yılın işlemleri 2y'de 49 hayalet / 68 eksik, 3y'de 1/1, **4y ve 5y'de 0 fark (401/401)**; `tkg` (son 2 yıl süzgeci) 4y = 10y 0 fark;
  açık pozisyonlar, iz stop (kilit seviyesi dahil) ve 🌱 aynı; kalan farklar yine 2+ yıl önce kapanmış işlemler (9 hissede `tk.durum`
  CIKTI ↔ yok, OTKAR, HEKTS 🌱) ve `bolunme`. Kilit zinciri kısaltır (erken çıkış): 10y'de en uzun tutuş 891 işlem günü (ANSGR
  2017-20, kilitsizle aynı), şu an açık en uzun 406 gün (GLYHO 03.03.2025) → 4 yıl yetiyor; ~3 yılı aşan tek pozisyon çıkarsa 4y'de fark doğabilir.

## 🔐 Kâr kilidi — v3 çıkışına ek (2026-10-19, dal `kar-kilidi`; scratchpad `cikis2/`, `finalcikis/`, `karkilidi/`)
- **Kural:** v3 girişi aynen; çıkış %20 iz stop (girişten beri tepe kapanış × 0,80) AYNEN, ama kapanışta en az bir kez giriş fiyatının
  ≥ +%8 üstü görüldüyse stop = max(tepe × 0,80, giriş × 1,05) (kilit bir kez açılınca kalıcı; tepe düşmez). Giriş = sinyalin ertesi
  açılışı, tepe başlangıcı = giriş, kapanış < stop → o kapanışta sat (kilitli tabanda `gercekci_cikis` aynen). Ayar TEK yerde:
  `sinyal.KAR_KILIT_ESIK = 0.08` ('A4'), `KAR_KILIT_SEVIYE = 0.05`; 'A1' = eşik 0.10; `KAR_KILIT_ESIK = 0` → eski v3 (kilitsiz).
  Metin sayıları `KAR_KILIT_ARASTIRMA`'dan (ayar değişirse eşleşen satır yoksa sayı yazılmaz; JS `KK` = [eşik %, seviye %] | null).
- **Araştırma (Ekim 2017 → 16.10.2026, 286 hisse: ana 123 + küçük 163; 200 rastgele yarım liste, 10 yuva, iki 'dengeli puan' tanımı):**
  ~400 kural (iz %10-30, kademeli iz, chandelier/ATR merdiveni, ilk zarar stopu, başarısız kırılım, zaman stopu, SMA/EMA/kijun, kısmi
  kâr, giriş filtreleri: uzama, geri test, hacim, piyasa, RS, yeniden giriş yasağı). Kâr kilidi içeren kurallar açık ara önde; A4 dengeli
  puanda 1. (iki tanımda da ilk 3), 2018-26'da ana 9/9, küçük 9/9 yıl v3'ten iyi; 2017-21'de seçilen ayar 2022-26'da da tutuyor (ve
  tersi); +%6-12 eşik / +%3-7 kilit geniş plato. İsabet %52 → %72 (ana) / %51 → %68 (küçük); kârdan zarara dönen işlem %22 → %4-6;
  tepeden geri verme %22 → %17; 10 yuva portföy kârı v3'ün %140 / %122'si; son 12 ayda (ana) isabet %28 → %63. ATR×3 merdiveni tek
  başına v3'ten belirgin iyi değil (isabet artmıyor, sepet %64-89, GLYHO'da büyük trendi kaçırıyor) → eklenmedi. Girişe filtre: fayda yok.
- **Bedeller (kullanıcıya açık söylendi):** her işleme eşit para koyan sınırsız sepette toplam kâr v3'ün %91 / %88'i (A1: %95 / %91) →
  **sepet kârı ~%5-15 düşer**; işlem başı ortalama +%30 → +%21 (backtest.py 10y: endekse göre +18,1 → +12,7 puan); **kilitle
  kapananların ~%23'ü (A1 %20) eski kuralla +%30'un üstünde biterdi** (büyük yükselişin başında +%5'te satış); işlem sayısı +%28;
  'satıp daha yukarıdan yeniden alım' %39 → %48; 2024 gibi kesintisiz yükselen yılda v3'ten az (ana +44 vs +58); 20 yuvada ana %90.
  İsabet artışı mekanik (rastgele hisseye aynı çıkış da ~%70 isabet) — 'daha iyi hisse seçimi' değil. TAVHL 334 → 268 değişmez (+%8
  hiç görülmedi); RYSAS 27,1 → 28,24 (+%4, eskiden 23,8), RYSAS 14 → 13,86 (−%1, eskiden 12,23), ALARK 103,2 → 106,6 (+%3, eskiden 86,8).
- **Kod (stop seviyesi TEK fonksiyonda):** `sinyal.iz_seviye(giris, tepe, kk)` → (stop, kilit) — ATR merdiveni ya da başka bileşen
  eklenecekse buraya bir max() daha; `iz_yuru` pozisyonu gün gün yürütür (`izs` = her günün stop'u, `kk_i`, `kk_cik`); `trend_kirilimi(...,
  kar_kilit=None|False|(eşik, seviye))`. Açık/kapanmış `tk`'ye `iz20`, `kk`, `kilit`, `kilit_seviye`, `kilit_esik_fiyat`, `kilit_tarih`,
  `kilit_cik` eklendi (analiz_et `iz` override'ına da). `tkg` 5. eleman artık BİT alanı: 1 = çıkış günü kilitli taban, 2 = 🔐 kâr kilidiyle
  çıkış, 4 = açık + kilit devrede. `spark.tk`'de 'K' = 🔐 çıkışı; `spark.iz` parçası [başlangıç, değerler(, kilidin devreye girdiği parça içi
  sıra)] — **çizgi değerleri Python'dan hazır gelir, JS hesaplamaz** (kural değişince pano kodu değişmez).
- **Nerelere girdi:** canlı 🚀 AL/SAT (AL sinyalleri de değişir: erken çıkıştan sonra yeni kırılım sayılır), grafik ▼ SAT (kilitle
  çıkışta 'SAT 🔐'), mor iz stop çizgisi (kilit devredeyse en az giriş × 1,05; devreye girdiği gün çizgi üstünde küçük 🔐; fare bilgisinde
  'İz stop X 🔐'), `tkSonHtml`, Sinyal geçmişi ('🔐 kâr kilidiyle çıktı'), Son roketler, `tkHtml`, `pozHtml`/`pozPlan` (`izNeden`),
  `sadeHtml`, sözlük + 'Sistemi nasıl kullanırım?' / 'Grafik nasıl okunur?' / 'Çıkış ve hedef' (yer tutucular `__KKSOZ__`, `__KKCUMLE__`,
  `__KKGRAFIK__`, `pano.kk_metinleri`), Telegram (`tarama.kk_metni`, `iz_aciklama`: AL satırı, portföy planı, '🔐 kâr kilidi
  seviyesinin altında' SAT başlığı), backtest.py (`v3` = kilitli; `v3_eski` = 'v3 (eski, kilitsiz)' kıyas kartı + dönem satırı + not;
  sebep '🔐 kâr kilidi', `kar_kilidi` sayısı).
- **Karne (gecmis.json) İLERİYE DÖNÜK:** geçmiş kayıtlar yeniden yazılmadı. Kural açıkken açılan yeni kayıtlar `kar_kilit` = [eşik,
  seviye] taşır; sadece KESİN kapanış taramasında fiyat ≥ kayıt fiyatı × 1,08 görülünce `kk` = o gün yazılır (gün içi fiyat saymaz), stop
  `iz_seviye` ile; sebep '🔐 kâr kilidi'. Bu alanı olmayan kayıtlar (o an açık olanlar dahil) eski %20 iz stop'la kapanır. gecmis.html
  notunda (`__KKKARNE__`) ve tabloda 🔐. (Karnenin giriş fiyatı kendi tanımı: sinyal günü kapanışı.)
- **İşlem Odası ETKİLENMEZ:** robotlar kilitsiz v3 ile araştırıldı. `analiz_et` → `tk_oda` (= `trend_kirilimi(kar_kilit=False)`);
  tarama oda'ya `tk` yerine `tk_oda`'yı geçirir (canlı kilitli `tk` → `tk_kk`); `oda_replay.ozellik` `kar_kilit=False`. Odadaki 🔐 robot
  (`kilitli_kirilimci`, İşlem Odası bölümündeki '💪 güç robotları + 🔐' maddesi) aynı A4 kuralını (+%8 → alış +%5) `oda.robot_karar` içinde
  kendi pozisyonuna uygular; girdisi yine kilitsiz `tk` (giriş sinyalleri Kırılımcı'yla aynı). 2026-10-20'den beri aynı kilit
  ☁️🔐 Bulutçu (iz stop'suz), 📐🔐 Şabloncu ve 🪜 Weinstein robotlarında da ('ÇIKIŞ DENEMESİ' köşesi); 2026-10-20'den beri 🔐📉 Daralan iz
  robotunda kilit + kâr büyüdükçe daralan iz ('K2', İşlem Odası bölümü).
- **Bilinen:** portföy iz stop'u son giriş v3 DEĞİLSE (gösterge AL'i daha yeni) eski gösterge iz'i (kilitsiz) — değişmedi.
- **Doğrulama (scratchpad `karkilidi/`):** canlı `trend_kirilimi` + `gercekci_cikis` = `finalcikis/motor2.py` işlem işlem, 10y 286 hisse:
  A4 2.280 / A1 2.096 / kilitsiz 1.783 işlem, **0 fark** (A4'te 982 kâr kilidi çıkışı; `cikis2/motor.py` A1 ile de 0 fark) (`t1_motor2.py`).
  `KAR_KILIT_ESIK = 0` iken `analiz_et` çıktısı main'deki eski kodla 286 hissede (2y ve 10y) tüm alanlarda birebir; kilit açıkken `tk_oda`
  = eski `tk`, `oda_replay.ozellik` 27 alanın hepsi 286 hissede eski kodla aynı (`t3_esit.py`, `t4_oda.py`). Örnekler `t2_ornek.py`, karne
  `t6_karne.py`, Telegram `t7_telegram.py`, backtest `t5_backtest.py`. Gerçek tarama (Telegram'sız kopya) → index.html: `node --check`
  tamam; headless Chrome CDP 390/1280 px (RYSAS, GLYHO, ALARK + sahte portföy + Son roketler): JS hatası yok, yatay taşma yok (`cdp_test.mjs`).
- **Birleştirme (2026-10-19, dal `birlesik-deneme` = `veri-pencere` + `kar-kilidi` + `guc-robot`; scratchpad `birlesik/`):** testler
  birleşik kodda yeniden: motor2 10y A4 2.280 / A1 2.096 / kilitsiz 1.783 işlem 0 fark (`a1_motor2.py`); kilit kapalıyken `analiz_et`
  = main 286 hissede 10y ve 4y veriyle birebir (beklenen farklar normalize: yeni `gh`/`tk_oda` anahtarları, `tkg` son 2 yıl süzgeci,
  boş `spark.tk` yazılmaması; `a2_esit.py`), kilit açıkken `tk_oda` = main `tk`; veri penceresi yukarıda; oda: `oda_oynat` = `calistir`
  20/20, yeniden üretilen oda_replay.json `guc-robot` dalındakiyle birebir (sadece `uretim` saati), eski 14 robot main'le aynı, canlı
  `canli_calistir` (tarama'nın `tk_oda` eşlemesiyle) `guc-robot` dalının çıktısıyla birebir. Telegram'sız tarama (gün içi + kapanış
  yolu), backtest.py, index/oda.html CDP 390/1280 (RYSAS, ALARK, GLYHO, TAVHL; oda canlı + tekrar oynatma) hatasız. Süre gün içi
  ~25,8 → ~27,6 sn (yerel, 3'er ölçüm), index.html 3.477 → 3.520 KB (gzip 588 → 603 KB).

## 🚀 Sinyal geçmişi · son AL/SAT grafikte · Son roketler filtresi (2026-10, hepsi BİLGİ)
- `sinyal.tk_gecmis` → `tkg`: son 6 v3 işlemi `[sinyal günü, giriş (ertesi açılış), çıkış günü|null, çıkış kapanışı|null(, bit alanı: 1 = çıkış günü kilitli taban, 2 = 🔐 kâr kilidiyle çıkış, 4 = açık + kilit devrede)]`
  (canlı `trend_kirilimi(ham=True)`, yani 🔐 kâr kilitli v3; komisyonsuz; sadece çıkışı son 2 yılda olan ya da açık işlemler — `TKG_YIL`, bkz. 'Veri penceresi (4 yıl)'). Portföyden bağımsız. `tk.kisa` = veri <250 gün (yeni arz: sinyal çıkamaz).
- Modal grafik: ▲ AL (yeşil, 🚀 girişi) / ▼ SAT (kırmızı, iz stop çıkışı), mor kesikli iz stop; üstte `tkSonHtml` özet satırı;
  '6 ay / 1 yıl' düğmesi — 1 yılda grafik penceresinden önceki ~6 ay HAFTALIK kapanış (`spark.w0` pazartesi + `spark.w`, x ekseni
  tarihe göre), eski işlemlerin işaretleri `tkg`'den. Kullanılmayan `spark.sg` (eski oylama dizisi) kaldırıldı. Altta `tkGecmisHtml`
  tablosu (getiri, aynı günlerde BIST 100'e göre fark — XU sinyal günü kapanışından; 6 aydan eski işlemler ≈ işaretli).
- Tablo filtresi '🚀 Son roketler' (5/20/60 işlem günü, `roketListe/roketOzet/roketHtml`): kapananlar DAHİL (seçim yanlılığı),
  sinyal gününe göre yeniden eskiye, üstte özet (sayı, artıda, ort/medyan, endekse göre), 20+ gün geç giriş notu. 'Bugün ne var?'
  kartında kısayol. `tkGun` = rozetlerdeki `tk.gun` (spark.t sırası). Python aynası testte (scratchpad sg/py_roket.py): 0 fark.
- Araştırma (2026-10-08, 5y veri): son 60 işlem gününün 50 sinyalinin 5'i artıda (ort −%11,8, medyan −%14,9; BIST 100'e göre
  medyan −8,8 puan; 37'si iz stop'la kapandı) — Ağustos kümesi piyasa düşüşüne denk geldi; AHGAZ (+%36) en iyisiydi, genel değil.
  Tarihsel 30 gün ufku (1.033 işlem): ort +%13, medyan +%6, %59 artıda; 34 aylık kohortun 6'sında artıda oranı ≤%20 (2023-04,
  2023-09/10/11, 2024-07, 2025-01) → kötü kohortlar olağan dışı değil.

## 🔒 Kilitli taban · gerçekçi iz stop çıkışı · aşırı uzama notu (2026-10, scratchpad bt/korn: 587 hisse, 2021-10…2026-10)
- **🔒 `sinyal.kilitli_taban`** (olay serisi `kilitli_taban_seri`): dün ve bugün taban (kapanış ≤ −%9, `TABAN_GETIRI`), bugün **kilitli**
  (`kilitli_gun`: Yüksek−Düşük ≤ %0,15 × kapanış = gün boyu işlem neredeyse yok), ilk tabandan önceki 10 günde taban yok, XU100 iki
  gün de > −%4. Sonuç: 15 günde 4+ tabana uzama ~%60 (n=218; canlı liste %66; tüm ilk tabanlarda ~%9), yıllara göre %49-71, iki faiz
  döneminde tutarlı; bugünkü 'taban serisi' uyarısından ~2 gün önce. Canlı fonksiyon araştırma olaylarıyla birebir (228/228, 0 fark;
  araştırma ilk 130 günü almıyordu) ve son-gün fonksiyonu olay serisiyle 3.710 hisse-günde 0 fark (scratchpad kilit/t1, t4).
  **Bilinen kör nokta:** piyasa çöküş gününde (XU100 ≤ −%4) başlayan serileri kaçırır — 16.09.2026'da (XU −%5,5) başlayan OZATD, ALKLC,
  IEYHO, MANAS, TRHOL'de 🔒 hiç yanmadı. Çöküş günündeki kilitli olaylar tutarsız: Eylül 2026 öncesi 80 olayda kesinlik %5 (78'i 2023'te),
  2026'da 16/16 → koşul gevşetilmedi.
  Rozet 1-2 gün görünür (olay günü + ertesi gün hâlâ tabansa); 15 günde 4+ taban olunca `analiz_et` `kt`'yi boşaltır, 'taban serisi'
  öncelikli (çift gösterim yok). Eşik ±%9,5 gün içi 'taban' mesajıyla değil, araştırma ve taban serisiyle aynı −%9 (BIST taban fiyatı
  önceki kapanış × 0,90'ın fiyat adımına yuvarlanmışı ≈ −%9,5…−%10; −%9 hepsini yakalar, adım hesabı gerekmiyor).
  **Zamanlama:** seans içinde Yahoo'nun gün içi Yüksek/Düşük'ü o ana kadarki işlemler → tarama `kt.kesin` ekler (18:30+ ya da son bar
  bugünün değilse kesin); kesin değilse metinde 'gün içi veri, kapanışta kesinleşir'. Telegram: portföy hissesinde gün içi olay
  `kilitli` (olay günü, fiyat hâlâ günün dibinde / tabanda ve aralık ≤ %0,15; 'taban'/'sert'i bastırır, gizli anahtarla günde bir kez)
  + akşam portföy özetinde en başta not. 🔒 olan hisseden 🚀 AL mesajı gitmez (`_riskli`, taban serisi/🎈 gibi). durum.json'a yeni
  anahtar yok. Pano: tablo rozeti, modal kutusu (taban serisi kutusuyla birlikte en üstte), sade anlat uyarısı en üstte (🔒 > taban
  serisi > 🎈), 'Bugün ne var?' (`bugunUyari` ilk sırada), sözlük. Metin Python `tarama.kilit_metni` = JS `ktMetin` (810/810 eşleşme).
- **Gerçekçi iz stop çıkışı (`sinyal.gercekci_cikis`, backtest.py v3 varsayılanı):** iz stop kilitli taban gününde tetiklenirse o gün
  satılamaz; ilk kilitsiz günün açılışında çıkılır, veri biterken hâlâ kilitliyse son kapanışla değerlenir. Canlı liste (1.208 işlem):
  endekse göre +%18,4 → +%16,7 (en iyi 10 hariç +13,3 → +11,7), en kötü işlem −%27 → −%81 (TRHOL/IEYHO 18.09.2026). Katı varyant
  ('her taban günü satılamaz', `v3_taban`) +%13,6 / en kötü −%82; backtest.html'de duyarlılık tablosu (kapanış / kilitli / katı).
  backtest.py korn verisiyle s4_kart.txt'yi birebir tekrarladı. v2/eski kurallarda bu düzeltme yok (kıyas v3 aleyhine hafif eğik).
  `tk_gecmis` 5. eleman `1` = çıkış günü kilitli tabandı → Sinyal geçmişi / grafik üstü satır / Son roketler'de '🔒 tabanda alıcı
  yoktu, bu fiyattan satılamamış olabilir' (OZATD 18 Eyl 3.632,5).
- **Aşırı uzamış 🚀 girişi (`sinyal.asiri_uzama` → `tk.uzama`, BİLGİ notu, AL engellenmez):** sinyal günü fiyat 52h (250g) dibinin ≥5
  katı ya da 126 gün öncesinin ≥3 katı. s1_kuyruk (OR birleşimi, canlı liste, 'her taban satılamaz' çıkışıyla): bu grubun %13,3'ü
  %30+ kayıpla kapandı, diğerleri %1,3 (sadece kilitli taban satılamazsa %5,7 / %0,2; kapanış varsayımıyla ikisi de %0); en büyük
  %5 kazananın 6/60'ı bu grupta. Düşük faizde çok az olay. Portföyde filtre (hariç/yarım) hücreden hücreye işaret değiştiriyor →
  sadece not: modal tkHtml kutusu (pozisyon açıkken) + Telegram 🚀 AL satırı. Python `uzama_metni` = JS `uzamaMetin` (173/173).
- **Test edilip GEREKMİYOR çıkanlar (tekrar araştırma):** aşırı uzama FİLTRESİ (hariç/yarım pozisyon; sepet farkı −160…+24 puan,
  tutarsız); 🔻 hacim kuruması (taban + hacim <0,5x: düşük faizde endeksi yenme %51 — ayırmıyor; 1. gün hacim <0,25x kesinlik %18,5,
  taban oranı %7,3, olay az); 1. gün taban/1. gün kilitli uyarısı (kesinlik %22-30, yanlış alarm çok); KAP VBTS tedbiri (kesinlik
  %13 vs %9 taban oranı) ve pay bazında devre kesici bildirimi (%8,4 vs %9 — hiç ayırmıyor).
- Not (değiştirilmedi): canlı karne kaydı (`gecmis_guncelle`) sadece taban serisini dışlar; Telegram AL ise 🎈 şişme ve 🔒'yi de
  dışlar → karne, mesajı gitmeyen birkaç 🎈 girişini de sayabilir (v3 girişlerinin ~1/417'si 🎈'li günde).

## 📏 Sıkı çizgi · uyarlamalı çıkış araştırması (2026-10-09, scratchpad `cikis/`; kullanıcı onayıyla sadece BİLGİ notu)
- Soru: paralı bir indikatör OZATD'den (27.08 🚀, 16.09'dan taban serisi, iz stop çıkışı kilitli tabanda −%81) erken çıkardı mı? **Tek örnekten
  kural çıkarılmaz** — 587 hisse 2022-09…2026-10, sepet + 10 yuva, iki faiz dönemi, çökenler dahil/hariç, 200 rastgele yarım liste ile test edildi.
- Düz çıkış araçları (c13, ~60 araç: SuperTrend, PSAR, chandelier, kijun, EMA/SMA, Donchian, Heikin-Ashi, RSI uyumsuzluğu, sıkı iz %8-15, zaman...):
  **30'u OZATD'yi kurtarıyor ama bu 30'un hiçbiri genel testte v3'ü (iz %20) sepet hücrelerinin 3/4'ünde bile geçmiyor** (erken çıkış büyük
  kazananları kesiyor; genelde iyi olan keltner_alt OZATD'yi kurtarmıyor).
- Uyarlamalı (sadece aşırı uzamış pozisyonda sıkı araç, c5/c6): en sağlamı uzama/hic/kijun sepette çoğu hücrede biraz önde, ama canlı listenin
  10 yuvasında yüksek faiz/çökenler hariç geride (+%178 vs +%213), 2026 çökenler hariç −%11 vs −%8; en büyük kazananları kesiyor
  (RAYSG +%2.132 → +%122, KTLEV +%1.734 → +%324); kijun-altı ilk kapanıştan sonra (c12, 306 olay) 20 günde %5'inde 4+ taban, %11'inde %25+ düşüş ama %20'sinde %25+ yükseliş, 60 gün sonra %41'i satış fiyatının üstünde.
  → **Canlı kural YAPILMADI** (v3 AL/SAT, iz stop, backtest değişmedi); kullanıcı onayıyla bilgi notu.
- **`sinyal.siki_cizgi` → `tk.sc`** (sadece açık 🚀 pozisyonda, `trend_kirilimi` içinde; backtest/islemler/ham yolları etkilenmez): sinyal gününden
  bugüne herhangi bir gün `asiri_uzama` (52h dibinin ≥5 katı ya da 6 ayda ≥3 kat; araştırmanın en sağlam ailesi 'uzama/hic' = girişten beri)
  ise bugünkü **kijun** (26 günün en yüksek + en düşük ortası, bugün dahil) = `s`; `alt` = son 5 işlem gününde kijun altı kapanışlar, `ilk` =
  pozisyondaki ilk kijun-altı kapanış (araştırmanın çıkış günü), `u` = uzama sinyal gününden sonra başladıysa ilk günü, `bugun`; tarama `kesin`
  ekler (seans içinde bugünkü 'altında' kesin sayılmaz: 'şu an altında, kapanışta kesinleşir'). Grafik için `spark.sc` = [başlangıç sırası, değerler].
- **Neden kijun (chandelier 3 ATR değil):** 200 rastgele yarım listede uzama/hic/kijun v3'ü 100/86/95/82 (düşük dahil/hariç, yüksek dahil/hariç),
  chand3 100/94/87/62 — yüksek faiz çökenler hariç hücrede kijun daha sağlam; c12'de daha az yanlış alarm (306 vs 399 tetik; %25+ yükselişi
  kaçırma %20 vs %25). İkisinden yüksek olanı seçmek (karışık tanım) test edilmedi ve c12 oranlarını geçersiz kılar. OZATD'de ikisi de 10.09.
- Doğrulama: canlı `ilk` ↔ araştırma motoru (`cikis/ortak_c.cikis_bul`, uzama/hic/kijun) 2.031 v3 işleminde 0 fark (421'inde çizgi gösterilir,
  369'unda iz stop'tan önce altında kapanış). OZATD 10.09 kapanış 4.450 < kijun 4.542,5 → 'altında kapandı (10.09)'. KTLEV: iz stop'tan (02.09) önce
  altına inmedi (araştırmayla aynı). Bilinen küçük fark: araştırma 52h dibini ≥120 günle de alıyordu, canlı `asiri_uzama` 250 gün ister.
- Pano: 🚀 kutusunda aşırı uzama notunun yanında (`scMetin`), grafikte ince pembe kesikli çizgi (#D6336C; iz stop mor), fare bilgisinde 'Sıkı çizgi',
  sözlük + 'Grafik nasıl okunur?'. Portföyde: 'Bugün ne var?' (`bugunUyari`, son 5 günde altında kapanış) ve akşam portföy özeti notu (özet zaten günde
  bir kez, kesin kapanıştan sonra; durum.json'a anahtar YOK). AL mesajına eklenmedi. Metin Python `tarama.siki_metni`/`siki_alt`/`_sayi_tr` =
  JS `scMetin`/`scAlt`/`sayiTr` (3.094/3.094). Sayılar c12'den (`SIKI_NOT`); değişirse ikisini birlikte güncelle.

## 📅 Vadeler · ⏱️ gün içi görünüm · 🚀 gün içi kırılım notu (2026-10, hepsi BİLGİ — scratchpad vade_uzun, vade_gunici, vade_impl)
- **Vadeler (`sinyal.vade_durum` → `vd` = [günlük, haftalık, aylık], +1/0/−1/None):** Günlük ↑ = kapanış > SMA50 ve SMA50 10 gün
  öncesinden yüksek, ↓ = altında ve yükselmiyor; Haftalık (Weinstein) = son TAMAMLANMIŞ haftanın (W-FRI) kapanışı > 30 haftalık ort.
  ve ort. 4 hafta öncesinden yüksek; Aylık = son tamamlanmış ay > 10 aylık ort. ve ort. bir önceki aydan yüksek; aksi →. Mumlar 4 yıllık
  günlükten türetilir; hafta/ay 'tamam' = son gün kesin (18:30+ ya da geçmiş gün) ve sonraki iş günü ya da bugün yeni dönemde
  (`analiz_et(bar_kesin, bugun)`). 11 aydan kısa geçmişte aylık —. Doğrulama (vade_impl/t_vade.py, 258 hisse × son 120 gün = 30.960
  hisse-gün): 2y pencere = 5y veri 0 fark; araştırma `durum.py` ile günlük/aylık 0, haftalık 33 fark (hepsi 30.04.2026: 1 Mayıs tatili,
  araştırma perşembe kapanışında haftayı tamam sayıyor, canlı ertesi günü bekliyor). Pano: tablo 'Vade' sütunu (G↑ H↑ A↓, istemcide
  `DATA.vd`'den çizilir, sıralanabilir), modal `vadeHtml` satırı, sözlük. Üçü ↓: 2016-2026'da sonraki 60/120 günde endeksi yenme
  ~%35-45 (tüm hisselerde ~%41-56; düşük faiz/çökenler hariç n=53 hücrede %49-53) → 'fark küçük, kesin değil'. Üçü ↑: 'tek başına
  alım sinyali değil'.
- **⏱️ Gün içi görünüm (`gunici.py` → panoda `const GI={g,t,tam,v:{kod:[15dk trend,RSI,kırılım, 1s…, 4s…]}}`):** trend ↑ = EMA20 >
  EMA50 ve fiyat > EMA50 (↓ tersi), RSI(14), son 3 mumda önceki 20 mumun zirve/dip kırılımı. 15 dk verisi `veri_cek`'in tek toplu
  indirmesinden (`start=` son 59 gün, threads=True; kapanış düzeltmesi de bundan); 1 s 10:00 hizalı, 4 s 10:00-14:00 / 14:00-18:00;
  bitişi 'şimdi − 15 dk'dan sonra olan yarım mum atılır; `bolunme_duzelt` uygulanır; <60 mum → o vade boş. 59 gün yeterliliği: 45
  güne kısaltınca 4 s trendi 325 hissenin 7'sinde değişiyor (EMA50 tam oturmuyor, Yahoo 15 dk en fazla 60 gün veriyor). Seans
  dışında (18:30+, hafta sonu, 10:00 öncesi) önceki index.html'deki `GI` son seansın tamamlanmış hâliyse (`tam`) yeniden kullanılır
  ve sadece 7 günlük 15 dk iner. İndirme/hesap hatasında `GI=null`, tarama bozulmaz (test: 15 dk yok → saatlik yedek; hepsi yok;
  hesap hatası). Süre: 15 dk 59 gün ≈ 15 sn (eski saatlik 7 gün ≈ 12-15 sn, yerine geçti) + hesap ~10 sn → Actions'a ~+10 sn.
  Araştırma (323 hisse 2023-11→2026-10): BIST100+EK'te 1 s trend/RSI/oylama sonraki 1-5 günde maliyetten küçük fark (±3-12 baz
  puan); RSI<30 sonraki 5 günde ort. hisseden −36 bp (tümü −100 bp) → modal notu.
- **🚀 gün içi kırılım:** kesin kapanış öncesi `tk.bugun` ise `tk.gk` = verinin saatine (şimdi − 15 dk) göre o saatte görünen
  kırılımların kapanışta tutma oranı (`tarama.GK_ORAN`: 10:30 %67, 11:30 %71, 12:30 %74, 13:30 %77, 14:30 %76, 15:30 %79, 16:30 %85,
  17:30 %88; v3_yanlis.py, 611 aday gün). Kutuda + Telegram 🚀 başlığında `GK_NOT` (kapanış seansında almak ertesi açılışa göre
  ort. +0,8 puan; ertesi gün VWAP geri çekilmesi −1,0, limit −%1/−%2 −6,8/−10,2 puan — en güçlüler dolmadan kaçıyor). Backtest'in
  ertesi açılış varsayımı DEĞİŞMEDİ. 17:30-18:30 mesajındaki eski '25/25 tuttu' cümlesi `gk_metni` ile değişti. Python `gk_metni` /
  `GK_NOT` = JS `gkMetin` / `GK_NOT` (9/9).
- **🚀 'seviyenin üstünde ama AL yok' (ENERY 2026-10-08):** kutu 'Kapanış 14 TL üstüne çıkarsa AL (%-1.1 yukarıda)' diyordu; fiyat
  zaten üstteydi ama (a) kırılım ilk gün değildi (dünkü kapanış da 20g zirvesinin üstünde, kural sadece ilk günü sayar) ve (b) BIST 100
  < SMA50 (piyasa filtresi). `trend_kirilimi` artık şablonda/pozisyonsuzken `eksik` = ['ilk','oynak','piyasa','cikis'] verir; kutu ve
  sade anlat eksik koşulu yazar. Aynı durumda HRKET (−%1,5) vardı.
- **Test edilip GEREKMİYOR çıkanlar (tekrar araştırma):** 1/5/15 dk sistemleri (oylama, SuperTrend, EMA kesişimi, kırılım; maliyet
  sonrası işlem başı −0,6…+0,4 puan, aynı tutuşlu rastgele girişe göre fark küçük; 1 dk'da hepsi eksi); 1 s / 4 s trend sistemleri (aynı tutuşlu rastgele girişten fark tutarsız, 4 s kırılım
  tümünde −2,7 puan); açılış aralığı kırılımı (ORB 30/60 dk), VWAP kesişimi, RSI<30 dip dönüşü (rastgeleden ayrılmıyor ya da kötü);
  haftalık/aylık v3 değişikliği (haftalık+aylık ↑ filtresi, cuma kapanışında iz stop, haftalık SAT'ta çık, haftalık v3: 200 yarım
  listede v3'ü yenme %16-90, düşük faizde fark yok → tutarsız); 'zayıf kapanış' etiketi (kapanış gün aralığının alt yarısı / tipik
  fiyat altı: yüksek faizde kötü, düşük faizde iyi; 10 yuvada atlamak 4 yılda +%478 → +%424).

## Canlı kurallar (5 yıllık backtest'e dayanarak, 2026-09)
- Piyasa filtresi: XU100 < SMA50 → "piyasa zayıf" bandı + Telegram notu (AL'ler engellenmez).
- Hacim: AL'e dönüş günü hacmi ≥ 1.5× önceki 20 gün → "📈 hacim" etiketi. Aynı işlemler etiketlenince (çökenler hariç) hacimli/hacimsiz farkı YOK; önceki "filtre" testindeki fark seçim yan etkisiydi → bilgi amaçlı tut, filtreye çevirme.
- Piyasa filtresi etiket testinde de sağlam (her iki faiz dönemi, çökenler dahil/hariç).
- Dirence <%3 yakınken gelen AL'ler backtest'te en iyi grup (kırılım) → "Dirence yaklaşıyor" yeni AL için "uzak dur" değil.
- AL eşiği (4/5) ve stop (%8+20g dip) zaten en dengeli; %10-15 stop farkı gürültü düzeyinde.
- Kısmi kâr alma (dirençte ya da 2R'de yarısını sat) backtest'te belirgin şekilde KÖTÜ (düşük faiz +9.3 → −1.3; yüksek +2.5 → +0.2-0.4 endekse göre). Hedefleri "satış emri" diye sunma; izleme noktası.
- Zamanlama: AL/SAT geçişleri 17:30'dan (`SINYAL_DAKIKA`) sonra değerlendirilir; gün içi daha erken taramada
  `durum.json` → `son` DEĞİŞMEZ. Saatlik veriyle: 17:00 civarı yeni AL'lerin ~%88'i kapanışta tutuyor (erken saatte
  ~%75); 17:00 fiyatıyla ertesi açılış arasında belirgin fark yok. 17:30–18:30 arası verilen sinyaller `on_sinyal`'de
  tutulur; 18:30 (`KAPANIS_DAKIKA`, kesin kapanış) sonrası tutmayanlar için "iptal" mesajı ve `son` geri alınır.
  Günlük/haftalık özet ve uzun vade kırılım kontrolü 18:30 sonrası.
- Uzun vade (`uzun: true` portföy kaydı): stop yerine karar çizgisi = fiyatın altındaki en yakın destek × (1−tol).
  Karar çizgisi hep fiyatın altından hesaplandığı için kırılım, bir önceki kapanışta kaydedilen çizgiyle
  (`karar_cizgisi`) kıyaslanır; aynı seviye için bir kez (`karar_kirilim`). Backtest: güçlü yükselişte büyük
  hisselerde al-tut, sinyale göre girip çıkmaktan belirgin iyi (19 hisseden 15'i).
- SAT + destekten tepki: SAT sürerken destek tepkilerinin ~%68'i 20 günde kırıldı → çelişki notu + karar çizgisi.
- **v2 (gece testleri 2026-09-26, `oneri/v2-iz-stop`):** sınırsız sepet simülasyonunda asıl sorun ÇIKIŞ: stop+SAT2
  yükseliş piyasasında kazancı eritiyor (düşük faiz +%9; 2023 −%6). %20 iz stop (AL'den beri tepe kapanışın %20 altı,
  SAT'ı yok say) + giriş filtresi (trend: fiyat>SMA200 ve SMA200 20 günde yükselmiş; 60g oynaklık ≤%5): düşük faiz
  +%67/+%70/+%52 (tüm/çökenler hariç/büyük), yüksek faiz +%224/+%215/+%174; hiçbir yıl eksi değil; %18/%22 komşu
  tutarlı; ort. tutuş ~4 ay. İşlem başı (backtest.py v2): düşük faiz isabet %71, endekse göre +%19.4 (top10 hariç +%8.5).
  İz stop manipülatif hisse etkisini de nötrlüyor (tüm ≈ çökenler hariç). Önceki per-trade testte iz stop kötü
  görünmüştü: ölçüt farkı (per-trade vs portföy) — kararları sepet simülasyonuyla ver.
- Kısa vade gerçeği: BIST'te <1 ay tutuşlu çıkışlar (SMA20 altı, SuperTrend dönüşü) her evrende en kötü.
- 🌱 Uzun vade sinyali (`sinyal.uzun_vade`): yükselen trendde (fiyat>SMA200, SMA200 20 günde yükselmiş) SMA50'ye
  %2 yakın geri çekilip yükselişle kapanış → AL; 2 gün SMA200 altı → SAT. Backtest (çökenler hariç): düşük faiz
  endekse göre +%10.7/isabet %65, yüksek faiz +%3.4 — günlük sinyalden iyi ama en iyi 10 işlem hariç hafif eksi.
  Alternatifler (altın kesişim: kırılgan; haftalık MACD: +8.5/+2.2) daha zayıf. SMA200 ve durum makinesi için tarama 4 yıl veri çeker (2y pencerede 21 hissede 🌱 tarihi/durumu yanlıştı).
  Telegram: kapanış sonrası (18:30+) `uv_son` ile geçişler; AL herkese, SAT portföye.
- 🚩 Bayrak kırılımı (`sinyal.bayrak_kirilimi`): isabet %46 (günlük %34) ama endekse göre fark günlükten düşük
  ve kırılımların %70-85'i zaten AL ile aynı gün → sadece bilgi etiketi, ayrı sinyal değil.
- **AL önceliği:** portföy simülasyonunda aynı gün birden çok AL varken son 20 (10/40) günde AZ yükselmiş olanı
  önce seçmek, çökenler hariç her iki faiz döneminde en iyi (yüksek faiz +%208 → +%290). Telegram AL listesi
  buna göre sıralı (`mom20`). Çökenler dahil edilince uç sonuç (+%1128) — güvenilmez, o yüzden sadece sıralama.
- **Portföy düzeyi gerçekçilik (2026-09):** 10 eşit parçalı portföy simülasyonunda canlı kurallar 4 yılda
  (Eyl 2022–Eyl 2026) XU100 al-tut'u YENEMEDİ: endeks +%295 (maks düşüş −%23); sistem nakit faizli +%277
  (−%28), faizsiz +%179 (−%33). Sadece yüksek faiz döneminde, nakit faizli ve çökenler hariç endeksin
  önünde (+%208 vs +%160). İşlem başı "endekse göre fark" pozitif olsa da nakitte bekleme + yoğunlaşma
  portföyü geri bırakıyor. Kullanıcıya "endeksi yener" deme; sistemin değeri risk uyarılarında. Yeni
  kural önerirken portföy simülasyonuyla da ölç (scratchpad bt/portfoy_sim.py mantığı).
- Sektör: Yahoo sector/industry günlük oran önbelleğinde (5 elemanlı liste); `ENDUSTRI_TR` Türkçe karşılıklar.
- Bilanço (`bilanco.py`, bilgi amaçlı): yfinance çeyreklik net kâr/satış (son ~6 çeyrek), geçen yılın aynı çeyreğine
  göre değişim, sonraki bilanço tarihi (Yahoo takvimi varsa, yoksa SPK konsolide son teslim: 3/9 ay 40, 6 ay 60, yıllık 70 gün).
  `bilanco.json` önbelleği 3 günde bir, seans dışında (18:30+) yenilenir. Veri geçmişi kısa → backtest edilemedi, sinyale
  GİRMEZ. Portföy özetinde 7 gün içindeki bilanço uyarısı; panoda 📅 rozet + modal çeyreklik grafik. THY gibi USD raporlayanlar var.
- Endeksle kıyas: portföy kaydında isteğe bağlı `tarih` (alış) ve `xu_birim` = adet×maliyet / o günkü BIST 100 (pano
  hesaplar; aynı hisseye eklemede birimler toplanır, tarihsiz alım kıyası o hisse için kapatır). Kıyas = Σ adet×fiyat vs
  Σ xu_birim×XU_son. `tarama.endeks_serisi` (son 2 yıl günlük + 10 yıla kadar haftalık) panoya `XU` olarak gömülür;
  `endeks_kiyas` (Python) ve `pfKiyas` (JS) aynı mantık. Portföy özetinde de satır. Temettü iki tarafta da yok.
- Temettü (`bilanco.temettu_ozet`, aynı önbellek): son 12 ay nakit temettü/hisse + verim (>%25 'şüpheli': yfinance
  bedelsizi bilmez), Yahoo'da varsa ileri hak kullanım günü (az hissede var, tahmini olabilir). 7 gün içindeyse 💰 rozet +
  portföy özeti notu (o sabah fiyat temettü kadar düşük açılır). Bilgi amaçlı.
- KAP (`kap.py`): kap.org.tr'nin kendi sitesinin kullandığı POST `api/disclosure/members/byCriteria` (ODA + FR,
  son 7 gün, tek istekte tüm şirketler; en çok 2000 kayıt). Gürültü konular ayıklanır; `kap.json` 45 gün hisse başı (+ `fr`: ilk
  'Finansal Rapor' yayınları 400 gün, bkz. '📈 RS puanı · 📊 bilanço tepkisi' bölümü).
  Modalda son 5 bildirim. Telegram: portföy hisselerinin yeni bildirimleri (geri alım hariç), `durum.json` → `kap_son`
  (genel bildirim sayacı, portföy bilgisi içermez); ilk çalışmada sessiz başlangıç. KAP'a ulaşılamazsa önbellekle devam.
- 📋 'Bugün ne var?' kartı (`bugunRender`, istemci): PIYASA (piyasa_durumu JSON), 🚀 AL son 5 gün, portföy uyarıları
  (`bugunUyari`: 🔒/taban serisi ilk sırada; iz stop kırıldı/%3'ten yakın sadece portföyde; 🎈/⚠️/🪤/bilanço/temettü ≤7 gün/bölünme ≤30 gün),
  favoriler (🚀, 👀 ≤%3, uyarılar). Üst sayılar artık v3: bugün 🚀 AL / son 5 günde 🚀 AL.
- Karne (gecmis.html): kartlar sadece `kural: v3` kayıtları; eski kayıtlar 'eski kural' etiketi + ayrı özet satırı (`ozet['eski']`).
- ⭐ Favoriler: istemci tarafı (`favoriler_v1` localStorage + `FAVORILER` variable, portföyle aynı anahtar). `tabloDuzen()`
  favorileri üste alır (sunucu sırası AL→NÖTR→SAT korunur), sütun sıralamasında da üstte tutar; arama kutusu + 'sadece
  favoriler'. Satırlarda `data-kod`; ilk sütun ⭐. AL+ işareti ★ yerine 'AL+' yazısı (favori yıldızıyla karışmasın).
- 📍 Portföy gün içi (`tarama.gunici_olaylar`, 10:15-18:10 hafta içi): destek/direnç DÜNKÜ kapanışa kadarki veriyle
  (`sd_dun`; bugün yeniden hesaplanan destek kırılınca alttaki dibe kayar),
  destek dün üstünde kapanılıp bugün karar çizgisi üstünde (hafif altında) kapanınca ertesi gün de korunur (`destek_direnc`,
  2026-09-29; eskiden %97'sinde kayboluyordu, 'yarın izle' izlenmiyordu; gün içi 'desteği kırdı' mesajı hisse-günlerin %4,9 → %8,1'i), olaylar d_yakin/d_sarkti/d_kirildi (karar
  çizgisi = S·(1−tol)), r_kirdi/r_dondu, iz_yakin (%2)/iz_alti, taban/tavan (±%9,5)/sert (−%5). Olay+seviye günde bir kez
  (`durum.gunici`, gizli anahtar); ağır olay hafifleri bastırır. Veri teyidi: olay `_son_fiyat` (fast_info) ile de tutmalı,
  iki fiyat >%1 farklıysa atlanır (THYAO 24.09 Yahoo günlük 288,5 / resmi 289,5, destek 289,25 → yanlış 'kırıldı' görünmüştü).
  Son bar bugünün değilse (hisse henüz işlem görmedi) olay yok. Kesin kapanışta `kapanis_sd` sonucu günlük portföy özetinin
  başında (ayrı mesaj değil; uzun vadede kırılım karar çizgisi mesajına bırakılır). `GUNICI_OLAYLAR`: d_sarkti/d_yakin
  kapalı (gürültü); r_dondu gün içi tepe dirence DEĞMELİ (bölge kenarı değil). bt/mesajsay*.py: 5 hisselik portföyde
  mesaj gelen gün %82 → %41. ☀️ Sabah (`seviye_satiri`, günün ilk taraması <12:00, `sabah_tarih`).
  Olay çalışması (bt/sd1-2.py, 125 hisse 2022-26): sarkmaların %41'i kapanışta geri alındı, %40 tolerans içi, %19 kırıldı;
  kırılım/dönüş/aşım sonrası 20g getiri, aynı trenddeki rastgele günden ±1-2 puan ve dönemden döneme yön değiştiriyor
  (düşük faizde kırılanlar daha İYİ gitti) → mesajlar bilgi, sinyal değil (`SD_NOT`).
  Ek gün içi olaylar: 🎈/⚠️ `tahta_riski` bugün yeni oluştuysa (dünkü veriyle aynıysa sadece günlük özette), BIST 100
  ±%2,5 (`PIYASA_SERT`) günde portföyün günlük K/Z satırı. iz_alti metni: v3 pozisyonlarında gün içi iz stop altına ilk
  sarkmaların %44'ü kapanışta geri alındı; kapanışa bakmak gün içi stop'ta satmaktan ort. +%3 (bt/izgunici.py).
- Portföy özeti: 🛡️ risk satırı (her pozisyon iz stop / karar çizgisine inerse kayıp, % portföy değeri); 📉 `trend_asagi`
  (fiyat < SMA200 ve SMA200 20 günde düşmüş) notu. bt/trend1.py (125 hisse + tüm borsa, 5 günde bir örnek): düşük faizde
  ASAGI'daki hisselerin 60g'de endeksi yenme oranı %24-38 (YUKARI %41-50), medyan −%9…−12; yüksek faizde fark küçük/karışık
  (tüm borsada ters). Pano portföy tablosunda Destek sütunu (`d.sd.destek`, bugünkü veriyle en yakın destek).
- Fiyat alarmı: panoda hisse penceresinden kurulur, `ALARMLAR` variable'ına (portföyle aynı anahtar) yazılır;
  her taramada (gün içi de) kontrol, her alarm bir kez çalar. durum.json herkese açık olduğundan sadece
  alarmın sha1 özeti (`alarm_tetik`) saklanır; silinen alarmın kaydı temizlenir. **Önerilen alarmlar** (`alOneriler`, JS):
  en yakın destek (fiyat desteğin hafif altındaysa karar çizgisi), direnç, 🚀 kırılım seviyesi (şablonda), portföydeyse iz stop /
  karar çizgisi (aşılmış seviye önerilmez); tek tek ya da 'Hepsini kur', aynı kod+yön+fiyata ikinci alarm kurulmaz (elle de).
  Kayıtta isteğe bağlı `not` ('destek', 'iz stop'...; ≤40 karakter, Telegram'da escape'li gösterilir). Anahtar hâlâ
  kod|yön|fiyat → eski alarmlar aynen çalışır.
- Taban serisi: son 15 günde ≥4 kez ≤ −%9 → "⚠ taban serisi"; bu hisselerden AL mesajı gitmez. Erken aşaması 🔒 kilitli taban (yukarıda).
- SAT: 1. gün "⏳" işaretiyle gösterilir/bildirilir, 2. gün "✅ teyit" mesajı (portföy).
- Portföy: çıkış = son AL başındaki sabit stop (`al_stop`), SAT'ta çıkış sebebi sinyal; hedefler
  küçükten büyüğe (en yakın direnç, 2R). Günlük portföy özeti 18:00 sonrası ilk taramada.
- Python (`tarama.pozisyon_plani`) ve JS (`pano.pozPlan`) aynı mantık — birini değiştirirsen ikisini de.
- Şablon (pano.py `_SABLON`) raw string içinde JS: tek tırnaklı JS dizelerinde kesme işareti `\'` olmalı;
  değişiklikten sonra şablon JS'ini `node --check` ile doğrula (bir kez sayfayı tamamen bozuyordu).

## 💬 Sade anlat · 🔎 Neden yükseldi/düştü? (2026-10, hisse penceresi, hepsi istemci JS — yapay zekâ yok)
- `sadeHtml`: (a) genel yön — `trend`/`trend_asagi` + SMA50 (📉 trend aşağı uyarısıyla aynı kural), ikisi de değilse 60g
  getiri ±%10; (b) kısa vade alıcı/satıcı — 💪 güç ≥5 (sinyal SAT değilse) / ≤2 (AL değilse), yoksa 'dengede' (oylama ile
  çelişmesin) + 5g hacim ≥1,5x notu; (c) tek seviye — portföydeyse iz stop / karar çizgisi (JS, localStorage), değilse 👀 kırılım
  seviyesi (≤%3) ya da en yakın destek/direnç (±%15'ten uzaksa 'yakında seviye yok'); (d) en önemli tek uyarı (🔒 > taban serisi >
  🎈 > ⚠️ > 🪤 > 🔻 > bilanço/temettü ≤7g > bölünme > ⚡). Sunucu tarafına portföy cümlesi YAZILMAZ.
- Metin düzeltmeleri (2026-10-08 vaka testi): (a) taban serisinde ya da 60 günde ≤ −%50'de genel yön '💥 çöküş' (DMRGD 7 tabanla
  'yükseliş' diyordu); (b) 🎈 tetiklendi ama 20g getiri eksiyse (çöküş sonrası tepki tavanları: HEDEF, PASEU, KLRHO, CRDFA, LYDHO)
  rozet/kutu/Telegram metni '🎈 sert dalgalanma / sert tavan-taban dalgalanması' (`thDalga` = `tarama._sisme_ad`; `tahta_riski` tetiği
  aynı); (c) 🌱 SAT kalmışken fiyat SMA200 üstüne döndüyse 'hâlâ SAT …, fiyat o zamandan beri üstüne döndü' (eskiden hem 'trend
  bozuk' hem 'trend yükselişte'); (d) neden kutusundaki iz stop satırı: portföy dışında sadece 🚀 v3 çıkışı (`tk.cikis_tarih`,
  Sinyal geçmişiyle aynı), portföyde portföyün kullandığı `d.iz` (eskiden gösterge iz stop'u: 313 hissenin 175'inde çelişki).
- `nedenHtml`/`hareket`: 1/5/20 gün hisse getirisi (grafik verisi `spark`), aynı tarihlerde BIST 100 (`XU`), kıyas grubundaki
  diğer hisselerin ortalaması, hacim oranı (`sinyal.hacim_oranlari` → `hv`: 1g/önceki 20g, 5g/önceki
  60g, 20g/önceki 60g), pencere içi tavan/taban, KAP (son 5 bildirimden pencere içindekiler, geri alım ayrı sayılır), bölünme,
  6 ay/20 gün zirve-dip, destek tepkisi/direnç, iz stop kırılımı. 'Aynı dönemde' der, sebep iddia etmez.
- Eşikler (scratchpad bt/hareket/dagilim.py, 299 hisse, Eki 2021–Eki 2026): endeksten ayrışma ≥ 4 / 10 / 20 puan (1/5/20 gün)
  → günlerin %12,9 / %11,6 / %12,8'i; hacim ≥1,5x → %12,5-12,7 (≥2,5x 'çok yüksek', <%5). Ayrışanların sadece %7-8'inde
  sektör de aynı yönde gitmiş ('sektörel': sektörden fark < T/2 ve sektör endeksten ≥ T/2 aynı yönde); gerisi 'hisseye özel'.
- Olay çalışması (bt/hareket/olay.py; aynı hissede 20 günde bir olay; sonraki 20g endekse göre, aynı hisselerin tüm günleri
  ort +%1,4 / medyan −%1,2 / endeksi yenme %46): hisseye özel + hacimli YÜKSELİŞ (5g) ort +%2,3 / medyan −%2,4 / %44 (2.421
  olay; 1g ve 20g benzer, hacimsizler biraz daha iyi) → belirgin değil, kutuda sadece 'farklı gitmedi' notu. Hisseye özel +
  hacimli DÜŞÜŞ ise her yıl endeksin gerisinde: 5g ort −%3,8 / medyan −%5,2 / yenme %36 (839 olay), 20g −%7,4 / %33 (284) —
  bugünkü hisselerle (hayatta kalan yanlılığı tersine çalışır).
- 🔻 **Hisseye özel hacimli düşüş** (`tarama.ozel_dusus`, kullanıcı onayıyla BİLGİ uyarısı — AL/SAT kuralı değil): 5 ya da 20 günde
  getiri ve endeksten fark ≤ −10 / −20 puan, tür 'hisseye özel' (benzer hisseler açıklamıyor), hacim ≥1,5x. Canlı tanımla
  sağlamlık (bt/hareket/olay2.py, 299 hisse, aynı hissede 20 günde bir olay, sonraki 20g endekse göre; parantezde tüm günler):
  tümü 1.052 olay medyan −%4,8 / endeksi yenme %38 (−%1,1 / %46); 2021-10/2022-09 %33 (%45), **düşük faiz 2022-09/2023-06 %46
  (%47) → fark YOK**, yüksek faiz 2023-07 sonrası %38 (%46); çökenler hariç (örneklemde taban serisi yaşamış 144 hisse çıkarılınca)
  345 olay %39 (%45), düşük faizde yine fark yok. Metinler buna göre yumuşak: "~%38'i endeksi geçti (normalde ~%46); 2022-23 düşük
  faizde fark yoktu; kesin değil". Canlı fonksiyon geçmiş olaylarla birebir: 25 rastgele gün × tüm hisse 6.152 hisse-gün, 5 fark
  (4'ü 15 Temmuz tatil günü karşılaştırma artefaktı, 1 yuvarlama). Pano: tablo rozeti '🔻 özel düşüş', sözlük, sade anlat uyarı
  önceliği (🪤'dan sonra), `bugunUyari` (sadece portföyde), neden kutusu notu; Telegram akşam portföy özetinde hisse notu.
- Python aynası: `tarama.hareket_hepsi` = JS `hareket` (aynı girdi: spark + XU + hv + kg, aynı eşikler `HR_ESIK`/`HR_HACIM`).
  Kontrol: 313 hissede 939 ufuk, 0 fark. Akşam portföy özetinde '🔎 Bugün hisseye özel hareket' satırı (`hareket_satiri`: 1 günde
  tür 'hisseye özel' ve dikkat çekici olanlar; yoksa satır yok).
- Sektör kıyas grubu (`tarama.kiyas_gruplari` → panoda `kg`): Yahoo endüstrileri çoğu hissede 2-3 hisse, ana sektör ise çok
  geniş ('Sanayi' 77: holding+havayolu+savunma). `KIYAS_GRUP` benzer küçük endüstrileri birleştirir (Elektrik/doğalgaz,
  Ulaştırma, Makine/metal, Gıda/içecek, Yazılım/BT, GYO, Sağlık...); grupta (kendisi dahil) <4 hisse varsa kıyas yok
  ("karşılaştırılacak yeterli benzer hisse yok", 313 hisseden 10'u). Ana sektöre düşülmez.
- Eskiyen önerilen alarm (`alEski`/`alGuncelle`, JS): notlu (önerilenden kurulmuş) alarmın aynı aile+yöndeki güncel önerisi
  farklı seviyedeyse ya da yoksa '⚠ bu seviye artık güncel değil' + 'Güncelle' (güncel seviye zaten kuruluysa eskisi silinir).
  Notsuz (elle) alarmlara dokunulmaz. Seviye değişince alarm anahtarı da değişir → yeni seviye için yeniden kurulmuş sayılır.

## 🏢 İşlem Odası (2026-10-09, sanal para — `oda.py`, `oda_replay.py`, `oda.html`, `oda.json`, `oda_replay.json`, `oda_replay_sans.json`)
- Arkadaş önerisi 'Hızlı İşlem Odası': panonun kurallarını 100.000 **sanal** TL ile deneyen KURAL robotları (yapay zekâ yok;
  sayfada '🧠 Yapay zekâ ekibi — yakında' boş bölüm). Pano başlığında '🏢 İşlem Odası' düğmesi → `oda.html` (ayrı sayfa; panonun
  geri kalanı değişmedi). Yatırım tavsiyesi değil; kullanıcı portföyüyle ilgisi yok; `oda.json` herkese açık, portföy bilgisi YOK.
- **Robotlar ve kurallar araştırmadan** (scratchpad `oda_arastirma/`: robotlar.py referans motoru birebir `oda.py`'ye alındı;
  2022-10 → 2026-10, iki faiz dönemi; ana_tablo.txt, bekci_oneri.txt, pencere.txt, kayma_kilit.txt, baslangic.txt): 🚀 Kırılımcı (v3),
  📏 Kırılımcı + sıkı çizgi, 👀 Erkenci (👀 ≤%3, %20 iz), 📈 Momentumcu (ayın ilk kararı, BIST 100 < SMA50 ise nakit), 🧲 Dip avcısı
  (SMA200 üstünde destekten tepki; destek altı / direnç / 20 gün — 4 yılda ~1.300 işlem, −%40: 'çok işlem = komisyon erir' ders
  robotu), 🌱 Uzun vadeci, ↩️ RSI dönüşçü (**TAHMİNİ**: arkadaşın AL kuralı, çıkış %20 iz varsayım), 🎲 Rastgele (o gün kaç 🚀 varsa o
  kadar rastgele hisse, tarih tohumlu → tekrarlanabilir), 🧭 Endeksçi (BIST 100 al-tut). 10 yuva; 🛡️ Bekçi (`BEKCI`): alımda tek hisse
  ≤%10, sonradan >%25 olanın fazlası satılır, günde −%5 → ertesi gün alım yok, zirveden −%25 → hepsini sat + 20 işlem günü dur
  (araştırmada 4 yılda robot başına 0-2 kez; kâr aracı değil, emniyet kemeri). Motor notu: mola/durdurma bitince düşüş zirvesi o günün
  kasasına sıfırlanır (araştırma kodu böyle; değiştirilmedi).
- **Zamanlama/maliyet:** karar günde bir kez kesin kapanış taramasında (18:30+); emirler ERTESİ işlem gününün AÇILIŞ fiyatıyla, o
  günün kesin kapanış taramasında yazılır (bütün günün mumu belli → 'gün boyu kilitli' kesin). Alış açılış + 1 fiyat adımı, satış −
  1 adım, her yönde %0,2 komisyon, lot tam sayı (endeks kesirli), kilitli tabanda satış ertesi güne kalır, kilitli tavanda alım iptal.
  Bedelsiz/bölünme gününde eldeki adet/fiyat düzeltilir (`bolunme_uygula`). Gün içi taramalar sadece `anlik` kasa değerini yazar.
- **Canlı = tekrar oynatma:** ikisi de `oda.gun_isle` (emir_uygula + robot_karar). Canlıda gözlem `tarama.py`'nin `sonuclar`'ından
  (`ozet_hazirla`; yeniden veri çekme yok; sadece bugün işlem görmüş hisseler; RSI 24-34 ve 📏 elindekiler için düzeltilmiş df'den
  rsi değişimi/kijun/uzama). `tarama.py` çağrısı try/except'li (hata taramayı bozmaz; test edildi), süresi ~0,2 sn. `oda.json`: `v`,
  `bas`, `son_tarih` (aynı gün ikinci kez işlenmez), `tg_tarih`, `xu`, `robot` {kasa: nakit, poz, bekleyen, defter (tümü), seri,
  mevduat, atla, atla_n, tem}, `olay` (son 300), `anlik`, `makro` {gram, usd, faiz, faiz_t, tufe, tcmb_t}. Başlangıç 09.10.2026 (ilk akşam sessiz; ilk alımlar 12.10 açılışında). `defter`/`seri` büyür (~yılda 100-150 KB).
- **Telegram:** kesin kapanıştan sonra günde TEK skor mesajı (`ozet_mesaji`; 2026-10-10'dan beri sade biçim, aşağıda); ilk gün
  yok, gönderilemezse sonraki taramada tekrar.
- **`oda_replay.py`** (elle, ayda bir; Actions'ta ÇALIŞMAZ; ~1 dk; `--veri x.pkl` indirilmiş veriyle, `--sans N` hızlı deneme):
  araştırmanın hazirla+sim+replay'i. **2026-10-10'dan beri TEK UZUN oynatma** (eskiden son 250 gün sıfırdan): Yahoo'dan
  `UZUN_YIL` (5) + ~2 yıl ısınma indirir (canlı tarama 4 yıl kullanıyor, 2026-10-19 öncesi 2 yıl; 🌱 durum makinesi, v3 'pozisyon açık', Wilder ATR gibi
  geçmişe bağlı alanlar oturur — 1 yıl ısınmayla 🌱 4 yılda +%641, 2 yılla +%1.162 çıktı; 6 ve 7 yıllık indirme aynı), oynatma
  en erken `ISINMA` (260) işlem günü sonra, en fazla 5 yıl geriden başlar (şu an 11.10.2021 → bugün, ~1.250 gün). Robotlar
  baştan 100.000 TL ile kesintisiz çalışır. Hazır dönemler `DONEMLER` (son 6 ay=125 / 1 yıl=250 / 2 yıl=500 / 4 yıl=1000 işlem
  günü / tümü; varsayılan 1 yıl) için: 🎲 şans bandı (Rastgele 200 zar, dönem başında 100.000'e ölçekli %5/%50/%95) ve robot
  başına 'ikiz' şans yüzdeliği (her alım aynı gün rastgele hisseyle, 200 deneme; ikizlerin TAM serisi tutulur, her dönemin
  getirisi ayrı sıralanır; ≥95 'şansla açıklanması zor', 50-95 'üst yarıda ama şans olabilir', <50 'rastgele seçimden iyi değil').
  `oda_replay.json` (v2: gun, xu, robot{d: günlük kasa, i: işlemler, dur, sans{dönem}}, donem[{id,ad,a}], bant{dönem}, olay,
  veri_bas, isinma) ~410 KB / sıkıştırılmış ~135 KB; `oda_replay_sans.json` Rastgele'nin ilk 100 zarının günlük getirisi
  (on binde bir) ~460 KB / ~180 KB — sayfa SADECE özel dönem seçilince indirir. Eski 'aynı kural 4 yılda' alanı (`uzun`) yok;
  sayfa aynı satırı tüm oynatmadan hesaplar ('Aynı kural ~5 yılda').
  Doğrulama (2026-10-10): yeni kod araştırma verisiyle (sg/veri5y.pkl) araştırmanın oda_replay.json'unu 9/9 robotta işlem işlem
  üretiyor; eski 250 günlük dosyanın penceresi sıfırdan oynatılınca 7/9 robot işlem işlem ve kuruşu kuruşuna aynı (🧲 744→744
  işlem ama birkaç fiyat farkı, 🎲 70→62: eski dosya 09.10 öğlen indirilen veriyle üretilmişti); canlı yol (`gun_isle`) = tek robot
  sim 5 yılda 9/9 aynı. **Uzun oyun KAOTİK:** aynı gün iki kez indirilen veride Yahoo'nun düzeltilmiş fiyatları ~1e-7 oranında
  farklı geliyor (temettü katsayısı yuvarlaması) → eşit fiyat karşılaştırmaları (destek testi, 20g zirve) birkaç hisse-günde
  değişiyor → 🧲 ve özellikle 🎲 Rastgele'nin 5 yıllık yolu tamamen değişebiliyor (tümü +%430 ↔ +%852). Diğer robotlar iki
  indirmede aynıydı. Bu yüzden tek zarın sonucu değil şans bandı esas. Uzun oyunun son 250 günü eski sıfırdan oynatmayla aynı
  DEĞİL (dönem başında elde pozisyon var, kasa büyüklüğü/yuva doluluğu farklı; ortak işlem 📈 %86, 🧲 %99, diğerleri %36-53,
  🎲 ~%0) — tasarım gereği.
- **Sayfa (`oda.html`):** `oda.py`'deki `_SABLON`'dan `html_yaz` ile (sadece değişince) yazılır → fork'larda da *.py ile gelir; veri
  gömülü değil, `fetch('oda.json')` / `fetch('oda_replay.json')` (fork'ta yoksa YA DA eski v1 biçimindeyse ana projenin GitHub
  Pages'inden; `oda_replay_sans.json` da aynı kaynaktan). Kendi SVG'miz: mor izometrik salon, masa + robot figürü + isim etiketi +
  durum rozeti, borsa tahtası, bağlantı çizgileri, işlem olunca robot tahtaya yürür; sağda skor (getiri asla tek başına: BIST 100
  farkı, en büyük düşüş, alım, isabet, gün, en iyi 3 işlem hariç, şans yüzdeliği, 'aynı kural ~5 yılda' satırı), olay akışı, robot
  kartı (kural, pozisyonlar, işlem geçmişi, kasa grafiği + şans bandı, komisyon+kayma TL). Canlı / Tekrar oynat (1x/5x/20x/60x,
  kaydırıcı). **Dönem seçici** (tekrar oynatmada): Son 6 ay / 1 yıl / 2 yıl / 4 yıl / Tümü / Özel… (iki tarih, en az 20 işlem
  günü). Seçilen dönem uzun oyunun DİLİMİ: dönem başındaki kasa 100.000 TL'ye ölçeklenir (o gün eldeki hisseler dahil); getiri,
  BIST 100 farkı, en büyük düşüş, alım/isabet (dönemdeki alım ve satışlar), komisyon, sıralama, şans bandı o döneme göre. Neden
  yeniden 100.000'den başlatma değil: her tarih aralığı tarayıcıda anında hesaplanır (yeniden başlatma tüm hisse verisini ister),
  dönemler birbiriyle tutarlı, 'hepsi ilk gün alındı' etkisi yok (baslangic.txt'deki aşırı başlangıç duyarlılığının kaynağı).
  Bedeli: dönem başında robotun önceki alımları elde; satış sonucu ilk alış fiyatına göre; Bekçi'nin zirve ölçümü öncesinden gelir.
  Şans yüzdeliği sadece hazır dönemlerde; özel dönemde şans bandı 100 zarla tarayıcıda hesaplanır. Sayfada dönem notu: tarih
  aralığı, oyunun başlangıcı, verinin başlangıcı + ısınma günü, 'başlangıç günü sonucu çok değiştirir (🎲 −%4…+%137)'.
  URL: `#rep=120` (seçili dönemin 120. günü; varsayılan dönem 1 yıl → eski bağlantılar aynı anlamda), `#rep&don=2y`,
  `#rep&don=ozel:2023-01-02:2024-06-28` (dönem değişince adres çubuğu güncellenir), `#kart=kirilimci`. Üçüncü taraf script YOK.
  Telefonda salon yatay kayar, panel alta iner, dönem satırı alt satıra sarar (390 px'te yatay taşma yok). Şablon JS değişince
  `node --check`.
- **2026-10-10 geliştirme (dal `oda-gelistir`):**
  - **Motor düzeltmeleri (tüm robotlar):** (a) Bekçi'nin kırpması (kısmi satış) yuva AÇMAZ; kilitli tabanda bekleyen tam satış
    (`p['kilit']` = kaç gün satılamadı) boş yuva sayılmaz; `emir_uygula` yuvalar doluyken alım yazmaz (`_red` → 'alınamadı: yuvalar
    dolu') → 10 yuvalı robot asla 11 pozisyon taşımaz (eski motor 5 yılda 7 robotta 1-159 gün 11-12 pozisyon taşımıştı). (b) Nakit yuva
    payının yarısından azsa (`KUCUK_ALIM` = 0,5; karar anında satışların tahmini geliri dahil, uygulamada gerçek nakit) alım yok —
    eskiden 'kırıntı' alımlar yapılıyordu. Önce/sonra: `YUVA_DUZELTME = False` + `KUCUK_ALIM = 0` eski motoru verir (aynı veriyle eski
    oda_replay.json'u 9/9 robotta işlem işlem üretti; scratchpad `w/karsilastir.py`, `kars.txt`). Uzun oyun kaotik olduğu için tek
    düzeltme bile 5 yıllık yolu değiştiriyor (tümü: 🚀 +%900→+%931, 📏 +%1.348→+%1.094, 👀 +%1.791→+%2.584, 🌱 +%1.482→+%1.933,
    ↩️ +%1.058→+%787, 🎲 +%852→+%725, 📈 +%398→+%413, 🧲 −%28→−%29; yön robottan robota değişiyor → 'düzeltme getiriyi artırır' denemez).
    (c) **Temettü:** canlıda `temettu_isle` hak kullanım (ex) günü elde tutulan hisseye NET temettü (brüt × %85) nakit ekler (kaynak
    tarama'nın `bilancolar`'ı = bilanco.json'daki Yahoo temettü listesi; 3 günde bir yenilendiği için kayıt birkaç gün geç gelebilir,
    son 30 gün taranır; alış ex gününden önce olmalı; her (hisse, ex) bir kez, `kasa['tem']`). Tekrar oynatmada eklenmedi: Yahoo
    düzeltmeli fiyatlar temettüyü brüt olarak fiyata yeniden yatırır. Neden düzeltilmemiş fiyat + net temettüye geçilmedi: sinyaller
    (v3, destek, RSI) canlıda/backtest'te düzeltilmiş fiyatla hesaplanıyor; replay'i değiştirmek 'canlı = replay' eşitliğini ve geçmiş
    doğrulamaları bozar; fark sadece %15 stopaj — bu evrende ortalama verim ~%1 → ~0,15 puan/yıl iyimserlik (`oda_replay.TEMETTU_NOT`,
    sayfa notu). Bilinen küçük fark: canlıda ex günü fiyat düşüşü iz stop tepesine göre ölçülür (replay'de düzeltilmiş).
  - **🚀 Kırılımcı · 20 yuva** (`kirilimci20`, yarışmacı, kıyas amaçlı): v3 kuralı, her hisseye %5.
  - **💰 Birikim köşesi** (kıyas, yarışmacı DEĞİL; `KIYAS_TUR`/`BIRIKIM_TUR`; Bekçi yok; Telegram sıralamasına girmez):
    🏦 Faizci (32 günlük TL mevduat, TCMB politika faizi = 1 hafta repo; brüt × 32/365, stopaj vadenin açıldığı/yenilendiği günün
    oranı `STOPAJ`: 30.09.2020 %5, 01.05.2024 %7,5, 01.11.2024 %10, 01.02.2025 %15, 09.07.2025 %17,5; yenilemede o günkü politika
    faizi; kasa değeri işlemiş net faizi içerir), 🥇 Altıncı (gram = GC=F × USDTRY=X ÷ 31,1035; makas her yönde %1, alışta %0,2 BSMV,
    kesirli; kasa değeri satış fiyatından), 💵 Dolarcı (USDTRY=X; makas her yönde %0,5, %0,2 BSMV), ⚖️ Dengeci (1/3 mevduat, 1/3
    altın, 1/3 BIST 100; son dengelemeden ≥90 gün sonraki ilk vade sonunda yeniden 1/3, %2'den küçük sapmada işlem yok). Kesirli
    kodlar `KESIRLI` (XU100/ALTIN/USD; eskiden `kod == "XU100"`), mevduat `kasa['mevduat']` = {ana, t, oran, st}; defter yeni
    türleri MEV / FAIZ / TEM; alışta `makas`/`bsmv`, satışta `makas` TL. Kartta stopaj/makas/BSMV TL. 5 yılda (2021-10 → 2026-10):
    Faizci +%286, Altıncı +%1.185, Dolarcı +%442, Dengeci +%735, Endeksçi +%769. Altın/dolar 'açılış' fiyatı = o günün Yahoo
    kapanışı (gün içi saat farkı yok sayıldı). Gerçek mevduat faizi politika faizinden farklı (2023-24'te üstündeydi) — kural metninde.
  - **Canlı makro** (`makro_guncelle`, sadece kesin kapanış işleminde): Yahoo GC=F + USDTRY=X son 10 gün; TCMB politika faizi ve
    TÜFE (`politika_faizi_tablo` / `tufe_tablo`, anahtarsız HTML sayfaları; EVDS kullanılmadı) günde bir kez; her biri ayrı
    try/except, hata → son bilinen (`oda.json` → `makro`), o da yoksa `oda_replay.json` → `makro`. Test: üçü de çökerken gün işlendi,
    Faizci faizi oda_replay.json'dan aldı, altın/dolar alımı ertesi güne kaldı; tarama.py'deki blok oda istisnasını yutuyor.
  - **Reel getiri** (her robot, canlı + dönem seçici): TÜFE dönemin başladığı aydan SON AÇIKLANAN aya kadar bileşik (başlangıç ayı tam
    sayılır); etiket 'TÜFE Eki 2025 – Eyl 2026 (son açıklanan aya kadar)'. Python `tufe_kum` = JS `tufeKum`.
  - **Geriye uyumluluk:** `oku` artık eksik robotu reddetmiyor; kesin kapanış işleminde `ROBOTLAR`'da olup oda.json'da olmayan robot
    o gün 100.000 TL ile eklenir (`baslangic` = o gün; skor/Telegram'da BIST 100 farkı kendi başlangıcından). `seri` öğeleri artık
    [tarih, değer, pozisyon sayısı] (eskiler 2 elemanlı, okunur). Test: 09.10 oda.json (9 robot, bekleyen emirler) → eski emirler
    yazıldı, 5 yeni robot eklendi.
  - **Kaçırılan roketler:** `robot_karar` alınamayan adayları kaydeder: kırılım robotlarında `kasa['atla']` = [tarih, kod, 'yuva'|'nakit'
    (+ canlıda `atla_guncelle` ile v3 sonucu %, kapandı)], diğerlerinde `atla_n` = [tarih, yuva, nakit] sayısı. Tekrar oynatmada robot
    çıktısı `k` = [gün, kod, 'y'|'n', v3'ün kendi sonucu %, çıkış günü|−1] (`kacan_listesi`; sayfa sadece o güne kadar kapanmışların
    sonucunu gösterir), `kn`, `p` (günlük pozisyon sayısı, base36). Kartta: N roket / M alındı / K yuva dolu / L nakit kalmadı,
    atlananların ortalaması vs robotun kapattıkları, yuvaların dolu olduğu gün oranı, en uzun 3 yuva işgalcisi, son kaçanlar; olay
    akışında '⛔ X roketi kaçtı'. Not: kaçışların çoğu 'nakit kalmadı' (para kazanan hisselerde; eskiden kırıntı alım yapılırdı).
  - **Neden notları:** alım emrinde `not` = [ölçü, o günkü aday sayısı, boş yuva, sıra] (ölçü: 🚀 kırılan 20g zirvesi = `tk.seviye`
    (canlıda `kirilim_seviye`, replay `hh20`), 👀 zirveye %, 🧲 destek, ↩️ RSI, 📈 6 ay %), satışta {tp tepe, iz seviyesi, k karar
    kapanışı, kb kilitli tabanda bekleme günü}. Replay işlem listesi: A [g,'A',kod,adet,fiyat,not|0,(makas,bsmv)], S [...,neden,not|0,
    (makas)], M [g,'M',ana,faiz%], F [g,'F',brüt,stopaj]; yeni neden kodu `dg` (Dengeci kısmi satış).
  - **Sayfa:** salon derinliği 14,4 (viewBox −700 −185 1500 940), 🚀·20 masası [9.1,5.4], 💰 Birikim köşesi ön sırada (bağlantı çizgisi
    yok), skor tablosunda yarışmacılar numaralı, birikim satırları ayrı başlık altında; reel satırı; robot kartında reel/stopaj/makas/
    BSMV/temettü kutuları, kaçan roket paneli, MEVDUAT/FAİZ/TEMETTÜ satırları; **aylık getiri ısı tablosu** (salon altında; robot × ay,
    + BIST 100 satırı, 'endeksi yendiği ay oranı'; JS günlük seriden hesaplar). Test (scratchpad `w/cdp.py`, CDP mobil öykünme):
    390 px ve 1280 px'te 9 senaryoda yatay taşma yok, JS hatası yok. Not: `chrome --window-size=390` masaüstü penceresi ~500 px'in
    altına inmez → taşma varmış gibi görünür; mobil testi CDP `Emulation.setDeviceMetricsOverride` ile yap.
  - **Telegram sade:** ilk 3 + son 3 (yarışmacı + Endeksçi/Rastgele; ≤6 ise hepsi), 'Bugün: 🚀 AL X · SAT Y …', '🚫 Kasa dolu,
    bugün N roket alınamadı' (yuva dolu + nakit kalmadı), BIST 100, '💰 Kıyas: Faiz · Altın · Dolar · TÜFE', Bekçi; şans notu sadece
    CUMA (ilk 6 ay).
  - **Boyutlar:** oda_replay.json ~694 KB (gzip ~235 KB; önce 409 KB — notlar, kaçan roketler, 5 yeni robot), oda_replay_sans.json
    ~464 KB (gzip ~181 KB). Doğrulama: canlı yol (`oda_oynat`/`gun_isle`) = tek robot `calistir` 5 yılda 14/14 robot birebir
    (scratchpad `w/testler.py esit`); yuva senaryosu testi `testler.py yuva` (eski 12 pozisyon, yeni 10). `oda_replay.py --makro x.pkl`
    indirilmiş altın/dolar/faiz/TÜFE ile çalışır (yoksa Yahoo + TCMB'den indirir).
- **2026-10-19: 💪 güç robotları + 🔐 kâr kilidi (dal `guc-robot`; scratchpad `gucrobot/RAPOR.md`, betikler orada):** 6 yeni
  yarışmacı (hepsi 10 yuva, Bekçi, riskli filtre, aynı emir/maliyet). 💪 Güçlü (`guclu`, tur `guc`): güç puanı ≥6 al, ≤3 ya da %20 iz sat.
  📐 Şabloncu (`sablon`): trend şablonunda al (kırılım beklemeden), şablon bozulunca sat. ☁️ Bulutçu (`bulut`): fiyat > bulut ve kijun,
  tenkan > kijun, fiyat > 26 gün önceki kapanış (chikou) al; bulut altında kapanışta sat (`cik: 'kijun'` seçeneği var, kullanılmıyor).
  🏔️ Zirveci (`zirve`): 55g zirveye ≤%3 + CMF > 0,05 al; önceki 20 günün en düşük kapanışı altı ya da %20 iz sat. 💧 Para akışı (`para`):
  CMF (20g) dün ≤0 bugün >0 ve fiyat > SMA50 al; CMF < −0,10 sat. Güç robotlarında sıra: güç puanı yüksek önce, eşitse son 20 günde az
  yükselen (`guc_giris`); veri <250 gün (yeni arz) alınmaz; 'kaçan aday' sayacı (`atla_n`) tutulmaz (her gün çok aday var).
  🔐 Kırılımcı + kâr kilidi (`kilitli_kirilimci`, tur `kirilim`, `kar_kilit: (0.08, 0.05)`): v3 girişi + %20 iz; tepe kapanış alışın
  ≥%8 üstüne çıktıysa stop = max(tepe×0,80, alış×1,05), kalıcı (alış = maliyet/(1+komisyon); scratchpad finalcikis kafa kafaya testi 'A4';
  ilk sürüm +%10 'A1' idi). Parametreler 2017-21'de
  seçildi (Bulutçu kijun→bulut çıkışı, Zirveci iz %15→%20, Para akışı −0,05→−0,10; Güçlü kullanıcının 6/3'ü — komşular 17-21'de hep zayıf).
  **Sonuç (5 yıl replay, tümü):** Güçlü +%2.740, Şabloncu +%1.651, Bulutçu +%4.238, Zirveci +%2.065, Para akışı +%2.151, Kâr kilidi +%1.635 (isabet %66, Kırılımcı %56)
  (Kırılımcı +%931, BIST 100 +%727); şans yüzdeliği tümünde 92-100. AMA 10 yıllık testte (2017-21) güç robotlarının çoğu küçük hisselerde
  çöktü (Güçlü 17-21 +%4, BIST 100'e göre −42 puan, düşüş −%67); ana listede ılımlı. Güçleri 2022-26 yüksek enflasyon yükselişinden.
  **Canlı yol:** `sinyal.guc_puani(d, ham=True)` → `analiz_et` `gh` (panoya gömülmez; tenkan/kijun/bulut üst-alt/c26/dip20/s50/cmf/cmf1)
  → `oda.ozet_hazirla` `g` (`guc_ozet`) + `kisa`. Replay: `oda_replay.guc_seri` (aynı formüller) + `guc_aday` (gun_verisi'ne aday).
  Panodaki canlı v3 kâr kilitli (bkz. '🔐 Kâr kilidi'); oda robotlarına `tarama` kilitsiz `tk_oda`'yı `tk` olarak verir, replay
  `ozellik` `kar_kilit=False` → güç robotları ve eski robotlar kilitten etkilenmez; 🔐 robot kilidi kendi içinde uygular.
  Test: canlı alanlar = replay alanları 556 hisse-günde puan/bileşenler 0 fark (fiyat düzeyleri 12'sinde sabit çarpanla farklı: sonradan
  gelen bölünme düzeltmesi, kararları etkilemez). **Bilinen eski fark:** Yahoo bazı hisselere tatil satırı (25 Aralık vb.) koyuyor,
  replay sadece BIST 100 günlerini alıyor → canlıda o hisselerin göstergeleri hafif farklı (tüm robotlar için, yeni değil).
  `oda_oynat` = tek robot `calistir` 20/20; eski 14 robot önce/sonra birebir (işlemler, kasa, şans, kaçanlar, olaylar, şans dosyası);
  eski oda.json'a 6 robot o gün 100.000 TL ile eklendi; canli_calistir 0,45 → 0,9 sn. Sayfa: salon derinliği 17,8 (viewBox −860 −185
  1660 1030), '💪 GÜÇ ROBOTLARI' sırası y=8,8, Yapay zekâ köşesi y=12,4, 🔐 'ÇIKIŞ DENEMESİ' [9,6, 12,4], Birikim y=15,5, Bekçi [14,6, 9,5];
  390/1280 px 7 senaryoda taşma/JS hatası yok. Yeni neden kodları gp/bu/kj/d20/cm/kk. oda_replay.json 693 → 1.009 KB (gzip 235 → ~335 KB;
  6 robot), replay ~4-7 dk (ikiz testleri), sans dosyası aynı.
- **2026-10-20: 6 yarışmacı daha → 26 robot (dal `guc-robot2`; analiz scratchpad `bulutcu/RAPOR.md` + `ucretli/RAPOR.md`, testler
  `gucrobot2/`).** Hepsi 10 yuva, 🛡️ Bekçi, riskli/kısa geçmişli hisse yok, sıra = güç puanı yüksek önce, eşitse son 20 günde az yükselen
  (`guc_giris`; hepsi `GUC_TUR`'da, 'kaçan aday' sayacı yok). AL koşulu 'durum' (sürdükçe aday), Weinstein hariç.
  📶 ADX yön (`adxci`, tur `adx`): güç bileşeni b[4] (ADX14 > 25 ve +DI > −DI) al; kapanışta −DI > +DI sat (iz yok).
  〽️ EMA 10/30 (`emaci`, `ema`): b[5] al, b[5] yanlış (EMA10 ≤ EMA30) sat. ⚖️ RSI 50 (`rsi50`, `rsi50`; id `rsi` = ↩️ dönüşçü): b[6]
  al, RSI ≤ 50 sat. (`GUC_BILESEN` = {adx: 4, ema: 5, rsi50: 6}.) ☁️🔐 Bulutçu + kâr kilidi (`bulutcu_kilit`, tur `bulut`,
  `kar_kilit: (0.08, 0.05)`, iz YOK): Bulutçu girişi; bulut altı kapanış VEYA tepe kapanış ≥ alış×1,08 olduktan sonra kapanış < alış×1,05.
  📐🔐 Şabloncu + kâr kilidi (`sablon_kilit`, tur `sablon`, `iz: 0.20` + `kar_kilit`, `kendi_cikis: False`): şablon girişi, çıkış sadece
  %20 iz + A4 (şablon bozulması çıkış değil). 🪜 Weinstein evre 2 + kâr kilidi (`weinstein`, tur `weinstein`, iz %20 + A4): kapanış >
  SMA200, SMA200 > 20 gün önceki, Mansfield RS = (hisse/XU100) ÷ SMA250(hisse/XU100) − 1 > 0 — üçü bugün İLK KEZ birlikte (dün değil)
  → al (`sinyal.weinstein_evre2`, scratchpad `ucretli/gosterge.weinstein(n=200)` ile 286 hissede 506.407 hisse-gün 0 fark; sadece
  XU100 günleri, Yahoo tatil satırları atılır).
  **Kod:** `oda.robot_karar` kâr kilidi artık iz stop'suz robotta da (`if kk:`; `iz_sev is None` ise stop = kilit seviyesi; satış notunda
  `iz` = o seviye) — iz'li robotlarda davranış aynı (20 eski robot birebir). `guc_ozet` alanları tek listede `oda.GUC_HAM` (+ `pdi`,
  `ndi`, `w2`, `w2d`); canlı: `guc_puani(ham=True)` pdi/ndi, `analiz_et` w2/w2d (try/except; 286 hissede +0,13 sn); replay:
  `guc_seri` g_pdi/g_ndi, `ozellik` g_w2/g_w2d, `guc_aday` bu robotlar varsa b4/b5/b6 ve Weinstein giriş günü (aday kümesi büyür ama
  eski robotların kararları ondan bağımsız — test edildi). Yeni neden kodları di/em/r50. Sayfa: salon derinliği 21,2 (viewBox
  −1015 −185 1815 1110); '💪 GÜÇ ROBOTLARI' y=8,8 (5), '💪 TEK BİLEŞEN' y=12,2 (📶 〽️ ⚖️), '🔐 ÇIKIŞ DENEMESİ · KÂR KİLİDİ' [8,6-16,7 ×
  11,4-17,4]: 🔐 Kırılımcı, ☁️🔐, 📐🔐 (y=12,2) + 🪜 [11,8, 15,6]; Yapay zekâ köşesi y=15,6 solda; 💰 Birikim y=19,0; `#kart=` artık alt
  çizgili id'leri de açar (eskiden `kilitli_kirilimci` açılmıyordu).
  **Testler (hepsi geçti):** `oda_oynat` = tek robot `calistir` 26/26; eski 20 robot önce/sonra birebir (işlemler, kasa, şans, kaçanlar,
  olaylar; `oda_replay_sans.json` aynı; önce çıktısı git'teki oda_replay.json ile `uretim` hariç aynı); canlı alanlar = replay 556
  hisse-günde puan/bileşen/w2 0 fark (fiyat düzeyleri bilinen 12 bölünme vakasında sabit çarpanla farklı, pdi/ndi 1'inde ~1e-5),
  Weinstein giriş günü ±1 240 hisse-günde 0 fark; git'teki oda.json (20 robot) + yapay 20.10 mumu → 6 yeni robot o gün 100.000 TL ile
  eklendi, eski 20 robotun durumu ve olayları kodun eski hâliyle birebir, Telegram metni aynı (sadece sıra numaraları); `node --check`;
  CDP 390/1280 px 10 senaryo + 6 kart: yatay taşma ve JS hatası yok, etiket–etiket/etiket–figür çakışması yok (etiketin arka sıradaki
  masanın ekran üstüne ~10 px binmesi eski düzende de var). **Boyut:** oda_replay.json 1.009 → 1.329 KB (gzip 336 → 432 KB; robot
  başına ~53 KB, en büyük ⚖️ RSI 50'nin 521 alımı); replay ~13 dk (950 sn). Küçültme (uygulanmadı, sayfa biçimi değişir): kilitli
  tabanda 'satılamadı' olaylarını sayıya çevirmek (~60 KB), güç robotlarının alım notunu atmak (~8 KB/robot), `d`'yi fark kodlamak.
  **5 yıl replay (2021-10 → 2026-10, tümü):** ☁️🔐 +%7.750 (yılda +%139, düşüş −%33, isabet %64), 📐🔐 +%4.246, 〽️ +%4.153 (düşüş
  −%42), 🪜 +%2.719 (isabet %68), ⚖️ +%2.684 (düşüş −%48, 521 alım), 📶 +%1.451; ☁️ +%4.238, 🔐 Kırılımcı +%1.635, 🚀 +%931, BIST 100
  +%727; şans yüzdeliği (tümü) 96-100. 10 yıllık sınavın ışığında oku (aşağıda).
  **Bulutçu analizinin özeti (scratchpad `bulutcu/RAPOR.md`, 10 yıl, Bekçisiz motor, ana 123 / küçük 163):**
  1. 'Onlarca kat' algısı: 5 yılda +%4.238'e karşı +%931 = yılda +%113'e karşı +%59 (BIST 100 +%53); bileşik büyüme farkı büyütüyor.
     Ana listede Bulutçu v3'ün gerisinde (5 yıl +%498 / yılda +%43 vs +%1.278 / +%69); farkın tamamı küçük hisselerden.
  2. Küçüklerdeki kâr Ichimoku'dan değil: hayatta kalan yanlılığı (bugünkü küçük listesi geçmişte zaten yükselmiş; rastgele hisse alıp
     bulut altında satan ikiz de 10 yılda ×113, Bulutçu şans yüzdeliği 62, ana listede 14) + birkaç dev işlem (TERA +%3.296, RTALB
     +%1.430, ODINE +%1.046; en iyi 10 işlem sıfırlanınca küçüklerde yılda +%73 → +%22). Bedeli: küçüklerde Ağu → 16 Eki 2026 −%70.
  3. Diğer güç bileşenleri (ADX, EMA, RSI 50) aynı desen: küçüklerde v3'ten çok (yılda +%54…+%87, düşüş −%50…−%73), ana listede v3
     yanında; 2017-21'de seçilen sıra 2022-26'da küçüklerde tutmuyor (sıra benzerliği 0,26). Sağlam tek istisna 📐 Şabloncu + A4
     (ana listede iki dönemde de dengeli puanda 1., yılda +%66, şans 98; küçüklerde v3+🔐 kadar).
  4. Kâr kilidi isabet aracı (her robotta +6…+20 puan), getiriye etkisi ± (26 durumun 12'sinde arttı); en çok Bulutçu'ya yarıyor: ana
     listede yılda +%36 → +%52, isabet %38 → %56, düşüş −%38 → −%30, şans 14 → 90, 9 yılın 8'inde daha iyi. Çok işlem yapan (RSI 50,
     Şabloncu kendi çıkışı) robotlarda gereksiz.
  5. **Hüküm: panodaki AL/SAT değişmez — v3 + 🔐 A4 kalır** (iki listede de en az düşüş, rastgele ikizin belirgin üstünde: şans 95/88).
     Bulutçu'ya geçmek ana listede kötüleştirir; 'v3 + bulut üstü şartı' iki listede de kötü. Yeni robotlar odada yarışmacı olarak izlenir;
     Nisan 2027'de canlı karneyle yeniden bakılacak (📐🔐 ana listede canlıda da v3+🔐'ü geçerse panoya aday olur, bugün değil).
  🪜 Weinstein (scratchpad `ucretli/RAPOR.md` 'Aday 2'): kanıt zayıf DENEME robotu — 10 yılda ana +%49 / küçük +%75 yılda, isabet %71/%66,
  dengeli puanda canlının gerisinde; panoyla farkını gerçek zamanda görmek için.
- **2026-10-20: 🔐📉 Daralan iz → 27 robot (dal `daralan-iz`; araştırma scratchpad `kademeli/RAPOR.md`, testler `daralan/`).**
  `daralan`, tur `kirilim` (giriş 🚀 Kırılımcı / 🔐 Kırılımcı ile aynı: kilitsiz v3 `tk`, 10 yuva, Bekçi, filtre), `iz: 0.20`,
  `kar_kilit: (0.08, 0.05)`, `daralan: (0.30, 0.75, 0.08)`. Çıkış 'K2': g = tepe kapanış / alış − 1; iz = min(%20, max(%8,
  0,30 / (1 + 0,75·g))); çizgi = max(tepe × (1 − iz), kilit) — kilit = tepe ≥ alış×1,08 olunca alış×1,05 (A4); kapanış < çizgi → SAT
  (kilitli tabanda bekler). Tepe ve g yalnız artar → çizgi hiç inmez. Tablo: +%50'ye kadar %20, +%75 %19, +%100 %17, +%150 %14,
  +%200 %12, +%300 %9, +%400 ve üstü %8 (+%30'a kadar çizgiyi kilit belirler). **Kod:** çizgi TEK yerde `oda.stop_seviyesi(robot,
  alış, tepe)` → (çizgi, 'kk'|'iz'|None) + `oda.iz_orani` (daralan yoksa `robot['iz']`); `robot_karar` bunu kullanır (eski robotlar
  birebir). Satış nedeni 'daralan iz (tepe X, iz %Y)' → replay neden kodu `dz` (kilit kırılırsa yine `kk`). Salon: '🔐 ÇIKIŞ
  DENEMESİ · KÂR KİLİDİ' köşesinde 🔐 Kırılımcı'nın önünde [9,1, 15,6] (kısa ad 'Daralan iz', renk #FCA5A5).
  **Aynı commit'te düzeltme:** 🧲 Dip avcısının '20 işlem günü doldu' satışları replay'de neden kodu '?' yazılıyordu (eşleşme 'gün doldu'
  arıyordu) → artık `sr`; işlemler/kasa değişmedi (test edildi).
  **Testler (hepsi geçti):** oda dışı, işlem işlem: `oda.stop_seviyesi` = `kademeli/motor3.py` K2 (10y 286 hisse, 2.361 işlem, 0 fark;
  aynı düzenekle 🔐 Kırılımcı = motor3 A4 2.280 / 🚀 = kilitsiz 1.783, 0 fark; iz tablosu aynı; `t_motor3.py`). `oda_oynat` = tek robot `calistir` 27/27; eski 26 robot önce/sonra birebir (işlemler, kasa, şans, kaçanlar,
  olaylar; `oda_replay_sans.json` aynı; 🧲'de tek fark 43 satışın kodu '?' → 'sr'; önce çıktısı git'tekiyle `uretim` hariç aynı); git'teki
  canlı oda.json (20 robot, 19.10) + yapay 20.10 mumu → 7 yeni robot (🔐📉 dahil) o gün 100.000 TL ile eklendi, eski 26 robotun durumu
  kodun eski hâliyle birebir, Telegram yalnız sıra numaraları kaydı; `node --check`; CDP 390/1280 px (canlı, #rep, tümü, #kart=daralan):
  yatay taşma ve JS hatası yok, etiket–etiket / etiket–figür çakışması yok. **Boyut:** oda_replay.json 1.329 → 1.388 KB (gzip 431 →
  451 KB), replay ~6-8 dk. **5 yıl replay (2021-10 → 2026-10, tümü):** 🔐📉 Daralan iz +%1.406 (yılda +%72, düşüş −%30, isabet %61,
  189 alım, son 1 yıl +%18, şans 88 / 1y 55) · 🔐 Kırılımcı +%1.635 (+%77, −%26, %66, son 1 yıl +%33, şans 97 / 86) · 🚀 Kırılımcı
  +%931 (+%59, −%32, %50, +%9, şans 79 / 45) · BIST 100 +%727. Odada da 🔐'ün gerisinde (araştırmadaki 'canlıdan anlamlı iyi değil' ile uyumlu).
  **Kademeli iz araştırmasının özeti (scratchpad `kademeli/RAPOR.md`; 1.383 ayar, 5 aile, kilitli/kilitsiz, 200 yarım liste):**
  1. **Kâr kilidi asıl işi yapıyor.** Kilit açıkken iz daraltmanın katkısı küçük (dengeli puanda +20…+85; kilidin v3'e katkısı +522).
     Kilit kapatılıp yerine daraltma konunca hepsi canlının çok gerisinde (−380…−455). ATR ailesi hiçbir ayarda canlıyı geçmedi.
  2. **Tek bir 'en iyi oran' yok.** 2017-21'de en iyi çıkan ayar her ailede 2022-26'da sıranın ortasına düşüyor (ve tersi); geniş
     düzlük var, belirgin zirve yok. 2017-21 'erken ve hafif sıkılaştır', 2022-26 'ilk kata kadar dokunma' diyor.
  3. **Kullanıcının '+%90 kârda %8-9 iz' fikri (K4) büyük trendleri kesiyor:** en büyük 20 kazanandan alınan kâr canlının %65'i,
     sepet %83/%91, ana 10 yuva %83; GLYHO zinciri +%219 → +%37, ASELS +%419 → +%211 (erken satıp daha yukarıdan yeniden alım).
  4. **K2 zararsız ama anlamlı değil:** toplam kârı koruyan tek aday (sepet %100/%99, 10 yuva %119/%129), ama fark neredeyse tamamen
     2022 sonrası (2017-21 ~0), son 12 ayda canlıdan biraz kötü, KTLEV +%1.543 → +%590. **Hüküm: canlı (v3 + %20 iz + 🔐) değişmez;
     K2 odada yan robot olarak karne tutar** (Nisan 2027'de 🔐 Kırılımcı ile canlı karneye bakılacak).
- **2026-10-20: ⏩ Erken kırılımcı → 28 robot (dal `erken-giris`; araştırma scratchpad `erkengiris/RAPOR.md` 'Q', testler
  `erkenrobot/`).** `erken_kirilim`, tur `erkenkir`, 10 yuva, Bekçi, filtre, `iz: 0.20` + `kar_kilit: (0.08, 0.05)` (çıkış 🔐 Kırılımcı
  ile aynı). Giriş: v3 kırılımının aynısı ama şablonda 150 günlük şartlar (fiyat > SMA150, SMA150 > SMA200, SMA50 > SMA150) yerine
  SMA50 > SMA200 (`sinyal.trend_sablonu(d, erken=True)`, `trend_kirilimi(..., erken=True)`); giriş zinciri kilitsiz (oda robotları
  gibi) → `sinyal.erken_kirilim(d, xu_ust)` = {bugun, seviye} → `analiz_et` `tq` (panoya gömülmez) → `oda.ozet_hazirla` `tq`; replay
  `ozellik` `tq_bugun` (+ `aday`'a eklenir, `ozet` `tq`). Canlı pano v3 DEĞİŞMEDİ. Alım notu = kırılan 20g zirvesi; 'kaçan aday' `atla_n`.
  Salon: 🔐 köşesi [14,5, 15,6] (kısa ad 'Erken kırılım', renk #67E8F9). BRSAN'da AL 24.08 yerine 14.08.
  **Testler (hepsi geçti):** canlı `trend_kirilimi(erken=True)` + `gercekci_cikis` = erkengiris motoru işlem işlem, 10y 286 hisse: Q+A4
  2.711, kilitsiz Q 2.082, kontrol v3+A4 2.280 işlem — 0 fark (`t_q.py`); canlı `tq` (analiz_et 4 yıl → ozet_hazirla) = replay
  1.051 hisse-günde (584 ⏩ sinyal günü dahil) `bugun` 0 fark, `tq` = `trend_kirilimi(erken=True)['bugun']`; `seviye` 28'inde sabit
  çarpanla farklı (bilinen sonradan bölünme düzeltmesi, sadece alım notu) (`t_ozellik.py`); `oda_oynat` = tek robot `calistir` 28/28;
  eski 27 robot önce/sonra AYNI veriyle (gucrobot/veri_oda.pkl) birebir (işlemler, kasa, şans, kaçanlar, olaylar, şans dosyası);
  git'teki canlı oda.json (19.10) + yapay 20.10 → eski 27 robot durumu birebir, ⏩ o gün 100.000 TL ile eklendi, Telegram yalnız sıra
  numaraları; analiz_et 257 hisse 7,9 → 8,3 sn; `node --check`; CDP 390/1280 (canlı, #rep, tümü, #kart=erken_kirilim): sayfa taşması ve
  JS hatası yok (390'da kart içindeki aylık tablo kendi kaydırmalı kutusunda — eskiden de öyle), etiket çakışması yok.
  **oda_replay.json yeniden üretildi (gerçek veri, MANIPULE'siz yeni evren, 2021-10 → 2026-10):** ⏩ +%738 (son 1 yıl +%4, düşüş −%30,
  isabet %63, 187 alım, şans 94) · 🔐 Kırılımcı +%1.694 · 🚀 Kırılımcı +%1.103 · BIST 100 +%696. Fon krizi hisseleri çıkınca güç robotları
  belirgin düştü (☁️🔐 +%7.750 → +%1.920, 〽️ +%4.153 → +%1.934, ☁️ +%4.238 → +%1.918, 💪 +%2.740 → +%1.384); 📐 Şabloncu +%1.651 →
  +%2.883, 🔐 Kırılımcı ve 🔐📉 neredeyse aynı. Uzun oyun kaotik (evren değişince her robotun yolu değişir) → farkın tamamı fon krizi
  hisselerine yazılamaz; tablo scratchpad `manipule/tablo_robot.txt`.
- **Workflow değişti** (`tarama.yml`: `git add ... oda.json oda.html`). GITHUB_TOKEN workflow dosyasını güncelleyemediği için
  **fork'taki arkadaşlar bu satırı elle güncellemeli**; güncellemezlerse oda her taramada sıfırdan başlar ve kaydedilmez (ilk gün
  sessiz kuralı sayesinde Telegram'a mesaj gitmez), panodaki düğme `oda.html` bulunamaz.
