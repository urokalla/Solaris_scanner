import os
import json

cache_dir = "/home/udai/RS_PROJECT/stock_scanner_sovereign/data/cache"
for f in os.listdir(cache_dir):
    if f.endswith(".json"):
        path = os.path.join(cache_dir, f)
        try:
            with open(path, "r") as r:
                data = json.load(r)
            
            new_data = {}
            for k, v in data.items():
                if "NSE:" not in k:
                    # Guess format: Indices usually don't have suffixes in this context
                    # But we'll follow the mapper's lead
                    new_key = f"NSE:{k}-EQ"
                else:
                    new_key = k
                new_data[new_key] = v
            
            with open(path, "w") as w:
                json.dump(new_data, w)
            print(f"✅ Fixed {f}")
        except Exception as e:
            print(f"❌ Failed {f}: {e}")
