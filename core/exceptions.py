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

class ContractNotFoundError(AegisError):
    """Financial contract is missing from the registry mapping."""

# -----------------------------------------------------------------------------

class MarketTimeoutError(AegisError):
    """Feed timeout expiration."""

# -----------------------------------------------------------------------------

class StrategyError(AegisError):
    """Exception for strategy and signal calculation anomalies."""

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
