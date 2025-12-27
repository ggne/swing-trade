# risk/position_sizer.py
import numpy as np

def calculate_position_size(entry_price: float, stop_loss: float, account_balance: float, risk_pct: float = 1.0) -> int:
    """
    Risk yüzdesine göre pozisyon boyutunu hesaplar.
    """
    if stop_loss <= 0 or entry_price <= 0:
        return 0
    risk_amount = account_balance * (risk_pct / 100)
    risk_per_share = abs(entry_price - stop_loss)
    if risk_per_share <= 0:
        return 0
    position_size = risk_amount / risk_per_share
    return max(1, int(position_size))

def validate_risk_parameters(config: dict, account_balance: float) -> dict:
    """
    Risk parametrelerini doğrular ve varsayılanları uygular.
    """
    validated = {
        'risk_pct': config.get('max_risk_pct', 1.0),
        'min_rr_ratio': config.get('min_risk_reward_ratio', 2.0),
        'max_position_size_pct': config.get('max_position_size_pct', 10.0),
        'account_balance': account_balance
    }
    validated['risk_pct'] = max(0.1, min(5.0, validated['risk_pct']))
    validated['min_rr_ratio'] = max(1.0, validated['min_rr_ratio'])
    validated['max_position_size_pct'] = min(100.0, max(1.0, validated['max_position_size_pct']))
    return validated