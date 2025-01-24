from typing import List
from services.solscan.models import SolscanAPI
from services.solscan.solscan_engine import SolscanEngine
from services.twitter.twitter_engine import TwitterEngine
from utils import regexp_check_sol
from utils.proxy_manager import ProxyManager
from utils.csv_writer import CSVWriter
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import math
from utils.logger import logger
import logging
import logging.config
from config.config import LOGGING_CONFIG
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel

# Инициализация логирования
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('twitter_parser')

console = Console()

def load_contract_addresses(file_path: str) -> list:
    """Загружает адреса контрактов из файла."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл с адресами контрактов не найден: {file_path}")
        
    with open(file_path, 'r') as file:
        addresses = [line.strip() for line in file if line.strip()]
    return addresses

def split_into_chunks(lst: list, chunk_size: int) -> list:
    """Разбивает список на чанки указанного размера."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def process_contract_chunk(contract_addresses: list, proxy_manager: ProxyManager, 
                         eligible_holders: list, not_eligible_holders: list, lock: Lock):
    """Обрабатывает группу контрактов в отдельном потоке."""
    twitter_engine = TwitterEngine(proxy_manager=proxy_manager)
    solscan_engine = SolscanEngine(proxy_manager=proxy_manager)
    
    chunk_stats = {
        'total_contracts': len(contract_addresses),
        'processed_contracts': 0,
        'total_holders': 0,
        'processed_holders': 0,
        'eligible': 0,
        'not_eligible': 0
    }
    
    for contract_address in contract_addresses:
        try:
            all_holders = solscan_engine.get_holders(contract_address, 100)
            
            with lock:
                chunk_stats['processed_contracts'] += 1
                chunk_stats['total_holders'] += len(all_holders.data)
                
                # Вычисляем проценты
                contracts_progress = (chunk_stats['processed_contracts'] / chunk_stats['total_contracts']) * 100
                holders_progress = (chunk_stats['processed_holders'] / chunk_stats['total_holders'] * 100) if chunk_stats['total_holders'] > 0 else 0
                
                # Обновляем прогресс в одну строку
                print(f"\r📈 Контракты: {contracts_progress:.1f}% ({chunk_stats['processed_contracts']}/{chunk_stats['total_contracts']}) | "
                      f"Холдеры: {holders_progress:.1f}% ({chunk_stats['processed_holders']}/{chunk_stats['total_holders']}) | "
                      f"✅ {chunk_stats['eligible']} | ❌ {chunk_stats['not_eligible']}", end='', flush=True)

            for holder in all_holders.data:
                search_response = twitter_engine.get_latest_posts(query=holder.owner)
            
                with lock:
                    chunk_stats['processed_holders'] += 1
                    
                    if not search_response or not search_response.entries:
                        chunk_stats['not_eligible'] += 1
                        not_eligible_holders.append({
                            'address': holder.owner,
                            'reason': 'Твиты не найдены'
                        })
                    else:
                        found_eligible_tweet = False
                        for entry in search_response.entries:
                            if entry.tweet and regexp_check_sol(entry.tweet.text):
                                chunk_stats['eligible'] += 1
                                eligible_holders.append({
                                    'address': holder.owner,
                                    'twitter_username': entry.tweet.author.screen_name,
                                    'tweet_text': entry.tweet.text,
                                    'can_dm': entry.tweet.author.can_dm,
                                    'followers_count': entry.tweet.author.followers_count
                                })
                                print(f"\n✨ Найден: @{entry.tweet.author.screen_name} ({holder.owner[:8]}...)")
                                found_eligible_tweet = True
                                break
                        
                        if not found_eligible_tweet:
                            chunk_stats['not_eligible'] += 1
                            not_eligible_holders.append({
                                'address': holder.owner,
                                'reason': 'Нет твитов с упоминанием SOL'
                            })
                    
                    # Обновляем проценты
                    contracts_progress = (chunk_stats['processed_contracts'] / chunk_stats['total_contracts']) * 100
                    holders_progress = (chunk_stats['processed_holders'] / chunk_stats['total_holders'] * 100) if chunk_stats['total_holders'] > 0 else 0
                    
                    # Обновляем статистику после каждого обработанного холдера
                    print(f"\r📈 Контракты: {contracts_progress:.1f}% ({chunk_stats['processed_contracts']}/{chunk_stats['total_contracts']}) | "
                          f"Холдеры: {holders_progress:.1f}% ({chunk_stats['processed_holders']}/{chunk_stats['total_holders']}) | "
                          f"✅ {chunk_stats['eligible']} | ❌ {chunk_stats['not_eligible']}", end='', flush=True)

        except Exception as e:
            print(f"\n❌ Ошибка контракта {contract_address}: {str(e)}")

    return chunk_stats

