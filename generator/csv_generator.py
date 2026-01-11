#!/usr/bin/env python3
"""
CSV event generator for bulk data import.

Generates 200,000+ clickstream events for initial data loading.
"""

import csv
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

from faker import Faker

# Configuration
OUTPUT_DIR = Path(__file__).parent.parent / "data"
EVENTS_FILE = OUTPUT_DIR / "events.csv"
USERS_FILE = OUTPUT_DIR / "users.csv"

TOTAL_EVENTS = 250_000  # Generate 250k events
TOTAL_USERS = 5_000     # 5000 unique users
DAYS_RANGE = 30         # Events spread over 30 days

# Initialize Faker
fake = Faker(["ru_RU", "en_US"])

# Sample data
PAGES = [
    {"url": "/", "category": "main"},
    {"url": "/catalog", "category": "catalog"},
    {"url": "/catalog/electronics", "category": "catalog"},
    {"url": "/catalog/clothing", "category": "catalog"},
    {"url": "/catalog/books", "category": "catalog"},
    {"url": "/catalog/sports", "category": "catalog"},
    {"url": "/catalog/home", "category": "catalog"},
    {"url": "/product/1", "category": "product"},
    {"url": "/product/2", "category": "product"},
    {"url": "/product/3", "category": "product"},
    {"url": "/product/4", "category": "product"},
    {"url": "/product/5", "category": "product"},
    {"url": "/product/6", "category": "product"},
    {"url": "/product/7", "category": "product"},
    {"url": "/product/8", "category": "product"},
    {"url": "/product/9", "category": "product"},
    {"url": "/product/10", "category": "product"},
    {"url": "/cart", "category": "checkout"},
    {"url": "/checkout", "category": "checkout"},
    {"url": "/checkout/payment", "category": "checkout"},
    {"url": "/checkout/success", "category": "checkout"},
    {"url": "/profile", "category": "user"},
    {"url": "/profile/orders", "category": "user"},
    {"url": "/profile/settings", "category": "user"},
    {"url": "/profile/wishlist", "category": "user"},
    {"url": "/search", "category": "search"},
    {"url": "/search?q=iphone", "category": "search"},
    {"url": "/search?q=samsung", "category": "search"},
    {"url": "/about", "category": "info"},
    {"url": "/contacts", "category": "info"},
    {"url": "/delivery", "category": "info"},
    {"url": "/returns", "category": "info"},
    {"url": "/blog", "category": "content"},
    {"url": "/blog/article-1", "category": "content"},
    {"url": "/blog/article-2", "category": "content"},
    {"url": "/blog/article-3", "category": "content"},
]

ELEMENTS = [
    {"id": "#add-to-cart", "title": "add_to_cart"},
    {"id": "#buy-now", "title": "buy_now"},
    {"id": "#subscribe", "title": "subscribe"},
    {"id": "#search-btn", "title": "search"},
    {"id": "#menu-toggle", "title": "menu_toggle"},
    {"id": "#login-btn", "title": "login"},
    {"id": "#register-btn", "title": "register"},
    {"id": "#apply-filter", "title": "apply_filter"},
    {"id": "#sort-select", "title": "sort"},
    {"id": "#load-more", "title": "load_more"},
    {"id": "#share-btn", "title": "share"},
    {"id": "#favorite-btn", "title": "favorite"},
    {"id": ".product-card", "title": "product_click"},
    {"id": ".category-link", "title": "category_click"},
    {"id": ".banner", "title": "banner_click"},
    {"id": ".nav-link", "title": "nav_click"},
    {"id": "#checkout-btn", "title": "checkout"},
    {"id": "#apply-coupon", "title": "apply_coupon"},
]

USER_AGENTS = [
    # Desktop Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Desktop Chrome (Mac)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Desktop Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Desktop Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Desktop Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Mobile Chrome (Android)
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    # Mobile Chrome (iOS)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1",
    # Mobile Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    # Tablet
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-X910) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

COUNTRIES = ["RU", "US", "DE", "FR", "GB", "JP", "CN", "BR", "IN", "CA", "ES", "IT", "AU", "KR", "NL"]

REFERRERS = [
    "",  # Direct
    "https://google.com/",
    "https://yandex.ru/",
    "https://vk.com/",
    "https://t.me/",
    "https://youtube.com/",
    "https://facebook.com/",
    "https://instagram.com/",
    "https://twitter.com/",
    "/",
    "/catalog",
    "/search",
]


