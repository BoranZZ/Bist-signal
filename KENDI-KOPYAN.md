# Kendi kopyanı kur (arkadaşlar için)

Bu rehberle panonun **tamamen sana ait bir kopyasını** kurarsın: kendi siten, kendi Telegram botun, kendi portföyün.
Boran'ın portföyünü göremezsin, o da seninkini göremez; birbirinizin mesajlarını almazsınız.
Hepsi ücretsiz. Bir kez yapılır, ~20-30 dakika sürer. Yatırım tavsiyesi değildir; karar her zaman senin.

Gerekenler: bir GitHub hesabı (github.com → Sign up) ve Telegram.

## 1. Kopyayı oluştur (fork)
1. https://github.com/BoranZZ/Bist-signal adresini aç.
2. Sağ üstte **Fork** → adı **değiştirme** (`Bist-signal` kalsın) → **Create fork**.
3. Artık `https://github.com/<kullanıcı-adın>/Bist-signal` senin.

## 2. Otomatik taramayı aç
1. Kendi kopyanda **Settings** → soldan **Actions** → **General** → en altta **Workflow permissions** → **Read and write permissions** → **Save**.
2. Üstte **Actions** sekmesi → yeşil **I understand my workflows, go ahead and enable them**.
3. Soldan **BIST Sinyal Taraması**'na tıkla → sarı uyarı çıkarsa **Enable workflow**.

## 3. Siteni aç (GitHub Pages)
1. **Settings** → soldan **Pages**.
2. **Source: Deploy from a branch** → Branch: **main**, klasör **/ (root)** → **Save**.
3. Birkaç dakika sonra panon burada: `https://<kullanıcı-adın>.github.io/Bist-signal/` (telefonda ana ekrana ekleyebilirsin).

## 4. Telegram botunu oluştur
1. Telegram'da **@BotFather**'ı aç → `/newbot` yaz → bota bir ad ve sonu `bot` ile biten bir kullanıcı adı ver.
2. BotFather sana uzun bir **token** verir (`123456789:AA...` gibi). Kopyala, kimseyle paylaşma.
3. Yeni botunu aç ve **/start** yaz (bunu yapmazsan bot sana yazamaz).
4. Tarayıcıda şu adresi aç (TOKEN yerine kendi token'ını yapıştır):
   `https://api.telegram.org/botTOKEN/getUpdates`
   Çıkan yazıda `"chat":{"id":` sonrasındaki sayı senin **Chat ID**'n (ör. `123456789`). Boş çıkarsa bota bir mesaj daha yazıp sayfayı yenile.

## 5. Bilgileri GitHub'a gir
Kendi kopyanda **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:
- Name: `TELEGRAM_TOKEN` → Secret: BotFather'ın verdiği token → **Add secret**
- Name: `TELEGRAM_CHAT_ID` → Secret: Chat ID sayın → **Add secret**

## 6. Dene
**Actions** → **BIST Sinyal Taraması** → **Run workflow** → **"Telegram'a test mesajı gönder"** kutusunu işaretle → **Run workflow**.
3-5 dakika sonra botundan test mesajı gelir ve siten güncellenir. Kırmızı biterse README'deki Telegram hata listesine bak.

## 6b. Telegram'dan soru sor (isteğe bağlı)
Botuna şu komutları yazabilirsin: `/yardim`, `/hisse THYAO`, `/piyasa`, `/portfoy`. Cevap **anlık gelmez**: bir sonraki taramada (hafta içi piyasa
saatinde ~15 dakikada bir) gelir. Bot sadece **senin** Chat ID'ne cevap verir; başkası yazarsa yok sayar. Ek ayar gerekmez (workflow dosyası değişmedi).
Not: botun token'ını başka bir programa/webhook'a bağladıysan komutlar okunamaz (Actions logunda "HTTP 409" görürsün) — bu bot sadece bu sistem için olsun.

## 7. Portföyünü gir ve Telegram'a bağla
1. **Kendi siteni** aç (`<kullanıcı-adın>.github.io/...`). Boran'ın sitesine girdiğin portföy buraya gelmez (tarayıcı her siteyi ayrı saklar), bir kez yeniden gir.
2. **Portföyüm** altında **Telegram'a bağla** → ekrandaki adımlarla GitHub'da anahtar oluştur (Repository: kendi `Bist-signal`'in, izin: **Variables: Read and write**) → yapıştır → **Bağla**.
3. Telefonda da aynı şeyi yap (her cihaza bir kez): portföyün, favorilerin ve alarmların cihazlar arasında eşitlenir.

## 8. Daha düzenli tarama (isteğe bağlı ama önerilir)
GitHub'ın kendi zamanlayıcısı bazen saatlerce gecikiyor. README'deki **Otomatik çalışma (cron-job.org)** adımlarını uygula;
adresteki `BoranZZ` yerine **kendi kullanıcı adını** yaz.

## Güncellemeler
Boran sistemi geliştirdikçe senin kopyan her taramada yeni kodu **kendiliğinden** alır; portföyün ve ayarların değişmez.
İstemezsen: **Settings → Secrets and variables → Actions → Variables** sekmesi → **New repository variable** → `KOD_GUNCELLE` = `hayir`.
Nadiren `.github/workflows` içindeki dosyalar değişir; bunlar otomatik gelmez. O zaman Boran sana hangi dosyayı nasıl değiştireceğini söyler.
GitHub'daki **Sync fork** düğmesine basmana gerek yok (panonun kendi dosyalarıyla çakışabilir).

## Gizlilik ve güvenlik
- Kopyan herkese açık (kod ve pano). **Portföyün açık değil**: GitHub'da gizli bir değişkende durur, sistem onu loglara yazmaz.
- Telegram token'ını ve GitHub anahtarlarını **kimseyle paylaşma**. Birine anahtarını verirsen portföyünü görebilir ve değiştirebilir.
