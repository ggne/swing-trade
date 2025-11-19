"""
Gelişmiş Backtest Modülü
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
import logging

@dataclass
class Trade:
    entry_date: datetime
    exit_date: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    stop_loss: float
    target1: float
    target2: float
    shares: int
    status: str
    exit_reason: str = ""
    profit: float = 0.0
    profit_pct: float = 0.0

class RealisticBacktester:
    def __init__(self, config, commission_pct=0.2, slippage_pct=0.1):
        self.config = config
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.trades: List[Trade] = []
        self.max_positions = 5
    
    def calculate_position_size(self, capital, risk_pct, entry_price, stop_loss):
        risk_amount = capital * (risk_pct / 100)
        price_risk = entry_price - stop_loss
        
        if price_risk <= 0:
            return 0
            
        shares = int(risk_amount / price_risk)
        max_shares = int(capital * 0.25 / entry_price)
        
        return min(shares, max_shares)
    
    def run_backtest(self, symbol, df, hunter, initial_capital=10000):
        capital = initial_capital
        open_trades: List[Trade] = []
        closed_trades: List[Trade] = []
        
        test_period = min(252, len(df) - 50)
        start_idx = len(df) - test_period
        
        logging.info(f"Backtesting {symbol}: {test_period} bars, Capital: {capital:,.0f} TL")
        
        for idx in range(start_idx, len(df)):
            current_date = df.index[idx]
            current_row = df.iloc[idx]
            current_price = current_row['close']
            
            # Açık pozisyonları kontrol et
            for trade in open_trades[:]:
                should_exit = False
                exit_price = 0.0
                exit_reason = ""
                
                # Stop loss kontrolü
                if current_price <= trade.stop_loss:
                    should_exit = True
                    exit_price = trade.stop_loss * (1 - self.slippage_pct / 100)
                    exit_reason = "stop_loss"
                
                # Target kontrolü
                elif current_price >= trade.target1:
                    should_exit = True
                    exit_price = trade.target1 * (1 - self.slippage_pct / 100)
                    exit_reason = "target_reached"
                
                if should_exit:
                    trade.exit_date = current_date
                    trade.exit_price = exit_price
                    trade.days_held = (current_date - trade.entry_date).days
                    
                    entry_cost = trade.shares * trade.entry_price * (1 + self.commission_pct / 100)
                    exit_value = trade.shares * exit_price * (1 - self.commission_pct / 100)
                    
                    trade.profit = exit_value - entry_cost
                    trade.profit_pct = (trade.profit / entry_cost) * 100
                    trade.exit_reason = exit_reason
                    trade.status = 'closed_profit' if trade.profit > 0 else 'closed_loss'
                    
                    capital += exit_value
                    open_trades.remove(trade)
                    closed_trades.append(trade)
            
            # Yeni pozisyon kontrolü
            if len(open_trades) < self.max_positions and capital > 1000:
                try:
                    historical_data = df.iloc[:idx+1].copy()
                    analyzed_data = hunter.calculate_indicators(historical_data)
                    latest = analyzed_data.iloc[-1]
                    
                    if hunter._basic_filters(latest):
                        risk_reward = hunter._calculate_stops_targets(
                            analyzed_data, latest, {}, hunter._empty_consolidation()
                        )
                        
                        stop_loss, target1, target2 = risk_reward
                        
                        if stop_loss > 0 and stop_loss < current_price * 0.9:
                            max_risk_pct = self.config.get('max_risk_pct', 2.0)
                            shares = self.calculate_position_size(
                                capital, max_risk_pct, current_price, stop_loss
                            )
                            
                            if shares > 0:
                                actual_entry = current_price * (1 + self.slippage_pct / 100)
                                entry_cost = shares * actual_entry * (1 + self.commission_pct / 100)
                                
                                if entry_cost <= capital:
                                    trade = Trade(
                                        entry_date=current_date,
                                        exit_date=None,
                                        entry_price=actual_entry,
                                        exit_price=None,
                                        stop_loss=stop_loss,
                                        target1=target1,
                                        target2=target2,
                                        shares=shares,
                                        status='open'
                                    )
                                    
                                    capital -= entry_cost
                                    open_trades.append(trade)
                except Exception as e:
                    logging.warning(f"Entry sinyal hatası: {e}")
        
        # Açık pozisyonları kapat
        for trade in open_trades:
            final_price = df.iloc[-1]['close']
            trade.exit_date = df.index[-1]
            trade.exit_price = final_price
            
            entry_cost = trade.shares * trade.entry_price * (1 + self.commission_pct / 100)
            exit_value = trade.shares * final_price * (1 - self.commission_pct / 100)
            
            trade.profit = exit_value - entry_cost
            trade.profit_pct = (trade.profit / entry_cost) * 100
            trade.status = 'closed_profit' if trade.profit > 0 else 'closed_loss'
            trade.exit_reason = 'backtest_end'
            
            closed_trades.append(trade)
        
        # Performans metrikleri
        results = self.calculate_performance_metrics(closed_trades, initial_capital)
        
        return {
            'symbol': symbol,
            'trades': closed_trades,
            'metrics': results
        }
    
    def calculate_performance_metrics(self, trades, initial_capital):
        if not trades:
            return {}
        
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.profit > 0]
        losing_trades = [t for t in trades if t.profit <= 0]
        
        total_profit = sum(t.profit for t in trades)
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        avg_win = np.mean([t.profit for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.profit for t in losing_trades]) if losing_trades else 0
        
        profit_factor = abs(sum(t.profit for t in winning_trades) / 
                           sum(t.profit for t in losing_trades)) if losing_trades else float('inf')
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_profit': total_profit,
            'total_return_pct': (total_profit / initial_capital) * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor
        }
    
    def _empty_consolidation(self):
        from swing_analyzer_ultimate import ConsolidationPattern
        return ConsolidationPattern(False, 0, 0, 'none', 0, 0, 0)