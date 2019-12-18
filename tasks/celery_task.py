from celery import Celery, Task
import os, sys
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))


import config
from kube_control import control, health_check
import requests
import time


PERIOD_TIME = 20
MAX_RETRY = 3
URL_PREFIX = "http://34.97.132.189/"
SERVER_URL = os.environ.get("SERVER_URL", "http://127.0.0.1:8000")
celery = Celery("tasks",
                broker=config.BROKER_URL,
                backend=config.CELERY_RESULT_BACKEND)


class CallbackTask(Task):
    def on_success(self, retval, task_id, args, kwargs):
        requests.get(f'{SERVER_URL}/check', params={
            'status': 'success',
            'id': task_id
        })

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        requests.get(f'{SERVER_URL}/check', params={
            'status': 'failed',
            'id': task_id,
            'err_info': einfo
        })


@celery.task(name="tasks.update", base=CallbackTask)
def update_task(*args, **kwargs):
    project_name = kwargs.get('project_name')
    images = kwargs.get('images')

    result = control.update_deployment(project_name, images)

    ret = {
        'status': "success"
    }
    with requests.Session() as s:
        s.put(f"{config.BUILD_SERVER_URL}repo/{project_name}", json=ret)
    return ret


@celery.task(name="tasks.create", base=CallbackTask)
def create_task(*args, **kwargs):
    # project_name: str, images: list, ports: dict = {}, envs: dict = {}
    project_name = kwargs.get('project_name')
    images = kwargs.get('images')
    ports = kwargs.get('ports')
    envs = kwargs.get('envs')

    result = control.create_sequence(project_name, images, ports, envs)
    ret = dict()
    for i in range(MAX_RETRY):
        resp = health_check.http_health_check(project_name)
        if resp.get('status') == 200:
            ret = {
                # 'result': 'success',
                'url': URL_PREFIX + resp.get('service'),
                'status': "success"
            }
            break
        time.sleep(PERIOD_TIME)
    if not ret:
        ret = {
            'status': 'failed'
        }
    with requests.Session() as s:
        # s.put("http://127.0.0.1:8000/test", json=ret)
        s.put(f"{config.BUILD_SERVER_URL}repo/{project_name}", json=ret)
    return resp


@celery.task(name="tasks.delete", base=CallbackTask)
def delete_task(*args, **kwargs):
    # project_name: str
    project_name = kwargs.get('project_name')

    result = control.delete_sequence(project_name)
    ret = {
        'status': result.status.lower()
    }
    with requests.Session() as s:
        s.put(f'{config.BUILD_SERVER_URL}repo/{project_name}', json=ret)
    return ret


@celery.task(name='periodic_tasks.health_check')
def periodic_health_check():
    resp = health_check.ingress_health_check()
    unconditionals = dict()
    idx = 0
    for i in range(len(resp)):
        if resp.get(str(i)).get('status') >= 400:
            temp = {
                'status': resp.get(str(i)).get('status'),
                'url': resp.get(str(i)).get('service')
            }
            unconditionals[str(idx)] = i
            idx += 1

    with requests.Session() as s:
        # reqeust to web server
        s.put('http://127.0.0.1:8000/test', json=unconditionals)
    return
