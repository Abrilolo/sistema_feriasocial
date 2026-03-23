import urllib.request
import json

url = "http://127.0.0.1:8000/public/generate-qr"
data = json.dumps({"matricula": "A01234567", "email": "test@tec.mx"}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status: {response.status}")
        print(f"Body: {response.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print(f"Error Detail: {e.read().decode()}")
except Exception as e:
    print(f"Exception: {e}")
