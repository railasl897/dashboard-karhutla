"""Dashboard Klasterisasi Titik Panas Kalimantan Tengah (DBSCAN), Kelompok 5 3KA33.
Jalankan: streamlit run app.py  (folder 'hasil' dari notebook harus berada di samping file ini)
"""
import json
from pathlib import Path
import pandas as pd
import pydeck as pdk
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='Klaster Titik Panas Kalimantan Tengah', layout='wide')
H = Path(__file__).parent / 'hasil'  # folder hasil di samping app.py, aman dijalankan dari folder mana pun
BULAN = ['Agustus', 'September', 'Oktober']
WARNA = [[230, 25, 75], [60, 180, 75], [0, 130, 200], [245, 130, 48], [145, 30, 180],
         [70, 240, 240], [240, 50, 230], [210, 245, 60], [0, 128, 128], [170, 110, 40]]
def angka(x, d=0):
    """Format angka gaya Indonesia: titik untuk ribuan, koma untuk desimal."""
    return f'{x:,.{d}f}'.replace(',', '#').replace('.', ',').replace('#', '.')


WARNA_BULAN = {'Agustus': [245, 130, 48], 'September': [230, 25, 75], 'Oktober': [145, 30, 180]}


@st.cache_data
def muat():
    data = pd.read_csv(f'{H}/titikpanas.csv.gz')
    grid = pd.read_csv(f'{H}/gridsearch.csv')
    kab = pd.read_csv(f'{H}/kabupaten.csv')
    bulan = pd.read_csv(f'{H}/bulan.csv')
    pusat = pd.read_csv(f'{H}/pusatklaster.csv')
    kabbulan = pd.read_csv(f'{H}/kabupatenbulan.csv')
    batas = json.load(open(f'{H}/batas.geojson'))
    ringkas = json.load(open(f'{H}/ringkasan.json'))
    tambahan = {n: pd.read_csv(f'{H}/{n}.csv') for n in ['kepadatan', 'harian', 'klaster', 'pusatsebaran', 'pergeseran']}
    return data, grid, kab, bulan, pusat, kabbulan, batas, ringkas, tambahan


data, grid, kab, bulan, pusat, kabbulan, batas, R, X = muat()

st.title('Klasterisasi Titik Panas Kalimantan Tengah dengan DBSCAN')
st.caption('Kelompok 5 · 3KA33 · Metodologi Penelitian · Data: titik panas VIIRS S-NPP (NRT) FIRMS NASA, '
           '1 Agustus sampai 31 Oktober 2026 · Batas wilayah: GADM 4.1')

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric('Titik panas dianalisis', f"{R['jumlah_titik']:,}".replace(',', '.'))
c2.metric('Eps / MinPts terbaik', f"{R['eps_km']:g} km / {R['minpts']}")
c3.metric('Silhouette Coefficient', f"{R['silhouette']:.4f}".replace('.', ','))
c4.metric('Jumlah klaster', R['jumlah_klaster'])
c5.metric('Titik noise', f"{R['persen_noise']:.2f}%".replace('.', ','))

tab1, tab2, tab3, tab4 = st.tabs(['1. Parameter terbaik (RM1)', '2. Peta sebaran (RM2)',
                                  '3. Perubahan per bulan (RM3)', '4. Tentang data'])


def peta(titik, kol, judul_tooltip):
    titik = titik.copy()
    titik['warna'] = titik[kol].apply(lambda k: [150, 150, 150, 90] if k == -1 else WARNA[int(k) % 10] + [200])
    lapis_batas = pdk.Layer('GeoJsonLayer', batas, stroked=True, filled=True, get_fill_color=[255, 255, 255, 20],
                            get_line_color=[40, 40, 40], line_width_min_pixels=1, pickable=True)
    lapis_titik = pdk.Layer('ScatterplotLayer', titik, get_position='[longitude, latitude]', get_fill_color='warna',
                            get_radius=350, radius_min_pixels=1.2, pickable=True)
    view = pdk.ViewState(latitude=-1.6, longitude=113.4, zoom=6.3)
    tip = {'html': '<b>{kabupaten}</b><br/>' + judul_tooltip + ': {' + kol + '}<br/>Tanggal: {acq_date}',
           'style': {'fontSize': '12px'}}
    return pdk.Deck(layers=[lapis_batas, lapis_titik], initial_view_state=view, tooltip=tip, map_style=None)


