from os import environ

REDIS_HOST = "0.0.0.0"
REDIS_PORT = 6379
BROKER_URL = environ.get('REDIS_URL', f"redis://{REDIS_HOST}:{str(REDIS_PORT)}/0")
CELERY_RESULT_BACKEND = BROKER_URL
