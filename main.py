# seismic_analysis/main.py

from plotly.subplots import make_subplots
import plotly.graph_objects as go
import os
import sys
import datetime # Tarih kontrolü için

# Yardımcı fonksiyonları ilgili modüllerden import et
from utils import seismic_utils
from utils import catalog_utils  # Hem plot hem de parse fonksiyonu için
from utils import hdf5_utils
from utils import eqt_utils
from utils import download_utils

# Yapılandırma ve veri dosyalarını import et
try:
    from config.config import CONFIG
except ImportError:
    print("Hata: config/config.py dosyası bulunamadı veya içe aktarılamadı.")
    print("Lütfen dosyanın doğru yerde olduğundan ve Python hatası içermediğinden emin olun.")
    sys.exit(1)
try:
    from data.station_names import STATION_NAMES # HDF5 için istasyon listesi
except ImportError:
    print("Hata: data/station_names.py dosyası bulunamadı veya içe aktarılamadı.")
    sys.exit(1)


# --- Yardımcı Fonksiyon: Dosya okuma ---
def read_file_content(file_path):
    """Verilen dosyanın içeriğini okur ve string olarak döndürür."""
    if not os.path.exists(file_path):
         print(f"Hata: Dosya bulunamadı: {file_path}")
         return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        print(f"Uyarı: '{file_path}' utf-8 ile okunamadı, latin-1 deneniyor.")
        try:
             with open(file_path, 'r', encoding='latin-1') as f: return f.read()
        except Exception as e: print(f"Hata: Dosya okunurken hata ({file_path}) (latin-1 denendi): {e}"); return None
    except Exception as e:
        print(f"Hata: Dosya okunurken hata ({file_path}): {e}")
        return None
# --- ---


