# core/types.py
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

class MarketRegime(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    NEUTRAL = "neutral"

@dataclass
class FibonacciLevel:
    level: float
    price: float
    distance_pct: float
    zone: str

@dataclass
class ConsolidationPattern:
    detected: bool
    duration: int
    range_pct: float
    breakout_type: str
    breakout_strength: float
    support: float
    resistance: float

@dataclass
class MultiTimeframeAnalysis:
    daily_trend: str
    weekly_trend: str
    alignment: bool
    weekly_rsi: float
    weekly_macd_positive: bool
    recommendation: str

@dataclass
class MarketAnalysis:
    regime: str
    trend_strength: float
    volatility: float
    volume_trend: float
    market_score: float
    recommendation: str

@dataclass
class BacktestResult:
    symbol: str
    total_trades: int
    winning_trades: int
    win_rate: float
    total_profit: float
    total_return_pct: float
    max_drawdown: float
    sharpe_ratio: float
    best_trade: float
    worst_trade: float
    avg_trade: float

@dataclass
class Trade:
    """Trade veri yapısı - GÜNCELLENMİŞ"""
    entry_price: float
    stop_loss: float
    target1: float
    target2: float
    shares: int
    risk_amount: float = field(default=0.0)  # YENİ EKLENDİ
    capital_usage_pct: float = field(default=0.0)
    risk_percentage: float = field(default=0.0)  # YENİ EKLENDİ
    rr_ratio: float = field(default=0.0)  # YENİ EKLENDİ
    entry_date: date = field(default_factory=lambda: datetime.now().date())
    status: str = "open"
    exit_reason: str = ""
    exit_price: Optional[float] = None
    exit_date: Optional[date] = None
    profit_loss: Optional[float] = None
    profit_loss_pct: Optional[float] = None
    max_profit: Optional[float] = None  # YENİ EKLENDİ
    max_loss: Optional[float] = None  # YENİ EKLENDİ
    max_favorable_excursion: Optional[float] = None 
    max_adverse_excursion: Optional[float] = None 
      
    def calculate_risk(self) -> float:
        """Risk miktarını hesapla"""
        return abs(self.entry_price - self.stop_loss) * self.shares
    
    def calculate_profit_potential(self) -> float:
        """Potansiyel karı hesapla"""
        return abs(self.target1 - self.entry_price) * self.shares

    def update_stop_loss(self, new_stop: float):
        object.__setattr__(self, 'stop_loss', new_stop)

    def update_metrics(self, current_price: float):
        if self.entry_price > 0:
            pct_change = (current_price - self.entry_price) / self.entry_price * 100
            if not hasattr(self, 'max_favorable_excursion') or pct_change > self.max_favorable_excursion:
                object.__setattr__(self, 'max_favorable_excursion', pct_change)
            if not hasattr(self, 'max_adverse_excursion') or pct_change < self.max_adverse_excursion:
                object.__setattr__(self, 'max_adverse_excursion', pct_change)

@dataclass
class FilterScore:
    category: str
    score: float
    max_score: float
    weight: float
    details: Dict
    passed: bool