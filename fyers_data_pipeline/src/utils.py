import logging
import os
from datetime import datetime, timedelta

def setup_logging(name: str, log_file: str = "pipeline.log"):
    """Configures logging for the pipeline with duplicate prevention."""
    log_dir = os.path.join(os.getcwd(), "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler
    fh = logging.FileHandler(os.path.join(log_dir, log_file))
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # Prevent propagation to avoid duplicate logs if root logger is also configured
    logger.propagate = False
    
    return logger

def get_date_range(years: int):
    """Returns (from_date, to_date) strings for Fyers API."""
    to_date = datetime.now()
    from_date = to_date - timedelta(days=years * 365)
    return from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")

def chunk_date_range(start_date_str: str, end_date_str: str, chunk_days: int = 100):
    """Chunks a large date range into smaller pieces for Fyers API limits."""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=chunk_days), end_date)
        yield current_start.strftime("%Y-%m-%d"), current_end.strftime("%Y-%m-%d")
        current_start = current_end + timedelta(days=1)
