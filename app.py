import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- KONFIGURASI AWAL ---
st.set_page_config(page_title="Keuangan 2026", layout="wide")
FILE_DB = 'transaksi_keuangan.csv'

# ==========================================
# 🔒 BAGIAN KEAMANAN (PASSWORD)
# ==========================================
# Ganti "rahasia123" dengan password yang kamu mau
PASSWORD_ACCESS = "rahasia123" 

def check_password():
    """Meminta password sebelum menampilkan aplikasi utama."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.text_input("Masukkan Password:", type="password", key="password_input")
        if st.session_state.password_input == PASSWORD_ACCESS:
            st.session_state.password_correct = True
            st.rerun()
        elif st.session_state.password_input != "":
            st.error("😕 Password salah bro/sist.")
        return False
    return True

# Stop aplikasi jika password belum tembus
if not check_password():
    st.stop()

# ==========================================
# 🚀 APLIKASI UTAMA (Hanya jalan setelah login)
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

# --- FUNGSI LOAD & SAVE DATA ---
def load_data():
    if not os.path.exists(FILE_DB):
        df = pd.DataFrame(columns=['Tanggal', 'Tipe', 'Kategori', 'Sumber', 'Tujuan', 'Nominal', 'Catatan'])
        df.to_csv(FILE_DB, index=False)
    
    df = pd.read_csv(FILE_DB)
    # UPDATE: Menggunakan format='mixed' agar tidak error saat baca tanggal
    df['Tanggal'] = pd.to_datetime(df['Tanggal'], format='mixed')
    return df

def save_data(new_entry):
    df = load_data()
    new_df = pd.DataFrame([new_entry])
    df = pd.concat([df, new_df], ignore_index=True)
    df.to_csv(FILE_DB, index=False)

# --- UI UTAMA ---
st.title("💰 Dashboard Keuangan & KPI 2026")

# 1. SIDEBAR: Input Transaksi
with st.sidebar:
    st.header("📝 Input Transaksi Baru")
    
    tgl = st.date_input("Tanggal", datetime.now())
    tipe = st.selectbox("Tipe Transaksi", ["Expense (Pengeluaran)", "Income (Pemasukan)", "Transfer (Pindah Dana)"])
    
    # Logika Form Dinamis
    kategori = "-"
    sumber = "-"
    tujuan = "-"
    
    if "Expense" in tipe:
        sumber = st.selectbox("Sumber Dana (Bayar Pakai Apa?)", AKUN_LIST)
        kategori = st.selectbox("Kategori Budget", list(BUDGET_PLAN.keys()) + ["Lainnya"])
    elif "Income" in tipe:
        tujuan = st.selectbox("Masuk ke Akun Mana?", AKUN_LIST)
        kategori = "Income"
    elif "Transfer" in tipe:
        col_tr1, col_tr2 = st.columns(2)
        with col_tr1: sumber = st.selectbox("Dari Akun", AKUN_LIST)
        with col_tr2: tujuan = st.selectbox("Ke Akun", AKUN_LIST, index=len(AKUN_LIST)-1) # Default ke Tabungan
        
        # UPDATE: Checkbox agar Transfer bisa dihitung sebagai realisasi Nabung
        is_saving = st.checkbox("✅ Ini setoran untuk Target Nabung?")
        if is_saving:
            kategori = "Nabung"
        else:
            kategori = "Transfer"

    nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000)
    catatan = st.text_input("Catatan (Opsional)")
    
    if st.button("Simpan Transaksi"):
        entry = {
            'Tanggal': tgl,
            'Tipe': tipe.split(" ")[0], # Ambil kata pertama saja (Expense/Income/Transfer)
            'Kategori': kategori,
            'Sumber': sumber,
            'Tujuan': tujuan,
            'Nominal': nominal,
            'Catatan': catatan
        }
        save_data(entry)
        st.success("Data berhasil disimpan!")
        st.rerun() # Refresh halaman

# --- PROSES DATA ---
df = load_data()

# Filter Data Bulan Ini (Untuk KPI Budget)
current_month = datetime.now().month
current_year = datetime.now().year
df_month = df[(df['Tanggal'].dt.month == current_month) & (df['Tanggal'].dt.year == current_year)]

# --- BAGIAN 1: KPI SALDO (HARTA) ---
st.subheader("🏦 Posisi Saldo (Real-Time)")

# Hitung Saldo per Akun
saldo_cols = st.columns(len(AKUN_LIST))
total_harta = 0

for i, akun in enumerate(AKUN_LIST):
    # Rumus: Income + Transfer Masuk - Expense - Transfer Keluar
    masuk = df[((df['Tipe'] == 'Income') | (df['Tipe'] == 'Transfer')) & (df['Tujuan'] == akun)]['Nominal'].sum()
    keluar = df[((df['Tipe'] == 'Expense') | (df['Tipe'] == 'Transfer')) & (df['Sumber'] == akun)]['Nominal'].sum()
    saldo_akhir = masuk - keluar
    total_harta += saldo_akhir
    
    with saldo_cols[i]:
        st.metric(label=akun, value=f"{saldo_akhir:,.0f}")

st.info(f"**Total Harta (Net Worth): Rp {total_harta:,.0f}**")
st.divider()

# --- BAGIAN 2: MONITORING BUDGET BULANAN ---
st.subheader(f"📉 Monitoring Budget (Bulan {current_month}/{current_year})")

# Buat Tabel Progress Bar
col_kiri, col_kanan = st.columns([2, 1])

with col_kiri:
    budget_data = []
    total_budget = sum(BUDGET_PLAN.values())
    total_spent_month = 0
    
    for kat, pagu in BUDGET_PLAN.items():
        # UPDATE: Menghitung Expense ATAU Transfer yang kategorinya Nabung
        terpakai = df_month[
            ((df_month['Tipe'] == 'Expense') | (df_month['Tipe'] == 'Transfer')) & 
            (df_month['Kategori'] == kat)
        ]['Nominal'].sum()
        
        sisa = pagu - terpakai
        persen = min(terpakai / pagu, 1.0) if pagu > 0 else 0
        total_spent_month += terpakai
        
        # Tampilkan Progress Bar Custom
        st.write(f"**{kat}**")
        col_b1, col_b2 = st.columns([3, 1])
        col_b1.progress(persen)
        col_b2.write(f"{terpakai:,.0f} / {pagu:,.0f}")
        
        budget_data.append([kat, pagu, terpakai, sisa])

with col_kanan:
    # KPI Summary Bulanan
    sisa_total_budget = total_budget - total_spent_month
    st.metric("Total Pagu Budget", f"{total_budget:,.0f}")
    st.metric("Total Terpakai", f"{total_spent_month:,.0f}", delta_color="inverse")
    st.metric("Sisa Uang Operasional", f"{sisa_total_budget:,.0f}", delta=f"{sisa_total_budget:,.0f}")

st.divider()

# --- BAGIAN 3: HISTORY TRANSAKSI ---
with st.expander("Lihat Riwayat Transaksi Lengkap"):
    st.dataframe(df.sort_values(by='Tanggal', ascending=False), use_container_width=True)