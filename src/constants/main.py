import json
import os

dir_path = os.path.dirname(os.path.realpath(__file__))
with open(f"{dir_path}/courts.json") as f:
    courts = json.load(f)

# FINAL_COLUMNS = [
#     "Case Number",
#     "Filed Date",
#     "Locality",
#     "Name",
#     "Status",
#     "Defense Attorney",
#     "Address",
#     "AKA1",
#     "AKA2",
#     "Gender",
#     "Race",
#     "DOB",
#     "Charge",
#     "Code Section",
#     "Case Type",
#     "Class",
#     "Offense Date",
#     "Arrest Date",
#     "Complainant",
#     "Amended Charge",
#     "Amended Code",
#     "Amended Case Type",
#     "Date,Time,Result,Hearing Type,Courtroom,Plea,Continuance Code,,Final Disposition",
#     "Sentence Time",
#     "Sentence Suspended Time",
#     "Probation Type",
#     "Probation Time",
#     "Probation Starts",
#     "Operator License Suspension Time",
#     "Restriction Effective Date",
#     "Operator License Restriction Codes",
#     "Fine",
#     "Costs",
#     "Fine/Costs Due",
#     "Fine/Costs Paid",
#     "Fine/Costs Paid Date",
#     "VASAP",
#     "searchDate",
#     "Court",
# ]
