#!/usr/bin/env python3
"""
Ultimate Swing Hunter - Path-Independent Başlatıcı
Launchers klasöründen çalıştırılabilir
"""

import os
import sys
import logging
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QMessageBox, QGroupBox,
                             QButtonGroup, QRadioButton, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
import json
import time

# Önce path'leri ayarla
def setup_paths():
    """Tüm gerekli path'leri proje root'una göre ayarla"""
    # Mevcut dosyanın bulunduğu dizin (Launchers klasörü)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Proje root dizinini bul (bir üst dizin)
    project_root = os.path.dirname(current_dir)
    
    # Gerekli path'leri sys.path'e ekle
    paths_to_add = [
        project_root,  # Root dizin
        os.path.join(project_root, 'CORE_ANALYZERS'),
        os.path.join(project_root, 'GUI_INTERFACE'), 
        os.path.join(project_root, 'CONFIG_FILES'),
        os.path.join(project_root, 'MAIN_SCRIPTS'),
        os.path.join(project_root, 'UTILITY')
    ]
    
    for path in paths_to_add:
        if os.path.exists(path) and path not in sys.path:
            sys.path.insert(0, path)  # Başa ekle ki öncelikli olsun
    
    return project_root

# Path'leri hemen ayarla
PROJECT_ROOT = setup_paths()

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemCheckThread(QThread):
    """Sistem kontrolü için thread"""
    finished = pyqtSignal(list)
    progress = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._is_running = True
        
    def run(self):
        try:
            status_messages = self.check_system()
            if self._is_running:
                self.finished.emit(status_messages)
        except Exception as e:
            if self._is_running:
                self.finished.emit([f"❌ Sistem kontrol hatası: {e}"])
    
    def stop(self):
        """Thread'i güvenli şekilde durdur"""
        self._is_running = False
        self.quit()
        self.wait(500)  # 500ms bekle

    def check_system(self):
        """Sistem gereksinimlerini kontrol et"""
        status_messages = []
        
        # Python modüllerini kontrol et
        packages = [
            ('pandas', 'pandas'),
            ('PyQt5', 'PyQt5'),
            ('tvDatafeed', 'tvDatafeed'),
            ('TA-Lib', 'talib'),
            ('python-dotenv', 'dotenv'),
            ('mplfinance', 'mplfinance'),
            ('openpyxl', 'openpyxl'),
            ('numpy', 'numpy'),
            ('matplotlib', 'matplotlib')
        ]
        
        for package_name, import_name in packages:
            if not self._is_running:
                return []
            try:
                __import__(import_name)
                status_messages.append(f"✅ {package_name} yüklü")
            except ImportError as e:
                status_messages.append(f"❌ {package_name} yüklenmemiş")
        
        # Config dosyalarını kontrol et (proje root'unda)
        if self._is_running:
            config_files = {
                'swing_config.json': 'Ana konfigürasyon',
                'chart_config.json': 'Grafik ayarları', 
            }
            
            for file, desc in config_files.items():
                file_path = os.path.join(PROJECT_ROOT, file)
                if os.path.exists(file_path):
                    status_messages.append(f"✅ {desc} mevcut")
                else:
                    status_messages.append(f"⚠️ {desc} bulunamadı")
        
        # Klasörleri kontrol et
        if self._is_running:
            folders = ['CORE_ANALYZERS', 'GUI_INTERFACE', 'CONFIG_FILES', 'data_cache', 'exports', 'logs']
            for folder in folders:
                folder_path = os.path.join(PROJECT_ROOT, folder)
                if os.path.exists(folder_path):
                    status_messages.append(f"✅ {folder}/ klasörü mevcut")
                else:
                    status_messages.append(f"⚠️ {folder}/ klasörü bulunamadı")
        
        return status_messages

