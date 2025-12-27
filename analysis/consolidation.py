# analysis/consolidation.py
import pandas as pd
import numpy as np
from core.types import ConsolidationPattern

def detect_consolidation_pattern(df, period=20, threshold_pct=8.0) -> ConsolidationPattern:
    """
    Konsolidasyon deseni tespiti
    """
    try:
        if df is None or len(df) < period:
            return ConsolidationPattern(
                detected=False, duration=0, range_pct=0,
                breakout_type='none', breakout_strength=0,
                support=0, resistance=0
            )
        recent = df.tail(period)
        high_range = recent['high'].max()
        low_range = recent['low'].min()
        mid_price = (high_range + low_range) / 2
        range_pct = (high_range - low_range) / mid_price * 100
        current = df.iloc[-1]
        is_consolidating = range_pct < threshold_pct
        breakout_type = 'none'
        breakout_strength = 0.0
        if is_consolidating:
            if current['close'] > high_range:
                breakout_type = 'upward'
                price_strength = min(
                    ((current['close'] - high_range) / high_range * 100) * 10, 
                    40
                )
                volume_strength = min(
                    (current.get('Relative_Volume', 1) - 1) * 30, 
                    30
                )
                momentum_strength = 20 if current.get('RSI', 50) > 50 else 10
                breakout_strength = price_strength + volume_strength + momentum_strength
            elif current['close'] > high_range * 0.98:
                if current.get('Relative_Volume', 1) > 1.3:
                    breakout_type = 'potential_upward'
                    breakout_strength = 60
        return ConsolidationPattern(
            detected=is_consolidating,
            duration=period,
            range_pct=round(range_pct, 2),
            breakout_type=breakout_type,
            breakout_strength=round(breakout_strength, 2),
            support=round(low_range, 2),
            resistance=round(high_range, 2)
        )
    except Exception as e:
        import logging
        logging.error(f"Konsolidasyon tespit hatası: {e}")
        return ConsolidationPattern(
            detected=False, duration=0, range_pct=0, 
            breakout_type='none', breakout_strength=0,
            support=0, resistance=0
        )