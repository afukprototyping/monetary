import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Keuangan 2026", layout="wide")

# --- KONFIGURASI GOOGLE SHEETS ---
# Pastikan nama ini SAMA PERSIS dengan nama file Google Sheet kamu
SHEET_NAME = "Database Monetary Afuk"

# --- BAGIAN KEAMANAN (PASSWORD DARI SECRETS) ---
def check_password():
    """Meminta password sebelum masuk."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.text_input("Masukkan Password:", type="password", key="password_input")
        # Mengambil password dari Streamlit Secrets agar aman di Public Repo
        if st.session_state.password_input == st.secrets["PASSWORD_APP"]:
            st.session_state.password_correct = True
            st.rerun()
        elif st.session_state.password_input != "":
            st.error("😕 Password salah.")
        return False
    return True

if not check_password():
    st.stop()

# --- FUNGSI KONEKSI DATABASE (GOOGLE SHEETS) ---
# Menggunakan @st.cache_resource supaya koneksi tidak dibuat ulang terus menerus
@st.cache_resource
def connect_to_gsheets():
    # Mengambil credentials dari Secrets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"]) # Konversi object secrets ke dict
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def load_data():
    client = connect_to_gsheets()
    try:
        sheet = client.open(SHEET_NAME).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Jika sheet kosong (belum ada kolom), buat DataFrame kosong
        if df.empty:
            return pd.DataFrame(columns=['Tanggal', 'Tipe', 'Kategori', 'Sumber', 'Tujuan', 'Nominal', 'Catatan'])
        
        # Pastikan format tanggal benar
        df['Tanggal'] = pd.to_datetime(df['Tanggal'], format='mixed')
        return df
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"❌ File Google Sheet '{SHEET_NAME}' tidak ditemukan. Pastikan nama sama & sudah dishare ke email Service Account.")
        st.stop()

def save_data(new_entry):
    client = connect_to_gsheets()
    sheet = client.open(SHEET_NAME).sheet1
    
    # Jika baris pertama (header) belum ada, tulis dulu
    if len(sheet.get_all_values()) == 0:
        header = ['Tanggal', 'Tipe', 'Kategori', 'Sumber', 'Tujuan', 'Nominal', 'Catatan']
        sheet.append_row(header)
    
    # Ubah format tanggal jadi string agar diterima Google Sheet
    row_values = [
        new_entry['Tanggal'].strftime("%Y-%m-%d"),
        new_entry['Tipe'],
        new_entry['Kategori'],
        new_entry['Sumber'],
        new_entry['Tujuan'],
        int(new_entry['Nominal']),
        new_entry['Catatan']
    ]
    sheet.append_row(row_values)

# ==========================================
# 🚀 APLIKASI UTAMA
# ==========================================

# Daftar Akun & Budget
AKUN_LIST = ['BSI', 'Permata', 'BCA', 'Gopay', 'Cash', 'Tabungan/Investasi']
BUDGET_PLAN = {
    'Makan': 1800000,
    'Transport': 200000,
    'Main/Entertainment': 100000,
    'Parfum & Sabun': 100000,
    'Sedekah & Admin': 50000,
    'Nabung': 700000
}

st.title("💰 Dashboard Keuangan & KPI 2026 (Online Database)")

# 1. SIDEBAR: Input Transaksi
with st.sidebar:
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
        st.success("Berhasil tersimpan di Database!")
        # Gunakan st.rerun() dengan hati-hati agar tidak refresh berlebihan
        st.cache_data.clear() # Clear cache agar data baru terbaca
        st.rerun()

# --- PROSES DATA ---
df = load_data()

# Filter Data Bulan Ini
if not df.empty:
    current_month = datetime.now().month
    current_year = datetime.now().year
    df_month = df[(df['Tanggal'].dt.month == current_month) & (df['Tanggal'].dt.year == current_year)]
else:
    df_month = pd.DataFrame()

# --- KPI SALDO (HARTA) ---
st.subheader("🏦 Posisi Saldo (Real-Time)")
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

st.info(f"**Total Harta (Net Worth): Rp {total_harta:,.0f}**")
st.divider()

# --- MONITORING BUDGET ---
st.subheader(f"📉 Monitoring Budget (Bulan {datetime.now().month})")
col_kiri, col_kanan = st.columns([2, 1])

with col_kiri:
    total_budget = sum(BUDGET_PLAN.values())
    total_spent_month = 0
    if not df_month.empty:
        for kat, pagu in BUDGET_PLAN.items():
            terpakai = df_month[((df_month['Tipe'] == 'Expense') | (df_month['Tipe'] == 'Transfer')) & (df_month['Kategori'] == kat)]['Nominal'].sum()
            sisa = pagu - terpakai
            persen = min(terpakai / pagu, 1.0) if pagu > 0 else 0
            total_spent_month += terpakai
            
            st.write(f"**{kat}**")
            c1, c2 = st.columns([3, 1])
            c1.progress(persen)
            c2.write(f"{terpakai:,.0f} / {pagu:,.0f}")
    else:
        st.write("Belum ada data bulan ini.")

with col_kanan:
    sisa_total = total_budget - total_spent_month
    st.metric("Total Budget", f"{total_budget:,.0f}")
    st.metric("Terpakai", f"{total_spent_month:,.0f}", delta_color="inverse")
    st.metric("Sisa", f"{sisa_total:,.0f}", delta=f"{sisa_total:,.0f}")

st.divider()
with st.expander("Lihat Riwayat Transaksi (Google Sheets)"):
    st.dataframe(df.sort_values(by='Tanggal', ascending=False) if not df.empty else df, use_container_width=True)
