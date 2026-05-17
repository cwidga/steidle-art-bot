"""
Steidle Art Bot (GitHub Actions Version)
Posts one random artwork from the Penn State EMS Museum Steidle Collection
once per day to a Bluesky account.

Designed to run via GitHub Actions (no local state file required).

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


def get_collection_items():
    response = requests.get(BASE_URL)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        if "/item/" in a["href"]:
            full_url = a["href"]
            if not full_url.startswith("http"):
                full_url = "https://exhibitions.psu.edu" + full_url
            links.append(full_url)

    return list(set(links))


def scrape_item_page(url):
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Image
    img = soup.find("img")
    image_url = None
    if img and img.get("src"):
        image_url = img["src"]
        if not image_url.startswith("http"):
            image_url = "https://exhibitions.psu.edu" + image_url

    # Title
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    page_text = soup.get_text(separator="\n")
    artist = "Unknown artist"
    date = "Date unknown"

    for line in page_text.split("\n"):
        clean = line.strip()
        if clean.lower().startswith("artist"):
            artist = clean
        if clean.lower().startswith("date"):
            date = clean

    return image_url, title, artist, date


def download_image(image_url):
    response = requests.get(image_url)
    response.raise_for_status()
    return response.content


def post_to_bluesky(image_bytes, caption, alt_text):
    handle = os.getenv("BLUESKY_HANDLE")
    password = os.getenv("BLUESKY_APP_PASSWORD")

    if not handle or not password:
        raise EnvironmentError("Missing Bluesky credentials in environment variables.")

client = Client(base_url="https://bsky.social")
client.login(handle, password)

    upload = client.upload_blob(image_bytes)

    client.send_post(
        text=caption,
        embed={
            "$type": "app.bsky.embed.images",
            "images": [
                {
                    "alt": alt_text,
                    "image": upload.blob,
                }
            ],
        },
    )


def main():
    items = get_collection_items()
    if not items:
        print("No items found.")
        return

    item_url = random.choice(items)
    image_url, title, artist, date = scrape_item_page(item_url)

    if not image_url:
        print("No image found for selected item.")
        return

    image_bytes = download_image(image_url)

    caption = (
        f"{title}\n"
        f"{artist}\n"
        f"{date}\n\n"
        f"From the Steidle Collection (Penn State EMS Museum)\n"
        f"{item_url}\n\n"
        f"#SteidleArtBot"
    )

    alt_text = f"{title} by {artist}. {date}. From the Steidle Collection at Penn State EMS Museum."

    post_to_bluesky(image_bytes, caption, alt_text)

    print(f"Posted: {title}")


if __name__ == "__main__":
    main()
