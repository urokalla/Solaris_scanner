import os
import re
import base64
import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fyers_apiv3 import fyersModel
from dotenv import load_dotenv


def _ist_calendar_date_str() -> str:
    """IST date for rolling daily API counters (Asia/Kolkata)."""
    return datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()


def _normalize_access_token(raw: str) -> str:
    """Strip BOM, newlines from manual pastes, and wrapping quotes."""
    s = (raw or "").replace("\ufeff", "").strip()
    if "\n" in s or "\r" in s:
        s = s.splitlines()[0].strip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        s = s[1:-1].strip()
    # JWT is ASCII; drop invisible / stray chars that break Authorization
    s = "".join(ch for ch in s if ch.isascii() and (ch.isalnum() or ch in "._=-"))
    return s


def _strip_env_scalar(value: str | None) -> str:
    """Strip whitespace and optional surrounding quotes from .env values."""
    if value is None:
        return ""
    s = str(value).strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    return s


# Fyers My API App ID in SDK is like LR8X7AEHVC-100 (prefix + hyphen + tier digits).
# JWT `aud` is often a *list of scope strings* (d:1, x:0) — not the app id; never str(list) that.
_FYERS_APP_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{4,}-\d{2,3}$")


def _looks_like_fyers_app_id(s: str) -> bool:
    s = (s or "").strip()
    return bool(_FYERS_APP_ID_PATTERN.match(s))


def _deep_find_fyers_app_id(obj) -> str | None:
    """Search nested JWT claims (e.g. oms) for a string matching App ID shape."""
    if isinstance(obj, str) and _looks_like_fyers_app_id(obj):
        return obj.strip()
    if isinstance(obj, dict):
        for v in obj.values():
            r = _deep_find_fyers_app_id(v)
            if r:
                return r
    if isinstance(obj, (list, tuple)):
        for item in obj:
            r = _deep_find_fyers_app_id(item)
            if r:
                return r
    return None


def _extract_fyers_app_id_from_payload(payload: dict) -> str | None:
    """
    Find a value that looks like the Fyers App ID string inside JWT claims.
    `aud` may be str, or list mixing real app id with OAuth scopes — only accept pattern match.
    """
    for key in ("aud", "app_id", "client_id", "appId", "AppId", "fyAppId"):
        v = payload.get(key)
        if v is None:
            continue
        if isinstance(v, str):
            if _looks_like_fyers_app_id(v):
                return v.strip()
        elif isinstance(v, (list, tuple)):
            for item in v:
                if isinstance(item, str) and _looks_like_fyers_app_id(item):
                    return item.strip()
    sub = payload.get("sub")
    if isinstance(sub, str) and _looks_like_fyers_app_id(sub):
        return sub.strip()
    return _deep_find_fyers_app_id(payload)


def _fyers_jwt_inspect(token: str) -> dict:
    """
    Decode access-token JWT payload (no signature check).
    Fyers has used different claim names; try several. Always return a dict for connect().
    """
    out: dict = {
        "payload": None,
        "parse_error": None,
        "app_id": None,
        "exp": None,
        "expired": False,
        "payload_keys": [],
    }
    try:
        parts = (token or "").strip().split(".")
        if len(parts) != 3:
            out["parse_error"] = "token is not a 3-part JWT"
            return out
        pad = "=" * (-len(parts[1]) % 4)
        raw = base64.urlsafe_b64decode(parts[1] + pad)
        payload = json.loads(raw)
        out["payload"] = payload
        out["payload_keys"] = sorted(payload.keys())
        out["app_id"] = _extract_fyers_app_id_from_payload(payload)
        exp = payload.get("exp")
        if isinstance(exp, (int, float)):
            out["exp"] = int(exp)
            now_ts = datetime.now(timezone.utc).timestamp()
            out["expired"] = now_ts > float(exp)
    except Exception as e:
        out["parse_error"] = str(e)
    return out


