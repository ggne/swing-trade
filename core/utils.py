# core/utils.py
import json
import logging
import os
import random
import time
from tvDatafeed import TvDatafeed

def setup_logging(log_file='swing_hunter_ultimate.log'):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def load_config(path):
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except FileNotFoundError:
        default = {
            "symbols": ["AKBNK", "GARAN"],
            "exchange": "BIST",
            "lookback_bars": 250,
            "min_rsi": 30,
            "max_rsi": 70,
            "min_trend_score": 50,
            "min_relative_volume": 1.0,
            "max_daily_change_pct": 8.0,
            "min_risk_reward_ratio": 2.0,
            "max_risk_pct": 5.0,
            "use_multi_timeframe": True,
            "use_fibonacci": True,
            "use_consolidation": True,
            "use_smart_filter": True,
            "min_total_score": 60,
            "max_workers": 4,
            "use_parallel_scan": True,
            "cache_ttl_hours": 1,
            "initial_capital": 10000
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        return default

def safe_api_call(tv: TvDatafeed, cache, symbol, exchange, interval, n_bars):
    cached = cache.get(symbol, str(interval), n_bars)
    if cached is not None:
        return cached
    for attempt in range(3):
        try:
            time.sleep(random.uniform(0.1, 0.3))
            data = tv.get_hist(symbol=symbol, exchange=exchange, interval=interval, n_bars=n_bars)
            if data is not None and not data.empty:
                cache.set(symbol, str(interval), n_bars, data)
                return data
        except Exception as e:
            if attempt == 2:
                logging.error(f"API hatası {symbol}: {e}")
    return None