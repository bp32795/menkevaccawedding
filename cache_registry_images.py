"""
Retroactively cache all registry item images to Azure Blob Storage.

Usage:
    python cache_registry_images.py

Requires environment variables:
    COSMOS_ENDPOINT, COSMOS_KEY  (or COSMOS_DATABASE / COSMOS_CONTAINER overrides)
    BLOB_CONNECTION_STRING       (Azure Storage connection string)
    BLOB_CONTAINER_NAME          (default: registry-images)
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

# ---------- Cosmos DB setup ----------
try:
    from azure.cosmos import CosmosClient, PartitionKey
except ImportError:
    print("ERROR: azure-cosmos is required.  pip install azure-cosmos")
    sys.exit(1)

try:
    from azure.storage.blob import BlobServiceClient, ContentSettings
except ImportError:
    print("ERROR: azure-storage-blob is required.  pip install azure-storage-blob")
    sys.exit(1)

COSMOS_ENDPOINT = os.environ.get('COSMOS_ENDPOINT', '')
COSMOS_KEY = os.environ.get('COSMOS_KEY', '')
COSMOS_DATABASE = os.environ.get('COSMOS_DATABASE', 'wedding')
COSMOS_CONTAINER = os.environ.get('COSMOS_CONTAINER', 'registry')
BLOB_CONNECTION_STRING = os.environ.get('BLOB_CONNECTION_STRING', '')
BLOB_CONTAINER_NAME = os.environ.get('BLOB_CONTAINER_NAME', 'registry-images')

if not COSMOS_ENDPOINT or not COSMOS_KEY:
    print("ERROR: COSMOS_ENDPOINT and COSMOS_KEY must be set.")
    sys.exit(1)
if not BLOB_CONNECTION_STRING:
    print("ERROR: BLOB_CONNECTION_STRING must be set.")
    sys.exit(1)


def main():
    # Connect Cosmos DB
    cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
    database = cosmos_client.get_database_client(COSMOS_DATABASE)
    container = database.get_container_client(COSMOS_CONTAINER)

    # Connect Blob Storage
    blob_service = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
    blob_container = blob_service.get_container_client(BLOB_CONTAINER_NAME)
    try:
        blob_container.get_container_properties()
    except Exception:
        blob_container.create_container()
        print(f"Created blob container: {BLOB_CONTAINER_NAME}")

    # Fetch all registry items
    items = list(container.query_items(query="SELECT * FROM c", enable_cross_partition_query=True))
    print(f"Found {len(items)} registry items.")

    cached = 0
    skipped = 0
    failed = 0

    for item in items:
        item_id = item['id']
        image_url = item.get('image_url', '')

        # Skip if already cached
        if item.get('cached_image'):
            print(f"  SKIP  {item.get('title', item_id)[:50]} — already cached")
            skipped += 1
            continue

        # Skip if no image URL
        if not image_url:
            print(f"  SKIP  {item.get('title', item_id)[:50]} — no image URL")
            skipped += 1
            continue

        # Download image
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                              '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            }
            resp = requests.get(image_url, headers=headers, timeout=15)
            resp.raise_for_status()

            content_type = resp.headers.get('Content-Type', 'image/jpeg')
            ext_map = {
                'image/jpeg': '.jpg', 'image/png': '.png',
                'image/webp': '.webp', 'image/gif': '.gif',
            }
            ext = ext_map.get(content_type.split(';')[0].strip(), '.jpg')
            blob_name = f"{item_id}{ext}"

            blob_client = blob_container.get_blob_client(blob_name)
            blob_client.upload_blob(
                resp.content,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type.split(';')[0].strip()),
            )

            # Update Cosmos DB item with cached_image field
            item['cached_image'] = blob_name
            container.replace_item(item=item_id, body=item)

            print(f"  OK    {item.get('title', item_id)[:50]} → {blob_name}")
            cached += 1

        except Exception as e:
            print(f"  FAIL  {item.get('title', item_id)[:50]} — {e}")
            failed += 1

    print(f"\nDone: {cached} cached, {skipped} skipped, {failed} failed.")


if __name__ == '__main__':
    main()