def main():
    """
    Ana fonksiyon. Gerekirse waveform indirir, verileri işler ve grafiği oluşturur.
    """
    print("="*50)
    print(" Seismic Analysis Pipeline Başlatılıyor ".center(50, "="))
    print("="*50)
    print(f"Proje Kök Dizini: {CONFIG.get('PROJECT_ROOT', 'Bilinmiyor')}")
    print(f"Girdi Veri Dizini: {CONFIG.get('INPUT_DATA_DIR', 'Bilinmiyor')}")

    # === 1. Adım: Waveform İndirme (Opsiyonel) ===
    try:
        if 'download_settings' in CONFIG and CONFIG['download_settings'].get('enable_download', False):
            download_utils.run_download(CONFIG)
        else:
            print("\nWaveform indirme adımı atlandı (config dosyasında etkin değil).")
            mseed_folder = CONFIG.get('seismic_data', {}).get('mseed_folder')
            if not os.path.isdir(mseed_folder): print(f"[UYARI] Mseed klasörü bulunamadı: {mseed_folder}")
            else: print(f"Mevcut mseed klasörü kullanılacak: {mseed_folder}")
    except Exception as download_err:
        print(f"\n[HATA] Waveform indirme sırasında beklenmedik bir hata oluştu: {download_err}")

    # === 2. Adım: Ortak Verileri Hazırlama (İstasyon Lokasyonları - Katalog için) ===
    print("\nOrtak veriler hazırlanıyor (Katalog için İstasyon Lokasyonları)...")
    station_data_path = CONFIG.get('catalog_data', {}).get('station_data_path')
    parsed_station_locs = {} # Başlangıçta boş sözlük
    if station_data_path and os.path.exists(station_data_path):
        station_data_content = read_file_content(station_data_path)
        if station_data_content:
            parsed_station_locs = catalog_utils.parse_station_data(station_data_content)
            print(f"  {len(parsed_station_locs)} adet istasyon lokasyonu 'station_data.txt' dosyasından ayrıştırıldı (Katalog Grafiği için).")
        else: print(f"  Uyarı: İstasyon veri dosyası ({station_data_path}) okunamadı veya boş.")
    else: print(f"  Uyarı: İstasyon veri dosyası yolu bulunamadı veya dosya mevcut değil ({station_data_path}).")
    if not parsed_station_locs: print("  [UYARI] Katalog Grafiği için istasyon lokasyonları yüklenemedi.")


    # === 3. Adım: Dosya Yolu Kontrolleri (Grafikleme Öncesi) ===
    print("\nGrafikleme için dosya ve klasör yolları kontrol ediliyor...")
    paths_ok = True
    # Mseed klasörü kontrolü
    mseed_folder = CONFIG.get('seismic_data', {}).get('mseed_folder')
    if not os.path.isdir(mseed_folder):
        print(f"  [HATA] Mseed klasörü bulunamadı/oluşturulamadı: {mseed_folder}")
        paths_ok = False
    # Diğer gerekli dosyalar
    required_files = [
        CONFIG.get('catalog_data', {}).get('catalog_file_path'),
        CONFIG.get('catalog_data', {}).get('station_data_path'),
        CONFIG.get('hdf5_data', {}).get('hdf5_file_path'),
        CONFIG.get('eqt_data', {}).get('summary_csv_path'),
    ]
    required_files = [f for f in required_files if f is not None] # None değerleri filtrele
    for f in required_files:
         if not os.path.isfile(f):
            print(f"  [HATA] Gerekli dosya bulunamadı: {f}")
            paths_ok = False
    if not paths_ok:
         print("\nEksik girdi dosyaları veya klasörleri var! Devam ediliyor...")
    else:
         print("  Grafikleme için gerekli tüm girdi yolları mevcut görünüyor.")


    # === 4. Adım: Alt Grafikleri Oluştur ===
    print("\n--- Grafik Oluşturma İşlemi Başlatılıyor ---")
    fig = make_subplots(
        rows=4, cols=1,
        subplot_titles=(
            "Sismik Veri (Filtreli ve Ham)",
            "Deprem Katalog Verisi (Zaman-Boylam)",
            "HDF5 Verisi: Pickler ve Eventler (Zaman-Enlem)", # Başlık güncellendi
            "EQTransformer Pick Dağılımı (Zaman-İstasyon)"
        ),
        vertical_spacing=0.08
    )

    # 4.1 Sismik Veri Grafiği
    print("1. Sismik veri grafiği oluşturuluyor...")
    seismic_cfg = CONFIG['seismic_data']
    fig1 = seismic_utils.plot_seismic_data(
        output_folder=seismic_cfg['mseed_folder'],
        selected_station=seismic_cfg['selected_station'],
        date=seismic_cfg['date'],
        start_hour=seismic_cfg['start_hour'],
        filter_type=seismic_cfg['filter_type'],
        freqmin=seismic_cfg['freqmin'],
        freqmax=seismic_cfg['freqmax'],
        corners=seismic_cfg['corners'],
        zerophase=seismic_cfg['zerophase'],
        phase_component=seismic_cfg['phase_component']
    )
    if fig1:
        for trace in fig1.data: fig.add_trace(trace, row=1, col=1)
        fig.update_xaxes(title_text=fig1.layout.xaxis.title.text, row=1, col=1, rangeselector=fig1.layout.xaxis.rangeselector, rangeslider=fig1.layout.xaxis.rangeslider)
        fig.update_yaxes(title_text=fig1.layout.yaxis.title.text, row=1, col=1)
        print("   Sismik veri grafiği eklendi.")
    else:
        print("   Uyarı: Sismik veri grafiği oluşturulamadı.")
        fig.add_annotation(text="Sismik Veri Yüklenemedi/Bulunamadı", row=1, col=1, showarrow=False)


    # 4.2 Katalog Grafiği
    print("2. Deprem katalog grafiği oluşturuluyor...")
    catalog_cfg = CONFIG['catalog_data']
    fig2 = catalog_utils.plot_catalog_data(
        catalog_file_path=catalog_cfg['catalog_file_path'],
        station_data_path=catalog_cfg['station_data_path']
    )
    if fig2:
        # Katalog grafiğinin lejantını bu alt grafiğe özel yapalım
        for trace in fig2.data:
             trace.showlegend = True # Bu alt grafikte lejant görünsün
             fig.add_trace(trace, row=2, col=1)
        fig.update_xaxes(title_text=fig2.layout.xaxis.title.text, row=2, col=1, tickformat='%H:%M:%S')
        fig.update_yaxes(title_text=fig2.layout.yaxis.title.text, row=2, col=1)
        # Lejant ayarları (isteğe bağlı, default genellikle yeterli)
        # fig.update_layout(legend2=dict(...)) # Alt grafiklere özel lejant ayarı daha karmaşık
        print("   Katalog grafiği eklendi.")
    else:
        print("   Uyarı: Deprem katalog grafiği oluşturulamadı.")
        fig.add_annotation(text="Katalog Verisi Yüklenemedi", row=2, col=1, showarrow=False)


    # 4.3 HDF5 Pick Grafiği
    print("3. HDF5 pick grafiği oluşturuluyor...")
    hdf5_cfg = CONFIG['hdf5_data']
    seismic_cfg = CONFIG['seismic_data'] # Tarih bilgisi için
    analysis_date_for_hdf5 = seismic_cfg.get('date')
    if not analysis_date_for_hdf5:
        print("Uyarı: HDF5 event zamanları için tarih config'de bulunamadı! Bugünün tarihi kullanılacak.")
        analysis_date_for_hdf5 = datetime.date.today().strftime('%Y-%m-%d')

    # Artık station_location_dict gönderilmiyor
    fig3 = hdf5_utils.plot_hdf5_picks(
        hdf5_file_path=hdf5_cfg['hdf5_file_path'],
        station_names=STATION_NAMES,
        analysis_date_str=analysis_date_for_hdf5
    )
    if fig3:
        # HDF5 grafiğinin lejantını bu alt grafiğe özel yapalım
        for trace in fig3.data:
             # Sadece Event merkezleri için lejant gösterelim
             if trace.name is not None and 'Event Merkezleri' in trace.name:
                 trace.showlegend = True
             else:
                 trace.showlegend = False
             fig.add_trace(trace, row=3, col=1)
        fig.update_xaxes(title_text=fig3.layout.xaxis.title.text, row=3, col=1, tickformat='%H:%M:%S')
        fig.update_yaxes(title_text=fig3.layout.yaxis.title.text, row=3, col=1)
        print("   HDF5 pick grafiği eklendi.")
    else:
        print("   Uyarı: HDF5 pick grafiği oluşturulamadı.")
        fig.add_annotation(text="HDF5 Verisi Yüklenemedi", row=3, col=1, showarrow=False)


    # 4.4 EQTransformer Pick Grafiği
    print("4. EQTransformer pick grafiği oluşturuluyor...")
    eqt_cfg = CONFIG['eqt_data']
    fig4 = eqt_utils.plot_eqtransformer_picks(
        csv_file_path=eqt_cfg['summary_csv_path'],
        eqt_start_hour=eqt_cfg['start_hour'],
        eqt_end_hour=eqt_cfg['end_hour'],
        eqt_date=eqt_cfg['date']
    )
    if fig4:
        # EQT grafiğinin lejantını bu alt grafiğe özel yapalım
        for trace in fig4.data:
             trace.showlegend = True
             fig.add_trace(trace, row=4, col=1)
        fig.update_xaxes(title_text=fig4.layout.xaxis.title.text, row=4, col=1, tickformat='%H:%M:%S')
        fig.update_yaxes(title_text=fig4.layout.yaxis.title.text, row=4, col=1, categoryorder='array', categoryarray=fig4.layout.yaxis.categoryarray)
        print("   EQTransformer pick grafiği eklendi.")
    else:
        print("   Uyarı: EQTransformer pick grafiği oluşturulamadı.")
        fig.add_annotation(text="EQTransformer Verisi Yüklenemedi", row=4, col=1, showarrow=False)


    # --- 5. Adım: Genel Figür Ayarları ve Gösterim ---
    plot_cfg = CONFIG['plot_settings']
    fig.update_layout(
        height=plot_cfg['figure_height'],
        title_text=plot_cfg['figure_title'],
        title_x=0.5, # Başlığı ortala
        # Ana lejantı tamamen kapatmak yerine, her alt grafiğin kendi lejantını yönetmesine izin verdik.
        # Eğer hala tek bir genel lejant isteniyorsa, showlegend=True yapıp,
        # her add_trace'deki showlegend=False/True ayarlarını kaldırmak gerekir.
        showlegend=False,
        template="plotly_white"
    )
    # Alt grafik başlıklarının konumunu ayarlayabiliriz (biraz yukarı)
    for annotation in fig.layout.annotations:
        annotation.y = annotation.y + 0.01 # Biraz yukarı kaydır

    print("\n--- Grafik Gösteriliyor ---")
    fig.show()
    print("\nProgram tamamlandı.")
    print("="*50)


if __name__ == "__main__":
    main()