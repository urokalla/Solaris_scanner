import os, numpy as np, pyarrow as pa, pyarrow.parquet as pq
from datetime import datetime

def save_parquet_vectorized(path, data, names=['timestamp', 'open', 'high', 'low', 'close', 'volume']):
    if os.path.exists(path):
        exist = pq.read_table(path); arrs = []
        for i, n in enumerate(names):
            t = exist.column(n).type
            if n == 'timestamp' and pa.types.is_timestamp(t):
                u = (1000 if t.unit == 'ms' else 1); ts = (data[:, i] * u).astype(np.int64)
                arrs.append(pa.array(ts).cast(t))
            else: arrs.append(pa.array(data[:, i]).cast(t))
        new = pa.Table.from_arrays(arrs, names=names)
        tab = pa.concat_tables([exist, new]).combine_chunks()
        ts_v = tab.column('timestamp').to_numpy(); _, idx = np.unique(ts_v, return_index=True)
        tab = tab.take(idx)
    else:
        arrs = [pa.array(data[:, i]) for i in range(6)]
        arrs[0] = pa.array(data[:, 0].astype('datetime64[s]'))
        tab = pa.Table.from_arrays(arrs, names=names)
    pq.write_table(tab.sort_by("timestamp"), path)

def append_single_row(path, row_data, names=['timestamp', 'open', 'high', 'low', 'close', 'volume']):
    d = {n: [datetime.fromtimestamp(row_data[0]) if n=='timestamp' else float(row_data[i])] for i, n in enumerate(names)}
    new_t = pa.Table.from_pydict(d)
    if os.path.exists(path):
        tab = pq.read_table(path); ts_c = tab.column('timestamp').to_numpy().astype('datetime64[s]').astype(np.int64)
        tab = tab.filter(pa.array(ts_c != int(row_data[0])))
        tab = pa.concat_tables([tab, new_t])
    else: tab = new_t
    pq.write_table(tab, path)
