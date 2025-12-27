"""
Gelişmiş Backtest Modülü - Gerçekçi Swing Trade Testi
DÜZELTİLMİŞ VERSİYON: Trade sınıfı çakışması çözüldü
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# ✅ DÜZELTME: Core Trade'i kullan
from core.types import Trade as CoreTrade

@dataclass
class BacktestTrade:
    """Backtest'e özel trade objesi - CoreTrade'den farklı"""
    entry_date: datetime
    exit_date: Optional[datetime] = None
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    stop_loss: float = 0.0
    target1: float = 0.0
    target2: float = 0.0
    shares: int = 0
    status: str = "open"
    exit_reason: str = ""
    profit: float = 0.0
    profit_pct: float = 0.0
    days_held: int = 0
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0
    
    def update_stop_loss(self, new_stop: float):
        """Stop loss güncelleme - SAFE MUTATION"""
        object.__setattr__(self, 'stop_loss', new_stop)
    
    def update_metrics(self, current_price: float):
        """MFE/MAE metriklerini güncelle"""
        if self.entry_price > 0:
            pct_change = (current_price - self.entry_price) / self.entry_price * 100
            
            if pct_change > self.max_favorable_excursion:
                object.__setattr__(self, 'max_favorable_excursion', pct_change)
            
            if pct_change < self.max_adverse_excursion:
                object.__setattr__(self, 'max_adverse_excursion', pct_change)
    
    def close_trade(self, exit_date: datetime, exit_price: float, 
                   exit_reason: str, commission_pct: float = 0.2) -> float:
        """Trade'i kapat ve kârı hesapla"""
        object.__setattr__(self, 'exit_date', exit_date)
        object.__setattr__(self, 'exit_price', exit_price)
        object.__setattr__(self, 'exit_reason', exit_reason)
        
        if self.entry_date:
            days = (exit_date - self.entry_date).days
            object.__setattr__(self, 'days_held', days)
        
        # Komisyon ve slippage dahil kâr hesapla
        entry_cost = self.shares * self.entry_price * (1 + commission_pct / 100)
        exit_value = self.shares * exit_price * (1 - commission_pct / 100)
        
        profit = exit_value - entry_cost
        profit_pct = (profit / entry_cost) * 100 if entry_cost > 0 else 0
        
        object.__setattr__(self, 'profit', profit)
        object.__setattr__(self, 'profit_pct', profit_pct)
        object.__setattr__(self, 'status', 'closed_profit' if profit > 0 else 'closed_loss')
        
        return profit

