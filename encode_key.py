import base64

with open("utils/serviceAccountKey.json", "rb") as f:
    encoded = base64.b64encode(f.read()).decode("utf-8")

print(encoded)
