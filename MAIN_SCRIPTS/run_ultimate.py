#!/usr/bin/env python3
"""
Ultimate Swing Hunter - Kolay Başlatıcı
"""

import os
import sys
import logging
from PyQt5.QtWidgets import QApplication

# Yolları ayarla
sys.path.append(os.path.join(os.path.dirname(__file__), 'CORE_ANALYZERS'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'GUI_INTERFACE'))

def main():
    """Ana başlatıcı"""
    try:
        from gui_ultimate_integration import SwingGUIUltimate
        
        print("🚀 Ultimate Swing Hunter Başlatılıyor...")
        print("=" * 50)
        
        # Gerekli klasörleri oluştur
        for folder in ['data_cache', 'exports', 'logs']:
            os.makedirs(folder, exist_ok=True)
        
        # GUI'yi başlat
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        gui = SwingGUIUltimate()
        gui.show()
        
        print("✅ Sistem başarıyla başlatıldı!")
        print("💡 Özellikler: Multi-Timeframe, Fibonacci, Konsolidasyon, Backtest")
        
        sys.exit(app.exec_())
        
    except Exception as e:
        logging.critical(f"Başlatma hatası: {e}")
        print(f"❌ Hata: {e}")
        input("Çıkmak için Enter'a basın...")
        sys.exit(1)

if __name__ == '__main__':
    main()