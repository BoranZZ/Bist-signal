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

## Dosyalar
- `sinyal.py` — gösterge + sinyal çekirdeği. **Tek kural seti** (canlı tarama + backtest ortak).
  SuperTrend, MACD, EMA20/50, RSI, Stochastic oy verir; ADX/Bollinger bağlam. `analiz_et(df)`
  son gün özetini döndürür (sinyal, uyum, detay, sinyal_gun, giris_stop, hedef, spark...).
- `tarama.py` — evren (BIST100 + izleme listesi), oran önbelleği (F/K, PD/DD, FD-FAVÖK günde 1),
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
1. **Grafik:** modaldaki gömülü TradingView'i kaldır; kendi SVG grafiğini büyüt, fiyat/tarih
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
6. **Sektör dağılımı/çeşitlendirme uyarısı**, fiyat/seviye alarmı, haftalık Telegram özeti.

## Kullanıcının okumayı bilmediği şeyler (öğretilecek)
RSI, MACD ve hacim panellerinin nasıl okunacağını sade anlat (grafik dersi).
