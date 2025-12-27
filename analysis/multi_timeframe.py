# analysis/multi_timeframe.py - DÜZELTMİŞ VERSİYON
import pandas as pd
import logging
from core.types import MultiTimeframeAnalysis
from indicators.ta_manager import calculate_indicators

def analyze_multi_timeframe_from_data(df_daily: pd.DataFrame, df_weekly: pd.DataFrame) -> MultiTimeframeAnalysis:
    """
    Günlük ve haftalık timeframe analizi - DataFrame'lerden.
    """
    try:
        if df_daily is None or len(df_daily) < 50:
            return _fallback_mtf_analysis()
        
        if df_weekly is None or len(df_weekly) < 20:
            return _fallback_mtf_analysis()
        
        df_daily = calculate_indicators(df_daily)
        latest_daily = df_daily.iloc[-1]
        
        df_weekly = calculate_indicators(df_weekly)
        latest_weekly = df_weekly.iloc[-1]
        
        # Günlük trend
        daily_trend = _determine_trend(latest_daily)
        weekly_trend = _determine_trend(latest_weekly)
        
        alignment = (daily_trend == "uptrend" and weekly_trend == "uptrend")
        
        weekly_rsi = latest_weekly.get('RSI', 50)
        weekly_macd_positive = latest_weekly.get('MACD_Level', 0) > latest_weekly.get('MACD_Signal', 0)
        
        recommendation = _generate_mtf_recommendation(daily_trend, weekly_trend, alignment)
        
        return MultiTimeframeAnalysis(
            daily_trend=daily_trend,
            weekly_trend=weekly_trend,
            alignment=alignment,
            weekly_rsi=round(weekly_rsi, 1),
            weekly_macd_positive=weekly_macd_positive,
            recommendation=recommendation
        )
    except Exception as e:
        logging.error(f"MTF analiz hatası: {e}")
        return _fallback_mtf_analysis()

# ESKİ FONKSİYON - BACKWARD COMPATIBILITY İÇİN (isteğe bağlı)
def analyze_multi_timeframe(tv, symbol: str, exchange: str, config: dict = None) -> MultiTimeframeAnalysis:
    """
    Eski fonksiyon - backward compatibility için.
    Uyarı: Bu fonksiyon cache kullanmaz!
    """
    logging.warning(f"⚠️ Eski analyze_multi_timeframe() kullanılıyor. DataCache kullanılmıyor!")
    
    try:
        from tvDatafeed import Interval
        
        # Günlük veri
        df_daily = tv.get_hist(symbol=symbol, exchange=exchange, 
                              interval=Interval.in_daily, n_bars=100)
        
        # Haftalık veri
        df_weekly = tv.get_hist(symbol=symbol, exchange=exchange,
                               interval=Interval.in_weekly, n_bars=52)
        
        return analyze_multi_timeframe_from_data(df_daily, df_weekly)
        
    except Exception as e:
        logging.error(f"MTF API hatası {symbol}: {e}")
        return _fallback_mtf_analysis()

def _determine_trend(latest):
    try:
        if (latest['close'] > latest['EMA20'] > latest['EMA50'] and 
            latest.get('RSI', 50) > 50):
            return "uptrend"
        elif (latest['close'] < latest['EMA20'] and 
              latest.get('RSI', 50) < 50):
            return "downtrend"
        else:
            return "sideways"
    except KeyError:
        return "unknown"

def _generate_mtf_recommendation(daily, weekly, aligned):
    if aligned and daily == "uptrend":
        return "🟢 GÜÇLÜ ALIM (MTF UYUMLU)"
    elif daily == "uptrend" and weekly == "sideways":
        return "🟡 KISMİ ALIM (GÜNLÜK UYDU)"
    elif daily == "downtrend" and weekly == "downtrend":
        return "🔴 KAÇIN (MTF SATIM)"
    elif daily == "uptrend" and weekly == "downtrend":
        return "⚠️ DİKKAT (GÜNLÜK ALIŞ, HAFTALIK SATIŞ)"
    else:
        return "⚪ NÖTR"

def _fallback_mtf_analysis() -> MultiTimeframeAnalysis:
    return MultiTimeframeAnalysis(
        daily_trend="unknown",
        weekly_trend="unknown",
        alignment=False,
        weekly_rsi=50.0,
        weekly_macd_positive=False,
        recommendation="⚪ NÖTR"
    )