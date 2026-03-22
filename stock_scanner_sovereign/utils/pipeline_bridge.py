import os, numpy as np, pyarrow.parquet as pq
class PipelineBridge:
    def __init__(self, d=None):
        from config.settings import settings; self.d = d or settings.PIPELINE_DATA_DIR
    def _files(self, s):
        c = s.strip().upper().replace(":", "_"); u = c.replace("-", "_")
        while "__" in u: u = u.replace("__", "_")
        return [f"{u}.parquet", f"{c}.parquet"]
    def get_historical_data(self, s, limit=1250):
        fs = self._files(s); f = next((os.path.join(self.d, x) for x in fs if os.path.exists(os.path.join(self.d, x))), None)
        if not f: return None
        try:
            t = pq.read_table(f); ac = [c.lower() for c in t.column_names]; tg = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            cd = []
            for x in tg:
                id = next((i for i, c in enumerate(ac) if c == x or (x == 'timestamp' and c == 'ts')), None)
                if id is not None:
                    a = t.column(id).to_numpy()
                    if x == 'timestamp' and np.issubdtype(a.dtype, np.datetime64): a = a.astype('datetime64[s]').astype(np.int64)
                    cd.append(a)
            if not cd: return None
            nd = np.column_stack(cd); nd = nd[nd[:, 0].argsort()[::-1]][:limit]
            return nd[::-1]
        except: return None
    def exists(self, s): return any(os.path.exists(os.path.join(self.d, x)) for x in self._files(s))
