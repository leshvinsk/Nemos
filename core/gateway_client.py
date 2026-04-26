import requests
from django.conf import settings


class GatewayError(Exception):
    pass


def gateway_get(path, query_params=None, timeout=10):
    base_url = getattr(settings, "API_GATEWAY_URL", "http://127.0.0.1:8004").rstrip("/")
    url = f"{base_url}/{path.lstrip('/')}"
    try:
        response = requests.get(url, params=query_params or {}, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise GatewayError(str(exc)) from exc
    return response.json()
