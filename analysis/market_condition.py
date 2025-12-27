# analysis/market_condition.py
import pandas as pd
import numpy as np
from core.types import MarketAnalysis

def analyze_market_condition(tv, config) -> MarketAnalysis:
    """Piyasa durumu analizi - BIST100 bazlı"""
    try:
        from tvDatafeed import Interval
        from indicators.ta_manager import calculate_indicators

        bist_data = tv.get_hist(
            symbol='XU100',
            exchange='BIST',
            interval=Interval.in_daily,
            n_bars=100
        )
        if bist_data is None or len(bist_data) < 50:
            return _empty_market_analysis()

        df = calculate_indicators(bist_data)
        latest = df.iloc[-1]
        trend_strength = _calculate_trend_strength(df, latest)
        returns = df['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100
        volume_trend = latest['volume'] / df['volume'].rolling(20).mean().iloc[-1]
        market_score = _calculate_market_score(trend_strength, volatility, volume_trend)
        regime = _determine_market_regime(trend_strength, volatility, market_score)
        recommendation = _generate_market_recommendation(regime, market_score)

        return MarketAnalysis(
            regime=regime,
            trend_strength=round(trend_strength, 1),
            volatility=round(volatility, 1),
            volume_trend=round(volume_trend, 2),
            market_score=round(market_score, 1),
            recommendation=recommendation
        )
    except Exception as e:
        import logging
        logging.error(f"Piyasa analizi hatası: {e}")
        return _empty_market_analysis()

def _calculate_trend_strength(df, latest):
    strength = 0
    if latest['close'] > latest['EMA20'] > latest['EMA50']:
        strength += 40
    elif latest['close'] > latest['EMA20']:
        strength += 20
    adx = latest.get('ADX', 0)
    if adx > 25:
        strength += 30
    elif adx > 20:
        strength += 15
    if latest.get('MACD_Level', 0) > latest.get('MACD_Signal', 0):
        strength += 30
    return min(strength, 100)

def _calculate_market_score(trend_strength, volatility, volume_trend):
    score = 0
    score += trend_strength * 0.4
    vol_score = max(0, 100 - volatility * 2)
    score += vol_score * 0.3
    vol_trend_score = min(volume_trend * 50, 100)
    score += vol_trend_score * 0.3
    return score

def _determine_market_regime(trend_strength, volatility, market_score):
    if trend_strength >= 70 and volatility < 25:
        return "bullish"
    elif trend_strength <= 30 and volatility > 35:
        return "bearish"
    elif volatility > 40:
        return "volatile"
    elif 40 <= trend_strength <= 60 and volatility < 30:
        return "sideways"
    else:
        return "neutral"

def _generate_market_recommendation(regime, market_score):
    recommendations = {
        "bullish": "🟢 AĞIRLIKLI ALIM",
        "bearish": "🔴 DİKKATLİ ALIM",
        "volatile": "🟡 SEÇİCİ ALIM",
        "sideways": "🔵 DİKEY PAZAR",
        "neutral": "⚪ NÖTR"
    }
    return recommendations.get(regime, "⚪ NÖTR")

def _empty_market_analysis() -> MarketAnalysis:
    return MarketAnalysis(
        regime="neutral",
        trend_strength=50.0,
        volatility=25.0,
        volume_trend=1.0,
        market_score=50.0,
        recommendation="⚪ NÖTR"
    )