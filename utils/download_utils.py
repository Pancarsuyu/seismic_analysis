# seismic_analysis/utils/download_utils.py

from obspy import UTCDateTime
from obspy.clients.fdsn import Client
import os

def _create_output_folder(folder_path):
    """Belirtilen klasörün var olduğundan emin olur, yoksa oluşturur."""
    os.makedirs(folder_path, exist_ok=True)
    print(f"Veri indirme klasörü kontrol edildi/oluşturuldu: {folder_path}")

def download_waveforms_for_station(client_name, station, channel, start_time, end_time, output_folder):
    """Belirli bir istasyon için waveform verisini indirir ve kaydeder."""
    try:
        print(f"  İndiriliyor: İstasyon={station}, Kanal={channel}, Zaman={start_time.date} {start_time.time}-{end_time.time}...")

        # Belirtilen FDSN istemcisini başlat
        client = Client(client_name)

        # Waveform verisini al (Network ve Location için wildcard kullan)
        # Not: Location='*' bazen çok fazla veri getirebilir veya hiç getirmeyebilir.
        # Gerekirse boş ('') veya spesifik bir kod ('00', '10' vb.) denenebilir.
        stream = client.get_waveforms(
            network="*",       # Veya spesifik ağ (örn: "KO")
            station=station,
            location="*",      # Veya ""
            channel=channel,
            starttime=start_time,
            endtime=end_time
        )

        if not stream:
            print(f"    Uyarı: {station} - {channel} için belirtilen zaman aralığında veri bulunamadı.")
            return

        # Stream içindeki her trace için ayrı dosya veya birleştirilmiş dosya?
        # Genellikle her trace'in network/location bilgisi farklı olabilir.
        # seismic_utils.py tek bir dosya bekliyor gibi. Şimdilik ilk trace'i baz alalım
        # veya stream'i birleştirelim. Birleştirmek daha mantıklı olabilir.
        try:
            stream.merge(method=1, fill_value='latest') # Çakışan verileri birleştir
             # method=0 sadece bitişik olanları birleştirir, 1 çakışanları da birleştirir (veri kaybı olabilir)
             # method=-1 gapleri doldurur (veri üretir) - dikkatli kullanılmalı
        except Exception as merge_err:
             print(f"    Uyarı: {station} - {channel} stream birleştirme hatası: {merge_err}. Ayrı trace'ler işlenecek.")
             # Birleştirme başarısız olursa ilk trace'i alalım (geçici çözüm)
             # Veya her trace için ayrı dosya kaydedilebilir, ancak bu seismic_utils'i değiştirir.

        if not stream: # Birleştirme sonrası boş kalırsa
             print(f"    Uyarı: {station} - {channel} için birleştirme sonrası veri kalmadı.")
             return

        # Dosya adını oluşturma (seismic_utils.py'nin okuyabileceği formata yakın)
        # Örnek: GELI_HHZ_KO_20231204_060000.mseed
        # Not: Network kodu stream'den alınabilir. Location kodu da alınabilir.
        tr = stream[0] # İlk trace'in bilgilerini kullanalım (birleştirilmişse tek trace olmalı)
        network_code = tr.stats.network if tr.stats.network else "XX" # Network yoksa XX
        location_code = tr.stats.location if tr.stats.location else "YY" # Location yoksa YY
        # Tarih formatını YYYYMMDD yapalım
        date_str_nodash = start_time.strftime('%Y%m%d')
        # Saat formatını HHMMSS yapalım (başlangıç saati)
        time_str = start_time.strftime('%H%M%S')

        # Dosya adı formatı: ISTASYON_KANAL_NETWORK_TARIH_SAAT.mseed
        # seismic_utils glob: {station}_{phase_component}_*_{date}_*{start_hour:02d}00*.mseed
        # Bu glob ile eşleşmesi için:
        filename_date_part = start_time.strftime('%Y-%m-%d') # seismic_utils'in aradığı format
        filename_hour_part = start_time.strftime('%H%M') # Sadece saat ve dakika (0600 gibi)

        # seismic_utils glob deseniyle daha uyumlu bir format deneyelim:
        # {output_folder}/{station}_{channel}_{network}_{date_YYYY-MM-DD}_{hour}00.mseed
        filename = f"{output_folder}/{station}_{channel}_{network_code}_{filename_date_part}_{filename_hour_part}.mseed"

        # Alternatif standart Obspy adı:
        # filename = f"{output_folder}/{tr.stats.network}.{tr.stats.station}.{tr.stats.location}.{tr.stats.channel}__{start_time.strftime('%Y%m%dT%H%M%S')}__" \
        #           f"{end_time.strftime('%Y%m%dT%H%M%S')}.mseed"
        # Bu durumda seismic_utils.py'deki glob deseninin de değişmesi gerekir. Şimdilik yukarıdaki formatı kullanalım.

        stream.write(filename, format="MSEED")
        print(f"    Başarıyla kaydedildi: {filename}")

    except Exception as e:
        print(f"  Hata: {station} - {channel} indirilirken sorun oluştu: {str(e)}")


def run_download(config):
    """
    Yapılandırmaya göre waveform indirme işlemini başlatır.

    Args:
        config (dict): 'config.py' dosyasından okunan CONFIG sözlüğü.
    """
    download_cfg = config.get('download_settings')
    if not download_cfg:
        print("Yapılandırmada 'download_settings' bölümü bulunamadı.")
        return

    if not download_cfg.get('enable_download', False):
        print("Waveform indirme işlemi config dosyasında devre dışı bırakılmış (enable_download=False).")
        return

    print("\n--- Waveform İndirme İşlemi Başlatılıyor ---")

    # Gerekli parametreleri al
    date = download_cfg.get('date')
    start_hour = download_cfg.get('start_hour')
    end_hour = download_cfg.get('end_hour')
    channel = download_cfg.get('channel')
    stations_to_download = download_cfg.get('stations_to_download', [])
    client_name = download_cfg.get('client_name', 'KOERI') # Varsayılan KOERI

    # Hedef klasörü al (seismic_data bölümünden)
    # Bu klasörün mseed dosyalarını içermesi bekleniyor
    output_folder = config.get('seismic_data', {}).get('mseed_folder')

    # Parametre kontrolleri
    if not all([date, start_hour is not None, end_hour is not None, channel, stations_to_download, output_folder]):
        print("Hata: İndirme ayarlarında eksik parametreler var (date, start_hour, end_hour, channel, stations_to_download, mseed_folder).")
        print(f"  Date: {date}, Start: {start_hour}, End: {end_hour}, Channel: {channel}, Stations: {len(stations_to_download)}, Folder: {output_folder}")
        return

    # Zaman aralığını oluştur (UTC)
    try:
        start_time = UTCDateTime(f"{date}T{start_hour:02d}:00:00")
        # Bitiş saati dahil değil, bu yüzden tam bitiş saatini kullanıyoruz
        end_time = UTCDateTime(f"{date}T{end_hour:02d}:00:00")
        print(f"İndirilecek Zaman Aralığı (UTC): {start_time} - {end_time}")
    except Exception as e:
        print(f"Hata: Geçersiz tarih/saat formatı. Date='{date}', StartHour={start_hour}, EndHour={end_hour}. Hata: {e}")
        return

    # Hedef klasörü oluştur/kontrol et
    _create_output_folder(output_folder)

    # Her istasyon için veriyi indir
    print(f"{len(stations_to_download)} istasyon için indirme başlıyor...")
    for station in stations_to_download:
        download_waveforms_for_station(client_name, station, channel, start_time, end_time, output_folder)

    print("--- Waveform İndirme İşlemi Tamamlandı ---\n")