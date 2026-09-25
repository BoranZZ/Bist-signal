# BIST Sinyal Sistemi

Hafta içi, piyasa saatlerinde **~15 dk'da bir** çalışır: BIST 100'ü tarar, panoyu günceller, yeni AL'leri (ve portföyündeki yeni SAT'ları) Telegram'a yollar. Ücretsiz (public repo + Actions + Pages). Veri ~15 dk gecikmeli olabilir.

## Sayfalar
- **index.html** — ana pano: Portföyüm bölümü + tüm hisseler. Satıra tıkla → grafik + o hisseye özel yorum + TradingView.
- **gecmis.html** — Sinyal Geçmişi (canlı karne): açık takipler + kapanmış sinyaller + isabet oranı.
- **backtest.html** — geçmiş simülasyonu (elle çalıştırılır).

## Dosyalar
`sinyal.py` (kurallar) · `tarama.py` (tarama+pano+Telegram, ayarlar en üstte) · `pano.py` (pano+geçmiş sayfası) · `backtest.py` · `requirements.txt` · `.github/workflows/tarama.yml` (15 dk) · `.github/workflows/backtest.yml` (elle)

## Portföyün (artık butonla)
Panoda **Portföyüm → + Ekle** ile hisse/adet/maliyet girersin; **cihazında** saklanır (dosya düzenlemeye gerek yok). Her satırda kâr/zarar, güncel sinyal ve SAT uyarısı; ✕ ile silersin. Tüm hisseler yine taranır — bu sadece senin pozisyonların. Telegram'ın da bilmesi için aşağıdaki "Portföyü Telegram'a tanıtmak" adımına bak.


## Sinyal geçmişi (canlı karne)
Sistem AL dediği anki fiyatı `gecmis.json`'a kaydeder; stop yerse ya da sinyal SAT'a dönerse kapatıp sonucu yazar. `gecmis.html`'de birikir. Bu **ileriye dönük gerçek** performanstır (bugünden itibaren). `gecmis.json` otomatik oluşur, elleme.

## Backtest (geçmiş simülasyonu)
Actions → **Backtest (elle)** → **Run workflow**. Gerçek 2 yıllık veriyle çalışır, `backtest.html` üretir. Sinyal kapanışta oluşur, işleme ertesi gün girilir, çift yön %0.2 komisyon düşülür, al-tut ile kıyaslanır.

## Ayarlar (`tarama.py` en üstü)
`BIST100` (endeks listesi, 3 ayda bir güncellenmeli) · `EK_HISSELER` (endeks dışı ama taranan) · `PORTFOY_TL`, `RISK_YUZDESI` (öneri lot) · `ASIRI_ISLEM_ESIGI`.

## Otomatik çalışma (cron-job.org)
GitHub'ın kendi zamanlayıcısı ücretsiz hesapta saatlerce gecikebiliyor ya da hiç çalışmayabiliyor. Asıl tetikleyici ücretsiz **cron-job.org**; `tarama.yml`'deki zamanlama yedek olarak duruyor. Bir kez kurulur:
1. **GitHub anahtarı:** GitHub → sağ üstte profil resmi → **Settings** → en altta **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
   - Token name: `cron-job`
   - Expiration: en uzun süre (bitmeden yenile)
   - Repository access: **Only select repositories** → `Bist-signal`
   - Permissions → Repository permissions → **Actions: Read and write**
   - **Generate token**'a bas, çıkan anahtarı kopyala. Bir daha gösterilmez; kimseyle paylaşma.
