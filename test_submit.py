import requests
import uuid

url = "http://127.0.0.1:5000/submit"
new_nin = str(uuid.uuid4().int)[:11]
data = {
    "surname": "Doe", # restored
    "firstname": "John",
    "phone": "08012345678",
    "age": "25",
    "address": "123 Test Street, Lagos",
    "nin": new_nin,
    "nok": "Jane Doe",
    "previous_work": ["Job 1", "Job 2"]
}

files = {
    "photo": ("dummy_photo.jpg", open("dummy_photo.jpg", "rb"), "image/jpeg")
}

response = requests.post(url, data=data, files=files, allow_redirects=False)

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("Submission successful!")
elif response.status_code == 302:
    print(f"Redirected to: {response.headers.get('Location')}")
else:
    print(f"Error Code: {response.status_code}")
    print(f"Error text: {response.text}")
