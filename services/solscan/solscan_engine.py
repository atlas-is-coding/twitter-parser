import os
import sys
from typing import Dict, List, Optional
import requests
from dacite import from_dict, Config
import time
from utils.proxy_manager import ProxyManager
import logging

from config import SOLSCAN_BASE_HEADER
from services.solscan.models import SolscanAPI
from config.constants import (
    SOLSCAN_PAGE_SIZE, SOLSCAN_MAX_PAGE, MAX_RETRIES,
    SOLSCAN_DELAY_BETWEEN_REQUESTS, REQUEST_TIMEOUT
)

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger('twitter_parser')

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
    def construct_search_url(contract_address: str, page_size: int = SOLSCAN_PAGE_SIZE, page: int = 1) -> str:
        return f"https://api-v2.solscan.io/v2/token/holders?address={contract_address}&page_size={page_size}&page={page}"

    def get_holders(self, contract_address: str, page_size: int = SOLSCAN_PAGE_SIZE) -> SolscanAPI:
        logger.info(f"Начало получения холдеров для контракта {contract_address}")
        all_holders_data = []
        current_page = 1
        retry_limit = MAX_RETRIES  # Создаем локальную переменную
        delay = SOLSCAN_DELAY_BETWEEN_REQUESTS
        
        metadata = None
        total_holders_processed = 0
        total_expected = None

        print(f"\r📊 Контракт {contract_address}: ", end='', flush=True)

        while current_page < SOLSCAN_MAX_PAGE:
            url = self.construct_search_url(contract_address, page_size, current_page)
            logger.debug(f"Запрос к Solscan API: {url}")
            
            for attempt in range(retry_limit):
                proxy_url = self.proxy_manager.get_proxy()
                if not proxy_url:
                    logger.error("Не удалось получить прокси для запроса")
                    return SolscanAPI(success=True, data=all_holders_data, metadata=metadata or {})

                try:
                    response = requests.get(
                        url, 
                        headers=self.headers, 
                        proxies={'http': proxy_url, 'https': proxy_url},
                        timeout=REQUEST_TIMEOUT
                    )
                    response.raise_for_status()
                    
                    if not response.text.strip():
                        logger.warning(f"Получен пустой ответ от Solscan API для контракта {contract_address}")
                        return SolscanAPI(success=True, data=all_holders_data, metadata=metadata or {})
                    
                    try:
                        response_data = response.json()
                        page_response = from_dict(
                            data_class=SolscanAPI,
                            data=response_data,
                            config=self.config
                        )
                        
                        if total_expected is None and 'total' in response_data.get('metadata', {}):
                            total_expected = response_data['metadata']['total']
                        
                    except (ValueError, requests.exceptions.JSONDecodeError) as json_error:
                        logger.error(f"Ошибка парсинга JSON: {str(json_error)}", exc_info=True)
                        if attempt == retry_limit - 1:
                            logger.error(f"Превышено максимальное количество попыток парсинга JSON для контракта {contract_address}")
                            return SolscanAPI(success=True, data=all_holders_data, metadata=metadata or {})
                        time.sleep(delay)
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
                    time.sleep(delay)
                    break
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Ошибка запроса к Solscan API: {str(e)}", exc_info=True)
                    self.proxy_manager.report_error(proxy_url)
                    if attempt == retry_limit - 1:
                        logger.error(f"Превышено максимальное количество попыток запроса для контракта {contract_address}")
                        return SolscanAPI(success=True, data=all_holders_data, metadata=metadata or {})
                    time.sleep(delay)
                    continue
                except Exception as e:
                    logger.error(f"Неожиданная ошибка при получении холдеров: {str(e)}", exc_info=True)
                    return SolscanAPI(success=True, data=all_holders_data, metadata=metadata or {})

        logger.info(f"Завершено получение холдеров для контракта {contract_address}. Всего получено: {total_holders_processed}")
        return SolscanAPI(success=True, data=all_holders_data, metadata=metadata or {})