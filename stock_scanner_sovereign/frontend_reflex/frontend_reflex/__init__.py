import os, sys

# Add the project root to sys.path to resolve backend and utils
current_dir = os.path.dirname(os.path.abspath(__file__))
scanner_root = os.path.abspath(os.path.join(current_dir, "../../"))
if scanner_root not in sys.path:
    sys.path.append(scanner_root)
