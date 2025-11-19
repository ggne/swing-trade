"""
Ultimate GUI - Multi-timeframe, Fibonacci ve Konsolidasyon entegreli
Swing Analyzer Ultimate ile tam entegre - Pandas 2.0+ Uyumlu
"""

import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QMessageBox, QProgressBar,
                             QTableWidget, QTableWidgetItem, QTextEdit, QLineEdit, 
                             QListWidget, QTabWidget, QHeaderView, QSplitter, QGroupBox,
                             QCheckBox, QFileDialog)
from PyQt5.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QFont
import logging
from datetime import datetime
import pandas as pd
import json

# Ultimate analyzer'ı import et
from swing_analyzer_ultimate import SwingHunterUltimate, AdvancedSignal

# ============================================================================
# Worker Sınıfları
# ============================================================================

class UltimateScanWorker(QObject):
    """Ultimate tarama worker"""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str)
    
    def __init__(self, hunter, symbols):
        super().__init__()
        self.hunter = hunter
        self.symbols = symbols
    
    def run(self):
        try:
            results = self.hunter.run_advanced_scan(
                self.symbols,
                progress_callback=self.progress.emit
            )
            
            self.finished.emit(results)
            
        except Exception as e:
            self.error.emit(str(e))


# ============================================================================
# Ana GUI
# ============================================================================

