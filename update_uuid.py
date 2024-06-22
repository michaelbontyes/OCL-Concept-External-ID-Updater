"""
This script updates the UUIDs of concepts in an OCL source.
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
COUNTERS = {
    'UPDATED_EMPTY': 0,
    'UPDATED_MSF': 0,
    'UPDATED_INVALID': 0,
    'SKIPPED': 0
}

# Headers for the API request
HEADERS = {
    "Authorization": f"Token {OCL_TOKEN}",
    "Content-Type": "application/json"
}

# Prepare CSV file for dry run mode
CSV_FILENAME = 'updated_concepts_dry_run.csv' if DRY_RUN else 'updated_concepts.csv'

with open(CSV_FILENAME, mode='w', newline='', encoding='utf-8') as csv_file:
    fieldnames = [
        'Timestamp', 'Status', 'Valid External ID', 'Concept ID', 'Name', 'URL',
        'Current External ID', 'New External ID', 'Original Response', 'Update Payload'
    ]
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()

    def generate_new_uuid():
        """Generate a new UUID (16 characters)."""
        return str(uuid.uuid4())[:36]

    def is_valid_36_char_uuid(ext_id):
        """Check if the external ID is a valid 36-character UUID."""
        if ext_id is None or ext_id == '':
            COUNTERS['UPDATED_EMPTY'] += 1
            return False
        if ext_id.startswith("MSF-"):
            COUNTERS['UPDATED_MSF'] += 1
            return False
        if len(ext_id) != 36:
            COUNTERS['UPDATED_INVALID'] += 1
            return False
        return True

    def update_concept_external_id(url, concept_details, ext_id):
        """Update the external ID of a concept."""
        if not is_valid_36_char_uuid(ext_id):
            new_ext_id = generate_new_uuid()
            update_payload = json.dumps({"external_id": new_ext_id})
            if not DRY_RUN:
                response_update = requests.put(
                    url, headers=HEADERS, data=update_payload, timeout=10
                )
                response_update.raise_for_status()
            else:
                response_update = None

            # Write to CSV
            writer.writerow({
                'Timestamp': datetime.now().isoformat(),
                'Status': 'Updated',
                'Valid External ID': ext_id,
                'Concept ID': concept_details['id'],
                'Name': concept_details['display_name'],
                'URL': url,
                'Current External ID': ext_id,
                'New External ID': new_ext_id,
                'Original Response': response_update.text if response_update else '',
                'Update Payload': update_payload
            })
        else:
            COUNTERS['SKIPPED'] += 1

    def get_all_concepts(url):
        """Retrieve all concepts from the given URL."""
        all_concepts = []
        while url:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
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
    TOTAL_CONCEPTS = len(concepts)
    PROCESSED_CONCEPTS_COUNT = 0
    
    # Iterate over the concepts and update external IDs based on the conditions
    for concept in concepts:
        concept_url = f"{OCL_API_URL}{concept['url']}"
        response = requests.get(concept_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        concept_info = response.json()
        concept_name = concept['display_name']
        external_id = concept.get('external_id', '')
        update_concept_external_id(concept_url, concept_info, external_id)

        # Update progress
        PROCESSED_CONCEPTS_COUNT += 1
        progress_percentage = (PROCESSED_CONCEPTS_COUNT / TOTAL_CONCEPTS) * 100
        print(
            f"Progress: {PROCESSED_CONCEPTS_COUNT}/{TOTAL_CONCEPTS} concepts verified "
            f"({progress_percentage:.2f}%) - Last concept: {concept_name} (ExtID: {external_id})"
        )

# Print the results
if DRY_RUN:
    print("DRY RUN MODE: No changes will be made to the OCL source.")
print(f"Number of concepts updated because they were empty: {COUNTERS['UPDATED_EMPTY']}")
print(f"Number of concepts updated because they started with 'MSF-': {COUNTERS['UPDATED_MSF']}")
print(f"Number of concepts updated because ID was <36 characters: {COUNTERS['UPDATED_INVALID']}")
print(f"Number of concepts skipped: {COUNTERS['SKIPPED']}")
