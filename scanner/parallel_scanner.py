# parallel_scanner.py
import concurrent.futures
import threading
import time
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ParallelScanner:
    """Paralel hisse tarayıcı - GÜNCELLENMİŞ"""
    def __init__(self, hunter, max_workers=4):
        self.hunter = hunter
        self.max_workers = max_workers
        self.results_lock = threading.Lock()
        self.progress_lock = threading.Lock()
        self.scan_results = []
        self.processed_count = 0
        self.total_count = 0
        self.progress_callback = None

    def process_symbol_safe(self, symbol: str) -> Optional[Dict]:
        """Güvenli sembol işleme - GÜNCELLENMİŞ: process_symbol_advanced çağrılıyor"""
        try:
            result = self.hunter.process_symbol_advanced(symbol)  # ✅ DOĞRU METOD
            with self.progress_lock:
                self.processed_count += 1
                progress_pct = int((self.processed_count / self.total_count) * 100)
                if self.progress_callback:
                    self.progress_callback(progress_pct, f"{self.processed_count}/{self.total_count} - {symbol} tarandı")
            return result
        except Exception as e:
            logger.error(f"Paralel tarama hatası - {symbol}: {e}")
            return None

    def scan_parallel(self, symbols: List[str], progress_callback=None) -> Dict:
        """Paralel tarama"""
        self.scan_results = []
        self.processed_count = 0
        self.total_count = len(symbols)
        self.progress_callback = progress_callback

        start_time = time.time()
        logger.info(f"🚀 Paralel tarama başlıyor: {len(symbols)} sembol, {self.max_workers} thread")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_symbol = {
                executor.submit(self.process_symbol_safe, symbol): symbol 
                for symbol in symbols
            }
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result(timeout=30)
                    if result:
                        with self.results_lock:
                            self.scan_results.append(result)
                except concurrent.futures.TimeoutError:
                    logger.warning(f"⏱️ Timeout: {symbol}")
                except Exception as e:
                    logger.error(f"❌ Hata - {symbol}: {e}")

        elapsed_time = time.time() - start_time
        if self.scan_results:
            self.scan_results.sort(
                key=lambda x: int(x.get('Skor', '0/100').split('/')[0]),
                reverse=True
            )
        logger.info(f"✅ Paralel tarama tamamlandı: {len(self.scan_results)} sonuç, {elapsed_time:.1f} saniye")
        return {"Swing Uygun": self.scan_results}