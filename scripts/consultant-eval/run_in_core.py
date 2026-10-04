"""One-off evaluation runner executed inside the Core API container.

Reads the bundle JSON from stdin, calls YandexGPT with the same fixed
parameters as app/adapters/yandex_completion.py and prints only model texts.
The API key is read from the mounted file and never printed.
"""

import json
import os
import sys
import time
import urllib.request

URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

bundle = json.load(sys.stdin)
folder = os.environ["YANDEX_PRODUCTION_FOLDER_ID"]
model = os.environ.get("YANDEX_PRODUCTION_MODEL", "yandexgpt/latest")
with open(os.environ["YANDEX_PRODUCTION_API_KEY_PATH"], encoding="utf-8") as handle:
    key = handle.read().strip()

results = []
for case in bundle["cases"]:
    body = json.dumps({
        "modelUri": f"gpt://{folder}/{model}",
        "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": "600"},
        "messages": [{"role": "system", "text": bundle["system"]}, *case["messages"]],
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(URL, data=body, method="POST")
    request.add_header("Authorization", f"Api-Key {key}")
    request.add_header("Content-Type", "application/json")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = data["result"]["alternatives"][0]["message"]["text"]
        tokens = data["result"].get("usage", {})
        results.append({"id": case["id"], "text": text, "ms": int((time.monotonic() - started) * 1000), "usage": tokens})
    except Exception as error:  # noqa: BLE001 -- report the class only
        results.append({"id": case["id"], "error": type(error).__name__, "ms": int((time.monotonic() - started) * 1000)})
    time.sleep(0.5)

json.dump(results, sys.stdout, ensure_ascii=False)
