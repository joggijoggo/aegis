"""Aegis Framework - Core Domain Exceptions.

Provides specific exception structures to enable engine fault routing.
"""

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AegisError(Exception):
    """Exception for all framework-level anomalies."""

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BrokerConnectionError(AegisError):
    """Broker connection failure."""

# -----------------------------------------------------------------------------

class BrokerOrderNotFoundError(AegisError):
    """The requested order was not found within the active broker's open carnet."""

# -----------------------------------------------------------------------------

class BrokerPositionNotFoundError(AegisError):
    """The requested market exposure was not found within the active portfolio ledger."""

# -----------------------------------------------------------------------------

class ContractNotFoundError(AegisError):
    """Financial contract is missing from the registry mapping."""

# -----------------------------------------------------------------------------

class ContractVolumeUnderflowError(AegisError):
    """Calculated position volume is lower than the broker minimum contract threshold."""

# -----------------------------------------------------------------------------

class CorruptedOrderGroupError(AegisError):
    """Execution mutation attempt over a compromised transaction state."""

# -----------------------------------------------------------------------------

class DuplicateOrderGroupError(AegisError):
    """The execution engine attempted to register an already existing order group identifier."""

# -----------------------------------------------------------------------------

class MarketTimeoutError(AegisError):
    """Feed timeout expiration."""

# -----------------------------------------------------------------------------

class MissingExchangeRateError(AegisError):
    """Requested currency exchange rate is missing."""

# -----------------------------------------------------------------------------

class NettingRestrictionError(AegisError):
    """Trading bot execution concurrency violation under strict netting rules."""

# -----------------------------------------------------------------------------

class StrategyError(AegisError):
    """Exception for strategy and signal calculation anomalies."""

# -----------------------------------------------------------------------------

class UnsupportedBrokerEventError(AegisError):
    """The received infrastructure event category is not supported by the execution engine."""

# -----------------------------------------------------------------------------

class UntrackedOrderException(AegisError):
    """Tracking layer breach due to an unrecognized group or order identifier."""

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class InvalidSignalError(StrategyError):
    """Generated market convictions violate contract boundaries."""

# -----------------------------------------------------------------------------

class InsufficientHistoryError(StrategyError):
    """Historical data series length is shorter than required."""

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
