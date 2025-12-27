#!/bin/bash
# build.sh - Render için özel build script

echo "🚀 Swing Trade Platform kuruluyor..."

# Pip'i güncelle
python -m pip install --upgrade pip setuptools wheel

# ÖNEMLİ: Önce pandas 1.5.3 yükle (pyarrow'suz)
echo "📦 Pandas 1.5.3 yükleniyor..."
pip install pandas==1.5.3 --no-deps
pip install numpy==1.24.3

# Sonra diğer bağımlılıklar
echo "📦 Diğer kütüphaneler yükleniyor..."
pip install streamlit==1.28.0 plotly==5.17.0 yfinance==0.2.28

# TA-Lib alternatifi (PyQt5'siz)
pip install ta==0.10.2

# TVDataFeed (alternatif kurulum)
echo "📦 TVDataFeed yükleniyor..."
pip install tvdatafeed==1.5.4 || echo "TVDataFeed kurulamadı, yfinance kullanılacak"

echo "✅ Kurulum tamamlandı!"
