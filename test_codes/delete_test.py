import requests

if __name__ == '__main__':
    payload = {
        'project_name': 'my-test'
    }
    with requests.Session() as s:
        resp = s.post('http://127.0.0.1:8000/delete', json=payload)
        print(resp.text)




