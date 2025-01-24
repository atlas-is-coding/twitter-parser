import os
import sys
from typing import Dict, List, Optional
import requests
from dacite import from_dict, Config
import time
from utils.proxy_manager import ProxyManager

from config import SOLSCAN_BASE_HEADER
from services.solscan.models import SolscanAPI

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class SolscanEngine:
    def __init__(self, proxy_manager: Optional[ProxyManager] = None):
        self.headers = SOLSCAN_BASE_HEADER
        self.proxy_manager = proxy_manager or ProxyManager()
        self.config = Config(
            check_types=False,
            cast=[int, float],
            type_hooks={
                Dict: lambda x: x if x is not None else {},
                List: lambda x: x if x is not None else [],
            }
        )

    @staticmethod
    def construct_search_url(contract_address: str, page_size: int = 10, page: int = 1) -> str:
        return f"https://api-v2.solscan.io/v2/token/holders?address={contract_address}&page_size={page_size}&page={page}"

    def get_holders(self, contract_address: str, page_size: int = 10) -> SolscanAPI:
        all_holders_data = []
        current_page = 1
        MAX_PAGE = 101
        MAX_RETRIES = 3
        DELAY_BETWEEN_REQUESTS = 1
        
        metadata = None
        total_holders_processed = 0
        total_expected = None  # Изначально None, пока не получим реальное значение

        print(f"\r📊 Контракт {contract_address}: ", end='', flush=True)

        while current_page < MAX_PAGE:
            url = self.construct_search_url(contract_address, page_size, current_page)
            
            for attempt in range(MAX_RETRIES):
                proxy_url = self.proxy_manager.get_proxy()
                if not proxy_url:
                    print("\n❌ Нет доступных прокси")
                    return SolscanAPI(success=True, data=all_holders_data, metadata=metadata or {})

                try:
                    response = requests.get(url, headers=self.headers, proxies={'http': proxy_url, 'https': proxy_url})
                    response.raise_for_status()
                    
                    if not response.text.strip():
                        print(f"\r💼 Контракт {contract_address}: Обработано {total_holders_processed} холдеров")
                        return SolscanAPI(success=True, data=all_holders_data, metadata=metadata or {})
                    
                    try:
                        response_data = response.json()
                        page_response = from_dict(
                            data_class=SolscanAPI,
                            data=response_data,
                            config=self.config
                        )
                        
                        # Получаем общее количество холдеров из первого ответа
                        if total_expected is None and 'total' in response_data.get('metadata', {}):
                            total_expected = response_data['metadata']['total']
                        
                    except (ValueError, requests.exceptions.JSONDecodeError) as json_error:
                        if attempt == MAX_RETRIES - 1:
                            print(f"\n❌ Ошибка обработки данных после {MAX_RETRIES} попыток")
                            return SolscanAPI(success=True, data=all_holders_data, metadata=metadata or {})
                        continue
                    
                    if not page_response.data:
                        print(f"\r💼 Контракт {contract_address}: Обработано {total_holders_processed} холдеров")
                        return SolscanAPI(success=True, data=all_holders_data, metadata=metadata or {})
                    
                    all_holders_data.extend(page_response.data)
                    total_holders_processed += len(page_response.data)
                    
                    # Вычисляем и отображаем процент выполнения
                    if total_expected:
                        progress = (total_holders_processed / total_expected * 100)
                        print(f"\r📊 Контракт {contract_address}: {progress:.1f}% ({total_holders_processed}/{total_expected})", end='', flush=True)
                    else:
                        print(f"\r📊 Контракт {contract_address}: Обработано {total_holders_processed} холдеров", end='', flush=True)
                    
                    current_page += 1
                    time.sleep(DELAY_BETWEEN_REQUESTS)
                    break
                    
                except requests.exceptions.RequestException as e:
                    self.proxy_manager.report_error(proxy_url)
                    if attempt == MAX_RETRIES - 1:
                        print(f"\n❌ Ошибка запроса после {MAX_RETRIES} попыток: {str(e)}")
                        return SolscanAPI(success=True, data=all_holders_data, metadata=metadata or {})
                    continue

        print(f"\r💼 Контракт {contract_address}: Обработано {total_holders_processed} холдеров")
        return SolscanAPI(success=True, data=all_holders_data, metadata=metadata or {})