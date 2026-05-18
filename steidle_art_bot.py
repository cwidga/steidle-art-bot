"""
Steidle Art Bot (Final Clean Version)
Posts one random artwork from the Penn State EMS Museum Steidle Collection
as a Bluesky external link preview using Omeka S API data.

Requirements:
    requests
    atproto

Environment variables required:
    BLUESKY_HANDLE
    BLUESKY_APP_PASSWORD
"""

import os
import random
import re
import requests
from atproto import Client

BASE_COLLECTION_URL = "https://exhibitions.psu.edu/s/EMSMuseum-Steidle-collection/item"
API_BASE = "https://exhibitions.psu.edu/api/items"


# --------------------------------------------------
# Get all numeric item URLs from collection landing
# --------------------------------------------------
def get_collection_items():
    api_url = "https://exhibitions.psu.edu/api/items?site_id=3&per_page=1000"

    response = requests.get(api_url)
    response.raise_for_status()

    items = response.json()

    urls = []

    for item in items:
        item_id = item.get("o:id")
        if item_id:
            item_url = f"https://exhibitions.psu.edu/s/EMSMuseum-Steidle-collection/item/{item_id}"
            urls.append(item_url)

    return urls


# --------------------------------------------------
# Fetch item metadata from Omeka S API
# --------------------------------------------------
def scrape_item_page(url):
    item_id = url.rstrip("/").split("/")[-1]
    api_url = f"{API_BASE}/{item_id}"

    response = requests.get(api_url)
    response.raise_for_status()
    data = response.json()

    title = data.get("o:title", "Untitled")

    creator = "Creator unknown"
    if "dcterms:creator" in data:
        values = data["dcterms:creator"]
        if isinstance(values, list) and values:
            creator = values[0].get("@value", creator)

    date = "Date unknown"
    if "dcterms:date" in data:
        values = data["dcterms:date"]
        if isinstance(values, list) and values:
            date = values[0].get("@value", date)

    materials = "Materials not listed"
    if "dcterms:medium" in data:
        values = data["dcterms:medium"]
        if isinstance(values, list) and values:
            materials = values[0].get("@value", materials)

    return title, creator, date, materials


# --------------------------------------------------
# Post to Bluesky as external link preview
# --------------------------------------------------
def post_to_bluesky(title, creator, date, materials, item_url):
    handle = os.getenv("BLUESKY_HANDLE")
    password = os.getenv("BLUESKY_APP_PASSWORD")

    if not handle or not password:
        raise EnvironmentError("Missing Bluesky credentials.")

    client = Client(base_url="https://bsky.social")
    client.login(handle, password)

    print("Logged in as:", client.me.handle)

    response = client.send_post(
        text=f"{title}\n{item_url}",
        embed={
            "$type": "app.bsky.embed.external",
            "external": {
                "uri": item_url,
                "title": title or "Untitled",
                "description": f"{creator or 'Creator unknown'} | {date or 'Date unknown'} | {materials or 'Materials not listed'}",
            },
        },
    )

    print("Post URI:", response.uri)


# --------------------------------------------------
# Main execution
# --------------------------------------------------
def main():
    items = get_collection_items()

    if not items:
        print("No items found.")
        return

    random.shuffle(items)

    for item_url in items:
        print("Trying:", item_url)

        try:
            title, creator, date, materials = scrape_item_page(item_url)
            post_to_bluesky(title, creator, date, materials, item_url)
            print("Posted:", title)
            return
        except Exception as e:
            print("Skipping due to error:", e)
            continue

    print("No valid items found.")


if __name__ == "__main__":
    main()
