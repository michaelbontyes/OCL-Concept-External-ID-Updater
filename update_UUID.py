import argparse
import requests
import uuid
import json
import csv
from datetime import datetime

# Parse command-line arguments
parser = argparse.ArgumentParser(description="OCL Concept External ID Updater")
parser.add_argument("--dry-run", action="store_true", help="Enable dry run mode")
args = parser.parse_args()

# Load configuration from config.json
with open('config.json') as config_file:
    config = json.load(config_file)

OCL_API_URL = config['OCL_API_URL']
SOURCE_ID = config['SOURCE_ID']
OCL_TOKEN = config['OCL_TOKEN']
ORG_ID = config['ORG_ID']

# Dry run option
DRY_RUN = args.dry_run

# Counters for updated and skipped concepts
updated_empty = 0
updated_msf = 0
updated_invalid = 0
skipped = 0

# Headers for the API request
headers = {
    "Authorization": f"Token {OCL_TOKEN}",
    "Content-Type": "application/json"
}

# Prepare CSV file for dry run mode
if DRY_RUN:
    csv_filename = 'updated_concepts_dry_run.csv'
else:
    csv_filename = 'updated_concepts.csv'

with open(csv_filename, mode='w', newline='') as csv_file:
    fieldnames = ['Timestamp', 'ID', 'Name', 'URL', 'Current External ID', 'New External ID']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()

    # Function to generate a new UUID (16 characters)
    def generate_new_uuid():
        return str(uuid.uuid4())[:36]

    # Function to check if the external ID is a valid 16-character UUID
    def is_valid_36_char_uuid(external_id):
        global updated_empty, updated_msf, updated_invalid
        if external_id is None or external_id == '':
            updated_empty += 1
            return False
        if external_id.startswith("MSF-"):
            updated_msf += 1
            return False
        if len(external_id) != 36:
            updated_invalid += 1
            return False
        else: 
            return True

    # Function to update the external ID of a concept
    def update_concept_external_id(concept_url, concept_id, new_external_id, concept_names):
        payload = {
            "id": concept_id,
            "external_id": new_external_id,
            "names": concept_names
        }
        if not DRY_RUN:
            response = requests.patch(concept_url, headers=headers, json=payload)
            response.raise_for_status()

        # Write to CSV
        writer.writerow({
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ID': concept_id,
            'Name': concept_names[0]['name'] if concept_names else '',
            'URL': concept_url,
            'Current External ID': external_id,
            'New External ID': new_external_id
        })

    # Function to get all concepts with pagination
    def get_all_concepts(url):
        all_concepts = []
        while url:
            response = requests.get(url, headers=headers)
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

    # Iterate over the concepts and update external IDs based on the conditions
    for concept in concepts:
        concept_url = f"{OCL_API_URL}{concept['url']}"
        concept_id = concept['id']
        external_id = concept.get('external_id', '')
        response = requests.get(concept_url, headers=headers)
        response.raise_for_status()
        concept_details = response.json()
        concept_names = concept_details.get('names', [])

        if is_valid_36_char_uuid(external_id):
            skipped += 1
        else:
            new_external_id = generate_new_uuid()
            update_concept_external_id(concept_url, concept_id, new_external_id, concept_names)

# Print the results
if DRY_RUN:
    print("DRY RUN MODE: No changes will be made to the OCL source.")
print(f"Number of concepts updated because they were empty: {updated_empty}")
print(f"Number of concepts updated because they started with 'MSF-': {updated_msf}")
print(f"Number of concepts updated because current ID was less than 36 characters: {updated_invalid}")
print(f"Number of concepts skipped: {skipped}")