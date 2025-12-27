# -*- coding: utf-8 -*-

"""
Swing GUI Advanced Plus - Tüm İyileştirmeler Entegre
Piyasa analizi düzeltildi, backtest geliştirildi
"""
import logging
logger = logging.getLogger(__name__)
import sys, json, os, logging
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QPixmap, QFont
import pandas as pd
import numpy as np
from datetime import datetime
import time

# Import core modules
try:
    from scanner.swing_hunter import SwingHunterUltimate
    from backtest.backtester import RealisticBacktester
except ImportError:
    # Local import
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from scanner.swing_hunter import SwingHunterUltimate


from tvDatafeed import TvDatafeed, Interval
# YENİ: PyQtGraph chart
from gui.chart_widget import SwingTradeChart

# ============================================================================
# Worker Sınıfları
# ============================================================================

class ScanWorker(QObject):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str)
    
    def __init__(self, hunter, symbols):
        super().__init__()
        self.hunter = hunter
        self.symbols = symbols
        self.is_running = True
    
    def stop(self):
        """Worker'ı durdur"""
        self.is_running = False
        self.hunter.stop_scanning()
    
    def run(self):
        try:
            # Piyasa analizini önce yap
            self.progress.emit(10, "📈 Piyasa analizi yapılıyor...")
            market_analysis = self.hunter.analyze_market_condition()
            
            self.progress.emit(20, f"✅ Piyasa: {market_analysis.regime} - Tarama başlıyor...")
            
            results = self.hunter.run_advanced_scan(
                self.symbols,
                progress_callback=self.progress.emit
            )
            
            if self.is_running:
                excel_file = self.hunter.save_to_excel(results)
                output = {
                    'results': results,
                    'excel_file': excel_file,
                    'market_analysis': market_analysis
                }
                self.finished.emit(output)
        except Exception as e:
            if self.is_running:
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
            total_symbols = len(self.symbols)
            
            self.progress.emit(5, "🎯 Backtest başlıyor...")
            
            results = self.hunter.run_backtest(
                self.symbols, 
                days=self.backtest_config['days']
            )
            
            if self.is_running:
                self.progress.emit(100, "✅ Backtest tamamlandı!")
                self.finished.emit(results)
                
        except Exception as e:
            if self.is_running:
                self.error.emit(str(e))

class MarketAnalysisWorker(QObject):
    finished = pyqtSignal(object)  # MarketAnalysis objesi
    error = pyqtSignal(str)
    
    def __init__(self, hunter):
        super().__init__()
        self.hunter = hunter
    
    def run(self):
        try:
            analysis = self.hunter.analyze_market_condition()
            self.finished.emit(analysis)
        except Exception as e:
            self.error.emit(str(e))

# ============================================================================
# Log Handler
# ============================================================================

class QTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = parent
        self.widget.setReadOnly(True)
    
    def emit(self, record):
        msg = self.format(record)
        self.widget.append(msg)
        self.widget.verticalScrollBar().setValue(self.widget.verticalScrollBar().maximum())

# ============================================================================
# Ana GUI Sınıfı
# ============================================================================

