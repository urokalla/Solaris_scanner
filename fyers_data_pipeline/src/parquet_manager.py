import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import logging

logger = logging.getLogger(__name__)

class ParquetManager:
    """
    Handles Parquet file operations for historical market data.
    """
    def __init__(self, storage_path: str = "data/historical"):
        self.storage_path = storage_path
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def get_file_path(self, symbol: str) -> str:
        """Returns the absolute path for a symbol's Parquet file."""
        # Clean symbol name for filename (remove colon if present)
        clean_symbol = symbol.replace(":", "_").replace("-", "_")
        return os.path.join(self.storage_path, f"{clean_symbol}.parquet")

    def save_data(self, symbol: str, df: pd.DataFrame, overwrite: bool = False):
        """
        Saves DataFrame to Parquet. If overwrite is False, it appends to existing.
        """
        file_path = self.get_file_path(symbol)
        
        if df.empty:
            logger.warning(f"Empty DataFrame provided for {symbol}. Skipping.")
            return

        # Ensure index is datetime if applicable, or sorted
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')

        if not os.path.exists(file_path) or overwrite:
            df.to_parquet(file_path, engine='pyarrow', index=False)
            logger.info(f"Saved {len(df)} rows to {file_path}")
        else:
            # Append logic
            existing_df = pd.read_parquet(file_path)
            
            # Remove duplicates by timestamp if present
            if 'timestamp' in df.columns:
                combined_df = pd.concat([existing_df, df]).drop_duplicates(subset=['timestamp'], keep='last')
            else:
                combined_df = pd.concat([existing_df, df])
            
            combined_df = combined_df.sort_values('timestamp') if 'timestamp' in combined_df.columns else combined_df
            combined_df.to_parquet(file_path, engine='pyarrow', index=False)
            logger.info(f"Appended reaching {len(combined_df)} rows for {symbol}")

    def read_data(self, symbol: str) -> pd.DataFrame:
        """Reads historical data for a symbol."""
        file_path = self.get_file_path(symbol)
        if os.path.exists(file_path):
            return pd.read_parquet(file_path)
        return pd.DataFrame()
