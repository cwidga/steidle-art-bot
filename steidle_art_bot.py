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
    api_url = "https://exhibitions.psu.edu/api/items?site_id=12&per_page=1000"

    response = requests.get(api_url)
    response.raise_for_status()

    items = response.json()

    urls = []

    for item in items:
        item_id = item.get("o:id")
        if item_id:
            item_url = f"https://exhibitions.psu.edu/s/EMSMuseum-Steidle-collection/item/{item_id}"
            urls.append(item_url)

    print("Total items found:", len(urls))
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
media_list = data.get("o:media", [])
image_url = None

if media_list:
    media_obj = media_list[0]
    thumbs = media_obj.get("o:thumbnail_urls", {})
    image_url = (
        thumbs.get("large")
        or thumbs.get("medium")
        or thumbs.get("square")
    )    
    return title, creator, date, materials, image_url

# --------------------------------------------------
# Post to Bluesky as external link preview
# --------------------------------------------------
def post_to_bluesky(title, creator, date, materials, item_url, image_url):
    handle = os.getenv("BLUESKY_HANDLE")
    password = os.getenv("BLUESKY_APP_PASSWORD")

    client = Client(base_url="https://bsky.social")
    client.login(handle, password)

    print("Logged in as:", client.me.handle)

    # Download image
    image_response = requests.get(image_url)
    image_response.raise_for_status()
    image_bytes = image_response.content

    # Upload to Bluesky
    upload = client.upload_blob(image_bytes)

    caption = f"{title}\n{creator} | {date} | {materials}\n\n{item_url}"

    response = client.send_post(
        text=caption,
        embed={
            "$type": "app.bsky.embed.images",
            "images": [
                {
                    "alt": f"{title} by {creator}, {date}. {materials}.",
                    "image": upload.blob,
                }
            ],
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

        title, creator, date, materials = scrape_item_page(item_url)

        if title:
            post_to_bluesky(title, creator, date, materials, item_url)
            print("Posted:", title)
            return
title, creator, date, materials, image_url = scrape_item_page(item_url)

if image_url:
    post_to_bluesky(title, creator, date, materials, item_url, image_url)
    print("Posted:", title)
    return
    
    print("No valid items found.")

if __name__ == "__main__":
    main()