with tab1:
    st.subheader('Mencari Eps dan MinPts terbaik berdasarkan Silhouette Coefficient')
    st.write('DBSCAN dijalankan dengan 15 kombinasi Eps dan MinPts. Jarak dihitung dengan haversine dalam kilometer. '
             'Silhouette dihitung tanpa titik noise, memakai sampel acak 10.000 titik.')
    piv = grid.pivot(index='minpts', columns='eps_km', values='silhouette')
    fig = px.imshow(piv, text_auto='.3f', color_continuous_scale='RdYlGn', aspect='auto',
                    labels=dict(x='Eps (km)', y='MinPts', color='Silhouette'))
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width='stretch')
    tampil = grid.sort_values('silhouette', ascending=False).rename(columns={
        'eps_km': 'Eps (km)', 'minpts': 'MinPts', 'jumlah_klaster': 'Jumlah klaster', 'titik_noise': 'Titik noise',
        'persen_noise': 'Noise (%)', 'silhouette': 'Silhouette'})
    st.dataframe(tampil, hide_index=True, width='stretch')
    st.info(f"Kombinasi terbaik: Eps {R['eps_km']:g} km dan MinPts {R['minpts']} dengan Silhouette "
            f"{R['silhouette']:.4f}. Nilai ini rendah karena titik panas tiga bulan ditumpuk dalam satu peta, "
            "sehingga banyak klaster saling berdekatan. Per bulan, nilainya lebih tinggi (lihat tab 3).")

with tab2:
    st.subheader('Pola sebaran klaster titik panas menurut kabupaten/kota')
    pilih = st.radio('Periode', ['Seluruh periode'] + BULAN, horizontal=True)
    if pilih == 'Seluruh periode':
        t, kol = data, 'klaster'
    else:
        t, kol = data[data['bulan'] == pilih], 'klaster_bulan'
    st.pydeck_chart(peta(t[['latitude', 'longitude', 'kabupaten', 'acq_date', kol]], kol, 'Klaster'), height=520)
    st.caption('Warna menunjukkan klaster yang berbeda; titik abu-abu adalah noise. Garis menunjukkan batas kabupaten/kota.')
    a, b = st.columns([3, 2])
    with a:
        st.dataframe(kab.rename(columns={'kabupaten': 'Kabupaten/kota', 'jumlah_titik': 'Jumlah titik',
                                         'titik_dalam_klaster': 'Dalam klaster', 'titik_noise': 'Noise',
                                         'jumlah_klaster': 'Jumlah klaster', 'persen_dari_kalteng': '% dari Kalteng'}),
                     hide_index=True, width='stretch')
    with b:
        fig = px.bar(kab.sort_values('jumlah_titik'), x='jumlah_titik', y='kabupaten', orientation='h',
                     labels={'jumlah_titik': 'Jumlah titik panas', 'kabupaten': ''})
        fig.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width='stretch')

    st.markdown('**Kepadatan titik panas per 1.000 km²** (luas dari poligon GADM 4.1, proyeksi luas-sama EPSG:6933)')
    kp = X['kepadatan']
    rata = 1000 * R['jumlah_titik'] / kp['luas_km2'].sum()
    st.caption(f"Rata-rata provinsi {angka(rata, 1)} titik per 1.000 km². Wilayah terpadat: {kp.iloc[0]['kabupaten']} "
               f"({angka(kp.iloc[0]['titik_per_1000km2'], 1)}), sekitar {angka(kp.iloc[0]['titik_per_1000km2'] / rata, 1)} kali rata-rata.")
    st.dataframe(kp.rename(columns={'kabupaten': 'Kabupaten/kota', 'luas_km2': 'Luas (km²)', 'jumlah_titik': 'Jumlah titik',
                                    'jumlah_klaster': 'Jumlah klaster', 'titik_per_1000km2': 'Titik per 1.000 km²',
                                    'klaster_per_1000km2': 'Klaster per 1.000 km²'}), hide_index=True, width='stretch')

    st.markdown('**Sepuluh klaster terbesar (seluruh periode)**')
    top = X['klaster'].head(10)
    st.caption(f"Sepuluh klaster ini menampung {angka(100 * top['jumlah_titik'].sum() / R['jumlah_titik'], 1)}% titik panas. "
               "Bentang adalah jarak diagonal kotak pembatas klaster, bukan luas area terbakar.")
    st.dataframe(top[['klaster', 'jumlah_titik', 'kabupaten_utama', 'jumlah_kabupaten', 'tanggal_pertama', 'tanggal_terakhir',
                      'hari_aktif', 'bentang_km']].rename(columns={
        'klaster': 'Klaster', 'jumlah_titik': 'Jumlah titik', 'kabupaten_utama': 'Kabupaten/kota utama', 'jumlah_kabupaten': 'Jumlah wilayah',
        'tanggal_pertama': 'Pertama terdeteksi', 'tanggal_terakhir': 'Terakhir terdeteksi', 'hari_aktif': 'Hari aktif', 'bentang_km': 'Bentang (km)'}),
        hide_index=True, width='stretch')

