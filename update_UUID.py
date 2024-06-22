"""
This script updates the UUIDs of concepts in the OCL source.
"""

import argparse
import uuid
import json
import csv
from datetime import datetime
import requests

# Parse command-line arguments
parser = argparse.ArgumentParser(description="OCL Concept External ID Updater")
parser.add_argument("--dry-run", action="store_true", help="Enable dry run mode")
args = parser.parse_args()

# Load configuration from config.json
with open('config.json', encoding='utf-8') as config_file:
    config = json.load(config_file)

OCL_API_URL = config['OCL_API_URL']
SOURCE_ID = config['SOURCE_ID']
OCL_TOKEN = config['OCL_TOKEN']
ORG_ID = config['ORG_ID']

# Dry run option
DRY_RUN = args.dry_run

# Counters for updated and skipped concepts
counters = {
    'updated_empty': 0,
    'updated_msf': 0,
    'updated_invalid': 0,
    'skipped': 0
}

# Headers for the API request
HEADERS = {
    "Authorization": f"Token {OCL_TOKEN}",
    "Content-Type": "application/json"
}

# Prepare CSV file for dry run mode
CSV_FILENAME = 'updated_concepts_dry_run.csv' if DRY_RUN else 'updated_concepts.csv'

with open(CSV_FILENAME, mode='w', newline='', encoding='utf-8') as csv_file:
    fieldnames = ['Timestamp', 'ID', 'Name', 'URL', 'Current External ID', 'New External ID']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()

    def generate_new_uuid():
        """Generate a new UUID (16 characters)."""
        return str(uuid.uuid4())[:36]

    def is_valid_36_char_uuid(ext_id, counters):
        """Check if the external ID is a valid 36-character UUID."""
        if ext_id is None or ext_id == '':
            counters['updated_empty'] += 1
            return False
        if ext_id.startswith("MSF-"):
            counters['updated_msf'] += 1
            return False
        if len(ext_id) != 36:
            counters['updated_invalid'] += 1
            return False
        return True

    def update_concept_external_id(url, con_id, new_ext_id, con_names, current_ext_id):
        """Update the external ID of a concept."""
        data = {
            "external_id": new_ext_id
        }
        if not DRY_RUN:
            resp = requests.put(url, headers=HEADERS, data=json.dumps(data))
            resp.raise_for_status()
        timestamp = datetime.now().isoformat()
        writer.writerow({
            'Timestamp': timestamp,
            'ID': con_id,
            'Name': ", ".join([name['name'] for name in con_names]),
            'URL': url,
            'Current External ID': current_ext_id,
            'New External ID': new_ext_id
        })

    def get_all_concepts(url):
        """Get all concepts with pagination."""
        all_concepts = []
        while url:
            resp = requests.get(url, headers=HEADERS)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                all_concepts.extend(data.get('results', []))
                url = data.get('next')
            elif isinstance(data, list):
                all_concepts.extend(data)
                break
            else:
                print("Unexpected response format:", data)
                break
        return all_concepts

    # Get the list of concepts in the source
    concepts_url = f"{OCL_API_URL}/orgs/{ORG_ID}/sources/{SOURCE_ID}/concepts/"
    concepts = get_all_concepts(concepts_url)

    # Iterate over the concepts and update external IDs based on the conditions
    for concept in concepts:
        concept_url = f"{OCL_API_URL}{concept['url']}"
        concept_id = concept['id']
        external_id = concept.get('external_id', '')
        response = requests.get(concept_url, headers=HEADERS)
        response.raise_for_status()
        concept_details = response.json()
        concept_names = concept_details.get('names', [])

        if is_valid_36_char_uuid(external_id, counters):
            counters['skipped'] += 1
        else:
            NEW_EXTERNAL_ID = generate_new_uuid()
            update_concept_external_id(
                concept_url, concept_id, NEW_EXTERNAL_ID, concept_names, external_id
            )

# Print the results
if DRY_RUN:
    print("DRY RUN MODE: No changes will be made to the OCL source.")
print(f"Number of concepts updated because they were empty: {counters['updated_empty']}")
print(f"Number of concepts updated because they started with 'MSF-': {counters['updated_msf']}")
print(f"Number of concepts updated because current ID was less than 36 characters: {counters['updated_invalid']}")
print(f"Number of concepts skipped: {counters['skipped']}")
print()
