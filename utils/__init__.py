import re


def regexp_check_sol(text: str) -> bool:
    """
    Проверяет наличие Solana адреса в тексте и фильтрует нежелательные сообщения.
    
    Паттерны:
    - Чистый адрес: [1-9A-HJ-NP-Za-km-z]{32,44}
    - С префиксом sol: sol:[1-9A-HJ-NP-Za-km-z]{32,44}
    - В составе URL: solscan.io/account/[1-9A-HJ-NP-Za-km-z]{32,44}
    - В составе URL: explorer.solana.com/address/[1-9A-HJ-NP-Za-km-z]{32,44}
    """
    # Черный список слов
    blacklist = [
        r'know\b',
        r'this\s+wallet',
        r'dis\s+wallet',
        r'who\s+dis',
        r'who\s+this',
        r'scammer\b',
        r'hacked\b',
        r'bot\b',
        r'spam\b',
        r'fake\b',
        r'report\b',
        r'blocked\b',
        r'suspicious\b',
        r'beware\b',
        r'warning\b',
        r'scam\b',
        r'hack\b',
    ]
    
    # Проверяем наличие слов из черного списка
    blacklist_pattern = '|'.join(blacklist)
    if re.search(blacklist_pattern, text.lower()):
        return False
    
    # Base58 символы без 0, O, I, l
    base58_chars = r'[1-9A-HJ-NP-Za-km-z]'
    
    # Паттерны для разных форматов адресов
    patterns = [
        # Чистый адрес
        rf'{base58_chars}{{32,44}}',
        # С префиксом sol:
        rf'sol:{base58_chars}{{32,44}}',
        # Solscan URL
        rf'solscan\.io/account/{base58_chars}{{32,44}}',
        # Solana Explorer URL
        rf'explorer\.solana\.com/address/{base58_chars}{{32,44}}'
    ]
    
    # Объединяем все паттерны через |
    combined_pattern = '|'.join(f'(?:{pattern})' for pattern in patterns)
    
    # Добавляем границы слова и игнорируем регистр
    final_pattern = rf'\b({combined_pattern})\b'
    
    return bool(re.search(final_pattern, text, re.IGNORECASE))
