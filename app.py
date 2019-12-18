from tasks import config
from flask import Flask, request, jsonify

from celery import Celery
# from celery.result import AsyncResult

celery = Celery("flask_tasks",
                broker=config.BROKER_URL,
                backend=config.CELERY_RESULT_BACKEND)

app = Flask(__name__)


@app.route('/create', methods=['POST'])
def create():
    try:
        # if multiple image --> need to check
        if not (isinstance(request.json['image'], str) or isinstance(request.json['ports'], list) \
                or isinstance(request.json['envs'], list) or isinstance(request.json['project_name'], str)):
            raise ValueError
        payload = {
            'project_name': request.json['project_name'],
            'images': [request.json['image']],
            'ports': {request.json['image']: request.json['ports']},
            'envs': {request.json['image']: request.json['envs']}
        }
    except (KeyError, ValueError) as e:
        ret = {
            'status': 'failed',
            'id': None,
            'err': '''Unavailable Keys or Values. JSON format must be like this.
            { 
                project_name: string,
                image: string,
                ports: list, 
                envs: list 
            }'''
        }
        return ret
    task = celery.send_task('tasks.create', kwargs=payload)
    ret = {
        'status': 'proceeded',
        'id': task.id
    }
    if not task.state == 'PENDING':
        ret['status'] = 'failed'
    return ret


@app.route('/delete', methods=['POST'])
def delete():
    try:
        payload = {
            'project_name': request.json['project_name']
        }
    except KeyError:
        ret = {
            'status': 'failed',
            'id': None,
            'err': '''Unavailable Keys or Values. JSON format must be like this.
                { 
                    project_name: string, 
                } '''
        }
        return ret

    task = celery.send_task('tasks.delete', kwargs=payload)
    ret = {
        'status': 'proceeded',
        # 'id': task.id
    }

    return ret


@app.route('/update', methods=['POST'])
def update():
    try:
        payload = {
            'project_name': request.json['project_name'],
            'images': [request.json['image']],
            'ports': {request.json['image']: request.json['ports']} if request.json.get('ports') else {},
            'envs': {request.json['image']: request.json['envs']} if request.json.get('envs') else {},
        }
    except (KeyError, ValueError) as e:
        ret = {
            'status': 'failed',
            'id': None,
            'err': '''Unavailable Keys or Values. JSON format must be like this.
                { 
                    project_name: string, 
                } '''
        }
        return ret

    task = celery.send_task('tasks.update', kwargs=payload)
    ret = {
        'status': 'proceeded',
        'id': task.id
    }
    if not task.state == 'PENDING':
        ret['status'] = 'failed'
    return ret


@app.route('/')
def index():
    return "index"


@app.route('/check')
def check():
    res = celery.AsyncResult(request.args.get('id'))
    ret = {
        'state': res.state,
        'result': res.result
    }
    if res.state == 'failed':
        ret['err_info']: res.err_info
    # print(res.state, res.result)
    # add request to web server -- good to separate to celery task

    return ret


@app.route('/test', methods=['PUT'])
def test():
    data = request.json
    print(data)
    return 'test'


if __name__ == '__main__':
    app.run(debug=True,
            port=8000)
