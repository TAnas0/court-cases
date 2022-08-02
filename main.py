import requests


session = requests.Session()

# Agree to the terms and conditions
x = session.get(
    url="https://eapps.courts.state.va.us/ocis-rest/api/public/termsAndCondAccepted",
    headers={
        "Content-Type": "application/json;charset=UTF-8",
    },
)

url = "https://eapps.courts.state.va.us/ocis-rest/api/public/search"
headers = {
    "Accept": "application/json, text/plain, */*",
}
data = {
    "courtLevels": [],
    "divisions": [
        "Criminal/Traffic"
    ],
    "selectedCourts": [],
    "searchString": [
        "07/01/2022"
    ],
    "searchBy": "HD"
}
res = session.post(url, headers=headers, json=data)
print(res)

