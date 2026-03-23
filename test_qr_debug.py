import requests

url = "http://127.0.0.1:8000/public/generate-qr"
payload = {
    "matricula": "A01234567",
    "email": "test@tec.mx"
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