class SwingGUIAdvancedPlus(QWidget):
    def __init__(self):
        super().__init__()
        self.hunter = SwingHunterUltimate()
        self.cfg = self.hunter.cfg
        self.tv = TvDatafeed()
        self.current_chart_image = None
        self.backtest_results = None
        self.market_analysis = None
        self.trade_details_text = None
        # Worker referansları
        self.scan_worker = None
        self.scan_thread = None
        self.backtest_worker = None
        self.backtest_thread = None
        self.market_worker = None
        self.market_thread = None
        
        self.init_ui()
        self.load_settings()
        self.start_market_analysis()  # Piyasa analizini otomatik başlat
    
    def init_ui(self):
        """UI başlangıcı"""
        self.setWindowTitle("🎯 Swing Hunter Advanced Plus - Profesyonel Tarama Sistemi")
        self.setGeometry(50, 50, 1800, 1000)
        
        # Modern stil
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
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
                padding: 0 8px;
                color: #2E7D32;
            }
            QPushButton {
                padding: 10px 15px;
                font-weight: bold;
                border-radius: 6px;
                border: 1px solid #ccc;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QTableWidget {
                gridline-color: #d0d0d0;
                border: 1px solid #ddd;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
        """)
        
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        
        # Sol panel
        left_widget = self._create_left_panel()
        
        # Sağ panel  
        right_widget = self._create_right_panel()
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 1300])
        
        main_layout.addWidget(splitter)
    
    def _create_left_panel(self):
        """Sol panel - Ayarlar"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Başlık
        title = QLabel("🚀 Ultimate Scanner Plus")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1976D2; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Tab Widget
        tabs = QTabWidget()
        
        # Tab 1: Hisseler
        tab1 = self._create_symbols_tab()
        tabs.addTab(tab1, "🎯 Hisseler")
        
        # Tab 2: Temel Kriterler
        tab2 = self._create_basic_criteria_tab()
        tabs.addTab(tab2, "📊 Temel")
        
        # Tab 3: Gelişmiş Kriterler
        tab3 = self._create_advanced_criteria_tab()
        tabs.addTab(tab3, "⚡ Gelişmiş")
        
        # Tab 4: Risk Yönetimi
        tab4 = self._create_risk_tab()
        tabs.addTab(tab4, "🛡️ Risk")
        
        layout.addWidget(tabs)
        
        # Kontrol paneli
        control_group = self._create_control_panel()
        layout.addWidget(control_group)
        
        # Log
        log_group = QGroupBox("📋 İşlem Günlüğü")
        log_layout = QVBoxLayout()
        self.log_widget = QTextEdit()
        self.log_widget.setMaximumHeight(120)
        self.log_widget.setStyleSheet("font-family: 'Courier New'; font-size: 9pt; background-color: #f5f5f5;")
        log_layout.addWidget(self.log_widget)
        log_group.setLayout(log_layout)
        
        layout.addWidget(log_group)
        
        # Log handler
        log_handler = QTextEditLogger(self.log_widget)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)
        
        return widget

    def _create_symbols_tab(self):
        """Hisseler sekmesi"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        symbol_group = QGroupBox("📊 Taranacak Hisseler")
        symbol_layout = QVBoxLayout()
        
        self.symbol_list_widget = QListWidget()
        self.symbol_list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.symbol_list_widget.itemClicked.connect(self.show_selected_chart)
        
        # Ekleme
        input_layout = QHBoxLayout()
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Hisse kodu (örn: GARAN)")
        self.symbol_input.returnPressed.connect(self.add_symbol)
        
        add_btn = QPushButton("➕ Ekle")
        add_btn.clicked.connect(self.add_symbol)
        add_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        input_layout.addWidget(self.symbol_input)
        input_layout.addWidget(add_btn)
        
        # Yönetim butonları
        manage_layout = QHBoxLayout()
        
        remove_btn = QPushButton("🗑️ Sil")
        remove_btn.clicked.connect(self.remove_symbol)
        remove_btn.setStyleSheet("background-color: #f44336; color: white;")
        
        clear_btn = QPushButton("🧹 Temizle")
        clear_btn.clicked.connect(self.clear_all_symbols)
        clear_btn.setStyleSheet("background-color: #FF9800; color: white;")
        
        manage_layout.addWidget(remove_btn)
        manage_layout.addWidget(clear_btn)
        manage_layout.addStretch()
        
        # Hızlı ekleme
        quick_group = QGroupBox("⚡ Hızlı Ekle")
        quick_layout = QHBoxLayout()
        
        bist30_btn = QPushButton("BIST30")
        bist30_btn.clicked.connect(self.quick_add_bist30)
        bist30_btn.setStyleSheet("background-color: #2196F3; color: white;")
        
        bist100_btn = QPushButton("BIST100")
        bist100_btn.clicked.connect(self.quick_add_bist100)
        bist100_btn.setStyleSheet("background-color: #2196F3; color: white;")
        
        banks_btn = QPushButton("Bankalar")
        banks_btn.clicked.connect(self.quick_add_banks)
        banks_btn.setStyleSheet("background-color: #2196F3; color: white;")
        
        import_btn = QPushButton("📂 CSV")
        import_btn.clicked.connect(self.import_symbols_from_csv)
        import_btn.setStyleSheet("background-color: #FF9800; color: white;")
        
        quick_layout.addWidget(bist30_btn)
        quick_layout.addWidget(bist100_btn)
        quick_layout.addWidget(banks_btn)
        quick_layout.addWidget(import_btn)
        quick_group.setLayout(quick_layout)
        
        symbol_layout.addWidget(self.symbol_list_widget, 1)
        symbol_layout.addLayout(input_layout)
        symbol_layout.addLayout(manage_layout)
        symbol_layout.addWidget(quick_group)
        symbol_group.setLayout(symbol_layout)
        
        layout.addWidget(symbol_group)
        
        # Genel ayarlar
        general_group = QGroupBox("⚙️ Genel Ayarlar")
        general_layout = QVBoxLayout()
        
        exchange_layout = QHBoxLayout()
        exchange_layout.addWidget(QLabel("Borsa:"))
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["BIST", "NASDAQ", "NYSE"])
        exchange_layout.addWidget(self.exchange_combo)
        exchange_layout.addStretch()
        
        lookback_layout = QHBoxLayout()
        lookback_layout.addWidget(QLabel("Veri Aralığı (Gün):"))
        self.lookback_spin = QSpinBox()
        self.lookback_spin.setRange(50, 500)
        self.lookback_spin.setValue(250)
        lookback_layout.addWidget(self.lookback_spin)
        lookback_layout.addStretch()
        
        general_layout.addLayout(exchange_layout)
        general_layout.addLayout(lookback_layout)
        general_group.setLayout(general_layout)
        
        layout.addWidget(general_group)
        layout.addStretch()
        
        return tab

    def _create_basic_criteria_tab(self):
        """Temel kriterler sekmesi"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # TÜM KRİTERLERİ AYARLANABİLİR YAPIYORUZ
        numeric_group = QGroupBox("📈 Sayısal Kriterler")
        numeric_layout = QVBoxLayout()
        
        self.spin_widgets = {}
        
        numeric_settings = [
            ("Min RSI", "min_rsi", 0, 100, 1, 30),
            ("Max RSI", "max_rsi", 0, 100, 1, 70),
            ("Min Göreceli Hacim", "min_relative_volume", 0.1, 10.0, 0.1, 1.0),
            ("Max Günlük Değişim %", "max_daily_change_pct", 0, 20.0, 0.5, 8.0),
            ("Min Trend Skoru", "min_trend_score", 0, 100, 5, 50),
            ("Min Likidite Oranı", "min_liquidity_ratio", 0.1, 5.0, 0.1, 0.5),
            ("Min Hacim Patlaması", "min_volume_surge", 1.0, 5.0, 0.1, 1.2),
            ("Min Yükselen Dipler", "min_higher_lows", 0, 10, 1, 2),
        ]
        
        for label, key, min_val, max_val, step, default in numeric_settings:
            row_layout = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(200)
            spin = QDoubleSpinBox()
            spin.setRange(min_val, max_val)
            spin.setSingleStep(step)
            spin.setValue(self.cfg.get(key, default))
            spin.setMinimumWidth(100)
            
            row_layout.addWidget(lbl)
            row_layout.addWidget(spin)
            row_layout.addStretch()
            
            numeric_layout.addLayout(row_layout)
            self.spin_widgets[key] = spin
        
        numeric_group.setLayout(numeric_layout)
        layout.addWidget(numeric_group)
        
        # Checkbox kriterler
        check_group = QGroupBox("✅ Aktif/Pasif Kriterler")
        check_layout = QVBoxLayout()
        
        self.check_widgets = {}
        
        check_settings = [
            ("🔵 Fiyat EMA20 Üstünde", "price_above_ema20"),
            ("🟠 Fiyat EMA50 Üstünde", "price_above_ema50"),
            ("📈 MACD Pozitif", "macd_positive"),
            ("💪 ADX Kontrolü", "check_adx"),
            ("💰 Kurumsal Akış Kontrolü", "check_institutional_flow"),
            ("📊 Momentum Uyumsuzluk Kontrolü", "check_momentum_divergence"),
        ]
        
        for label, key in check_settings:
            cb = QCheckBox(label)
            cb.setChecked(self.cfg.get(key, True))
            cb.setStyleSheet("padding: 5px;")
            check_layout.addWidget(cb)
            self.check_widgets[key] = cb
        
        check_group.setLayout(check_layout)
        layout.addWidget(check_group)
        
        scroll.setWidget(container)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        
        return tab

    def _create_advanced_criteria_tab(self):
        """Gelişmiş özellikler sekmesi"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        features_group = QGroupBox("🚀 Gelişmiş Özellikler")
        features_layout = QVBoxLayout()
        
        self.advanced_checkboxes = {}
        
        advanced_features = [
            ("📊 Multi-Timeframe Analiz", "use_multi_timeframe", "Günlük + Haftalık trend"),
            ("🌀 Fibonacci Retracement", "use_fibonacci", "Fibonacci destek/direnç"),
            ("📦 Konsolidasyon Tespiti", "use_consolidation", "Pattern tespiti"),
        ]
        
        for label, key, description in advanced_features:
            feature_layout = QHBoxLayout()
            
            cb = QCheckBox(label)
            cb.setChecked(self.cfg.get(key, True))
            
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #666; font-size: 9pt;")
            
            feature_layout.addWidget(cb)
            feature_layout.addWidget(desc_label)
            feature_layout.addStretch()
            
            features_layout.addLayout(feature_layout)
            self.advanced_checkboxes[key] = cb
        
        features_group.setLayout(features_layout)
        layout.addWidget(features_group)
        
        layout.addStretch()
        
        return tab

    def _create_risk_tab(self):
        """Risk yönetimi sekmesi"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        risk_group = QGroupBox("🛡️ Risk Yönetimi Parametreleri")
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
            lbl.setMinimumWidth(200)
            spin = QDoubleSpinBox()
            spin.setRange(min_val, max_val)
            spin.setSingleStep(step)
            spin.setValue(self.cfg.get(key, default))
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

    def _create_control_panel(self):
        """Kontrol paneli"""
        control_group = QGroupBox("🎮 Kontrol Paneli")
        control_layout = QVBoxLayout()
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("▶️ Taramayı Başlat")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 12pt;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.run_btn.clicked.connect(self.start_scan)
        
        self.stop_btn = QPushButton("⏸️ Durdur")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 12pt;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_scan)
        self.stop_btn.setEnabled(False)
        
        button_layout.addWidget(self.run_btn)
        button_layout.addWidget(self.stop_btn)
        
        # İlerleme
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar { height: 25px; }")
        
        self.status_label = QLabel("⏳ Beklemede...")
        self.status_label.setStyleSheet(
            "font-size: 11pt; padding: 10px; "
            "background-color: #e8f5e9; border-radius: 4px;"
        )
        
        control_layout.addLayout(button_layout)
        control_layout.addWidget(self.progress_bar)
        control_layout.addWidget(self.status_label)
        control_group.setLayout(control_layout)
        
        return control_group

    def _create_right_panel(self):
        """Sağ panel - Sonuçlar ve Grafik"""
        widget = QWidget() 
        layout = QVBoxLayout(widget)
        chart_group = QGroupBox("📊 Hisse Grafiği ve Analiz Detayları")
        chart_layout = QVBoxLayout()
        
        # Tab widget
        tabs = QTabWidget()
        
        # Tab 1: Grafik (BÜYÜTÜLDÜ)
        chart_tab = self._create_chart_tab()
        tabs.addTab(chart_tab, "📊 Grafik")
        
        # Tab 2: Sonuçlar
        results_tab = self._create_results_tab()
        tabs.addTab(results_tab, "📋 Sonuçlar")
        
        # Tab 3: Piyasa Durumu + Backtest
        market_tab = self._create_market_backtest_tab()
        tabs.addTab(market_tab, "📈 Piyasa & Backtest")
        
        layout.addWidget(tabs)
        
        return widget

    def _create_chart_tab(self):
        """Grafik sekmesi - BÜYÜTÜLDÜ"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Başlık
        self.chart_title = QLabel("Hisse seçin veya tarama yapın...")
        self.chart_title.setStyleSheet(
            "font-size: 14pt; font-weight: bold; padding: 10px; "
            "background-color: #e3f2fd; border-radius: 4px;"
        )
        self.chart_title.setAlignment(Qt.AlignCenter)
        
        # Grafik label - BÜYÜK
        self.chart_label = QLabel("Yükleniyor...")
        self.chart_label.setAlignment(Qt.AlignCenter)
        self.chart_label.setMinimumSize(800, 600) 
        self.chart_label.setStyleSheet("border: 1px solid #ccc; background-color: #ffffff;")
        
        self.chart_label.setText("📊 Grafik Alanı\n\nHisse seçin veya tarama yapın")
        
        layout.addWidget(self.chart_title)
        layout.addWidget(self.chart_label, 1)  # Stretch factor = 1
        
        return tab

    # swing_gui_advanced_plus.py içinde düzeltilmesi gereken bölüm:

    def _create_results_tab(self):
        """Sonuçlar Sekmesi - DÜZELTİLMİŞ"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
    
        # Başlık
        header_layout = QHBoxLayout()
        
        self.results_title = QLabel("📊 Tarama Sonuçları")
        self.results_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #1976D2;")
        
        self.results_stats = QLabel("Sonuç: 0 hisse")
        self.results_stats.setStyleSheet("font-size: 11pt; font-weight: bold; color: #4CAF50;")
        
        header_layout.addWidget(self.results_title)
        header_layout.addStretch()
        header_layout.addWidget(self.results_stats)
        
        layout.addLayout(header_layout)
        
        # Tablo
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSortingEnabled(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.itemSelectionChanged.connect(self.on_table_selection_changed)
        
        layout.addWidget(self.results_table)
        
        # ✅ YENİ: Trade detayları paneli
        details_group = QGroupBox("📋 Seçili Hisse Detayları")
        details_layout = QVBoxLayout()
        
        self.trade_details_text = QTextEdit()
        self.trade_details_text.setReadOnly(True)
        self.trade_details_text.setMaximumHeight(200)
        self.trade_details_text.setStyleSheet(
            "font-family: 'Courier New'; font-size: 9pt; "
            "background-color: #f0f8ff; border: 1px solid #4CAF50;"
        )
        self.trade_details_text.setPlainText("Bir hisse seçin...")
        
        details_layout.addWidget(self.trade_details_text)
        details_group.setLayout(details_layout)
        
        layout.addWidget(details_group)
        
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
        
        layout.addLayout(export_layout)
        
        return tab

    # on_table_selection_changed fonksiyonunu da güvenli hale getir:
    def on_table_selection_changed(self):
        """Sonuçlar tablosunda seçim değiştiğinde - GÜVENLİ VERSİYON"""
        try:
            selected_items = self.results_table.selectedItems()
            
            if not selected_items:
                if hasattr(self, 'trade_details_text') and self.trade_details_text:
                    self.trade_details_text.setPlainText("Bir hisse seçin...")
                return
            
            row = selected_items[0].row()
            
            # Güvenli veri okuma
            try:
                symbol_item = self.results_table.item(row, 0)
                if not symbol_item:
                    return
                symbol = symbol_item.text()
                
                # Fiyat değerlerini güvenli şekilde al
                entry_item = self.results_table.item(row, 4)
                stop_item = self.results_table.item(row, 5)
                target_item = self.results_table.item(row, 6)
                
                if not all([entry_item, stop_item, target_item]):
                    return
                
                entry_str = entry_item.text()
                stop_str = stop_item.text()
                target_str = target_item.text()
                
                # ✅ Aralık formatını işle (96.98-100.94)
                def safe_float_conversion(text):
                    if not text:
                        return None
                    if '-' in text and text.count('-') == 1:  # Aralık formatı
                        parts = text.split('-')
                        try:
                            return (float(parts[0]) + float(parts[1])) / 2
                        except:
                            return None
                    try:
                        return float(text)
                    except ValueError:
                        return None
                
                entry_price = safe_float_conversion(entry_str)
                stop_loss = safe_float_conversion(stop_str)
                target1 = safe_float_conversion(target_str)
                
                if None in [entry_price, stop_loss, target1]:
                    if hasattr(self, 'trade_details_text') and self.trade_details_text:
                        self.trade_details_text.setPlainText("Fiyat verileri okunamadı")
                    return
                
                # Trade detaylarını göster
                if hasattr(self, 'trade_details_text') and self.trade_details_text:
                    self.show_trade_details(symbol, entry_price, stop_loss, target1)
                
                # Grafiği göster
                self.show_selected_chart_from_symbol(symbol)
                
            except (ValueError, AttributeError) as e:
                logging.error(f"Tablo veri okuma hatası: {e}")
                if hasattr(self, 'trade_details_text') and self.trade_details_text:
                    self.trade_details_text.setPlainText(f"Veri okuma hatası: {e}")
        
        except Exception as e:
            logging.error(f"Seçim değişikliği hatası: {e}")
            if hasattr(self, 'trade_details_text') and self.trade_details_text:
                self.trade_details_text.setPlainText(f"Hata: {e}")
    
    def _get_market_strategy(self, regime):
        """Piyasa rejimine göre strateji"""
        strategies = {
            "bullish": "• Trend takip stratejileri kullan\n• EMA üstü kırılımlara odaklan\n• Risk/Ödül oranını 2.0+ tut",
            "bearish": "• Kısa pozisyonlardan kaçın\n• Sadece güçlü desteklerde alım\n• Risk/Ödül oranını 3.0+ yap", 
            "volatile": "• Pozisyon büyüklüğünü küçült\n• Daha geniş stop loss kullan\n• Günlük işlemlerden kaçın",
            "sideways": "• Range breakout stratejileri\n• Destek/direnç seviyelerine odaklan\n• Hacim konfirmasyonu önemli",
            "neutral": "• Seçici alım stratejisi\n• Temel analiz önem kazanır\n• Risk yönetimine dikkat"
        }
        return strategies.get(regime, "• Standart strateji uygula")
    
    def show_selected_chart_from_symbol(self, symbol):
        """Sembol string'inden grafik göster"""
        try:
            # ListWidget'ta hisseyi bul
            items = self.symbol_list_widget.findItems(symbol, Qt.MatchExactly)
            if items:
                self.show_selected_chart(items[0])
        except Exception as e:
            logging.error(f"Grafik gösterme hatası: {e}")

    def _create_market_backtest_tab(self):
        """Piyasa durumu ve backtest birleşik sekmesi - GELİŞTİRİLMİŞ"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Piyasa Durumu - GELİŞTİRİLMİŞ
        market_group = QGroupBox("📈 Canlı Piyasa Durumu")
        market_layout = QVBoxLayout()
        
        self.market_status_label = QLabel("🔄 Piyasa analizi yapılıyor...")
        self.market_status_label.setStyleSheet("font-size: 12pt; padding: 10px; background-color: #e3f2fd; border-radius: 4px;")
        self.market_status_label.setWordWrap(True)
        
        # Piyasa detayları
        self.market_details = QTextEdit()
        self.market_details.setReadOnly(True)
        self.market_details.setMaximumHeight(150)
        self.market_details.setStyleSheet("font-family: 'Segoe UI'; font-size: 10pt; background-color: #f0f8ff;")
        
        market_layout.addWidget(self.market_status_label)
        market_layout.addWidget(self.market_details)
        
        # Piyasa yenileme butonu
        market_btn_layout = QHBoxLayout()
        self.refresh_market_btn = QPushButton("🔄 Piyasa Analizini Yenile")
        self.refresh_market_btn.clicked.connect(self.start_market_analysis)
        self.refresh_market_btn.setStyleSheet("background-color: #2196F3; color: white;")
        
        market_btn_layout.addWidget(self.refresh_market_btn)
        market_btn_layout.addStretch()
        
        market_layout.addLayout(market_btn_layout)
        market_group.setLayout(market_layout)
        
        layout.addWidget(market_group)
        
        # Backtest - GELİŞTİRİLMİŞ
        backtest_group = QGroupBox("🎯 Gelişmiş Backtest")
        backtest_layout = QVBoxLayout()
        
        # Backtest ayarları
        backtest_settings_layout = QHBoxLayout()
        
        backtest_settings_layout.addWidget(QLabel("Gün:"))
        self.backtest_days = QSpinBox()
        self.backtest_days.setRange(30, 730)
        self.backtest_days.setValue(180)
        backtest_settings_layout.addWidget(self.backtest_days)
        
        backtest_settings_layout.addWidget(QLabel("Sermaye:"))
        self.initial_capital = QSpinBox()
        self.initial_capital.setRange(1000, 100000)
        self.initial_capital.setValue(10000)
        self.initial_capital.setSuffix(" TL")
        backtest_settings_layout.addWidget(self.initial_capital)
        
        backtest_settings_layout.addStretch()
        
        # Backtest buton
        self.backtest_btn = QPushButton("▶️ Backtest Başlat")
        self.backtest_btn.clicked.connect(self.start_backtest)
        self.backtest_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px;")
        
        self.backtest_results_text = QTextEdit()
        self.backtest_results_text.setReadOnly(True)
        self.backtest_results_text.setStyleSheet(
            "font-family: 'Courier New'; font-size: 9pt; background-color: #f5f5f5;"
        )
        
        backtest_layout.addLayout(backtest_settings_layout)
        backtest_layout.addWidget(self.backtest_btn)
        backtest_layout.addWidget(self.backtest_results_text, 1)
        backtest_group.setLayout(backtest_layout)
        
        layout.addWidget(backtest_group, 1)
        
        return tab

    def start_market_analysis(self):
        """Piyasa analizini başlat - DÜZELTİLMİŞ"""
        self.market_status_label.setText("🔄 Piyasa analizi yapılıyor...")
        self.market_details.setText("BIST100 ve piyasa verileri analiz ediliyor...")
        
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

    def market_analysis_finished(self, analysis):
        """Piyasa analizi tamamlandı - DÜZELTİLMİŞ"""
        self.market_analysis = analysis
        
        # Renk kodları
        color = "#4CAF50"  # varsayılan
        if analysis.regime == "bearish":
            color = "#f44336"
        elif analysis.regime == "volatile":
            color = "#FF9800"
        elif analysis.regime == "sideways":
            color = "#2196F3"
        
        self.market_status_label.setText(
            f"📈 Piyasa Durumu: <span style='color: {color}; font-weight: bold;'>{analysis.regime.upper()}</span> - {analysis.recommendation}"
        )
        
        # Detaylı bilgi
        details = f"""
    📊 PİYASA ANALİZ RAPORU
    {'='*40}
    📈 Trend Gücü: {analysis.trend_strength}/100
    📉 Volatilite: {analysis.volatility}%
    📊 Hacim Trendi: {analysis.volume_trend:.2f}x
    ⭐ Piyasa Skoru: {analysis.market_score}/100

    💡 ÖNERİ: {analysis.recommendation}

    📋 STRATEJİ:
    {self._get_market_strategy(analysis.regime)}
    """
        self.market_details.setText(details)
        
        logging.info(f"✅ Piyasa analizi tamamlandı: {analysis.regime}")

        
    def market_analysis_error(self, error_message):
        """Piyasa analizi hatası"""
        self.market_status_label.setText("❌ Piyasa analizi başarısız")
        self.market_details.setText(f"Hata: {error_message}\n\nLütfen internet bağlantınızı kontrol edin ve tekrar deneyin.")
        logging.error(f"Piyasa analizi hatası: {error_message}")

    def start_backtest(self):
        """Backtest başlat - GELİŞTİRİLMİŞ"""
        if self.symbol_list_widget.count() == 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir hisse ekleyin!")
            return
        
        symbols = [
            self.symbol_list_widget.item(i).text() 
            for i in range(self.symbol_list_widget.count())
        ]
        
        backtest_config = {
            'days': self.backtest_days.value(),
            'initial_capital': self.initial_capital.value(),
            'commission_rate': 0.2
        }
        
        self.backtest_btn.setEnabled(False)
        self.backtest_btn.setText("⏳ Backtest Sürüyor...")
        
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
        
        logging.info(f"🎯 Backtest başlatıldı: {len(symbols)} sembol, {backtest_config['days']} gün")

    def backtest_finished(self, results):
        """Backtest tamamlandı - GELİŞTİRİLMİŞ"""
        self.backtest_results = results
        self.display_backtest_results(results)
        
        self.backtest_btn.setEnabled(True)
        self.backtest_btn.setText("▶️ Backtest Başlat")
        
        if 'summary' in results:
            summary = results['summary']
            QMessageBox.information(
                self, "Backtest Tamamlandı",
                f"Backtest sonuçları hazır!\n\n"
                f"Test edilen hisse: {summary['total_symbols']}\n"
                f"Toplam işlem: {summary['total_trades']}\n"
                f"Başarı oranı: {summary['win_rate']:.1f}%\n"
                f"Toplam kâr: {summary['total_profit']:,.0f} TL"
            )
        else:
            QMessageBox.warning(self, "Uyarı", "Backtest sonuç alınamadı!")
        
        self.backtest_worker = None

    def display_backtest_results(self, results):
        """Backtest sonuçlarını göster - GÜVENLİ VERSİYON"""
        try:
            # Hata kontrolü
            if isinstance(results, dict) and 'error' in results:
                self.backtest_results_text.setPlainText(f"❌ HATA: {results['error']}")
                return
            
            if not isinstance(results, dict) or 'summary' not in results:
                self.backtest_results_text.setPlainText("❌ Geçersiz backtest sonuç formatı")
                return
            
            summary = results.get('summary', {})
            detailed = results.get('detailed', [])
            
            # Rapor oluştur
            report_lines = []
            report_lines.append("🎯 BACKTEST SONUÇ RAPORU")
            report_lines.append("=" * 50)
            report_lines.append("")
            
            # Summary bölümü
            report_lines.append("📊 PERFORMANS ÖZETİ:")
            report_lines.append(f"• Test edilen hisse: {summary.get('total_symbols', 0)}")
            report_lines.append(f"• Toplam işlem: {summary.get('total_trades', 0)}")
            report_lines.append(f"• Kazanan işlem: {summary.get('winning_trades', 0)}")
            report_lines.append(f"• Başarı oranı: {summary.get('win_rate', 0):.1f}%")
            report_lines.append(f"• Toplam kâr: {summary.get('total_profit', 0):,.0f} TL")
            report_lines.append(f"• Ortalama getiri: {summary.get('avg_return', 0):.1f}%")
            report_lines.append(f"• En iyi hisse: {summary.get('best_symbol', 'N/A')}")
            report_lines.append(f"• En kötü hisse: {summary.get('worst_symbol', 'N/A')}")
            report_lines.append("")
            
            # Detaylı sonuçlar
            if detailed:
                report_lines.append("📈 DETAYLI SONUÇLAR:")
                report_lines.append("-" * 40)
                
                for idx, result in enumerate(detailed[:10], 1):  # İlk 10
                    symbol = result.get('Symbol', f'Hisse-{idx}')
                    trades = result.get('Trades', 0)
                    win_rate = result.get('Win Rate %', 0)
                    total_return = result.get('Total Return %', 0)
                    total_profit = result.get('Total Profit', 0)
                    max_dd = result.get('Max Drawdown %', 0)
                    sharpe = result.get('Sharpe Ratio', 0)
                    
                    report_lines.append(f"\n{idx}. {symbol}:")
                    report_lines.append(f"   • İşlem: {trades} | Başarı: {win_rate:.1f}%")
                    report_lines.append(f"   • Getiri: {total_return:.1f}% | Kâr: {total_profit:,.0f} TL")
                    report_lines.append(f"   • Maks. Düşüş: {max_dd:.1f}% | Sharpe: {sharpe:.2f}")
            
            # Not
            if results.get('note'):
                report_lines.append(f"\n💡 NOT: {results['note']}")
            
            self.backtest_results_text.setPlainText("\n".join(report_lines))
            
        except Exception as e:
            error_msg = f"Backtest sonuç gösterim hatası:\n{str(e)}"
            self.backtest_results_text.setPlainText(error_msg)
            logging.error(f"display_backtest_results hatası: {e}")

    def backtest_error(self, error_message):
        """Backtest hatası"""
        self.backtest_btn.setEnabled(True)
        self.backtest_btn.setText("▶️ Backtest Başlat")
        
        logging.error(f"Backtest hatası: {error_message}")
        QMessageBox.critical(self, "Backtest Hatası", f"Backtest sırasında hata oluştu:\n\n{error_message}")
        
        self.backtest_worker = None

    # ========================================================================
    # Hisse Yönetimi Fonksiyonları
    # ========================================================================
    
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
        reply = QMessageBox.question(
            self, 'Onay', 'Tüm hisseleri silmek istediğinizden emin misiniz?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.symbol_list_widget.clear()
            logging.info("🧹 Tüm hisseler temizlendi")
    
    def quick_add_bist30(self):
        """BIST30 ekle"""
        bist30 = [
            'AKBNK', 'ARCLK', 'ASELS', 'BIMAS', 'EKGYO', 'EREGL', 'FROTO',
            'GARAN', 'HALKB', 'ISCTR', 'KCHOL', 'KOZAA', 'KOZAL', 'KRDMD',
            'MGROS', 'ODAS', 'OYAKC', 'PETKM', 'PGSUS', 'SAHOL', 'SASA',
            'SISE', 'SKBNK', 'TCELL', 'THYAO', 'TKFEN', 'TOASO', 'TTKOM',
            'TUPRS', 'VAKBN', 'YKBNK'
        ]
        self.add_symbols_to_list(bist30)
    
    def quick_add_bist100(self):
        """BIST100 ekle"""
        bist100 = [
            'AKBNK', 'AKSEN', 'ALARK', 'ARCLK', 'ASELS', 'AYGAZ', 'BIMAS', 
            'DOHOL', 'EKGYO', 'ENJSA', 'EREGL', 'FROTO', 'GARAN', 'GUBRF',
            'HALKB', 'ISCTR', 'KCHOL', 'KONTR', 'KOZAA', 'KOZAL', 'KRDMD',
            'MGROS', 'ODAS', 'OYAKC', 'PETKM', 'PGSUS', 'SAHOL', 'SASA',
            'SISE', 'SKBNK', 'TCELL', 'THYAO', 'TKFEN', 'TOASO', 'TTKOM',
            'TUPRS', 'VAKBN', 'VESTL', 'YKBNK'
        ]
        self.add_symbols_to_list(bist100)
    
    def quick_add_banks(self):
        """Banka hisseleri ekle"""
        banks = [
            'AKBNK', 'GARAN', 'ISCTR', 'HALKB', 'SKBNK', 
            'VAKBN', 'YKBNK', 'ALBRK', 'QNBFB', 'ICBCT'
        ]
        self.add_symbols_to_list(banks)
    
    def add_symbols_to_list(self, symbols):
        """Sembolleri listeye ekle"""
        added = 0
        for symbol in symbols:
            items = self.symbol_list_widget.findItems(symbol, Qt.MatchExactly)
            if not items:
                self.symbol_list_widget.addItem(symbol)
                added += 1
        logging.info(f"✅ {added} hisse eklendi")
    
    def import_symbols_from_csv(self):
        """CSV'den import"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "CSV Dosyası Seç", "", "CSV Files (*.csv);;All Files (*)"
            )
            
            if file_path:
                df = pd.read_csv(file_path)
                
                symbol_col = None
                for col in df.columns:
                    if 'symbol' in col.lower() or 'hisse' in col.lower():
                        symbol_col = col
                        break
                
                if symbol_col is None:
                    symbol_col = df.columns[0]
                
                symbols = df[symbol_col].astype(str).str.upper().tolist()
                self.add_symbols_to_list(symbols)
                
                QMessageBox.information(self, "Başarılı", f"{len(symbols)} hisse içe aktarıldı!")
                
        except Exception as e:
            logging.error(f"CSV import hatası: {e}")
            QMessageBox.critical(self, "Hata", f"CSV import hatası:\n{e}")
    
    # ========================================================================
    # Ayar Yönetimi
    # ========================================================================
    
    def load_settings(self):
        """Ayarları yükle"""
        try:
            # Sembolleri yükle
            self.symbol_list_widget.clear()
            self.symbol_list_widget.addItems(self.cfg.get('symbols', []))
            
            # Genel ayarlar
            self.exchange_combo.setCurrentText(self.cfg.get('exchange', 'BIST'))
            self.lookback_spin.setValue(self.cfg.get('lookback_bars', 250))
            
            logging.info("✅ Ayarlar yüklendi")
            
        except Exception as e:
            logging.error(f"Ayar yükleme hatası: {e}")
    
    def save_settings(self):
        """Ayarları kaydet"""
        try:
            # Sayısal ayarlar
            for key, spin in self.spin_widgets.items():
                self.cfg[key] = spin.value()
            
            # Risk ayarları
            for key, spin in self.risk_spin_widgets.items():
                self.cfg[key] = spin.value()
            
            # Checkbox ayarları
            for key, cb in self.check_widgets.items():
                self.cfg[key] = cb.isChecked()
            
            # Gelişmiş özellikler
            for key, cb in self.advanced_checkboxes.items():
                self.cfg[key] = cb.isChecked()
            
            # Semboller
            symbols = [
                self.symbol_list_widget.item(i).text() 
                for i in range(self.symbol_list_widget.count())
            ]
            self.cfg['symbols'] = symbols
            
            # Genel ayarlar
            self.cfg['exchange'] = self.exchange_combo.currentText()
            self.cfg['lookback_bars'] = self.lookback_spin.value()
            
            # Dosyaya kaydet
            with open('swing_config.json', 'w', encoding='utf-8') as f:
                json.dump(self.cfg, f, indent=2, ensure_ascii=False)
            
            logging.info("💾 Ayarlar kaydedildi")
            
        except Exception as e:
            logging.error(f"Ayar kaydetme hatası: {e}")
    
    # ========================================================================
    # Tarama Fonksiyonları
    # ========================================================================
    
    def start_scan(self):
        """Taramayı başlat"""
        if self.symbol_list_widget.count() == 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir hisse ekleyin!")
            return
        
        # Ayarları kaydet
        self.save_settings()
        
        # Sembolleri al
        symbols = [
            self.symbol_list_widget.item(i).text() 
            for i in range(self.symbol_list_widget.count())
        ]
        
        # UI'yi hazırla
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.run_btn.setText("⏳ Tarama Sürüyor...")
        self.progress_bar.setValue(0)
        self.results_table.setRowCount(0)
        self.status_label.setText("🔍 Tarama başladı...")
        
        # Worker başlat
        self.scan_thread = QThread()
        self.scan_worker = ScanWorker(self.hunter, symbols)
        self.scan_worker.moveToThread(self.scan_thread)
        
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.finished.connect(self.scan_worker.deleteLater)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        
        self.scan_worker.progress.connect(self.update_progress)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.error.connect(self.scan_error)
        
        self.scan_thread.start()
        
        logging.info(f"🚀 Tarama başlatıldı: {len(symbols)} sembol")
    
    def stop_scan(self):
        """Taramayı durdur"""
        if self.scan_worker:
            self.scan_worker.stop()
            self.stop_btn.setEnabled(False)
            self.status_label.setText("⏸️ Tarama durduruluyor...")
            logging.info("⏸️ Tarama durdurma sinyali gönderildi")
    
    def update_progress(self, percent, message):
        """İlerleme güncelle"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def generate_and_show_chart(self, symbol):
        """Tarama sonrası ilk hissenin grafiğini otomatik göster - GÜVENLİ VERSİYON"""
        if not symbol or self.results_table.rowCount() == 0:
            return
        
        # Veriyi çek
        try:
            data = self.tv.get_hist(
                symbol=symbol,
                exchange=self.cfg.get('exchange', 'BIST'),
                interval=Interval.in_daily,
                n_bars=self.cfg.get('lookback_bars', 250)
            )
            
            if data is not None and len(data) > 20:
                # chart_widget.py'den import et
                from gui.chart_widget import SwingTradeChart
                
                # DataFrame'i düzelt
                if not isinstance(data.index, pd.DatetimeIndex):
                    data.index = pd.to_datetime(data.index)
                data = data.reset_index()
                
                # Column mapping - daha güvenli
                column_mapping = {
                    'open': 'open',
                    'high': 'high', 
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume'
                }
                
                # Mevcut sütunları bul
                available_cols = {col.lower(): col for col in data.columns}
                
                # Eşleştirme yap
                for target_col in ['open', 'high', 'low', 'close', 'volume']:
                    if target_col not in data.columns:
                        # Alternatif isimleri kontrol et
                        for avail_key, avail_col in available_cols.items():
                            if target_col in avail_key:
                                data[target_col] = data[avail_col]
                                break
                
                # Eksik sütun kontrolü
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                missing = [col for col in required_cols if col not in data.columns]
                if missing:
                    logging.warning(f"Eksik sütunlar: {missing}")
                    return
                
                # trade_info oluştur - GÜVENLİ OKUMA
                trade_info = {}
                
                # Tablodan sembolü bul
                for row in range(self.results_table.rowCount()):
                    current_symbol = self.results_table.item(row, 0).text() if self.results_table.item(row, 0) else ""
                    
                    if current_symbol == symbol:
                        try:
                            # Sütun başlıklarını al
                            headers = []
                            for col in range(self.results_table.columnCount()):
                                header_item = self.results_table.horizontalHeaderItem(col)
                                if header_item:
                                    headers.append(header_item.text())
                            
                            # Hangi sütunun ne olduğunu bul
                            entry_col = -1
                            stop_col = -1
                            target_col = -1
                            
                            for i, header in enumerate(headers):
                                if 'giriş' in header.lower():
                                    entry_col = i
                                elif 'stop' in header.lower():
                                    stop_col = i
                                elif 'hedef' in header.lower() and '1' in header:
                                    target_col = i
                            
                            # Değerleri güvenli şekilde oku
                            def safe_float_conversion(text):
                                if not text:
                                    return None
                                # "96.98-100.94" formatı kontrolü
                                if '-' in text:
                                    parts = text.split('-')
                                    try:
                                        return (float(parts[0]) + float(parts[1])) / 2
                                    except:
                                        return None
                                # Normal float dönüşümü
                                try:
                                    return float(text)
                                except ValueError:
                                    # "/" karakteri içeriyorsa (örn: "0/20")
                                    if '/' in text:
                                        return None
                                    # Diğer durumlar
                                    return None
                            
                            # Entry fiyatı
                            if entry_col >= 0:
                                entry_item = self.results_table.item(row, entry_col)
                                if entry_item:
                                    entry_price = safe_float_conversion(entry_item.text())
                                    if entry_price:
                                        trade_info['entry_price'] = entry_price
                            
                            # Stop loss
                            if stop_col >= 0:
                                stop_item = self.results_table.item(row, stop_col)
                                if stop_item:
                                    stop_price = safe_float_conversion(stop_item.text())
                                    if stop_price:
                                        trade_info['stop_loss'] = stop_price
                            
                            # Hedef fiyat
                            if target_col >= 0:
                                target_item = self.results_table.item(row, target_col)
                                if target_item:
                                    target_price = safe_float_conversion(target_item.text())
                                    if target_price:
                                        trade_info['target_price'] = target_price
                            
                            break
                            
                        except Exception as e:
                            logging.error(f"Trade info okuma hatası: {e}")
                
                # Grafik penceresini aç
                chart_window = SwingTradeChart(data, symbol, trade_info)
                chart_window.show()
                
                # Pencereyi kaybetmemek için referans tut
                if not hasattr(self, 'open_charts'):
                    self.open_charts = []
                self.open_charts.append(chart_window)
                
                logging.info(f"✅ {symbol} grafiği açıldı")
                
        except Exception as e:
            logging.error(f"Grafik gösterim hatası: {e}")
            QMessageBox.critical(self, "Grafik Hatası", f"{symbol} grafiği açılamadı:\n{str(e)}")
    
    def scan_finished(self, output):
        """Tarama tamamlandı - Market analizi entegre"""
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.run_btn.setText("▶️ Taramayı Başlat")
        self.progress_bar.setValue(100)
        self.status_label.setText("✅ Tarama tamamlandı!")
        
        results_list = output.get('results', {}).get('Swing Uygun', [])
        market_analysis = output.get('market_analysis')
        
        if results_list:
            self.populate_table(results_list)
            
            # İlk hissenin grafiğini göster
            if results_list:
                first_symbol = results_list[0]['Hisse']
                self.generate_and_show_chart(first_symbol)
            
            msg = f"🎉 {len(results_list)} adet uygun hisse bulundu!"
            if market_analysis:
                msg += f"\n📈 Piyasa Durumu: {market_analysis.regime.title()}"
            if output.get('excel_file'):
                msg += f"\n📊 Excel Raporu: {output['excel_file']}"
            
            QMessageBox.information(self, "Başarılı", msg)
        else:
            QMessageBox.warning(
                self, "Sonuç Yok",
                "Kriterlere uyan hisse bulunamadı.\n\n"
                "💡 İpucu: Filtreleri gevşetmeyi deneyin."
            )
        
        self.scan_worker = None
    
    def scan_error(self, error_message):
        """Tarama hatası"""
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.run_btn.setText("▶️ Taramayı Başlat")
        self.status_label.setText("❌ Hata oluştu!")
        
        logging.error(f"Tarama hatası: {error_message}")
        QMessageBox.critical(
            self, "Hata",
            f"Tarama sırasında hata:\n\n{error_message}"
        )
        
        self.scan_worker = None

    def show_trade_details(self, symbol, entry_price, stop_loss, target1):
        """Trade detaylarını göster - DÜZELTİLMİŞ"""
        if not hasattr(self, 'trade_details_text') or self.trade_details_text is None:
            print("Trade details widget henüz oluşturulmamış")
            return
        
        try:
            # Trade planı hesapla (capital parametresi ekle)
            capital = self.cfg.get('initial_capital', 10000)
            trade_plan = self.hunter.calculate_trade_plan(
                symbol, entry_price, stop_loss, target1, capital
            )
            
            # Validasyon yap
            validation = self.hunter.validate_trade_parameters(
                entry_price, stop_loss, target1, symbol
            )
            
            # Detaylı bilgi penceresi
            details = f"""
    🎯 DETAYLI TRADE PLANI: {symbol}
    {'='*50}

    📊 TEMEL BİLGİLER:
    • Giriş Fiyatı: {entry_price:.2f} TL
    • Stop Loss: {stop_loss:.2f} TL
    • Hedef 1: {target1:.2f} TL
    • Risk/Hisse: {trade_plan.get('risk_per_share', 0):.2f} TL

    💰 POZİSİYON BOYUTU:
    • Sermaye: {trade_plan.get('capital', 0):,.0f} TL
    • Risk Oranı: {trade_plan.get('risk_pct', 0):.1f}%
    • Alınacak Hisse: {trade_plan.get('shares', 0)} adet
    • Toplam Yatırım: {trade_plan.get('investment', 0):,.0f} TL

    ⚠️ RİSK ANALİZİ:
    • Maksimum Kayıp: {trade_plan.get('max_loss_tl', 0):,.0f} TL ({trade_plan.get('max_loss_pct', 0):.1f}%)
    • Maksimum Kâr: {trade_plan.get('max_gain_tl', 0):,.0f} TL
    • R/R Oranı: 1:{trade_plan.get('rr_ratio', 0):.1f}
    • Validasyon Skoru: {validation.get('score', 0)}/100

    💡 ÖNERİ: {trade_plan.get('recommendation', 'N/A')}
    """
            
            # Uyarıları ekle
            if validation.get('has_warnings', False):
                details += "\n⚠️ UYARILAR:\n"
                for warning in validation.get('warnings', []):
                    details += f"• {warning}\n"
            
            # Hataları göster
            if not validation.get('is_valid', False):
                details += "\n❌ HATALAR:\n"
                for error in validation.get('errors', []):
                    details += f"• {error}\n"
            
            # GUI'de göster
            if hasattr(self, 'trade_details_text'):
                self.trade_details_text.setPlainText(details)
            
        except Exception as e:
            logging.error(f"Trade detay gösterim hatası: {e}")
            if hasattr(self, 'trade_details_text'):
                self.trade_details_text.setPlainText(f"Hata: {str(e)}")
    # ========================================================================
    # Grafik Fonksiyonları
    # ========================================================================

    def show_selected_chart(self, item):
        if not item:
            return
        symbol = item.text()
        try:
            # Günlük veri çek (Interval.in_daily ile)
            df = self.tv.get_hist(
                symbol=symbol,
                exchange=self.cfg.get('exchange', 'BIST'),
                interval=Interval.in_daily,  # <<<< BURASI DÜZELTİLDİ
                n_bars=self.cfg.get('lookback_bars', 250)
            )
            if df is None or len(df) < 30:
                self.status_label.setText(f"{symbol}: Yeterli veri yok")
                return

            # İndikatörleri hesapla
            from indicators.ta_manager import calculate_indicators
            df = calculate_indicators(df)

            # Tüm analiz verilerini topla
            trade_info = {}

            # 1. Pattern analizi
            from patterns.price_action import PriceActionDetector
            pattern_detector = PriceActionDetector()
            patterns = pattern_detector.analyze_patterns(df)
            trade_info['patterns'] = patterns

            # 2. Konsolidasyon
            from analysis.consolidation import detect_consolidation_pattern
            consolidation = detect_consolidation_pattern(df)
            trade_info['consolidation'] = consolidation.__dict__

            # 3. Fibonacci
            from analysis.fibonacci import calculate_fibonacci_levels
            fib = calculate_fibonacci_levels(df)
            trade_info['fibonacci'] = fib

            # 4. Support/Resistance
            from analysis.support_resistance import SupportResistanceFinder
            sr_finder = SupportResistanceFinder()
            sr_levels = sr_finder.find_levels(df)
            trade_info['sr_levels'] = sr_levels

            # 5. Breakout kontrolü
            breakout_info = sr_finder.check_breakout(df, sr_levels)
            trade_info['breakout_info'] = breakout_info

            # 6. Trade bilgileri (basit varsayılanlar)
            latest = df.iloc[-1]
            trade_info['stop_loss'] = latest['close'] * 0.95
            trade_info['target1'] = latest['close'] * 1.10

            # Grafiği göster
            from gui.chart_widget import SwingTradeChart
            chart_window = SwingTradeChart(df, symbol, trade_info)
            chart_window.show()

            # Pencereyi kaybetmemek için referans tut
            if not hasattr(self, 'open_charts'):
                self.open_charts = []
            self.open_charts.append(chart_window)

            self.status_label.setText(f"✅ {symbol} grafiği açıldı")

        except Exception as e:
            import logging
            logging.error(f"Grafik hatası {symbol}: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Hata", f"{symbol} grafiği yüklenemedi:\n{str(e)}")

    # ========================================================================
    # Tablo Yönetimi
    # ========================================================================
    def on_table_selection_changed(self):
        """Sonuçlar tablosunda seçim değiştiğinde"""
        selected_items = self.results_table.selectedItems()
        
        if not selected_items:
            return
        
        try:
            row = selected_items[0].row()
            
            # Tablo sütunlarını kontrol et
            column_count = self.results_table.columnCount()
            
            # Hangi sütunun hangi veri olduğunu bul
            symbol_col = -1
            entry_col = -1
            stop_loss_col = -1
            target1_col = -1
            
            for col in range(column_count):
                header = self.results_table.horizontalHeaderItem(col).text()
                if header == 'Hisse':
                    symbol_col = col
                elif header == 'Optimal Giriş':
                    entry_col = col
                elif header == 'Stop Loss':
                    stop_loss_col = col
                elif header == 'Hedef 1':
                    target1_col = col
            
            if symbol_col == -1 or entry_col == -1 or stop_loss_col == -1 or target1_col == -1:
                return
            
            # Değerleri al
            symbol = self.results_table.item(row, symbol_col).text()
            
            # Optimal Giriş değerini al (aralık değil, tek değer)
            entry_text = self.results_table.item(row, entry_col).text()
            # Eğer aralık formatındaysa (96.98-100.94), ortasını al
            if '-' in entry_text:
                # "96.98-100.94" formatını ayır ve ortalamasını al
                parts = entry_text.split('-')
                if len(parts) == 2:
                    entry_price = (float(parts[0]) + float(parts[1])) / 2
                else:
                    entry_price = float(parts[0])
            else:
                entry_price = float(entry_text)
            
            stop_loss = float(self.results_table.item(row, stop_loss_col).text())
            target1 = float(self.results_table.item(row, target1_col).text())
            
            # Grafik göster
            self.show_selected_chart(self.results_table.item(row, symbol_col))
            
            # Trade detaylarını göster
            self.show_trade_details(symbol, entry_price, stop_loss, target1)
            
        except Exception as e:
            logging.error(f"Tablo seçim hatası: {e}")
            QMessageBox.warning(self, "Hata", f"Veri okuma hatası:\n{str(e)}")
                
    def populate_table(self, data):
        """Tabloyu doldur - YENİ ÖZELLİKLER EKLENDİ"""
        if not data:
            self.results_stats.setText("Sonuç: 0 hisse")
            return
        
        # Varsayılan sütunlar
        if data and isinstance(data[0], dict):
            headers = list(data[0].keys())
        else:
            return
        
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        self.results_table.setRowCount(len(data))
        
        for row_idx, row_data in enumerate(data):
            for col_idx, key in enumerate(headers):
                value = str(row_data.get(key, ''))
                item = QTableWidgetItem(value)
                
                # Renklendirme - YENİ KRİTERLER EKLENDİ
                if key == 'Skor':
                    try:
                        score = float(value.split('/')[0])
                        if score >= 85:
                            item.setBackground(QColor(50, 205, 50))  # LimeGreen
                            item.setForeground(QColor(255, 255, 255))
                        elif score >= 75:
                            item.setBackground(QColor(144, 238, 144))  # LightGreen
                        elif score >= 65:
                            item.setBackground(QColor(255, 255, 153))  # LightYellow
                    except:
                        pass
                
                elif key == 'Sinyal':
                    if '🔥🔥🔥' in value:
                        item.setBackground(QColor(50, 205, 50))
                        item.setForeground(QColor(255, 255, 255))
                    elif '🔥🔥' in value:
                        item.setBackground(QColor(144, 238, 144))
                    elif '🎯' in value:
                        item.setBackground(QColor(255, 215, 0))  # Gold
                
                elif key == 'Pattern Skor':
                    try:
                        pattern_score = float(value.split('/')[0])
                        if pattern_score >= 15:
                            item.setBackground(QColor(255, 182, 193))  # LightPink
                            item.setForeground(QColor(139, 0, 0))  # DarkRed
                        elif pattern_score >= 10:
                            item.setBackground(QColor(255, 228, 225))  # MistyRose
                    except:
                        pass
                
                elif key == 'Bullish Patternler' and value != 'Yok':
                    item.setBackground(QColor(230, 230, 250))  # Lavender
                    item.setFont(QFont('Arial', 9, QFont.Bold))
                
                elif key == 'R/R':
                    try:
                        rr_value = float(value.split(':')[1])
                        if rr_value >= 3.0:
                            item.setBackground(QColor(152, 251, 152))  # PaleGreen
                            item.setFont(QFont('Arial', 9, QFont.Bold))
                        elif rr_value >= 2.5:
                            item.setBackground(QColor(144, 238, 144))
                    except:
                        pass
                
                elif key == 'Piyasa Skoru':
                    try:
                        market_score = float(value.split('/')[0])
                        if market_score >= 70:
                            item.setBackground(QColor(135, 206, 250))  # LightSkyBlue
                    except:
                        pass
                
                self.results_table.setItem(row_idx, col_idx, item)
        
        self.results_table.resizeColumnsToContents()
        self.results_stats.setText(f"Sonuç: {len(data)} hisse")
    
    # ========================================================================
    # Export Fonksiyonları
    # ========================================================================
    
    def export_to_excel(self):
        """Excel'e aktar"""
        try:
            if self.results_table.rowCount() == 0:
                QMessageBox.warning(self, "Uyarı", "Aktarılacak veri yok!")
                return
            
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
            
            df = pd.DataFrame(data, columns=headers)
            filename = f"Swing_Advanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filename, index=False)
            
            logging.info(f"📊 Excel raporu: {filename}")
            QMessageBox.information(self, "Başarılı", f"Excel raporu oluşturuldu:\n{filename}")
            
        except Exception as e:
            logging.error(f"Excel aktarım hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Excel hatası:\n{e}")
    
    def export_to_csv(self):
        """CSV'ye aktar"""
        try:
            if self.results_table.rowCount() == 0:
                QMessageBox.warning(self, "Uyarı", "Aktarılacak veri yok!")
                return
            
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
            
            df = pd.DataFrame(data, columns=headers)
            filename = f"Swing_Advanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            logging.info(f"💾 CSV raporu: {filename}")
            QMessageBox.information(self, "Başarılı", f"CSV raporu oluşturuldu:\n{filename}")
            
        except Exception as e:
            logging.error(f"CSV aktarım hatası: {e}")
            QMessageBox.critical(self, "Hata", f"CSV hatası:\n{e}")
    
    # ========================================================================
    # Cleanup
    # ========================================================================
    
    def closeEvent(self, event):
        """Pencere kapatıldığında - SON DÜZELTME"""
        try:
            # Worker'ları durdur
            if hasattr(self, 'scan_worker') and self.scan_worker:
                try:
                    self.scan_worker.stop()
                except:
                    pass
            
            # Thread'leri güvenli şekilde kapat
            def safe_thread_stop(thread_obj):
                if thread_obj is None:
                    return
                try:
                    # Obje hala geçerli mi kontrol et
                    if hasattr(thread_obj, 'isRunning'):
                        if thread_obj.isRunning():
                            thread_obj.quit()
                            thread_obj.wait(300)  # 300ms bekle
                except RuntimeError:
                    pass  # Obje zaten silinmiş
                except Exception:
                    pass
            
            # Tüm thread'leri kapat
            safe_thread_stop(getattr(self, 'scan_thread', None))
            safe_thread_stop(getattr(self, 'backtest_thread', None))
            safe_thread_stop(getattr(self, 'market_thread', None))
            
            # Ayarları kaydet
            self.save_settings()
            
            logging.info("👋 Swing Hunter Advanced kapatılıyor...")
            event.accept()
            
        except Exception as e:
            logging.error(f"Kapatma hatası: {e}")
            event.accept()  # Her durumda pencereyi kapat

# ============================================================================
# Main
# ============================================================================

def main():
    """Ana fonksiyon"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    try:
        gui = SwingGUIAdvancedPlus()
        gui.show()
        sys.exit(app.exec_())
    except Exception as e:
        logging.critical(f"GUI başlatma hatası: {e}")
        QMessageBox.critical(None, "Kritik Hata", f"Program başlatılamadı:\n{e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
