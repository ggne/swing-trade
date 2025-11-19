"""
Gelişmiş Swing Grafik Oluşturucu
"""

import mplfinance as mpf
import pandas as pd
import numpy as np
import ta as ta_lib
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

class SwingChart:
    def __init__(self, df, symbol, save_path=None):
        self.df = df.copy()
        self.symbol = symbol
        self.save_path = save_path or f"{symbol}_Swing_Chart.png"
        
    def prepare_dataframe(self):
        try:
            df_clean = self.df.copy()
            df_clean.columns = [col.lower() for col in df_clean.columns]
            
            if all(col in df_clean.columns for col in ['open', 'high', 'low', 'close', 'volume']):
                final_df = df_clean[['open', 'high', 'low', 'close', 'volume']].copy()
                final_df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            else:
                return None
            
            if not isinstance(final_df.index, pd.DatetimeIndex):
                final_df.index = pd.to_datetime(final_df.index)
            
            final_df = final_df.dropna()
            final_df = final_df[final_df['Volume'] > 0]
            final_df = final_df[final_df['High'] >= final_df['Low']]
            
            return final_df
            
        except Exception as e:
            print(f"Data preparation error: {e}")
            return None
    
    def calculate_simple_indicators(self, df):
        try:
            # EMA'lar
            df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            
            # RSI
            df['RSI'] = ta_lib.momentum.rsi(df['Close'], window=14)
            
            # MACD
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
            
            # Bollinger Bands
            df['BB_Middle'] = df['Close'].rolling(window=20).mean()
            bb_std = df['Close'].rolling(window=20).std()
            df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
            df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
            
            # Volume MA
            df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
            
            df = df.dropna()
            return df
            
        except Exception as e:
            print(f"Indicator calculation error: {e}")
            return self.df
    
    def create_basic_chart(self, df):
        try:
            plot_df = df.tail(60).copy()
            
            if len(plot_df) < 10:
                return False
            
            apds = []
            
            # EMA'lar
            if 'EMA20' in plot_df.columns:
                apds.append(mpf.make_addplot(plot_df['EMA20'], color='blue', width=1.2, panel=0, label='EMA20'))
            if 'EMA50' in plot_df.columns:
                apds.append(mpf.make_addplot(plot_df['EMA50'], color='red', width=1.2, panel=0, label='EMA50'))
            
            # RSI
            if 'RSI' in plot_df.columns:
                apds.append(mpf.make_addplot(plot_df['RSI'], panel=1, color='purple', ylabel='RSI'))
                apds.append(mpf.make_addplot([70] * len(plot_df), panel=1, color='red', linestyle='--', alpha=0.7))
                apds.append(mpf.make_addplot([30] * len(plot_df), panel=1, color='green', linestyle='--', alpha=0.7))
            
            # Grafik oluştur
            fig, axes = mpf.plot(
                plot_df,
                type='candle',
                style='charles',
                title=f'\n{self.symbol} - Swing Analysis',
                ylabel='Price (TL)',
                volume=True,
                addplot=apds if apds else None,
                panel_ratios=[3, 1, 1],
                figratio=(12, 8),
                returnfig=True,
                closefig=False
            )
            
            plt.savefig(self.save_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            
            return True
            
        except Exception as e:
            print(f"Chart creation error: {e}")
            return False
    
    def plot(self):
        try:
            prepared_df = self.prepare_dataframe()
            if prepared_df is None or len(prepared_df) < 20:
                print("Insufficient data for chart")
                return False
            
            indicator_df = self.calculate_simple_indicators(prepared_df)
            if indicator_df is None:
                print("Indicator calculation failed")
                return False
            
            return self.create_basic_chart(indicator_df)
            
        except Exception as e:
            print(f"Plot error: {e}")
            return False