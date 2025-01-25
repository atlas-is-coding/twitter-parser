# Solana Wallet Scanner

Инструмент для сканирования и анализа балансов кошельков в сети Solana.

## Описание

Этот проект представляет собой Python-скрипт для:
- Проверки балансов SOL и других токенов в кошельках Solana
- Нахождение твитов с упоминанием кошелька
- Получения актуальных цен токенов из различных источников (CoinGecko, Jupiter, Raydium)
- Расчета общей стоимости портфеля в USD

## Требования

- Python 3.8+
- pip (менеджер пакетов Python)

## Установка

1. Клонируйте репозиторий:

   ```bash
   git clone https://github.com/yourusername/solana-wallet-scanner.git
   cd solana-wallet-scanner
   ```

2. Создайте виртуальное окружение и активируйте его:

   ```bash
   python -m venv venv
   source venv/bin/activate  # Для Linux/MacOS
   .\venv\Scripts\activate   # Для Windows
   ```

3. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

## Настройка

1. **Конфигурация API**: Откройте файл `config/config.py` и добавьте необходимые API ключи

2. **Адреса контрактов**: В файле `config/contractAddresses.txt` укажите адреса контрактов

3. **Прокси-серверы**: Обязательно использовать прокси формата http(s)://user:pass@host:port

## Использование

1. Запустите основной скрипт:

   ```bash
   python main.py
   ```

2. Результаты будут сохранены в CSV файлы в папке `output`.