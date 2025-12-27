# smart_filter/smart_filter.py
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from core.types import FilterScore, MarketRegime

class SmartFilterSystem:
    """Akıllı filtre sistemi - ağırlıklı skorlama"""
    def __init__(self, config):
        self.config = config
        self.weights = {
            'trend': 30,
            'momentum': 25,
            'volume': 20,
            'volatility': 15,
            'risk': 10
        }
        self.min_total_score = config.get('min_total_score', 60)
        self.min_category_scores = {
            'trend': 15,
            'momentum': 10,
            'volume': 8,
        }

    def detect_market_regime(self, market_data: pd.DataFrame) -> MarketRegime:
        if market_data is None or len(market_data) < 50:
            return MarketRegime.SIDEWAYS
        close = market_data['close']
        ema20 = close.ewm(span=20).mean()
        ema50 = close.ewm(span=50).mean()
        current_price = close.iloc[-1]
        if current_price > ema20.iloc[-1] > ema50.iloc[-1]:
            slope_20 = (ema20.iloc[-1] - ema20.iloc[-20]) / ema20.iloc[-20] * 100
            if slope_20 > 5:
                return MarketRegime.BULL
            else:
                return MarketRegime.SIDEWAYS
        elif current_price < ema20.iloc[-1] < ema50.iloc[-1]:
            return MarketRegime.BEAR
        returns = close.pct_change()
        volatility = returns.std() * np.sqrt(252)
        if volatility > 0.4:
            return MarketRegime.VOLATILE
        return MarketRegime.SIDEWAYS

    def adjust_filters_for_regime(self, regime: MarketRegime):
        adjustments = {}
        if regime == MarketRegime.BULL:
            adjustments = {
                'min_rsi': 35,
                'max_rsi': 75,
                'min_trend_score': 55,
                'min_relative_volume': 0.9
            }
        elif regime == MarketRegime.BEAR:
            adjustments = {
                'min_rsi': 40,
                'max_rsi': 65,
                'min_trend_score': 70,
                'min_relative_volume': 1.3,
                'check_adx': True,
                'min_adx': 25
            }
        elif regime == MarketRegime.VOLATILE:
            adjustments = {
                'max_atr14_pct': 5.0,
                'max_daily_change_pct': 5.0,
                'min_trend_score': 65,
                'use_atr_stop': True
            }
        else:  # SIDEWAYS
            adjustments = {
                'check_consolidation': True,
                'max_consolidation_range': 8.0,
                'check_breakout_potential': True
            }
        return adjustments

    def calculate_trend_score(self, df: pd.DataFrame, latest: pd.Series) -> FilterScore:
        score = 0.0; max_score = 30.0; details = {}
        ema_score = 4 if latest['close'] > latest.get('EMA20', 0) else 0
        if ema_score > 0 and latest.get('EMA20', 0) > latest.get('EMA50', 0):
            ema_score += 6
        details['ema_alignment'] = ema_score
        score += ema_score

        ema20_slope = df['EMA20'].pct_change(5).iloc[-1] * 100 if 'EMA20' in df.columns else 0
        ema50_slope = df['EMA50'].pct_change(5).iloc[-1] * 100 if 'EMA50' in df.columns else 0
        slope_score = 0
        if ema20_slope > 0.05: slope_score += 5
        elif ema20_slope > 0: slope_score += 2
        if ema50_slope > 0.02: slope_score += 5
        elif ema50_slope > 0: slope_score += 2
        details['ema_slopes'] = {'ema20': ema20_slope, 'ema50': ema50_slope}
        score += slope_score

        adx = latest.get('ADX', 0)
        adx_score = 10 if adx > 30 else (7 if adx > 25 else (4 if adx > 20 else 0))
        details['adx'] = adx
        score += adx_score

        passed = score >= self.min_category_scores.get('trend', 15)
        return FilterScore('trend', score, max_score, self.weights['trend'], details, passed)

    def calculate_momentum_score(self, df: pd.DataFrame, latest: pd.Series) -> FilterScore:
        score = 0.0; max_score = 25.0; details = {}
        rsi = latest.get('RSI', 50)
        rsi_score = 10 if 40 <= rsi <= 60 else (7 if 35 <= rsi <= 65 else (4 if 30 <= rsi <= 70 else 0))
        details['rsi'] = rsi
        score += rsi_score

        macd_level = latest.get('MACD_Level', 0)
        macd_signal = latest.get('MACD_Signal', 0)
        macd_hist = latest.get('MACD_Hist', 0)
        macd_score = 0
        if macd_level > macd_signal:
            macd_score += 4
            if macd_hist > 0 and len(df) > 1:
                prev_hist = df['MACD_Hist'].iloc[-2]
                if macd_hist > prev_hist:
                    macd_score += 4
        details['macd'] = {'level': macd_level, 'signal': macd_signal}
        score += macd_score

        weekly_change = latest.get('Weekly_Change_Pct', 0)
        daily_change = latest.get('Daily_Change_Pct', 0)
        momentum_score = 0
        if 0 < weekly_change <= 15: momentum_score += 4
        if -3 < daily_change <= 5: momentum_score += 3
        details['price_momentum'] = {'weekly': weekly_change, 'daily': daily_change}
        score += momentum_score

        passed = score >= self.min_category_scores.get('momentum', 10)
        return FilterScore('momentum', score, max_score, self.weights['momentum'], details, passed)

    def calculate_volume_score(self, df: pd.DataFrame, latest: pd.Series) -> FilterScore:
        score = 0.0; max_score = 20.0; details = {}
        rel_volume = latest.get('Relative_Volume', 1.0)
        vol_score = 12 if rel_volume >= 1.5 else (9 if rel_volume >= 1.2 else (6 if rel_volume >= 1.0 else 0))
        details['relative_volume'] = rel_volume
        score += vol_score

        volume_trend_score = 0
        if 'volume' in df.columns and len(df) >= 20:
            vol_ma10 = df['volume'].rolling(10).mean()
            vol_ma20 = df['volume'].rolling(20).mean()
            current_vol = latest.get('volume', 0)
            if current_vol > vol_ma10.iloc[-1]: volume_trend_score += 4
            if vol_ma10.iloc[-1] > vol_ma20.iloc[-1]: volume_trend_score += 4
        details['volume_trend'] = volume_trend_score > 0
        score += volume_trend_score

        passed = score >= self.min_category_scores.get('volume', 8)
        return FilterScore('volume', score, max_score, self.weights['volume'], details, passed)

    def calculate_volatility_score(self, df: pd.DataFrame, latest: pd.Series) -> FilterScore:
        score = 0.0; max_score = 15.0; details = {}
        atr_pct = (latest.get('ATR14', 0) / latest['close'] * 100) if latest['close'] > 0 else 0
        atr_score = 7 if 1 <= atr_pct <= 4 else (4 if 4 < atr_pct <= 6 else 0)
        details['atr_pct'] = atr_pct
        score += atr_score

        bb_width = latest.get('BB_Width_Pct', 0)
        bb_score = 8 if 5 <= bb_width <= 20 else (5 if 20 < bb_width <= 30 else 2)
        details['bb_width'] = bb_width
        score += bb_score

        passed = score >= 5
        return FilterScore('volatility', score, max_score, self.weights['volatility'], details, passed)

    def calculate_risk_score(self, df: pd.DataFrame, latest: pd.Series, risk_reward: Dict) -> FilterScore:
        score = 0.0; max_score = 10.0; details = {}
        rr_ratio = risk_reward.get('rr_ratio', 0)
        rr_score = 6 if rr_ratio >= 3.0 else (5 if rr_ratio >= 2.5 else (4 if rr_ratio >= 2.0 else 0))
        details['rr_ratio'] = rr_ratio
        score += rr_score

        risk_pct = risk_reward.get('risk_pct', 100)
        risk_score = 4 if risk_pct <= 3 else (3 if risk_pct <= 5 else (1 if risk_pct <= 8 else 0))
        details['risk_pct'] = risk_pct
        score += risk_score

        passed = score >= 4
        return FilterScore('risk', score, max_score, self.weights['risk'], details, passed)

    def evaluate_stock(self, df: pd.DataFrame, latest: pd.Series, risk_reward: Dict, symbol: str) -> Tuple[bool, float, Dict]:
        trend_score = self.calculate_trend_score(df, latest)
        momentum_score = self.calculate_momentum_score(df, latest)
        volume_score = self.calculate_volume_score(df, latest)
        volatility_score = self.calculate_volatility_score(df, latest)
        risk_score = self.calculate_risk_score(df, latest, risk_reward)

        total_weighted_score = (
            (trend_score.score / trend_score.max_score) * trend_score.weight +
            (momentum_score.score / momentum_score.max_score) * momentum_score.weight +
            (volume_score.score / volume_score.max_score) * volume_score.weight +
            (volatility_score.score / volatility_score.max_score) * volatility_score.weight +
            (risk_score.score / risk_score.max_score) * risk_score.weight
        )

        critical_checks = {
            'trend': trend_score.passed,
            'momentum': momentum_score.passed,
            'volume': volume_score.passed
        }

        passed = total_weighted_score >= self.min_total_score and all(critical_checks.values())

        report = {
            'symbol': symbol,
            'total_score': round(total_weighted_score, 2),
            'passed': passed,
            'categories': {
                'trend': trend_score,
                'momentum': momentum_score,
                'volume': volume_score,
                'volatility': volatility_score,
                'risk': risk_score
            },
            'critical_checks': critical_checks,
            'signal_quality': self._determine_signal_quality(total_weighted_score)
        }

        return passed, total_weighted_score, report

    def _determine_signal_quality(self, score: float) -> str:
        if score >= 85: return "🔥🔥🔥 Mükemmel"
        elif score >= 75: return "🔥🔥 Çok Güçlü"
        elif score >= 65: return "🔥 Güçlü"
        elif score >= 60: return "⚡ Orta"
        else: return "⚠️ Zayıf"