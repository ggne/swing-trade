# filters/basic_filters.py - GÜVENLİ VERSİYON
import pandas as pd
import numpy as np

def has_higher_lows(df: pd.DataFrame, min_count: int = 2) -> bool:
    """Son 20 barda en az min_count adet yükselen dip kontrolü"""
    if df is None or len(df) < 20:
        return False
    
    lows = df['low'].tail(20).values
    higher_low_count = 0
    
    for i in range(1, len(lows)):
        if lows[i] > lows[i-1]:
            higher_low_count += 1
    
    return higher_low_count >= min_count

def basic_filters(latest: dict, config: dict, df: pd.DataFrame = None) -> bool:
    """
    Temel filtreleri uygular - GÜVENLİ VERSİYON
    """
    symbol = latest.get('symbol', 'UNKNOWN')
    debug_mode = config.get('debug_mode', False)
    
    if debug_mode:
        print(f"\n🔍 {symbol} - FİLTRE ANALİZİ:")
    
    # 1. RSI kontrolü
    rsi = latest.get('RSI', 50)
    min_rsi = config.get('min_rsi', 30)
    max_rsi = config.get('max_rsi', 70)
    if not (min_rsi <= rsi <= max_rsi):
        if debug_mode:
            print(f"   ❌ RSI: {rsi:.1f} → [{min_rsi}-{max_rsi}] aralığında DEĞİL")
        return False
    if debug_mode:
        print(f"   ✅ RSI: {rsi:.1f}")
    
    # 2. Relative volume - GÜVENLİ
    rel_vol = latest.get('Relative_Volume', 1.0)
    min_rel_vol = config.get('min_relative_volume', 0.6)
    if rel_vol < min_rel_vol:
        if debug_mode:
            print(f"   ❌ RelVol: {rel_vol:.3f} → Min {min_rel_vol}'ten DÜŞÜK")
        return False
    if debug_mode:
        print(f"   ✅ RelVol: {rel_vol:.3f}")
    
    # 3. EMA20 kontrolü - OPSİYONEL
    if config.get('price_above_ema20', False):
        price = latest.get('close', 0)
        ema20 = latest.get('EMA20', 0)
        if price <= ema20:
            if debug_mode:
                print(f"   ❌ EMA20: {price:.2f} ≤ {ema20:.2f}")
            return False
        if debug_mode:
            print(f"   ✅ EMA20: {price:.2f} > {ema20:.2f}")
    
    # 4. EMA50 kontrolü - OPSİYONEL
    if config.get('price_above_ema50', False):
        price = latest.get('close', 0)
        ema50 = latest.get('EMA50', 0)
        if price <= ema50:
            if debug_mode:
                print(f"   ❌ EMA50: {price:.2f} ≤ {ema50:.2f}")
            return False
        if debug_mode:
            print(f"   ✅ EMA50: {price:.2f} > {ema50:.2f}")
    
    # 5. MACD kontrolü
    if config.get('macd_positive', False):
        macd_level = latest.get('MACD_Level', 0)
        macd_signal = latest.get('MACD_Signal', 0)
        if macd_level <= macd_signal:
            if debug_mode:
                print(f"   ❌ MACD: {macd_level:.4f} ≤ {macd_signal:.4f}")
            return False
        if debug_mode:
            print(f"   ✅ MACD: {macd_level:.4f} > {macd_signal:.4f}")
    
    # 6. ADX kontrolü
    if config.get('check_adx', False):
        adx = latest.get('ADX', 0)
        min_adx = 20
        if adx < min_adx:
            if debug_mode:
                print(f"   ❌ ADX: {adx:.1f} → Min {min_adx}'ten DÜŞÜK")
            return False
        if debug_mode:
            print(f"   ✅ ADX: {adx:.1f}")
    
    # 7. CMF kontrolü (kurumsal akış)
    if config.get('check_institutional_flow', False):
        cmf = latest.get('CMF', 0)
        if cmf < 0:
            if debug_mode:
                print(f"   ❌ CMF: {cmf:.3f} → Negatif (kurumsal satış)")
            return False
        if debug_mode:
            print(f"   ✅ CMF: {cmf:.3f}")
    
    # 8. Momentum divergens kontrolü
    if config.get('check_momentum_divergence', False):
        rsi_val = latest.get('RSI', 50)
        daily_pct = latest.get('Daily_Change_Pct', 0)
        
        if rsi_val > 70 and daily_pct < 0:
            if debug_mode:
                print(f"   ❌ Momentum: AŞIRI alımda düşüş (RSI={rsi_val:.1f}, Change={daily_pct:.1f}%)")
            return False
        
        if rsi_val < 30 and daily_pct > 0:
            if debug_mode:
                print(f"   ❌ Momentum: AŞIRI satımda yükseliş (RSI={rsi_val:.1f}, Change={daily_pct:.1f}%)")
            return False
        if debug_mode:
            print(f"   ✅ Momentum: Uyumlu")
    
    # ✅ 9. Yükselen dipler kontrolü - GÜVENLİ
    if config.get('min_higher_lows', 0) > 0:
        if df is not None and len(df) >= 20:
            min_higher_lows = config.get('min_higher_lows', 1)
            if not has_higher_lows(df, min_higher_lows):
                if debug_mode:
                    print(f"   ❌ Yükselen Dip: {min_higher_lows} adet bulunamadı")
                return False
            if debug_mode:
                print(f"   ✅ Yükselen Dip: {min_higher_lows}+ adet")
        else:
            if debug_mode:
                print(f"   ⚠️ Yükselen Dip: Veri yetersiz (df: {len(df) if df is not None else 0} bar)")
    
    # 10. Likidite kontrolü
    min_liquidity = config.get('min_liquidity_ratio', 0.3)
    volume_20d_avg = latest.get('Volume_20d_Avg', 0)
    current_volume = latest.get('volume', 0)
    
    if volume_20d_avg > 0:
        liquidity_ratio = current_volume / volume_20d_avg
        if liquidity_ratio < min_liquidity:
            if debug_mode:
                print(f"   ❌ Likidite: {liquidity_ratio:.2f} → Min {min_liquidity}'ten DÜŞÜK")
            return False
        if debug_mode:
            print(f"   ✅ Likidite: {liquidity_ratio:.2f}")
    
    if debug_mode:
        print(f"   🎉 {symbol}: TÜM FİLTRELERDEN GEÇTİ!")
    
    return True
