# indicators/ta_manager.py
import pandas as pd
import numpy as np
import warnings

# TA_LIBRARY kontrolü
TA_AVAILABLE = True
try:
    from ta.momentum import RSIIndicator
    from ta.trend import MACD, ADXIndicator, EMAIndicator
    from ta.volatility import BollingerBands, AverageTrueRange
    from ta.volume import OnBalanceVolumeIndicator, ChaikinMoneyFlowIndicator, MFIIndicator
    print("✅ TA-Lib kütüphanesi yüklü")
except ImportError:
    TA_AVAILABLE = False
    print("⚠️ TA-Lib kütüphanesi yüklenmedi, fallback metodlar kullanılacak")

# ADX warning'lerini gizle
warnings.filterwarnings('ignore', category=RuntimeWarning)

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    
    df = df.copy()
    
    # 1. EMA'lar (her zaman hesaplanabilir)
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # 2. Diğer indikatörler (TA_AVAILABLE kontrolü)
    if TA_AVAILABLE:
        try:
            # RSI
            df['RSI'] = RSIIndicator(df['close'], window=14).rsi()
            
            # MACD
            macd = MACD(df['close'])
            df['MACD_Level'] = macd.macd()
            df['MACD_Signal'] = macd.macd_signal()
            df['MACD_Hist'] = macd.macd_diff()
            
            # Bollinger Bands
            bb = BollingerBands(df['close'], window=20)
            df['BB_Upper'] = bb.bollinger_hband()
            df['BB_Lower'] = bb.bollinger_lband()
            df['BB_Middle'] = bb.bollinger_mavg()
            df['BB_Width_Pct'] = ((df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle'] * 100).fillna(0)
            
            # ATR
            df['ATR14'] = AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
            
            # ADX (warning olabilir)
            adx = ADXIndicator(df['high'], df['low'], df['close'])
            df['ADX'] = adx.adx()
            df['DI_Plus'] = adx.adx_pos()
            df['DI_Minus'] = adx.adx_neg()
            
            # Volume indikatörleri
            df['OBV'] = OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
            df['OBV_EMA'] = df['OBV'].ewm(span=20, adjust=False).mean()
            df['CMF'] = ChaikinMoneyFlowIndicator(df['high'], df['low'], df['close'], df['volume']).chaikin_money_flow()
            df['MFI'] = MFIIndicator(df['high'], df['low'], df['close'], df['volume']).money_flow_index()
            
        except Exception as e:
            print(f"⚠️ TA-Lib indikatör hatası: {e}. Fallback kullanılıyor...")
            _calculate_fallback_indicators(df)
    else:
        print("ℹ️ TA-Lib yok, fallback indikatörler kullanılıyor")
        _calculate_fallback_indicators(df)
    
    # 3. Hacim hesaplamaları (her zaman)
    _calculate_volume_indicators(df)
    
    # 4. Temizlik
    _cleanup_indicators(df)
    
    return df

def _calculate_fallback_indicators(df):
    """TA-Lib yoksa fallback hesaplamalar"""
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'].fillna(50, inplace=True)
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD_Level'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD_Level'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD_Level'] - df['MACD_Signal']
    
    # Bollinger Bands
    df['BB_Middle'] = df['close'].rolling(window=20, min_periods=1).mean()
    bb_std = df['close'].rolling(window=20, min_periods=1).std()
    df['BB_Upper'] = df['BB_Middle'] + bb_std * 2
    df['BB_Lower'] = df['BB_Middle'] - bb_std * 2
    df['BB_Width_Pct'] = ((df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle'] * 100).fillna(0)
    
    # ATR
    tr = pd.concat([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift()),
        abs(df['low'] - df['close'].shift())
    ], axis=1).max(axis=1)
    df['ATR14'] = tr.rolling(window=14, min_periods=1).mean()
    
    # Default değerler
    df['ADX'] = 20
    df['DI_Plus'] = 20
    df['DI_Minus'] = 20
    df['OBV'] = (df['volume'] * np.sign(df['close'].diff())).cumsum()
    df['OBV_EMA'] = df['OBV'].ewm(span=20, adjust=False).mean()
    df['CMF'] = 0
    df['MFI'] = 50

def _calculate_volume_indicators(df):
    """Hacim göstergelerini hesapla"""
    # Volume ortalamaları
    df['Volume_10d_Avg'] = df['volume'].rolling(window=10, min_periods=1).mean()
    df['Volume_20d_Avg'] = df['volume'].rolling(window=20, min_periods=1).mean()
    
    # Relative Volume
    with np.errstate(divide='ignore', invalid='ignore'):
        df['Relative_Volume'] = df['volume'] / df['Volume_20d_Avg']
    
    df['Relative_Volume'] = df['Relative_Volume'].replace([np.inf, -np.inf], np.nan)
    df['Relative_Volume'] = df['Relative_Volume'].fillna(1.0)
    df['Relative_Volume'] = df['Relative_Volume'].clip(lower=0.1, upper=10.0)
    
    # Değişim yüzdeleri
    df['Daily_Change_Pct'] = df['close'].pct_change(1) * 100
    df['Weekly_Change_Pct'] = df['close'].pct_change(5) * 100

def _cleanup_indicators(df):
    """NaN değerleri temizle"""
    # İlk değerleri doldur
    indicator_cols = ['RSI', 'MACD_Level', 'MACD_Signal', 'ADX', 'Relative_Volume', 'ATR14']
    
    for col in indicator_cols:
        if col in df.columns:
            if col == 'RSI':
                default = 50
            elif col == 'Relative_Volume':
                default = 1.0
            else:
                default = 0.0
            
            df[col] = df[col].fillna(default)
    
    # İlk birkaç satırı doldur
    df = df.ffill().bfill()
    
    return df