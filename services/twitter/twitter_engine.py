import requests
from requests.exceptions import RequestException
from typing import Optional
from dacite import from_dict, Config
import time
import logging
from rich.console import Console

from config.config import TWITTER_BASE_HEADERS
from services.twitter.models import TwitterSearchResponse, Tweet, User, TimelineEntry
from utils.proxy_manager import ProxyManager
from utils.headers_manager import HeadersManager
from config.constants import (
    MAX_RETRIES, REQUEST_TIMEOUT, TWITTER_SEARCH_PAGE_SIZE,
    TWITTER_DELAY_BETWEEN_REQUESTS
)

logger = logging.getLogger('twitter_parser')
console = Console()

class TwitterEngine:
    def __init__(self, proxy_manager: Optional[ProxyManager] = None, proxy_url: Optional[str] = None):
        logger.debug("Initializing TwitterEngine")
        self.proxy_manager = proxy_manager or ProxyManager()
        self.headers_manager = HeadersManager(TWITTER_BASE_HEADERS)
        self.config = Config(
            check_types=False,
            cast=[int, float]
        )
        self.retry_count = 0
        self.max_retries = MAX_RETRIES
        self.console = Console()

    @staticmethod
    def construct_search_url(query: str) -> str:
        return f"https://x.com/i/api/graphql/S9Y5e9vylJCliXvZ8MOB3g/SearchTimeline?variables=%7B%22rawQuery%22%3A%22{query}%22%2C%22count%22%3A20%2C%22querySource%22%3A%22typed_query%22%2C%22product%22%3A%22Latest%22%7D&features=%7B%22profile_label_improvements_pcf_label_in_post_enabled%22%3Atrue%2C%22rweb_tipjar_consumption_enabled%22%3Atrue%2C%22responsive_web_graphql_exclude_directive_enabled%22%3Atrue%2C%22verified_phone_label_enabled%22%3Afalse%2C%22creator_subscriptions_tweet_preview_api_enabled%22%3Atrue%2C%22responsive_web_graphql_timeline_navigation_enabled%22%3Atrue%2C%22responsive_web_graphql_skip_user_profile_image_extensions_enabled%22%3Afalse%2C%22premium_content_api_read_enabled%22%3Afalse%2C%22communities_web_enable_tweet_community_results_fetch%22%3Atrue%2C%22c9s_tweet_anatomy_moderator_badge_enabled%22%3Atrue%2C%22responsive_web_grok_analyze_button_fetch_trends_enabled%22%3Afalse%2C%22responsive_web_grok_analyze_post_followups_enabled%22%3Atrue%2C%22responsive_web_jetfuel_frame%22%3Afalse%2C%22responsive_web_grok_share_attachment_enabled%22%3Atrue%2C%22articles_preview_enabled%22%3Atrue%2C%22responsive_web_edit_tweet_api_enabled%22%3Atrue%2C%22graphql_is_translatable_rweb_tweet_is_translatable_enabled%22%3Atrue%2C%22view_counts_everywhere_api_enabled%22%3Atrue%2C%22longform_notetweets_consumption_enabled%22%3Atrue%2C%22responsive_web_twitter_article_tweet_consumption_enabled%22%3Atrue%2C%22tweet_awards_web_tipping_enabled%22%3Afalse%2C%22creator_subscriptions_quote_tweet_preview_enabled%22%3Afalse%2C%22freedom_of_speech_not_reach_fetch_enabled%22%3Atrue%2C%22standardized_nudges_misinfo%22%3Atrue%2C%22tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled%22%3Atrue%2C%22rweb_video_timestamps_enabled%22%3Atrue%2C%22longform_notetweets_rich_text_read_enabled%22%3Atrue%2C%22longform_notetweets_inline_media_enabled%22%3Atrue%2C%22responsive_web_grok_image_annotation_enabled%22%3Atrue%2C%22responsive_web_enhance_cards_enabled%22%3Afalse%7D"

    def _parse_user_data(self, tweet_data: dict) -> dict:
        """Подготовка данных пользователя для десериализации"""
        try:
            user_data = tweet_data['core']['user_results']['result']
            legacy = user_data['legacy']
            return {
                'id': user_data['id'],
                'rest_id': user_data['rest_id'],
                'name': legacy['name'],
                'screen_name': legacy['screen_name'],
                'description': legacy['description'],
                'followers_count': legacy['followers_count'],
                'following_count': legacy['friends_count'],
                'can_dm': legacy.get('can_dm', False)
            }
        except KeyError:
            user_result = tweet_data.get('user_results', {}).get('result', {})
            legacy = user_result.get('legacy', {})
            return {
                'id': user_result.get('id', ''),
                'rest_id': user_result.get('rest_id', ''),
                'name': legacy.get('name', ''),
                'screen_name': legacy.get('screen_name', ''),
                'description': legacy.get('description', ''),
                'followers_count': legacy.get('followers_count', 0),
                'following_count': legacy.get('friends_count', 0),
                'can_dm': legacy.get('can_dm', False)
            }

    def _parse_tweet_data(self, tweet_data: dict, user_dict: dict) -> dict:
        """Подготовка данных твита для десериализации"""
        if 'tweet' in tweet_data:
            tweet_data = tweet_data['tweet']
            
        legacy_data = tweet_data.get('legacy', {})
        return {
            'id': tweet_data.get('rest_id', ''),
            'text': legacy_data.get('full_text', ''),
            'created_at': legacy_data.get('created_at', ''),
            'author': user_dict,
            'reply_count': legacy_data.get('reply_count', 0),
            'retweet_count': legacy_data.get('retweet_count', 0),
            'like_count': legacy_data.get('favorite_count', 0),
            'quote_count': legacy_data.get('quote_count', 0)
        }

    def parse_tweet(self, tweet_data: dict) -> Optional[Tweet]:
        """Парсинг твита из JSON-данных"""
        try:
            user_dict = self._parse_user_data(tweet_data)
            tweet_dict = self._parse_tweet_data(tweet_data, user_dict)
            
            return from_dict(
                data_class=Tweet,
                data=tweet_dict,
                config=self.config
            )
        except Exception as e:
            print(f"Ошибка при парсинге твита: {str(e)}")
            return None

    def get_latest_posts(self, query: str) -> Optional[TwitterSearchResponse]:
        proxy_url = self.proxy_manager.get_proxy()
        headers = self.headers_manager.get_headers()
        
        if not proxy_url or not headers:
            logger.error(f"Не удалось получить прокси или заголовки для запроса. Proxy: {proxy_url}, Headers present: {bool(headers)}")
            return None
        
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        try:
            logger.debug(f"Отправка запроса к Twitter API для query: {query}")
            response = requests.get(
                self.construct_search_url(query), 
                headers=headers, 
                proxies=proxies,
                timeout=30
            )
            
            if response.status_code == 429:
                logger.warning(f"Достигнут лимит запросов (429). Попытка: {self.retry_count + 1}/{self.max_retries}")
                if self.retry_count >= self.max_retries:
                    logger.error("Превышено максимальное количество попыток после ошибки 429")
                    self.retry_count = 0
                    return None
                    
                wait_time = 2 ** self.retry_count
                logger.info(f"Ожидание {wait_time} секунд перед повторной попыткой")
                time.sleep(wait_time)
                self.retry_count += 1
                return self.get_latest_posts(query)
            
            response.raise_for_status()
            
            data = response.json()
            entries_data = data['data']['search_by_raw_query']['search_timeline']['timeline']['instructions'][0]['entries']
            
            logger.info(f"Получено {len(entries_data)} записей для query: {query}")
            
            timeline_entries = []
            for entry_data in entries_data:
                if 'tweet_results' not in entry_data['content'].get('itemContent', {}):
                    continue
                    
                tweet_data = entry_data['content']['itemContent']['tweet_results']['result']
                tweet = self.parse_tweet(tweet_data)
                
                if tweet:
                    entry_dict = {
                        'entry_id': entry_data['entryId'],
                        'tweet': tweet
                    }
                    timeline_entry = from_dict(
                        data_class=TimelineEntry,
                        data=entry_dict,
                        config=self.config
                    )
                    timeline_entries.append(timeline_entry)
            
            return TwitterSearchResponse(entries=timeline_entries)
            
        except RequestException as error:
            logger.error(f"Ошибка запроса к Twitter API: {str(error)}", exc_info=True)
            self.proxy_manager.report_error(proxy_url)
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении твитов: {str(e)}", exc_info=True)
            return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    console = Console()
    
    engine = TwitterEngine()
    query = "solana"
    console.print(f"[blue]Поиск твитов по запросу:[/blue] {query}")
    
    response = engine.get_latest_posts(query)
    if response:
        console.print(f"[green]Получено твитов:[/green] {len(response.entries)}")
        for entry in response.entries[:3]:
            tweet = entry.tweet
            console.print("\n[bold blue]═══════════════════════════════[/bold blue]")
            console.print(f"[cyan]Автор:[/cyan] @{tweet.author.screen_name}")
            console.print(f"[cyan]Текст:[/cyan] {tweet.text}")
            console.print(f"[cyan]Статистика:[/cyan] ❤️ {tweet.like_count} 🔄 {tweet.retweet_count} 💬 {tweet.reply_count}")
    else:
        console.print("[red]Не удалось получить твиты[/red]") 