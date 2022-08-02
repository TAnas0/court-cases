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

date_hearings = []
if res.status_code == 200:

    res = res.json()["context"]["entity"]["payload"]
    search_results = res["searchResults"]
    for result in search_results:
        print(result)
        data = {
            "Case Number": result["formattedCaseNumber"],
            # Filed Date ,
            # Locality ,
            # Name ,
            # Status ,
            # Defense Attorney ,
            # Address ,
            # AKA1 ,
            # AKA2 ,
            # Gender ,
            # Race ,
            # DOB ,
            # Charge ,
            "Code Section": result["codeSection"],
            "Case Type": result["caseType"],  # To format: Misdemeanor, felony, show cause...
            # Class ,
            "Offense Date": result["offenseDate"],
            # Arrest Date ,
            "Complainant": result.get("complainantName", None),
            # Amended Charge ,
            # Amended Code ,
            # Amended Case Type ,
            "Date": result["hearingDate"].split(",")[0],
            "Time": result["hearingDate"].split(",")[1].strip(),
            "Result": "",
            # Hearing Type,
            # Courtroom,
            # Plea,
            # Continuance Code,
            # Final Disposition ,
            # Sentence Time ,
            # Sentence Suspended Time ,
            # Probation Type ,
            # Probation Time ,
            # Probation Starts ,
            # Operator License Suspension Time ,
            # Restriction Effective Date ,
            # Operator License Restriction Codes ,
            # Fine ,
            # Costs ,
            # Fine/Costs Due ,
            # Fine/Costs Paid ,
            # Fine/Costs Paid Date ,
            # VASAP ,
            # searchDate,
            # Court
        }
        date_hearings.append(data)
    last_page = res["hasMoreRecords"] != "Y"
    # if last_page:
    #     break

print(date_hearings)
