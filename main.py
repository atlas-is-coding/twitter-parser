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
from utils.wallets import BalanceChecker
import sys
from config.constants import CHUNK_SIZE

# Инициализация логирования
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] - %(name)s:%(lineno)d - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '%(message)s'
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'twitter_parser.log',
            'mode': 'a',
            'formatter': 'detailed',
            'level': 'DEBUG',
            'encoding': 'utf-8'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': 'INFO',
            'filters': ['info_and_below'],
            'stream': sys.stdout
        }
    },
    'filters': {
        'info_and_below': {
            '()': lambda: lambda record: record.levelno <= logging.INFO
        }
    },
    'loggers': {
        'twitter_parser': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file']
    }
})

logger = logging.getLogger('twitter_parser')
console = Console()

def load_contract_addresses(file_path: str) -> list:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл с адресами контрактов не найден: {file_path}")
        
    with open(file_path, 'r') as file:
        addresses = [line.strip() for line in file if line.strip()]
    return addresses

def split_into_chunks(lst: list, chunk_size: int) -> list:
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def process_contract_chunk(contract_addresses: list, proxy_manager: ProxyManager, 
                         eligible_holders: list, not_eligible_holders: list, lock: Lock):
    logger.info(f"Начало обработки чанка с {len(contract_addresses)} контрактами")
    twitter_engine = TwitterEngine(proxy_manager=proxy_manager)
    solscan_engine = SolscanEngine(proxy_manager=proxy_manager)
    balance_checker = BalanceChecker()
    
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
            logger.info(f"Обработка контракта: {contract_address}")
            all_holders = solscan_engine.get_holders(contract_address, 100)
            
            if not all_holders or not all_holders.data:
                logger.warning(f"Не удалось получить холдеров для контракта {contract_address}")
                continue

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
                try:
                    logger.debug(f"Проверка холдера: {holder.owner}")
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
                                    balances, usd_values = balance_checker.get_wallet_balance(holder.owner)
                                    total_usd = sum(usd_values.values()) if usd_values else 0
                                    
                                    chunk_stats['eligible'] += 1
                                    eligible_holders.append({
                                        'address': holder.owner,
                                        'twitter_username': entry.tweet.author.screen_name,
                                        'tweet_text': entry.tweet.text,
                                        'can_dm': entry.tweet.author.can_dm,
                                        'followers_count': entry.tweet.author.followers_count,
                                        'total_balance_usd': total_usd,
                                    })
                                    print(f"\n✨ Найден: @{entry.tweet.author.screen_name} ({holder.owner[:8]}...) | Баланс: ${total_usd:.2f}")
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

                except Exception as holder_error:
                    logger.error(f"Ошибка при обработке холдера {holder.owner}: {str(holder_error)}", exc_info=True)

        except Exception as e:
            logger.error(f"Ошибка при обработке контракта {contract_address}: {str(e)}", exc_info=True)
            print(f"\n❌ Ошибка контракта {contract_address}: {str(e)}")

    logger.info(f"Завершена обработка чанка. Статистика: {chunk_stats}")
    return chunk_stats

def main():
    try:
        # Установка кодировки для stdout
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Для старых версий Python
        pass
    
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
    
    def save_results():
        """Функция для сохранения промежуточных результатов"""
        try:
            logger.info("Сохранение промежуточных результатов...")
            eligible_file = csv_writer.write_eligible_holders(eligible_holders)
            not_eligible_file = csv_writer.write_not_eligible_holders(not_eligible_holders)
            
            eligible_path = os.path.relpath(eligible_file) if eligible_file else "Не создан"
            not_eligible_path = os.path.relpath(not_eligible_file) if not_eligible_file else "Не создан"
            
            console.print(Panel(
                "[bold yellow]⚠️ Программа прервана пользователем[/bold yellow]\n\n"
                "[green]📊 Промежуточные результаты:[/green]\n"
                f"✓ Подходящих холдеров: {len(eligible_holders)}\n"
                f"✓ Неподходящих холдеров: {len(not_eligible_holders)}\n\n"
                f"[blue]📂 Файлы сохранены:[/blue]\n"
                f"✓ Подходящие: {eligible_path}\n"
                f"✓ Неподходящие: {not_eligible_path}",
                title="💾 Сохранение результатов",
                border_style="yellow"
            ))
            logger.info(f"Результаты сохранены. Eligible: {eligible_path}, Not eligible: {not_eligible_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении результатов: {str(e)}", exc_info=True)
            console.print(Panel(
                f"[bold red]❌ Ошибка при сохранении результатов:[/bold red]\n{str(e)}",
                title="Error",
                border_style="red"
            ))
    
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
            
            try:
                for future in futures:
                    chunk_stats = future.result()
                    if chunk_stats:
                        total_stats['processed_contracts'] += chunk_stats['processed_contracts']
                        total_stats['total_holders'] += chunk_stats['total_holders']
                        total_stats['processed_holders'] += chunk_stats['processed_holders']
            except KeyboardInterrupt:
                logger.warning("Получен сигнал прерывания (CTRL+C)")
                executor.shutdown(wait=False)
                save_results()
                sys.exit(1)

        print("\n")
        
        # Сохраняем финальные результаты
        save_results()
        
        contracts_progress = (total_stats['processed_contracts'] / total_stats['total_contracts'] * 100) if total_stats['total_contracts'] > 0 else 0
        holders_progress = (total_stats['processed_holders'] / total_stats['total_holders'] * 100) if total_stats['total_holders'] > 0 else 0

        console.print(Panel(
            "[bold green]✨ Обработка успешно завершена![/bold green]\n\n"
            f"[green]📊 Итоговая статистика:[/green]\n"
            f"✓ Контракты: {contracts_progress:.1f}% ({total_stats['processed_contracts']}/{total_stats['total_contracts']})\n"
            f"✓ Холдеры: {holders_progress:.1f}% ({total_stats['processed_holders']}/{total_stats['total_holders']})\n"
            f"✓ Подходящих: {len(eligible_holders)}\n"
            f"✓ Неподходящих: {len(not_eligible_holders)}",
            title="📈 Результаты",
            border_style="green"
        ))
        
        logger.info(f"Processing completed. Eligible: {len(eligible_holders)}, Not eligible: {len(not_eligible_holders)}")
        
    except KeyboardInterrupt:
        logger.warning("Получен сигнал прерывания (CTRL+C)")
        save_results()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        console.print(Panel(
            f"[bold red]❌ Произошла ошибка:[/bold red]\n{str(e)}",
            title="Error",
            border_style="red"
        ))
        save_results()  # Сохраняем результаты даже при ошибке
        raise
    
    logger.info("✨ Программа успешно завершена")

if __name__ == "__main__":
    main()
