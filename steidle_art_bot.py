"""
Steidle Art Bot
Posts one random artwork from the Penn State EMS Museum Steidle Collection
as a Bluesky image post with metadata and item link.

Requirements:
    requests
    atproto

Environment variables required:
    BLUESKY_HANDLE
    BLUESKY_APP_PASSWORD
"""

import os
import random
import requests
from atproto import Client

BASE_DOMAIN = "https://exhibitions.psu.edu"
SITE_ID = 12
SITE_SLUG = "EMSMuseum-Steidle-collection"


# --------------------------------------------------
# Get all collection item URLs (with pagination)
# --------------------------------------------------
def get_collection_items():
    base_api = f"{BASE_DOMAIN}/api/items"
    urls = []
    page = 1

    while True:
        api_url = f"{base_api}?site_id={SITE_ID}&page={page}"
        response = requests.get(api_url)
        response.raise_for_status()

        items = response.json()
        if not items:
            break

        for item in items:
            item_id = item.get("o:id")
            if item_id:
                item_url = f"{BASE_DOMAIN}/s/{SITE_SLUG}/item/{item_id}"
                urls.append(item_url)

        page += 1

    print("Total items found:", len(urls))
    return urls


# --------------------------------------------------
# Get metadata + image via Omeka API
# --------------------------------------------------
def scrape_item_page(url):
    item_id = url.rstrip("/").split("/")[-1]
    api_url = f"{BASE_DOMAIN}/api/items/{item_id}"

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

    # IMAGE retrieval via media endpoint
    image_url = None
    media_list = data.get("o:media", [])

    if media_list:
        media_id = media_list[0].get("o:id")

        if media_id:
            media_api = f"{BASE_DOMAIN}/api/media/{media_id}"
            media_response = requests.get(media_api)
            media_response.raise_for_status()
            media_data = media_response.json()

            image_url = media_data.get("o:original_url")

            if not image_url:
                thumbs = media_data.get("o:thumbnail_urls", {})
                image_url = (
                    thumbs.get("large")
                    or thumbs.get("medium")
                    or thumbs.get("square")
                )

    if image_url and not image_url.startswith("http"):
        image_url = BASE_DOMAIN + image_url

    return title, creator, date, materials, image_url


# --------------------------------------------------
# Post to Bluesky with image embed
# --------------------------------------------------
from atproto import models

def post_to_bluesky(title, creator, date, materials, item_url, image_url):
    handle = os.getenv("BLUESKY_HANDLE")
    password = os.getenv("BLUESKY_APP_PASSWORD")

    client = Client(base_url="https://bsky.social")
    client.login(handle, password)

    # Download image
    headers = {"User-Agent": "Mozilla/5.0"}
    image_response = requests.get(image_url, headers=headers, timeout=20)
    image_response.raise_for_status()
    image_bytes = image_response.content

    upload = client.upload_blob(image_bytes)

    caption = (
        f"{title}\n"
        f"{creator} | {date} | {materials}\n\n"
        f"{item_url}\n\n"
        "#bsmuseums #artbot #pennstate"
    )
facets = []

# URL facet
start = caption.find(item_url)
end = start + len(item_url)

facets.append(
    models.AppBskyRichtextFacet.Main(
        index=models.AppBskyRichtextFacet.ByteSlice(
            byteStart=start,
            byteEnd=end,
        ),
        features=[
            models.AppBskyRichtextFacet.Link(uri=item_url)
        ],
    )
)

# Hashtags
hashtags = ["bsmuseums", "artbot", "pennstate"]

for tag in hashtags:
    hashtag_text = f"#{tag}"
    tag_start = caption.find(hashtag_text)
    tag_end = tag_start + len(hashtag_text)

    facets.append(
        models.AppBskyRichtextFacet.Main(
            index=models.AppBskyRichtextFacet.ByteSlice(
                byteStart=tag_start,
                byteEnd=tag_end,
            ),
            features=[
                models.AppBskyRichtextFacet.Tag(tag=tag)
            ],
        )
    )

    # Hashtag facet
    hashtag = "#bsmuseums"
    tag_start = caption.find(hashtag)
    tag_end = tag_start + len(hashtag)

    facets.append(
        models.AppBskyRichtextFacet.Main(
            index=models.AppBskyRichtextFacet.ByteSlice(
                byteStart=tag_start,
                byteEnd=tag_end,
            ),
            features=[
                models.AppBskyRichtextFacet.Tag(tag="bsmuseums")
            ],
        )
    )

    response = client.send_post(
        text=caption,
        facets=facets,
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
# Main
# --------------------------------------------------
def main():
    items = get_collection_items()

    if not items:
        print("No items found.")
        return

    random.shuffle(items)

    for item_url in items:
        print("Trying:", item_url)

        title, creator, date, materials, image_url = scrape_item_page(item_url)

        if image_url:
            post_to_bluesky(title, creator, date, materials, item_url, image_url)
            print("Posted:", title)
            return

    print("No valid items with images found.")


if __name__ == "__main__":
    main()
