#!/usr/bin/env python3
"""
Understated Stays — content batch generator.

Pulls a batch of hotels (from Travelpayouts once you're approved, or from
a mock list for now), builds an affiliate deep link + caption for each,
and writes them to a review folder as simple JSON + a markdown preview
you can approve before anything posts.

Nothing in this script auto-publishes. It only prepares the batch.
Posting/scheduling is a separate step once you've reviewed a batch.

Setup:
  1. pip install requests --break-system-packages
  2. Set TRAVELPAYOUTS_TOKEN and TRAVELPAYOUTS_MARKER as env vars once
     your Travelpayouts account is approved. Until then, this runs in
     MOCK MODE using placeholder hotels so you can see the full pipeline
     working end to end.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

TRAVELPAYOUTS_TOKEN = os.environ.get("TRAVELPAYOUTS_TOKEN")
TRAVELPAYOUTS_MARKER = os.environ.get("TRAVELPAYOUTS_MARKER", "772858")  # your real marker
UNSPLASH_ACCESS_KEY = os.environ.get(
    "UNSPLASH_ACCESS_KEY", "ehblI9GT_L5j9ht59l0w919z3f103Sc6EEMutGAKKlE"
)

OUTPUT_DIR = Path("review_batches")
BATCH_SIZE = 5

# ---------------------------------------------------------------------------
# Step 1: get hotel candidates
# ---------------------------------------------------------------------------

MOCK_HOTELS = [
    {
        "name": "Casa Cook Ibiza",
        "city": "Ibiza",
        "country": "Spain",
        "hotel_id": "mock-1",
        "photo_url": "https://example.com/photos/casa-cook-ibiza.jpg",
        "blurb": "Adults-only, breeze-block architecture, boho-quiet not boho-loud.",
        "nightly_from": 190,
    },
    {
        "name": "Azulik Tulum",
        "city": "Tulum",
        "country": "Mexico",
        "hotel_id": "mock-2",
        "photo_url": "https://example.com/photos/azulik-tulum.jpg",
        "blurb": "Handbuilt treehouse suites, no electricity in some rooms, on purpose.",
        "nightly_from": 310,
    },
    {
        "name": "Amangiri",
        "city": "Canyon Point, Utah",
        "country": "USA",
        "hotel_id": "mock-3",
        "photo_url": "https://example.com/photos/amangiri.jpg",
        "blurb": "Built into the mesa itself. The desert does the decorating.",
        "nightly_from": 2500,
    },
    {
        "name": "San Giorgio Mykonos",
        "city": "Mykonos",
        "country": "Greece",
        "hotel_id": "mock-4",
        "photo_url": "https://example.com/photos/san-giorgio.jpg",
        "blurb": "The un-serious side of Mykonos. Hammocks over infinity pools.",
        "nightly_from": 220,
    },
    {
        "name": "Habitas Tulum",
        "city": "Tulum",
        "country": "Mexico",
        "hotel_id": "mock-5",
        "photo_url": "https://example.com/photos/habitas-tulum.jpg",
        "blurb": "Off-grid tents that still have better wifi than your office.",
        "nightly_from": 160,
    },
]


def fetch_hotels(batch_size=BATCH_SIZE):
    """Return a list of hotel dicts. Uses Travelpayouts if credentials are
    set, otherwise falls back to the mock list so the pipeline is testable
    right away."""
    if TRAVELPAYOUTS_TOKEN and TRAVELPAYOUTS_MARKER:
        return fetch_hotels_travelpayouts(batch_size)
    print("[mock mode] No Travelpayouts credentials found — using placeholder hotels.")
    return MOCK_HOTELS[:batch_size]


def fetch_hotels_travelpayouts(batch_size):
    """Placeholder for the real Travelpayouts integration.

    Once your account is approved, Travelpayouts gives you a data feed /
    API for hotel search results including images and prices. Wire that
    call in here — it should return the same shape as MOCK_HOTELS.
    """
    import requests  # local import so mock mode doesn't require it

    # Example shape only — replace with the real endpoint from your
    # Travelpayouts dashboard once approved.
    raise NotImplementedError(
        "Add your Travelpayouts API call here once approved. "
        "Until then this script runs in mock mode automatically."
    )


# ---------------------------------------------------------------------------
# Step 2: build affiliate link + caption for each hotel
# ---------------------------------------------------------------------------

def build_affiliate_link(hotel):
    """Real, working Hotellook deep link using your marker. Anyone who books
    through this link after clicking it gets tracked to your account."""
    city_query = hotel["city"].replace(" ", "%20")
    return f"https://search.hotellook.com/?marker={TRAVELPAYOUTS_MARKER}&destination={city_query}"


def build_caption(hotel):
    return (
        f"{hotel['name']} — {hotel['city']}, {hotel['country']}\n\n"
        f"{hotel['blurb']}\n\n"
        f"From ${hotel['nightly_from']}/night. Link in bio.\n\n"
        f"#hushluxestays #{slugify(hotel['city'])} #boutiquehotel"
    )


def slugify(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def fetch_photo_for_city(city):
    """Pull one real, free-to-use photo matching the hotel's city from
    Unsplash. Falls back to a placeholder note if the API call fails
    (e.g. no internet, bad key, rate limit)."""
    import requests

    try:
        response = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": f"{city} hotel", "per_page": 1},
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            # Fall back to a broader travel/scenery search for the city
            response = requests.get(
                "https://api.unsplash.com/search/photos",
                params={"query": city, "per_page": 1},
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                timeout=10,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
        if results:
            return {
                "photo_url": results[0]["urls"]["regular"],
                "photographer": results[0]["user"]["name"],
                "photographer_link": results[0]["user"]["links"]["html"],
            }
    except Exception as e:
        print(f"  [photo fetch failed for {city}: {e}]")

    return {"photo_url": None, "photographer": None, "photographer_link": None}


# ---------------------------------------------------------------------------
# Step 3: write the review batch
# ---------------------------------------------------------------------------

def write_batch(hotels):
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    batch = []

    for hotel in hotels:
        photo = fetch_photo_for_city(hotel["city"])
        batch.append(
            {
                "name": hotel["name"],
                "city": hotel["city"],
                "country": hotel["country"],
                "photo_url": photo["photo_url"] or hotel["photo_url"],
                "photo_credit": (
                    f"Photo by {photo['photographer']} on Unsplash ({photo['photographer_link']})"
                    if photo["photographer"]
                    else None
                ),
                "affiliate_link": build_affiliate_link(hotel),
                "caption": build_caption(hotel),
                "approved": False,
            }
        )

    json_path = OUTPUT_DIR / f"batch_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(batch, f, indent=2)

    md_path = OUTPUT_DIR / f"batch_{timestamp}.md"
    with open(md_path, "w") as f:
        f.write(f"# Review batch — {timestamp}\n\n")
        f.write("Set `\"approved\": true` in the matching JSON file for each post you want queued.\n\n")
        for i, post in enumerate(batch, 1):
            f.write(f"## {i}. {post['name']}\n\n")
            f.write(f"**Photo:** {post['photo_url']}\n\n")
            if post["photo_credit"]:
                f.write(f"**Photo credit (include in caption or comment):** {post['photo_credit']}\n\n")
            f.write(f"**Caption:**\n\n```\n{post['caption']}\n```\n\n")
            f.write(f"**Affiliate link:** {post['affiliate_link']}\n\n---\n\n")

    return json_path, md_path


if __name__ == "__main__":
    hotels = fetch_hotels()
    json_path, md_path = write_batch(hotels)
    print(f"\nWrote {len(hotels)} posts for review:")
    print(f"  {md_path}  (read this)")
    print(f"  {json_path}  (mark approved: true per post, then run the publish step)")
