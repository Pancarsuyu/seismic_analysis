import glob
import datetime
import plotly.graph_objects as go
from obspy import read
import pandas as pd # <<< Pandas'ı import et
import numpy as np

def plot_seismic_data(output_folder, selected_station, date, start_hour, filter_type, freqmin, freqmax, corners, zerophase, phase_component):
    """
    Seismic veriyi okur, filtreler ve Plotly ile grafiklendirir.
    """
    # Dosya adındaki saat formatını ve jolly karakterini kontrol et
    # İndirilen format: GELI_HHZ_KO_2023-12-04_0600.mseed
    # Aranan glob: {station}_{phase_component}_*_{date}_*{start_hour:02d}00*.mseed
    # Bu desen eşleşmeli.
    file_pattern = f"{output_folder}/{selected_station}_{phase_component}_*_{date}_*{start_hour:02d}00*.mseed"

    print(f"Aranan dosya deseni: {file_pattern}") # Hata ayıklama için
    file_path_list = glob.glob(file_pattern)

    if not file_path_list:
        print(f"Uyarı: Dosya bulunamadı: {file_pattern}")
        # Başka bir saat formatını dene? Veya sadece istasyon/kanal/tarih ile ara?
        # Alternatif daha genel desen:
        alt_file_pattern = f"{output_folder}/{selected_station}_{phase_component}_*_{date}*.mseed"
        print(f"Alternatif desen deneniyor: {alt_file_pattern}")
        file_path_list = glob.glob(alt_file_pattern)
        # Sadece ilk eşleşeni al (eğer birden fazla saat varsa)
        if file_path_list:
             # Belirli saate en yakın olanı seçmek daha iyi olabilir ama şimdilik ilkini alalım
             file_path = sorted(file_path_list)[0] # İsme göre sıralayıp ilkini al
             print(f"Alternatif desenle dosya bulundu: {file_path}")
        else:
            print(f"Uyarı: Alternatif desenle de dosya bulunamadı: {alt_file_pattern}")
            return None # Dosya bulunamazsa None dön


    # Eğer ilk desen başarılıysa, ilkini al
    if len(file_path_list) > 0 and 'file_path' not in locals():
         file_path = file_path_list[0]

    if 'file_path' not in locals() or not file_path:
         print(f"Uyarı: {selected_station} için uygun mseed dosyası bulunamadı.")
         return None

    print(f"Okunan dosya: {file_path}") # Hata ayıklama için

    try:
        stream = read(file_path)
        if not stream:
             print(f"Uyarı: {file_path} dosyası boş veya okunamadı.")
             return None
        raw_data = stream.copy()

        # Filtreleme
        # ... (Filtreleme kodu aynı kalır) ...
        if filter_type: # Filtre tipi belirtilmişse uygula
            try:
                if filter_type == 'highpass':
                    stream.filter(type=filter_type, freq=freqmin, corners=corners, zerophase=zerophase)
                elif filter_type in ['lowpass', 'bandpass', 'bandstop']:
                    if filter_type == 'lowpass':
                        stream.filter(type=filter_type, freq=freqmax, corners=corners, zerophase=zerophase)
                    else:
                         if freqmin is None or freqmax is None: print(f"Uyarı: {filter_type} için freqmin ve freqmax tanımlanmalı."); return None
                         stream.filter(type=filter_type, freqmin=freqmin, freqmax=freqmax, corners=corners, zerophase=zerophase)
                else: print(f"Uyarı: Geçersiz filtre tipi '{filter_type}'. Filtre uygulanmadı.")
            except Exception as e: print(f"Filtreleme hatası: {str(e)}")


        if not stream: # Filtreleme sonrası stream boşalırsa (çok nadir)
             print(f"Uyarı: Filtreleme sonrası veri kalmadı: {file_path}")
             return None

        trace = stream[0]
        raw_trace = raw_data[0]

        # === ZAMAN EKSENİ DEĞİŞİKLİĞİ ===
        # trace.times("datetime") yerine Pandas Timestamp kullanalım
        start_time_ns = trace.stats.starttime.ns # Nanosecond precision start time
        delta_s = trace.stats.delta             # Sampling interval in seconds
        times_rel_ns = np.arange(trace.stats.npts) * delta_s * 1e9 # Relative time in ns
        # Başlangıç zamanına göre mutlak zamanı ns cinsinden hesapla
        times_abs_ns = start_time_ns + times_rel_ns
        # Pandas Timestamp serisine çevir (UTC varsayalım, Obspy genelde UTC kullanır)
        time_series_pd = pd.to_datetime(times_abs_ns, unit='ns', utc=True)
        # ================================


        fig = go.Figure()
        # Ham Sinyal (Gizli Başlat)
        fig.add_trace(go.Scatter(
            x=time_series_pd, y=raw_trace.data, mode='lines', # <<< Değiştirildi: time_series_pd
            name='Ham Sinyal', line=dict(width=1, color='gray'),
            visible='legendonly'
        ))
        # Filtreli Sinyal
        filter_label = f'Filtreli ({filter_type} {freqmin or ""} - {freqmax or ""} Hz)' if filter_type else 'Filtresiz Sinyal'
        fig.add_trace(go.Scatter(
            x=time_series_pd, y=trace.data, mode='lines', # <<< Değiştirildi: time_series_pd
            name=filter_label,
            line=dict(width=1.5, color='blue')
        ))

        # Grafik Bilgileri ve Düzenlemeler
        nyquist = 0.5 * trace.stats.sampling_rate
        fig.add_annotation(
            text=f"Örnekleme Oranı: {trace.stats.sampling_rate:.2f} Hz<br>Nyquist: {nyquist:.2f} Hz",
            align='left', showarrow=False, xref='paper', yref='paper',
            x=0.02, y=0.98, bordercolor='black', borderwidth=1, bgcolor='rgba(255,255,255,0.7)'
        )

        # Başlığı biraz daha bilgilendirici yapalım (bitiş saati trace'den alınabilir)
        trace_endtime_utc = trace.stats.endtime.strftime('%H:%M:%S')
        trace_starttime_utc = trace.stats.starttime.strftime('%H:%M:%S')
        title_text = f"{selected_station} {phase_component} - {date} {trace_starttime_utc}-{trace_endtime_utc} UTC"
        if filter_type:
            title_text += f"<br><sup>Filtre: {filter_type} {freqmin or ''}-{freqmax or ''} Hz, Corners: {corners}, Zerophase: {zerophase}</sup>"
        else:
             title_text += "<br><sup>Filtre Uygulanmadı</sup>"

        fig.update_layout(
            title=title_text,
            xaxis_title="Zaman (UTC)",
            yaxis_title="Amplitüd",
            hovermode="x unified",
            template="plotly_white",
            showlegend=True,
            height=300, # Alt grafik için standart yükseklik
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=80, b=40)
        )
        fig.update_xaxes(
            rangeselector=dict(
                buttons=list([
                    dict(count=5, label="5dk", step="minute", stepmode="backward"),
                    dict(count=15, label="15dk", step="minute", stepmode="backward"),
                    dict(count=1, label="1sa", step="hour", stepmode="backward"),
                    dict(step="all", label="Tümü")
                ])
            ),
            rangeslider=dict(visible=False)
        )
        return fig

    # Hata yakalamayı spesifikleştirelim
    except FileNotFoundError:
        print(f"Hata: {file_path} dosyası okunamadı veya bulunamadı.")
        return None
    except IndexError:
         print(f"Hata: {file_path} dosyasında beklenen trace bulunamadı.")
         return None
    except Exception as e:
        # Hatayı ve traceback'i yazdırabiliriz (daha detaylı hata ayıklama için)
        import traceback
        print(f"Sismik veri işlenirken beklenmedik bir hata oluştu: {str(e)}")
        # traceback.print_exc() # Bunu etkinleştirirseniz tam hata izini görürsünüz
        return None