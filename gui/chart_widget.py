# gui/chart_widget.py - ULTIMATE EDITION
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    print("⚠️ TA-Lib kurulu değil. Pattern detection çalışmayacak!")

try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False
    print("⚠️ PyQtGraph kurulu değil. Grafik gösterilemeyecek!")
import numpy as np
import pandas as pd
import talib
import pyqtgraph as pg
from datetime import datetime
from collections import deque

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QGridLayout, QWidget, QScrollArea, QCheckBox,
                             QGroupBox, QMessageBox, QProgressDialog, QInputDialog,
                             QSpinBox, QDoubleSpinBox, QFormLayout, QTabWidget)
from PyQt5.QtGui import QColor, QBrush, QPen, QFont
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QTimer
from PyQt5.QtMultimedia import QSound

# ---------------------------------------------------------------------
# GLOBAL CONFIG
# ---------------------------------------------------------------------
pg.setConfigOptions(antialias=True)
pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")

REQUIRED_COLUMNS = {"open", "high", "low", "close", "volume"}

# Tema Ayarları
THEMES = {
    "light": {
        "background": "w",
        "foreground": "k",
        "grid": "#E0E0E0",
        "candle_up": "#2E7D32",
        "candle_down": "#C62828",
    },
    "dark": {
        "background": "#1E1E1E",
        "foreground": "w",
        "grid": "#424242",
        "candle_up": "#4CAF50",
        "candle_down": "#F44336",
    }
}

CURRENT_THEME = "light"

EMA_CONFIG = {
    "EMA9":   dict(period=9,   color="#FF9800", width=1.3, style=Qt.DashLine),
    "EMA20":  dict(period=20,  color="#FF5722", width=1.6, style=Qt.DashLine),
    "EMA50":  dict(period=50,  color="#2196F3", width=2.0, style=Qt.SolidLine),
    "EMA200": dict(period=200, color="#9C27B0", width=2.4, style=Qt.SolidLine),
}

