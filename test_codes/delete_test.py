import requests

if __name__ == '__main__':
    payload = {
        'project_name': 'test-app2'
    }
    with requests.Session() as s:
        resp = s.post('http://34.97.171.66/delete', json=payload)
        print(resp.text)




