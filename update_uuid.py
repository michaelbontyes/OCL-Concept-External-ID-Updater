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
COLLECTION_ID = config['COLLECTION_ID']
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
        COUNTERS['SKIPPED'] += 1
        return True
    def update_concept_external_id(url, id_param, name, ext_id, original_resp):
        """Update the external ID of a concept."""
        valid_uuid = is_valid_36_char_uuid(ext_id)
        changed_uuid = False
        concept_names = concept_details.get('names', [])
        if not DRY_RUN and not valid_uuid:
            new_external_id = generate_new_uuid()
            data = {
                "id": id_param,
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
            'Concept ID': id_param,
            'Name': name,
            'URL': url,
            'Current External ID': ext_id,
            'New External ID': new_external_id if not DRY_RUN and changed_uuid else '{}',
            'Original Response': original_resp,
            'Update Payload': json.dumps(data) if not DRY_RUN and changed_uuid else '{}'
        })

    def fetch_all_concepts(url):
        "Fetch all concepts from the API and return them as a list."
        all_concepts = []
        total_concepts = 0
        page = 1
        while True:
            data = requests.get(f"{url}&page={page}", timeout=30)
            if data.status_code == 200:
                data = data.json()
                total_concepts += len(data)
                # If no more data is available, break the loop
                if not data:
                    break
                # Add data to all_concepts list
                all_concepts.extend(data)
                page += 1
                # Print progress
                print(f"Page {page} fetched. Total concepts: {total_concepts}")
            else:
                print(f"Error fetching page {page}: {data.status_code}")
                break
        return all_concepts

    # Get the list of concepts in the source
    LIMIT = "?q=&limit=0"
    if not SOURCE_ID:
        concepts_url = f"{OCL_API_URL}/orgs/{ORG_ID}/collections/{COLLECTION_ID}/concepts/{LIMIT}"
    else:
        concepts_url = f"{OCL_API_URL}/orgs/{ORG_ID}/sources/{SOURCE_ID}/concepts/{LIMIT}"

    # Print the total number of concepts to be processed
    concepts = fetch_all_concepts(concepts_url)
    TOTAL_CONCEPTS = len(concepts)
    PROCESSED_CONCEPTS_COUNT = 0

    # Iterate over the concepts and update external IDs based on the conditions
    for concept in concepts:
        concept_url = f"{OCL_API_URL}{concept['url']}"
        concept_id = concept['id']
        external_id = concept.get('external_id', '')
        response = requests.get(concept_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        concept_details = response.json()
        concept_name = concept['display_name']
        update_concept_external_id(
            concept_url, concept_id, concept_name, external_id, concept_details
        )

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
print(f"TOTAL CONCEPTS ARE {TOTAL_CONCEPTS} AND PROCESSED CONCEPTS ARE {PROCESSED_CONCEPTS_COUNT}")
print(f"Number of concepts updated because they were empty: {COUNTERS['UPDATED_EMPTY']}")
print(f"Number of concepts updated because they started with 'MSF-': {COUNTERS['UPDATED_MSF']}")
print(f"Number of concepts updated because ID was <36 characters: {COUNTERS['UPDATED_INVALID']}")
print(f"Number of concepts skipped: {COUNTERS['SKIPPED']}")
