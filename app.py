import streamlit as st
import pandas as pd
import pdfplumber
import sqlite3
import re

# ==========================================
# 1. SETUP DATABASE (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect('equity_notes.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS corporate_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            jenis_aksi TEXT,
            status TEXT,
            tanggal_cum TEXT,
            rasio TEXT,
            sumber_file TEXT
        )
    ''')
    conn.commit()
    return conn

# ==========================================
# 2. LOGIKA EKSTRAKSI PDF (Regex Lanjutan)
# ==========================================
def extract_data_from_pdf(pdf_file):
    extracted_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        # Membaca 5 halaman pertama saja agar lebih cepat (info penting biasanya di awal)
        for page in pdf.pages[:5]:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
    
    # 1. Ekstraksi Ticker
    ticker_match = re.search(r'\("([A-Z]{4})"\)', extracted_text)
    ticker = ticker_match.group(1) if ticker_match else "UNKNOWN"
    
    # 2. Deteksi Jenis Aksi Korporasi
    jenis_aksi = "Lainnya"
    if re.search(r'(HAK MEMESAN EFEK TERLEBIH DAHULU|HMETD|RIGHT ISSUE)', extracted_text, re.IGNORECASE):
        jenis_aksi = "Right Issue"
    elif re.search(r'(TENDER OFFER|PENAWARAN TENDER)', extracted_text, re.IGNORECASE):
        jenis_aksi = "Tender Offer"
    elif re.search(r'(TANPA HAK MEMESAN EFEK TERLEBIH DAHULU|PMTHMETD|PRIVATE PLACEMENT)', extracted_text, re.IGNORECASE):
        jenis_aksi = "Private Placement"
    elif re.search(r'(RAPAT UMUM PEMEGANG SAHAM|RUPS)', extracted_text, re.IGNORECASE):
        jenis_aksi = "RUPS"

    # 3. Ekstraksi Rasio (Pola: "Setiap X saham ... berhak atas Y HMETD")
    rasio = "Tidak Ditemukan"
    # Regex ini mencari angka setelah kata 'Setiap', mengabaikan kata-kata di tengah, lalu mencari angka setelah 'atas'
    match_rasio = re.search(r'Setiap\s+(\d+(?:[.,]\d+)?)[^\.]+?berhak\s+atas\s+(\d+(?:[.,]\d+)?)', extracted_text, re.IGNORECASE)
    if match_rasio:
        rasio = f"{match_rasio.group(1)} : {match_rasio.group(2)}"
    else:
        # Coba pola alternatif: "Rasio X : Y"
        match_rasio_alt = re.search(r'Rasio.*?(\d+)\s*:\s*(\d+)', extracted_text, re.IGNORECASE)
        if match_rasio_alt:
            rasio = f"{match_rasio_alt.group(1)} : {match_rasio_alt.group(2)}"

    # 4. Ekstraksi Tanggal Cum-Date (Pencarian format tanggal di sekitar kata "Cum")
    tanggal_cum = "Tidak Ditemukan"
    # Mencari kata 'Cum', lalu mencari pola tanggal (misal: 12 Agustus 2026 atau 12-Agu-2026)
    match_cum = re.search(r'Cum[^\n\:]*?:\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})', extracted_text, re.IGNORECASE)
    if match_cum:
        tanggal_cum = match_cum.group(1)
    else:
        # Pola alternatif jika format tabel
        match_cum_alt = re.search(r'Cum.*?Reguler.*?\n.*?([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})', extracted_text, re.IGNORECASE)
        if match_cum_alt:
            tanggal_cum = match_cum_alt.group(1)

    return {
        "ticker": ticker,
        "jenis_aksi": jenis_aksi,
        "status": "Pipeline", # Diubah ke Pipeline sebagai default
        "tanggal_cum": tanggal_cum.strip() if tanggal_cum != "Tidak Ditemukan" else tanggal_cum,
        "rasio": rasio,
        "sumber_file": pdf_file.name
    }

def insert_to_db(conn, data):
    c = conn.cursor()
    c.execute('''
        INSERT INTO corporate_actions (ticker, jenis_aksi, status, tanggal_cum, rasio, sumber_file)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data['ticker'], data['jenis_aksi'], data['status'], data['tanggal_cum'], data['rasio'], data['sumber_file']))
    conn.commit()

# ==========================================
# 3. ANTARMUKA DASHBOARD (Streamlit)
# ==========================================
st.set_page_config(page_title="Equity Notes", layout="wide")
conn = init_db()

st.title("📊 Equity Notes: Corporate Actions Automator")
st.write("Sistem otomatis ekstraksi prospektus IDX dan pemantauan aksi korporasi.")

# --- Bagian Upload & Proses PDF ---
with st.expander("➕ Tambah Data (Upload Prospektus)", expanded=True):
    uploaded_file = st.file_uploader("Upload File Pengumuman/Prospektus IDX (PDF)", type="pdf")

    if uploaded_file is not None:
        if st.button("Proses Ekstraksi PDF", type="primary"):
            with st.spinner("Mengekstrak data menggunakan Regex..."):
                extracted_data = extract_data_from_pdf(uploaded_file)
                insert_to_db(conn, extracted_data)
                
                st.success(f"Data {extracted_data['ticker']} berhasil ditambahkan ke database!")
                
                # Tampilkan preview hasil ekstraksi agar bisa divalidasi langsung
                st.json(extracted_data)

st.divider()

# --- Bagian Dashboard Utama ---
st.header("Terminal Aksi Korporasi")

df = pd.read_sql_query("SELECT * FROM corporate_actions", conn)

if not df.empty:
    col1, col2 = st.columns(2)
    with col1:
        aksi_filter = st.multiselect("Filter Jenis Aksi:", options=df['jenis_aksi'].unique(), default=df['jenis_aksi'].unique())
    with col2:
        search_ticker = st.text_input("Cari Ticker:")

    # Logika Filter
    df_filtered = df[df['jenis_aksi'].isin(aksi_filter)]
    if search_ticker:
        df_filtered = df_filtered[df_filtered['ticker'].str.contains(search_ticker.upper())]
    
    st.dataframe(
        df_filtered[['ticker', 'jenis_aksi', 'status', 'tanggal_cum', 'rasio', 'sumber_file']], 
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Database masih kosong. Silakan upload dokumen PDF pertama Anda di atas.")

conn.close()
