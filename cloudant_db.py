import requests
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

CLOUDANT_URL = os.getenv('CLOUDANT_URL')
CLOUDANT_API_KEY = os.getenv('CLOUDANT_API_KEY')
DB_NAME = 'finance_transactions'

def get_headers():
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {get_token()}'
    }

def get_token():
    response = requests.post(
        'https://iam.cloud.ibm.com/identity/token',
        data={
            'grant_type': 'urn:ibm:params:oauth:grant-type:apikey',
            'apikey': CLOUDANT_API_KEY
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    return response.json().get('access_token')

def ensure_db_exists():
    headers = get_headers()
    url = f"{CLOUDANT_URL}/{DB_NAME}"
    r = requests.get(url, headers=headers)
    if r.status_code == 404:
        requests.put(url, headers=headers)

def add_transaction(data):
    ensure_db_exists()
    headers = get_headers()
    doc = {
        '_id': str(uuid.uuid4()),
        'amount': float(data.get('amount', 0)),
        'category': data.get('category', 'Other'),
        'description': data.get('description', ''),
        'date': data.get('date', datetime.now().strftime('%Y-%m-%d'))
    }
    url = f"{CLOUDANT_URL}/{DB_NAME}/{doc['_id']}"
    r = requests.put(url, headers=headers, data=json.dumps(doc))
    return {'success': r.status_code in [200, 201], 'id': doc['_id']}

def get_transactions():
    ensure_db_exists()
    headers = get_headers()
    url = f"{CLOUDANT_URL}/{DB_NAME}/_all_docs?include_docs=true"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return []
    rows = r.json().get('rows', [])
    return [row['doc'] for row in rows if not row['id'].startswith('_')]