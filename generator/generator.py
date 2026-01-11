"""
Real-time event generator for Kafka.

Generates clickstream events and sends them to Kafka topic.
"""

import json
import logging
import os
import random
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List

from faker import Faker
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", "kafka-1:29092,kafka-2:29092,kafka-3:29092"
)
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "clickstream-events")
EVENTS_PER_SECOND = int(os.getenv("EVENTS_PER_SECOND", "10"))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Faker for generating random data
fake = Faker(["ru_RU", "en_US"])

# Sample data for realistic events
PAGES = [
    {"url": "/", "title": "Главная", "category": "main"},
    {"url": "/catalog", "title": "Каталог", "category": "catalog"},
    {"url": "/catalog/electronics", "title": "Электроника", "category": "catalog"},
    {"url": "/catalog/clothing", "title": "Одежда", "category": "catalog"},
    {"url": "/catalog/books", "title": "Книги", "category": "catalog"},
    {"url": "/catalog/sports", "title": "Спорт", "category": "catalog"},
    {"url": "/product/1", "title": "iPhone 15 Pro", "category": "product"},
    {"url": "/product/2", "title": "Samsung Galaxy S24", "category": "product"},
    {"url": "/product/3", "title": "MacBook Pro 16", "category": "product"},
    {"url": "/product/4", "title": "Sony WH-1000XM5", "category": "product"},
    {"url": "/product/5", "title": "Nike Air Max", "category": "product"},
    {"url": "/cart", "title": "Корзина", "category": "checkout"},
    {"url": "/checkout", "title": "Оформление заказа", "category": "checkout"},
    {"url": "/checkout/payment", "title": "Оплата", "category": "checkout"},
    {"url": "/checkout/success", "title": "Заказ оформлен", "category": "checkout"},
    {"url": "/profile", "title": "Личный кабинет", "category": "user"},
    {"url": "/profile/orders", "title": "Мои заказы", "category": "user"},
    {"url": "/profile/settings", "title": "Настройки", "category": "user"},
    {"url": "/search", "title": "Поиск", "category": "search"},
    {"url": "/about", "title": "О компании", "category": "info"},
    {"url": "/contacts", "title": "Контакты", "category": "info"},
    {"url": "/blog", "title": "Блог", "category": "content"},
    {"url": "/blog/article-1", "title": "Статья 1", "category": "content"},
    {"url": "/blog/article-2", "title": "Статья 2", "category": "content"},
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
]

USER_AGENTS = [
    # Desktop Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Desktop Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Desktop Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Mobile Chrome
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1",
    # Mobile Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    # Tablet
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-X910) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

COUNTRIES = ["RU", "US", "DE", "FR", "GB", "JP", "CN", "BR", "IN", "CA"]

DEVICE_TYPES = ["desktop", "mobile", "tablet"]