class LauncherGUI(QWidget):
    """Path-Independent Başlatıcı GUI"""
    
    def __init__(self):
        super().__init__()
        self.selected_gui = "advanced"  # Varsayılan
        self.system_thread = None
        self.current_gui = None
        self.init_ui()
        
    def init_ui(self):
        """Başlatıcı UI'sını oluştur"""
        self.setWindowTitle("🚀 Ultimate Swing Hunter - Başlatıcı")
        self.setGeometry(300, 300, 700, 600)
        
        # Basit ve temiz CSS
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #1e3c72, stop: 1 #2a5298);
                color: white;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12pt;
                border: 2px solid #4CAF50;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 24px;
                font-size: 11pt;
                font-weight: bold;
                border-radius: 8px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QRadioButton {
                font-size: 11pt;
                padding: 8px;
                color: white;
            }
            QRadioButton::indicator {
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid #4CAF50;
                background-color: white;
            }
            QRadioButton::indicator:checked {
                background-color: #4CAF50;
                border: 2px solid white;
            }
            QTextEdit {
                background-color: rgba(0, 0, 0, 0.3);
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 5px;
                font-family: 'Consolas', monospace;
                font-size: 9pt;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Başlık
        title = QLabel("🚀 ULTIMATE SWING HUNTER")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 24pt;
                font-weight: bold;
                color: white;
                padding: 20px;
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y1: 0,
                    stop: 0 #FFD700, stop: 0.5 #4CAF50, stop: 1 #2196F3);
                border-radius: 15px;
                margin: 10px;
            }
        """)
        layout.addWidget(title)
        
        # Açıklama
        desc = QLabel("Profesyonel Swing Trade Analiz Sistemi")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("font-size: 14pt; color: #E0E0E0; padding: 10px;")
        layout.addWidget(desc)
        
        # Proje yolu bilgisi
        path_info = QLabel(f"📁 Proje Yolu: {PROJECT_ROOT}")
        path_info.setStyleSheet("font-size: 9pt; color: #90CAF9; padding: 5px;")
        path_info.setWordWrap(True)
        layout.addWidget(path_info)
        
        # GUI Seçim Bölümü
        selection_group = QGroupBox("🎮 ÇALIŞTIRMA MODU SEÇİN")
        selection_layout = QVBoxLayout()
        
        # Radio buton grubu
        self.button_group = QButtonGroup(self)
        
        # Basit Mod
        simple_rb = QRadioButton("🟢 BASİT MOD - Hızlı ve Kolay")
        simple_rb.setToolTip("Temel özellikler, hızlı tarama, basit arayüz")
        self.button_group.addButton(simple_rb, 1)
        
        simple_desc = QLabel("""
        • Temel swing analiz özellikleri
        • Hızlı tarama ve basit filtreler  
        • Kolay kullanım için optimize edilmiş
        • Yeni başlayanlar için ideal
        """)
        simple_desc.setStyleSheet("font-size: 10pt; color: #CCCCCC; padding-left: 30px;")
        simple_desc.setWordWrap(True)
        
        # Advanced Mod
        advanced_rb = QRadioButton("🔵 ADVANCED MOD - Profesyonel")
        advanced_rb.setToolTip("Tüm gelişmiş özellikler, multi-timeframe, backtest")
        self.button_group.addButton(advanced_rb, 2)
        
        advanced_desc = QLabel("""
        • Multi-timeframe analiz
        • Fibonacci retracement seviyeleri
        • Konsolidasyon pattern tespiti  
        • Backtest ve optimizasyon
        • Paralel tarama ve akıllı filtreler
        """)
        advanced_desc.setStyleSheet("font-size: 10pt; color: #CCCCCC; padding-left: 30px;")
        advanced_desc.setWordWrap(True)
        
        # Varsayılan seçim
        advanced_rb.setChecked(True)
        
        selection_layout.addWidget(simple_rb)
        selection_layout.addWidget(simple_desc)
        selection_layout.addSpacing(10)
        selection_layout.addWidget(advanced_rb)
        selection_layout.addWidget(advanced_desc)
        selection_group.setLayout(selection_layout)
        
        layout.addWidget(selection_group)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        self.launch_btn = QPushButton("🚀 UYGULAMAYI BAŞLAT")
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                font-size: 12pt;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.launch_btn.clicked.connect(self.launch_app)
        
        exit_btn = QPushButton("❌ ÇIKIŞ")
        exit_btn.clicked.connect(self.close_application)
        
        button_layout.addWidget(exit_btn)
        button_layout.addWidget(self.launch_btn)
        
        layout.addLayout(button_layout)
        
        # Sistem durumu
        status_group = QGroupBox("🖥️ SİSTEM DURUMU")
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setPlainText("Sistem kontrol ediliyor...")
        
        status_layout.addWidget(self.status_text)
        status_group.setLayout(status_layout)
        
        layout.addWidget(status_group)
        
        # Sinyal bağlantıları
        self.button_group.buttonClicked.connect(self.on_gui_selected)
        
        # Sistem kontrolünü başlat
        self.start_system_check()
        
    def start_system_check(self):
        """Sistem kontrol thread'ini başlat"""
        if self.system_thread and self.system_thread.isRunning():
            self.system_thread.stop()
            
        self.system_thread = SystemCheckThread()
        self.system_thread.finished.connect(self.on_system_check_complete)
        self.system_thread.start()
    
    def on_system_check_complete(self, status_messages):
        """Sistem kontrolü tamamlandığında"""
        if status_messages:
            self.status_text.setPlainText("\n".join(status_messages))
        
        # Thread'i temizle
        if self.system_thread:
            self.system_thread.stop()
            self.system_thread = None
    
    def on_gui_selected(self, button):
        """GUI seçimi değiştiğinde"""
        if button.text().startswith("🟢 BASİT MOD"):
            self.selected_gui = "simple"
            logger.info("Basit Mod seçildi")
        else:
            self.selected_gui = "advanced" 
            logger.info("Advanced Mod seçildi")
    
    def safe_thread_cleanup(self):
        """Thread'leri güvenli şekilde temizle"""
        if self.system_thread:
            if self.system_thread.isRunning():
                self.system_thread.stop()
            self.system_thread = None
    
    def close_application(self):
        """Uygulamayı güvenli kapat"""
        self.safe_thread_cleanup()
        self.close()
    
    def launch_app(self):
        """Seçilen GUI'yi başlat"""
        try:
            # Thread'leri temizle
            self.safe_thread_cleanup()
            
            # Gerekli klasörleri oluştur
            data_folders = ['data_cache', 'exports', 'logs']
            for folder in data_folders:
                folder_path = os.path.join(PROJECT_ROOT, folder)
                os.makedirs(folder_path, exist_ok=True)
            
            if self.selected_gui == "simple":
                self.launch_simple_gui()
            else:
                self.launch_advanced_gui()
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Uygulama başlatılamadı:\n{e}")
            logger.error(f"Başlatma hatası: {e}")
    
    def launch_simple_gui(self):
        """Basit GUI'yi başlat"""
        try:
            logger.info("Basit GUI başlatılıyor...")
            
            # Mevcut GUI'yi temizle
            if self.current_gui:
                try:
                    self.current_gui.close()
                    self.current_gui.deleteLater()
                except:
                    pass
                self.current_gui = None
            
            # GUI'yi import et ve başlat
            try:
                from gui_ultimate_integration import SwingGUIUltimate
                gui_class = SwingGUIUltimate
            except ImportError as e:
                logger.error(f"Basit GUI import hatası: {e}")
                # Alternatif import denemesi
                from GUI_INTERFACE.gui_ultimate_integration import SwingGUIUltimate
                gui_class = SwingGUIUltimate
            
            self.hide()  # Başlatıcıyı gizle
            
            # Yeni application context oluştur
            app = QApplication.instance()
            
            self.current_gui = gui_class()
            self.current_gui.show()
            
            logger.info("Basit GUI başarıyla başlatıldı")
            
            # GUI kapandığında başlatıcıyı tekrar göster
            def show_launcher():
                self.current_gui = None
                self.show()
                logger.info("Basit GUI kapandı, başlatıcı gösteriliyor")
                # Garbage collection için biraz bekle
                QApplication.processEvents()
            
            self.current_gui.destroyed.connect(show_launcher)
            
        except Exception as e:
            self.show()  # Hata durumunda başlatıcıyı tekrar göster
            self.current_gui = None
            error_msg = f"Basit GUI başlatılamadı:\n{str(e)}"
            QMessageBox.critical(self, "Hata", error_msg)
            logger.error(error_msg)
    
    def launch_advanced_gui(self):
        """Advanced GUI'yi başlat"""
        try:
            logger.info("Advanced GUI başlatılıyor...")
            
            # Mevcut GUI'yi temizle
            if self.current_gui:
                try:
                    self.current_gui.close()
                    self.current_gui.deleteLater()
                except:
                    pass
                self.current_gui = None
            
            # GUI'yi import et ve başlat
            try:
                from swing_gui_advanced import SwingGUIAdvanced
                gui_class = SwingGUIAdvanced
            except ImportError as e:
                logger.error(f"Advanced GUI import hatası: {e}")
                # Alternatif import denemesi
                from GUI_INTERFACE.swing_gui_advanced import SwingGUIAdvanced
                gui_class = SwingGUIAdvanced
            
            self.hide()  # Başlatıcıyı gizle
            
            # Yeni application context oluştur
            app = QApplication.instance()
            
            self.current_gui = gui_class()
            self.current_gui.show()
            
            logger.info("Advanced GUI başarıyla başlatıldı")
            
            # GUI kapandığında başlatıcıyı tekrar göster
            def show_launcher():
                self.current_gui = None
                self.show()
                logger.info("Advanced GUI kapandı, başlatıcı gösteriliyor")
                # Garbage collection için biraz bekle
                QApplication.processEvents()
            
            self.current_gui.destroyed.connect(show_launcher)
            
        except Exception as e:
            self.show()  # Hata durumunda başlatıcıyı tekrar göster
            self.current_gui = None
            error_msg = f"Advanced GUI başlatılamadı:\n{str(e)}"
            QMessageBox.critical(self, "Hata", error_msg)
            logger.error(error_msg)
    
    def closeEvent(self, event):
        """Pencere kapatıldığında - Thread güvenli kapatma"""
        logger.info("Başlatıcı kapatılıyor...")
        self.safe_thread_cleanup()
        
        # Mevcut GUI'yi temizle
        if self.current_gui:
            try:
                self.current_gui.close()
                self.current_gui.deleteLater()
            except:
                pass
            self.current_gui = None
            
        # Garbage collection
        QApplication.processEvents()
        time.sleep(0.1)  # Kısa bekleme
        
        event.accept()

