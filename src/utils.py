import requests
from constants.main import courts


def accept_terms_and_conditions():
    session = requests.Session()
    session.get(
        url="https://eapps.courts.state.va.us/ocis-rest/api/public/termsAndCondAccepted",
        headers={
            "Content-Type": "application/json;charset=UTF-8",
        },
    )

    return session

def get_court_name_by_fips(fipsCode4):
    return list(filter(lambda d: d["fipsCode4"] == fipsCode4, courts))[0]["courtName"]