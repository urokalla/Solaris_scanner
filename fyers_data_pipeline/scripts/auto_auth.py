"""Placeholder for the previous non-interactive Fyers login script.

We tried automating the full `vagator/v2` OTP + PIN flow here, but Fyers rotates
that flow without notice and it cannot be relied on in production. The scanner
now runs in **manual-token mode**:

- Operator runs ``stock_scanner_sovereign/manual_token.py`` once a day (or the
  Fyers dashboard) and writes a fresh JWT into
  ``stock_scanner_sovereign/access_token.txt``.
- ``eod_sync.py`` detects expired tokens early, exits 0 and prints
  ``EOD_SYNC_RESULT skipped reason=token_expired`` so ``main.py`` can back off
  without spamming the logs.
- The very next scheduler tick after the token file mtime changes will run
  EOD again automatically.

This file is kept so any old reference to it produces a clear, non-zero exit
instead of mysteriously pretending to refresh the token.
"""

from __future__ import annotations

import sys

_MESSAGE = (
    "auto_auth.py is disabled — Fyers requires manual token refresh. "
    "Run stock_scanner_sovereign/manual_token.py and overwrite "
    "stock_scanner_sovereign/access_token.txt."
)


def main() -> int:
    print(_MESSAGE, file=sys.stderr, flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
