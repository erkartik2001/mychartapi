from flask import Flask, request, redirect, jsonify
import requests
import xml.etree.ElementTree as ET
import xmltodict
import json

app = Flask(__name__)

CLIENT_ID = "83b342ad-f838-4582-8418-407a2e4095eb" # Production CLient ID
CLIENT_SECRET = "sIvnMFJPPTZEz/dMpvAfYPJuniDmYC1lusCjXaIkOf1+NuzNinYMrKZUDqR3JPq29UDUSCPv70Oq63D4aXIRwA=="
REDIRECT_URI = "https://localhost:5000/callback"
AUTHORIZATION_URL = 'https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize'
TOKEN_URL = 'https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token'
BASE_API_URL = 'https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/'


@app.route('/')
def home():
    return 'Welcome! Go to /login to start the OAuth flow.'

@app.route('/login')
def login():
    authorization_url = (
        f"{AUTHORIZATION_URL}"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state=dev"
        f"&scope=patient.read patient.search patient/Condition.read patient/MedicationRequest.read patient/AllergyIntolerance.read"
    )
    url = f"{AUTHORIZATION_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=patient.read patient.search patient/Condition.read patient/MedicationRequest.read patient/AllergyIntolerance.read&state=dev"
    return redirect(url)



@app.route('/callback')
def callback():
    authorization_code = request.args.get('code')
    if authorization_code:
        token_response = exchange_code_for_token(authorization_code)
        access_token = token_response.get('access_token')
        if access_token:
            print("*****",access_token)
            patient_id = get_patient_id(access_token)
            if patient_id:
                patient_data = {
                    "Conditions": get_patient_data(f'Condition?patient={patient_id}', access_token),
                    "Medications": get_patient_data(f'MedicationRequest?patient={patient_id}', access_token),
                    "Allergies": get_patient_data(f'AllergyIntolerance?patient={patient_id}', access_token),
                    "Appointments":get_patient_data(f'Appointment?patient={patient_id}',access_token)
                }

               
                return jsonify(patient_data)
            else:
                return 'Patient ID not found in token response. Authorization failed.', 400
    return 'Authorization failed. Please try again.', 400

def exchange_code_for_token(authorization_code):
    data = {
        'grant_type': 'authorization_code',
        'code': authorization_code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID
    }
    response = requests.post(TOKEN_URL, data=data,headers={"Content-Type": "application/x-www-form-urlencoded"})
    response.raise_for_status()
    return response.json()

def get_patient_id(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    response = requests.get(f'{BASE_API_URL}Patient', headers=headers)
    response.raise_for_status()
    
    try:
        root = ET.fromstring(response.content)
        for entry in root.findall("{http://hl7.org/fhir}entry"):
            resource = entry.find("{http://hl7.org/fhir}resource")
            patient = resource.find("{http://hl7.org/fhir}Patient")
            if patient is not None:
                patient_id = patient.find("{http://hl7.org/fhir}id").attrib['value']
                return patient_id
    except ET.ParseError as e:
        print("XML Parse Error:", e)
        return None

    return None

def get_patient_data(endpoint, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    response = requests.get(f'{BASE_API_URL}{endpoint}', headers=headers)
    response.raise_for_status()

    return json.loads(json.dumps(xmltodict.parse(response.content), indent=4))

if __name__ == '__main__':
    app.run(port=5000, debug=False)
    
