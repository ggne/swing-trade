"""
Swing Hunter Advanced GUI - Alternatif Gelişmiş Arayüz
Multi-timeframe, Fibonacci ve Konsolidasyon entegreli
"""

import sys, json, os, logging, traceback
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QDoubleSpinBox, QCheckBox, QPushButton,
                             QMessageBox, QScrollArea, QGroupBox, QProgressBar,
                             QTableWidget, QTableWidgetItem, QTextEdit, QLineEdit, 
                             QListWidget, QAbstractItemView, QSpinBox, QTabWidget,
                             QHeaderView, QComboBox, QSplitter, QFrame, QFileDialog)
from PyQt5.QtCore import QObject, QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QColor, QPixmap, QFont
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import shutil

# Core modülleri import et
try:
    from swing_analyzer_ultimate import SwingHunterUltimate, AdvancedSignal
    from parallel_scanner import FastSwingHunter
    from smart_filter_system import SmartFilterSystem, MarketRegime
    from improved_backtest import RealisticBacktester
    from swing_chart_advanced import SwingChart
except ImportError:
    # Relative import fallback
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'CORE_ANALYZERS'))
    from swing_analyzer_ultimate import SwingHunterUltimate, AdvancedSignal
    from parallel_scanner import FastSwingHunter
    from smart_filter_system import SmartFilterSystem, MarketRegime
    from improved_backtest import RealisticBacktester
    from swing_chart_advanced import SwingChart

from tvDatafeed import TvDatafeed, Interval

# GUI loglarını yakalamak için handler
class QTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = parent
        self.widget.setReadOnly(True)
    
    def emit(self, record):
        msg = self.format(record)
        self.widget.append(msg)
        self.widget.verticalScrollBar().setValue(self.widget.verticalScrollBar().maximum())

# Arka plan işlemler için Worker sınıfları
class ScanWorker(QObject):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str)
    
    def __init__(self, hunter, symbols, use_fast_scan=True):
        super().__init__()
        self.hunter = hunter
        self.symbols = symbols
        self.use_fast_scan = use_fast_scan
    
    def run(self):
        try:
            if self.use_fast_scan and len(self.symbols) > 5:
                fast_hunter = FastSwingHunter(self.hunter)
                results = fast_hunter.run_scan_fast(
                    self.symbols, 
                    progress_callback=self.progress.emit,
                    use_batches=len(self.symbols) > 30
                )
            else:
                results = self.hunter.run_advanced_scan(self.symbols, self.progress.emit)
            
            excel_file = self.hunter.save_to_excel(results)
            output = {
                'results': results,
                'excel_file': excel_file
            }
            
            self.finished.emit(output)
        except Exception as e:
            self.error.emit(str(e))

class BacktestWorker(QObject):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str)
    
    def __init__(self, hunter, symbols, backtest_config):
        super().__init__()
        self.hunter = hunter
        self.symbols = symbols
        self.backtest_config = backtest_config
        self.is_running = True
    
    def stop(self):
        self.is_running = False
    
    def run(self):
        try:
            results = []
            total_symbols = len(self.symbols)
            
            for idx, symbol in enumerate(self.symbols):
                if not self.is_running:
                    break
                    
                progress = int((idx / total_symbols) * 100)
                self.progress.emit(progress, f"{symbol} backtest ediliyor...")
                
                try:
                    data = self.hunter.safe_api_call(
                        self.hunter.tv.get_hist,
                        symbol=symbol,
                        exchange=self.hunter.cfg.get('exchange', 'BIST'),
                        interval=Interval.in_daily,
                        n_bars=300
                    )
                    
                    if data is not None and len(data) > 100:
                        backtester = RealisticBacktester(self.hunter.cfg)
                        result = backtester.run_backtest(symbol, data, self.hunter)
                        
                        if result and result['metrics']['total_trades'] > 0:
                            results.append(result)
                            
                except Exception as e:
                    logging.error(f"Backtest hatası {symbol}: {e}")
                    continue
            
            if self.is_running:
                summary = self.calculate_summary_metrics(results)
                self.finished.emit({
                    'detailed_results': results,
                    'summary': summary
                })
                
        except Exception as e:
            if self.is_running:
                self.error.emit(str(e))

    def calculate_summary_metrics(self, results):
        if not results:
            return {}
        
        total_trades = sum(r['metrics']['total_trades'] for r in results)
        winning_trades = sum(r['metrics']['winning_trades'] for r in results)
        total_profit = sum(r['metrics']['total_profit'] for r in results)
        total_return = sum(r['metrics']['total_return_pct'] for r in results)
        
        return {
            'total_symbols': len(results),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': (winning_trades / total_trades) * 100 if total_trades > 0 else 0,
            'total_profit': total_profit,
            'avg_return_per_symbol': total_return / len(results) if results else 0,
            'avg_trades_per_symbol': total_trades / len(results) if results else 0
        }

class MarketAnalysisWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, hunter):
        super().__init__()
        self.hunter = hunter
        self.smart_filter = SmartFilterSystem(hunter.cfg)
    
    def run(self):
        try:
            market_data = self.hunter.tv.get_hist('XU100', 'BIST', Interval.in_daily, 100)
            
            if market_data is None:
                self.error.emit("Piyasa verisi alınamadı")
                return
            
            regime = self.smart_filter.detect_market_regime(market_data)
            adjustments = self.smart_filter.adjust_filters_for_regime(regime)
            
            market_analysis = self.analyze_market(market_data)
            
            self.finished.emit({
                'regime': regime.value,
                'adjustments': adjustments,
                'market_analysis': market_analysis
            })
            
        except Exception as e:
            self.error.emit(str(e))
    
    def analyze_market(self, market_data):
        try:
            df = market_data.copy()
            df['returns'] = df['close'].pct_change()
            
            analysis = {
                'current_price': df['close'].iloc[-1],
                'daily_change_pct': df['returns'].iloc[-1] * 100,
                'volatility_30d': df['returns'].std() * np.sqrt(252) * 100,
                'trend_20d': (df['close'].iloc[-1] / df['close'].iloc[-20] - 1) * 100,
                'volume_trend': (df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1])
            }
            
            return analysis
            
        except Exception as e:
            logging.error(f"Piyasa analiz hatası: {e}")
            return {}

