#!/usr/bin/env python3
"""
Swing Hunter - Path-Independent Advanced Mod Başlatıcı
"""

import os
import sys

# Path'leri ayarla
def setup_paths():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    paths_to_add = [
        project_root,
        os.path.join(project_root, 'CORE_ANALYZERS'),
        os.path.join(project_root, 'GUI_INTERFACE')
    ]
    
    for path in paths_to_add:
        if os.path.exists(path) and path not in sys.path:
            sys.path.insert(0, path)
    
    return project_root

# Path'leri hemen ayarla
PROJECT_ROOT = setup_paths()

def main():
    """Advanced modu başlat"""
    try:
        from swing_gui_advanced import SwingGUIAdvanced
        from PyQt5.QtWidgets import QApplication
        
        print("🚀 Swing Hunter - Advanced Mod Başlatılıyor...")
        print(f"📁 Proje Root: {PROJECT_ROOT}")
        
        # Gerekli klasörleri oluştur
        for folder in ['data_cache', 'exports', 'logs']:
            folder_path = os.path.join(PROJECT_ROOT, folder)
            os.makedirs(folder_path, exist_ok=True)
        
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        gui = SwingGUIAdvanced()
        gui.show()
        
        print("✅ Advanced Mod başarıyla başlatıldı!")
        print("💡 Özellikler: Multi-Timeframe, Fibonacci, Konsolidasyon, Backtest")
        
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Advanced Mod başlatılamadı: {e}")
        import traceback
        traceback.print_exc()
        input("Çıkmak için Enter'a basın...")
        sys.exit(1)

if __name__ == '__main__':
    main()