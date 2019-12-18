from celery import Celery
import os, sys
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))


import config


SERVER_URL = os.environ.get("SERVER_URL", "http://127.0.0.1:8000")
celery = Celery("periodic_tasks",
                broker=config.BROKER_URL,
                backend=config.CELERY_RESULT_BACKEND)

celery.conf.beat_schedule = {
    'periodic-health-check': {
        'task': 'periodic_tasks.health_check',
        'schedule': 20.0
    }
}