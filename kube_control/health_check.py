import os, sys
import hashlib
import control
import requests

INGRESS_HOST = os.environ.get("INGRESS_HOST", "http://34.97.132.189")


def http_health_check(project_name: str, namespace: str = "default"):
    resp = control.describe_ingress(control.MAIN_INGRESS)
    backends = resp.spec.rules[0]
    # print(backends.http.paths)
    ret = dict()
    session = requests.Session()
    for path in backends.http.paths:
        get_path = path.path[:-4] if path.path[-4:] == '(.*)' else path.path
        http_response = session.get(INGRESS_HOST + get_path)
        # print(http_response.status_code)
        if get_path[1:-1] == hashlib.sha256(project_name.encode()).hexdigest()[:16]:
            ret['service'] = get_path[1:-1] if not get_path == path.path else get_path
            ret['status'] = http_response.status_code
    return ret


def ingress_health_check():
    resp = control.describe_ingress(control.MAIN_INGRESS)
    backends = resp.spec.rules[0]
    # print(backends.http.paths)
    ret = dict()
    idx = 0
    session = requests.Session()
    for path in backends.http.paths:
        get_path = path.path[:-4] if path.path[-4:] == '(.*)' else path.path
        http_response = session.get(INGRESS_HOST + get_path)
        # print(http_response.status_code)
        temp = {
            'service': get_path[1:-1] if not get_path == path.path else get_path[1:],
            'status': http_response.status_code
        }
        ret[str(idx)] = temp
        idx += 1
    return ret


if __name__ == '__main__':
    pass
    # http_health_check('test-project')
    print(ingress_health_check())