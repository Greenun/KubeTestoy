import requests

if __name__ == "__main__":
    s = requests.Session()
    payload = {
        'project_name': 'my-test',
        'image': 'web-test-2:2.0',
        'ports': [8080],
        'envs': [{
            'name': 'WHAT',
            'value': 'GOD'
        }]
    }
    resp = s.post('http://127.0.0.1:8000/update', json=payload)
    print(resp.json())
    s.close()

