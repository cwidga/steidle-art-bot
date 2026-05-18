"""
Steidle Art Bot (GitHub Native - External Embed Version)
Posts one random artwork from the Penn State EMS Museum Steidle Collection
as a Bluesky external link preview with metadata.

Requirements:
    requests
    beautifulsoup4
    atproto

Environment variables required:
    BLUESKY_HANDLE
    BLUESKY_APP_PASSWORD
"""

import os
import random
import re
import requests
from bs4 import BeautifulSoup
from atproto import Client

BASE_URL = "https://exhibitions.psu.edu/s/EMSMuseum-Steidle-collection/item"
BASE_DOMAIN = "https://exhibitions.psu.edu"


# --------------------------------------------------
# Get all valid numeric item URLs
# --------------------------------------------------
def get_collection_items():
    response = requests.get(BASE_URL)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        match = re.search(r"/item/(\d+)$", href)
        if match:
            full_url = href
            if not full_url.startswith("http"):
                full_url = BASE_DOMAIN + full_url
            links.add(full_url)

    return list(links)


# --------------------------------------------------
# Scrape individual item page
# --------------------------------------------------
def scrape_item_page(url):
    item_id = url.rstrip("/").split("/")[-1]

    api_url = f"https://exhibitions.psu.edu/api/items/{item_id}"
    response = requests.get(api_url)
    response.raise_for_status()

    data = response.json()

    # ------------------------
    # TITLE
    # ------------------------
    title = data.get("o:title", "Untitled")

    # ------------------------
    # CREATOR
    # ------------------------
    creator = "Creator unknown"
    if "dcterms:creator" in data:
        creator_values = data["dcterms:creator"]
        if isinstance(creator_values, list) and creator_values:
            creator = creator_values[0].get("@value", creator)

    # ------------------------
    # DATE
    # ------------------------
    date = "Date unknown"
    if "dcterms:date" in data:
        date_values = data["dcterms:date"]
        if isinstance(date_values, list) and date_values:
            date = date_values[0].get("@value", date)

    # ------------------------
    # MATERIALS (medium)
    # ------------------------
    materials = "Materials not listed"
    if "dcterms:medium" in data:
        medium_values = data["dcterms:medium"]
        if isinstance(medium_values, list) and medium_values:
            materials = medium_values[0].get("@value", materials)

    # ------------------------
    # IMAGE (from item API)
    # ------------------------
    image_url = None

    media_list = data.get("o:media", [])
    if media_list:
        media_obj = media_list[0]

        thumbs = media_obj.get("o:thumbnail_urls", {})
        image_url = (
            thumbs.get("large")
            or thumbs.get("medium")
            or thumbs.get("square")
        )

    return image_url, title, creator, date, materials


# --------------------------------------------------
# Download image (used only to verify valid media)
# --------------------------------------------------
def download_image(image_url):
    response = requests.get(image_url)
    response.raise_for_status()
    return response.content


# --------------------------------------------------
# Post to Bluesky as external embed
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

        image_url, title, creator, date, materials = scrape_item_page(item_url)

        if image_url:
            # Verify image exists
            download_image(image_url)

            post_to_bluesky(title, creator, date, materials, item_url)
            print("Posted:", title)
            return

    print("No valid items with images found.")


if __name__ == "__main__":
    main()
