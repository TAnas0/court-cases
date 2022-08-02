import requests

def accept_terms_and_conditions():
    session = requests.Session()
    session.get(
        url="https://eapps.courts.state.va.us/ocis-rest/api/public/termsAndCondAccepted",
        headers={
            "Content-Type": "application/json;charset=UTF-8",
        },
    )

    return session