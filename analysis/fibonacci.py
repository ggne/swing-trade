# analysis/fibonacci.py
import numpy as np
from core.types import FibonacciLevel

def calculate_fibonacci_levels(df, lookback=100) -> dict:
    """
    Fibonacci geri çekilme ve genişleme seviyelerini hesaplar.
    """
    if df is None or len(df) < 10:
        return {"levels": []}
    
    recent = df.tail(lookback)
    high = recent['high'].max()
    low = recent['low'].min()
    current = recent['close'].iloc[-1]
    range_val = high - low

    if range_val == 0:
        return {"levels": []}

    fib_ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]
    levels = []

    for ratio in fib_ratios:
        if ratio <= 1.0:
            price = high - (range_val * ratio)
            zone = "retracement"
        else:
            price = high + (range_val * (ratio - 1.0))
            zone = "extension"
        
        distance_pct = abs(current - price) / current * 100
        levels.append(FibonacciLevel(
            level=ratio,
            price=price,
            distance_pct=distance_pct,
            zone=zone
        ))
    
    # Sırala: Yükselen fiyata göre
    levels.sort(key=lambda x: x.price)
    return {"levels": levels}

def find_fibonacci_entry_zone(levels: list, current_price: float, tolerance_pct=1.5) -> dict:
    """
    Fibonacci seviyelerine göre giriş bölgesi önerisi.
    """
    if not levels:
        return {"entry_zone": None, "recommendation": "Fibonacci verisi yok"}
    
    # 0.618 ve 0.786 arasında olan retracement seviyeleri
    retracement_levels = [l for l in levels if l.zone == "retracement" and 0.6 <= l.level <= 0.79]
    if not retracement_levels:
        return {"entry_zone": None, "recommendation": "Uygun retracement yok"}

    # En yakın seviye
    nearest = min(retracement_levels, key=lambda x: x.distance_pct)
    if nearest.distance_pct <= tolerance_pct:
        return {
            "entry_zone": nearest.price,
            "level": nearest.level,
            "distance_pct": nearest.distance_pct,
            "recommendation": f"🎯 Fibonacci {nearest.level:.3f} - GİRİŞ FıR SATI"
        }
    else:
        return {
            "entry_zone": nearest.price,
            "level": nearest.level,
            "distance_pct": nearest.distance_pct,
            "recommendation": f"➡️ Fibonacci {nearest.level:.3f} - Yaklaşma bekleniyor"
        }