"""Aegis Framework - Unified Backtrader Infrastructure Facade."""

from aegis.infra.backtrader.backtrader_bridge import (
    BacktraderBridge as BacktraderBridge,
)
from aegis.infra.backtrader.backtrader_bridge import (
    BridgeAlreadyBoundError as BridgeAlreadyBoundError,
)
from aegis.infra.backtrader.backtrader_bridge import (
    BridgeUnboundError as BridgeUnboundError,
)
from aegis.infra.backtrader.backtrader_broker_adapter import (
    AssetSymbolNotFoundError as AssetSymbolNotFoundError,
)
from aegis.infra.backtrader.backtrader_broker_adapter import (
    BacktraderBrokerAdapter as BacktraderBrokerAdapter,
)
from aegis.infra.backtrader.backtrader_broker_adapter import (
    InvalidOrderQuantityError as InvalidOrderQuantityError,
)
from aegis.infra.backtrader.backtrader_broker_adapter import (
    InvalidProtectionPriceError as InvalidProtectionPriceError,
)
from aegis.infra.backtrader.backtrader_market_feed import (
    BacktraderMarketFeed as BacktraderMarketFeed,
)
from aegis.infra.backtrader.backtrader_proxy_strategy import (
    BacktraderProxyStrategy as BacktraderProxyStrategy,
)
from aegis.infra.backtrader.backtrader_runner import (
    BacktraderRunner as BacktraderRunner,
)
from aegis.infra.backtrader.backtrader_schemes import (
    ForexDynamicLeverageScheme as ForexDynamicLeverageScheme,
)
from aegis.infra.backtrader.backtrader_schemes import (
    ForexFixedMarginScheme as ForexFixedMarginScheme,
)
from aegis.infra.backtrader.backtrader_schemes import (
    FutureFixedMarginScheme as FutureFixedMarginScheme,
)
from aegis.infra.backtrader.backtrader_schemes import (
    SpotStockCashScheme as SpotStockCashScheme,
)
