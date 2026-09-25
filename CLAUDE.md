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

## Dosyalar
- `sinyal.py` — gösterge + sinyal çekirdeği. **Tek kural seti** (canlı tarama + backtest ortak).
  SuperTrend, MACD, EMA20/50, RSI, Stochastic oy verir; ADX/Bollinger bağlam. `analiz_et(df)`
  son gün özetini döndürür (sinyal, uyum, detay, sinyal_gun, giris_stop, hedef, spark...).
- `tarama.py` — evren (BIST100 + EK_HISSELER + izleme listesi), oran önbelleği (F/K, PD/DD, FD-FAVÖK günde 1),
  yorum üretimi, sinyal geçmişi (gecmis.json), Telegram. Ayarlar dosyanın başında.
- `pano.py` — `index.html` ve `gecmis.html` üretir. Portföy istemci tarafında (localStorage),
  modalda kendi SVG grafiğimiz + TradingView butonu.
- `backtest.py` — ertesi-gün girişli, komisyonlu, al-tut kıyaslı simülasyon.

## Önemli ilkeler
- Sinyal kuralları tek yerde (`sinyal.py`); backtest ve canlı aynı motoru kullanmalı.
- Backtest'te look-ahead yasak; işleme ertesi gün girilir; çift yön %0.2 maliyet düşülür.
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
2. **Hacim/likidite filtresi:** düşük hacimli/az işlem gören hisseleri ele veya işaretle
   (yanıltıcı sinyalleri azaltır).
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
güncellenmeli; yfinance BIST bedelsiz/bölünme kaydı tutmuyor, arzdan beri getiri bölünmede yanılır.
Fon krizinde çöken şişirilmiş hisseler (TERA, SMRTG, GENIL, MIATK) listeden çıkarıldı; kullanıcı
isteğiyle faiz yüzünden düşen eski büyükler (KONTR vb.) KALDI — tüm çökenleri çıkarma.

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
  Alternatifler (altın kesişim: kırılgan; haftalık MACD: +8.5/+2.2) daha zayıf. SMA200 için tarama 2 yıl veri çeker.
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
- Fiyat alarmı: panoda hisse penceresinden kurulur, `ALARMLAR` variable'ına (portföyle aynı anahtar) yazılır;
  her taramada (gün içi de) kontrol, her alarm bir kez çalar. durum.json herkese açık olduğundan sadece
  alarmın sha1 özeti (`alarm_tetik`) saklanır; silinen alarmın kaydı temizlenir.
- Taban serisi: son 15 günde ≥4 kez ≤ −%9 → "⚠ taban serisi"; bu hisselerden AL mesajı gitmez.
- SAT: 1. gün "⏳" işaretiyle gösterilir/bildirilir, 2. gün "✅ teyit" mesajı (portföy).
- Portföy: çıkış = son AL başındaki sabit stop (`al_stop`), SAT'ta çıkış sebebi sinyal; hedefler
  küçükten büyüğe (en yakın direnç, 2R). Günlük portföy özeti 18:00 sonrası ilk taramada.
- Python (`tarama.pozisyon_plani`) ve JS (`pano.pozPlan`) aynı mantık — birini değiştirirsen ikisini de.
- Şablon (pano.py `_SABLON`) raw string içinde JS: tek tırnaklı JS dizelerinde kesme işareti `\'` olmalı;
  değişiklikten sonra şablon JS'ini `node --check` ile doğrula (bir kez sayfayı tamamen bozuyordu).
