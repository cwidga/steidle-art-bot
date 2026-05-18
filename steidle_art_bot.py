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
def post_to_bluesky(image_bytes, title, creator, date, materials, item_url):
    handle = os.getenv("BLUESKY_HANDLE")
    password = os.getenv("BLUESKY_APP_PASSWORD")

    client = Client(base_url="https://bsky.social")
    client.login(handle, password)

    print("Logged in as:", client.me.handle)

    upload = client.upload_blob(image_bytes)

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
        if "/item/" in a["href"] and a["href"].count("/") > 2:
            full_url = a["href"]
            if not full_url.startswith("http"):
                full_url = BASE_DOMAIN + full_url
            links.append(full_url)

    return list(set(links))


def scrape_item_page(url):
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Primary item image (exclude hero/banner images)
    image_url = None
    main_content = soup.select_one("main")
    if main_content:
        for img in main_content.find_all("img"):
            src = img.get("src")
            if src and "hero" not in src.lower():
                image_url = src
                break

    if image_url and not image_url.startswith("http"):
        image_url = BASE_DOMAIN + image_url

    # Extract metadata
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    creator = "Unknown creator"
    date = "Date unknown"
    materials = "Materials not listed"

    metadata_text = soup.get_text(separator="\n")

    for line in metadata_text.split("\n"):
        clean = line.strip()
        lower = clean.lower()
        if lower.startswith("creator") or lower.startswith("artist"):
            creator = clean
        if lower.startswith("date"):
            date = clean
        if lower.startswith("materials") or lower.startswith("medium"):
            materials = clean

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

    client = Client()
    client.login(handle, password)

    upload = client.upload_blob(image_bytes)

    post_text = (
        f"{title}\n"
        f"{creator}\n"
        f"{date}\n"
        f"{materials}\n\n"
        f"{item_url}"
    )

    client.send_post(
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

print("Posted to:", client.me.handle)
print("Post URI:", response.uri)

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
