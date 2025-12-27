# risk/trade_validator.py - DÜZELTİLMİŞ VERSİYON
from typing import Optional, Dict
from datetime import datetime
from core.types import Trade

def validate_trade_parameters(entry_price: float, stop_loss: float, target1: float, target2: float, config: dict) -> Dict:
    """
    Trade parametrelerini doğrular ve risk/reward oranını kontrol eder.
    """
    min_rr = config.get('min_risk_reward_ratio', 1.5)  # 2.0'dan 1.5'e düşürüldü
    
    # Risk uzaklığı
    risk_distance = abs(entry_price - stop_loss)
    if risk_distance <= 0:
        return {'valid': False, 'reason': 'stop_loss >= entry_price'}

    # Reward uzaklıkları
    reward1 = target1 - entry_price
    reward2 = target2 - entry_price
    if reward1 <= 0:
        return {'valid': False, 'reason': 'target1 <= entry_price'}
    if reward2 < reward1:
        return {'valid': False, 'reason': 'target2 < target1'}

    # Risk/reward oranı
    rr_ratio = reward1 / risk_distance
    if rr_ratio < min_rr:
        return {'valid': False, 'reason': f'rr_ratio ({rr_ratio:.2f}) < {min_rr}'}

    return {
        'valid': True,
        'risk_distance': risk_distance,
        'reward1': reward1,
        'reward2': reward2,
        'rr_ratio': rr_ratio
    }

def calculate_trade_plan(entry_price: float, stop_loss: float, target1: float, target2: float, 
                        config: dict, account_balance: float = 10000) -> Optional[Trade]:
    """
    Tam trade planı oluşturur (pozisyon boyutu dahil).
    """
    validation = validate_trade_parameters(entry_price, stop_loss, target1, target2, config)
    if not validation['valid']:
        print(f"Trade validasyon hatası: {validation['reason']}")
        return None

    from risk.position_sizer import calculate_position_size
    risk_pct = config.get('max_risk_pct', 2.0)  # 1.0'dan 2.0'ya yükseltildi
    
    try:
        shares = calculate_position_size(entry_price, stop_loss, account_balance, risk_pct)
    except Exception as e:
        print(f"Pozisyon boyutu hesaplama hatası: {e}")
        shares = 0
    
    if shares == 0:
        print("Pozisyon boyutu 0, trade planı oluşturulamıyor")
        return None

    # Lot uyumluluğu (BIST en az 1 lot = 1 adet)
    shares = max(1, int(shares))
    
    # Risk amount hesapla
    risk_amount = abs(entry_price - stop_loss) * shares
    capital_usage_pct = (entry_price * shares) / account_balance * 100 if account_balance > 0 else 0

    trade = Trade(
        entry_price=entry_price,
        stop_loss=stop_loss,
        target1=target1,
        target2=target2,
        shares=shares,
        risk_amount=risk_amount,
        capital_usage_pct=capital_usage_pct,
        entry_date=datetime.now().date(),
        status="open",
        exit_reason=""
    )
    return trade