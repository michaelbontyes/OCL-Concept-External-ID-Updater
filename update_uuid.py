# This script updates the UUIDs of concepts in an OCL source.
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
COUNTERS = {
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
    fieldnames = ['Timestamp', 'Status', 'Valid External ID', 'Concept ID', 'Name', 'URL', 'Current External ID', 'New External ID', 'Original Response', 'Update Payload']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()

    def generate_new_uuid():
        """Generate a new UUID (16 characters)."""
        return str(uuid.uuid4())[:36]

# Check if the external ID is a valid 36-character UUID.
    def is_valid_36_char_uuid(ext_id):
        if ext_id is None or ext_id == '':
            COUNTERS['updated_empty'] += 1
            return False
        if ext_id.startswith("MSF-"):
            COUNTERS['updated_msf'] += 1
            return False
        if len(ext_id) != 36:
            COUNTERS['updated_invalid'] += 1
            return False
        return True

    # Update the external ID of a concept.
    def update_concept_external_id(url, concept_id, concept_name, concept_names, current_ext_id, original_response):
        valid_uuid = is_valid_36_char_uuid(current_ext_id)
        changed_uuid = False
        if valid_uuid:
            COUNTERS['skipped'] += 1
        elif not DRY_RUN and not valid_uuid:
            new_external_id = generate_new_uuid()
            data = {
                "id": concept_id,
                "external_id": new_external_id,
                "names": concept_names
            }
            resp = requests.put(url, headers=HEADERS, data=json.dumps(data), timeout=10)
            resp.raise_for_status()
            changed_uuid = True
            valid_uuid = True
        timestamp = datetime.now().isoformat()
        writer.writerow({
            'Timestamp': timestamp,
            'Status': 'New ID' if not DRY_RUN and changed_uuid else 'No Change',
            'Valid External ID': 'Yes' if valid_uuid else 'No',
            'Concept ID': concept_id,
            'Name': concept_name,
            'URL': url,
            'Current External ID': current_ext_id,
            'New External ID': new_external_id if not DRY_RUN and changed_uuid else '{}',
            'Original Response': original_response,
            'Update Payload': json.dumps(data) if not DRY_RUN and changed_uuid else '{}'
        })

    # Get all concepts with pagination.
    def get_all_concepts(url):
        all_concepts = []
        while url:
            resp = requests.get(url, headers=HEADERS, timeout=10)
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
        response = requests.get(concept_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        concept_details = response.json()
        concept_name = concept['display_name']
        concept_names = concept_details.get('names', [])
        update_concept_external_id(
            concept_url, concept_id, concept_name, concept_names, external_id, concept_details
        )

# Print the results
if DRY_RUN:
    print("DRY RUN MODE: No changes will be made to the OCL source.")
print(f"Number of concepts updated because they were empty: {COUNTERS['updated_empty']}")
print(f"Number of concepts updated because they started with 'MSF-': {COUNTERS['updated_msf']}")
print(f"Number of concepts updated because ID was <36 characters: {COUNTERS['updated_invalid']}")
print(f"Number of concepts skipped: {COUNTERS['skipped']}")
print()