class SwingGUIUltimate(QWidget):
    """Ultimate Swing GUI"""
    
    def __init__(self):
        super().__init__()
        self.hunter = SwingHunterUltimate()
        self.cfg = self.hunter.cfg
        self.current_results = []
        
        self.init_ui()
        self.load_symbols()
        
        logging.info("✅ Ultimate GUI başlatıldı")
    
    def init_ui(self):
        """UI oluştur"""
        self.setWindowTitle("🚀 Swing Hunter Ultimate - Multi-Timeframe + Fibonacci + Konsolidasyon")
        self.setGeometry(50, 50, 1600, 900)
        
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                color: #1976D2;
            }
            QPushButton {
                padding: 10px 15px;
                font-weight: bold;
                border-radius: 6px;
                border: 1px solid #ccc;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
            }
            QTableWidget {
                gridline-color: #d0d0d0;
                border: 1px solid #ddd;
            }
            QTableWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
        """)
        
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        
        # Sol panel - Semboller ve ayarlar
        left_widget = self._create_left_panel()
        
        # Sağ panel - Sonuçlar
        right_widget = self._create_right_panel()
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 1100])
        
        main_layout.addWidget(splitter)
    
    def _create_left_panel(self):
        """Sol panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Başlık
        title = QLabel("🚀 Ultimate Scanner")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1976D2; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Özellikler
        features_group = QGroupBox("✨ Aktif Özellikler")
        features_layout = QVBoxLayout()
        
        self.use_mtf_cb = QCheckBox("📊 Multi-Timeframe Analiz (Günlük + Haftalık)")
        self.use_mtf_cb.setChecked(True)
        self.use_mtf_cb.setStyleSheet("padding: 5px;")
        
        self.use_fib_cb = QCheckBox("🌀 Fibonacci Retracement")
        self.use_fib_cb.setChecked(True)
        self.use_fib_cb.setStyleSheet("padding: 5px;")
        
        self.use_cons_cb = QCheckBox("📦 Konsolidasyon & Kırılım Tespiti")
        self.use_cons_cb.setChecked(True)
        self.use_cons_cb.setStyleSheet("padding: 5px;")
        
        features_layout.addWidget(self.use_mtf_cb)
        features_layout.addWidget(self.use_fib_cb)
        features_layout.addWidget(self.use_cons_cb)
        
        info_label = QLabel("ℹ️ Bu özellikler daha hassas analiz sağlar")
        info_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        info_label.setWordWrap(True)
        features_layout.addWidget(info_label)
        
        features_group.setLayout(features_layout)
        layout.addWidget(features_group)
        
        # Sembol listesi
        symbols_group = QGroupBox("📈 Hisse Sembolleri")
        symbols_layout = QVBoxLayout()
        
        self.symbol_list = QListWidget()
        self.symbol_list.setSelectionMode(QListWidget.ExtendedSelection)
        symbols_layout.addWidget(self.symbol_list)
        
        # Hisse ekleme
        add_layout = QHBoxLayout()
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Hisse kodu (örn: GARAN)")
        self.symbol_input.returnPressed.connect(self.add_symbol)
        
        add_btn = QPushButton("➕ Ekle")
        add_btn.clicked.connect(self.add_symbol)
        add_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        add_layout.addWidget(self.symbol_input)
        add_layout.addWidget(add_btn)
        symbols_layout.addLayout(add_layout)
        
        # Hızlı ekleme
        quick_layout = QHBoxLayout()
        
        bist30_btn = QPushButton("BIST30")
        bist30_btn.clicked.connect(self.add_bist30)
        bist30_btn.setStyleSheet("background-color: #2196F3; color: white;")
        
        banks_btn = QPushButton("Bankalar")
        banks_btn.clicked.connect(self.add_banks)
        banks_btn.setStyleSheet("background-color: #2196F3; color: white;")
        
        import_btn = QPushButton("📂 CSV'den İçe Aktar")
        import_btn.clicked.connect(self.import_symbols_from_csv)
        import_btn.setStyleSheet("background-color: #FF9800; color: white;")
        
        quick_layout.addWidget(bist30_btn)
        quick_layout.addWidget(banks_btn)
        quick_layout.addWidget(import_btn)
        
        symbols_layout.addLayout(quick_layout)
        
        symbols_group.setLayout(symbols_layout)
        layout.addWidget(symbols_group, 1)
        
        # Kontrol butonları
        control_group = QGroupBox("🎮 Kontrol")
        control_layout = QVBoxLayout()
        
        self.scan_btn = QPushButton("🚀 Ultimate Taramayı Başlat")
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 12pt;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.scan_btn.clicked.connect(self.start_scan)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar { height: 25px; }")
        
        self.status_label = QLabel("⏳ Beklemede...")
        self.status_label.setStyleSheet(
            "font-size: 11pt; padding: 10px; "
            "background-color: #e8f5e9; border-radius: 4px;"
        )
        
        control_layout.addWidget(self.scan_btn)
        control_layout.addWidget(self.progress_bar)
        control_layout.addWidget(self.status_label)
        control_group.setLayout(control_layout)
        
        layout.addWidget(control_group)
        
        # Log
        log_group = QGroupBox("📋 İşlem Günlüğü")
        log_layout = QVBoxLayout()
        
        self.log_widget = QTextEdit()
        self.log_widget.setMaximumHeight(150)
        self.log_widget.setStyleSheet(
            "font-family: 'Courier New'; font-size: 9pt; "
            "background-color: #f5f5f5;"
        )
        log_layout.addWidget(self.log_widget)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Log handler
        log_handler = QTextEditLogger(self.log_widget)
        log_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)
        
        return widget
    
    def _create_right_panel(self):
        """Sağ panel - Sonuçlar"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Başlık ve istatistikler
        header_layout = QHBoxLayout()
        
        self.results_title = QLabel("📊 Tarama Sonuçları")
        self.results_title.setStyleSheet(
            "font-size: 14pt; font-weight: bold; color: #1976D2;"
        )
        
        self.results_stats = QLabel("Sonuç: 0 hisse")
        self.results_stats.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #4CAF50;"
        )
        
        header_layout.addWidget(self.results_title)
        header_layout.addStretch()
        header_layout.addWidget(self.results_stats)
        
        layout.addLayout(header_layout)
        
        # Tab widget
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabBar::tab {
                background-color: #E1E1E1;
                padding: 10px 15px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #2196F3;
                color: white;
            }
        """)
        
        # Tab 1: Özet tablo
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSortingEnabled(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.itemSelectionChanged.connect(self.on_selection_changed)
        
        summary_layout.addWidget(self.results_table)
        
        # Export butonları
        export_layout = QHBoxLayout()
        
        excel_btn = QPushButton("📊 Excel'e Aktar")
        excel_btn.clicked.connect(self.export_to_excel)
        excel_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        csv_btn = QPushButton("💾 CSV'ye Aktar")
        csv_btn.clicked.connect(self.export_to_csv)
        csv_btn.setStyleSheet("background-color: #2196F3; color: white;")
        
        export_layout.addWidget(excel_btn)
        export_layout.addWidget(csv_btn)
        export_layout.addStretch()
        
        summary_layout.addLayout(export_layout)
        
        tabs.addTab(summary_tab, "📋 Özet Tablo")
        
        # Tab 2: Detaylı analiz
        detail_tab = QWidget()
        detail_layout = QVBoxLayout(detail_tab)
        
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet(
            "font-family: 'Courier New'; font-size: 10pt; "
            "background-color: #f0f8ff;"
        )
        detail_layout.addWidget(self.detail_text)
        
        tabs.addTab(detail_tab, "🔍 Detaylı Analiz")
        
        layout.addWidget(tabs)
        
        return widget
    
    def load_symbols(self):
        """Config'den sembolleri yükle"""
        symbols = self.cfg.get('symbols', [])
        self.symbol_list.clear()
        self.symbol_list.addItems(symbols)
        logging.info(f"✅ {len(symbols)} sembol yüklendi")
    
    def add_symbol(self):
        """Sembol ekle"""
        symbol = self.symbol_input.text().upper().strip()
        if symbol:
            items = self.symbol_list.findItems(symbol, Qt.MatchExactly)
            if not items:
                self.symbol_list.addItem(symbol)
                self.symbol_input.clear()
                logging.info(f"✅ Eklendi: {symbol}")
            else:
                QMessageBox.information(self, "Bilgi", f"{symbol} zaten listede")
    
    def add_bist30(self):
        """BIST30 hisselerini ekle"""
        bist30 = [
            'AKBNK', 'ARCLK', 'ASELS', 'BIMAS', 'EKGYO', 'EREGL', 'FROTO',
            'GARAN', 'HALKB', 'ISCTR', 'KCHOL', 'KOZAA', 'KOZAL', 'KRDMD',
            'MGROS', 'ODAS', 'OYAKC', 'PETKM', 'PGSUS', 'SAHOL', 'SASA',
            'SISE', 'SKBNK', 'TCELL', 'THYAO', 'TKFEN', 'TOASO', 'TTKOM',
            'TUPRS', 'VAKBN', 'YKBNK'
        ]
        
        for symbol in bist30:
            items = self.symbol_list.findItems(symbol, Qt.MatchExactly)
            if not items:
                self.symbol_list.addItem(symbol)
        
        logging.info(f"✅ BIST30 hisseleri eklendi")
    
    def add_banks(self):
        """Banka hisselerini ekle"""
        banks = ['AKBNK', 'GARAN', 'ISCTR', 'HALKB', 'SKBNK', 'VAKBN', 'YKBNK']
        
        for symbol in banks:
            items = self.symbol_list.findItems(symbol, Qt.MatchExactly)
            if not items:
                self.symbol_list.addItem(symbol)
        
        logging.info(f"✅ Banka hisseleri eklendi")
    
    def import_symbols_from_csv(self):
        """CSV'den hisse listesi içe aktar"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Hisse Listesi Seç", "", "CSV Files (*.csv);;All Files (*)"
            )
            
            if file_path:
                df = pd.read_csv(file_path)
                
                # Sembol sütununu bul
                symbol_col = None
                for col in df.columns:
                    if 'symbol' in col.lower() or 'hisse' in col.lower() or 'kod' in col.lower():
                        symbol_col = col
                        break
                
                if symbol_col is None:
                    # İlk sütunu kullan
                    symbol_col = df.columns[0]
                
                symbols = df[symbol_col].astype(str).str.upper().tolist()
                
                # Mevcut listeye ekle
                for symbol in symbols:
                    items = self.symbol_list.findItems(symbol, Qt.MatchExactly)
                    if not items:
                        self.symbol_list.addItem(symbol)
                
                logging.info(f"✅ CSV'den {len(symbols)} hisse içe aktarıldı")
                QMessageBox.information(self, "Başarılı", f"{len(symbols)} hisse içe aktarıldı!")
                
        except Exception as e:
            logging.error(f"CSV import hatası: {e}")
            QMessageBox.critical(self, "Hata", f"CSV import hatası: {e}")
    
    def start_scan(self):
        """Taramayı başlat"""
        if self.symbol_list.count() == 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir hisse ekleyin!")
            return
        
        # Sembolleri al
        symbols = [
            self.symbol_list.item(i).text() 
            for i in range(self.symbol_list.count())
        ]
        
        # Config'i güncelle
        self.cfg['use_multi_timeframe'] = self.use_mtf_cb.isChecked()
        self.cfg['use_fibonacci'] = self.use_fib_cb.isChecked()
        self.cfg['use_consolidation'] = self.use_cons_cb.isChecked()
        
        # UI'yi hazırla
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("⏳ Tarama Sürüyor...")
        self.progress_bar.setValue(0)
        self.results_table.setRowCount(0)
        self.detail_text.clear()
        
        # Worker başlat
        self.scan_thread = QThread()
        self.scan_worker = UltimateScanWorker(self.hunter, symbols)
        self.scan_worker.moveToThread(self.scan_thread)
        
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.finished.connect(self.scan_worker.deleteLater)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        
        self.scan_worker.progress.connect(self.update_progress)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.error.connect(self.scan_error)
        
        self.scan_thread.start()
        
        logging.info(f"🚀 Ultimate tarama başladı: {len(symbols)} sembol")
    
    def update_progress(self, percent, message):
        """İlerleme güncelle"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
    
    def scan_finished(self, results):
        """Tarama tamamlandı"""
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("🚀 Ultimate Taramayı Başlat")
        self.progress_bar.setValue(100)
        self.status_label.setText("✅ Tarama tamamlandı!")
        
        self.current_results = results.get('Swing Uygun', [])
        
        if self.current_results:
            self.populate_table(self.current_results)
            
            msg = f"🎉 {len(self.current_results)} adet uygun hisse bulundu!\n\n"
            msg += "✨ Gelişmiş özellikler aktif:\n"
            if self.use_mtf_cb.isChecked():
                msg += "  📊 Multi-Timeframe analiz\n"
            if self.use_fib_cb.isChecked():
                msg += "  🌀 Fibonacci analiz\n"
            if self.use_cons_cb.isChecked():
                msg += "  📦 Konsolidasyon tespiti\n"
            
            QMessageBox.information(self, "Başarılı", msg)
        else:
            QMessageBox.warning(
                self, "Sonuç Yok",
                "Kriterlere uyan hisse bulunamadı.\n\n"
                "💡 İpucu: Filtreleri gevşetmeyi deneyin."
            )
    
    def scan_error(self, error_msg):
        """Tarama hatası"""
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("🚀 Ultimate Taramayı Başlat")
        self.status_label.setText("❌ Hata oluştu!")
        
        logging.error(f"Tarama hatası: {error_msg}")
        QMessageBox.critical(self, "Hata", f"Tarama sırasında hata:\n\n{error_msg}")
    
    def populate_table(self, results):
        """Tabloyu doldur"""
        if not results:
            return
        
        headers = list(results[0].keys())
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        self.results_table.setRowCount(len(results))
        
        for row_idx, row_data in enumerate(results):
            for col_idx, key in enumerate(headers):
                value = str(row_data[key])
                item = QTableWidgetItem(value)
                
                # Renklendirme
                if key == 'Skor':
                    try:
                        score_val = float(value.split('/')[0])
                        if score_val >= 80:
                            item.setBackground(QColor(144, 238, 144))
                            item.setForeground(QColor(0, 100, 0))
                        elif score_val >= 70:
                            item.setBackground(QColor(255, 255, 153))
                    except:
                        pass
                
                elif key == 'MTF Uyum':
                    if value == '✅':
                        item.setBackground(QColor(198, 239, 206))
                
                elif key == 'MTF Öneri':
                    if 'Strong Buy' in value:
                        item.setBackground(QColor(0, 176, 80))
                        item.setForeground(QColor(255, 255, 255))
                    elif 'Buy' in value:
                        item.setBackground(QColor(146, 208, 80))
                
                self.results_table.setItem(row_idx, col_idx, item)
        
        self.results_table.resizeColumnsToContents()
        self.results_stats.setText(f"Sonuç: {len(results)} hisse")
    
    def on_selection_changed(self):
        """Tablo seçimi değişti - detay göster"""
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        if row < len(self.current_results):
            result = self.current_results[row]
            self.show_detail(result)
    
    def show_detail(self, result):
        """Detaylı analiz göster"""
        detail = f"""
{'='*70}
📊 DETAYLI ANALİZ: {result['Hisse']}
{'='*70}

🎯 GENEL BİLGİLER:
   Sinyal Gücü: {result['Sinyal']}
   Toplam Skor: {result['Skor']}
   Güncel Fiyat: {result['Fiyat']} TL

💰 GİRİŞ VE RİSK YÖNETİMİ:
   Giriş Aralığı: {result['Giriş (Min-Max)']}
   Optimal Giriş: {result['Optimal Giriş']} TL
   Stop Loss: {result['Stop Loss']} TL
   Hedef 1 (2R): {result['Hedef 1']} TL
   Hedef 2: {result['Hedef 2']} TL
   Risk/Reward: {result['R/R']}
   Risk Yüzdesi: {result['Risk %']}%

📈 MULTI-TIMEFRAME ANALİZ:
   Günlük Trend: {result['Günlük Trend']}
   Haftalık Trend: {result['Haftalık Trend']}
   Trend Uyumu: {result['MTF Uyum']}
   Öneri: {result['MTF Öneri']}

🌀 FIBONACCI ANALİZİ:
   {result['Fibonacci']}

📦 KONSOLİDASYON:
   {result['Konsolidasyon']}

💡 İŞLEM ÖNERİSİ:
   1. {result['Optimal Giriş']} TL seviyesinden giriş yap
   2. Stop loss'u {result['Stop Loss']} TL'ye koy
   3. İlk hedef {result['Hedef 1']} TL'de %50 pozisyon kapat
   4. İkinci hedef {result['Hedef 2']} TL'de %30 pozisyon kapat
   5. Kalan %20'yi trailing stop ile takip et

{'='*70}
        """
        
        self.detail_text.setPlainText(detail.strip())
    
    def export_to_excel(self):
        """Excel'e aktar"""
        if not self.current_results:
            QMessageBox.warning(self, "Uyarı", "Aktarılacak veri yok!")
            return
        
        try:
            results_dict = {'Swing Uygun': self.current_results}
            filename = self.hunter.save_to_excel(results_dict)
            
            if filename:
                QMessageBox.information(
                    self, "Başarılı",
                    f"Excel raporu oluşturuldu:\n\n{filename}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel hatası:\n{e}")
    
    def export_to_csv(self):
        """CSV'ye aktar"""
        if not self.current_results:
            QMessageBox.warning(self, "Uyarı", "Aktarılacak veri yok!")
            return
        
        try:
            filename = f"Swing_Ultimate_Raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df = pd.DataFrame(self.current_results)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            QMessageBox.information(
                self, "Başarılı",
                f"CSV raporu oluşturuldu:\n\n{filename}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"CSV hatası:\n{e}")


# ============================================================================
# Yardımcı Sınıflar
# ============================================================================

class QTextEditLogger(logging.Handler):
    """QTextEdit log handler"""
    def __init__(self, parent):
        super().__init__()
        self.widget = parent
        self.widget.setReadOnly(True)
    
    def emit(self, record):
        msg = self.format(record)
        self.widget.append(msg)
        self.widget.verticalScrollBar().setValue(
            self.widget.verticalScrollBar().maximum()
        )


# ============================================================================
# Main
# ============================================================================

def main():
    """Ana fonksiyon"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    try:
        gui = SwingGUIUltimate()
        gui.show()
        sys.exit(app.exec_())
    except Exception as e:
        logging.critical(f"GUI başlatma hatası: {e}")
        QMessageBox.critical(None, "Kritik Hata", f"Program başlatılamadı:\n{e}")
        sys.exit(1)


if __name__ == '__main__':
    main()