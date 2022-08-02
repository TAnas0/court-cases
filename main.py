import requests


url = "https://eapps.courts.state.va.us/ocis-rest/api/public/search"
headers = {}
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
res = requests.post(url, headers=headers, json=data)
print(res)

