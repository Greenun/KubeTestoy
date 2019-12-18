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
    print(request.json)
    payload = {
        'project_name': request.json['project_name'],
        'images': [request.json['image']],
        'ports': {request.json['image']: request.json['ports']},
        'envs': {request.json['image']: request.json['envs']}
    }

    task = celery.send_task('tasks.create', kwargs=payload)

    ret = {
        'status': 'proceed',
        'id': task.id
    }
    # if task.state == 'PENDING':
    #     print('PENDING')
    # print(type(task))
    # res = celery.AsyncResult(task.id)
    # print("res:", type(res))

    return ret


@app.route('/delete')
def delete():
    pass


@app.route('/')
def index():
    return "index"


@app.route('/check')
def check():
    # print(request.args.get('id'))
    res = celery.AsyncResult(request.args.get('id'))

    print(res.state, res.result)
    return {'state': res.state, 'result': res.result}


if __name__ == '__main__':
    app.run(debug=True,
            port=8000)
