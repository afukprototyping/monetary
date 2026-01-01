import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Financial Dashboard", layout="wide")

# --- KONFIGURASI GOOGLE SHEETS ---
SHEET_NAME = "Database Monetary Afuk"

# --- BAGIAN KEAMANAN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.text_input("Masukkan Password:", type="password", key="password_input")
        if st.session_state.password_input == st.secrets["PASSWORD_APP"]:
            st.session_state.password_correct = True
            st.rerun()
        elif st.session_state.password_input != "":
            st.error("😕 Password salah.")
        return False
    return True

if not check_password():
    st.stop()

# --- FUNGSI KONEKSI DATABASE ---
@st.cache_resource
def connect_to_gsheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def load_data():
    client = connect_to_gsheets()
    try:
        sheet = client.open(SHEET_NAME).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty:
            return pd.DataFrame(columns=['Tanggal', 'Tipe', 'Kategori', 'Sumber', 'Tujuan', 'Nominal', 'Catatan'])
        
        df['Tanggal'] = pd.to_datetime(df['Tanggal'], format='mixed')
        return df
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"❌ File Google Sheet '{SHEET_NAME}' tidak ditemukan.")
        st.stop()

def save_data(new_entry):
    client = connect_to_gsheets()
    sheet = client.open(SHEET_NAME).sheet1
    
    if len(sheet.get_all_values()) == 0:
        header = ['Tanggal', 'Tipe', 'Kategori', 'Sumber', 'Tujuan', 'Nominal', 'Catatan']
        sheet.append_row(header)
    
    row_values = [
        new_entry['Tanggal'].strftime("%Y-%m-%d"),
        new_entry['Tipe'],
        new_entry['Kategori'],
        new_entry['Sumber'],
        new_entry['Tujuan'],
        new_entry['Nominal'],
        new_entry['Catatan']
    ]
    sheet.append_row(row_values)

# ==========================================
# 🚀 APLIKASI UTAMA
# ==========================================

AKUN_LIST = ['BSI', 'Permata', 'BCA', 'Gopay', 'Cash', 'Tabungan/Investasi']
BUDGET_PLAN = {
    'Makan': 1800000,
    'Transport': 200000,
    'Main/Entertainment': 100000,
    'Parfum & Sabun': 100000,
    'Sedekah & Admin': 50000,
    'Nabung': 700000
}

# --- LOAD DATA AWAL ---
df = load_data()

st.title("💰 Financial Dashboard")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Filter Data")
    
    if not df.empty:
        df['Bulan_Tahun'] = df['Tanggal'].dt.strftime('%Y-%m')
        available_months = sorted(df['Bulan_Tahun'].unique(), reverse=True)
    else:
        available_months = [datetime.now().strftime('%Y-%m')]

    selected_month_str = st.selectbox("Pilih Bulan", available_months)
    sel_year, sel_month = map(int, selected_month_str.split('-'))

    st.divider()

    st.header("📝 Input Transaksi Baru")
    tgl = st.date_input("Tanggal", datetime.now())
    tipe = st.selectbox("Tipe", ["Expense (Pengeluaran)", "Income (Pemasukan)", "Transfer (Pindah Dana)"])
    
    kategori, sumber, tujuan = "-", "-", "-"
    
    if "Expense" in tipe:
        sumber = st.selectbox("Sumber Dana", AKUN_LIST)
        kategori = st.selectbox("Kategori", list(BUDGET_PLAN.keys()) + ["Lainnya"])
    elif "Income" in tipe:
        tujuan = st.selectbox("Masuk ke Akun", AKUN_LIST)
        kategori = "Income"
    elif "Transfer" in tipe:
        col_tr1, col_tr2 = st.columns(2)
        with col_tr1: sumber = st.selectbox("Dari", AKUN_LIST)
        with col_tr2: tujuan = st.selectbox("Ke", AKUN_LIST, index=len(AKUN_LIST)-1)
        
        is_saving = st.checkbox("✅ Ini Nabung?")
        kategori = "Nabung" if is_saving else "Transfer"

    nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000)
    catatan = st.text_input("Catatan")
    
    if st.button("Simpan ke Cloud ☁️"):
        entry = {
            'Tanggal': tgl,
            'Tipe': tipe.split(" ")[0],
            'Kategori': kategori,
            'Sumber': sumber,
            'Tujuan': tujuan,
            'Nominal': nominal,
            'Catatan': catatan
        }
        with st.spinner("Menyimpan ke Google Sheets..."):
            save_data(entry)
        st.success("Berhasil tersimpan!")
        st.cache_data.clear()
        st.rerun()

# --- FILTER DATA UTAMA (BULANAN) ---
if not df.empty:
    df_month = df[(df['Tanggal'].dt.month == sel_month) & (df['Tanggal'].dt.year == sel_year)]
else:
    df_month = pd.DataFrame()

# --- KPI SALDO (GLOBAL) ---
saldo_cols = st.columns(len(AKUN_LIST))
total_harta = 0

if not df.empty:
    for i, akun in enumerate(AKUN_LIST):
        masuk = df[((df['Tipe'] == 'Income') | (df['Tipe'] == 'Transfer')) & (df['Tujuan'] == akun)]['Nominal'].sum()
        keluar = df[((df['Tipe'] == 'Expense') | (df['Tipe'] == 'Transfer')) & (df['Sumber'] == akun)]['Nominal'].sum()
        saldo_akhir = masuk - keluar
        total_harta += saldo_akhir
        with saldo_cols[i]:
            st.metric(label=akun, value=f"{saldo_akhir:,.0f}")
