import httpx
import json

api_key = "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"
base_url = "https://integrate.api.nvidia.com/v1"
model = "meta/llama-3.1-70b-instruct"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

payload = {
    "model": model,
    "messages": [{"role": "user", "content": "Hello, this is a test. Reply with 'OK'."}],
    "temperature": 0.2,
    "max_tokens": 64,
}

print(f"[*] Testing NVIDIA API with model {model}...")
try:
    response = httpx.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=30.0)
    print(f"[*] Status Code: {response.status_code}")
    if response.status_code == 200:
        print("[!] SUCCESS:")
        print(json.dumps(response.json(), indent=2))
    else:
        print("[X] FAILURE:")
        print(response.text)
except Exception as e:
    print(f"[X] EXCEPTION: {e}")
