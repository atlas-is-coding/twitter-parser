from dataclasses import dataclass
from typing import Dict, Optional, List
import time
import random

@dataclass
class HeaderStats:
    headers: Dict
    requests_count: int = 0
    last_used: float = 0
    is_active: bool = True
    errors_count: int = 0

class HeadersManager:
    def __init__(self, headers_list: List[Dict], max_requests: int = 50):
        self.headers_list = [HeaderStats(headers=headers) for headers in headers_list]
        self.max_requests = max_requests
        self.current_index = 0
    
    def _get_next_headers(self) -> Optional[HeaderStats]:
        """Получение следующего доступного набора заголовков"""
        start_index = self.current_index
        while True:
            header_stats = self.headers_list[self.current_index]
            
            # Проверяем количество запросов
            if header_stats.requests_count >= self.max_requests:
                header_stats.requests_count = 0
                header_stats.is_active = True  # Сбрасываем статус
            
            if header_stats.is_active:
                return header_stats
                
            self.current_index = (self.current_index + 1) % len(self.headers_list)
            if self.current_index == start_index:
                return None
    
    def get_headers(self) -> Optional[Dict]:
        """Получение рабочих заголовков"""
        header_stats = self._get_next_headers()
        if header_stats:
            header_stats.requests_count += 1
            header_stats.last_used = time.time()
            self.current_index = (self.current_index + 1) % len(self.headers_list)
            return header_stats.headers
        return None
    
    def report_error(self, headers: Dict) -> None:
        """Отметить ошибку использования заголовков"""
        for header_stats in self.headers_list:
            if header_stats.headers == headers:
                header_stats.errors_count += 1
                if header_stats.errors_count >= 7:
                    header_stats.is_active = False
                break
