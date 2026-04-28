import os

from nemos.settings import *  # noqa: F401,F403


MICROSERVICE_REGISTRY = {
    "user_service": os.environ.get("USER_SERVICE_URL", "http://127.0.0.1:8001").strip(),
    "ngo_service": os.environ.get("NGO_SERVICE_URL", "http://127.0.0.1:8002").strip(),
    "registration_service": os.environ.get(
        "REGISTRATION_SERVICE_URL",
        "http://127.0.0.1:8003",
    ).strip(),
}
