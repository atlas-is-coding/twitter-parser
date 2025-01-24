# Twitter Eligibility Checker

## Описание проекта
Этот проект представляет собой инструмент для проверки eligibility Twitter-аккаунтов на основе заданных критериев. Программа анализирует Twitter-профили и создает два CSV-файла: один для eligible аккаунтов, другой для not eligible.

## Структура проекта
├── config/
│ ├── init.py
│ ├── config.py
│ └── contractAddresses.txt
├── output/
│ ├── eligible_[timestamp].csv
│ └── not_eligible_[timestamp].csv
├── services/
│ └── twitter/
│ └── twitter_engine.py
├── utils/
│ ├── init.py
│ └── csv_writer.py
└── main.py


## Предварительные требования
- Python 3.8 или выше
- pip (менеджер пакетов Python)

## Установка

1. Клонируйте репозиторий:
bash
git clone [url-вашего-репозитория]
cd [название-директории]