# Ana GUI Sınıfı
class SwingGUIAdvanced(QWidget):
    def __init__(self):
        super().__init__()
        self.hunter = SwingHunterUltimate()
        self.cfg = self.hunter.cfg
        self.tv = TvDatafeed()
        self.current_chart_image = None
        self.backtest_results = None
        self.market_analysis = None
        self.fast_scanner = FastSwingHunter(self.hunter)
        self.smart_filter = SmartFilterSystem(self.cfg)
        
        self.init_ui()
        self.load_settings()
        self.start_market_analysis()
    
    def init_ui(self):
        """UI'yi başlat"""
        self.setWindowTitle("🎯 Swing Hunter Advanced - Multi-Timeframe + Fibonacci + Konsolidasyon")
        self.setGeometry(50, 50, 1800, 1000)
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #2E7D32;
            }
            QPushButton {
                padding: 8px 12px;
                font-weight: bold;
                border-radius: 6px;
                border: 1px solid #ccc;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QTableWidget {
                gridline-color: #d0d0d0;
                font-size: 10pt;
                border: 1px solid #ddd;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        
        main_layout = QHBoxLayout(self)
        
        # Splitter ile bölünmüş arayüz
        splitter = QSplitter(Qt.Horizontal)
        
        # --- SOL PANEL (Ayarlar) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Tab Widget
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #C2C7CB;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #E1E1E1;
                border: 1px solid #C4C4C3;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
                color: white;
            }
        """)
        
        # Tab 1: Hisseler
        tab1 = self.create_symbols_tab()
        tabs.addTab(tab1, "🎯 Hisseler")
        
        # Tab 2: Teknik Kriterler
        tab2 = self.create_technical_tab()
        tabs.addTab(tab2, "📊 Teknik")
        
        # Tab 3: Gelişmiş Özellikler
        tab3 = self.create_advanced_features_tab()
        tabs.addTab(tab3, "⚡ Gelişmiş")
        
        # Tab 4: Backtest
        tab4 = self.create_backtest_tab()
        tabs.addTab(tab4, "🎯 Backtest")
        
        left_layout.addWidget(tabs)
        
        # Kontrol Paneli
        control_group = QGroupBox("🎮 Kontrol Paneli")
        control_layout = QVBoxLayout()
        
        # Tarama seçenekleri
        scan_options_layout = QHBoxLayout()
        self.fast_scan_cb = QCheckBox("🚀 Hızlı Tarama (Paralel)")
        self.fast_scan_cb.setChecked(True)
        scan_options_layout.addWidget(self.fast_scan_cb)
        
        self.smart_filter_cb = QCheckBox("🧠 Akıllı Filtre")
        self.smart_filter_cb.setChecked(True)
        scan_options_layout.addWidget(self.smart_filter_cb)
        scan_options_layout.addStretch()
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("▶️ Ultimate Taramayı Başlat")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; 
                color: white; 
                font-size: 12pt;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.run_btn.clicked.connect(self.start_scan)
        
        self.backtest_btn = QPushButton("🎯 Backtest Başlat")
        self.backtest_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; 
                color: white;
                padding: 10px;
            }
        """)
        self.backtest_btn.clicked.connect(self.start_backtest)
        
        button_layout.addWidget(self.run_btn)
        button_layout.addWidget(self.backtest_btn)
        
        # İlerleme çubuğu
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar { height: 20px; }")
        
        self.status_label = QLabel("⏳ Beklemede...")
        self.status_label.setStyleSheet("font-size: 11pt; padding: 8px; background-color: #e8f5e8; border-radius: 4px;")
        
        control_layout.addLayout(scan_options_layout)
        control_layout.addLayout(button_layout)
        control_layout.addWidget(self.progress_bar)
        control_layout.addWidget(self.status_label)
        control_group.setLayout(control_layout)
        
        left_layout.addWidget(control_group)
        
        # Log Penceresi
        log_group = QGroupBox("📝 İşlem Günlüğü")
        log_layout = QVBoxLayout()
        self.log_widget = QTextEdit()
        self.log_widget.setMaximumHeight(150)
        self.log_widget.setStyleSheet("font-family: 'Courier New'; font-size: 9pt; background-color: #f5f5f5;")
        log_layout.addWidget(self.log_widget)
        log_group.setLayout(log_layout)
        
        left_layout.addWidget(log_group)
        
        # --- SAĞ PANEL (Grafik ve Sonuçlar) ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # ÜST: Piyasa Durumu ve Grafik
        top_splitter = QSplitter(Qt.Horizontal)
        
        # Piyasa Durumu
        market_widget = QWidget()
        market_layout = QVBoxLayout(market_widget)
        
        market_group = QGroupBox("📈 Piyasa Durumu")
        market_inner_layout = QVBoxLayout()
        
        self.market_status_label = QLabel("Piyasa analiz ediliyor...")
        self.market_status_label.setStyleSheet("font-size: 10pt; padding: 5px;")
        self.market_status_label.setWordWrap(True)
        
        self.regime_label = QLabel()
        self.regime_label.setStyleSheet("font-size: 11pt; font-weight: bold; padding: 5px;")
        
        market_inner_layout.addWidget(self.market_status_label)
        market_inner_layout.addWidget(self.regime_label)
        market_group.setLayout(market_inner_layout)
        
        market_layout.addWidget(market_group)
        market_layout.addStretch()
        
        # Grafik Alanı
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        
        chart_group = QGroupBox("📊 Hisse Grafiği")
        chart_inner_layout = QVBoxLayout()
        
        self.chart_title = QLabel("Hisse seçin veya tarama yapın...")
        self.chart_title.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 8px; background-color: #e3f2fd; border-radius: 4px;")
        self.chart_title.setAlignment(Qt.AlignCenter)
        
        self.chart_label = QLabel()
        self.chart_label.setAlignment(Qt.AlignCenter)
        self.chart_label.setStyleSheet("""
            QLabel {
                border: 2px solid #cccccc;
                border-radius: 8px;
                background-color: #f9f9f9;
                min-height: 300px;
            }
        """)
        self.chart_label.setText("Grafik burada görünecek\n\nListeden hisse seçin veya tarama yapın")
        self.chart_label.setWordWrap(True)
        
        chart_inner_layout.addWidget(self.chart_title)
        chart_inner_layout.addWidget(self.chart_label, 1)
        chart_group.setLayout(chart_inner_layout)
        
        chart_layout.addWidget(chart_group)
        
        top_splitter.addWidget(market_widget)
        top_splitter.addWidget(chart_widget)
        top_splitter.setSizes([300, 700])
        
        # ALT: Sonuç Tablosu
        results_group = QGroupBox("📋 Ultimate Tarama Sonuçları")
        results_layout = QVBoxLayout(results_group)
        
        # Sonuç istatistikleri
        stats_layout = QHBoxLayout()
        self.results_stats_label = QLabel("Sonuçlar: 0 hisse")
        self.results_stats_label.setStyleSheet("font-weight: bold; color: #2E7D32;")
        stats_layout.addWidget(self.results_stats_label)
        stats_layout.addStretch()
        
        # Export butonları
        self.export_excel_btn = QPushButton("📊 Excel'e Aktar")
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        self.export_excel_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        self.export_csv_btn = QPushButton("💾 CSV'ye Aktar")
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        self.export_csv_btn.setStyleSheet("background-color: #2196F3; color: white;")
        
        stats_layout.addWidget(self.export_excel_btn)
        stats_layout.addWidget(self.export_csv_btn)
        
        results_layout.addLayout(stats_layout)
        
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.itemSelectionChanged.connect(self.on_table_selection_changed)
        self.results_table.setSortingEnabled(True)
        
        results_layout.addWidget(self.results_table)
        
        right_layout.addWidget(top_splitter, 2)
        right_layout.addWidget(results_group, 3)
        
        # Splitter'a widget'ları ekle
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([800, 1000])
        
        main_layout.addWidget(splitter)
        
        # Log handler'ı ayarla
        log_handler = QTextEditLogger(self.log_widget)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)
        
        # Timer for auto-save
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_settings)
        self.auto_save_timer.start(30000)  # 30 saniyede bir
    
    def create_symbols_tab(self):
        """Hisseler sekmesi"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Hisse Senedi Yönetimi
        symbol_group = QGroupBox("📊 Taranacak Hisseler")
        symbol_layout = QVBoxLayout()
        
        self.symbol_list_widget = QListWidget()
        self.symbol_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.symbol_list_widget.itemClicked.connect(self.show_selected_chart)
        
        # Hisse ekleme bölümü
        symbol_input_layout = QHBoxLayout()
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Hisse kodu girin (Örn: GARAN) ve Enter'a basın")
        self.symbol_input.returnPressed.connect(self.add_symbol)
        
        add_btn = QPushButton("➕ Ekle")
        add_btn.clicked.connect(self.add_symbol)
        add_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        symbol_input_layout.addWidget(self.symbol_input)
        symbol_input_layout.addWidget(add_btn)
        
        # Hisse yönetim butonları
        symbol_manage_layout = QHBoxLayout()
        
        remove_btn = QPushButton("🗑️ Seçileni Sil")
        remove_btn.clicked.connect(self.remove_symbol)
        remove_btn.setStyleSheet("background-color: #f44336; color: white;")
        
        clear_all_btn = QPushButton("🧹 Tümünü Temizle")
        clear_all_btn.clicked.connect(self.clear_all_symbols)
        clear_all_btn.setStyleSheet("background-color: #FF9800; color: white;")
        
        symbol_manage_layout.addWidget(remove_btn)
        symbol_manage_layout.addWidget(clear_all_btn)
        symbol_manage_layout.addStretch()
        
        # Hızlı hisse ekleme
        quick_add_group = QGroupBox("⚡ Hızlı Ekle")
        quick_add_layout = QVBoxLayout()
        
        quick_buttons_layout = QHBoxLayout()
        
        bist30_btn = QPushButton("BIST30")
        bist30_btn.clicked.connect(self.quick_add_bist30)
        bist30_btn.setStyleSheet("background-color: #2196F3; color: white;")
        
        bank_btn = QPushButton("Bankalar")
        bank_btn.clicked.connect(self.quick_add_banks)
        bank_btn.setStyleSheet("background-color: #2196F3; color: white;")
        
        import_btn = QPushButton("📂 CSV'den İçe Aktar")
        import_btn.clicked.connect(self.import_symbols_from_csv)
        import_btn.setStyleSheet("background-color: #FF9800; color: white;")
        
        quick_buttons_layout.addWidget(bist30_btn)
        quick_buttons_layout.addWidget(bank_btn)
        quick_buttons_layout.addWidget(import_btn)
        
        quick_add_layout.addLayout(quick_buttons_layout)
        quick_add_group.setLayout(quick_add_layout)
        
        symbol_layout.addWidget(self.symbol_list_widget, 1)
        symbol_layout.addLayout(symbol_input_layout)
        symbol_layout.addLayout(symbol_manage_layout)
        symbol_layout.addWidget(quick_add_group)
        symbol_group.setLayout(symbol_layout)
        
        layout.addWidget(symbol_group)
        
        # Genel Ayarlar
        general_group = QGroupBox("⚙️ Genel Ayarlar")
        general_layout = QVBoxLayout()
        
        # Borsa seçimi
        exchange_layout = QHBoxLayout()
        exchange_layout.addWidget(QLabel("Borsa:"))
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["BIST", "NASDAQ", "NYSE"])
        exchange_layout.addWidget(self.exchange_combo)
        exchange_layout.addStretch()
        
        # Veri aralığı
        lookback_layout = QHBoxLayout()
        lookback_layout.addWidget(QLabel("Veri Aralığı (Gün):"))
        self.lookback_spin = QSpinBox()
        self.lookback_spin.setRange(50, 500)
        self.lookback_spin.setValue(250)
        self.lookback_spin.setSuffix(" gün")
        lookback_layout.addWidget(self.lookback_spin)
        lookback_layout.addStretch()
        
        general_layout.addLayout(exchange_layout)
        general_layout.addLayout(lookback_layout)
        general_group.setLayout(general_layout)
        
        layout.addWidget(general_group)
        layout.addStretch()
        
        return tab

    def create_technical_tab(self):
        """Teknik kriterler sekmesi"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Sayısal Kriterler
        numeric_group = QGroupBox("📈 Teknik İndikatör Kriterleri")
        numeric_layout = QVBoxLayout()
        
        self.spin_widgets = {}
        
        numeric_settings = [
            ("Min RSI", "min_rsi", 0, 100, 1, 30),
            ("Max RSI", "max_rsi", 0, 100, 1, 70),
            ("Min Göreceli Hacim", "min_relative_volume", 0.1, 10.0, 0.1, 1.0),
            ("Max Günlük Değişim %", "max_daily_change_pct", 0, 20.0, 0.5, 8.0),
            ("Min Trend Skoru", "min_trend_score", 0, 100, 5, 50),
        ]
        
        for label, key, min_val, max_val, step, default in numeric_settings:
            row_layout = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(200)
            spin = QDoubleSpinBox()
            spin.setRange(min_val, max_val)
            spin.setSingleStep(step)
            spin.setValue(default)
            spin.setMinimumWidth(100)
            
            row_layout.addWidget(lbl)
            row_layout.addWidget(spin)
            row_layout.addStretch()
            
            numeric_layout.addLayout(row_layout)
            self.spin_widgets[key] = spin
        
        numeric_group.setLayout(numeric_layout)
        layout.addWidget(numeric_group)
        
        # Checkbox Kriterler
        check_group = QGroupBox("✅ Aktif/Pasif Kriterler")
        check_layout = QVBoxLayout()
        
        self.check_widgets = {}
        
        check_settings = [
            ("🔵 Fiyat EMA20 Üstünde", "price_above_ema20"),
            ("🟠 Fiyat EMA50 Üstünde", "price_above_ema50"),
            ("📈 MACD Pozitif", "macd_positive"),
            ("💪 ADX Kontrolü", "check_adx"),
            ("🛑 ATR Stop Kullan", "use_atr_stop"),
        ]
        
        for label, key in check_settings:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet("QCheckBox { font-size: 11pt; padding: 8px; }")
            check_layout.addWidget(cb)
            self.check_widgets[key] = cb
        
        check_group.setLayout(check_layout)
        layout.addWidget(check_group)
        
        scroll.setWidget(container)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        
        return tab

    def create_advanced_features_tab(self):
        """Gelişmiş özellikler sekmesi"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Gelişmiş Özellikler
        features_group = QGroupBox("🚀 Gelişmiş Özellikler")
        features_layout = QVBoxLayout()
        
        self.advanced_checkboxes = {}
        
        advanced_features = [
            ("📊 Multi-Timeframe Analiz", "use_multi_timeframe", "Günlük + Haftalık trend analizi"),
            ("🌀 Fibonacci Retracement", "use_fibonacci", "Fibonacci destek/direnç seviyeleri"),
            ("📦 Konsolidasyon Tespiti", "use_consolidation", "Konsolidasyon ve breakout pattern'leri"),
            ("🎯 Akıllı Risk/Reward", "use_atr_stop", "ATR bazlı stop loss hesaplama"),
        ]
        
        for label, key, description in advanced_features:
            feature_layout = QHBoxLayout()
            
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet("QCheckBox { font-size: 11pt; }")
            
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #666; font-size: 9pt;")
            desc_label.setWordWrap(True)
            
            feature_layout.addWidget(cb)
            feature_layout.addWidget(desc_label)
            feature_layout.addStretch()
            
            features_layout.addLayout(feature_layout)
            self.advanced_checkboxes[key] = cb
        
        features_group.setLayout(features_layout)
        layout.addWidget(features_group)
        
        # Risk Yönetimi
        risk_group = QGroupBox("🛡️ Risk Yönetimi")
        risk_layout = QVBoxLayout()
        
        risk_settings = [
            ("Min Risk/Ödül Oranı", "min_risk_reward_ratio", 1.0, 5.0, 0.5, 2.0),
            ("Max Risk %", "max_risk_pct", 1.0, 10.0, 0.5, 5.0),
            ("ATR Stop Çarpanı", "atr_stop_multiplier", 1.0, 5.0, 0.5, 2.0),
        ]
        
        self.risk_spin_widgets = {}
        
        for label, key, min_val, max_val, step, default in risk_settings:
            row_layout = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(180)
            spin = QDoubleSpinBox()
            spin.setRange(min_val, max_val)
            spin.setSingleStep(step)
            spin.setValue(default)
            spin.setMinimumWidth(100)
            
            row_layout.addWidget(lbl)
            row_layout.addWidget(spin)
            row_layout.addStretch()
            
            risk_layout.addLayout(row_layout)
            self.risk_spin_widgets[key] = spin
        
        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group)
        
        layout.addStretch()
        
        return tab

    def create_backtest_tab(self):
        """Backtest sekmesi"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Backtest Ayarları
        settings_group = QGroupBox("⚙️ Backtest Ayarları")
        settings_layout = QVBoxLayout()
        
        # Test periyodu
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Test Periyodu (gün):"))
        self.backtest_days = QSpinBox()
        self.backtest_days.setRange(30, 730)
        self.backtest_days.setValue(365)
        period_layout.addWidget(self.backtest_days)
        period_layout.addStretch()
        
        # Başlangıç sermayesi
        capital_layout = QHBoxLayout()
        capital_layout.addWidget(QLabel("Başlangıç Sermayesi:"))
        self.initial_capital = QDoubleSpinBox()
        self.initial_capital.setRange(1000, 1000000)
        self.initial_capital.setValue(10000)
        self.initial_capital.setSuffix(" TL")
        capital_layout.addWidget(self.initial_capital)
        capital_layout.addStretch()
        
        # Komisyon oranı
        commission_layout = QHBoxLayout()
        commission_layout.addWidget(QLabel("Komisyon Oranı (%):"))
        self.commission_rate = QDoubleSpinBox()
        self.commission_rate.setRange(0.0, 1.0)
        self.commission_rate.setValue(0.2)
        self.commission_rate.setSuffix(" %")
        commission_layout.addWidget(self.commission_rate)
        commission_layout.addStretch()
        
        settings_layout.addLayout(period_layout)
        settings_layout.addLayout(capital_layout)
        settings_layout.addLayout(commission_layout)
        settings_group.setLayout(settings_layout)
        
        layout.addWidget(settings_group)
        
        # Backtest Sonuçları
        results_group = QGroupBox("📊 Backtest Sonuçları")
        results_layout = QVBoxLayout(results_group)
        
        self.backtest_results_text = QTextEdit()
        self.backtest_results_text.setReadOnly(True)
        self.backtest_results_text.setStyleSheet("font-family: 'Courier New'; font-size: 9pt; background-color: #f5f5f5;")
        results_layout.addWidget(self.backtest_results_text)
        
        layout.addWidget(results_group)
        
        return tab

    def quick_add_bist30(self):
        """BIST30 hisselerini ekle"""
        bist30_symbols = [
            'AKBNK', 'ARCLK', 'ASELS', 'BIMAS', 'EKGYO', 'EREGL', 'FROTO',
            'GARAN', 'HALKB', 'ISCTR', 'KCHOL', 'KOZAA', 'KOZAL', 'KRDMD',
            'MGROS', 'ODAS', 'OYAKC', 'PETKM', 'PGSUS', 'SAHOL', 'SASA',
            'SISE', 'SKBNK', 'TCELL', 'THYAO', 'TKFEN', 'TOASO', 'TTKOM',
            'TUPRS', 'VAKBN', 'YKBNK'
        ]
        self.add_symbols_to_list(bist30_symbols)

    def quick_add_banks(self):
        """Banka hisselerini ekle"""
        bank_symbols = [
            'AKBNK', 'GARAN', 'ISCTR', 'HALKB', 'ICBCT', 'SKBNK', 'TSKB',
            'VAKBN', 'YKBNK', 'ALBRK', 'QNBFS', 'TNBNK'
        ]
        self.add_symbols_to_list(bank_symbols)

    def add_symbols_to_list(self, symbols):
        """Listeye sembol ekle (tekrarı önle)"""
        for symbol in symbols:
            items = self.symbol_list_widget.findItems(symbol, Qt.MatchExactly)
            if not items:
                self.symbol_list_widget.addItem(symbol)
        logging.info(f"✅ {len(symbols)} hisse eklendi")

    def add_symbol(self):
        """Hisse ekle"""
        symbol = self.symbol_input.text().upper().strip()
        if symbol:
            items = self.symbol_list_widget.findItems(symbol, Qt.MatchExactly)
            if not items:
                self.symbol_list_widget.addItem(symbol)
                self.symbol_input.clear()
                logging.info(f"✅ Hisse eklendi: {symbol}")
            else:
                QMessageBox.information(self, "Bilgi", f"{symbol} zaten listede!")

    def remove_symbol(self):
        """Seçili hisseyi sil"""
        selected_items = self.symbol_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Lütfen silmek için hisse seçin!")
            return
        
        for item in selected_items:
            self.symbol_list_widget.takeItem(self.symbol_list_widget.row(item))
            logging.info(f"🗑️ Hisse silindi: {item.text()}")

    def clear_all_symbols(self):
        """Tüm hisseleri temizle"""
        reply = QMessageBox.question(self, 'Onay', 'Tüm hisseleri silmek istediğinizden emin misiniz?',
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.symbol_list_widget.clear()
            logging.info("🧹 Tüm hisseler temizlendi")

    def import_symbols_from_csv(self):
        """CSV'den hisse listesi içe aktar"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Hisse Listesi CSV Dosyası Seç", "", "CSV Files (*.csv);;All Files (*)"
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
                
                # Mevcut listeye ekle (tekrarları önle)
                added_count = 0
                for symbol in symbols:
                    items = self.symbol_list_widget.findItems(symbol, Qt.MatchExactly)
                    if not items:
                        self.symbol_list_widget.addItem(symbol)
                        added_count += 1
                
                logging.info(f"✅ CSV'den {added_count} hisse içe aktarıldı")
                QMessageBox.information(self, "Başarılı", f"{added_count} hisse içe aktarıldı!")
                
        except Exception as e:
            logging.error(f"CSV import hatası: {e}")
            QMessageBox.critical(self, "Hata", f"CSV import hatası:\n{e}")

    def load_settings(self):
        """Ayarları yükle"""
        try:
            # Sayısal ayarlar
            for key, spin in self.spin_widgets.items():
                spin.setValue(self.cfg.get(key, spin.value()))
            
            # Risk ayarları
            for key, spin in self.risk_spin_widgets.items():
                spin.setValue(self.cfg.get(key, spin.value()))
            
            # Checkbox ayarları
            for key, cb in self.check_widgets.items():
                cb.setChecked(self.cfg.get(key, True))
            
            # Gelişmiş özellikler
            for key, cb in self.advanced_checkboxes.items():
                cb.setChecked(self.cfg.get(key, True))
            
            # Sembol listesi
            self.symbol_list_widget.clear()
            self.symbol_list_widget.addItems(self.cfg.get('symbols', []))
            
            # Genel ayarlar
            self.exchange_combo.setCurrentText(self.cfg.get('exchange', 'BIST'))
            self.lookback_spin.setValue(self.cfg.get('lookback_bars', 250))
            
            logging.info("✅ Ayarlar başarıyla yüklendi")
            
        except Exception as e:
            logging.error(f"Ayarlar yükleme hatası: {e}")

    def save_settings(self):
        """Ayarları kaydet"""
        try:
            # Sayısal ayarları kaydet
            for key, spin in self.spin_widgets.items():
                self.cfg[key] = spin.value()
            
            # Risk ayarlarını kaydet
            for key, spin in self.risk_spin_widgets.items():
                self.cfg[key] = spin.value()
            
            # Checkbox ayarları kaydet
            for key, cb in self.check_widgets.items():
                self.cfg[key] = cb.isChecked()
            
            # Gelişmiş özellikleri kaydet
            for key, cb in self.advanced_checkboxes.items():
                self.cfg[key] = cb.isChecked()
            
            # Sembol listesini kaydet
            symbols = [self.symbol_list_widget.item(i).text() for i in range(self.symbol_list_widget.count())]
            self.cfg['symbols'] = symbols
            
            # Genel ayarları kaydet
            self.cfg['exchange'] = self.exchange_combo.currentText()
            self.cfg['lookback_bars'] = self.lookback_spin.value()
            
            # Dosyaya kaydet
            with open('swing_config.json', 'w', encoding='utf-8') as f:
                json.dump(self.cfg, f, indent=2, ensure_ascii=False)
            
            logging.info("💾 Ayarlar başarıyla kaydedildi")
            
        except Exception as e:
            logging.error(f"Ayarlar kaydetme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Ayarları kaydederken hata oluştu:\n{e}")

    def auto_save_settings(self):
        """Otomatik ayar kaydetme"""
        self.save_settings()

    def start_scan(self):
        """Taramayı başlat"""
        if self.symbol_list_widget.count() == 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir hisse ekleyin!")
            return
        
        self.save_settings()
        
        symbols = [self.symbol_list_widget.item(i).text() for i in range(self.symbol_list_widget.count())]
        
        # Akıllı filtre ayarlarını uygula
        if self.smart_filter_cb.isChecked() and self.market_analysis:
            try:
                adjustments = self.smart_filter.adjust_filters_for_regime(
                    MarketRegime(self.market_analysis['regime'])
                )
                self.cfg.update(adjustments)
                logging.info(f"🧠 Akıllı filtreler uygulandı: {self.market_analysis['regime']}")
            except Exception as e:
                logging.warning(f"Akıllı filtre uygulama hatası: {e}")
        
        self.run_btn.setEnabled(False)
        self.backtest_btn.setEnabled(False)
        self.run_btn.setText("⏳ Tarama Sürüyor...")
        self.progress_bar.setValue(0)
        self.results_table.clear()
        self.results_table.setRowCount(0)
        
        # Worker thread başlat
        self.scan_thread = QThread()
        self.scan_worker = ScanWorker(
            self.hunter, 
            symbols, 
            use_fast_scan=self.fast_scan_cb.isChecked()
        )
        self.scan_worker.moveToThread(self.scan_thread)
        
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.finished.connect(self.scan_worker.deleteLater)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        
        self.scan_worker.progress.connect(self.update_progress)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.error.connect(self.scan_error)
        
        self.scan_thread.start()
        
        logging.info(f"🔍 Ultimate tarama başlatıldı: {len(symbols)} sembol")

    def update_progress(self, percent, message):
        """İlerleme güncelle"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def scan_finished(self, output):
        """Tarama tamamlandı"""
        self.status_label.setText("✅ Tarama tamamlandı!")
        self.run_btn.setEnabled(True)
        self.backtest_btn.setEnabled(True)
        self.run_btn.setText("▶️ Ultimate Taramayı Başlat")
        self.progress_bar.setValue(100)
        
        results_list = output.get('results', {}).get('Swing Uygun', [])
        
        if results_list:
            self.populate_table(results_list)
            
            # İlk hissenin grafiğini göster
            if results_list:
                first_symbol = results_list[0]['Hisse']
                self.generate_and_show_chart(first_symbol)
            
            # Başarı mesajı
            msg = f"🎉 {len(results_list)} adet uygun hisse bulundu!"
            if output.get('excel_file'):
                msg += f"\n📊 Excel Raporu: {output['excel_file']}"
            
            QMessageBox.information(self, "Başarılı", msg)
            
        else:
            QMessageBox.warning(self, "Sonuç Yok", 
                              "Kriterlere uyan hiçbir hisse senedi bulunamadı.\n\n"
                              "💡 İpucu: Filtreleri gevşetmeyi deneyin.")

    def scan_error(self, error_message):
        """Hata oluştu"""
        self.status_label.setText("❌ Hata oluştu!")
        self.run_btn.setEnabled(True)
        self.backtest_btn.setEnabled(True)
        self.run_btn.setText("▶️ Ultimate Taramayı Başlat")
        
        logging.error(f"Tarama hatası: {error_message}")
        QMessageBox.critical(self, "Kritik Hata", 
                           f"Tarama sırasında bir hata oluştu:\n\n{error_message}")

    def start_backtest(self):
        """Backtest başlat"""
        if self.symbol_list_widget.count() == 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir hisse ekleyin!")
            return
        
        symbols = [self.symbol_list_widget.item(i).text() for i in range(self.symbol_list_widget.count())]
        
        backtest_config = {
            'days': self.backtest_days.value(),
            'initial_capital': self.initial_capital.value(),
            'commission_rate': self.commission_rate.value()
        }
        
        self.run_btn.setEnabled(False)
        self.backtest_btn.setEnabled(False)
        self.backtest_btn.setText("⏳ Backtest Sürüyor...")
        self.progress_bar.setValue(0)
        
        # Backtest worker başlat
        self.backtest_thread = QThread()
        self.backtest_worker = BacktestWorker(self.hunter, symbols, backtest_config)
        self.backtest_worker.moveToThread(self.backtest_thread)
        
        self.backtest_thread.started.connect(self.backtest_worker.run)
        self.backtest_worker.finished.connect(self.backtest_thread.quit)
        self.backtest_worker.finished.connect(self.backtest_worker.deleteLater)
        self.backtest_thread.finished.connect(self.backtest_thread.deleteLater)
        
        self.backtest_worker.progress.connect(self.update_progress)
        self.backtest_worker.finished.connect(self.backtest_finished)
        self.backtest_worker.error.connect(self.backtest_error)
        
        self.backtest_thread.start()
        
        logging.info(f"🎯 Backtest başlatıldı: {len(symbols)} sembol")

    def backtest_finished(self, results):
        """Backtest tamamlandı"""
        self.backtest_results = results
        self.display_backtest_results(results)
        
        self.run_btn.setEnabled(True)
        self.backtest_btn.setEnabled(True)
        self.backtest_btn.setText("🎯 Backtest Başlat")
        self.progress_bar.setValue(100)
        self.status_label.setText("✅ Backtest tamamlandı!")
        
        summary = results['summary']
        QMessageBox.information(self, "Backtest Tamamlandı", 
                              f"Backtest sonuçları hazır!\n\n"
                              f"Test edilen hisse: {summary['total_symbols']}\n"
                              f"Toplam işlem: {summary['total_trades']}\n"
                              f"Başarı oranı: {summary['win_rate']:.1f}%")

    def backtest_error(self, error_message):
        """Backtest hatası"""
        self.run_btn.setEnabled(True)
        self.backtest_btn.setEnabled(True)
        self.backtest_btn.setText("🎯 Backtest Başlat")
        
        logging.error(f"Backtest hatası: {error_message}")
        QMessageBox.critical(self, "Backtest Hatası", 
                           f"Backtest sırasında hata oluştu:\n\n{error_message}")

    def display_backtest_results(self, results):
        """Backtest sonuçlarını göster"""
        summary = results['summary']
        detailed = results['detailed_results']
        
        report = "🎯 BACKTEST SONUÇ RAPORU\n"
        report += "=" * 50 + "\n\n"
        
        report += f"📊 PERFORMANS ÖZETİ:\n"
        report += f"• Test edilen hisse: {summary['total_symbols']}\n"
        report += f"• Toplam işlem: {summary['total_trades']}\n"
        report += f"• Kazanan işlem: {summary['winning_trades']}\n"
        report += f"• Başarı oranı: {summary['win_rate']:.1f}%\n"
        report += f"• Toplam kâr: {summary['total_profit']:,.0f} TL\n"
        report += f"• Hisse başı getiri: {summary['avg_return_per_symbol']:.1f}%\n\n"
        
        report += f"📈 DETAYLI SONUÇLAR:\n"
        report += "-" * 40 + "\n"
        
        for result in detailed[:10]:  # İlk 10 hisseyi göster
            metrics = result['metrics']
            report += f"\n🎯 {result['symbol']}:\n"
            report += f"   • İşlem: {metrics['total_trades']} | Kazanan: {metrics['winning_trades']}\n"
            report += f"   • Başarı: {metrics['win_rate']:.1f}% | Getiri: {metrics['total_return_pct']:.1f}%\n"
            report += f"   • Profit Faktör: {metrics.get('profit_factor', 0):.2f}\n"
        
        if len(detailed) > 10:
            report += f"\n... ve {len(detailed) - 10} hisse daha\n"
        
        self.backtest_results_text.setPlainText(report)

    def start_market_analysis(self):
        """Piyasa analizini başlat"""
        self.status_label.setText("📈 Piyasa analiz ediliyor...")
        
        self.market_thread = QThread()
        self.market_worker = MarketAnalysisWorker(self.hunter)
        self.market_worker.moveToThread(self.market_thread)
        
        self.market_thread.started.connect(self.market_worker.run)
        self.market_worker.finished.connect(self.market_thread.quit)
        self.market_worker.finished.connect(self.market_worker.deleteLater)
        self.market_thread.finished.connect(self.market_thread.deleteLater)
        
        self.market_worker.finished.connect(self.market_analysis_finished)
        self.market_worker.error.connect(self.market_analysis_error)
        
        self.market_thread.start()

    def market_analysis_finished(self, results):
        """Piyasa analizi tamamlandı"""
        self.market_analysis = results
        regime = results['regime']
        adjustments = results['adjustments']
        market_data = results['market_analysis']
        
        # Piyasa durumunu göster
        regime_text = {
            'bull': "🐂 YÜKSELİŞ TRENDİ",
            'bear': "🐻 DÜŞÜŞ TRENDİ", 
            'sideways': "➡️ YATAY TREND",
            'volatile': "⚡ YÜKSEK VOLATİLİTE"
        }.get(regime, "❓ BİLİNMEYEN")
        
        self.regime_label.setText(f"Piyasa Durumu: {regime_text}")
        
        # Piyasa analizini göster
        analysis_text = f"📊 CANLI PİYASA ANALİZİ\n{'='*40}\n\n"
        analysis_text += f"🎯 Piyasa Durumu: {regime_text}\n\n"
        
        if market_data:
            analysis_text += f"• BIST100: {market_data.get('current_price', 0):.0f}\n"
            analysis_text += f"• Günlük Değişim: {market_data.get('daily_change_pct', 0):+.2f}%\n"
            analysis_text += f"• 30 Günlük Volatilite: {market_data.get('volatility_30d', 0):.1f}%\n"
            analysis_text += f"• 20 Günlük Trend: {market_data.get('trend_20d', 0):+.1f}%\n"
        
        analysis_text += f"\n⚙️ OTOMATİK AYARLAR:\n"
        for key, value in adjustments.items():
            analysis_text += f"• {key}: {value}\n"
        
        self.market_status_label.setText(analysis_text)
        
        self.status_label.setText("✅ Piyasa analizi tamamlandı")
        logging.info(f"🧠 Piyasa analizi tamamlandı: {regime}")

    def market_analysis_error(self, error_message):
        """Piyasa analizi hatası"""
        self.status_label.setText("❌ Piyasa analizi hatası")
        logging.error(f"Piyasa analizi hatası: {error_message}")

    def show_selected_chart(self, item):
        """Listeden hisse seçildiğinde grafik göster"""
        symbol = item.text()
        self.generate_and_show_chart(symbol)

    def on_table_selection_changed(self):
        """Tablodan hisse seçildiğinde grafik göster"""
        selected_items = self.results_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            symbol_item = self.results_table.item(row, 0)
            if symbol_item:
                symbol = symbol_item.text()
                self.generate_and_show_chart(symbol)

    def generate_and_show_chart(self, symbol):
        """Grafik oluştur ve göster"""
        try:
            self.status_label.setText(f"📊 {symbol} grafiği yükleniyor...")
            
            data = self.tv.get_hist(
                symbol=symbol, 
                exchange=self.cfg.get('exchange', 'BIST'),
                interval=Interval.in_daily, 
                n_bars=80
            )
            
            if data is not None and len(data) > 20:
                chart = SwingChart(data, symbol)
                success = chart.plot()
                
                if success:
                    pixmap = QPixmap(f"{symbol}_Swing_Chart.png")
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(800, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        self.chart_label.setPixmap(scaled_pixmap)
                        self.chart_title.setText(f"📊 {symbol} - Swing Analiz")
                        self.current_chart_image = f"{symbol}_Swing_Chart.png"
                        logging.info(f"✅ {symbol} grafiği gösterildi")
                else:
                    self.chart_label.setText(f"{symbol} grafiği oluşturulamadı")
            else:
                self.chart_label.setText(f"{symbol} için yeterli veri yok")
                
            self.status_label.setText("✅ Hazır")
            
        except Exception as e:
            error_msg = f"❌ {symbol} grafik hatası: {str(e)}"
            logging.error(error_msg)
            self.chart_label.setText(error_msg)
            self.status_label.setText("❌ Hata")

    def populate_table(self, data):
        """Tabloyu doldur"""
        if not data: 
            self.results_stats_label.setText("Sonuçlar: 0 hisse")
            return
        
        headers = list(data[0].keys())
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        self.results_table.setRowCount(len(data))
        
        for row_idx, row_data in enumerate(data):
            for col_idx, key in enumerate(headers):
                item = QTableWidgetItem(str(row_data[key]))
                
                # Trend skoruna göre renklendirme
                if key == 'Skor':
                    try:
                        score = int(row_data[key].split('/')[0])
                        if score >= 80:
                            item.setBackground(QColor(144, 238, 144))  # Açık yeşil
                        elif score >= 65:
                            item.setBackground(QColor(255, 255, 153))  # Sarı
                        elif score >= 50:
                            item.setBackground(QColor(255, 200, 124))  # Turuncu
                    except:
                        pass
                
                # Sinyal gücüne göre renklendirme
                if key == 'Sinyal':
                    if '🔥🔥' in row_data[key]:
                        item.setBackground(QColor(50, 205, 50))  # Lime green
                        item.setForeground(QColor(255, 255, 255))
                    elif '🔥' in row_data[key]:
                        item.setBackground(QColor(144, 238, 144))  # Light green
                    elif '⚡' in row_data[key]:
                        item.setBackground(QColor(255, 255, 153))  # Light yellow
                
                # MTF Uyum renklendirme
                if key == 'MTF Uyum' and row_data[key] == '✅':
                    item.setBackground(QColor(198, 239, 206))  # Açık yeşil
                
                self.results_table.setItem(row_idx, col_idx, item)
        
        self.results_table.resizeColumnsToContents()
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # İstatistikleri güncelle
        self.results_stats_label.setText(f"Sonuçlar: {len(data)} hisse | En iyi: {data[0]['Hisse']} ({data[0]['Skor']})")

    def export_to_excel(self):
        """Sonuçları Excel'e aktar"""
        try:
            if self.results_table.rowCount() == 0:
                QMessageBox.warning(self, "Uyarı", "Aktarılacak veri yok!")
                return
            
            # Tablo verilerini topla
            data = []
            headers = []
            for col in range(self.results_table.columnCount()):
                headers.append(self.results_table.horizontalHeaderItem(col).text())
            
            for row in range(self.results_table.rowCount()):
                row_data = []
                for col in range(self.results_table.columnCount()):
                    item = self.results_table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            
            # DataFrame oluştur ve Excel'e kaydet
            df = pd.DataFrame(data, columns=headers)
            filename = f"Swing_Advanced_Raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filename, index=False)
            
            logging.info(f"📊 Excel raporu oluşturuldu: {filename}")
            QMessageBox.information(self, "Başarılı", f"Excel raporu oluşturuldu:\n{filename}")
            
        except Exception as e:
            logging.error(f"Excel aktarım hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Excel'e aktarım sırasında hata:\n{e}")

    def export_to_csv(self):
        """Sonuçları CSV'ye aktar"""
        try:
            if self.results_table.rowCount() == 0:
                QMessageBox.warning(self, "Uyarı", "Aktarılacak veri yok!")
                return
            
            # Tablo verilerini topla
            data = []
            headers = []
            for col in range(self.results_table.columnCount()):
                headers.append(self.results_table.horizontalHeaderItem(col).text())
            
            for row in range(self.results_table.rowCount()):
                row_data = []
                for col in range(self.results_table.columnCount()):
                    item = self.results_table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            
            # DataFrame oluştur ve CSV'ye kaydet
            df = pd.DataFrame(data, columns=headers)
            filename = f"Swing_Advanced_Raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            logging.info(f"💾 CSV raporu oluşturuldu: {filename}")
            QMessageBox.information(self, "Başarılı", f"CSV raporu oluşturuldu:\n{filename}")
            
        except Exception as e:
            logging.error(f"CSV aktarım hatası: {e}")
            QMessageBox.critical(self, "Hata", f"CSV'ye aktarım sırasında hata:\n{e}")

    def closeEvent(self, event):
        """Pencere kapatıldığında"""
        # Thread'leri durdur
        if hasattr(self, 'scan_thread') and self.scan_thread.isRunning():
            self.scan_thread.quit()
            self.scan_thread.wait()
        
        if hasattr(self, 'backtest_thread') and self.backtest_thread.isRunning():
            self.backtest_worker.stop()
            self.backtest_thread.quit()
            self.backtest_thread.wait()
        
        # Ayarları kaydet
        self.save_settings()
        
        # Timer'ı durdur
        if hasattr(self, 'auto_save_timer'):
            self.auto_save_timer.stop()
        
        logging.info("👋 Swing Hunter Advanced kapatılıyor...")
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Uygulama stilini ayarla
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f0f0f0;
        }
    """)
    
    try:
        gui = SwingGUIAdvanced()
        gui.show()
        sys.exit(app.exec_())
    except Exception as e:
        logging.critical(f"GUI başlatma hatası: {e}")
        QMessageBox.critical(None, "Kritik Hata", f"Program başlatılamadı:\n{e}")
        sys.exit(1)