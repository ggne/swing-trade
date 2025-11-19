"""
Geliştirilmiş Swing Hunter - Konsol Arayüzü
"""

import logging
import sys
import os

# Yolları ayarla
sys.path.append(os.path.join(os.path.dirname(__file__), 'CORE_ANALYZERS'))

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('swing_hunter_enhanced.log', mode='w', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        from swing_analyzer_ultimate import SwingHunterUltimate
        from parallel_scanner import FastSwingHunter
        
        logger.info("🚀 Geliştirilmiş Swing Hunter Başlatılıyor...")
        
        hunter = SwingHunterUltimate('swing_config.json')
        fast_hunter = FastSwingHunter(hunter)
        
        print("\n" + "="*50)
        print("🎯 GELİŞTİRİLMİŞ SWING HUNTER ULTIMATE")
        print("="*50)
        
        while True:
            print("\n🔍 Yapılacak İşlemi Seçin:")
            print("1. Hızlı Tarama (Paralel)")
            print("2. Ultimate Tarama (Tüm Özellikler)")
            print("3. Sistem Durumu")
            print("4. Çıkış")
            
            choice = input("\nSeçiminiz (1-4): ").strip()
            
            if choice == '1':
                symbols = hunter.cfg.get('symbols', ['GARAN', 'AKBNK'])
                print(f"\n🚀 Hızlı tarama başlıyor: {len(symbols)} sembol")
                
                results = fast_hunter.run_scan_fast(symbols)
                
                if results["Swing Uygun"]:
                    print(f"\n✅ {len(results['Swing Uygun'])} hisse bulundu!")
                    for stock in results["Swing Uygun"]:
                        print(f"   📈 {stock['Hisse']} - {stock['Sinyal']} (Skor: {stock['Skor']})")
                else:
                    print("\n❌ Uygun hisse bulunamadı")
                    
            elif choice == '2':
                symbols = hunter.cfg.get('symbols', ['GARAN', 'AKBNK'])
                print(f"\n🚀 Ultimate tarama başlıyor: {len(symbols)} sembol")
                
                results = hunter.run_advanced_scan(symbols)
                
                if results["Swing Uygun"]:
                    print(f"\n✅ {len(results['Swing Uygun'])} hisse bulundu!")
                    for stock in results["Swing Uygun"][:5]:  # İlk 5 hisse
                        print(f"   🎯 {stock['Hisse']} - {stock['Sinyal']}")
                        print(f"      Skor: {stock['Skor']}, R/R: {stock['R/R']}")
                        print(f"      MTF: {stock['MTF Öneri']}")
                        print()
                else:
                    print("\n❌ Uygun hisse bulunamadı")
                    
            elif choice == '3':
                print(f"\n🖥️ SİSTEM DURUMU")
                print(f"✅ Config yüklendi: {len(hunter.cfg.get('symbols', []))} sembol")
                print(f"📊 Özellikler: Multi-Timeframe, Fibonacci, Konsolidasyon")
                print(f"🚀 Hazır!")
                
            elif choice == '4':
                print("\n👋 Çıkış yapılıyor...")
                break
                
            else:
                print("\n❌ Geçersiz seçim!")
                
    except Exception as e:
        logger.error(f"Ana program hatası: {e}")
        print(f"❌ Kritik hata: {e}")

if __name__ == "__main__":
    main()