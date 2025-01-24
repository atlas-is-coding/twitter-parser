from dataclasses import dataclass
from typing import List, Dict, Optional, Any

@dataclass
class TokenHolder:
    address: str
    amount: int
    decimals: int
    owner: str
    rank: int
    withheldAmount: int

@dataclass
class TokenInfo:
    token_address: str
    token_decimals: int
    token_name: str
    token_symbol: str
    token_type: str
    token_icon: Optional[str] = None
    price_usdt: Optional[float] = None
    reputation: Optional[str] = None
    is_show_value: Optional[bool] = None
    is_calculate_on_portfolio: Optional[bool] = None
    token_icon_alternative: Optional[str] = None

@dataclass
class AccountInfo:
    account_address: str
    account_domain: Optional[str] = None
    account_label: Optional[str] = None
    account_icon: Optional[str] = None
    account_tags: Optional[List[str]] = None
    account_type: Optional[str] = None

@dataclass
class TagMetadata:
    icon: Optional[str] = None
    website: Optional[str] = None
    events: Optional[List[Dict[str, Any]]] = None

@dataclass
class Tag:
    tag_id: str
    tag_name: str
    tag_type: int
    tag_metadata: Optional[TagMetadata] = None

@dataclass
class Metadata:
    tokens: Dict[str, TokenInfo]
    accounts: Dict[str, Any]
    tags: Dict[str, Any]
    programs: Dict[str, Any]
    nftCollections: Dict[str, Any]
    nftMarketplaces: Dict[str, Any]

@dataclass
class SolscanResponse:
    success: bool
    data: List[TokenHolder]
    metadata: Metadata

@dataclass
class HolderData:
    address: str
    amount: float
    owner: Optional[str] = None
    rank: Optional[int] = None

@dataclass
class SolscanAPI:
    success: bool
    data: List[TokenHolder]
    metadata: Metadata
    total: Optional[int] = None
