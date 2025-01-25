# Общие настройки
CHUNK_SIZE = 5
MAX_RETRIES = 5
REQUEST_TIMEOUT = 30

# Настройки Twitter Parser
TWITTER_SEARCH_PAGE_SIZE = 20
TWITTER_MAX_PAGE = 101
TWITTER_DELAY_BETWEEN_REQUESTS = 1

# Настройки Solscan
SOLSCAN_PAGE_SIZE = 100
SOLSCAN_MAX_PAGE = 101
SOLSCAN_DELAY_BETWEEN_REQUESTS = 1

# Настройки Wallet Scanner
WALLET_CACHE_DURATION = 300  # 5 минут в секундах
WALLET_BATCH_SIZE = 50
WALLET_MAX_WORKERS = 10
WALLET_RATE_LIMIT_DELAY = 0.5

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

# API endpoints
JUPITER_TOKENS_URL = "https://token.jup.ag/all"
COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
JUPITER_PRICE_URL = "https://api.jup.ag/price/v2"
RAYDIUM_PRICE_URL = "https://api.raydium.io/v2/main/price"

# Solana constants
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA" 