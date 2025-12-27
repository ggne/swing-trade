# risk/stop_target_manager.py
import numpy as np
from typing import Tuple, Optional

def _calculate_stops_targets(df: 'pd.DataFrame', symbol: str, config: dict) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Dinamik stop-loss ve hedef seviyelerini belirler.
    """
    if df.empty:
        return None, None, None

    latest = df.iloc[-1]
    high = latest['high']
    low = latest['low']
    close = latest['close']
    atr = latest['ATR14'] if 'ATR14' in df.columns else (high - low) * 0.1
    atr = max(atr, 0.01)  # min ATR koruma

    # Stop-loss: ATR tabanlı
    stop_loss = close - (atr * config.get('stop_multiplier', 1.5))
    stop_loss = max(stop_loss, low - (atr * 0.5))  # dip koruma

    # Hedefler: Fibonacci veya sabit RR
    rr1 = config.get('min_risk_reward_ratio', 2.0)
    rr2 = rr1 * 1.5

    risk_dist = close - stop_loss
    if risk_dist <= 0:
        return None, None, None

    target1 = close + (risk_dist * rr1)
    target2 = close + (risk_dist * rr2)

    # Alternatif: BB üst bandı kullan
    if 'BB_Upper' in df.columns and df['BB_Upper'].iloc[-1] > target1:
        target1 = min(df['BB_Upper'].iloc[-1], target1 * 1.2)
        target2 = target1 * 1.3

    return float(stop_loss), float(target1), float(target2)