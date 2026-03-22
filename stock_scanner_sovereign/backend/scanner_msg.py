import time, numpy as np
def on_message_handler(self, msg):
    for cb in self.callbacks:
        try: cb(msg)
        except: pass
    for t in (msg if isinstance(msg, list) else [msg]):
        s = t.get('symbol')
        if not s or (idx := self.get_idx(s)) is None: continue
        lp, v = float(t.get('lp', 0)), float(t.get('v', 0) or 0)
        self.arr[idx]['ltp'], self.arr[idx]['heartbeat'] = lp, time.time()
        pc = self.pc_cache.get(s)
        if pc:
            ch = round(((lp/pc)-1)*100, 2)
            self.arr[idx]['change_pct'], self.arr[idx]['p1d'] = ch, f"{ch:+.2f}%".encode()
            self.arr[idx]['price_up'], self.arr[idx]['price_down'] = int(ch > 0), int(ch < 0)
        if v > 0:
            self.arr[idx]['rv_val'] = v
            av = self.av_cache.get(s)
            if av:
                rv = round(v/av, 2)
                ch_p = float(self.arr[idx]['change_pct'])
                self.arr[idx]['rv'] = rv
                self.arr[idx]['rv_up'] = int(rv >= 1.5 and ch_p >= 0)
                self.arr[idx]['rv_down'] = int(rv >= 1.5 and ch_p < 0)