else:
    st.info("Belum ada data transaksi.")

st.info(f"**Net Worth Saat Ini: Rp {total_harta:,.0f}**")
st.divider()

# --- MONITORING BUDGET (BULANAN) ---
nama_bulan = datetime(sel_year, sel_month, 1).strftime('%B %Y')
st.subheader(f"📉 Monitoring Budget ({nama_bulan})")

col_kiri, col_kanan = st.columns([2, 1])

with col_kiri:
    total_budget = sum(BUDGET_PLAN.values())
    total_spent_month = 0
    if not df_month.empty:
        for kat, pagu in BUDGET_PLAN.items():
            terpakai = df_month[((df_month['Tipe'] == 'Expense') | (df_month['Tipe'] == 'Transfer')) & (df_month['Kategori'] == kat)]['Nominal'].sum()
            persen = min(terpakai / pagu, 1.0) if pagu > 0 else 0
            total_spent_month += terpakai
            
            st.write(f"**{kat}**")
            c1, c2 = st.columns([3, 1])
            c1.progress(persen)
            c2.write(f"{terpakai:,.0f} / {pagu:,.0f}")
    else:
        st.write("Belum ada data untuk bulan ini.")

with col_kanan:
    sisa_total = total_budget - total_spent_month
    st.metric("Total Budget", f"{total_budget:,.0f}")
    st.metric("Terpakai", f"{total_spent_month:,.0f}", delta_color="inverse")
    st.metric("Sisa", f"{sisa_total:,.0f}", delta=f"{sisa_total:,.0f}")

st.divider()

# --- CHART VISUALISASI ---
st.subheader("📊 Analisis Pengeluaran")

if not df_month.empty:
    # 1. Ambil data Expense saja
    df_expense = df_month[df_month['Tipe'] == 'Expense'].copy()
    
    if not df_expense.empty:
        # --- FITUR INTERAKTIF (FILTER KATEGORI) ---
        # Ini akan mengontrol KEDUA chart di bawahnya
        unique_categories = df_expense['Kategori'].unique().tolist()
        selected_categories = st.multiselect(
            "🎛️ Filter Kategori (Pilih untuk ditampilkan):",
            unique_categories,
            default=unique_categories
        )

        # Filter data berdasarkan pilihan user
        df_chart = df_expense[df_expense['Kategori'].isin(selected_categories)]

        if not df_chart.empty:
            col_chart1, col_chart2 = st.columns([2, 1])

            # 1. LINE CHART (Tren Harian Biasa)
            # Menggunakan Line Chart biasa agar lebih clear dan tidak aneh
            with col_chart1:
                st.caption("Tren Pengeluaran Harian")
                # Grouping
                daily_chart = df_chart.groupby(['Tanggal', 'Kategori'])['Nominal'].sum().reset_index()
                
                fig_line = px.line(
                    daily_chart, 
                    x="Tanggal", 
                    y="Nominal", 
                    color="Kategori",
                    markers=True, # Pakai titik agar jelas posisi datanya
                    title=None
                )
                fig_line.update_layout(
                    xaxis_title=None,
                    yaxis_title=None,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    plot_bgcolor="rgba(0,0,0,0)",
                    hovermode="x unified" # Hover satu garis vertikal untuk liat semua kategori di tanggal itu
                )
                fig_line.update_yaxes(showgrid=True, gridcolor='rgba(200,200,200,0.2)')
                st.plotly_chart(fig_line, use_container_width=True)

            # 2. HORIZONTAL BAR CHART (Proporsi)
            # Data ini juga ikut berubah sesuai filter di atas
            with col_chart2:
                st.caption("Proporsi Kategori (%)")
                
                bar_data = df_chart.groupby('Kategori')['Nominal'].sum().reset_index()
                total_filtered = bar_data['Nominal'].sum()
                
                bar_data['Persen'] = (bar_data['Nominal'] / total_filtered) * 100
                bar_data = bar_data.sort_values(by='Persen', ascending=True)

                fig_bar = px.bar(
                    bar_data, 
                    x='Persen', 
                    y='Kategori', 
                    orientation='h', 
                    text=bar_data['Persen'].apply(lambda x: '{0:1.1f}%'.format(x)),
                    color='Kategori', 
                )
                
                fig_bar.update_layout(
                    showlegend=False,
                    xaxis_title=None,
                    yaxis_title=None,
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=0, b=0, l=0, r=0),
                    height=300
                )
                fig_bar.update_xaxes(showgrid=False, showticklabels=False)
                fig_bar.update_yaxes(showgrid=False)
                
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning("⚠️ Tidak ada kategori yang dipilih.")
    else:
        st.info("Belum ada pengeluaran di bulan ini.")
else:
    st.write("Tidak ada data untuk ditampilkan.")

st.divider()

# --- TABLE TRANSAKSI ---
with st.expander(f"Riwayat Transaksi - {nama_bulan}"):
    if not df_month.empty:
        df_display = df_month.copy()
        df_display['Tanggal'] = df_display['Tanggal'].dt.strftime('%d-%m-%Y')
        st.dataframe(df_display.sort_values(by='Tanggal', ascending=False), use_container_width=True)
    else:
        st.write("Tidak ada data.")