def detect_device_type(user_agent: str) -> str:
    """Detect device type from user agent."""
    ua_lower = user_agent.lower()
    if "ipad" in ua_lower or "tablet" in ua_lower or "sm-x" in ua_lower:
        return "tablet"
    if "mobile" in ua_lower or "iphone" in ua_lower or "android" in ua_lower:
        return "mobile"
    return "desktop"


def generate_users() -> List[Dict[str, Any]]:
    """Generate user records."""
    print(f"Generating {TOTAL_USERS} users...")

    users = []
    for i in range(1, TOTAL_USERS + 1):
        # 70% Russian, 30% international
        if random.random() < 0.7:
            fake_locale = Faker("ru_RU")
            country = "RU"
        else:
            fake_locale = Faker("en_US")
            country = random.choice([c for c in COUNTRIES if c != "RU"])

        users.append({
            "id": i,
            "external_id": f"user-{uuid.uuid4().hex[:8]}",
            "fio": fake_locale.name(),
            "email": fake_locale.email(),
            "country": country,
        })

        if i % 1000 == 0:
            print(f"  Generated {i} users...")

    return users


def generate_events(users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate event records."""
    print(f"Generating {TOTAL_EVENTS} events...")

    events = []
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=DAYS_RANGE)

    # Create session pool
    sessions = {}

    for i in range(TOTAL_EVENTS):
        # Pick user (weighted towards active users)
        user = random.choice(users)

        # Get or create session for user
        session_key = f"{user['id']}_{random.randint(1, 3)}"  # Each user has 1-3 sessions
        if session_key not in sessions:
            sessions[session_key] = {
                "session_id": f"sess-{uuid.uuid4().hex[:12]}",
                "user_agent": random.choice(USER_AGENTS),
                "ip": fake.ipv4_public(),
            }

        session = sessions[session_key]
        device_type = detect_device_type(session["user_agent"])

        # Generate timestamp (weighted towards recent dates)
        days_ago = int(random.expovariate(0.15))  # Exponential distribution
        days_ago = min(days_ago, DAYS_RANGE)
        event_date = end_date - timedelta(
            days=days_ago,
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )

        # 60% views, 40% clicks
        event_type = "view" if random.random() < 0.6 else "click"

        page = random.choice(PAGES)

        event = {
            "type": event_type,
            "session_id": session["session_id"],
            "user_id": user["id"],
            "url": page["url"],
            "created_at": event_date.isoformat() + "Z",
            "referrer": random.choice(REFERRERS),
            "device_type": device_type,
            "user_agent": session["user_agent"],
            "ip": session["ip"],
            "event_title": "",
            "element_id": "",
            "x": "",
            "y": "",
        }

        # Add click data
        if event_type == "click":
            element = random.choice(ELEMENTS)
            event["event_title"] = element["title"]
            event["element_id"] = element["id"]
            event["x"] = random.randint(0, 1920)
            event["y"] = random.randint(0, 1080)

        events.append(event)

        if (i + 1) % 10000 == 0:
            print(f"  Generated {i + 1} events...")

    # Sort by timestamp
    events.sort(key=lambda x: x["created_at"])

    return events


def save_users_csv(users: List[Dict[str, Any]]):
    """Save users to CSV file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Saving users to {USERS_FILE}...")

    with open(USERS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "external_id", "fio", "email", "country"])
        writer.writeheader()
        writer.writerows(users)

    print(f"  Saved {len(users)} users")


def save_events_csv(events: List[Dict[str, Any]]):
    """Save events to CSV file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Saving events to {EVENTS_FILE}...")

    fieldnames = [
        "type", "session_id", "user_id", "url", "created_at",
        "referrer", "device_type", "user_agent", "ip",
        "event_title", "element_id", "x", "y"
    ]

    with open(EVENTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)

    print(f"  Saved {len(events)} events")


def main():
    """Main function to generate all data."""
    print("=" * 60)
    print("Clickstream Data Generator")
    print("=" * 60)
    print()

    # Generate users
    users = generate_users()
    save_users_csv(users)
    print()

    # Generate events
    events = generate_events(users)
    save_events_csv(events)
    print()

    # Summary
    print("=" * 60)
    print("Generation complete!")
    print(f"  Users: {len(users)}")
    print(f"  Events: {len(events)}")
    print(f"  Output directory: {OUTPUT_DIR}")
    print("=" * 60)

    # Calculate statistics
    views = sum(1 for e in events if e["type"] == "view")
    clicks = sum(1 for e in events if e["type"] == "click")
    print(f"\nEvent breakdown:")
    print(f"  Views: {views} ({views/len(events)*100:.1f}%)")
    print(f"  Clicks: {clicks} ({clicks/len(events)*100:.1f}%)")


if __name__ == "__main__":
    main()
