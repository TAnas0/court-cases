# Get a case's details
def get_case_details(session, fips, court_level, division_type, case_number):
    # print(f"Getting details for {fips}, {court_level}, {division_type}, {case_number}")
    url = "https://eapps.courts.state.va.us/ocis-rest/api/public/getCaseDetails"
    data = {
        "qualifiedFips": fips,
        "courtLevel": court_level,
        "divisionType": division_type,
        "caseNumber": case_number,
    }
    res = session.post(url, json=data)
    if res.status_code == 200:
        result = res.json()
        if result["context"]["entity"]["status"] == "SUCCESS":
            return result["context"]["entity"]["payload"]
        else:
            raise Exception()
    else:
        raise Exception()
