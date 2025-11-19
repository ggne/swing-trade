"""
Akıllı Çok Katmanlı Filtre Sistemi
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

class MarketRegime(Enum):
    BULL = "bull"
    BEAR = "bear" 
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"

@dataclass
class FilterScore:
    category: str
    score: float
    max_score: float
    weight: float
    details: Dict
    passed: bool

class SmartFilterSystem:
    def __init__(self, config):
        self.config = config
        self.weights = {
            'trend': 30, 'momentum': 25, 'volume': 20, 
            'volatility': 15, 'risk': 10
        }
        self.min_total_score = config.get('min_total_score', 60)
        self.min_category_scores = {
            'trend': 15, 'momentum': 10, 'volume': 8
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
            return MarketRegime.BULL if slope_20 > 5 else MarketRegime.SIDEWAYS
        elif current_price < ema20.iloc[-1] < ema50.iloc[-1]:
            return MarketRegime.BEAR
        
        returns = close.pct_change()
        volatility = returns.std() * np.sqrt(252)
        return MarketRegime.VOLATILE if volatility > 0.4 else MarketRegime.SIDEWAYS
    
    def adjust_filters_for_regime(self, regime: MarketRegime):
        if regime == MarketRegime.BULL:
            return {'min_rsi': 35, 'max_rsi': 75, 'min_trend_score': 55}
        elif regime == MarketRegime.BEAR:
            return {'min_rsi': 40, 'max_rsi': 65, 'min_trend_score': 70}
        elif regime == MarketRegime.VOLATILE:
            return {'max_atr14_pct': 5.0, 'max_daily_change_pct': 5.0}
        else:
            return {'check_consolidation': True, 'max_consolidation_range': 8.0}
    
    def calculate_trend_score(self, df: pd.DataFrame, latest: pd.Series) -> FilterScore:
        score = 0.0
        details = {}
        
        # EMA düzeni
        if latest['close'] > latest.get('EMA20', 0):
            score += 4
            if latest.get('EMA20', 0) > latest.get('EMA50', 0):
                score += 6
        
        # EMA eğimleri
        ema20_slope = df['EMA20'].pct_change(5).iloc[-1] * 100 if 'EMA20' in df.columns else 0
        if ema20_slope > 0.05: score += 5
        elif ema20_slope > 0: score += 2
        
        # ADX
        adx = latest.get('ADX', 0)
        if adx > 30: score += 10
        elif adx > 25: score += 7
        elif adx > 20: score += 4
        
        passed = score >= self.min_category_scores.get('trend', 15)
        return FilterScore('trend', score, 30, self.weights['trend'], details, passed)
    
    def calculate_momentum_score(self, df: pd.DataFrame, latest: pd.Series) -> FilterScore:
        score = 0.0
        details = {}
        
        # RSI
        rsi = latest.get('RSI', 50)
        if 40 <= rsi <= 60: score += 10
        elif 35 <= rsi <= 65: score += 7
        elif 30 <= rsi <= 70: score += 4
        
        # MACD
        if latest.get('MACD_Level', 0) > latest.get('MACD_Signal', 0):
            score += 4
            if len(df) > 1 and df['MACD_Hist'].iloc[-1] > df['MACD_Hist'].iloc[-2]:
                score += 4
        
        passed = score >= self.min_category_scores.get('momentum', 10)
        return FilterScore('momentum', score, 25, self.weights['momentum'], details, passed)
    
    def evaluate_stock(self, df: pd.DataFrame, latest: pd.Series, risk_reward: Dict, symbol: str):
        trend_score = self.calculate_trend_score(df, latest)
        momentum_score = self.calculate_momentum_score(df, latest)
        
        total_weighted_score = (
            (trend_score.score / trend_score.max_score) * trend_score.weight +
            (momentum_score.score / momentum_score.max_score) * momentum_score.weight
        )
        
        critical_checks = {
            'trend': trend_score.passed,
            'momentum': momentum_score.passed
        }
        
        passed = (total_weighted_score >= self.min_total_score and 
                 all(critical_checks.values()))
        
        report = {
            'symbol': symbol,
            'total_score': round(total_weighted_score, 2),
            'passed': passed,
            'signal_quality': self._determine_signal_quality(total_weighted_score)
        }
        
        return passed, total_weighted_score, report
    
    def _determine_signal_quality(self, score: float) -> str:
        if score >= 85: return "🔥🔥🔥 Mükemmel"
        elif score >= 75: return "🔥🔥 Çok Güçlü"
        elif score >= 65: return "🔥 Güçlü"
        elif score >= 60: return "⚡ Orta"
        else: return "⚠️ Zayıf"