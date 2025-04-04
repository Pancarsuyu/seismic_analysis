import h5py
import numpy as np
import datetime
import plotly.graph_objects as go
import pytz # Zaman dilimi için
import traceback # Detaylı hata loglama için

def plot_hdf5_picks(hdf5_file_path, station_names, analysis_date_str):
    """
    HDF5'ten pickleri ve event merkezlerini ('srcs') okur.
    Konumları DOĞRUDAN HDF5 içerisindeki 'locs' verisinden alır.
    Hem pick hem de event zamanını analysis_date_str'e göre (gün başlangıcından saniye) hesaplar.
    Plotly ile zaman-BOYLAM grafiği oluşturur.

    Args:
        hdf5_file_path (str): HDF5 dosyasının yolu.
        station_names (list): İstasyon isimleri listesi (data/station_names.py'den).
        analysis_date_str (str): HDF5 verilerinin ait olduğu gün (YYYY-MM-DD).

    Returns:
        plotly.graph_objects.Figure or None: Oluşturulan Plotly figürü veya hata.
    """
    print(f"  HDF5 verisi işleniyor. Analiz tarihi: {analysis_date_str}")
    print(f"  UYARI: Konumlar doğrudan HDF5 'locs' verisinden alınacak.")
    print(f"  VARSAYIM: HDF5 Event zamanları (srcs), {analysis_date_str} 00:00:00 UTC'den itibaren geçen SANİYE cinsindendir.")
    print(f"  VARSAYIM: HDF5 Pick zamanları, {analysis_date_str} 00:00:00 UTC'den itibaren geçen SANİYE cinsindendir.")

    # Analiz tarihini işle (Event ve Pick zamanları için gerekli)
    try:
        analysis_date = datetime.datetime.strptime(analysis_date_str, '%Y-%m-%d').date()
        day_start_utc = datetime.datetime.combine(analysis_date, datetime.time.min, tzinfo=pytz.UTC)
        print(f"  HDF5 zamanları için gün başlangıcı (UTC): {day_start_utc}")
    except ValueError:
        print(f"Hata: Geçersiz analiz tarihi formatı: {analysis_date_str}. YYYY-MM-DD bekleniyor.")
        return None

    try:
        with h5py.File(hdf5_file_path, 'r') as hf:
            # 'locs' Verisini Kontrol Et
            locs = None
            if 'locs' in hf:
                locs = np.array(hf['locs'])
                print(f"  HDF5 'locs' verisi bulundu. Boyut: {locs.shape}")
                if locs.ndim != 2 or locs.shape[1] < 2:
                     print(f"Hata: HDF5 'locs' boyutu uygun değil (Nx2+ bekleniyor).")
                     return None
            else:
                print(f"Hata: HDF5 'locs' datasetyi bulunamadı.")
                return None

            if 'Picks' not in hf: 
                print(f"Hata: HDF5 'Picks' grubu bulunamadı.")
                return None

            # 'srcs' (Event Merkezleri) Oku
            event_sources = None
            hdf5_event_times = []
            hdf5_event_lats = []
            hdf5_event_lons = []
            hdf5_event_texts = []
            
            if 'srcs' in hf:
                event_sources = np.array(hf['srcs'])
                print(f"  HDF5 'srcs' veri şekli: {event_sources.shape}")
                
                # İlk 5 ve son 5 event verilerini yazdır
                if event_sources.ndim == 2 and len(event_sources) > 0:
                    max_to_show = min(5, len(event_sources))
                    print(f"  İlk {max_to_show} event verisi:")
                    for i in range(max_to_show):
                        print(f"    Event #{i}: {event_sources[i]}")
                    
                    if len(event_sources) > 10:
                        print(f"  Son {max_to_show} event verisi:")
                        for i in range(-max_to_show, 0):
                            print(f"    Event #{len(event_sources)+i}: {event_sources[i]}")
                
                if event_sources.ndim == 2 and event_sources.shape[1] >= 5:
                    for row_idx, row in enumerate(event_sources):
                        try:
                            ev_lat = row[0]
                            ev_lon = row[1]
                            ev_time_sec_of_day = row[3]  # Saniye varsayıyoruz
                            
                            # Event zamanı kontrolü ve yazdırma
                            if row_idx < 5 or row_idx >= len(event_sources) - 5:
                                print(f"    Event #{row_idx+1} ham zaman: {ev_time_sec_of_day} saniye")
                            
                            # Saniye cinsinden zaman kontrolü
                            if ev_time_sec_of_day < 0 or ev_time_sec_of_day > 86400:  # 24*60*60 saniye
                                print(f"    Uyarı: Event zamanı mantıksız: {ev_time_sec_of_day} saniye. Atlanıyor.")
                                continue
                                
                            # Saniye cinsinden zaman (kayan nokta değerini doğrudan kullan)
                            time_delta = datetime.timedelta(seconds=ev_time_sec_of_day)
                            ev_time_dt = day_start_utc + time_delta  # Gün başlangıcına ekle
                            
                            # Dönüştürülmüş zamanı yazdır
                            if row_idx < 5 or row_idx >= len(event_sources) - 5:
                                print(f"    Event #{row_idx+1} dönüştürülmüş zaman: {ev_time_dt}")
                            
                            hdf5_event_times.append(ev_time_dt)
                            hdf5_event_lats.append(ev_lat)
                            hdf5_event_lons.append(ev_lon)
                            
                            # Formatlı metin oluşturma
                            hdf5_event_texts.append(
                                f"HDF5 Event Merkezi #{row_idx+1}<br>"
                                f"Zaman: {ev_time_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}<br>"
                                f"Lat: {ev_lat:.4f}<br>"
                                f"Lon: {ev_lon:.4f}"
                            )
                        except (IndexError, ValueError) as e:
                            print(f"    Uyarı: HDF5 'srcs' satırı {row_idx} işlenemedi: {row} - Hata: {e}")
                else:
                    print(f"    Uyarı: HDF5 'srcs' formatı uygun değil.")
                    event_sources = None
            else:
                print("  Uyarı: HDF5 'srcs' datasetyi bulunamadı.")

            # --- Pick Ayrıştırma (Zaman ve Konum Düzeltmesi) ---
            pick_groups = {}
            processed_pick_count = 0
            skipped_pick_count = 0
            pick_dataset_counts = {}
            
            # Tüm Pick datasetlerini kontrol et ve sayıları yazdır
            print(f"  HDF5 'Picks' altındaki veri setleri:")
            for dataset_name in hf['Picks'].keys():
                pick_data = np.array(hf['Picks'][dataset_name])
                pick_dataset_counts[dataset_name] = len(pick_data)
                print(f"    {dataset_name}: {len(pick_data)} veri")
            
            for dataset_name in hf['Picks'].keys():
                parts = dataset_name.split('_')
                if len(parts) < 2:
                    continue
                    
                earthquake_id = "_".join(parts[:-1])
                pick_type = parts[-1].upper()
                
                if pick_type not in ['P', 'S']:
                    continue
                    
                if earthquake_id not in pick_groups:
                    pick_groups[earthquake_id] = {'P': [], 'S': []}
                    
                pick_data = np.array(hf['Picks'][dataset_name])
                
                # İlk 5 ve son 5 pick verilerini yazdır
                if len(pick_data) > 0:
                    max_picks_to_show = min(5, len(pick_data))
                    print(f"  İlk {max_picks_to_show} '{dataset_name}' pick verisi:")
                    for i in range(max_picks_to_show):
                        print(f"    Pick #{i}: {pick_data[i]}")
                    
                    if len(pick_data) > 10:
                        print(f"  Son {max_picks_to_show} '{dataset_name}' pick verisi:")
                        for i in range(-max_picks_to_show, 0):
                            print(f"    Pick #{len(pick_data)+i}: {pick_data[i]}")
                
                if pick_data.ndim == 1:
                    pick_data = pick_data.reshape(1, -1)
                    
                if pick_data.shape[1] < 2:
                    continue

                for pick_idx, pick_row in enumerate(pick_data):
                    processed_pick_count += 1
                    try:
                        pick_time_sec = pick_row[0]  # Varsayım: Gün başından saniye
                        station_index = int(pick_row[1])
                        
                        # Ham verileri yazdır
                        if pick_idx < 5 or pick_idx >= len(pick_data) - 5:
                            print(f"    {dataset_name} #{pick_idx+1} ham zaman: {pick_time_sec} saniye, istasyon: {station_index}")
                        
                        # Pick zamanı kontrolü
                        if pick_time_sec < 0 or pick_time_sec > 86400:  # 24*60*60 saniye
                            print(f"    Uyarı: Pick zamanı mantıksız: {pick_time_sec} saniye. Atlanıyor.")
                            skipped_pick_count += 1
                            continue

                        if not (0 <= station_index < len(station_names)):
                            print(f"    Uyarı: Geçersiz istasyon index ({station_index}), names sınırı. Atlanıyor.")
                            skipped_pick_count += 1
                            continue
                            
                        if not (0 <= station_index < len(locs)):
                            print(f"    Uyarı: Geçersiz istasyon index ({station_index}), locs sınırı. Atlanıyor.")
                            skipped_pick_count += 1
                            continue

                        # Pick Zamanını Hesapla - Tam saniye ve mikrosaniye olarak ayır
                        seconds = int(pick_time_sec)
                        microseconds = int((pick_time_sec - seconds) * 1000000)
                        pick_time_delta = datetime.timedelta(seconds=seconds, microseconds=microseconds)
                        pick_datetime_obj = day_start_utc + pick_time_delta
                        
                        # Dönüştürülmüş zamanı yazdır
                        if pick_idx < 5 or pick_idx >= len(pick_data) - 5:
                            print(f"    {dataset_name} #{pick_idx+1} dönüştürülmüş zaman: {pick_datetime_obj}")

                        station_name = station_names[station_index]

                        # Lat/Lon doğrudan locs'tan
                        # DİKKAT: HDF5 dosyanızda sütun sırası farklıysa (örn. 0=Lat, 1=Lon) bu indeksleri değiştirin!
                        longitude = locs[station_index, 1]  # Varsayım: 1. sütun Boylam
                        latitude = locs[station_index, 0]   # Varsayım: 0. sütun Enlem
                        source = "HDF5 locs"
                        
                        if np.isnan(longitude) or np.isnan(latitude):
                            print(f"    Uyarı: NaN konum (İstasyon: {station_name}). Atlanıyor.")
                            skipped_pick_count += 1
                            continue

                        pick_groups[earthquake_id][pick_type].append({
                            'time': pick_datetime_obj,
                            'longitude': longitude,
                            'latitude': latitude,
                            'station': station_name,
                            'source': source
                        })

                    except (IndexError, ValueError) as e:
                        print(f"    Hata: Pick satırı işlenirken hata (Satır: {pick_row}) - {e}. Atlanıyor.")
                        skipped_pick_count += 1
                        continue
                    except Exception as e_gen:
                        print(f"    Hata: Pick satırı beklenmedik hata (Satır: {pick_row}) - {e_gen}. Atlanıyor.")
                        traceback.print_exc()
                        skipped_pick_count += 1
                        continue
                        
            print(f"  HDF5 pick ayrıştırma özeti: İşlenen={processed_pick_count}, Atlanan={skipped_pick_count}")

            # ---- Grafik Oluşturma (Y Ekseni Boylam) ----
            fig = go.Figure()
            p_marker = dict(color='blue', symbol='circle', size=8, line=dict(color='black', width=1))
            s_marker = dict(color='red', symbol='x', size=8, line=dict(color='black', width=1))
            event_marker_hdf5 = dict(color='magenta', size=10, symbol='diamond', line=dict(color='black', width=1))
            line_style = dict(color='rgba(0,0,0,0.5)', width=1, dash='dot')
            has_data = False
            plotted_p_count = 0
            plotted_s_count = 0

            # Pickleri Çiz (Y ekseni Boylam)
            for earthquake_id, pick_types in pick_groups.items():
                p_picks = pick_types.get('P', [])
                s_picks = pick_types.get('S', [])
                
                if p_picks:
                    has_data = True
                    plotted_p_count += len(p_picks)
                    hover_texts_p = [
                        f"Faz: P<br>"
                        f"İstasyon: {p['station']}<br>"
                        f"Zaman: {p['time'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}<br>"
                        f"Lon: {p['longitude']:.4f}<br>"
                        f"Lat: {p['latitude']:.4f}"
                        for p in p_picks
                    ]
                    # Y Ekseni: longitude
                    fig.add_trace(go.Scatter(
                        x=[p['time'] for p in p_picks],
                        y=[p['longitude'] for p in p_picks],
                        mode='markers',
                        marker=p_marker,
                        name=f'P Picks ({earthquake_id})',
                        text=hover_texts_p,
                        hoverinfo='text',
                        showlegend=False
                    ))
                    
                if s_picks:
                    has_data = True
                    plotted_s_count += len(s_picks)
                    hover_texts_s = [
                        f"Faz: S<br>"
                        f"İstasyon: {s['station']}<br>"
                        f"Zaman: {s['time'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}<br>"
                        f"Lon: {s['longitude']:.4f}<br>"
                        f"Lat: {s['latitude']:.4f}"
                        for s in s_picks
                    ]
                    # Y Ekseni: longitude
                    fig.add_trace(go.Scatter(
                        x=[s['time'] for s in s_picks],
                        y=[s['longitude'] for s in s_picks],
                        mode='markers',
                        marker=s_marker,
                        name=f'S Picks ({earthquake_id})',
                        text=hover_texts_s,
                        hoverinfo='text',
                        showlegend=False
                    ))
                    
                # Pickleri birleştiren çizgiler (Y ekseni Boylam)
                all_picks = sorted(p_picks + s_picks, key=lambda x: x['time'])
                if len(all_picks) > 1:
                    has_data = True
                    # Y Ekseni: longitude
                    fig.add_trace(go.Scatter(
                        x=[p['time'] for p in all_picks],
                        y=[p['longitude'] for p in all_picks],
                        mode='lines',
                        line=line_style,
                        hoverinfo='none',
                        showlegend=False
                    ))
                    
            print(f"  HDF5 grafiğine eklendi: {plotted_p_count} P pick, {plotted_s_count} S pick.")

            # HDF5 Event Merkezlerini Çiz (Y ekseni Boylam)
            if hdf5_event_times:
                has_data = True
                print(f"  HDF5 grafiğine {len(hdf5_event_times)} adet event merkezi ekleniyor.")
                fig.add_trace(go.Scatter(
                    x=hdf5_event_times,
                    y=hdf5_event_lons,  # Y Ekseni: longitude
                    mode='markers',
                    marker=event_marker_hdf5,
                    name='HDF5 Event Merkezleri',
                    hoverinfo='text',
                    text=hdf5_event_texts,
                    showlegend=True
                ))

            # Grafik Başlığı ve Düzeni
            if not has_data:
                print("  Uyarı: HDF5'te grafiklenecek veri bulunamadı.")
                fig.add_annotation(
                    text="Veri bulunamadı!",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    showarrow=False,
                    font=dict(size=20)
                )
                
            fig.update_layout(
                title='HDF5 Verisi: Pickler ve Eventler (Konum: HDF5 \'locs\')',
                xaxis_title='Zaman (UTC)',
                yaxis_title='Boylam (°)',  # Y Ekseni Etiketi: Boylam
                showlegend=True,
                height=300,
                template="plotly_white",
                hovermode='closest',
                margin=dict(l=50, r=40, t=80, b=40)
            )
            # Zaman formatını milisaniye detayına kadar göster
            fig.update_xaxes(tickformat='%Y-%m-%d\n%H:%M:%S')
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            return fig

    # Hata Yakalama
    except FileNotFoundError:
        print(f"Hata: HDF5 dosyası bulunamadı: {hdf5_file_path}")
        return None
    except Exception as e:
        print(f'HDF5 verisi işlenirken beklenmedik bir hata oluştu: {str(e)}')
        traceback.print_exc()
        return None