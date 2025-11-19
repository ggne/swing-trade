"""
Paralel Hisse Tarayıcı - Hız Optimizasyonu
"""

import concurrent.futures
import threading
import time
from typing import List, Dict, Callable, Optional
import logging

class ParallelScanner:
    def __init__(self, hunter, max_workers=4):
        self.hunter = hunter
        self.max_workers = max_workers
        self.results_lock = threading.Lock()
        self.progress_lock = threading.Lock()
        self.scan_results = []
        self.processed_count = 0
        self.total_count = 0
        
    def process_symbol_safe(self, symbol: str) -> Optional[Dict]:
        try:
            result = self.hunter.process_symbol_advanced(symbol)
            
            with self.progress_lock:
                self.processed_count += 1
                progress_pct = int((self.processed_count / self.total_count) * 100)
                
                if hasattr(self, 'progress_callback') and self.progress_callback:
                    self.progress_callback(
                        progress_pct, 
                        f"{self.processed_count}/{self.total_count} - {symbol} tarandı"
                    )
            
            return result
            
        except Exception as e:
            logging.error(f"Paralel tarama hatası - {symbol}: {e}")
            return None
    
    def scan_parallel(self, symbols: List[str], progress_callback=None) -> Dict:
        self.scan_results = []
        self.processed_count = 0
        self.total_count = len(symbols)
        self.progress_callback = progress_callback
        
        start_time = time.time()
        
        logging.info(f"🚀 Paralel tarama başlıyor: {len(symbols)} sembol, {self.max_workers} thread")
        
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
                    logging.warning(f"⏱️ Timeout: {symbol}")
                except Exception as e:
                    logging.error(f"❌ Hata - {symbol}: {e}")
        
        elapsed_time = time.time() - start_time
        
        if self.scan_results:
            self.scan_results.sort(
                key=lambda x: x.get('score', 0), 
                reverse=True
            )
        
        logging.info(f"✅ Paralel tarama tamamlandı: {len(self.scan_results)} sonuç, {elapsed_time:.1f} saniye")
        
        return {"Swing Uygun": self.scan_results}

class FastSwingHunter:
    def __init__(self, hunter):
        self.hunter = hunter
        self.parallel_scanner = ParallelScanner(hunter, max_workers=5)
        
    def run_scan_fast(self, symbols: List[str], progress_callback=None, use_batches=False) -> Dict:
        symbol_count = len(symbols)
        
        if use_batches or symbol_count > 50:
            # Basit batch implementasyonu
            batches = [symbols[i:i + 15] for i in range(0, len(symbols), 15)]
            all_results = []
            
            for batch in batches:
                batch_results = self.parallel_scanner.scan_parallel(batch, progress_callback)
                if batch_results.get("Swing Uygun"):
                    all_results.extend(batch_results["Swing Uygun"])
                time.sleep(3)  # Batch'ler arası dinlenme
            
            return {"Swing Uygun": all_results}
        else:
            return self.parallel_scanner.scan_parallel(symbols, progress_callback)