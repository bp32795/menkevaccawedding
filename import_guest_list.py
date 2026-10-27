"""Import names-only guest households into the configured response database."""

import argparse
import json
import os
import shutil
import subprocess

from rsvp_tracking import read_guest_households


def main():
    """Validate a guest CSV and upsert households, optionally using an Azure app's settings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_path')
    parser.add_argument('--azure-app')
    parser.add_argument('--resource-group')
    args = parser.parse_args()
    if bool(args.azure_app) != bool(args.resource_group):
        parser.error('--azure-app and --resource-group must be provided together')

    with open(args.csv_path, encoding='utf-8-sig', newline='') as source:
        households = read_guest_households(source)

    if args.azure_app:
        azure_cli = shutil.which('az')
        if not azure_cli:
            parser.error('Azure CLI is required to read production app settings')
        result = subprocess.run(
            [
                azure_cli, 'webapp', 'config', 'appsettings', 'list',
                '--resource-group', args.resource_group, '--name', args.azure_app,
                '--query', "[?starts_with(name, 'COSMOS_')]", '--output', 'json'
            ],
            check=True, capture_output=True, text=True
        )
        settings = {setting['name']: setting['value'] for setting in json.loads(result.stdout)}
        if not settings.get('COSMOS_ENDPOINT') or not settings.get('COSMOS_KEY'):
            parser.error('The Azure app is missing Cosmos DB connection settings')
        os.environ.update(settings)

    from app import get_response_container

    container = get_response_container()
    if container is None:
        raise RuntimeError('Cannot connect to the guest response database.')
    for household in households:
        container.upsert_item(body=household)
    print(f'Imported {len(households)} households (names only; no contact information).')


if __name__ == '__main__':
    main()
