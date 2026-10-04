"""Value-silent check of one-owner Telegram routing in Hermes config."""

import json
from pathlib import Path
import yaml

config = yaml.safe_load(Path('/opt/data/config.yaml').read_text()) or {}
gateway = config.get('gateway') or {}
routes = gateway.get('profile_routes') or {}
assignments = [line.partition('=')[2].strip().strip('"\'')
               for line in Path('/opt/data/.env').read_text().splitlines()
               if line.startswith('TELEGRAM_ALLOWED_USERS=')]
allowed = ([item.strip() for item in assignments[-1].split(',') if item.strip()]
           if assignments else [])

print(json.dumps({
    'profile_routes_type': type(routes).__name__,
    'profile_route_count': len(routes),
    'allowed_user_count': len(allowed),
}, sort_keys=True))
