from time import perf_counter

from django.conf import settings
from django.core.cache import cache


NGO_LIST_CACHE_KEY = "nemos:ngo:list:active"
PARTICIPANT_SUMMARY_CACHE_KEY = "nemos:registration:monitor_summary"


def cache_timeout():
    return getattr(settings, "CACHE_TIMEOUT_SECONDS", 300)


def clear_ngo_cache():
    cache.delete(NGO_LIST_CACHE_KEY)


def clear_participant_cache():
    cache.delete(PARTICIPANT_SUMMARY_CACHE_KEY)


def measure_cached_call(raw_loader, cached_loader):
    raw_start = perf_counter()
    raw_loader()
    raw_ms = round((perf_counter() - raw_start) * 1000, 2)

    cache.delete(getattr(cached_loader, "cache_key", ""))
    cold_start = perf_counter()
    cached_loader()
    cold_ms = round((perf_counter() - cold_start) * 1000, 2)

    warm_start = perf_counter()
    cached_loader()
    warm_ms = round((perf_counter() - warm_start) * 1000, 2)

    return {
        "without_cache_ms": raw_ms,
        "first_cached_ms": cold_ms,
        "second_cached_ms": warm_ms,
    }
