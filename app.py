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
# 2. LOGIKA EKSTRAKSI PDF (Otomatisasi)
# ==========================================
def extract_data_from_pdf(pdf_file):
    extracted_text = ""
    # Membaca teks dari PDF menggunakan pdfplumber
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            extracted_text += page.extract_text() + "\n"
    
    # ---------------------------------------------------------
    # TAHAP INI MEMBUTUHKAN PENYESUAIAN REGEX YANG PRESISI
    # Format pengumuman IDX bervariasi, ini adalah contoh dasar
    # ---------------------------------------------------------
    
    # Contoh Regex mencari Ticker (Biasanya PT XXX Tbk ("KODE"))
    ticker_match = re.search(r'\("([A-Z]{4})"\)', extracted_text)
    ticker = ticker_match.group(1) if ticker_match else "UNKNOWN"
    
    # Deteksi Jenis Aksi Korporasi dari judul/isi
    jenis_aksi = "Lainnya"
    if "HAK MEMESAN EFEK TERLEBIH DAHULU" in extracted_text.upper() or "HMETD" in extracted_text.upper():
        jenis_aksi = "Right Issue"
    elif "TENDER OFFER" in extracted_text.upper() or "PENAWARAN TENDER" in extracted_text.upper():
        jenis_aksi = "Tender Offer"
    elif "TANPA HAK MEMESAN EFEK TERLEBIH DAHULU" in extracted_text.upper() or "PMTHMETD" in extracted_text.upper():
        jenis_aksi = "Private Placement"
    elif "RAPAT UMUM PEMEGANG SAHAM" in extracted_text.upper() or "RUPS" in extracted_text.upper():
        jenis_aksi = "RUPS"

    # Menyusun data hasil ekstraksi
    data = {
        "ticker": ticker,
        "jenis_aksi": jenis_aksi,
        "status": "On Going", # Default status saat pertama diupload
        "tanggal_cum": "Cek Manual", # Perlu Regex spesifik untuk format tanggal IDX
        "rasio": "Cek Manual", # Perlu Regex spesifik 
        "sumber_file": pdf_file.name
    }
    return data

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
st.header("1. Input & Ekstraksi Dokumen")
uploaded_file = st.file_uploader("Upload File Pengumuman/Prospektus IDX (PDF)", type="pdf")

if uploaded_file is not None:
    if st.button("Proses Ekstraksi PDF"):
        with st.spinner("Membaca dokumen dan mengekstrak data..."):
            # Proses PDF
            extracted_data = extract_data_from_pdf(uploaded_file)
            
            # Simpan ke Database
            insert_to_db(conn, extracted_data)
            
            st.success(f"Data berhasil diekstrak dan disimpan! Ticker terdeteksi: **{extracted_data['ticker']}** ({extracted_data['jenis_aksi']})")

st.divider()

# --- Bagian Dashboard Utama ---
st.header("2. Dashboard Aksi Korporasi")

# Membaca isi database
df = pd.read_sql_query("SELECT * FROM corporate_actions", conn)

if not df.empty:
    # Filter Interaktif
    aksi_filter = st.multiselect("Filter Jenis Aksi:", options=df['jenis_aksi'].unique(), default=df['jenis_aksi'].unique())
    df_filtered = df[df['jenis_aksi'].isin(aksi_filter)]
    
    # Menampilkan Tabel Data
    st.dataframe(
        df_filtered[['ticker', 'jenis_aksi', 'status', 'tanggal_cum', 'rasio', 'sumber_file']], 
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Database masih kosong. Silakan upload dokumen PDF pertama Anda.")

conn.close()