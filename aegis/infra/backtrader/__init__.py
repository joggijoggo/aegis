"""Aegis Framework - Unified Backtrader Infrastructure Facade."""

from aegis.infra.backtrader.backtrader_bridge import (
    BridgeAlreadyBoundError as BridgeAlreadyBoundError,
    BacktraderBridge as BacktraderBridge,
    BridgeUnboundError as BridgeUnboundError,
)
from aegis.infra.backtrader.backtrader_broker_adapter import (
    AssetSymbolNotFoundError as AssetSymbolNotFoundError,
    BacktraderBrokerAdapter as BacktraderBrokerAdapter,
    InvalidOrderQuantityError as InvalidOrderQuantityError,
    InvalidProtectionPriceError as InvalidProtectionPriceError,
)
from aegis.infra.backtrader.backtrader_market_feed import (
    BacktraderMarketFeed as BacktraderMarketFeed,
)
from aegis.infra.backtrader.backtrader_proxy_strategy import (
    BacktraderProxyStrategy as BacktraderProxyStrategy,
)