2. **cron-job.org:** Üye ol → **Create cronjob**.
   - URL: `https://api.github.com/repos/BoranZZ/Bist-signal/actions/workflows/tarama.yml/dispatches`
   - Execution schedule → **Custom**: dakika `0,15,30,45`; saat `10-18`; gün: Pazartesi–Cuma. Saat dilimi: `Europe/Istanbul`.
   - **Advanced** sekmesi:
     - Request method: **POST**
     - Request body: `{"ref":"main"}`
     - Headers (4 satır):
       - `Accept: application/vnd.github+json`
       - `Authorization: Bearer <kopyaladığın anahtar>`
       - `X-GitHub-Api-Version: 2022-11-28`
       - `Content-Type: application/json`
   - Kaydet → **Test run**. Sonuç **204** olmalı. Ardından GitHub'da Actions'ta yeni bir tarama başlar.

## Telegram
Mesaj şu durumlarda gelir:
- **Yeni AL:** Taranan tüm hisselerde. Hacmi yüksek AL'ler "📈 hacim" etiketiyle işaretlenir (bilgi amaçlı; backtest'te tek başına belirgin üstünlük sağlamadı). Piyasa zayıfsa (BIST 100 50 günlük ortalamasının altında) mesajda uyarı olur. Son 15 günde 4+ kez taban olan hisselerden AL mesajı gitmez.
- **Portföyündeki hisselerde:** Satırın başında ❗ olur. Altında şunlar yazar: kâr/zararın, 📍 çıkış seviyesi (stop) ve 🎯 hedefler (en yakın direnç ve risk/ödül 2:1).
- **Yeni SAT:** Sadece portföyündeki hisselerde. İlk gün "⏳ 1. gün, yarını bekle" diye gelir; ertesi gün de SAT kalırsa "✅ teyitlendi" mesajı gelir.
- **Zamanlama:** AL/SAT mesajları kapanıştan sonra (18:30 sonrası ilk tarama) gelir; gün içindeki sinyallerin ~%22'si kapanışta değiştiği için.
- **Uzun vade:** Portföyde "Uzun vade" işaretli hisselerde SAT bilgi olarak gelir; çıkış yerine 🧭 karar çizgisi (ana destek) gösterilir, kapanışla kırılırsa tek seferlik uyarı gelir.
- **Haftalık özet:** Cuma kapanıştan sonra: haftanın AL'leri, canlı karne, portföyün haftalık değişimi.
- **Günlük portföy özeti:** Hafta içi kapanıştan sonra (18:30+) bir kez. Sektör dağılımı ve tek sektöre yoğunlaşma uyarısı dahil. Her hisse için sinyal, K/Z, çıkış ve hedefler, dikkat notları (stop'a yakın, dirence yaklaşıyor, taban serisi).

AL ile NÖTR arasında gidip gelen hisse tekrar mesaj atmaz. Sinyalin önce SAT'a, sonra tekrar AL'e dönmesi gerekir. Listeye yeni eklenen hisse, ilk tarandığı turda mesaj atmaz.

**Portföyü Telegram'a bağlamak (her cihazda bir kez):** Panoda Portföyüm'ün altındaki **Telegram'a bağla**'ya bas, ekrandaki adımlarla bir GitHub anahtarı oluştur ("Variables: Read and write" yetkili) ve yapıştır. Sonrasında:
- **+ Ekle / ✎ / ✕** ile yaptığın her değişiklik GitHub'daki `PORTFOY` variable'ına otomatik kaydedilir, sonraki taramanın Telegram mesajları buna göre çıkar.
- **Aynı hisseyi tekrar eklersen** adetler toplanır, maliyet ağırlıklı ortalama olur.
- **Cihazlar arası eşitleme:** Anahtarı girdiğin başka bir cihaz portföyü GitHub'dan alır. Telefonda ve bilgisayarda aynı portföyü görürsün.
- **Gizlilik:** `PORTFOY` herkese açık değil. Onu sadece sen ve anahtarlarını görebilir; sistem portföyünü loglara yazmaz. Anahtar sadece girdiğin cihazda saklanır, kaldırmak için "Bu cihazdaki bağlantıyı kaldır".

Bağlantıyı denemek için: Actions → **BIST Sinyal Taraması** → **Run workflow** → **"Telegram'a test mesajı gönder"** kutusunu işaretle → Run. Mesaj gelmezse tarama kırmızı biter; "Taramayı çalıştır" adımında Telegram'ın verdiği hata yazar:
- *bilgi yok*: GitHub → Settings → Secrets and variables → Actions'ta `TELEGRAM_TOKEN` ve `TELEGRAM_CHAT_ID` tanımlı değil.
- *401 Unauthorized*: Token yanlış. BotFather'dan aldığın anahtarı tekrar kopyala.
- *400 chat not found*: Chat ID yanlış, ya da bota Telegram'dan hiç **/start** yazmadın.

## Mevcut repo'yu güncelleme
1. **Add file → Upload files** → şunları sürükle (üzerine yazılır): `sinyal.py`, `tarama.py`, `pano.py`, `backtest.py`, `requirements.txt`, `README.md` → Commit.
2. `.github/workflows/tarama.yml`'i aç → ✏️ → içeriği yenisiyle değiştir → Commit.
3. **Add file → Create new file** → ad: `.github/workflows/backtest.yml` → paketteki içeriği yapıştır → Commit.
4. **Actions → BIST Sinyal Taraması → Run workflow** (bir kez elle).

## Göstergeler (çoklu, şeffaf)
Artık tek bir karar yerine **5 popüler gösterge ayrı ayrı** oy veriyor; genel sinyal bunların uyumundan çıkıyor. Tabloda "Uyum" sütunu (ör. 4/5), hisseye tıklayınca her göstergenin ayrı AL/SAT durumu:
- **SuperTrend** (ATR tabanlı trend) — fiyat çizginin üstünde mi? Grafikte kırmızı çizgi olarak da görünür.
- **MACD** — momentum yönü. **EMA 20/50** — kısa/uzun ortalama dizilimi. **RSI** — aşırı alım/satım. **Stochastic** — kısa vadeli zamanlama.
- Bağlam (oy vermez): **ADX** (trend gücü) ve **Bollinger** (banda göre konum).

Eşikleri `sinyal.py` başından ayarlarsın (`AL_ESIK`, `SAT_ESIK`). Uyarı: çoğu gösterge trendi ölçtüğü için birlikte hareket eder; "daha çok gösterge = daha isabetli" değildir. Hangi kurgunun işe yaradığını **backtest + canlı karne** söyler.

## Sinyal zamanlaması ve çıkış
Her sinyalin **ne zaman başladığı** artık belli:
- Tabloda **"Sinyalde"** sütunu: kaç gündür o sinyalde (ör. `1g`, `12g`). **YENİ** etiketi = bugün AL'a döndü. Taze AL'ler listenin en üstünde.
- Hisseye tıklayınca: sinyal başlangıç tarihi, **başlangıçtan beri % değişim** (hareketi kaçırdın mı görürsün) ve **çıkış kuralı**: "sinyal SAT'a dönerse ya da stop X TL altına inerse çık." Ayrıca mekanik bir **2R örnek hedef** (tahmin değil, referans).
- Telegram zaten sadece **yeni** AL'de (ilk döndüğü an) mesaj atar — yani "kaçırdığın eski AL" değil, tazesi gelir.

Ne kadar tutmalı? Bu sistem **hedefe göre değil kurala göre** çıkışlıdır: pozisyonu sinyal AL kaldıkça / stop üstünde durdukça tutar, SAT'a döndüğünde ya da stop yediğinde bırakırsın. "3 gün / 5 gün" gibi sabit bir süre yok; piyasa karar verir, sen kurala uyarsın.

## Dürüst notlar
Yatırım tavsiyesi değildir; senin yerine işlem yapmaz. Göstergeler geçmişe bakar, geleceği garanti etmez. Stop-loss'u ciddiye al. F/K'nın mutlak "iyi" eşiği yoktur; grup medyanına göre görecedir ve enflasyonda yanıltıcı olabilir.
