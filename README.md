# OCL Concept External ID Updater

This script updates the external IDs of concepts in a given Open Concept Lab (OCL) source. It checks each concept's external ID against certain conditions and updates it if necessary. The updated external IDs are written to a CSV file.

It uses the [OCL API](https://docs.openconceptlab.org/en/latest/oclapi/apireference/concepts.html#edit-concept) to pull the details of each concept in the configured OCL source, check the external ID of each concept, and update it if necessary. 

[Here is an explanation video](https://www.loom.com/share/84919d2820434ae78e7be7827a607d5d?sid=b4ec5467-d560-467f-9d3a-5cbc3a324ccb)

### Conditions for Updating External IDs with a new UUID
1. If the external ID is **empty**
2. If the external ID starts with **"MSF-"**
3. If the external ID is **not a valid 36-character UUID**

## Prerequisites

- Python 3.x installed
- `requests` library installed
- `uuid` library installed

## Installation

1. Clone this repository: `git clone https://github.com/michaelbontyes/OCL_Toolbox.git`
2. Navigate to the project directory: `cd ocl-concept-updater`
3. Install the required libraries: `pip install requests uuid`

## Configuration

1. Create a `config.json` file in the project directory with the following structure:

```json
{
  "OCL_API_URL": "https://api.openconceptlab.org/",
  "SOURCE_ID": "your-source-id",
  "OCL_TOKEN": "your-api-token",
  "ORG_ID": "your-organization-id"
}
```

2. Replace "https://api.openconceptlab.org/", "your-source-id", "your-api-token", and "your-organization-id" with your actual OCL API URL, source ID, API token, and organization ID.
3. Save the config.json file.

## Usage (after careful Dry Run)
Run the script: 
`python update_UUID.py`

The script will update the external IDs of concepts in the specified OCL source and write the updated concepts to a CSV file named updated_concepts.csv and updated_concepts_dry_run.csv in Dry Run Mode.

## Dry Run / Test Mode
To run the script in dry run mode, add the --dry-run flag when executing the script:
Run the script: 
`python update_UUID.py --dry-run`

## CSV Files
The script creates two CSV files:

- **updated_concepts.csv**: Contains the details of all updated concepts, including the timestamp, concept ID, name, URL, current external ID, and new external ID.
- **updated_concepts_dry_run.csv**: Contains the details of all concepts that would have been updated if the script was run in dry run mode, including the timestamp, concept ID, name, URL, and current external ID.

### CSV File Structure
The CSV file will have the following columns:

- ID: The ID of the concept.
- Status: If the concept was updated or not by the script.
- Valid External ID: If the external UUID is a 36-characters UUID.
- Name: The name of the concept.
- URL: The URL of the concept.
- Current External ID: The current external ID of the concept.
- New External ID: The new external ID generated for the concept.
- Original Response: A Json backup of the concept before the update.
- Update Payload: A Json that details what was sent back to the OCL API (ID, External ID, Names)

## Additional Information
- The script uses pagination to retrieve all concepts from the specified OCL source.
- The script handles unexpected response formats and prints an error message if encountered.
- The script updates the external IDs in place, so make sure to back up your data before running the script.
