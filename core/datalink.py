"""Aegis Framework - Historical CSV DataLink Layer.

Handles parsing, timezone localization, and type enforcement of flat disk records
into safe multi-asset pandas DataFrames.
"""
import os

import pandas as pd

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class LocalCsvDataLink:
    """Ingests and sanitizes multi-asset historical CSV data files."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        root_directory: str
    ):
        """Initializes the data link repository path anchor.

        Args:
            root_directory (str): Local path mapping target historical assets.
        """
        self.root_directory = root_directory

# -----------------------------------------------------------------------------

    def load_asset_history(
        self,
        asset_pair: str
    ) -> pd.DataFrame:
        """Loads and formats a specific target currency pair time series.

        Args:
            asset_pair (str): Target currency pair symbol identifier.

        Returns:
            pd.DataFrame: Timezone-aware UTC synchronized price matrix.

        Raises:
            FileNotFoundError: If the target asset file does not exist on disk.
        """
        file_name = f'{asset_pair}.csv'
        full_path = os.path.join(self.root_directory, file_name)

        if not os.path.exists(full_path):
            raise FileNotFoundError(
                f'Aegis DataLink failure: {full_path} cannot be located.'
            )

        # Parse and index the timestamp column automatically
        df = pd.read_csv(
            full_path,
            parse_dates=['timestamp'],
            index_col='timestamp'
        )

        # Enforce strict timezone awareness anchored to pure UTC bounds
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')

        # Guarantee critical parameters extract under precise float constraints
        target_columns = ['open', 'high', 'low', 'close', 'volume', 'atr']
        for col in target_columns:
            if col in df.columns:
                df[col] = df[col].astype(float)

        return df[target_columns]

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