def main():
    CHUNK_SIZE = 2
    
    proxy_manager = ProxyManager()
    csv_writer = CSVWriter()
    
    contract_addresses = load_contract_addresses('config/contractAddresses.txt')
    contract_chunks = split_into_chunks(contract_addresses, CHUNK_SIZE)
    
    eligible_holders = []
    not_eligible_holders = []
    lock = Lock()
    
    console.print(Panel.fit(
        "[bold green]🚀 Twitter Parser Started[/bold green]\n\n"
        f"[cyan]Контрактов:[/cyan] {len(contract_addresses)}\n"
        f"[cyan]Размер чанка:[/cyan] {CHUNK_SIZE}\n"
        f"[cyan]Всего чанков:[/cyan] {len(contract_chunks)}",
        title="🤖 Twitter Parser",
        border_style="green"
    ))
    
    logger.info("Starting Twitter parser process")
    
    try:
        with ThreadPoolExecutor(max_workers=len(contract_chunks)) as executor:
            futures = [
                executor.submit(
                    process_contract_chunk, 
                    chunk, 
                    proxy_manager,
                    eligible_holders,
                    not_eligible_holders,
                    lock
                ) for chunk in contract_chunks
            ]
            
            # Собираем общую статистику
            total_stats = {
                'total_contracts': len(contract_addresses),
                'processed_contracts': 0,
                'total_holders': 0,
                'processed_holders': 0,
                'eligible': len(eligible_holders),
                'not_eligible': len(not_eligible_holders)
            }
            
            for future in futures:
                chunk_stats = future.result()
                if chunk_stats:
                    total_stats['processed_contracts'] += chunk_stats['processed_contracts']
                    total_stats['total_holders'] += chunk_stats['total_holders']
                    total_stats['processed_holders'] += chunk_stats['processed_holders']

        print("\n") # Добавляем пустую строку после прогресса
        
        # Сохраняем файлы и получаем их пути
        eligible_file = csv_writer.write_eligible_holders(eligible_holders)
        not_eligible_file = csv_writer.write_not_eligible_holders(not_eligible_holders)
        
        # Получаем относительные пути для более красивого отображения
        eligible_path = os.path.relpath(eligible_file) if eligible_file else "Не создан"
        not_eligible_path = os.path.relpath(not_eligible_file) if not_eligible_file else "Не создан"

        # Вычисляем проценты выполнения
        contracts_progress = (total_stats['processed_contracts'] / total_stats['total_contracts'] * 100) if total_stats['total_contracts'] > 0 else 0
        holders_progress = (total_stats['processed_holders'] / total_stats['total_holders'] * 100) if total_stats['total_holders'] > 0 else 0

        console.print(Panel(
            "[bold green]✨ Обработка успешно завершена![/bold green]\n\n"
            f"[green]📊 Итоговая статистика:[/green]\n"
            f"✓ Контракты: {contracts_progress:.1f}% ({total_stats['processed_contracts']}/{total_stats['total_contracts']})\n"
            f"✓ Холдеры: {holders_progress:.1f}% ({total_stats['processed_holders']}/{total_stats['total_holders']})\n"
            f"✓ Подходящих: {len(eligible_holders)}\n"
            f"✓ Неподходящих: {len(not_eligible_holders)}\n\n"
            f"[blue]📂 Файлы сохранены:[/blue]\n"
            f"✓ Подходящие: {eligible_path}\n"
            f"✓ Неподходящие: {not_eligible_path}",
            title="📈 Результаты",
            border_style="green"
        ))
        
        logger.info(f"Processing completed. Eligible: {len(eligible_holders)}, Not eligible: {len(not_eligible_holders)}")
        
    except Exception as e:
        console.print(Panel(
            f"[bold red]❌ Произошла ошибка:[/bold red]\n{str(e)}",
            title="Error",
            border_style="red"
        ))
        logger.error(f"Error occurred: {str(e)}", exc_info=True)
        raise
    
    logger.info("✨ Программа успешно завершена")

if __name__ == "__main__":
    main()
