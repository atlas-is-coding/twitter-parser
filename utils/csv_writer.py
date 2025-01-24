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
        """Создает директорию output, если она не существует"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _get_timestamp(self) -> str:
        """Возвращает текущую метку времени для имени файла"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def write_eligible_holders(self, holders: List[Dict]):
        """Записывает подходящих держателей в CSV файл"""
        timestamp = self._get_timestamp()
        filename = os.path.join(self.output_dir, f"eligible_{timestamp}.csv")
        
        logger.info(f"📝 Запись данных в файл: {filename}")
        console.print(f"[cyan]Writing data to:[/cyan] {filename}")
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Адрес', 'Имя в Twitter', 'Текст твита', 'Личка Открыта', 'Число подписчиков'])
                for holder in holders:
                    writer.writerow([
                        holder.get('address', ''),
                        holder.get('twitter_username', ''),
                        holder.get('tweet_text', ''),
                        holder.get('can_dm', ''),
                        holder.get('followers_count', '')
                    ])
            console.print(f"[green]Successfully written {len(holders)} records to {filename}[/green]")
            logger.info(f"✅ Успешно записано {len(holders)} строк в {filename}")
        except Exception as e:
            console.print(f"[red]Error writing to CSV:[/red] {str(e)}", style="bold red")
            logger.error(f"❌ Ошибка при записи в файл {filename}: {str(e)}", exc_info=True)
            raise

    def write_not_eligible_holders(self, holders: List[Dict]):
        """Записывает неподходящих держателей в CSV файл"""
        timestamp = self._get_timestamp()
        filename = os.path.join(self.output_dir, f"not_eligible_{timestamp}.csv")
        
        logger.info(f"📝 Запись данных в файл: {filename}")
        console.print(f"[cyan]Writing data to:[/cyan] {filename}")
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Адрес', 'Причина'])
                for holder in holders:
                    writer.writerow([
                        holder.get('address', ''),
                        holder.get('reason', '')
                    ])
            console.print(f"[green]Successfully written {len(holders)} records to {filename}[/green]")
            logger.info(f"✅ Успешно записано {len(holders)} строк в {filename}")
        except Exception as e:
            console.print(f"[red]Error writing to CSV:[/red] {str(e)}", style="bold red")
            logger.error(f"❌ Ошибка при записи в файл {filename}: {str(e)}", exc_info=True)
            raise

def write_to_csv(data, filename):
    logger.info(f"Writing data to CSV file: {filename}")
    console.print(f"[cyan]Writing data to:[/cyan] {filename}")
    try:
        # ... existing code ...
        console.print(f"[green]Successfully written {len(data)} records to {filename}[/green]")
        logger.info(f"Successfully written {len(data)} records to {filename}")
    except Exception as e:
        console.print(f"[red]Error writing to CSV:[/red] {str(e)}", style="bold red")
        logger.error(f"Error writing to CSV: {str(e)}", exc_info=True)
        raise
