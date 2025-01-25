from solana.rpc.api import Client
from solders.pubkey import Pubkey
from typing import Dict, Tuple, List, Optional
import requests
import time
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wallet_scanner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Константы
SOLANA_RPC_URL = "https://mainnet.helius-rpc.com/?api-key=12891d9f-e674-4ae8-b25e-23eab3a00621"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
CACHE_FILE = Path('solana_tokens.json')
CACHE_DURATION = 300  # 5 минут в секундах
REQUEST_TIMEOUT = 10  # таймаут для HTTP запросов
MAX_RETRIES = 3

# Базовые токены
TOKENS_INFO = {
    'SOL': {'coingecko_id': 'solana'},
    'USDC': {
        'coingecko_id': 'usd-coin',
        'mint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
    },
    'USDT': {
        'coingecko_id': 'tether',
        'mint': 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'
    },
    'RAY': {
        'coingecko_id': 'raydium',
        'mint': '4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R'
    }
}

class SolanaClient:
    def __init__(self, rpc_url: str = SOLANA_RPC_URL):
        self.client = Client(rpc_url)
        self._token_list: Optional[Dict[str, str]] = None
        self._last_token_update = 0

    @property
    def token_list(self) -> Dict[str, str]:
        """Получение списка токенов с кешированием"""
        current_time = time.time()
        if not self._token_list or (current_time - self._last_token_update) > CACHE_DURATION:
            self._token_list = self._load_or_fetch_tokens()
            self._last_token_update = current_time
        return self._token_list

    def _load_or_fetch_tokens(self) -> Dict[str, str]:
        """Загрузка токенов из кеша или Jupiter API"""
        try:
            if CACHE_FILE.exists() and (time.time() - CACHE_FILE.stat().st_mtime) < CACHE_DURATION:
                with CACHE_FILE.open('r') as f:
                    return json.load(f)
            
            tokens = self._fetch_jupiter_tokens()
            with CACHE_FILE.open('w') as f:
                json.dump(tokens, f, indent=2)
            return tokens
        except Exception as e:
            logger.error(f"Ошибка при загрузке токенов: {e}")
            return {}

    def _fetch_jupiter_tokens(self) -> Dict[str, str]:
        """Получение списка токенов из Jupiter API"""
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get("https://token.jup.ag/all", timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                tokens = response.json()
                return {token['symbol']: token['address'] for token in tokens}
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"Не удалось получить список токенов: {e}")
                    return {}
                time.sleep(1)
        return {}

    def get_token_prices(self, token_symbols: List[str] = None) -> Dict[str, float]:
        prices = {}
        try:
            # Сначала получаем цены для основных токенов через CoinGecko
            token_ids = [info['coingecko_id'] for info in TOKENS_INFO.values()]
            
            response = requests.get(
                f"https://api.coingecko.com/api/v3/simple/price",
                params={'ids': ','.join(token_ids), 'vs_currencies': 'usd'},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            for token, info in TOKENS_INFO.items():
                if info['coingecko_id'] in data:
                    prices[token] = data[info['coingecko_id']]['usd']

            # Получаем цены через Jupiter API v2
            try:
                # Получаем mint адреса для всех токенов
                token_mints = []
                for symbol in (token_symbols or []):
                    if symbol in self.token_list:
                        token_mints.append(self.token_list[symbol])
                
                if token_mints:
                    jupiter_response = requests.get(
                        "https://api.jup.ag/price/v2",
                        params={
                            "ids": ",".join(token_mints),
                            "vsToken": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC mint
                            "showExtraInfo": "true"
                        },
                        timeout=REQUEST_TIMEOUT
                    )
                    jupiter_response.raise_for_status()
                    jupiter_data = jupiter_response.json()
                    
                    # Создаем обратный маппинг mint -> symbol
                    mint_to_symbol = {v: k for k, v in self.token_list.items()}
                    
                    # Обрабатываем данные из Jupiter API v2
                    if 'data' in jupiter_data:
                        for mint, price_data in jupiter_data['data'].items():
                            if price_data and mint in mint_to_symbol:
                                if isinstance(price_data, dict) and 'price' in price_data:
                                    symbol = mint_to_symbol[mint]
                                    if symbol not in prices:  # не перезаписываем цены из CoinGecko
                                        prices[symbol] = float(price_data['price'])

            except Exception as e:
                logger.error(f"Ошибка при получении цен через Jupiter v2: {e}")

            # Получаем цены через Raydium API для оставшихся токенов
            try:
                missing_tokens = [t for t in (token_symbols or []) if t not in prices]
                if missing_tokens:
                    raydium_response = requests.get(
                        "https://api.raydium.io/v2/main/price",
                        timeout=REQUEST_TIMEOUT
                    )
                    raydium_response.raise_for_status()
                    raydium_data = raydium_response.json()
                    
                    for symbol in missing_tokens:
                        if symbol in self.token_list:
                            mint = self.token_list[symbol]
                            if mint in raydium_data:
                                price_info = raydium_data[mint]
                                if isinstance(price_info, dict) and 'price' in price_info:
                                    prices[symbol] = float(price_info['price'])

            except Exception as e:
                logger.error(f"Ошибка при получении цен через Raydium: {e}")

            # Добавляем стейблкоины
            for token in ['USDC', 'USDT']:
                if token not in prices:
                    prices[token] = 1.0

        except Exception as e:
            logger.error(f"Ошибка при получении цен: {e}")
        
        return prices

    def get_wallet_balance(self, wallet_address: str) -> Tuple[Dict[str, float], Dict[str, float]]:
        try:
            balances = self._get_wallet_tokens(wallet_address)
            print(f"DEBUG: Полученные балансы: {balances}")  # Для отладки
            
            # Получаем цены для всех найденных токенов
            prices = self.get_token_prices(list(balances.keys()))
            print(f"DEBUG: Полученные цены: {prices}")  # Для отладки
            
            usd_values = {}
            for token, balance in balances.items():
                if token in prices and balance > 0:  # Проверяем что баланс положительный
                    price = prices[token]
                    usd_value = balance * price
                    usd_values[token] = usd_value
                    print(f"DEBUG: Подсчет для {token}: {balance} * ${price} = ${usd_value}")  # Для отладки
            
            return balances, usd_values
        except Exception as e:
            logger.error(f"Ошибка при получении баланса кошелька {wallet_address}: {e}")
            return {}, {}

    def _get_wallet_tokens(self, wallet_address: str) -> Dict[str, float]:
        balances = {}
        try:
            # Получаем SOL баланс
            sol_response = self.client.get_balance(Pubkey.from_string(wallet_address))
            if hasattr(sol_response, 'value'):
                balances['SOL'] = float(sol_response.value) / 1e9

            # Получаем список токенов из Jupiter
            jupiter_tokens = self.token_list

            # Запрос к Helius RPC для получения токенов
            url = "https://mainnet.helius-rpc.com/?api-key=12891d9f-e674-4ae8-b25e-23eab3a00621"
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    wallet_address,
                    {
                        "programId": TOKEN_PROGRAM_ID
                    },
                    {
                        "encoding": "jsonParsed"
                    }
                ]
            }
            headers = {'Content-Type': 'application/json'}

            response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response_data = response.json()

            if 'result' in response_data and 'value' in response_data['result']:
                accounts = response_data['result']['value']
                
                for account in accounts:
                    try:
                        parsed_info = account['account']['data']['parsed']['info']
                        mint = parsed_info.get('mint')
                        token_amount = parsed_info.get('tokenAmount', {})
                        
                        if not mint or 'amount' not in token_amount or 'decimals' not in token_amount:
                            continue
                            
                        amount = float(token_amount['amount'])
                        decimals = int(token_amount['decimals'])
                        balance = amount / (10 ** decimals)

                        # Пропускаем нулевые балансы
                        if balance == 0:
                            continue

                        # Сначала проверяем в TOKENS_INFO
                        token_found = False
                        for token, token_info in TOKENS_INFO.items():
                            if 'mint' in token_info and token_info['mint'] == mint:
                                balances[token] = balance
                                token_found = True
                                break
                        
                        # Если токен не найден в TOKENS_INFO, ищем в Jupiter
                        if not token_found:
                            for symbol, address in jupiter_tokens.items():
                                if address == mint:
                                    balances[symbol] = balance
                                    break

                    except Exception as e:
                        logger.debug(f"Ошибка при обработке токена {mint}: {str(e)}")
                        continue

        except Exception as e:
            logger.error(f"Ошибка при получении токенов кошелька {wallet_address}: {str(e)}")

        return balances

    def get_wallets_balances(self, wallet_addresses: List[str], batch_size: int = 50) -> Dict[str, Tuple[Dict[str, float], Dict[str, float]]]:
        """Пакетная обработка кошельков"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            for i in range(0, len(wallet_addresses), batch_size):
                batch = wallet_addresses[i:i + batch_size]
                futures = [executor.submit(self.get_wallet_balance, address) for address in batch]
                
                for address, future in zip(batch, futures):
                    try:
                        balances, usd_values = future.result()
                        results[address] = (balances, usd_values)
                    except Exception as e:
                        logger.error(f"Ошибка при обработке кошелька {address}: {e}")
                        results[address] = ({}, {})
                
                time.sleep(0.5)  # Защита от rate limit
        
        return results

def main():
    client = SolanaClient()
    test_wallets = ["5cvQpjBpobuLEKf2myqpwrkcX4u1ct1XuEqmgcubAV7f"]
    
    results = client.get_wallets_balances(test_wallets)
    
    for wallet_address, (balances, usd_values) in results.items():
        print(f"\nКошелек: {wallet_address}")
        
        if not balances and not usd_values:
            print("Нет данных или произошла ошибка")
            continue
            
        print("\nБалансы и цены:")
        for token, amount in balances.items():
            usd_value = usd_values.get(token, 0)
            price = usd_value / amount if amount else 0
            print(f"{token}: {amount:.4f} * ${price:.6f} = ${usd_value:.2f}")
        
        total_usd = sum(usd_values.values())
        print(f"\nОбщая стоимость: ${total_usd:.2f}")

if __name__ == "__main__":
    main()
