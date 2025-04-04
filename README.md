
## Yapılandırma (`config/config.py`)

Analizi çalıştırmadan önce `config/config.py` dosyasını kendi veri setlerinize ve tercihlerinize göre düzenlemeniz **zorunludur**.

**Önemli Yapılandırma Ayarları:**

1.  **Girdi Dosya Adları:**
    *   `_PHASE_CATALOG_FILENAME`: `input_data/catalog/` içindeki katalog dosyanızın adı.
    *   `_STATION_DATA_FILENAME`: `input_data/catalog/` içindeki istasyon bilgi dosyanızın adı.
    *   `_HDF5_FILENAME`: `input_data/hdf5/` içindeki HDF5 dosyanızın adı.
    *   `_EQT_SUMMARY_FILENAME`: `input_data/eqt/` içindeki EQTransformer summary dosyasının adı (varsayılan: `summary.csv`).

2.  **Waveform İndirme Ayarları (`download_settings`):**
    *   `enable_download`: Waveform indirme özelliğini etkinleştirmek için `True`, devre dışı bırakmak için `False` olarak ayarlayın.
    *   `client_name`: Veri çekilecek FDSN istemcisinin adı (örneğin: `"KOERI"`, `"IRIS"`).
    *   `date`, `start_hour`, `end_hour`: İndirilecek verinin UTC zaman aralığı (YYYY-MM-DD formatında tarih, 0-23 arası saatler).
    *   `channel`: İndirilecek kanal kodu (örneğin: `"HHZ"`, `"BHZ"`, `"EHZ"`).
    *   `stations_to_download`: İndirilmesi istenen istasyon kodlarının Python listesi (örneğin: `["ISTA", "ANKR"]`).

3.  **Sismik Veri İşleme Ayarları (`seismic_data`):**
    *   `selected_station`: Waveform grafiği çizilecek olan istasyonun kodu.
    *   `date`, `start_hour`, `phase_component`: Grafiklenecek waveformun zaman ve kanal bilgileri. Bu bilgiler, indirilen veya `input_data/mseed/` klasöründe bulunan veriyle eşleşmelidir.
    *   `filter_type`, `freqmin`, `freqmax`, `corners`, `zerophase`: Waveform filtreleme parametreleri. Filtre uygulamak istemiyorsanız `filter_type=None` olarak ayarlayın.

4.  **Diğer Veri Kaynağı Ayarları (`catalog_data`, `hdf5_data`, `eqt_data`):**
    *   Bu bölümlerdeki dosya yolları genellikle `config.py` içinde otomatik olarak ayarlanır.
    *   Ancak, `eqt_data` içindeki `start_hour`, `end_hour`, `date` gibi grafikleme yapılacak zaman aralığını belirleyen parametreleri, analiz etmek istediğiniz aralığa göre ayarlamanız gerekebilir.

5.  **Genel Grafik Ayarları (`plot_settings`):**
    *   `figure_height`: Oluşturulacak toplam figürün piksel cinsinden yüksekliği.
    *   `figure_title`: Figürün ana başlığı.

## Kullanım

Pipeline'ı çalıştırmak için aşağıdaki adımları izleyin:

1.  **Girdi Dosyalarını Hazırlayın:**
    *   Analiz etmek istediğiniz Katalog (`.txt`), HDF5 (`.hdf5`) ve EQTransformer (`summary.csv`) dosyalarını `input_data/` klasörü altındaki ilgili alt klasörlere (`catalog`, `hdf5`, `eqt`) kopyalayın.
    *   Katalog grafiği için gerekli olan istasyon bilgilerini içeren dosyayı (genellikle `.txt` formatında) `input_data/catalog/` klasörüne yerleştirin.
    *   Eğer waveformları indirmek istemiyorsanız (`enable_download=False` ayarı ile), kullanmak istediğiniz `.mseed` dosyalarını `input_data/mseed/` klasörüne manuel olarak ekleyin. Dosya adlarının formatı `seismic_utils.py` içindeki `glob` deseni ile uyumlu olmalıdır (genellikle `ISTASYON_KANAL_NETWORK_YYYYMMDD_HHMMSS.mseed` gibi).

2.  **`config.py` Dosyasını Düzenleyin:** Yukarıdaki "Yapılandırma" bölümünde detaylandırılan ayarları, kendi verilerinize ve analiz hedeflerinize uygun şekilde güncelleyin. Özellikle dosya adlarını, zaman aralıklarını ve waveform indirme tercihlerinizi kontrol edin.

3.  **Pipeline'ı Çalıştırın:**
    Terminal veya komut istemcisini açın, projenin ana klasörüne (`seismic_analysis`) gidin ve aşağıdaki komutu çalıştırın:
    ```bash
    python main.py
    ```

