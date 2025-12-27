# swing_analyzer_fixed_plus.py
"""
Ana orchestrator - Tüm modülleri birleştirir
"""
import sys
import os

# Proje root dizinini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Core imports
from scanner.swing_hunter import SwingHunterUltimate
from backtest.backtester import RealisticBacktester

def test_enhanced_scanner():
    """Test fonksiyonu"""
    print("🚀 Swing Hunter Ultimate Test Başlıyor...")
    
    hunter = SwingHunterUltimate()
    
    # Piyasa analizi
    print("\n📈 Piyasa analizi yapılıyor...")
    market = hunter.analyze_market_condition()
    print(f"✅ Piyasa: {market.regime}, Skor: {market.market_score}")
    
    # Tarama
    print("\n🔍 Hisse taraması başlıyor...")
    test_symbols = ['GARAN', 'AKBNK', 'THYAO']
    results = hunter.run_advanced_scan(test_symbols)
    
    print(f"\n✅ Bulunan: {len(results['Swing Uygun'])} hisse")
    
    if results['Swing Uygun']:
        print("\n📊 İlk Sonuç:")
        first = results['Swing Uygun'][0]
        for key, value in first.items():
            print(f"  {key}: {value}")
    
    return results

if __name__ == '__main__':
    try:
        test_enhanced_scanner()
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()