class RealisticBacktester:
    """Gerçekçi swing trade backtest - DÜZELTİLMİŞ"""
    
    def __init__(self, config, commission_pct=0.2, slippage_pct=0.1):
        self.config = config
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.trades: List[BacktestTrade] = []
        self.max_positions = 5
        self.performance_history = []
        
    def calculate_position_size(self, capital: float, risk_pct: float, 
                               entry_price: float, stop_loss: float) -> int:
        """Risk bazlı pozisyon boyutu"""
        if entry_price <= 0 or stop_loss <= 0:
            return 0
            
        risk_amount = capital * (risk_pct / 100)
        price_risk = entry_price - stop_loss
        
        if price_risk <= 0:
            return 0
            
        shares = int(risk_amount / price_risk)
        max_shares = int(capital * 0.25 / entry_price)
        
        return min(shares, max_shares)
    
    def check_entry_signal(self, df: pd.DataFrame, idx: int, hunter) -> bool:
        """Gerçekçi entry sinyali kontrolü - LOOK-AHEAD FIXED"""
        if idx < 50:
            return False
            
        # ✅ DÜZELTME: Sadece şu ana kadar olan veriyi kullan
        historical_data = df.iloc[:idx+1].copy()
        
        try:
            # ✅ DÜZELTME: Hunter'ın calculate_indicators metodunu kullan
            analyzed_data = hunter.calculate_indicators(historical_data)
            
            if analyzed_data is None or analyzed_data.empty:
                return False
                
            latest = analyzed_data.iloc[-1]
            
            # ✅ DÜZELTME: basic_filters kullan
            is_valid = self._is_swing_ok_historical(analyzed_data, latest, hunter)
            
            return is_valid
            
        except Exception as e:
            logger.warning(f"Entry signal error at idx {idx}: {e}")
            return False
    
    def _is_swing_ok_historical(self, df: pd.DataFrame, latest: pd.Series, hunter) -> bool:
        """Tarihsel swing kontrolü - DÜZELTİLMİŞ"""
        try:
            # ✅ DÜZELTME: basic_filters'ı kullan
            from filters.basic_filters import basic_filters
            
            cfg = hunter.cfg
            
            # Latest'i dict'e çevir
            latest_dict = latest.to_dict()
            latest_dict['symbol'] = 'BACKTEST'
            
            # Basic filters kontrolü
            return basic_filters(latest_dict, cfg, df)
            
        except Exception as e:
            logger.error(f"Swing check error: {e}")
            return False
    
    def check_exit_conditions(self, trade: BacktestTrade, current_date: datetime, 
                             current_price: float, current_high: float, 
                             current_low: float) -> Tuple[bool, float, str]:
        """Çıkış koşullarını kontrol et"""
        
        # 1. Stop Loss
        if current_low <= trade.stop_loss * 0.995:
            exit_price = trade.stop_loss * (1 - self.slippage_pct / 100)
            return True, exit_price, "stop_loss"
        
        # 2. Target 1
        if current_high >= trade.target1:
            exit_price = trade.target1 * (1 - self.slippage_pct / 100)
            return True, exit_price, "target1_reached"
        
        # 3. Trailing Stop
        days_held = (current_date - trade.entry_date).days
        if days_held > 5:
            current_gain_pct = (current_price - trade.entry_price) / trade.entry_price * 100
            
            if current_gain_pct > 10:
                new_stop = current_price * 0.95
                if new_stop > trade.stop_loss:
                    trade.update_stop_loss(new_stop)
        
        # 4. Maksimum elde tutma süresi
        if days_held > 30:
            return True, current_price, "max_hold_time"
        
        return False, 0.0, ""
    
    def run_backtest(self, symbol: str, df: pd.DataFrame, hunter, 
                    initial_capital: float = 10000) -> Dict:
        """Ana backtest döngüsü - DÜZELTİLMİŞ"""
        capital = initial_capital
        open_trades: List[BacktestTrade] = []
        closed_trades: List[BacktestTrade] = []
        equity_curve = []
        
        test_period = min(252, len(df) - 50)
        
        if test_period < 50:
            logger.error(f"Yetersiz veri: {symbol} - {len(df)} bar")
            return {
                'symbol': symbol,
                'error': 'Yetersiz veri',
                'trades': [],
                'metrics': {},
                'success': False
            }
        
        start_idx = max(0, len(df) - test_period)
        
        logger.info(f"Backtesting {symbol}: {test_period} bars, Capital: {capital:,.0f} TL")
        
        # Tarih indeksi kontrolü
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        for idx in range(start_idx, len(df)):
            if self._should_stop_backtest():
                break
                
            current_date = df.index[idx]
            current_row = df.iloc[idx]
            current_price = current_row['close']
            current_high = current_row['high']
            current_low = current_row['low']
            
            # 1. Açık pozisyonları kontrol et
            trades_to_remove = []
            for trade in open_trades:
                trade.update_metrics(current_price)
                
                should_exit, exit_price, exit_reason = self.check_exit_conditions(
                    trade, current_date, current_price, current_high, current_low
                )
                
                if should_exit:
                    profit = trade.close_trade(
                        current_date, exit_price, exit_reason, self.commission_pct
                    )
                    
                    capital += (trade.shares * exit_price * (1 - self.commission_pct / 100))
                    trades_to_remove.append(trade)
                    closed_trades.append(trade)
                    
                    logger.debug(f"{symbol} - Trade closed: {exit_reason}, "
                                f"P/L: {trade.profit:.2f} TL ({trade.profit_pct:.2f}%)")
            
            for trade in trades_to_remove:
                open_trades.remove(trade)
            
            # 2. Yeni pozisyon kontrolü
            if len(open_trades) < self.max_positions and capital > 1000:
                if self.check_entry_signal(df, idx, hunter):
                    historical_data = df.iloc[:idx+1].copy()
                    analyzed_data = hunter.calculate_indicators(historical_data)
                    
                    if analyzed_data is not None and not analyzed_data.empty:
                        latest = analyzed_data.iloc[-1]
                        
                        risk_reward = self._calculate_risk_reward_historical(
                            analyzed_data, latest, current_price
                        )
                        
                        stop_loss = risk_reward['stop_loss']
                        target1 = risk_reward['target1']
                        target2 = risk_reward['target2']
                        
                        if stop_loss <= 0 or stop_loss >= current_price * 0.9:
                            continue
                        
                        max_risk_pct = self.config.get('max_risk_pct', 2.0)
                        shares = self.calculate_position_size(
                            capital, max_risk_pct, current_price, stop_loss
                        )
                        
                        if shares > 0:
                            actual_entry = current_price * (1 + self.slippage_pct / 100)
                            entry_cost = shares * actual_entry * (1 + self.commission_pct / 100)
                            
                            if entry_cost <= capital:
                                trade = BacktestTrade(
                                    entry_date=current_date,
                                    entry_price=actual_entry,
                                    stop_loss=stop_loss,
                                    target1=target1,
                                    target2=target2,
                                    shares=shares
                                )
                                
                                capital -= entry_cost
                                open_trades.append(trade)
                                
                                logger.info(f"{symbol} - New position: {shares} shares "
                                          f"@ {actual_entry:.2f}, Stop: {stop_loss:.2f}")
            
            # 3. Equity curve güncelle
            open_value = sum(t.shares * current_price for t in open_trades)
            total_equity = capital + open_value
            equity_curve.append({
                'date': current_date,
                'equity': total_equity,
                'cash': capital,
                'open_positions': len(open_trades),
                'open_value': open_value
            })
        
        # Backtest sonu - açık pozisyonları kapat
        for trade in open_trades:
            final_price = df.iloc[-1]['close']
            profit = trade.close_trade(
                df.index[-1], final_price, 'backtest_end', self.commission_pct
            )
            closed_trades.append(trade)
        
        # Performans metrikleri
        results = self.calculate_performance_metrics(
            closed_trades, equity_curve, initial_capital
        )
        
        return {
            'symbol': symbol,
            'trades': closed_trades,
            'equity_curve': equity_curve,
            'metrics': results,
            'success': True
        }
    
    def _calculate_risk_reward_historical(self, df: pd.DataFrame, 
                                         latest: pd.Series, 
                                         current_price: float) -> Dict:
        """Tarihsel risk/reward hesapla"""
        try:
            # ATR bazlı stop
            atr = latest.get('ATR14', 0)
            atr_stop = current_price - (self.config.get('atr_stop_multiplier', 2.0) * atr)
            
            # Swing low stop
            lookback = self.config.get('stop_loss_lookback', 20)
            recent_lows = df['low'].tail(min(lookback, len(df)))
            swing_stop = recent_lows.min() * 0.98 if len(recent_lows) > 0 else current_price * 0.95
            
            # En iyi stop'u seç
            stop_loss = max(atr_stop, swing_stop)
            
            # Target'lar
            risk = current_price - stop_loss
            target1 = current_price + (risk * self.config.get('target1_multiplier', 2.0))
            target2 = current_price + (risk * self.config.get('target2_multiplier', 3.0))
            
            rr_ratio = (target1 - current_price) / risk if risk > 0 else 0
            risk_pct = (risk / current_price) * 100
            
            return {
                'stop_loss': round(stop_loss, 2),
                'target1': round(target1, 2),
                'target2': round(target2, 2),
                'rr_ratio': round(rr_ratio, 2),
                'risk_pct': round(risk_pct, 2)
            }
        except Exception as e:
            logger.error(f"Risk/reward error: {e}")
            return {
                'stop_loss': current_price * 0.95,
                'target1': current_price * 1.06,
                'target2': current_price * 1.10,
                'rr_ratio': 2.0,
                'risk_pct': 5.0
            }
    
    def _should_stop_backtest(self) -> bool:
        """Backtest'i durdurma koşulu"""
        return False
    
    def calculate_performance_metrics(self, trades: List[BacktestTrade], 
                                     equity_curve: List[Dict], 
                                     initial_capital: float) -> Dict:
        """Detaylı performans metrikleri"""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'total_return_pct': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'expectancy': 0.0,
                'avg_days_held': 0.0,
                'avg_mfe': 0.0,
                'avg_mae': 0.0,
                'initial_capital': initial_capital,
                'final_equity': initial_capital
            }
        
        winning_trades = [t for t in trades if t.profit > 0]
        losing_trades = [t for t in trades if t.profit <= 0]
        
        total_trades = len(trades)
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        total_profit = sum(t.profit for t in trades)
        total_return_pct = (total_profit / initial_capital) * 100
        
        avg_win = np.mean([t.profit for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.profit for t in losing_trades]) if losing_trades else 0
        
        total_win = sum(t.profit for t in winning_trades)
        total_loss = abs(sum(t.profit for t in losing_trades))
        profit_factor = total_win / total_loss if total_loss > 0 else float('inf')
        
        if equity_curve:
            equity_values = [e['equity'] for e in equity_curve]
            peak = np.maximum.accumulate(equity_values)
            drawdowns = (equity_values - peak) / peak * 100
            max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
        else:
            max_drawdown = 0
        
        if equity_curve and len(equity_curve) > 1:
            equity_series = pd.Series([e['equity'] for e in equity_curve])
            returns = equity_series.pct_change().dropna()
            if len(returns) > 1 and returns.std() > 0:
                sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
            else:
                sharpe = 0
        else:
            sharpe = 0
        
        expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)
        
        avg_days_held = np.mean([t.days_held for t in trades]) if trades else 0
        avg_mfe = np.mean([t.max_favorable_excursion for t in trades]) if trades else 0
        avg_mae = np.mean([t.max_adverse_excursion for t in trades]) if trades else 0
        
        final_equity = initial_capital + total_profit
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'total_profit': round(total_profit, 2),
            'total_return_pct': round(total_return_pct, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown': round(max_drawdown, 2),
            'sharpe_ratio': round(sharpe, 2),
            'expectancy': round(expectancy, 2),
            'avg_days_held': round(avg_days_held, 1),
            'avg_mfe': round(avg_mfe, 2),
            'avg_mae': round(avg_mae, 2),
            'initial_capital': initial_capital,
            'final_equity': round(final_equity, 2)
        }
    
    def generate_backtest_report(self, results: Dict) -> str:
        """Backtest raporu oluştur"""
        metrics = results.get('metrics', {})
        
        report = f"""
        📊 BACKTEST RAPORU: {results.get('symbol', 'N/A')}
        {'='*50}
        
        📈 PERFORMANS METRİKLERİ:
        • Toplam İşlem: {metrics.get('total_trades', 0)}
        • Başarı Oranı: {metrics.get('win_rate', 0):.1f}%
        • Toplam Kâr: {metrics.get('total_profit', 0):,.2f} TL
        • Getiri %: {metrics.get('total_return_pct', 0):.2f}%
        • Max Çekilme: {metrics.get('max_drawdown', 0):.2f}%
        • Sharpe Oranı: {metrics.get('sharpe_ratio', 0):.2f}
        
        💰 SERMAYE:
        • Başlangıç: {metrics.get('initial_capital', 0):,.0f} TL
        • Son Durum: {metrics.get('final_equity', 0):,.0f} TL
        • Net Değişim: {metrics.get('final_equity', 0) - metrics.get('initial_capital', 0):,.0f} TL
        """
        
        return report
