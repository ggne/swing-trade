# scanner/swing_hunter.py - TAM DÜZELTİLMİŞ VERSİYON
import logging
import time
import random
from typing import Dict, List, Optional
from tvDatafeed import TvDatafeed, Interval

# Core
from core.types import MarketAnalysis, MultiTimeframeAnalysis, ConsolidationPattern
from core.utils import load_config, setup_logging

# Modüller
from indicators.ta_manager import calculate_indicators
from filters.basic_filters import basic_filters
from risk.stop_target_manager import _calculate_stops_targets
from risk.trade_validator import validate_trade_parameters, calculate_trade_plan
from analysis.trend_score import calculate_advanced_trend_score
from analysis.multi_timeframe import analyze_multi_timeframe_from_data
from analysis.fibonacci import calculate_fibonacci_levels
from analysis.consolidation import detect_consolidation_pattern
from analysis.support_resistance import SupportResistanceFinder
from analysis.market_condition import analyze_market_condition, _empty_market_analysis
from patterns.price_action import PriceActionDetector
from smart_filter.smart_filter import SmartFilterSystem
from backtest.backtester import RealisticBacktester
from scanner.parallel_scanner import ParallelScanner
from cache.data_cache import DataCache, ErrorHandler


class SwingHunterUltimate:
    def __init__(self, config_path='swing_config.json'):
        self.cfg = load_config(config_path)
        setup_logging(self.cfg.get("log_file", "swing_hunter_ultimate.log"))
        self.tv = TvDatafeed()
        self.error_handler = ErrorHandler()
        self.data_cache = DataCache(
            cache_dir=self.cfg.get('cache_dir', 'data_cache'),
            ttl_hours=self.cfg.get('cache_ttl_hours', 1)
        )
        self.pattern_detector = PriceActionDetector()
        self.sr_finder = SupportResistanceFinder()
        self.smart_filter = SmartFilterSystem(self.cfg)
        self.backtester = RealisticBacktester(self.cfg)
        self.parallel_scanner = ParallelScanner(self, max_workers=self.cfg.get('max_workers', 4))
        self.market_analysis = None
        import threading
        self._stop_event = threading.Event()
        
        # ✅ KRİTİK DÜZELTME: stop_scan attribute'u ekle
        self.stop_scan = False
        
        logging.info("🚀 SwingHunterUltimate başlatıldı (modüler sürüm)")

    def safe_api_call(self, symbol, exchange, interval, n_bars):
        """Interval artık tvDatafeed.Interval enum olmalı!"""
        # Cache key için interval string'e çevrilmeli
        cache_key = interval if isinstance(interval, str) else str(interval)
        cached = self.data_cache.get(symbol, cache_key, n_bars)
        if cached is not None:
            return cached
        
        for attempt in range(3):
            try:
                time.sleep(random.uniform(0.1, 0.3))
                data = self.tv.get_hist(symbol=symbol, exchange=exchange, interval=interval, n_bars=n_bars)
                if data is not None and not data.empty:
                    self.data_cache.set(symbol, cache_key, n_bars, data)
                    return data
            except Exception as e:
                if attempt == 2:
                    logging.error(f"API hatası {symbol}: {e}")
        return None

    def analyze_market_condition(self):
        """Piyasa durumu analizi - BIST100 - GÜVENLİ"""
        if self.market_analysis is not None:
            return self.market_analysis
        try:
            bist_data = self.safe_api_call('XU100', 'BIST', Interval.in_daily, 100)
            
            # ✅ DÜZELTME: None kontrolü
            if bist_data is None or len(bist_data) < 50:
                self.market_analysis = _empty_market_analysis()
                return self.market_analysis

            df = calculate_indicators(bist_data)
            latest = df.iloc[-1]

            # Trend gücü
            trend_strength = 0
            if latest['close'] > latest['EMA20'] > latest['EMA50']:
                trend_strength += 40
            elif latest['close'] > latest['EMA20']:
                trend_strength += 20
            if latest.get('ADX', 0) > 25:
                trend_strength += 30
            elif latest.get('ADX', 0) > 20:
                trend_strength += 15
            if latest.get('MACD_Level', 0) > latest.get('MACD_Signal', 0):
                trend_strength += 30
            trend_strength = min(trend_strength, 100)

            # Volatilite
            returns = df['close'].pct_change().dropna()
            volatility = returns.std() * (252 ** 0.5) * 100 if len(returns) > 1 else 25.0

            # Hacim trendi
            volume_trend = latest['volume'] / df['volume'].rolling(20).mean().iloc[-1] if 'volume' in df.columns else 1.0

            # Piyasa skoru
            vol_score = max(0, 100 - volatility * 2)
            vol_trend_score = min(volume_trend * 50, 100)
            market_score = (trend_strength * 0.4) + (vol_score * 0.3) + (vol_trend_score * 0.3)

            # Rejim
            if trend_strength >= 70 and volatility < 25:
                regime = "bullish"
            elif trend_strength <= 30 and volatility > 35:
                regime = "bearish"
            elif volatility > 40:
                regime = "volatile"
            elif 40 <= trend_strength <= 60 and volatility < 30:
                regime = "sideways"
            else:
                regime = "neutral"

            recommendations = {
                "bullish": "🟢 AĞIRLIKLI ALIM",
                "bearish": "🔴 DİKKATLİ ALIM",
                "volatile": "🟡 SEÇİCİ ALIM",
                "sideways": "🔵 DİKEY PAZAR",
                "neutral": "⚪ NÖTR"
            }
            recommendation = recommendations.get(regime, "⚪ NÖTR")

            self.market_analysis = MarketAnalysis(
                regime=regime,
                trend_strength=round(trend_strength, 1),
                volatility=round(volatility, 1),
                volume_trend=round(volume_trend, 2),
                market_score=round(market_score, 1),
                recommendation=recommendation
            )
            return self.market_analysis
        except Exception as e:
            logging.error(f"Piyasa analizi hatası: {e}")
            self.market_analysis = _empty_market_analysis()
            return self.market_analysis

    def analyze_multi_timeframe(self, symbol: str, exchange: str) -> MultiTimeframeAnalysis:
        try:
            # Günlük veri
            df_daily = self.safe_api_call(symbol, exchange, Interval.in_daily, 100)
            
            # Haftalık veri
            df_weekly = self.safe_api_call(symbol, exchange, Interval.in_weekly, 52)
            
            if df_daily is None or df_weekly is None:
                return MultiTimeframeAnalysis('unknown', 'unknown', False, 50.0, False, 'hold')
            
            return analyze_multi_timeframe_from_data(df_daily, df_weekly)
            
        except Exception as e:
            logging.error(f"MTF analiz hatası {symbol}: {e}")
            return MultiTimeframeAnalysis('unknown', 'unknown', False, 50.0, False, 'hold')

    def process_symbol_advanced(self, symbol: str) -> Optional[Dict]:
        try:
            if self.stop_scan:
                return None
            logging.info(f"🔍 {symbol} analiz ediliyor...")

            # Piyasa analizi
            if self.market_analysis is None:
                self.market_analysis = self.analyze_market_condition()
            
            # ✅ DÜZELTME: Güvenlik kontrolü
            if self.market_analysis is None:
                self.market_analysis = _empty_market_analysis()

            # Veri çek (GÜNLÜK)
            df = self.safe_api_call(
                symbol,
                self.cfg['exchange'],
                Interval.in_daily,
                self.cfg['lookback_bars']
            )
            if df is None or len(df) < 50:
                return None

            df = calculate_indicators(df)
            if df.empty:
                return None
            latest = df.iloc[-1]

            # 1. Temel filtreler
            if not basic_filters(latest, self.cfg, df):
                return None

            # 2. Pattern analizi
            patterns = self.pattern_detector.analyze_patterns(df)
            pattern_score = self.pattern_detector.get_pattern_score(patterns)

            # 3. Analizler
            fib_analysis = calculate_fibonacci_levels(df) if self.cfg.get('use_fibonacci', True) else {}
            sr_levels = self.sr_finder.find_levels(df) if self.cfg.get('use_support_resistance', True) else {}
            breakout_info = self.sr_finder.check_breakout(df, sr_levels) if sr_levels else {'breakout': False}
            consolidation = detect_consolidation_pattern(df) if self.cfg.get('use_consolidation', True) else ConsolidationPattern(False,0,0,'',0,0,0)
            mtf_analysis = self.analyze_multi_timeframe(symbol, self.cfg['exchange']) if self.cfg.get('use_multi_timeframe', True) else MultiTimeframeAnalysis('unknown','unknown',False,50.0,False,'hold')

            # 4. Skor
            score = calculate_advanced_trend_score(
                df, symbol, self.cfg,
                market_analysis={'regime': self.market_analysis.regime, 'levels': sr_levels}
            )
            
            total_score = min(score['total_score'] + pattern_score * 0.5, 100)
            
            if not score['passed']:
                return None

            # 5. Stop / Target
            stop_loss, target1, target2 = _calculate_stops_targets(df, symbol, self.cfg)
            if stop_loss is None or stop_loss >= latest['close']:
                stop_loss = latest['close'] * 0.95
                risk = latest['close'] - stop_loss
                target1 = latest['close'] + risk * 2
                target2 = latest['close'] + risk * 3

            rr_ratio = (target1 - latest['close']) / (latest['close'] - stop_loss) if stop_loss < latest['close'] else 0
            risk_pct = ((latest['close'] - stop_loss) / latest['close']) * 100

            # 6. Validasyon
            validation = validate_trade_parameters(latest['close'], stop_loss, target1, target2, self.cfg)
            if not validation['valid']:
                return None
            
            # 7. Trade Plan
            trade = calculate_trade_plan(latest['close'], stop_loss, target1, target2, self.cfg, self.cfg.get('initial_capital', 10000))
            if trade is None:
                return None

            # 8. Smart Filter
            if self.cfg.get('use_smart_filter', True):
                passed, smart_score, _ = self.smart_filter.evaluate_stock(
                    df, latest, {'rr_ratio': rr_ratio, 'risk_pct': risk_pct}, symbol
                )
                if not passed:
                    return None
                total_score = max(total_score, smart_score)

            # 9. Sonuç
            signal_strength = "🔥 Güçlü" if total_score >= 75 else "⚡ Orta"
            if pattern_score >= 15:
                signal_strength = "🎯 " + signal_strength

            return {
                'Hisse': symbol,
                'Fiyat': f"{latest['close']:.2f}",
                'Sinyal': signal_strength,
                'Skor': f"{int(total_score)}/100",
                'Pattern Skor': f"{pattern_score}/20",
                'Bullish Patternler': ", ".join([p for p, d in patterns.items() if d]) or "Yok",
                'Optimal Giriş': f"{latest['close']:.2f}",
                'Stop Loss': f"{stop_loss:.2f}",
                'Hedef 1': f"{target1:.2f}",
                'Hedef 2': f"{target2:.2f}",
                'R/R': f"1:{rr_ratio:.1f}",
                'Risk %': f"{risk_pct:.1f}",
                'Pozisyon': f"{trade.shares} adet",
                'Yatırım': f"{trade.shares * latest['close']:,.0f} TL",
                'Piyasa': self.market_analysis.regime.title(),
                'Piyasa Skoru': f"{self.market_analysis.market_score:.0f}/100"
            }

        except Exception as e:
            logging.error(f"❌ {symbol} hatası: {e}")
            return None

    def run_advanced_scan(self, symbols: List[str], progress_callback=None):
        if self.cfg.get('use_parallel_scan', True) and len(symbols) > 10:
            return self.parallel_scanner.scan_parallel(symbols, progress_callback)
        else:
            results = []
            for i, sym in enumerate(symbols):
                if self.stop_scan:
                    break
                if progress_callback:
                    progress_callback(int((i+1)/len(symbols)*100), f"{i+1}/{len(symbols)} - {sym}")
                res = self.process_symbol_advanced(sym)
                if res:
                    results.append(res)
            return {"Swing Uygun": sorted(results, key=lambda x: float(x['Skor'].split('/')[0]), reverse=True)}

    # ✅ YENİ METOD: Backtest için
    def run_backtest(self, symbols: List[str], days: int = 180) -> Dict:
        """
        Batch backtest - birden fazla sembol için
        """
        try:
            all_results = []
            
            for i, symbol in enumerate(symbols):
                if self.stop_scan:
                    break
                
                logging.info(f"Backtest {i+1}/{len(symbols)}: {symbol}")
                
                # Veri çek
                df = self.safe_api_call(
                    symbol,
                    self.cfg['exchange'],
                    Interval.in_daily,
                    days + 50  # Ekstra veri
                )
                
                if df is None or len(df) < 100:
                    logging.warning(f"{symbol}: Yetersiz veri")
                    continue
                
                # Backtest çalıştır
                result = self.backtester.run_backtest(
                    symbol=symbol,
                    df=df,
                    hunter=self,
                    initial_capital=self.cfg.get('initial_capital', 10000)
                )
                
                if result.get('success', False):
                    all_results.append(result)
            
            # Özet oluştur
            if not all_results:
                return {
                    'summary': {
                        'total_symbols': len(symbols),
                        'total_trades': 0,
                        'win_rate': 0.0,
                        'total_profit': 0.0
                    },
                    'detailed': [],
                    'note': 'Hiç başarılı backtest yapılamadı'
                }
            
            # Özet metrikleri hesapla
            total_trades = sum(r['metrics']['total_trades'] for r in all_results)
            winning_trades = sum(r['metrics']['winning_trades'] for r in all_results)
            total_profit = sum(r['metrics']['total_profit'] for r in all_results)
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            best_result = max(all_results, key=lambda x: x['metrics']['total_profit'])
            worst_result = min(all_results, key=lambda x: x['metrics']['total_profit'])
            
            summary = {
                'total_symbols': len(symbols),
                'tested_symbols': len(all_results),
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': round(win_rate, 2),
                'total_profit': round(total_profit, 2),
                'avg_return': round(total_profit / len(all_results), 2),
                'best_symbol': best_result['symbol'],
                'worst_symbol': worst_result['symbol']
            }
            
            # Detaylı sonuçlar
            detailed = []
            for r in all_results:
                detailed.append({
                    'Symbol': r['symbol'],
                    'Trades': r['metrics']['total_trades'],
                    'Win Rate %': r['metrics']['win_rate'],
                    'Total Return %': r['metrics']['total_return_pct'],
                    'Total Profit': r['metrics']['total_profit'],
                    'Max Drawdown %': r['metrics']['max_drawdown'],
                    'Sharpe Ratio': r['metrics']['sharpe_ratio']
                })
            
            return {
                'summary': summary,
                'detailed': detailed,
                'raw_results': all_results
            }
            
        except Exception as e:
            logging.error(f"Batch backtest hatası: {e}")
            return {
                'summary': {'total_symbols': len(symbols), 'total_trades': 0},
                'detailed': [],
                'error': str(e)
            }

    # ✅ YENİ METOD: Backtester uyumluluğu için
    def calculate_indicators(self, df):
        """Wrapper metod - ta_manager'ın calculate_indicators'ını çağırır"""
        return calculate_indicators(df)

    def stop_scanning(self):
        """Taramayı durdur - DÜZELTİLDİ"""
        self.stop_scan = True
        self._stop_event.set()

    def calculate_trade_plan(self, symbol, entry_price, stop_loss, target1, capital):
        """Trade planını hesaplar - GUI için özel metod."""
        try:
            target2 = target1 * 1.3
            
            trade = calculate_trade_plan(
                entry_price=entry_price,
                stop_loss=stop_loss,
                target1=target1,
                target2=target2,
                config=self.cfg,
                account_balance=capital
            )
            
            if trade:
                risk_per_share = abs(entry_price - stop_loss)
                max_loss_tl = risk_per_share * trade.shares
                max_gain_tl = (target1 - entry_price) * trade.shares
                rr_ratio = (target1 - entry_price) / risk_per_share if risk_per_share > 0 else 0
                
                return {
                    'risk_per_share': risk_per_share,
                    'capital': capital,
                    'risk_pct': self.cfg.get('max_risk_pct', 2.0),
                    'shares': trade.shares,
                    'investment': entry_price * trade.shares,
                    'max_loss_tl': max_loss_tl,
                    'max_loss_pct': (max_loss_tl / capital) * 100 if capital > 0 else 0,
                    'max_gain_tl': max_gain_tl,
                    'rr_ratio': rr_ratio,
                    'recommendation': '✅ Uygun' if trade.shares > 0 else '❌ Risk yüksek'
                }
            else:
                return {
                    'risk_per_share': abs(entry_price - stop_loss),
                    'capital': capital,
                    'risk_pct': 0,
                    'shares': 0,
                    'investment': 0,
                    'max_loss_tl': 0,
                    'max_loss_pct': 0,
                    'max_gain_tl': 0,
                    'rr_ratio': 0,
                    'recommendation': '❌ Trade planı oluşturulamadı'
                }
                
        except Exception as e:
            logging.error(f"Trade plan hesaplama hatası: {e}")
            return {
                'risk_per_share': 0,
                'capital': capital,
                'risk_pct': 0,
                'shares': 0,
                'investment': 0,
                'max_loss_tl': 0,
                'max_loss_pct': 0,
                'max_gain_tl': 0,
                'rr_ratio': 0,
                'recommendation': f'❌ Hata: {str(e)}'
            }

    def validate_trade_parameters(self, entry_price, stop_loss, target1, symbol):
        """Trade parametrelerini doğrular - GUI için özel metod."""
        try:
            target2 = target1 * 1.3
            
            result = validate_trade_parameters(
                entry_price=entry_price,
                stop_loss=stop_loss,
                target1=target1,
                target2=target2,
                config=self.cfg
            )
            
            score = 80 if result.get('valid', False) else 40
            warnings = []
            errors = []
            
            if not result.get('valid', False):
                errors.append(result.get('reason', 'Bilinmeyen hata'))
            
            rr_ratio = result.get('rr_ratio', 0)
            if rr_ratio < 1.5:
                warnings.append(f"Risk/Ödül oranı düşük: {rr_ratio:.1f}")
            
            risk_distance = abs(entry_price - stop_loss)
            if risk_distance / entry_price > 0.15:
                warnings.append("Stop loss çok uzak (%{:.1f} risk)".format((risk_distance / entry_price) * 100))
            
            return {
                'score': score,
                'is_valid': result.get('valid', False),
                'has_warnings': len(warnings) > 0,
                'warnings': warnings,
                'errors': errors,
                'rr_ratio': rr_ratio
            }
            
        except Exception as e:
            logging.error(f"Trade validasyon hatası: {e}")
            return {
                'score': 0,
                'is_valid': False,
                'has_warnings': True,
                'warnings': [],
                'errors': [f"Validasyon hatası: {str(e)}"],
                'rr_ratio': 0
            }

    def save_to_excel(self, results):
        import pandas as pd
        from datetime import datetime
        if not results.get("Swing Uygun"):
            return None
        df = pd.DataFrame(results["Swing Uygun"])
        filename = f"Swing_Rapor_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        df.to_excel(filename, index=False)
        return filename
