import csv
import os
from datetime import datetime
from typing import List, Dict
import logging
from rich.console import Console

logger = logging.getLogger('twitter_parser')
console = Console()

class CSVWriter:
    def __init__(self):
        self.output_dir = "output"
        self._ensure_output_directory()

    def _ensure_output_directory(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _get_timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def write_eligible_holders(self, holders: List[dict]) -> str:
        timestamp = self._get_timestamp()
        filename = os.path.join(self.output_dir, f'eligible_{timestamp}.csv')
        
        try:
            # Используем utf-8-sig для корректной работы с Excel в Windows
            with open(filename, 'w', newline='', encoding='utf-8-sig', errors='replace') as file:
                writer = csv.writer(file)
                writer.writerow([
                    'Address', 'Twitter Username', 'Tweet Text', 
                    'Can DM', 'Followers Count', 'Total Balance USD'
                ])
                
                for holder in holders:
                    # Обработка потенциально проблемных строк
                    tweet_text = str(holder.get('tweet_text', '')).encode('utf-8', errors='replace').decode('utf-8')
                    writer.writerow([
                        holder.get('address', ''),
                        holder.get('twitter_username', ''),
                        tweet_text,
                        holder.get('can_dm', False),
                        holder.get('followers_count', 0),
                        f"${holder.get('total_balance_usd', 0):.2f}",
                    ])
            
            logger.info(f"✅ Успешно сохранено {len(holders)} записей в {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Ошибка при записи в файл {filename}: {str(e)}", exc_info=True)
            console.print(f"[red]Ошибка при записи в CSV:[/red] {str(e)}")
            return None

    def write_not_eligible_holders(self, holders: List[Dict]):
        timestamp = self._get_timestamp()
        filename = os.path.join(self.output_dir, f"not_eligible_{timestamp}.csv")
        
        try:
            # Используем utf-8-sig для корректной работы с Excel в Windows
            with open(filename, 'w', newline='', encoding='utf-8-sig', errors='replace') as f:
                writer = csv.writer(f)
                writer.writerow(['Адрес', 'Причина'])
                for holder in holders:
                    # Безопасное получение значений с обработкой ошибок кодировки
                    reason = str(holder.get('reason', '')).encode('utf-8', errors='replace').decode('utf-8')
                    writer.writerow([
                        holder.get('address', ''),
                        reason
                    ])
                    
            logger.info(f"✅ Успешно записано {len(holders)} строк в {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Ошибка при записи в файл {filename}: {str(e)}", exc_info=True)
            console.print(f"[red]Ошибка при записи в CSV:[/red] {str(e)}")
            return None

def write_to_csv(data, filename):
    logger.info(f"Writing data to CSV file: {filename}")
    console.print(f"[cyan]Writing data to:[/cyan] {filename}")
    try:
        console.print(f"[green]Successfully written {len(data)} records to {filename}[/green]")
        logger.info(f"Successfully written {len(data)} records to {filename}")
    except Exception as e:
        console.print(f"[red]Error writing to CSV:[/red] {str(e)}", style="bold red")
        logger.error(f"Error writing to CSV: {str(e)}", exc_info=True)
        raise
