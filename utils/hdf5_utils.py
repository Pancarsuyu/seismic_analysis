# seismic_analysis/utils/hdf5_utils.py

import h5py
import numpy as np
import datetime
import plotly.graph_objects as go
import pytz # Zaman dilimi için

def plot_hdf5_picks(hdf5_file_path, station_names, station_location_dict, analysis_date_str):
    """
    HDF5'ten pickleri (Unix epoch) ve event merkezlerini ('srcs', gün saniyesi) okur.
    Konumları öncelikle dict'ten alır.
    Plotly ile zaman-BOYLAM grafiği oluşturur.
    """
    print(f"  HDF5 verisi işleniyor. Referans Tarih (Event için): {analysis_date_str}")
    try:
        analysis_date = datetime.datetime.strptime(analysis_date_str, '%Y-%m-%d').date()
        day_start_utc = datetime.datetime.combine(analysis_date, datetime.time.min, tzinfo=pytz.UTC)
        print(f"  HDF5 event zamanları için gün başlangıcı (UTC): {day_start_utc}")
    except ValueError: print(f"Hata: Geçersiz analiz tarihi formatı: {analysis_date_str}."); return None

    try:
        with h5py.File(hdf5_file_path, 'r') as hf:
            locs = None
            if 'locs' in hf: locs = np.array(hf['locs']); print(f"  HDF5 'locs' verisi bulundu. Boyut: {locs.shape}")
            else: print(f"  Uyarı: HDF5 'locs' datasetyi bulunamadı.")
            if 'Picks' not in hf: print(f"Hata: HDF5 'Picks' grubu bulunamadı."); return None

            # Event Merkezi Verisi ('srcs')
            event_sources = None; hdf5_event_times = []; hdf5_event_lats = []; hdf5_event_lons = []; hdf5_event_texts = []
            if 'srcs' in hf:
                event_sources = np.array(hf['srcs'])
                print(f"  HDF5 'srcs' verisi bulundu. Boyut: {event_sources.shape}")
                if event_sources.ndim == 2 and event_sources.shape[1] >= 4: # <<< DÜZELTME: En az 4 sütun yeterli (lat, lon, ?, time) >>>
                    print(f"  {event_sources.shape[0]} adet HDF5 event merkezi işleniyor...")
                    for row_idx, row in enumerate(event_sources):
                        try:
                            ev_lat = row[0]; ev_lon = row[1]
                            # <<< DÜZELTME: Zaman için doğru index = 3 >>>
                            ev_time_sec_of_day = row[3]

                            time_delta = datetime.timedelta(seconds=ev_time_sec_of_day)
                            ev_time_dt = day_start_utc + time_delta
                            # print(f"    srcs[{row_idx}]: sec={ev_time_sec_of_day} -> time={ev_time_dt}") # Debug

                            hdf5_event_times.append(ev_time_dt); hdf5_event_lats.append(ev_lat); hdf5_event_lons.append(ev_lon)
                            hdf5_event_texts.append(f"HDF5 Event Merkezi #{row_idx+1}<br>Zaman: {ev_time_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}<br>Lat: {ev_lat:.4f}<br>Lon: {ev_lon:.4f}")
                        except (IndexError, ValueError, TypeError) as e: print(f"    Uyarı: HDF5 'srcs' satırı {row_idx} işlenemedi: {row} - Hata: {e}")
                else: print(f"    Uyarı: HDF5 'srcs' formatı uygun değil (shape={event_sources.shape})."); event_sources = None
            else: print("  Uyarı: HDF5 'srcs' datasetyi bulunamadı.")

            # Pick Verisi Ayrıştırma
            pick_groups = {}; processed_pick_count = 0; skipped_pick_count = 0
            print("  HDF5 pick verileri işleniyor...")
            for dataset_name in hf['Picks'].keys():
                # ... (event_id, pick_type alma) ...
                parts = dataset_name.split('_'); #...
                if len(parts) < 2: continue
                earthquake_id = "_".join(parts[:-1]); pick_type = parts[-1].upper()
                if pick_type not in ['P', 'S']: continue
                if earthquake_id not in pick_groups: pick_groups[earthquake_id] = {'P': [], 'S': []}
                pick_data = np.array(hf['Picks'][dataset_name])
                if pick_data.ndim == 1: pick_data = pick_data.reshape(1, -1)
                if pick_data.shape[1] < 2: continue

                for pick_row in pick_data:
                    processed_pick_count +=1
                    # DÜZELTME: Zamanı gün başlangıcına göre hesapla
                    time_seconds_since_day_start = pick_row[0]  # Değişken ismi daha açıklayıcı
                    station_index = int(pick_row[1])

                    if station_index >= len(station_names): 
                        print(f"    Uyarı: Pick - Geçersiz index ({station_index}). Atlanıyor."); 
                        skipped_pick_count += 1; 
                        continue

                    # DÜZELTME: Unix epoch yerine gün başlangıcına ekle
                    try:
                        time_delta = datetime.timedelta(seconds=time_seconds_since_day_start)
                        pick_datetime_obj = day_start_utc + time_delta
                    except (ValueError, TypeError) as e:
                        print(f"    Uyarı: Pick - Zaman hesaplama hatası (saniye={time_seconds_since_day_start}). Hata: {e}. Atlanıyor.")
                        skipped_pick_count += 1; 
                        continue

                    station_name = station_names[station_index]
                    longitude = None; latitude = None; source = "Bilinmiyor"

                    # Lat/Lon al (Önce dict, sonra fallback)
                    station_info = station_location_dict.get(station_name)
                    if station_info:
                        lon_from_dict = station_info.get('lon'); lat_from_dict = station_info.get('lat')
                        if lon_from_dict is not None and lat_from_dict is not None:
                            longitude = lon_from_dict; latitude = lat_from_dict; source = "station_data.txt"
                        # else: print(f"    Uyarı: Pick - İstasyon '{station_name}' dict'te var ama lon/lat eksik.") # Gerekirse açılabilir
                    if source != "station_data.txt":
                        if locs is not None and station_index < len(locs):
                            try:
                                hdf5_lon = locs[station_index][0]; hdf5_lat = locs[station_index][1]
                                print(f"    Uyarı: Pick - İstasyon '{station_name}' için dict'te konum yok/eksik. HDF5 fallback (Lon={hdf5_lon:.4f}, Lat={hdf5_lat:.4f}).")
                                if longitude is None: longitude = hdf5_lon
                                if latitude is None: latitude = hdf5_lat
                                if longitude is not None and latitude is not None: source = "HDF5 locs (Fallback)"
                                else: source = "Error"
                            except IndexError: print(f"      Hata: Pick - HDF5 'locs' boyutu yetersiz."); source = "Error"
                        else: source = "Error" # Fallback mümkün değil

                    if longitude is None or latitude is None:
                        print(f"      Pick - Geçerli Lat/Lon bulunamadı ({station_name}, kaynak={source}). Atlanıyor.")
                        skipped_pick_count += 1; continue

                    # Pick bilgilerini sakla
                    pick_groups[earthquake_id][pick_type].append({'time': pick_datetime_obj, 'longitude': longitude, 'latitude': latitude, 'station': station_name, 'source': source})
            print(f"  HDF5 pick ayrıştırma özeti: İşlenen={processed_pick_count}, Atlanan={skipped_pick_count}")

            # Grafik Oluşturma (Y Ekseni = Boylam)
            fig = go.Figure(); p_marker = dict(color='blue', symbol='circle', size=8, line=dict(color='black', width=1)); s_marker = dict(color='red', symbol='x', size=8, line=dict(color='black', width=1)); event_marker_hdf5 = dict(color='magenta', size=10, symbol='diamond', line=dict(color='black', width=1)); line_style = dict(color='rgba(0,0,0,0.5)', width=1, dash='dot'); has_data = False; plotted_p_count = 0; plotted_s_count = 0; plotted_event_count = 0

            # Pickleri Çiz (Y=Boylam)
            for earthquake_id, pick_types in pick_groups.items():
                 p_picks = pick_types.get('P', []); s_picks = pick_types.get('S', [])
                 if p_picks:
                     has_data = True; plotted_p_count += len(p_picks)
                     hover_texts_p = [ f"Faz: P<br>İstasyon: {p['station']}<br>Zaman: {p['time'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}<br>Lon: {p['longitude']:.4f}<br>Lat: {p['latitude']:.4f}" for p in p_picks]
                     fig.add_trace(go.Scatter(x=[p['time'] for p in p_picks], y=[p['longitude'] for p in p_picks], mode='markers', marker=p_marker, name='P Picks', text=hover_texts_p, hoverinfo='text', showlegend=False, legendgroup="hdf5_picks"))
                 if s_picks:
                     has_data = True; plotted_s_count += len(s_picks)
                     hover_texts_s = [ f"Faz: S<br>İstasyon: {s['station']}<br>Zaman: {s['time'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}<br>Lon: {s['longitude']:.4f}<br>Lat: {s['latitude']:.4f}" for s in s_picks]
                     fig.add_trace(go.Scatter(x=[s['time'] for s in s_picks], y=[p['longitude'] for p in s_picks], mode='markers', marker=s_marker, name='S Picks', text=hover_texts_s, hoverinfo='text', showlegend=False, legendgroup="hdf5_picks"))
                 all_picks = sorted(p_picks + s_picks, key=lambda x: x['time'])
                 if len(all_picks) > 1:
                     has_data = True
                     fig.add_trace(go.Scatter(x=[p['time'] for p in all_picks], y=[p['longitude'] for p in all_picks], mode='lines', line=line_style, hoverinfo='none', showlegend=False))

            # HDF5 Event Merkezlerini Çiz (Y=Boylam)
            if hdf5_event_times:
                has_data = True; plotted_event_count = len(hdf5_event_times)
                fig.add_trace(go.Scatter(x=hdf5_event_times, y=hdf5_event_lons, mode='markers', marker=event_marker_hdf5, name='HDF5 Event Merkezleri', hoverinfo='text', text=hdf5_event_texts, showlegend=True, legendgroup="hdf5_events"))

            print(f"  HDF5 grafiğine eklendi: {plotted_p_count} P pick, {plotted_s_count} S pick, {plotted_event_count} Event Merkezi.")
            if not has_data: print("  Uyarı: HDF5'te grafiklenecek veri bulunamadı."); fig.add_annotation(...)

            # Grafik Düzeni (Y Ekseni = Boylam)
            fig.update_layout(title='HDF5 Verisi: Pickler ve Event Merkezleri (Konum Kaynağı: dict > locs)', xaxis_title='Zaman (UTC)', yaxis_title='Boylam (°)', height=300, template="plotly_white", hovermode='closest', margin=dict(l=40, r=40, t=60, b=40), legend=dict(title="HDF5 Veri", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig.update_xaxes(tickformat='%Y-%m-%d\n%H:%M:%S')
            return fig

    except FileNotFoundError: print(f"Hata: HDF5 dosyası bulunamadı: {hdf5_file_path}"); return None
    except Exception as e: import traceback; print(f'HDF5 verisi işlenirken beklenmedik bir hata oluştu: {str(e)}'); traceback.print_exc(); return None