# ---------------------------------------------------------------------
# PATTERN RECOGNITION WITH TOOLTIPS
# ---------------------------------------------------------------------
class PatternScatterItem(pg.ScatterPlotItem):
    """Tooltip'li pattern scatter item"""
    def __init__(self, pattern_name, pattern_description, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pattern_name = pattern_name
        self.pattern_description = pattern_description
        self.setToolTip(f"{pattern_name}\n{pattern_description}")

class PatternRecognizer:
    PATTERN_DESCRIPTIONS = {
        "hammer": "Çekiç - Güçlü yükseliş sinyali\nAlt direnç noktasında görülür",
        "shooting_star": "Düşen Yıldız - Güçlü düşüş sinyali\nÜst direnç noktasında görülür",
        "engulfing_bullish": "Yutan Boğa - Güçlü yükseliş\nÖnceki mumu tamamen yutar",
        "engulfing_bearish": "Yutan Ayı - Güçlü düşüş\nÖnceki mumu tamamen yutar",
        "doji": "Doji - Kararsızlık\nAlıcı satıcı dengesi",
        "morning_star": "Sabah Yıldızı - Yükseliş dönüşü\n3 mumluk formasyon",
        "evening_star": "Akşam Yıldızı - Düşüş dönüşü\n3 mumluk formasyon"
    }
    
    @staticmethod
    def detect_patterns(df: pd.DataFrame) -> dict:
        """Mum çubuğu pattern'lerini tespit et"""
        
        if not TALIB_AVAILABLE:  # ✅ Kontrol ekle
            return {
                "hammer": [], "shooting_star": [], "engulfing_bullish": [],
                "engulfing_bearish": [], "doji": [], "morning_star": [], "evening_star": []
            }
        
        patterns = {
            "hammer": [],
            "shooting_star": [],
            "engulfing_bullish": [],
            "engulfing_bearish": [],
            "doji": [],
            "morning_star": [],
            "evening_star": []
        }
        
        o = df["open"].values
        h = df["high"].values
        l = df["low"].values
        c = df["close"].values
        
        patterns["hammer"] = [(i, c[i]) for i in np.where(talib.CDLHAMMER(o, h, l, c) != 0)[0]]
        patterns["shooting_star"] = [(i, c[i]) for i in np.where(talib.CDLSHOOTINGSTAR(o, h, l, c) != 0)[0]]
        patterns["engulfing_bullish"] = [(i, c[i]) for i in np.where(talib.CDLENGULFING(o, h, l, c) > 0)[0]]
        patterns["engulfing_bearish"] = [(i, c[i]) for i in np.where(talib.CDLENGULFING(o, h, l, c) < 0)[0]]
        patterns["doji"] = [(i, c[i]) for i in np.where(talib.CDLDOJI(o, h, l, c) != 0)[0]]
        patterns["morning_star"] = [(i, c[i]) for i in np.where(talib.CDLMORNINGSTAR(o, h, l, c) != 0)[0]]
        patterns["evening_star"] = [(i, c[i]) for i in np.where(talib.CDLEVENINGSTAR(o, h, l, c) != 0)[0]]
        
        return patterns

# ---------------------------------------------------------------------
# VOLUME PROFILE
# ---------------------------------------------------------------------
class VolumeProfile:
    @staticmethod
    def calculate(df: pd.DataFrame, num_bins: int = 50):
        """Volume Profile hesapla - POC, VAH, VAL"""
        prices = df["close"].values
        volumes = df["volume"].values
        
        price_min, price_max = prices.min(), prices.max()
        bins = np.linspace(price_min, price_max, num_bins)
        
        volume_at_price = np.zeros(num_bins - 1)
        
        for i in range(len(prices)):
            bin_idx = np.digitize(prices[i], bins) - 1
            if 0 <= bin_idx < len(volume_at_price):
                volume_at_price[bin_idx] += volumes[i]
        
        # POC (Point of Control) - En yüksek volume
        poc_idx = np.argmax(volume_at_price)
        poc_price = (bins[poc_idx] + bins[poc_idx + 1]) / 2
        
        # Value Area (70% of volume)
        total_vol = volume_at_price.sum()
        target_vol = total_vol * 0.70
        
        sorted_indices = np.argsort(volume_at_price)[::-1]
        cumulative = 0
        value_area_indices = []
        
        for idx in sorted_indices:
            cumulative += volume_at_price[idx]
            value_area_indices.append(idx)
            if cumulative >= target_vol:
                break
        
        vah = bins[max(value_area_indices) + 1]  # Value Area High
        val = bins[min(value_area_indices)]      # Value Area Low
        
        return {
            "bins": bins,
            "volume_at_price": volume_at_price,
            "poc": poc_price,
            "vah": vah,
            "val": val
        }

# ---------------------------------------------------------------------
# PRICE ALERTS
# ---------------------------------------------------------------------
class PriceAlert:
    def __init__(self):
        self.alerts = []
        
    def add_alert(self, price: float, alert_type: str, message: str):
        """Fiyat alarmı ekle"""
        self.alerts.append({
            "price": price,
            "type": alert_type,  # "above" or "below"
            "message": message,
            "triggered": False
        })
    
    def check_alerts(self, current_price: float):
        """Alarmları kontrol et"""
        triggered = []
        for alert in self.alerts:
            if alert["triggered"]:
                continue
                
            if alert["type"] == "above" and current_price >= alert["price"]:
                alert["triggered"] = True
                triggered.append(alert)
            elif alert["type"] == "below" and current_price <= alert["price"]:
                alert["triggered"] = True
                triggered.append(alert)
        
        return triggered
    
    def clear_alerts(self):
        self.alerts = []

# ---------------------------------------------------------------------
# MEASURE TOOL (INTERACTIVE)
# ---------------------------------------------------------------------
class MeasureTool:
    def __init__(self, plot_widget, parent_dialog):
        self.plot = plot_widget
        self.parent = parent_dialog
        self.line = None
        self.label = None
        self.is_active = False
        self.points = []
        self.proxy = None
        
    def activate(self):
        """Ölçüm modunu aktifleştir"""
        self.is_active = True
        self.clear()
        self.points = []
        
        # Mouse click event'i dinle
        self.proxy = pg.SignalProxy(
            self.plot.scene().sigMouseClicked,
            rateLimit=60,
            slot=self.on_click
        )
        
        QMessageBox.information(
            self.parent,
            "📏 Ölçüm Modu Aktif",
            "Grafik üzerinde 2 nokta seçin:\n"
            "1. Başlangıç noktası\n"
            "2. Bitiş noktası\n\n"
            "Ölçüm otomatik hesaplanacak."
        )
    
    def on_click(self, evt):
        """Mouse tıklama olayını yakala"""
        if not self.is_active:
            return
            
        click_event = evt[0]
        if click_event.button() == Qt.LeftButton:
            pos = click_event.scenePos()
            if self.plot.sceneBoundingRect().contains(pos):
                mouse_point = self.plot.vb.mapSceneToView(pos)
                x, y = mouse_point.x(), mouse_point.y()
                
                self.points.append((x, y))
                
                if len(self.points) == 2:
                    self.draw(self.points[0][0], self.points[0][1], 
                             self.points[1][0], self.points[1][1])
                    self.is_active = False
                    if self.proxy:
                        self.proxy.disconnect()
        
    def clear(self):
        if self.line:
            self.plot.removeItem(self.line)
        if self.label:
            self.plot.removeItem(self.label)
        self.line = None
        self.label = None
        self.points = []
    
    def draw(self, x1, y1, x2, y2):
        """İki nokta arası ölçüm çiz"""
        self.clear()
        
        # Çizgi
        self.line = pg.PlotDataItem(
            [x1, x2], [y1, y2],
            pen=pg.mkPen("#FF5722", width=3, style=Qt.SolidLine)
        )
        self.plot.addItem(self.line)
        
        # Hesaplamalar
        price_diff = abs(y2 - y1)
        percent_change = (price_diff / min(y1, y2)) * 100
        bar_count = abs(int(x2 - x1))
        
        # Etiket
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        
        text = f"📏 ÖLÇÜM\n"
        text += f"Fiyat Farkı: {price_diff:.2f}\n"
        text += f"Değişim: {percent_change:.2f}%\n"
        text += f"Bar: {bar_count}"
        
        self.label = pg.TextItem(
            text=text,
            anchor=(0.5, 0.5),
            color='k',
            fill=pg.mkBrush(255, 152, 0, 220),
            border=pg.mkPen("#FF5722", width=3)
        )
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setPos(mid_x, mid_y)
        self.plot.addItem(self.label)

# ---------------------------------------------------------------------
# TREND LINE TOOL (INTERACTIVE)
# ---------------------------------------------------------------------
class TrendLineTool:
    def __init__(self, plot_widget, parent_dialog):
        self.plot = plot_widget
        self.parent = parent_dialog
        self.lines = []
        self.is_active = False
        self.points = []
        self.proxy = None
        
    def activate(self):
        """Trend çizgisi modunu aktifleştir"""
        self.is_active = True
        self.points = []
        
        # Mouse click event'i dinle
        self.proxy = pg.SignalProxy(
            self.plot.scene().sigMouseClicked,
            rateLimit=60,
            slot=self.on_click
        )
        
        QMessageBox.information(
            self.parent,
            "📈 Trend Çizgisi Modu",
            "Grafik üzerinde 2 nokta seçin:\n"
            "1. Başlangıç noktası\n"
            "2. Bitiş noktası\n\n"
            "Trend çizgisi oluşturulacak.\n"
            "Yeşil = Yükseliş, Kırmızı = Düşüş"
        )
    
    def on_click(self, evt):
        """Mouse tıklama olayını yakala"""
        if not self.is_active:
            return
            
        click_event = evt[0]
        if click_event.button() == Qt.LeftButton:
            pos = click_event.scenePos()
            if self.plot.sceneBoundingRect().contains(pos):
                mouse_point = self.plot.vb.mapSceneToView(pos)
                x, y = mouse_point.x(), mouse_point.y()
                
                self.points.append((x, y))
                
                # İlk nokta işareti
                if len(self.points) == 1:
                    marker = pg.ScatterPlotItem(
                        x=[x], y=[y],
                        size=10,
                        pen=pg.mkPen(None),
                        brush=pg.mkBrush(33, 150, 243, 200),
                        symbol='o'
                    )
                    self.plot.addItem(marker)
                    self.lines.append(marker)
                
                # İki nokta seçildi, çizgiyi çiz
                elif len(self.points) == 2:
                    x1, y1 = self.points[0]
                    x2, y2 = self.points[1]
                    
                    # Trend yönüne göre renk
                    color = "#4CAF50" if y2 > y1 else "#F44336"
                    
                    self.add_line(x1, y1, x2, y2, color)
                    self.is_active = False
                    self.points = []
                    if self.proxy:
                        self.proxy.disconnect()
                    
                    QMessageBox.information(
                        self.parent,
                        "✅ Trend Çizgisi Eklendi",
                        "Trend çizgisi başarıyla eklendi.\n\n"
                        "Yeni çizgi eklemek için tekrar 'Trend Çizgisi' butonuna tıklayın.\n"
                        "Silmek için 'Trend Sil' butonlarını kullanın."
                    )
    
    def add_line(self, x1, y1, x2, y2, color="#2196F3"):
        """Trend çizgisi ekle"""
        line = pg.PlotDataItem(
            [x1, x2], [y1, y2],
            pen=pg.mkPen(color, width=3)
        )
        self.plot.addItem(line)
        self.lines.append(line)
        return line
    
    def clear_all(self):
        """Tüm trend çizgilerini sil"""
        for line in self.lines:
            self.plot.removeItem(line)
        self.lines = []
        self.points = []
    
    def remove_last(self):
        """Son trend çizgisini sil"""
        if self.lines:
            line = self.lines.pop()
            self.plot.removeItem(line)

# ---------------------------------------------------------------------
# INDICATOR CALCULATOR
# ---------------------------------------------------------------------
class IndicatorCalculator:
    @staticmethod
    def validate_df(df: pd.DataFrame):
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Eksik kolonlar: {missing}")
        
        if df[list(REQUIRED_COLUMNS)].isnull().any().any():
            raise ValueError("Veri setinde NaN değerler var!")
        
        if np.isinf(df[list(REQUIRED_COLUMNS)].values).any():
            raise ValueError("Veri setinde Inf değerler var!")
        
        if len(df) < 200:
            raise ValueError("EMA200 için en az 200 bar veri gerekli!")

    @staticmethod
    def calculate(df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values

        for name, cfg in EMA_CONFIG.items():
            df[name] = talib.EMA(close, timeperiod=cfg["period"])

        df["BB_Upper"], df["BB_Middle"], df["BB_Lower"] = talib.BBANDS(
            close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )

        df["RSI"] = talib.RSI(close, timeperiod=14)
        df["RSI_MA"] = talib.EMA(df["RSI"], timeperiod=9)

        macd, signal, hist = talib.MACD(close, 12, 26, 9)
        df["MACD"] = macd
        df["MACD_Signal"] = signal
        df["MACD_Hist"] = hist

        df["VMA20"] = talib.SMA(volume, timeperiod=20)
        df["VMA50"] = talib.SMA(volume, timeperiod=50)

        df["ATR"] = talib.ATR(high, low, close, timeperiod=14)

        df["STOCH_K"], df["STOCH_D"] = talib.STOCH(
            high, low, close, 
            fastk_period=14, slowk_period=3, slowd_period=3
        )

        df["ADX"] = talib.ADX(high, low, close, timeperiod=14)

        return df

    @staticmethod
    def detect_signals(df: pd.DataFrame) -> dict:
        signals = {
            "buy": [],
            "sell": [],
            "support": [],
            "resistance": []
        }
        
        close = df["close"].values
        rsi = df["RSI"].values
        macd = df["MACD"].values
        macd_signal = df["MACD_Signal"].values
        
        for i in range(50, len(df)):
            if (rsi[i] < 35 and rsi[i-1] >= 35 and 
                macd[i] > macd_signal[i] and macd[i-1] <= macd_signal[i-1]):
                signals["buy"].append((i, close[i]))
            
            if (rsi[i] > 65 and rsi[i-1] <= 65 and 
                macd[i] < macd_signal[i] and macd[i-1] >= macd_signal[i-1]):
                signals["sell"].append((i, close[i]))
        
        signals["support"] = IndicatorCalculator._find_support_resistance(df, "support")
        signals["resistance"] = IndicatorCalculator._find_support_resistance(df, "resistance")
        
        return signals

    @staticmethod
    def _find_support_resistance(df: pd.DataFrame, sr_type: str) -> list:
        close = df["close"].values
        levels = []
        window = 20
        
        for i in range(window, len(close) - window):
            if sr_type == "support":
                if close[i] == min(close[i-window:i+window]):
                    levels.append(close[i])
            else:
                if close[i] == max(close[i-window:i+window]):
                    levels.append(close[i])
        
        if levels:
            levels = sorted(set(levels))
            merged = [levels[0]]
            for level in levels[1:]:
                if abs(level - merged[-1]) / merged[-1] > 0.02:
                    merged.append(level)
            return merged
        return []

# ---------------------------------------------------------------------
# CANDLESTICK ITEM
# ---------------------------------------------------------------------
class CandlestickItem(pg.GraphicsObject):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.picture = None
        self._generate_picture()

    def _generate_picture(self):
        self.picture = pg.QtGui.QPicture()
        painter = pg.QtGui.QPainter(self.picture)

        theme = THEMES[CURRENT_THEME]

        for i in range(len(self.data)):
            o, h, l, c = map(float, self.data[i])
            up = c >= o
            color = QColor(theme["candle_up"] if up else theme["candle_down"])

            painter.setPen(pg.mkPen(color, width=1))
            painter.drawLine(QPointF(i, l), QPointF(i, h))

            painter.setBrush(QBrush(color))
            painter.drawRect(QRectF(i - 0.35, min(o, c), 0.7, abs(c - o) or 0.1))

        painter.end()

    def paint(self, painter, *args):
        painter.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QRectF(self.picture.boundingRect())

    def setData(self, data):
        self.data = data
        self._generate_picture()
        self.update()

# ---------------------------------------------------------------------
# CROSSHAIR CURSOR
# ---------------------------------------------------------------------
class CrosshairCursor:
    def __init__(self, plot_widget, df):
        self.plot = plot_widget
        self.df = df
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#666", width=1, style=Qt.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen("#666", width=1, style=Qt.DashLine))
        self.plot.addItem(self.vLine, ignoreBounds=True)
        self.plot.addItem(self.hLine, ignoreBounds=True)
        
        self.label = pg.TextItem(anchor=(0, 1), color="#000", fill="#FFFFCC")
        self.plot.addItem(self.label)
        
        self.proxy = pg.SignalProxy(
            self.plot.scene().sigMouseMoved, 
            rateLimit=60, 
            slot=self.mouse_moved
        )

    def mouse_moved(self, evt):
        pos = evt[0]
        if self.plot.sceneBoundingRect().contains(pos):
            mouse_point = self.plot.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()
            
            self.vLine.setPos(x)
            self.hLine.setPos(y)
            
            idx = int(x)
            if 0 <= idx < len(self.df):
                row = self.df.iloc[idx]
                date_str = row.get('date', idx)
                if isinstance(date_str, pd.Timestamp):
                    date_str = date_str.strftime('%Y-%m-%d')
                
                text = f"📅 {date_str}\n"
                text += f"O: {row['open']:.2f} H: {row['high']:.2f}\n"
                text += f"L: {row['low']:.2f} C: {row['close']:.2f}\n"
                text += f"Vol: {row['volume']:,.0f}"
                
                if 'RSI' in row and not pd.isna(row['RSI']):
                    text += f"\n📊 RSI: {row['RSI']:.1f}"
                if 'MACD' in row and not pd.isna(row['MACD']):
                    text += f"\n📈 MACD: {row['MACD']:.2f}"
                
                self.label.setText(text)
                self.label.setPos(x, y)

# ---------------------------------------------------------------------
# FIBONACCI TOOL (WITH MANUAL MODE)
# ---------------------------------------------------------------------
class FibonacciTool:
    def __init__(self, plot_widget, parent_dialog):
        self.plot = plot_widget
        self.parent = parent_dialog
        self.lines = []
        self.labels = []
        self.is_manual_mode = False
        self.points = []
        self.proxy = None
        
        self.levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]
        self.colors = ["#F44336", "#FF9800", "#FFEB3B", "#4CAF50", "#2196F3", "#9C27B0", "#E91E63"]
        self.level_names = ["0%", "23.6%", "38.2%", "50%", "61.8%", "78.6%", "100%"]

    def activate_manual(self):
        """Manuel Fibonacci modunu aktifleştir"""
        self.is_manual_mode = True
        self.points = []
        self.clear()
        
        # Mouse click event'i dinle
        self.proxy = pg.SignalProxy(
            self.plot.scene().sigMouseClicked,
            rateLimit=60,
            slot=self.on_click
        )
        
        QMessageBox.information(
            self.parent,
            "📐 Manuel Fibonacci Modu",
            "Grafik üzerinde 2 nokta seçin:\n\n"
            "1. Düşük nokta (swing low)\n"
            "2. Yüksek nokta (swing high)\n\n"
            "Fibonacci seviyeleri otomatik hesaplanacak."
        )
    
    def on_click(self, evt):
        """Mouse tıklama olayını yakala"""
        if not self.is_manual_mode:
            return
            
        click_event = evt[0]
        if click_event.button() == Qt.LeftButton:
            pos = click_event.scenePos()
            if self.plot.sceneBoundingRect().contains(pos):
                mouse_point = self.plot.vb.mapSceneToView(pos)
                x, y = mouse_point.x(), mouse_point.y()
                
                self.points.append((x, y))
                
                # İlk nokta işareti
                if len(self.points) == 1:
                    marker = pg.ScatterPlotItem(
                        x=[x], y=[y],
                        size=12,
                        pen=pg.mkPen(None),
                        brush=pg.mkBrush(244, 67, 54, 220),
                        symbol='o'
                    )
                    self.plot.addItem(marker)
                    self.labels.append(marker)
                
                # İki nokta seçildi, fibonacci çiz
                elif len(self.points) == 2:
                    y1 = self.points[0][1]
                    y2 = self.points[1][1]
                    
                    # Düşükten yükseğe doğru sırala
                    start_y = min(y1, y2)
                    end_y = max(y1, y2)
                    
                    self.draw(start_y, end_y)
                    self.is_manual_mode = False
                    self.points = []
                    if self.proxy:
                        self.proxy.disconnect()
                    
                    QMessageBox.information(
                        self.parent,
                        "✅ Fibonacci Çizildi",
                        f"Manuel Fibonacci seviyeleri oluşturuldu.\n\n"
                        f"🔻 Düşük: {start_y:.2f}\n"
                        f"🔺 Yüksek: {end_y:.2f}\n\n"
                        f"Silmek için '🗑️ Fib Sil' butonunu kullanın."
                    )

    def clear(self):
        for line in self.lines:
            self.plot.removeItem(line)
        for label in self.labels:
            self.plot.removeItem(label)
        self.lines = []
        self.labels = []

    def draw(self, start_y, end_y):
        self.clear()
        diff = end_y - start_y
        
        for level, color, name in zip(self.levels, self.colors, self.level_names):
            price = start_y + (diff * level)
            
            line = pg.InfiniteLine(
                angle=0, 
                pos=price,
                pen=pg.mkPen(color, width=2.5, style=Qt.DashLine)
            )
            self.plot.addItem(line)
            self.lines.append(line)
            
            label = pg.TextItem(
                text=f"  FIB {name} = {price:.2f}",
                anchor=(0, 0.5),
                color='k',
                fill=pg.mkBrush(color + '90'),
                border=pg.mkPen(color, width=2)
            )
            font = QFont()
            font.setPointSize(11)
            font.setBold(True)
            label.setFont(font)
            label.setPos(0, price)
            
            self.plot.addItem(label)
            self.labels.append(label)
    
    def is_visible(self):
        return len(self.lines) > 0

# ---------------------------------------------------------------------
# INDICATOR PANEL
# ---------------------------------------------------------------------
class IndicatorPanel(QWidget):
    indicator_toggled = pyqtSignal(str, bool)
    
    def __init__(self):
        super().__init__()
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Fiyat Göstergeleri
        price_group = QGroupBox("💰 Fiyat Göstergeleri")
        price_layout = QVBoxLayout()
        
        self.indicators = {}
        
        price_indicators = [
            ("EMA9", "EMA 9", True),
            ("EMA20", "EMA 20", True),
            ("EMA50", "EMA 50", True),
            ("EMA200", "EMA 200", True),
            ("BB", "Bollinger Bands", True),
            ("VOLUME_PROFILE", "Volume Profile", False),
        ]
        
        for key, label, default in price_indicators:
            cb = QCheckBox(label)
            cb.setChecked(default)
            cb.stateChanged.connect(lambda state, k=key: self.indicator_toggled.emit(k, state == Qt.Checked))
            price_layout.addWidget(cb)
            self.indicators[key] = cb
        
        price_group.setLayout(price_layout)
        layout.addWidget(price_group)
        
        # Momentum Göstergeleri
        momentum_group = QGroupBox("📊 Momentum")
        momentum_layout = QVBoxLayout()
        
        momentum_indicators = [
            ("RSI", "RSI", True),
            ("MACD", "MACD", True),
            ("STOCH", "Stochastic", False),
            ("ADX", "ADX", False),
        ]
        
        for key, label, default in momentum_indicators:
            cb = QCheckBox(label)
            cb.setChecked(default)
            cb.stateChanged.connect(lambda state, k=key: self.indicator_toggled.emit(k, state == Qt.Checked))
            momentum_layout.addWidget(cb)
            self.indicators[key] = cb
        
        momentum_group.setLayout(momentum_layout)
        layout.addWidget(momentum_group)
        
        # Sinyaller
        signals_group = QGroupBox("🎯 Sinyaller & Pattern")
        signals_layout = QVBoxLayout()
        
        signals_indicators = [
            ("BUY_SIGNALS", "Alım Sinyalleri", True),
            ("SELL_SIGNALS", "Satım Sinyalleri", True),
            ("SUPPORT", "Support", True),
            ("RESISTANCE", "Resistance", True),
            ("PATTERNS", "Mum Pattern'leri", True),
        ]
        
        for key, label, default in signals_indicators:
            cb = QCheckBox(label)
            cb.setChecked(default)
            cb.stateChanged.connect(lambda state, k=key: self.indicator_toggled.emit(k, state == Qt.Checked))
            signals_layout.addWidget(cb)
            self.indicators[key] = cb
        
        signals_group.setLayout(signals_layout)
        layout.addWidget(signals_group)
        
        layout.addStretch()

# ---------------------------------------------------------------------
# MAIN CHART DIALOG
# ---------------------------------------------------------------------
class SwingTradeChart(QDialog):
    def __init__(self, df: pd.DataFrame, symbol: str, trade_info: dict | None = None):
        super().__init__()

        self.symbol = symbol
        self.trade_info = trade_info or {}
        self.df = df.copy().reset_index(drop=True)
        
        if 'date' not in self.df.columns:
            self.df['date'] = pd.date_range(end=datetime.now(), periods=len(self.df), freq='D')

        try:
            IndicatorCalculator.validate_df(self.df)
        except ValueError as e:
            QMessageBox.critical(self, "Veri Hatası", str(e))
            self.reject()
            return

        progress = QProgressDialog("Göstergeler hesaplanıyor...", None, 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(20)

        self.df = IndicatorCalculator.calculate(self.df)
        progress.setValue(40)
        
        self.signals = IndicatorCalculator.detect_signals(self.df)
        progress.setValue(60)
        
        self.patterns = PatternRecognizer.detect_patterns(self.df)
        progress.setValue(80)
        
        self.volume_profile_data = VolumeProfile.calculate(self.df)
        progress.setValue(90)

        self.price_alerts = PriceAlert()
        
        self._build_ui()
        self._build_plots()
        
        progress.setValue(100)
        progress.close()

    def _build_ui(self):
        self.setWindowTitle(f"🚀 {self.symbol} - Ultimate Trading Chart")
        self.resize(1800, 1000)

        main_layout = QHBoxLayout(self)
        
        # Sol Panel
        left_panel = QScrollArea()
        left_panel.setWidgetResizable(True)
        left_panel.setMaximumWidth(250)
        
        self.indicator_panel = IndicatorPanel()
        self.indicator_panel.indicator_toggled.connect(self.toggle_indicator)
        left_panel.setWidget(self.indicator_panel)
        
        main_layout.addWidget(left_panel)
        
        # Sağ Panel
        right_layout = QVBoxLayout()
        
        # Üst Kontroller - 2 satır
        controls1 = QHBoxLayout()
        controls2 = QHBoxLayout()
        
        # İlk Satır
        self.btn_fibonacci = QPushButton("📐 Fibonacci (Otomatik)")
        self.btn_fib_manual = QPushButton("✏️ Fibonacci (Manuel)")
        self.btn_fib_clear = QPushButton("🗑️ Fib Sil")
        self.btn_measure = QPushButton("📏 Ölçüm")
        self.btn_trend = QPushButton("📈 Trend Çizgisi")
        
        for b in (self.btn_fibonacci, self.btn_fib_manual, self.btn_fib_clear, self.btn_measure, self.btn_trend):
            controls1.addWidget(b)
        
        # İkinci Satır
        self.btn_trend_clear = QPushButton("🗑️ Trend Sil")
        self.btn_alert = QPushButton("🔔 Alarm")
        self.btn_theme = QPushButton("🌓 Tema")
        self.btn_reset_zoom = QPushButton("🔍 Zoom")
        self.btn_snapshot = QPushButton("📸 Snapshot")
        self.btn_export = QPushButton("💾 Export")
        self.btn_stats = QPushButton("📊 İstatistik")
        self.btn_close = QPushButton("❌ Kapat")

        for b in (self.btn_trend_clear, self.btn_alert, self.btn_theme, self.btn_reset_zoom, 
                  self.btn_snapshot, self.btn_export, self.btn_stats):
            controls2.addWidget(b)
        
        controls2.addStretch()
        controls2.addWidget(self.btn_close)

        # Event connections
        self.btn_close.clicked.connect(self.accept)
        self.btn_fibonacci.clicked.connect(self.activate_fibonacci_auto)
        self.btn_fib_manual.clicked.connect(self.activate_fibonacci_manual)
        self.btn_fib_clear.clicked.connect(self.clear_fibonacci)
        self.btn_measure.clicked.connect(self.activate_measure_tool)
        self.btn_trend.clicked.connect(self.activate_trend_tool)
        self.btn_trend_clear.clicked.connect(self.clear_trend_lines)
        self.btn_alert.clicked.connect(self.add_price_alert)
        self.btn_theme.clicked.connect(self.toggle_theme)
        self.btn_reset_zoom.clicked.connect(self.reset_zoom)
        self.btn_snapshot.clicked.connect(self.take_snapshot)
        self.btn_export.clicked.connect(self.export_chart)
        self.btn_stats.clicked.connect(self.show_statistics)

        right_layout.addLayout(controls1)
        right_layout.addLayout(controls2)

        self.graph = pg.GraphicsLayoutWidget()
        right_layout.addWidget(self.graph)

        main_layout.addLayout(right_layout, stretch=1)

    def _build_plots(self):
        df = self.df
        x = np.arange(len(df))

        # === PRICE ===
        self.price_plot = self.graph.addPlot(title=f"🚀 {self.symbol} - Fiyat Grafiği")
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)
        self.price_plot.setLabel('left', 'Fiyat', units='₺')
        self.price_plot.setLabel('bottom', 'Bar Index')

        ohlc = df[["open", "high", "low", "close"]].values
        self.candles = CandlestickItem(ohlc)
        self.price_plot.addItem(self.candles)

        # EMA
        self.ema_items = {}
        for name, cfg in EMA_CONFIG.items():
            line = self.price_plot.plot(
                x, df[name],
                pen=pg.mkPen(cfg["color"], width=cfg["width"], style=cfg["style"]),
                name=name
            )
            self.ema_items[name] = line

        # Bollinger Bands
        self.bb_upper = self.price_plot.plot(x, df["BB_Upper"], pen=pg.mkPen("#2196F3", width=1, style=Qt.DashLine))
        self.bb_middle = self.price_plot.plot(x, df["BB_Middle"], pen=pg.mkPen("#9E9E9E", width=1))
        self.bb_lower = self.price_plot.plot(x, df["BB_Lower"], pen=pg.mkPen("#2196F3", width=1, style=Qt.DashLine))
        
        self.bb_fill = pg.FillBetweenItem(self.bb_upper, self.bb_lower, brush=pg.mkBrush(33, 150, 243, 30))
        self.price_plot.addItem(self.bb_fill)

        # Trade Signals
        self.buy_scatter = pg.ScatterPlotItem(size=14, pen=pg.mkPen(None), brush=pg.mkBrush(46, 125, 50, 220), symbol='t1')
        self.sell_scatter = pg.ScatterPlotItem(size=14, pen=pg.mkPen(None), brush=pg.mkBrush(198, 40, 40, 220), symbol='t')
        self.price_plot.addItem(self.buy_scatter)
        self.price_plot.addItem(self.sell_scatter)
        
        if self.signals["buy"]:
            buy_x = [s[0] for s in self.signals["buy"]]
            buy_y = [s[1] for s in self.signals["buy"]]
            self.buy_scatter.setData(x=buy_x, y=buy_y)
        
        if self.signals["sell"]:
            sell_x = [s[0] for s in self.signals["sell"]]
            sell_y = [s[1] for s in self.signals["sell"]]
            self.sell_scatter.setData(x=sell_x, y=sell_y)

        # Pattern Markers with Tooltips
        self.pattern_scatters = {}
        pattern_config = {
            "hammer": (10, 'o', '#4CAF50', 180),
            "shooting_star": (10, 'o', '#F44336', 180),
            "engulfing_bullish": (12, 's', '#2E7D32', 150),
            "engulfing_bearish": (12, 's', '#C62828', 150),
            "doji": (8, 'd', '#FF9800', 150),
            "morning_star": (14, 'star', '#00BCD4', 200),
            "evening_star": (14, 'star', '#E91E63', 200)
        }
        
        for pattern_name, (size, symbol, color, alpha) in pattern_config.items():
            if self.patterns[pattern_name]:
                # Her pattern için text item'lar oluştur
                for px, py in self.patterns[pattern_name]:
                    # Pattern marker
                    scatter = pg.ScatterPlotItem(
                        x=[px], 
                        y=[py],
                        size=size, 
                        pen=pg.mkPen(None), 
                        brush=pg.mkBrush(QColor(color).red(), QColor(color).green(), QColor(color).blue(), alpha),
                        symbol=symbol
                    )
                    self.price_plot.addItem(scatter)
                    
                    # Pattern label (hover için)
                    pattern_label = pg.TextItem(
                        text=f"{pattern_name.replace('_', ' ').title()}",
                        anchor=(0.5, 1.2),
                        color='k',
                        fill=pg.mkBrush(color + '80'),
                        border=pg.mkPen(color, width=1)
                    )
                    font = QFont()
                    font.setPointSize(8)
                    font.setBold(True)
                    pattern_label.setFont(font)
                    pattern_label.setPos(px, py)
                    self.price_plot.addItem(pattern_label)
                    
                    if pattern_name not in self.pattern_scatters:
                        self.pattern_scatters[pattern_name] = []
                    self.pattern_scatters[pattern_name].append((scatter, pattern_label))

        # Support/Resistance
        self.support_lines = []
        self.resistance_lines = []
        
        for level in self.signals["support"]:
            line = self.price_plot.addLine(y=level, pen=pg.mkPen("#4CAF50", width=1.5, style=Qt.DashLine))
            self.support_lines.append(line)
        
        for level in self.signals["resistance"]:
            line = self.price_plot.addLine(y=level, pen=pg.mkPen("#F44336", width=1.5, style=Qt.DashLine))
            self.resistance_lines.append(line)

        # Volume Profile
        self.volume_profile_items = []
        vp = self.volume_profile_data
        
        max_vol = vp["volume_at_price"].max()
        scale_factor = (x[-1] - x[0]) * 0.15 / max_vol
        
        for i, vol in enumerate(vp["volume_at_price"]):
            y_pos = (vp["bins"][i] + vp["bins"][i+1]) / 2
            width = vol * scale_factor
            
            rect = pg.BarGraphItem(
                x=[x[-1] + 5], 
                height=[(vp["bins"][i+1] - vp["bins"][i])],
                width=width,
                y=[vp["bins"][i]],
                brush=pg.mkBrush(33, 150, 243, 80)
            )
            self.price_plot.addItem(rect)
            self.volume_profile_items.append(rect)
        
        # POC, VAH, VAL lines
        self.poc_line = self.price_plot.addLine(y=vp["poc"], pen=pg.mkPen("#FF9800", width=2.5, style=Qt.SolidLine))
        self.vah_line = self.price_plot.addLine(y=vp["vah"], pen=pg.mkPen("#4CAF50", width=2, style=Qt.DotLine))
        self.val_line = self.price_plot.addLine(y=vp["val"], pen=pg.mkPen("#F44336", width=2, style=Qt.DotLine))
        
        # Hide volume profile by default
        for item in self.volume_profile_items:
            item.setVisible(False)
        self.poc_line.setVisible(False)
        self.vah_line.setVisible(False)
        self.val_line.setVisible(False)

        if "stop_loss" in self.trade_info:
            self.price_plot.addLine(y=self.trade_info["stop_loss"], pen=pg.mkPen("#D32F2F", width=2, style=Qt.SolidLine))

        # Tools
        self.crosshair = CrosshairCursor(self.price_plot, df)
        self.fibonacci = FibonacciTool(self.price_plot, self)
        self.measure_tool = MeasureTool(self.price_plot, self)
        self.trend_tool = TrendLineTool(self.price_plot, self)

        # === VOLUME ===
        self.graph.nextRow()
        self.volume_plot = self.graph.addPlot(title="📊 Hacim")
        self.volume_plot.setMaximumHeight(150)
        self.volume_plot.setLabel('left', 'Hacim')

        colors = np.where(df["close"] >= df["open"], "#2E7D32", "#C62828")
        self.volume_bars = pg.BarGraphItem(x=x, height=df["volume"], width=0.8, brushes=colors)
        self.volume_plot.addItem(self.volume_bars)

        self.vma20 = self.volume_plot.plot(x, df["VMA20"], pen=pg.mkPen("#2196F3", width=1.5))
        self.vma50 = self.volume_plot.plot(x, df["VMA50"], pen=pg.mkPen("#9C27B0", width=1.5))

        # === RSI ===
        self.graph.nextRow()
        self.rsi_plot = self.graph.addPlot(title="📈 RSI (14)")
        self.rsi_plot.setYRange(0, 100)
        self.rsi_plot.setLabel('left', 'RSI')
        
        self.rsi_line = self.rsi_plot.plot(x, df["RSI"], pen=pg.mkPen("#673AB7", width=2))
        self.rsi_ma = self.rsi_plot.plot(x, df["RSI_MA"], pen=pg.mkPen("#FF9800", width=1.5, style=Qt.DashLine))

        for lvl, color in [(70, "#F44336"), (50, "#9E9E9E"), (30, "#4CAF50")]:
            self.rsi_plot.addLine(y=lvl, pen=pg.mkPen(color, style=Qt.DashLine))

        # === MACD ===
        self.graph.nextRow()
        self.macd_plot = self.graph.addPlot(title="📉 MACD (12,26,9)")
        self.macd_plot.setLabel('left', 'MACD')
        
        self.macd_line = self.macd_plot.plot(x, df["MACD"], pen=pg.mkPen("#2196F3", width=2))
        self.macd_signal = self.macd_plot.plot(x, df["MACD_Signal"], pen=pg.mkPen("#FF5722", width=2))

        hist_colors = np.where(df["MACD_Hist"] >= 0, "#2E7D32", "#C62828")
        self.macd_hist = pg.BarGraphItem(x=x, height=df["MACD_Hist"], width=0.6, brushes=hist_colors)
        self.macd_plot.addItem(self.macd_hist)
        self.macd_plot.addLine(y=0, pen=pg.mkPen("#9E9E9E"))

        # === STOCHASTIC ===
        self.graph.nextRow()
        self.stoch_plot = self.graph.addPlot(title="⚡ Stochastic (14,3,3)")
        self.stoch_plot.setYRange(0, 100)
        self.stoch_plot.setLabel('left', 'Stochastic')
        
        self.stoch_k = self.stoch_plot.plot(x, df["STOCH_K"], pen=pg.mkPen("#2196F3", width=2))
        self.stoch_d = self.stoch_plot.plot(x, df["STOCH_D"], pen=pg.mkPen("#FF5722", width=2))
        
        for lvl in (20, 50, 80):
            self.stoch_plot.addLine(y=lvl, pen=pg.mkPen("#9E9E9E", style=Qt.DashLine))
        
        self.stoch_plot.hide()

        # === ADX ===
        self.graph.nextRow()
        self.adx_plot = self.graph.addPlot(title="💪 ADX (14)")
        self.adx_plot.setYRange(0, 100)
        self.adx_plot.setLabel('left', 'ADX')
        
        self.adx_line = self.adx_plot.plot(x, df["ADX"], pen=pg.mkPen("#9C27B0", width=2))
        self.adx_plot.addLine(y=25, pen=pg.mkPen("#FF9800", style=Qt.DashLine))
        self.adx_plot.hide()

        # Link X Axes
        for p in (self.volume_plot, self.rsi_plot, self.macd_plot, self.stoch_plot, self.adx_plot):
            p.setXLink(self.price_plot)

    # ============================================================
    # TOGGLE FUNCTIONS
    # ============================================================
    def toggle_indicator(self, indicator: str, visible: bool):
        if indicator.startswith("EMA"):
            if indicator in self.ema_items:
                self.ema_items[indicator].setVisible(visible)
        
        elif indicator == "BB":
            self.bb_upper.setVisible(visible)
            self.bb_middle.setVisible(visible)
            self.bb_lower.setVisible(visible)
            self.bb_fill.setVisible(visible)
        
        elif indicator == "VOLUME_PROFILE":
            for item in self.volume_profile_items:
                item.setVisible(visible)
            self.poc_line.setVisible(visible)
            self.vah_line.setVisible(visible)
            self.val_line.setVisible(visible)
        
        elif indicator == "RSI":
            self.rsi_plot.setVisible(visible)
        
        elif indicator == "MACD":
            self.macd_plot.setVisible(visible)
        
        elif indicator == "STOCH":
            self.stoch_plot.setVisible(visible)
        
        elif indicator == "ADX":
            self.adx_plot.setVisible(visible)
        
        elif indicator == "BUY_SIGNALS":
            self.buy_scatter.setVisible(visible)
        
        elif indicator == "SELL_SIGNALS":
            self.sell_scatter.setVisible(visible)
        
        elif indicator == "SUPPORT":
            for line in self.support_lines:
                line.setVisible(visible)
        
        elif indicator == "RESISTANCE":
            for line in self.resistance_lines:
                line.setVisible(visible)
        
        elif indicator == "PATTERNS":
            for items in self.pattern_scatters.values():
                if isinstance(items, list):
                    for scatter, label in items:
                        scatter.setVisible(visible)
                        label.setVisible(visible)
                else:
                    items.setVisible(visible)

    # ============================================================
    # TOOL FUNCTIONS
    # ============================================================
    def activate_fibonacci_auto(self):
        """Otomatik Fibonacci (son N bar)"""
        bars, ok = QInputDialog.getInt(self, "📐 Otomatik Fibonacci", "Kaç bar için hesaplansın?", 100, 20, 500)
        if not ok:
            return
            
        recent_data = self.df.tail(bars)
        high = recent_data["high"].max()
        low = recent_data["low"].min()
        
        self.fibonacci.draw(low, high)
        QMessageBox.information(
            self,
            "✅ Fibonacci Çizildi (Otomatik)",
            f"Son {bars} bar için Fibonacci seviyeleri çizildi.\n\n"
            f"🔺 Yüksek: {high:.2f}\n"
            f"🔻 Düşük: {low:.2f}\n\n"
            f"Manuel çizmek için '✏️ Fibonacci (Manuel)' butonunu kullanın.\n"
            f"Silmek için '🗑️ Fib Sil' butonunu kullanın."
        )
    
    def activate_fibonacci_manual(self):
        """Manuel Fibonacci - kullanıcı 2 nokta seçer"""
        self.fibonacci.activate_manual()
    
    def clear_fibonacci(self):
        if self.fibonacci.is_visible():
            self.fibonacci.clear()
            QMessageBox.information(self, "🗑️ Temizlendi", "Fibonacci seviyeleri silindi.")
        else:
            QMessageBox.information(self, "ℹ️ Bilgi", "Çizili Fibonacci bulunamadı.")

    def activate_measure_tool(self):
        """Ölçüm aracını aktifleştir - kullanıcı 2 nokta seçer"""
        self.measure_tool.activate()

    def activate_trend_tool(self):
        """Trend çizgisi aracını aktifleştir - kullanıcı 2 nokta seçer"""
        self.trend_tool.activate()
    
    def clear_trend_lines(self):
        """Trend çizgilerini temizle"""
        if self.trend_tool.lines:
            reply = QMessageBox.question(
                self,
                "🗑️ Trend Çizgilerini Sil",
                "Tüm trend çizgileri silinsin mi?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.trend_tool.clear_all()
                QMessageBox.information(self, "✅ Temizlendi", "Tüm trend çizgileri silindi.")
        else:
            QMessageBox.information(self, "ℹ️ Bilgi", "Silinecek trend çizgisi bulunamadı.")

    def add_price_alert(self):
        current_price = self.df["close"].iloc[-1]
        
        price, ok = QInputDialog.getDouble(
            self, 
            "🔔 Fiyat Alarmı", 
            f"Alarm fiyatı girin:\n(Mevcut: {current_price:.2f})",
            current_price,
            0,
            current_price * 10,
            2
        )
        
        if ok:
            alert_type = "above" if price > current_price else "below"
            self.price_alerts.add_alert(
                price,
                alert_type,
                f"Fiyat {price:.2f} seviyesine ulaştı!"
            )
            
            # Grafikte göster
            line = self.price_plot.addLine(
                y=price,
                pen=pg.mkPen("#FF9800", width=2, style=Qt.DotLine),
                label=f"⚠️ Alarm: {price:.2f}"
            )
            
            QMessageBox.information(
                self,
                "✅ Alarm Eklendi",
                f"Fiyat {price:.2f} seviyesine geldiğinde uyarılacaksınız.\n"
                f"Alarm tipi: {'Üzerinde' if alert_type == 'above' else 'Altında'}"
            )

    def toggle_theme(self):
        global CURRENT_THEME
        CURRENT_THEME = "dark" if CURRENT_THEME == "light" else "light"
        theme = THEMES[CURRENT_THEME]
        
        pg.setConfigOption("background", theme["background"])
        pg.setConfigOption("foreground", theme["foreground"])
        
        QMessageBox.information(
            self, 
            "🌓 Tema Değiştirildi", 
            f"{CURRENT_THEME.upper()} tema aktif.\nYeni grafiklerde görünecek."
        )

    def reset_zoom(self):
        self.price_plot.autoRange()
        for plot in (self.volume_plot, self.rsi_plot, self.macd_plot, self.stoch_plot, self.adx_plot):
            if plot.isVisible():
                plot.autoRange()

    def take_snapshot(self):
        QMessageBox.information(
            self,
            "📸 Snapshot",
            "Snapshot özelliği: Grafiğin anlık görüntüsünü alır ve\n"
            "daha sonra karşılaştırma için saklar.\n\n"
            "Bu özellik ileride geliştirilecek!"
        )

    def export_chart(self):
        try:
            from PyQt5.QtWidgets import QFileDialog
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Grafiği Kaydet",
                f"{self.symbol}_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                "PNG Files (*.png)"
            )
            
            if filename:
                exporter = pg.exporters.ImageExporter(self.graph.scene())
                exporter.parameters()['width'] = 1920
                exporter.export(filename)
                QMessageBox.information(self, "✅ Başarılı", f"Grafik kaydedildi:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "❌ Hata", f"Export hatası: {str(e)}")

    def show_statistics(self):
        df = self.df
        
        # İstatistikler hesapla
        current_price = df["close"].iloc[-1]
        price_change = current_price - df["close"].iloc[0]
        price_change_pct = (price_change / df["close"].iloc[0]) * 100
        
        high_52w = df["high"].max()
        low_52w = df["low"].min()
        avg_volume = df["volume"].mean()
        
        current_rsi = df["RSI"].iloc[-1]
        current_macd = df["MACD"].iloc[-1]
        current_adx = df["ADX"].iloc[-1]
        
        volatility = df["ATR"].iloc[-1]
        
        # Dialog oluştur
        dialog = QDialog(self)
        dialog.setWindowTitle(f"📊 {self.symbol} - İstatistikler")
        dialog.resize(500, 600)
        
        layout = QVBoxLayout(dialog)
        
        stats_text = f"""
<h2>📈 Fiyat Bilgileri</h2>
<p><b>Mevcut Fiyat:</b> {current_price:.2f} ₺</p>
<p><b>Değişim:</b> {price_change:+.2f} ₺ ({price_change_pct:+.2f}%)</p>
<p><b>52-Hafta Yüksek:</b> {high_52w:.2f} ₺</p>
<p><b>52-Hafta Düşük:</b> {low_52w:.2f} ₺</p>

<h2>📊 Teknik Göstergeler</h2>
<p><b>RSI (14):</b> {current_rsi:.2f} {"🔥 AŞIRI ALIM" if current_rsi > 70 else "❄️ AŞIRI SATIM" if current_rsi < 30 else "✅ Normal"}</p>
<p><b>MACD:</b> {current_macd:.2f}</p>
<p><b>ADX:</b> {current_adx:.2f} {"💪 Güçlü Trend" if current_adx > 25 else "😴 Zayıf Trend"}</p>
<p><b>ATR (Volatilite):</b> {volatility:.2f}</p>

<h2>📦 Hacim</h2>
<p><b>Ortalama Hacim:</b> {avg_volume:,.0f}</p>
<p><b>Son Hacim:</b> {df["volume"].iloc[-1]:,.0f}</p>

<h2>🎯 Sinyaller</h2>
<p><b>Alım Sinyali:</b> {len(self.signals['buy'])} adet</p>
<p><b>Satım Sinyali:</b> {len(self.signals['sell'])} adet</p>
<p><b>Support Seviyesi:</b> {len(self.signals['support'])} adet</p>
<p><b>Resistance Seviyesi:</b> {len(self.signals['resistance'])} adet</p>

<h2>🔮 Pattern'ler</h2>
<p><b>Hammer:</b> {len(self.patterns['hammer'])}</p>
<p><b>Shooting Star:</b> {len(self.patterns['shooting_star'])}</p>
<p><b>Bullish Engulfing:</b> {len(self.patterns['engulfing_bullish'])}</p>
<p><b>Bearish Engulfing:</b> {len(self.patterns['engulfing_bearish'])}</p>
<p><b>Doji:</b> {len(self.patterns['doji'])}</p>

<h2>📍 Volume Profile</h2>
<p><b>POC (Point of Control):</b> {self.volume_profile_data['poc']:.2f} ₺</p>
<p><b>Value Area High:</b> {self.volume_profile_data['vah']:.2f} ₺</p>
<p><b>Value Area Low:</b> {self.volume_profile_data['val']:.2f} ₺</p>
        """
        
        label = QLabel(stats_text)
        label.setWordWrap(True)
        layout.addWidget(label)
        
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec_()

# ---------------------------------------------------------------------
# USAGE EXAMPLE
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=500, freq='D')
    
    base_price = 100
    prices = []
    for i in range(500):
        change = np.random.randn() * 2
        base_price += change
        prices.append(base_price)
    
    test_df = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p + abs(np.random.randn() * 2) for p in prices],
        'low': [p - abs(np.random.randn() * 2) for p in prices],
        'close': [p + np.random.randn() for p in prices],
        'volume': [np.random.randint(1000000, 10000000) for _ in range(500)]
    })
    
    app = QApplication(sys.argv)
    
    trade_info = {
        'stop_loss': 95,
        'entry_price': 100,
        'target_price': 120
    }
    
    chart = SwingTradeChart(test_df, "HALKB", trade_info)
    chart.exec_()
    
    sys.exit(0)