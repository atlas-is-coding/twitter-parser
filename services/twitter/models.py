from dataclasses import dataclass
from typing import List, Optional

@dataclass
class User:
    id: str
    rest_id: str
    name: str
    screen_name: str
    description: str
    followers_count: int
    following_count: int
    can_dm: bool
    
@dataclass 
class Tweet:
    id: str
    text: str
    created_at: str
    author: User
    reply_count: int
    retweet_count: int
    like_count: int
    quote_count: int
    
@dataclass
class TimelineEntry:
    entry_id: str
    tweet: Tweet
    
@dataclass
class TwitterSearchResponse:
    entries: List[TimelineEntry]