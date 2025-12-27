# patterns/price_action.py
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

class PriceActionDetector:
    """Swing trade için TÜM mum formasyonları - TYPE-SAFE VERSİYON"""
    def __init__(self, enable_all_patterns: bool = True):
        self.patterns_detected: Dict[str, bool] = {}
        self.enable_all = enable_all_patterns
        self.logger = logging.getLogger(__name__)

    def analyze_patterns(self, df: pd.DataFrame, lookback: int = 20) -> Dict[str, bool]:
        """Tüm pattern'leri tara - TYPE SAFE"""
        if df is None or len(df) < 3:
            return {}
        try:
            recent_df = df.tail(lookback) if len(df) > lookback else df
            # TEMEL PATTERNLER (mutlaka tanımlı)
            self.patterns_detected = {
                # 1. Bullish Patterns
                'bullish_engulfing': self.detect_bullish_engulfing(recent_df),
                'morning_star': self.detect_morning_star(recent_df),
                'hammer': self.detect_hammer(recent_df),
                'piercing_line': self.detect_piercing_line(recent_df),
                'inverse_hammer': self.detect_inverse_hammer(recent_df),
                'three_white_soldiers': self.detect_three_white_soldiers(recent_df),
                'bullish_harami': self.detect_bullish_harami(recent_df),
                # 2. Neutral/Reversal Patterns
                'doji': self.detect_doji(recent_df),
                'spinning_top': self.detect_spinning_top(recent_df),
                # 3. Bearish Patterns (bilgi amaçlı)
                'bearish_engulfing': self.detect_bearish_engulfing(recent_df),
                'shooting_star': self.detect_shooting_star(recent_df),
                'evening_star': self.detect_evening_star(recent_df)
            }
            # Sadece bullish pattern'leri döndür (swing için)
            bullish_patterns = {k: v for k, v in self.patterns_detected.items() 
                               if k in ['bullish_engulfing', 'morning_star', 'hammer', 
                                       'piercing_line', 'inverse_hammer', 
                                       'three_white_soldiers', 'bullish_harami']}
            active = [p for p, d in bullish_patterns.items() if d]
            if active:
                self.logger.debug(f"🎯 Pattern'ler: {active}")
            return bullish_patterns
        except Exception as e:
            self.logger.error(f"Pattern analiz hatası: {e}")
            return {}

    # ========== BULLISH PATTERNS ==========
    def detect_bullish_engulfing(self, df: pd.DataFrame) -> bool:
        if len(df) < 2: return False
        prev = df.iloc[-2]; curr = df.iloc[-1]
        prev_bearish = prev['close'] < prev['open']
        curr_bullish = curr['close'] > curr['open']
        engulfing = (curr['open'] <= prev['close'] and curr['close'] >= prev['open'])
        return prev_bearish and curr_bullish and engulfing

    def detect_morning_star(self, df: pd.DataFrame) -> bool:
        if len(df) < 3: return False
        day1 = df.iloc[-3]; day2 = df.iloc[-2]; day3 = df.iloc[-1]
        day1_bearish = day1['close'] < day1['open']
        day1_body = abs(day1['close'] - day1['open'])
        day1_range = day1['high'] - day1['low']
        day1_long = day1_body > day1_range * 0.6
        day2_body = abs(day2['close'] - day2['open'])
        day2_small = day2_body < day1_range * 0.3
        gap_down = day2['high'] < day1['close']
        day3_bullish = day3['close'] > day3['open']
        gap_up = day3['low'] > day2['high']
        day1_mid = (day1['open'] + day1['close']) / 2
        closes_above = day3['close'] > day1_mid
        return (day1_bearish and day1_long and day2_small and gap_down and
                day3_bullish and gap_up and closes_above)

    def detect_hammer(self, df: pd.DataFrame) -> bool:
        if len(df) < 1: return False
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        total_range = candle['high'] - candle['low']
        is_hammer = (lower_shadow > body * 2.0 and 
                     upper_shadow < body * 0.3 and
                     body < total_range * 0.3)
        if len(df) >= 5:
            downtrend = df['close'].iloc[-5] > candle['close']
            return is_hammer and downtrend
        return is_hammer

    def detect_piercing_line(self, df: pd.DataFrame) -> bool:
        if len(df) < 2: return False
        prev = df.iloc[-2]; curr = df.iloc[-1]
        prev_bearish = prev['close'] < prev['open']
        curr_bullish = curr['close'] > curr['open']
        if not (prev_bearish and curr_bullish): return False
        gap_down = curr['open'] < prev['close']
        prev_mid = (prev['open'] + prev['close']) / 2
        closes_above_mid = curr['close'] > prev_mid
        not_above_open = curr['close'] < prev['open']
        return gap_down and closes_above_mid and not_above_open

    def detect_inverse_hammer(self, df: pd.DataFrame) -> bool:
        if len(df) < 1: return False
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        total_range = candle['high'] - candle['low']
        return (upper_shadow > body * 2.0 and
                lower_shadow < body * 0.3 and
                body < total_range * 0.3)

    def detect_three_white_soldiers(self, df: pd.DataFrame) -> bool:
        if len(df) < 3: return False
        candles = [df.iloc[-3], df.iloc[-2], df.iloc[-1]]
        all_bullish = all(c['close'] > c['open'] for c in candles)
        if not all_bullish: return False
        higher_closes = all(candles[i]['close'] > candles[i-1]['close'] for i in range(1, 3))
        strong_bodies = all(abs(c['close'] - c['open']) / (c['high'] - c['low']) > 0.6 for c in candles)
        small_shadows = all((c['high'] - max(c['open'], c['close'])) / (c['high'] - c['low']) < 0.2 for c in candles)
        return higher_closes and strong_bodies and small_shadows

    def detect_bullish_harami(self, df: pd.DataFrame) -> bool:
        if len(df) < 2: return False
        prev = df.iloc[-2]; curr = df.iloc[-1]
        prev_bearish = prev['close'] < prev['open']
        curr_bullish = curr['close'] > curr['open']
        if not (prev_bearish and curr_bullish): return False
        inside = (curr['high'] < prev['open'] and curr['low'] > prev['close'])
        prev_body = abs(prev['close'] - prev['open'])
        prev_range = prev['high'] - prev['low']
        prev_long = prev_body > prev_range * 0.5
        return inside and prev_long

    # ========== NEUTRAL/REVERSAL PATTERNS ==========
    def detect_doji(self, df: pd.DataFrame) -> bool:
        if len(df) < 1: return False
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']
        if total_range == 0: return False
        body_ratio = body / total_range
        is_doji = body_ratio < 0.1
        return is_doji

    def detect_spinning_top(self, df: pd.DataFrame) -> bool:
        if len(df) < 1: return False
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']
        if total_range == 0: return False
        body_ratio = body / total_range
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        is_spinning_top = (0.1 <= body_ratio <= 0.3 and
                          upper_shadow > total_range * 0.3 and
                          lower_shadow > total_range * 0.3)
        return is_spinning_top

    # ========== BEARISH PATTERNS ==========
    def detect_bearish_engulfing(self, df: pd.DataFrame) -> bool:
        if len(df) < 2: return False
        prev = df.iloc[-2]; curr = df.iloc[-1]
        prev_bullish = prev['close'] > prev['open']
        curr_bearish = curr['close'] < curr['open']
        engulfing = (curr['open'] >= prev['close'] and curr['close'] <= prev['open'])
        return prev_bullish and curr_bearish and engulfing

    def detect_shooting_star(self, df: pd.DataFrame) -> bool:
        if len(df) < 1: return False
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        total_range = candle['high'] - candle['low']
        return (upper_shadow > body * 2.0 and
                lower_shadow < body * 0.3 and
                body < total_range * 0.3)

    def detect_evening_star(self, df: pd.DataFrame) -> bool:
        if len(df) < 3: return False
        day1 = df.iloc[-3]; day2 = df.iloc[-2]; day3 = df.iloc[-1]
        day1_bullish = day1['close'] > day1['open']
        day1_body = abs(day1['close'] - day1['open'])
        day1_range = day1['high'] - day1['low']
        day1_long = day1_body > day1_range * 0.6
        day2_body = abs(day2['close'] - day2['open'])
        day2_small = day2_body < day1_range * 0.3
        gap_up = day2['low'] > day1['high']
        day3_bearish = day3['close'] < day3['open']
        gap_down = day3['high'] < day2['low']
        day1_mid = (day1['open'] + day1['close']) / 2
        closes_below = day3['close'] < day1_mid
        return (day1_bullish and day1_long and day2_small and gap_up and
                day3_bearish and gap_down and closes_below)

    # ========== UTILITY METHODS ==========
    def get_pattern_score(self, patterns: Optional[Dict[str, bool]] = None) -> int:
        if patterns is None:
            patterns = self.patterns_detected
        if not patterns:
            return 0
        weights = {
            'bullish_engulfing': 15,
            'morning_star': 12,
            'three_white_soldiers': 10,
            'hammer': 8,
            'piercing_line': 7,
            'inverse_hammer': 6,
            'bullish_harami': 5,
            'doji': 3,
            'spinning_top': 2
        }
        score = 0
        for pattern, detected in patterns.items():
            if detected and pattern in weights:
                score += weights[pattern]
        return min(score, 30)

    def get_pattern_descriptions(self, patterns: Dict[str, bool]) -> Dict[str, str]:
        descriptions = {
            'bullish_engulfing': 'Güçlü trend dönüşü. Önceki kırmızı mumu tamamen yutan yeşil mum.',
            'morning_star': 'Dip sinyali. Kırmızı + doji + yeşil üçlüsü. Güçlü yükseliş öncesi.',
            'hammer': 'Destek teyidi. Uzun alt gölge, küçük beden. Düşüş trendi sonu.',
            'piercing_line': 'Yükseliş başlangıcı. Önceki mumun ortasını deliyor.',
            'inverse_hammer': 'Ters çekiç. Direnç testi sonrası yükseliş potansiyeli.',
            'three_white_soldiers': 'Güçlü yükseliş momentumu. Ardışık 3 büyük yeşil mum.',
            'bullish_harami': 'Trend dönüşü. Büyük kırmızı içinde küçük yeşil mum.',
            'doji': 'Belirsizlik. Alıcı ve satıcı eşit güçte. Trend değişimi öncesi.',
            'spinning_top': 'Kararsızlık. Küçük beden, uzun gölgeler. Yön belirsiz.',
            'bearish_engulfing': 'Güçlü düşüş sinyali. Dikkat edilmeli!',
            'shooting_star': 'Tepe sinyali. Uzun üst gölge, küçük beden.',
            'evening_star': 'Tepe formasyonu. Yeşil + doji + kırmızı üçlüsü.'
        }
        return {p: descriptions.get(p, '') for p in patterns.keys() if patterns.get(p, False)}

    def generate_signal_summary(self, df: pd.DataFrame) -> Dict:
        patterns = self.analyze_patterns(df)
        score = self.get_pattern_score(patterns)
        descriptions = self.get_pattern_descriptions(patterns) if patterns else {}
        trend = self._analyze_trend_context(df)
        return {
            'patterns_found': [p for p, d in patterns.items() if d] if patterns else [],
            'pattern_score': score,
            'total_possible_score': 30,
            'descriptions': descriptions,
            'trend_context': trend,
            'signal_strength': self._calculate_signal_strength(score, trend),
            'recommendation': self._generate_recommendation(patterns, score, trend) if patterns else "Veri yetersiz"
        }

    def _analyze_trend_context(self, df: pd.DataFrame) -> Dict:
        if df is None or len(df) < 20:
            return {'trend': 'unknown', 'strength': 0}
        closes = df['close']
        short_trend = 'up' if closes.iloc[-1] > closes.iloc[-5] else 'down'
        ma20 = closes.rolling(20).mean()
        med_trend = 'up' if closes.iloc[-1] > ma20.iloc[-1] else 'down'
        returns = closes.pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0
        return {
            'short_term': short_trend,
            'medium_term': med_trend,
            'volatility': round(volatility * 100, 2) if volatility > 0 else 0,
            'in_downtrend': short_trend == 'down' and med_trend == 'down',
            'in_uptrend': short_trend == 'up' and med_trend == 'up'
        }

    def _calculate_signal_strength(self, score: int, trend: Dict) -> str:
        if score <= 0:
            return "⚠️ SİNYAL YOK"
        base_strength = score / 30.0
        trend_bonus = 0
        if trend.get('in_downtrend', False):
            trend_bonus = 0.2
        elif trend.get('in_uptrend', False):
            trend_bonus = 0.1
        total = min(base_strength + trend_bonus, 1.0)
        if total >= 0.8:
            return "🔥🔥🔥 ÇOK GÜÇLÜ"
        elif total >= 0.6:
            return "🔥🔥 GÜÇLÜ"
        elif total >= 0.4:
            return "🔥 ORTA"
        else:
            return "⚠️ ZAYIF"

    def _generate_recommendation(self, patterns: Optional[Dict[str, bool]], score: int, trend: Dict) -> str:
        if not patterns or score <= 0:
            return "BEKLE - Anlamlı pattern yok"
        if score >= 20:
            return "GÜÇLÜ AL SİNYALİ - Pattern + Trend uyumlu"
        elif score >= 15:
            if trend.get('in_downtrend'):
                return "DİPTE AL SİNYALİ - Trend dönüşü başlıyor"
            else:
                return "AL SİNYALİ - Teknik yapı olumlu"
        elif score >= 10:
            return "İZLE - Pattern var ama teyit beklenmeli"
        elif score >= 5:
            return "NÖTR - Zayıf sinyal, takip et"
        else:
            return "BEKLE - Anlamlı pattern yok"