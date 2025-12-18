# app.py
# Streamlit version of muadil finder (Flask -> Streamlit)

import streamlit as st
import pandas as pd
import re
import os
import warnings
import random
from datetime import datetime

warnings.filterwarnings("ignore")

# ---------------------------
# CONFIG
# ---------------------------
FILE_PATH = "KAHVEMUADİLLER.xlsx"

CATEGORIES = ["ESPRESSO", "TURK_KAHVESI", "FILTRE_KAHVE"]

FEATURES = {
    "ESPRESSO": ["BARISTA_TIPI", "YARI_OTOMATIK", "TAM_OTOMATIK", "OGUTUCU", "SUTLU", "BARDAK_ISITICI"],
    "TURK_KAHVESI": ["SUTLU", "KOZDE", "OGUTUCU"],
    "FILTRE_KAHVE": ["OGUTUCU"]
}

KULLANIM_OPTIONS = ["Ev", "Ofis", "Profesyonel"]

BRANDS = [
    "JURA", "DELONGHI", "DE'LONGHI", "MIELE", "SIEMENS", "BOSCH", "PHILIPS",
    "BREVILLE", "WMF", "KARACA", "LEGGNO", "ARZUM", "FAKIR", "SAGE",
    "NESPRESSO", "TCHIBO", "BEKO", "ARÇELİK", "ANKA", "GASTROBACK",
    "CASO", "HAFELE"
]

# ---------------------------
# Helpers
# ---------------------------
def normalize_col(name):
    if not isinstance(name, str):
        return name
    s = name.strip()
    s = s.replace("İ","I").replace("ı","i").replace("Ğ","G").replace("ğ","g")
    s = s.replace("Ü","U").replace("ü","u").replace("Ş","S").replace("ş","s")
    s = s.replace("Ö","O").replace("ö","o").replace("Ç","C").replace("ç","c")
    s = re.sub(r"[^\w]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s.upper()

def safe_str(v):
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    s = str(v)
    return "" if s.lower() == "nan" else s.strip()

def is_true(v):
    return safe_str(v).upper() in ("1","TRUE","✔","DOGRU","EVET","YES")

def tick(v):
    return "✔" if is_true(v) else "❌"

def normalize_usage(value):
    s = safe_str(value).lower()
    if "ev" in s:
        return "Ev"
    if "ofis" in s:
        return "Ofis"
    if "prof" in s:
        return "Profesyonel"
    return value.title() if value else ""

def find_sheet_name(excel, candidates):
    for cand in candidates:
        for s in excel.sheet_names:
            if normalize_col(s) == normalize_col(cand):
                return s
    return None

@st.cache_data
def load_sheets():
    if not os.path.isfile(FILE_PATH):
        st.error("Excel dosyası bulunamadı")
        st.stop()

    xls = pd.ExcelFile(FILE_PATH)

    sheets = {
        "ESPRESSO": find_sheet_name(xls, ["ESPRESSO"]),
        "TURK_KAHVESI": find_sheet_name(xls, ["TÜRK_KAHVESİ", "TURK_KAHVESI"]),
        "FILTRE_KAHVE": find_sheet_name(xls, ["FİLTRE_KAHVE", "FILTRE_KAHVE"])
    }

    data = {}
    for key, sheet in sheets.items():
        df = pd.read_excel(FILE_PATH, sheet_name=sheet)
        df.columns = [normalize_col(c) for c in df.columns]

        for col in ["MARKA","STOK_KODU","STOK_ADI","KULLANIM_AMACI"]:
            if col not in df.columns:
                df[col] = ""

        for feat in FEATURES.get(key, []):
            if feat not in df.columns:
                df[feat] = ""

        data[key] = df

    return data

def find_muadil(row, df, category):
    results = []
    for col in df.columns:
        if "MUAD" in col.upper():
            cell = safe_str(row.get(col))
            for tok in cell.replace(";",",").split(","):
                tok = tok.strip()
                if not tok:
                    continue
                match = df[df["STOK_KODU"].astype(str).str.upper() == tok.upper()]
                if not match.empty:
                    results.append(match.iloc[0])

    if not results:
        mask = pd.Series([True]*len(df))
        for feat in FEATURES.get(category, []):
            mask &= df[feat].apply(lambda x: is_true(x) == is_true(row.get(feat)))
        mask &= df["STOK_KODU"] != row["STOK_KODU"]
        candidates = df[mask]
        if not candidates.empty:
            results = list(candidates.sample(min(3,len(candidates))).iterrows())
            results = [r[1] for r in results]

    return results

# ---------------------------
# UI
# ---------------------------
st.set_page_config(page_title="Muadil Arama", layout="wide")
st.title("Muadil / Eşdeğer Ürün Arama")

data = load_sheets()

kategori = st.selectbox("Kategori", [""] + CATEGORIES)
aranan = st.text_input("Stok kodu veya ürün adı")

secilen_kullanim = st.multiselect("Kullanım Amacı", KULLANIM_OPTIONS)

secilen_ozellikler = []
if kategori:
    st.subheader("Özellikler")
    for feat in FEATURES[kategori]:
        if st.checkbox(feat.replace("_"," ").title()):
            secilen_ozellikler.append(feat)

if kategori:
    df = data[kategori].copy()

    if aranan:
        df = df[
            df["STOK_KODU"].astype(str).str.contains(aranan, case=False, na=False) |
            df["STOK_ADI"].astype(str).str.contains(aranan, case=False, na=False)
        ]

    for feat in secilen_ozellikler:
        df = df[df[feat].apply(is_true)]

    if secilen_kullanim:
        df = df[df["KULLANIM_AMACI"].isin(secilen_kullanim)]

    st.markdown(f"### {len(df)} sonuç bulundu")

    for _, row in df.iterrows():
        st.markdown(f"**{row['MARKA']} | {row['STOK_KODU']} | {row['STOK_ADI']}**")

        for feat in FEATURES[kategori]:
            st.write(f"{feat.replace('_',' ')}: {tick(row.get(feat))}")

        ka = normalize_usage(row.get("KULLANIM_AMACI"))
        if ka:
            st.write(f"KULLANIM AMACI: {ka}")

        muadiller = find_muadil(row, data[kategori], kategori)
        if muadiller:
            st.markdown("**Muadiller:**")
            for m in muadiller:
                st.write(f"➡ {m['MARKA']} | {m['STOK_KODU']} | {m['STOK_ADI']}")

        st.divider()