4.  **Sonucu Görüntüleyin:**
    *   Kod çalışırken, terminalde ilerleme durumu hakkında bilgiler (örneğin, dosyaların okunması, waveform indirme durumu) ve olası uyarı/hatalar gösterilecektir.
    *   Eğer waveform indirme etkinleştirilmişse (`enable_download = True`), ilgili veriler `input_data/mseed/` klasörüne indirilecektir.
    *   İşlem başarıyla tamamlandığında, 4 alt grafikten oluşan interaktif bir Plotly figürü otomatik olarak varsayılan web tarayıcınızda açılacaktır. Bu figür üzerinde zoom yapabilir, pan yapabilir ve veri noktalarının detaylarını görebilirsiniz.

## Hata Ayıklama İpuçları

Pipeline çalışırken sorunlarla karşılaşırsanız aşağıdaki ipuçları yardımcı olabilir:

*   **Dosya Bulunamadı Hataları (`FileNotFoundError`):**
    *   `config.py` dosyasındaki dosya adı değişkenlerinin (`_FILENAME` ile bitenler) `input_data/` altındaki ilgili klasörlerde bulunan gerçek dosya adlarıyla tam olarak eşleştiğinden emin olun.
    *   Terminal çıktısında gösterilen dosya yollarının doğru olup olmadığını kontrol edin.

*   **Boş Grafikler:**
    *   **Sismik Veri Grafiği:** İlgili istasyon ve zaman aralığına ait `.mseed` dosyasının `input_data/mseed/` klasöründe mevcut olduğundan veya FDSN istemcisinden başarılı bir şekilde indirildiğinden emin olun. `config.py` içindeki `selected_station`, `date`, `start_hour`, `phase_component` ayarlarının, mevcut bir MSeed dosyasıyla eşleştiğini doğrulayın.
    *   **Katalog/HDF5 Grafikleri:** Terminal çıktısındaki ayrıştırma özeti mesajlarını kontrol edin (örneğin, `Başarıyla Ayrıştırılan Pick Sayısı: X`, `Grafiklenecek Event Merkezi Sayısı: Y`). Eğer bu sayılar sıfır (0) ise, girdi dosyasının formatı kodun beklediği formatla uyuşmuyor olabilir. İlgili `_utils.py` dosyasındaki (örn. `catalog_utils.py`, `hdf5_utils.py`) ayrıştırma (parsing) mantığını veya kullanılan düzenli ifadeleri (regex) kendi dosya formatınıza göre güncellemeniz gerekebilir.
    *   **EQT Grafiği:** `input_data/eqt/summary.csv` dosyasının var olduğundan ve `config.py` dosyasında belirtilen zaman aralığında (`start_hour`, `end_hour`, `date`) pick verisi içerdiğinden emin olun.

*   **Konum Hataları (HDF5 Grafiği):**
    *   HDF5 grafiği, konum bilgilerini (Enlem/Boylam) doğrudan HDF5 dosyası içindeki `locs` veya benzeri bir veri setinden alır. Eğer grafik üzerindeki konumlar hatalı görünüyorsa, bu durum büyük ihtimalle HDF5 dosyasının oluşturulması sırasındaki bir sorundan veya veri yapısının farklı olmasından kaynaklanır.
    *   Kod varsayılan olarak `locs` veri setindeki 0. sütunu Boylam (Longitude), 1. sütunu Enlem (Latitude) olarak kabul eder. Eğer sizin HDF5 dosyanızda bu sıra farklıysa (örneğin, 0. sütun Enlem, 1. sütun Boylam), `hdf5_utils.py` dosyasındaki ilgili satırları (`longitude = locs[...]`, `latitude = locs[...]`) bularak sütun indekslerini (0 ve 1) dosyanıza uygun şekilde değiştirmeniz gerekir.

*   **Zaman Hataları (HDF5 Grafiği):**
    *   Kod, HDF5 `Picks` verisindeki zamanı genellikle Epoch saniyesi (Unix timestamp) olarak, HDF5 `srcs` (kaynak/event) zamanını ise `config.py`'de belirtilen günün başlangıcından itibaren geçen saniye cinsinden bekleyebilir.
    *   Eğer HDF5 dosyanız farklı bir zaman formatı (örneğin, farklı bir referans zamanı, metin formatı) kullanıyorsa, `hdf5_utils.py` dosyasındaki zaman damgalarını okuyan ve dönüştüren kısımları dosyanızın formatına göre güncellemelisiniz.

*   **Genel Python Hataları (`TypeError`, `IndexError`, `KeyError` vb.):**
    *   Terminalde gösterilen tam hata mesajını ve "traceback" (hatanın oluştuğu kod satırlarını gösteren iz) dikkatlice inceleyin.
    *   Bu tür hatalar genellikle veri formatı uyumsuzluklarından, eksik verilerden (örneğin, beklenen bir sütunun dosyada olmaması) veya kodun beklemediği `None` gibi değerlerden kaynaklanır.
    *   Sorunun kaynağını daraltmak için ilgili `_utils.py` dosyasına geçici `print()` ifadeleri ekleyerek değişkenlerin değerlerini kontrol edebilirsiniz.