class SessionManager:
    """Manages user sessions for realistic event generation."""

    def __init__(self, max_sessions: int = 100):
        self.max_sessions = max_sessions
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def get_or_create_session(self) -> Dict[str, Any]:
        """Get existing session or create new one."""
        # 70% chance to continue existing session
        if self.sessions and random.random() < 0.7:
            session_id = random.choice(list(self.sessions.keys()))
            session = self.sessions[session_id]
            session["events_count"] += 1
            return session

        # Create new session
        session_id = f"sess-{uuid.uuid4().hex[:12]}"
        user_agent = random.choice(USER_AGENTS)
        device_type = self._detect_device_type(user_agent)

        session = {
            "session_id": session_id,
            "user_id": random.randint(1, 10000),
            "user_agent": user_agent,
            "device_type": device_type,
            "ip": fake.ipv4_public(),
            "country": random.choice(COUNTRIES),
            "referrer": self._generate_referrer(),
            "current_page": random.choice(PAGES),
            "events_count": 1,
            "started_at": datetime.utcnow(),
        }

        # Limit sessions
        if len(self.sessions) >= self.max_sessions:
            oldest_session = min(
                self.sessions.keys(),
                key=lambda k: self.sessions[k]["started_at"]
            )
            del self.sessions[oldest_session]

        self.sessions[session_id] = session
        return session

    def _detect_device_type(self, user_agent: str) -> str:
        """Detect device type from user agent."""
        ua_lower = user_agent.lower()
        if "mobile" in ua_lower or "iphone" in ua_lower or "android" in ua_lower:
            if "ipad" in ua_lower or "tablet" in ua_lower:
                return "tablet"
            return "mobile"
        return "desktop"

    def _generate_referrer(self) -> str:
        """Generate referrer URL."""
        referrers = [
            "",  # Direct
            "https://google.com/search?q=...",
            "https://yandex.ru/search?text=...",
            "https://vk.com/",
            "https://t.me/",
            "https://youtube.com/",
            "/",  # Internal
            "/catalog",
            "/search",
        ]
        return random.choice(referrers)

    def navigate(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate user navigation to next page."""
        current = session["current_page"]

        # Weighted navigation based on current page
        if current["category"] == "main":
            next_pages = [p for p in PAGES if p["category"] in ["catalog", "search", "content"]]
        elif current["category"] == "catalog":
            next_pages = [p for p in PAGES if p["category"] in ["product", "catalog"]]
        elif current["category"] == "product":
            next_pages = [p for p in PAGES if p["category"] in ["cart", "product", "catalog"]]
        elif current["category"] == "checkout":
            next_pages = [p for p in PAGES if p["category"] == "checkout"]
        else:
            next_pages = PAGES

        session["current_page"] = random.choice(next_pages)
        return session


class EventGenerator:
    """Generates clickstream events."""

    def __init__(self):
        self.session_manager = SessionManager()

    def generate_event(self) -> Dict[str, Any]:
        """Generate a single clickstream event."""
        session = self.session_manager.get_or_create_session()

        # 60% views, 40% clicks
        event_type = "view" if random.random() < 0.6 else "click"

        event = {
            "type": event_type,
            "session_id": session["session_id"],
            "user_id": session["user_id"],
            "url": session["current_page"]["url"],
            "created_at": datetime.utcnow().isoformat() + "Z",
            "referrer": session["referrer"],
            "device_type": session["device_type"],
            "user_agent": session["user_agent"],
            "ip": session["ip"],
            "country": session["country"],
        }

        # Add payload for click events
        if event_type == "click":
            element = random.choice(ELEMENTS)
            event["payload"] = {
                "event_title": element["title"],
                "element_id": element["id"],
                "x": random.randint(0, 1920),
                "y": random.randint(0, 1080),
            }

        # Navigate to next page for future events
        self.session_manager.navigate(session)

        return event


def create_producer() -> KafkaProducer:
    """Create Kafka producer with retry logic."""
    servers = KAFKA_BOOTSTRAP_SERVERS.split(",")

    for attempt in range(30):
        try:
            producer = KafkaProducer(
                bootstrap_servers=servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=3,
            )
            logger.info(f"Connected to Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except KafkaError as e:
            logger.warning(f"Kafka connection attempt {attempt + 1} failed: {e}")
            time.sleep(2)

    raise Exception("Failed to connect to Kafka after 30 attempts")


def main():
    """Main function to run the event generator."""
    logger.info("Starting event generator...")
    logger.info(f"Kafka servers: {KAFKA_BOOTSTRAP_SERVERS}")
    logger.info(f"Kafka topic: {KAFKA_TOPIC}")
    logger.info(f"Events per second: {EVENTS_PER_SECOND}")

    # Create producer
    producer = create_producer()

    # Create event generator
    generator = EventGenerator()

    # Calculate delay between events
    delay = 1.0 / EVENTS_PER_SECOND

    events_sent = 0
    start_time = time.time()

    try:
        while True:
            # Generate and send event
            event = generator.generate_event()

            try:
                producer.send(KAFKA_TOPIC, value=event)
                events_sent += 1

                if events_sent % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = events_sent / elapsed
                    logger.info(
                        f"Sent {events_sent} events, "
                        f"rate: {rate:.2f} events/sec"
                    )

            except KafkaError as e:
                logger.error(f"Failed to send event: {e}")

            time.sleep(delay)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        producer.close()
        logger.info(f"Total events sent: {events_sent}")


if __name__ == "__main__":
    main()
