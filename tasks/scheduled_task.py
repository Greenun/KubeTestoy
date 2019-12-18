from celery import Celery
import os, sys
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
print(sys.path)
import config
from kube_control import health_check
import requests


SERVER_URL = os.environ.get("SERVER_URL", "http://127.0.0.1:8000")
celery = Celery("periodic_tasks",
                broker=config.BROKER_URL,
                backend=config.CELERY_RESULT_BACKEND)


@celery.task(name='periodic_tasks.health_check')
def periodic_health_check():
    resp = health_check.ingress_health_check()
    unconditionals = dict()
    idx = 0
    for i in resp:
        if not resp.get('status') == 200:
            unconditionals[str(idx)] = i
            idx += 1
    with requests.Session() as s:
        # reqeust to web server
        pass


celery.conf.beat_schedule = {
    'periodic-health-check': {
        'task': 'periodic_tasks.health_check',
        'schedule': 100.0
    }
}