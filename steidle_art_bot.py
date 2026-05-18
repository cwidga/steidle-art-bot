"""
Steidle Art Bot (GitHub Actions Version)
Posts one random artwork from the Penn State EMS Museum Steidle Collection
once per day to a Bluesky account.

GitHub-native session-based authentication.

Requirements:
    requests
    beautifulsoup4
    atproto

Environment variables required:
    BLUESKY_SESSION
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
        if "/item/" in a["href"]:
            full_url = a["href"]
            if not full_url.startswith("http"):
                full_url = BASE_DOMAIN + full_url
            links.append(full_url)

    return list(set(links))


def scrape_item_page(url):
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # ✅ Try to get primary collection image (not hero/header)
    image_url = None

    # 1. Look for item image container
    primary_img = soup.select_one("div.item-img img")
    if primary_img and primary_img.get("src"):
        image_url = primary_img["src"]

    # 2. Fallback to figure image
    if not image_url:
        figure_img = soup.select_one("figure img")
        if figure_img and figure_img.get("src"):
            image_url = figure_img["src"]

    # 3. Fallback to OpenGraph image
    if not image_url:
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            image_url = og_img["content"]

    if image_url and not image_url.startswith("http"):
        image_url = BASE_DOMAIN + image_url

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
    session_string = os.getenv("BLUESKY_SESSION")

    if not session_string:
        raise EnvironmentError("Missing BLUESKY_SESSION secret.")

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
        print("No primary image found for selected item.")
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
