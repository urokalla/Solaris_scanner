import os, time, datetime, threading, numpy as np; from config.settings import settings; from utils.parquet_io import append_single_row

def run_persistence_loop(scanner):
    while not getattr(scanner, '_stop_event', threading.Event()).is_set():
        time.sleep(300); now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
        if now.hour == 15 and 35 <= now.minute <= 45: 
            try: finalize_and_append_daily_data(scanner)
            except: pass

def finalize_and_append_daily_data(scanner):
    p_dir = getattr(settings, "PIPELINE_DATA_DIR", ""); today = int(datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    if not os.path.exists(p_dir): return
    with scanner.lock: syms = list(scanner.buffers.keys())
    for s in syms:
        try:
            with scanner.lock: rb = scanner.buffers.get(s); d = rb.get_ordered_view() if rb else []
            if len(d) == 0: continue
            mask = (d[:, 0] >= today)
            if np.any(mask): append_single_row(os.path.join(p_dir, f"{s.replace(':','_')}.parquet"), d[mask][-1])
        except: pass
