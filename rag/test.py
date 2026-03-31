import requests

res = requests.post(
     "http://127.0.0.1:11434/api/generate",
    json={
        "model": "dhenu2-farming:latest",
        "prompt": "What is best time for growing paddy?",
        "stream": False
    }
)

print(res.json())