with tab3:
    st.subheader('Perubahan jumlah dan lokasi klaster dari Agustus sampai Oktober 2026')
    st.dataframe(bulan.rename(columns={'bulan': 'Bulan', 'jumlah_titik': 'Jumlah titik', 'jumlah_klaster': 'Jumlah klaster',
                                       'titik_noise': 'Noise', 'persen_noise': 'Noise (%)', 'silhouette': 'Silhouette',
                                       'kabupaten_terbanyak': 'Kabupaten dengan titik terbanyak'}),
                 hide_index=True, width='stretch')
    a, b = st.columns(2)
    with a:
        fig = px.bar(bulan, x='bulan', y='jumlah_klaster', text='jumlah_klaster', labels={'bulan': '', 'jumlah_klaster': 'Jumlah klaster'})
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), title='Jumlah klaster per bulan')
        st.plotly_chart(fig, width='stretch')
    with b:
        kb = kabbulan.set_index('kabupaten')[BULAN].sort_values('Oktober', ascending=False)
        st.write('Jumlah klaster per kabupaten/kota setiap bulan')
        st.dataframe(kb, width='stretch', height=320)
    st.write('Lokasi pusat klaster setiap bulan (ukuran lingkaran = jumlah titik dalam klaster)')
    p = pusat.copy()
    p['warna'] = p['bulan'].map(WARNA_BULAN).apply(lambda w: w + [170])
    lap = [pdk.Layer('GeoJsonLayer', batas, stroked=True, filled=False, get_line_color=[40, 40, 40], line_width_min_pixels=1),
           pdk.Layer('ScatterplotLayer', p, get_position='[lon_pusat, lat_pusat]', get_fill_color='warna',
                     get_radius='jumlah_titik * 6', radius_min_pixels=2, pickable=True)]
    st.pydeck_chart(pdk.Deck(layers=lap, initial_view_state=pdk.ViewState(latitude=-1.6, longitude=113.4, zoom=6.3),
                             tooltip={'html': '<b>{bulan}</b><br/>{kabupaten_utama}<br/>{jumlah_titik} titik'}, map_style=None), height=480)
    st.caption('Oranye = Agustus, merah = September, ungu = Oktober.')
    g = X['pergeseran']
    st.info(f"Pusat sebaran titik dalam klaster bergeser {angka(g.iloc[0]['jarak_km'], 1)} km ke {g.iloc[0]['arah']} dari Agustus ke September, "
            f"lalu {angka(g.iloc[1]['jarak_km'], 1)} km ke {g.iloc[1]['arah']} pada Oktober (total {angka(g.iloc[2]['jarak_km'], 1)} km ke {g.iloc[2]['arah']}).")
    st.write('Titik panas per hari (pelengkap dari kolom acq_date; klasterisasi tetap per bulan)')
    h = X['harian']
    fig = px.bar(h, x='tanggal', y='jumlah_titik', labels={'tanggal': '', 'jumlah_titik': 'Jumlah titik panas'})
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width='stretch')

with tab4:
    st.subheader('Data dan tahapan pengolahan')
    st.markdown(f"""
- **Sumber data:** titik panas VIIRS S-NPP versi NRT dari FIRMS NASA (1 Agustus sampai 31 Oktober 2026) dan batas kabupaten/kota GADM 4.1.
- **Penyusunan dataset:** {R['titik_kalteng']:,} titik di dalam Kalimantan Tengah, {R['titik_setelah_confidence']:,} setelah deteksi *confidence* rendah dibuang, {R['jumlah_titik']:,} setelah data ganda dihapus.
- **Fitur klasterisasi:** hanya *latitude* dan *longitude*. Kolom *acq_date* untuk membagi per bulan, *confidence* untuk penyaringan.
- **Algoritma:** DBSCAN dengan jarak haversine (kilometer). Parameter dipilih berdasarkan *Silhouette Coefficient*.
- **Batasan:** titik panas adalah indikasi kebakaran, bukan bukti kebakaran yang pasti; dashboard ini hanya menampilkan hasil analisis.
""".replace(',', '.'))