def check_requirements():
    """Gereksinimleri kontrol et"""
    required_packages = [
        'pandas', 'numpy', 'tvDatafeed', 'talib',
        'openpyxl', 'PyQt5', 'python-dotenv', 'requests',
        'mplfinance', 'matplotlib'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_missing_packages(missing_packages):
    """Eksik paketleri yükle"""
    import subprocess
    
    for package in missing_packages:
        try:
            print(f"📦 {package} yükleniyor...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} başarıyla yüklendi")
        except subprocess.CalledProcessError as e:
            print(f"❌ {package} yüklenemedi: {e}")
            return False
    
    return True

def check_and_create_configs():
    """Gerekli config dosyalarını kontrol et ve oluştur (proje root'unda)"""
    config_files = {
        'swing_config.json': {
            "swing_enabled": True,
            "symbols": ["AKBNK", "GARAN", "THYAO", "TUPRS"],
            "exchange": "BIST",
            "lookback_bars": 250,
            "min_rsi": 30.0,
            "max_rsi": 70.0,
            "min_trend_score": 50,
            "create_charts": True,
            "use_multi_timeframe": True,
            "use_fibonacci": True,
            "use_consolidation": True
        },
        'chart_config.json': {
            "chart_settings": {
                "default_bars": 80,
                "candle_style": "charles",
                "figure_size": [12, 8],
                "dpi": 100
            }
        }
    }
    
    for config_file, default_config in config_files.items():
        file_path = os.path.join(PROJECT_ROOT, config_file)
        if not os.path.exists(file_path):
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                print(f"✅ {config_file} oluşturuldu: {file_path}")
            except Exception as e:
                print(f"⚠️ {config_file} oluşturulamadı: {e}")

def main():
    """Ana başlatıcı fonksiyonu"""
    print("🚀 Ultimate Swing Hunter - Path-Independent Başlatıcı")
    print("=" * 50)
    print(f"📁 Proje Root: {PROJECT_ROOT}")
    print(f"📁 Çalışma Dizini: {os.getcwd()}")
    
    # Gereksinimleri kontrol et
    missing_packages = check_requirements()
    
    if missing_packages:
        print(f"⚠️  Eksik paketler: {', '.join(missing_packages)}")
        
        # Otomatik yükleme seçeneği
        response = input("❓ Eksik paketleri otomatik yüklemek ister misiniz? (e/h): ")
        if response.lower() in ['e', 'y', 'yes']:
            if not install_missing_packages(missing_packages):
                print("❌ Bazı paketler yüklenemedi. Lütfen manuel yükleyin.")
                input("Çıkmak için Enter'a basın...")
                return
        else:
            print("❌ Lütfen eksik paketleri manuel olarak yükleyin:")
            print(f"pip install {' '.join(missing_packages)}")
            input("Çıkmak için Enter'a basın...")
            return
    
    # Config dosyalarını kontrol et ve oluştur
    check_and_create_configs()
    
    # Gerekli klasörleri oluştur
    data_folders = ['data_cache', 'exports', 'logs']
    for folder in data_folders:
        folder_path = os.path.join(PROJECT_ROOT, folder)
        os.makedirs(folder_path, exist_ok=True)
        print(f"✅ {folder} klasörü hazır: {folder_path}")
    
    # Başlatıcıyı başlat
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        launcher = LauncherGUI()
        launcher.show()
        
        print("✅ Başlatıcı başarıyla başlatıldı!")
        print("💡 Özellikler: Basit/Advanced mod seçimi, sistem kontrolü")
        
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Başlatıcı hatası: {e}")
        import traceback
        traceback.print_exc()
        input("Çıkmak için Enter'a basın...")

if __name__ == '__main__':
    main()