def _http_probe_fyers_profile(client_id: str, token: str) -> None:
    """Optional raw HTTP check — only when FYERS_DEBUG_HTTP=1 (saves log noise)."""
    if os.getenv("FYERS_DEBUG_HTTP", "").strip() not in ("1", "true", "yes"):
        return
    try:
        import requests

        url = "https://api-t1.fyers.in/api/v3/profile"
        r = requests.get(
            url,
            headers={
                "Authorization": f"{client_id}:{token}",
                "Content-Type": "application/json",
                "version": "3",
            },
            timeout=25,
        )
        prefix = (r.text or "")[:280].replace("\n", " ")
        logger.debug("Raw HTTP GET /api/v3/profile: status=%s body_prefix=%r", r.status_code, prefix)
    except Exception as ex:
        logger.debug("Raw HTTP probe failed: %s", ex)


# Configure logging
from .utils import setup_logging
logger = setup_logging("pipeline_service.src")

class ConnectionManager:
    _lock = threading.Lock()
    """
    Manages connections to Fyers API, including authentication and session persistence.
    """
    def __init__(self, config_path: str = None):
        self._project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        # Parent of fyers_data_pipeline (monorepo root on host). In the pipeline *image*,
        # project_root is /app and dirname(/app) is / — so NEVER use dirname(project_root)
        # alone to find stock_scanner_sovereign; that resolves to /stock_scanner_sovereign (wrong).
        self._repo_root = os.path.abspath(os.path.join(self._project_root, ".."))
        # Default: pipeline config/.env (often absent locally)
        load_dotenv(config_path or os.path.join(self._project_root, "config", ".env"))
        # Sovereign credentials: two valid layouts (must try both):
        # - Docker pipeline: /app/stock_scanner_sovereign/.env (sibling mount under same parent as /app/src)
        # - Host monorepo:   <repo>/stock_scanner_sovereign/.env (sibling of fyers_data_pipeline/)
        sovereign_env_candidates = (
            os.path.join(self._project_root, "stock_scanner_sovereign", ".env"),
            os.path.join(self._repo_root, "stock_scanner_sovereign", ".env"),
        )
        root_env = os.path.join(self._repo_root, ".env")
        for extra in sovereign_env_candidates:
            if os.path.isfile(extra):
                # override=True: bind-mounted .env on the host must win over env_file snapshot
                # from `docker compose` (injected once at container create — stale after you edit .env).
                load_dotenv(extra, override=True)
                logger.debug("Loaded sovereign .env from %s", extra)
        if os.path.isfile(root_env):
            load_dotenv(root_env, override=True)
        self.client_id = _strip_env_scalar(os.getenv("FYERS_CLIENT_ID"))
        self.secret_key = os.getenv("FYERS_SECRET_KEY")
        self.redirect_url = os.getenv("FYERS_REDIRECT_URL")
        self.access_token_path = os.getenv("FYERS_ACCESS_TOKEN_PATH", "access_token.txt")
        self.fyers = None
        self.log_dir = os.path.join(self._project_root, "logs")
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)
        self.request_log_path = os.path.join(self.log_dir, "api_requests.txt")
        self._request_day_marker_path = os.path.join(self.log_dir, "api_requests_ist_day.txt")
        self.max_daily_requests = 80000

    def _refresh_credentials_from_disk(self) -> None:
        """
        Re-load sovereign .env on every connect(). `docker compose` env_file is fixed at
        container start; the mounted `.env` can change on the host — override=True keeps
        FYERS_CLIENT_ID in sync with the file without `docker compose up` again.
        """
        sovereign_env_candidates = (
            os.path.join(self._project_root, "stock_scanner_sovereign", ".env"),
            os.path.join(self._repo_root, "stock_scanner_sovereign", ".env"),
        )
        root_env = os.path.join(self._repo_root, ".env")
        for extra in sovereign_env_candidates:
            if os.path.isfile(extra):
                load_dotenv(extra, override=True)
        if os.path.isfile(root_env):
            load_dotenv(root_env, override=True)
        self.client_id = _strip_env_scalar(os.getenv("FYERS_CLIENT_ID"))

    def _load_access_token(self):
        """
        Resolve token file in a stable order. Local dev often has TWO files:
        `stock_scanner_sovereign/access_token.txt` (from manual_token.py) and
        `fyers_data_pipeline/access_token.txt` (cwd); we must prefer the sovereign file.
        """
        candidates: list[tuple[str, str]] = []
        env_path = os.getenv("FYERS_ACCESS_TOKEN_PATH")
        if env_path:
            candidates.append(("ENV", os.path.expanduser(env_path)))
        candidates.append(("DOCKER", "/app/stock_scanner_sovereign/access_token.txt"))
        candidates.append(
            (
                "SOVEREIGN_SIBLING",
                os.path.join(self._project_root, "stock_scanner_sovereign", "access_token.txt"),
            )
        )
        candidates.append(
            ("SOVEREIGN_REPO", os.path.join(self._repo_root, "stock_scanner_sovereign", "access_token.txt"))
        )
        candidates.append(("PIPELINE", os.path.join(self._project_root, "access_token.txt")))
        rel = self.access_token_path
        if rel:
            if os.path.isabs(rel):
                candidates.append(("ABS", rel))
            else:
                candidates.append(("CWD", os.path.join(os.getcwd(), rel)))

        seen: set[str] = set()
        for label, path in candidates:
            ap = os.path.abspath(path)
            if ap in seen:
                continue
            seen.add(ap)
            try:
                if not os.path.isfile(ap):
                    continue
                with open(ap, encoding="utf-8") as f:
                    token = _normalize_access_token(f.read())
                if token:
                    logger.debug("Loaded token from %s: %s", label, ap)
                    return token
            except OSError:
                continue
        return None

    def _rollover_api_request_count_if_new_ist_day(self) -> None:
        """Reset api_requests.txt when the IST calendar day changes (counter file had no date before)."""
        try:
            today = _ist_calendar_date_str()
            prev = ""
            if os.path.isfile(self._request_day_marker_path):
                with open(self._request_day_marker_path, encoding="utf-8") as f:
                    prev = f.read().strip()
            if prev == today:
                return
            with open(self._request_day_marker_path, "w", encoding="utf-8") as f:
                f.write(today + "\n")
            with open(self.request_log_path, "w", encoding="utf-8") as f:
                f.write("0")
            logger.info("API request counter reset for IST day %s (was %r)", today, prev or "unset")
        except OSError as ex:
            logger.debug("API request day rollover skipped: %s", ex)

    def _increment_request_count(self):
        """Persistent counter for API requests (Daily approx)."""
        with self._lock:
            self._rollover_api_request_count_if_new_ist_day()
            count = 0
            if os.path.exists(self.request_log_path):
                with open(self.request_log_path, 'r') as f:
                    try:
                        count = int(f.read().strip())
                    except: count = 0
            
            count += 1
            with open(self.request_log_path, 'w') as f:
                f.write(str(count))
            return count

    def get_request_count(self):
        """Returns the current recorded request count."""
        self._rollover_api_request_count_if_new_ist_day()
        if not os.path.exists(self.request_log_path):
            return 0
        with open(self.request_log_path, 'r') as f:
            try:
                return int(f.read().strip())
            except: return 0

    def connect(self):
        """Initializes the Fyers model with a valid access token."""
        self._refresh_credentials_from_disk()
        access_token = self._load_access_token()
        if not access_token:
            logger.error("Access token not found. Please run authentication script.")
            return False
        if not self.client_id:
            logger.error(
                "FYERS_CLIENT_ID is not set. Add it to stock_scanner_sovereign/.env or "
                "fyers_data_pipeline/config/.env (same App ID as your access token)."
            )
            return False

        try:
            logger.debug(
                "Fyers connect: client_id=%s token_len=%s",
                self.client_id,
                len(access_token) if access_token else 0,
            )
            jwt = _fyers_jwt_inspect(access_token)
            if jwt.get("parse_error"):
                logger.debug("JWT inspect: %s", jwt["parse_error"])
            else:
                logger.debug("JWT keys=%s", jwt.get("payload_keys") or [])
                if jwt.get("exp") is not None:
                    exp_dt = datetime.fromtimestamp(jwt["exp"], tz=timezone.utc)
                    logger.debug(
                        "JWT exp=%s UTC expired=%s",
                        exp_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        jwt.get("expired"),
                    )
                if jwt.get("expired"):
                    logger.error(
                        "Access token JWT is expired (exp in the past). Run "
                        "stock_scanner_sovereign/manual_token.py and overwrite access_token.txt."
                    )
                    return False
                if jwt.get("exp") is not None:
                    rem = float(jwt["exp"]) - datetime.now(timezone.utc).timestamp()
                    if 0 < rem < 7200:
                        logger.warning(
                            "Access token expires in ~%.0f minutes — refresh before long backfills.",
                            rem / 60.0,
                        )
            jwt_app = jwt.get("app_id")
            if jwt_app and self.client_id != jwt_app:
                logger.error(
                    "FYERS_CLIENT_ID (%r) does not match app id inside the token (%r). "
                    "Use the same My API app id in .env as the one used to generate this token.",
                    self.client_id,
                    jwt_app,
                )
                return False
            if jwt_app:
                logger.debug("JWT app id claim matches FYERS_CLIENT_ID")
            elif not jwt.get("parse_error"):
                logger.debug("No App ID-shaped claim in JWT; using FYERS_CLIENT_ID from .env")

            # Fyers SDK defaults to cwd for logs; exec with -w …/stock_scanner_sovereign + :ro mount breaks.
            self.fyers = fyersModel.FyersModel(
                client_id=self.client_id,
                token=access_token,
                log_path=self.log_dir,
            )
            # Verify connection with a simple profile call
            # 30-YEAR ENGINEER FIX: Fyers V3 sometimes returns -99 for get_profile while /history works.
            # We relax this check to allow the pipeline to proceed if history capability is confirmed.
            profile = self.fyers.get_profile()
            if profile.get('s') == 'ok' or profile.get('code') == 200:
                logger.info("Fyers connected.")
                return True
            else:
                logger.debug("get_profile code=%s; trying history fallback", profile.get("code"))
                t = datetime.now().date()
                t0 = (t - timedelta(days=5)).strftime("%Y-%m-%d")
                t1 = t.strftime("%Y-%m-%d")
                # Query-string APIs often expect string flags (matches Fyers docs examples).
                test_hist = self.fyers.history({
                    "symbol": "NSE:NIFTY50-INDEX",
                    "resolution": "1D",
                    "date_format": "1",
                    "range_from": t0,
                    "range_to": t1,
                    "cont_flag": "1",
                })
                if test_hist.get('s') == 'ok':
                    logger.info("Fyers connected (history check).")
                    return True

                code = profile.get("code") if profile.get("code") is not None else test_hist.get("code")
                msg = profile.get("message") or test_hist.get("message", "Unknown Error")
                logger.error("Fyers connect failed: %s (code %s). Refresh token / check FYERS_CLIENT_ID.", msg, code)
                logger.debug("get_profile=%s history=%s", profile, test_hist)
                if code == -8:
                    logger.error("Hint: token rejected (-8); refresh stock_scanner_sovereign/access_token.txt")
                elif code == -99:
                    logger.error(
                        "Hint: -99 usually means expired/revoked token or wrong app id — run manual_token.py"
                    )
                    logger.debug(
                        "FYERS_CLIENT_ID=%r len=%s token_len=%s",
                        self.client_id,
                        len(self.client_id),
                        len(access_token),
                    )
                    _http_probe_fyers_profile(self.client_id, access_token)
                return False
        except Exception as e:
            logger.exception(f"Exception during connection: {e}")
            return False

    def get_history(self, symbol: str, range_from: str, range_to: str, resolution: str = "1D"):
        """Wrapper for historical data fetching."""
        if not self.fyers:
            raise ConnectionError("Not connected to Fyers API")
        
        if self.get_request_count() >= self.max_daily_requests:
            logger.error("API Request Limit Reached (Safeguard). Stopping.")
            return {"s": "error", "message": "Safeguard: Daily Request Limit Reached", "code": -100}

        data = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": "1",
            "range_from": range_from,
            "range_to": range_to,
            "cont_flag": "1",
        }
        self._increment_request_count()
        return self.fyers.history(data=data)
