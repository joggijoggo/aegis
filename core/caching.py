"""Aegis Framework - Indicator Caching Engine.

Provides standalone SQLite-backed persistent caching layers with SHA-256
deterministic parameter hashing to accelerate rolling walk-forward loops.
"""
import hashlib
import json
import sqlite3
from typing import Any

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class IndicatorCacheEngine:
    """Manages transactional caching of calculated mathematical vectors."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        db_path: str = '.aegis_cache.db'
    ):
        """Initializes the relational database connection and creates tables.

        Args:
            db_path (str): File system location mapping or ':memory:' context.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._initialize_schema()

# -----------------------------------------------------------------------------

    def get_vectors(
        self,
        asset_pair: str,
        indicator_name: str,
        parameters: dict[str, Any]
    ) -> list[float] | None:
        """Retrieves matching serialized arrays using unique signature hits.

        Args:
            asset_pair (str): Target currency pair tracking symbol.
            indicator_name (str): Named identity of the technical rule.
            parameters (dict[str, Any]): Dictionary layout of inputs.

        Returns:
            list[float] | None: Decoded array of float values or None.
        """
        signature = self._compute_signature(
            asset_pair=asset_pair,
            indicator_name=indicator_name,
            parameters=parameters
        )

        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT payload FROM indicator_cache WHERE signature = ?',
            (signature,)
        )
        row = cursor.fetchone()

        if row:
            return json.loads(row[0])
        return None

# -----------------------------------------------------------------------------

    def save_vectors(
        self,
        asset_pair: str,
        indicator_name: str,
        parameters: dict[str, Any],
        payload_data: list[float]
    ) -> None:
        """Locks calculated floating matrices into persistent database slots.

        Args:
            asset_pair (str): Target currency pair tracking symbol.
            indicator_name (str): Named identity of the technical rule.
            parameters (dict[str, Any]): Dictionary layout of inputs.
            payload_data (list[float]): Linear sequence of numerical values.
        """
        signature = self._compute_signature(
            asset_pair=asset_pair,
            indicator_name=indicator_name,
            parameters=parameters
        )
        serialized_payload = json.dumps(payload_data)

        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO indicator_cache'
            ' (signature, asset_pair, indicator_name, payload)'
            ' VALUES (?, ?, ?, ?)',
            (signature, asset_pair, indicator_name, serialized_payload)
        )
        self.conn.commit()

# -----------------------------------------------------------------------------

    def _initialize_schema(self) -> None:
        """Constructs structural database boundaries if unallocated."""
        cursor = self.conn.cursor()
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS indicator_cache ('
            ' signature TEXT PRIMARY KEY,'
            ' asset_pair TEXT,'
            ' indicator_name TEXT,'
            ' payload TEXT'
            ')'
        )
        self.conn.commit()

# -----------------------------------------------------------------------------

    def _compute_signature(
        self,
        asset_pair: str,
        indicator_name: str,
        parameters: dict[str, Any]
    ) -> str:
        """Generates a unique deterministic SHA-256 signature key payload.

        Args:
            asset_pair (str): Target currency pair tracking symbol.
            indicator_name (str): Named identity of the technical rule.
            parameters (dict[str, Any]): Dictionary layout of inputs.

        Returns:
            str: Hexadecimal digest representation matching config signatures.
        """
        serialized_params = json.dumps(parameters, sort_keys=True)
        raw_key = f'{asset_pair}:{indicator_name}:{serialized_params}'
        return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
