"""
Steidle Art Bot (GitHub Actions Version)
Posts one random artwork from the Penn State EMS Museum Steidle Collection
once per day to a Bluesky account as a link preview with primary item image.

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
import requests
from bs4 import BeautifulSoup
from atproto import Client

BASE_URL = "https://exhibitions.psu.edu/s/EMSMuseum-Steidle-collection/item"
BASE_DOMAIN = "https://exhibitions.psu.edu"


def get_collection_items():
    response = requests.get(BASE_URL)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        if "/item/" in a["href"] and a["href"].count("/") >= 4:
            full_url = a["href"]
            if not full_url.startswith("http"):
                full_url = BASE_DOMAIN + full_url
            links.append(full_url)

    return list(set(links))


def scrape_item_page(url):
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # PRIMARY ITEM IMAGE (exclude hero/banner)
    image_url = None

    main = soup.select_one("main")
    if main:
        for img in main.find_all("img"):
            src = img.get("src")
            if not src:
                continue
            lower = src.lower()
            if "hero" in lower or "banner" in lower:
                continue
            if "/files/" in lower or "/media/" in lower:
                image_url = src
                break

    if image_url and not image_url.startswith("http"):
        image_url = BASE_DOMAIN + image_url

    # METADATA EXTRACTION (structured fields)
    title = "Untitled"
    creator = "Creator unknown"
    date = "Date unknown"
    materials = "Materials not listed"

    # Title
    title_tag = soup.select_one("h1")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Metadata fields often stored in dt/dd pairs
    for dt in soup.find_all("dt"):
        label = dt.get_text(strip=True).lower()
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        value = dd.get_text(" ", strip=True)

        if "creator" in label or "artist" in label:
            creator = value
        elif "date" in label:
            date = value
        elif "material" in label or "medium" in label:
            materials = value

    return image_url, title, creator, date, materials


def download_image(image_url):
    response = requests.get(image_url)
    response.raise_for_status()
    return response.content


def post_to_bluesky(item_url, image_bytes, title, creator, date, materials):
    handle = os.getenv("BLUESKY_HANDLE")
    password = os.getenv("BLUESKY_APP_PASSWORD")

    if not handle or not password:
        raise EnvironmentError("Missing Bluesky credentials.")

    client = Client(base_url="https://bsky.social")
    client.login(handle, password)

    upload = client.upload_blob(image_bytes)

    description = f"{creator} | {date} | {materials}"

    client.send_post(
        text=f"{title}\n{item_url}",
        embed={
            "$type": "app.bsky.embed.external",
            "external": {
                "uri": item_url,
                "title": title,
                "description": description,
                "thumb": upload.blob,
            },
        },
    )


def main():
    items = get_collection_items()
    if not items:
        print("No items found.")
        return

    item_url = random.choice(items)
    image_url, title, creator, date, materials = scrape_item_page(item_url)

    if not image_url:
        print("No primary image found.")
        return

    image_bytes = download_image(image_url)

    post_to_bluesky(item_url, image_bytes, title, creator, date, materials)

    print(f"Posted: {title}")


if __name__ == "__main__":
    main()
