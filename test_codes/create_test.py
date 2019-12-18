import requests

if __name__ == "__main__":
    s = requests.Session()
    payload = {
        'project_name': 'my-test',
        'image': 'test-app:latest',#'web-test-2:1.0',
        'ports': [8080],
        'envs': None
    }
    resp = s.post('http://127.0.0.1:8000/create', json=payload)
    print(resp.json())
    s.close()

