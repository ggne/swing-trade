# analysis/support_resistance.py
import pandas as pd
import numpy as np
from typing import Dict, List

class SupportResistanceFinder:
    """Otomatik destek/direnç tespiti"""
    def __init__(self, sensitivity=1.0):
        self.sensitivity = sensitivity

    def find_levels(self, df, lookback=100, tolerance=0.015):
        try:
            if df is None or len(df) < 20:
                return {'support': [], 'resistance': [], 'current_price': 0}
            recent_df = df.tail(lookback)
            highs = recent_df['high'].values
            lows = recent_df['low'].values
            closes = recent_df['close'].values

            # Resistance (pivot high)
            resistance_levels = []
            for i in range(3, len(highs) - 3):
                if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i-3] and
                    highs[i] > highs[i+1] and highs[i] > highs[i+2] and highs[i] > highs[i+3]):
                    confirmation = True
                    for j in range(1, 4):
                        if highs[i] - highs[i-j] < (highs[i] * 0.005):
                            confirmation = False
                            break
                    if confirmation:
                        resistance_levels.append(highs[i])

            # Support (pivot low)
            support_levels = []
            for i in range(3, len(lows) - 3):
                if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i-3] and
                    lows[i] < lows[i+1] and lows[i] < lows[i+2] and lows[i] < lows[i+3]):
                    confirmation = True
                    for j in range(1, 4):
                        if lows[i-j] - lows[i] < (lows[i] * 0.005):
                            confirmation = False
                            break
                    if confirmation:
                        support_levels.append(lows[i])

            # Fibonacci pivot ek katman
            fib_levels = self._find_fibonacci_pivots(recent_df)
            resistance_levels.extend(fib_levels.get('resistance', []))
            support_levels.extend(fib_levels.get('support', []))

            # Kümele
            resistance_levels = self._cluster_levels(resistance_levels, tolerance)
            support_levels = self._cluster_levels(support_levels, tolerance)

            current_price = closes[-1]
            filtered_support = sorted([s for s in support_levels if s < current_price * 0.999], reverse=True)[:5]
            filtered_resistance = sorted([r for r in resistance_levels if r > current_price * 1.001])[:5]

            support_strength = self._calculate_level_strength(filtered_support, recent_df, 'support')
            resistance_strength = self._calculate_level_strength(filtered_resistance, recent_df, 'resistance')

            return {
                'support': filtered_support,
                'resistance': filtered_resistance,
                'support_strength': support_strength,
                'resistance_strength': resistance_strength,
                'current_price': current_price,
                'nearest_support': filtered_support[-1] if filtered_support else current_price * 0.95,
                'nearest_resistance': filtered_resistance[0] if filtered_resistance else current_price * 1.05,
                'support_distance_pct': ((current_price - filtered_support[-1]) / current_price * 100) if filtered_support else 5.0,
                'resistance_distance_pct': ((filtered_resistance[0] - current_price) / current_price * 100) if filtered_resistance else 5.0
            }
        except Exception as e:
            import logging
            logging.error(f"Support/Resistance hatası: {e}")
            return {'support': [], 'resistance': [], 'current_price': df['close'].iloc[-1] if not df.empty else 0}

    def _find_fibonacci_pivots(self, df):
        try:
            if len(df) < 20:
                return {'support': [], 'resistance': []}
            swing_high = df['high'].max()
            swing_low = df['low'].min()
            fib_levels = {
                0.236: swing_low + (swing_high - swing_low) * 0.236,
                0.382: swing_low + (swing_high - swing_low) * 0.382,
                0.500: swing_low + (swing_high - swing_low) * 0.500,
                0.618: swing_low + (swing_high - swing_low) * 0.618,
                0.786: swing_low + (swing_high - swing_low) * 0.786
            }
            current_price = df['close'].iloc[-1]
            fib_support = []
            fib_resistance = []
            for price in fib_levels.values():
                if price < current_price * 0.995:
                    fib_support.append(price)
                elif price > current_price * 1.005:
                    fib_resistance.append(price)
            return {'support': fib_support, 'resistance': fib_resistance}
        except:
            return {'support': [], 'resistance': []}

    def _cluster_levels(self, levels, tolerance):
        if not levels:
            return []
        clustered = []
        levels = sorted(levels)
        current_cluster = [levels[0]]
        for level in levels[1:]:
            if abs(level - current_cluster[-1]) / current_cluster[-1] < tolerance:
                current_cluster.append(level)
            else:
                clustered.append(np.mean(current_cluster))
                current_cluster = [level]
        if current_cluster:
            clustered.append(np.mean(current_cluster))
        return clustered

    def _calculate_level_strength(self, levels, df, level_type='support'):
        if not levels:
            return []
        strengths = []
        for level in levels:
            strength = 0
            if level_type == 'support':
                touches = sum((df['low'] <= level * 1.005) & (df['low'] >= level * 0.995))
                bounces = sum((df['low'] <= level * 1.005) & (df['low'] >= level * 0.995) & (df['close'] > df['open']))
            else:
                touches = sum((df['high'] >= level * 0.995) & (df['high'] <= level * 1.005))
                bounces = sum((df['high'] >= level * 0.995) & (df['high'] <= level * 1.005) & (df['close'] < df['open']))
            if touches >= 3:
                strength += 40
            elif touches >= 2:
                strength += 25
            elif touches >= 1:
                strength += 10
            if touches > 0:
                bounce_rate = bounces / touches
                if bounce_rate >= 0.7:
                    strength += 30
                elif bounce_rate >= 0.5:
                    strength += 20
                elif bounce_rate >= 0.3:
                    strength += 10
            recent_touches = sum((df.tail(20)['low' if level_type == 'support' else 'high'] >= level * 0.995) & 
                                (df.tail(20)['low' if level_type == 'support' else 'high'] <= level * 1.005))
            if recent_touches > 0:
                strength += 20
            strengths.append(min(strength, 100))
        return strengths

    def check_breakout(self, df, levels, volume_lookback=20):
        try:
            if df is None or len(df) < 10:
                return {'breakout': False, 'type': 'none', 'strength': 0}
            current = df.iloc[-1]
            prev = df.iloc[-2]
            current_price = current['close']

            # Resistance breakout
            for resistance, strength in zip(levels.get('resistance', []), levels.get('resistance_strength', [])):
                if (prev['close'] < resistance * 1.005 and current['close'] > resistance * 0.995 and current['high'] > resistance):
                    avg_volume = df['volume'].tail(volume_lookback).mean()
                    volume_surge = current['volume'] / avg_volume if avg_volume > 0 else 1
                    close_above = (current['close'] - resistance) / resistance * 100
                    breakout_strength = 0
                    if volume_surge > 1.5 and close_above > 0.5:
                        breakout_strength = 80 + min(strength, 20)
                    elif volume_surge > 1.3 and close_above > 0.3:
                        breakout_strength = 60 + min(strength, 20)
                    elif volume_surge > 1.2 and close_above > 0.2:
                        breakout_strength = 40 + min(strength, 20)
                    if breakout_strength > 50:
                        return {
                            'breakout': True,
                            'type': 'resistance_breakout',
                            'level': resistance,
                            'strength': min(breakout_strength, 100),
                            'volume_surge': volume_surge,
                            'close_above_pct': close_above,
                            'level_strength': strength
                        }

            # Support breakdown (not used in buy signals)
            for support, strength in zip(reversed(levels.get('support', [])), reversed(levels.get('support_strength', []))):
                if (prev['close'] > support * 0.995 and current['close'] < support * 1.005 and current['low'] < support):
                    avg_volume = df['volume'].tail(volume_lookback).mean()
                    volume_surge = current['volume'] / avg_volume if avg_volume > 0 else 1
                    close_below = (support - current['close']) / support * 100
                    breakdown_strength = 0
                    if volume_surge > 1.5 and close_below > 0.5:
                        breakdown_strength = 80 + min(strength, 20)
                    elif volume_surge > 1.3 and close_below > 0.3:
                        breakdown_strength = 60 + min(strength, 20)
                    elif volume_surge > 1.2 and close_below > 0.2:
                        breakdown_strength = 40 + min(strength, 20)
                    if breakdown_strength > 50:
                        return {
                            'breakout': True,
                            'type': 'support_breakdown',
                            'level': support,
                            'strength': min(breakdown_strength, 100),
                            'volume_surge': volume_surge,
                            'close_below_pct': close_below,
                            'level_strength': strength,
                            'warning': '⚠️ DESTEK KIRILIMI - DİKKAT!'
                        }

            # Potential breakout
            nearest_resistance = levels.get('nearest_resistance', 0)
            if nearest_resistance > 0:
                distance_to_resistance = (nearest_resistance - current_price) / current_price * 100
                if 0 < distance_to_resistance < 2:
                    volume_trend = df['volume'].tail(5).mean() / df['volume'].tail(20).mean()
                    if volume_trend > 1.2:
                        return {
                            'breakout': False,
                            'type': 'potential_breakout',
                            'level': nearest_resistance,
                            'distance_pct': distance_to_resistance,
                            'volume_trend': volume_trend,
                            'strength': 30 + min(volume_trend * 20, 40)
                        }
            return {'breakout': False, 'type': 'none', 'strength': 0}
        except Exception as e:
            import logging
            logging.error(f"Breakout kontrol hatası: {e}")
            return {'breakout': False, 'type': 'error', 'strength': 0}

    def get_trading_zones(self, levels, current_price):
        if not levels.get('support') or not levels.get('resistance'):
            return {
                'zone': 'neutral',
                'distance_to_support': 5.0,
                'distance_to_resistance': 5.0,
                'recommendation': 'Nötr'
            }
        nearest_support = levels.get('nearest_support', current_price * 0.95)
        nearest_resistance = levels.get('nearest_resistance', current_price * 1.05)
        distance_to_support = (current_price - nearest_support) / current_price * 100
        distance_to_resistance = (nearest_resistance - current_price) / current_price * 100

        if distance_to_support < 2 and distance_to_resistance > 5:
            zone = 'near_support'
            recommendation = '🎯 DESTEK YAKIN - ALIM FIRSATI'
        elif distance_to_resistance < 2 and distance_to_support > 5:
            zone = 'near_resistance'
            recommendation = '⚠️ DİRENÇ YAKIN - SATIM/SKALP'
        elif distance_to_support < 3 and distance_to_resistance < 3:
            zone = 'consolidation'
            recommendation = '📊 KONSOLİDASYON - BREAKOUT BEKLE'
        elif current_price > nearest_resistance:
            zone = 'above_resistance'
            recommendation = '🚀 DİRENÇ ÜSTÜ - TREND DEVAM'
        elif current_price < nearest_support:
            zone = 'below_support'
            recommendation = '🔴 DESTEK ALTINDA - RİSKLİ'
        else:
            zone = 'mid_range'
            recommendation = '↔️ ORTA BÖLGE - NÖTR'
        return {
            'zone': zone,
            'distance_to_support': round(distance_to_support, 2),
            'distance_to_resistance': round(distance_to_resistance, 2),
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'recommendation': recommendation
        }