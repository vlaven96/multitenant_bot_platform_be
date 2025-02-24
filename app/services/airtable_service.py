import requests
from typing import List, Dict, Optional
from app.services.key_vault.key_vault_manager import KeyVaultManager


class AirtableService:
    def __init__(self, base_id: str, table_name: str, api_key_secret_name: str):
        """
        Initializes the Airtable service with the necessary configuration.

        :param base_id: The ID of the Airtable base.
        :param table_name: The name of the Airtable table.
        :param api_key_secret_name: The name of the secret for the Airtable API key in the key vault.
        """
        self.base_id = base_id
        self.table_name = table_name
        self.api_key = KeyVaultManager.get_secret(api_key_secret_name)
        self.endpoint = f'https://api.airtable.com/v0/{self.base_id}/{self.table_name}'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def get_records_from_view(self, view_name: str) -> List[Dict]:
        """
        Retrieves records from an Airtable view.

        :param view_name: The name of the Airtable view to retrieve records from.
        :return: A list of records from the specified view.
        """
        records = []
        params = {'view': view_name}

        while True:
            try:
                response = requests.get(self.endpoint, headers=self.headers, params=params)
                if response.status_code != 200:
                    print(f"Failed to fetch records: {response.status_code} - {response.text}")
                    break

                data = response.json()
                records.extend(data.get('records', []))

                # Handle pagination if an 'offset' is provided in the response
                if 'offset' in data:
                    params['offset'] = data['offset']
                else:
                    break

            except Exception as e:
                print(f"An error occurred while fetching records: {str(e)}")
                break

        return records
