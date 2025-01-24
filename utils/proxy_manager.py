import requests
from typing import Optional, List
import time
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ProxyStats:
    url: str
    requests_count: int = 0
    last_used: float = 0
    is_active: bool = True
    errors_count: int = 0

class ProxyManager:
    def __init__(self, proxies_file: str = "config/proxies.txt", max_requests: int = 100):
        self.proxies_file = Path(proxies_file)
        self.max_requests = max_requests
        self.proxies: List[ProxyStats] = []
        self.current_index = 0
        self._load_proxies()
    
    def _load_proxies(self) -> None:
        """Загрузка прокси из файла"""
        if not self.proxies_file.exists():
            raise FileNotFoundError(f"Файл с прокси не найден: {self.proxies_file}")
            
        with open(self.proxies_file, 'r') as f:
            proxy_urls = [line.strip() for line in f if line.strip()]
            self.proxies = [ProxyStats(url=url) for url in proxy_urls]
    
    def _check_proxy(self, proxy_url: str) -> bool:
        """Проверка работоспособности прокси"""
        try:
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            response = requests.get('https://api.twitter.com', proxies=proxies, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def _get_next_proxy(self) -> Optional[ProxyStats]:
        """Получение следующего доступного прокси"""
        start_index = self.current_index
        while True:
            proxy = self.proxies[self.current_index]
            
            # Проверяем нагрузку на прокси
            if proxy.requests_count >= self.max_requests:
                proxy.requests_count = 0
                proxy.is_active = self._check_proxy(proxy.url)
            
            if proxy.is_active:
                return proxy
                
            self.current_index = (self.current_index + 1) % len(self.proxies)
            if self.current_index == start_index:
                return None
    
    def get_proxy(self) -> Optional[str]:
        """Получение рабочего прокси с учётом нагрузки"""
        proxy = self._get_next_proxy()
        if proxy:
            proxy.requests_count += 1
            proxy.last_used = time.time()
            self.current_index = (self.current_index + 1) % len(self.proxies)
            return proxy.url
        return None
    
    def report_error(self, proxy_url: str) -> None:
        """Отметить ошибку использования прокси"""
        for proxy in self.proxies:
            if proxy.url == proxy_url:
                proxy.errors_count += 1
                if proxy.errors_count >= 3:
                    proxy.is_active = False
                break 