#!/usr/bin/env python3
from __future__ import annotations

"""Coursera course catalog scraper.

Pulls course metadata from Coursera's public REST API, supplements
with JSON-LD structured data from individual course pages, resolves
instructor/partner names, and outputs CSV + JSON for downstream
dbt ingestion into a star-schema data warehouse.
"""

import csv
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime
from typing import Any, Optional

import cloudscraper
from bs4 import BeautifulSoup

# ── CONFIG ───────────────────────────────────────────────────────────
BASE_API = "https://api.coursera.org/api"
COURSES_ENDPOINT = f"{BASE_API}/courses.v1"
INSTRUCTORS_ENDPOINT = f"{BASE_API}/instructors.v1"
PARTNERS_ENDPOINT = f"{BASE_API}/partners.v1"
COURSE_PAGE_BASE = "https://www.coursera.org/learn"
API_PAGE_SIZE = 100
API_DELAY = 0.5
PAGE_DELAY_MIN = 2.0
PAGE_DELAY_MAX = 3.0
BACKOFF_BASE = 10
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

OUTPUT_DIR = "output"
CSV_PATH = os.path.join(OUTPUT_DIR, "coursera_courses.csv")
JSON_PATH = os.path.join(OUTPUT_DIR, "coursera_courses.json")
CHECKPOINT_PATH = os.path.join(OUTPUT_DIR, "scraped_ids.txt")
LOG_PATH = os.path.join(OUTPUT_DIR, "scraper.log")

OUTPUT_COLUMNS = [
    "course_id", "Course_Title", "Course_URL", "Platform", "Language",
    "Description", "Skill", "Level", "Price", "No. of Reviews / Ratings",
    "No. of Students enrolled", "Programming Instructor", "Last_Update",
    "Type_of_Course", "Duration",
]

COURSE_TYPE_MAP = {
    "v1.session": "Course", "v2.ondemand": "Course",
    "v2.capstone": "Course", "course": "Course",
    "s12n": "Specialization", "specialization": "Specialization",
    "professional certificate": "Professional Certificate",
    "professional-certificate": "Professional Certificate",
    "guided project": "Guided Project", "project": "Guided Project",
    "rhyme project": "Guided Project", "degree": "Degree",
}

LEVEL_MAP = {
    "beginner": "Beginner", "introductory": "Beginner",
    "intermediate": "Intermediate", "mixed": "Mixed",
    "advanced": "Advanced",
}

LANG_MAP = {
    "en": "English", "ar": "Arabic", "fr": "French", "es": "Spanish",
    "de": "German", "pt": "Portuguese", "zh": "Chinese",
    "ja": "Japanese", "ko": "Korean", "ru": "Russian",
    "it": "Italian", "tr": "Turkish", "hi": "Hindi",
    "nl": "Dutch", "pl": "Polish", "sv": "Swedish",
}

logger = logging.getLogger("coursera_scraper")


# ── LOGGING ──────────────────────────────────────────────────────────
def setup_logging() -> None:
    """Configure logging to both file and console with timestamps."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    logger.addHandler(ch)


# ── CHECKPOINT ───────────────────────────────────────────────────────
def load_checkpoint() -> set[str]:
    """Read scraped_ids.txt and return set of already-scraped course IDs."""
    if not os.path.exists(CHECKPOINT_PATH):
        return set()
    with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
        ids = {line.strip() for line in f if line.strip()}
    logger.info("Checkpoint loaded: %d courses already scraped", len(ids))
    return ids


def save_checkpoint(course_id: str) -> None:
    """Append one course_id to the checkpoint file."""
    with open(CHECKPOINT_PATH, "a", encoding="utf-8") as f:
        f.write(f"{course_id}\n")


# ── API FETCHERS ─────────────────────────────────────────────────────
def _create_session() -> cloudscraper.CloudScraper:
    """Create a cloudscraper session with default headers."""
    session = cloudscraper.create_scraper()
    session.headers.update(HEADERS)
    return session


def _api_get(session: cloudscraper.CloudScraper, url: str,
             params: dict | None = None) -> dict | None:
    """GET with retry logic for API endpoints. Returns parsed JSON or None."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning("429 rate-limited. Waiting %ds (attempt %d/%d)",
                               wait, attempt + 1, MAX_RETRIES)
                time.sleep(wait)
                continue
            if resp.status_code in (503, 502, 500):
                logger.warning("HTTP %d. Waiting 5s (attempt %d/%d)",
                               resp.status_code, attempt + 1, MAX_RETRIES)
                time.sleep(5)
                continue
            logger.error("HTTP %d for %s", resp.status_code, url)
            return None
        except Exception as exc:
            logger.error("Connection error for %s: %s", url, exc)
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
    logger.error("All retries exhausted for %s", url)
    return None


def fetch_all_courses_from_api(session: cloudscraper.CloudScraper) -> list[dict]:
    """Paginate through courses.v1 API and return all course objects."""
    courses: list[dict] = []
    start = 0
    fields = "id,slug,name,courseType,primaryLanguages,instructorIds,partnerIds,domainTypes,description,categories"
    while True:
        params = {"start": start, "limit": API_PAGE_SIZE,
                  "fields": fields, "includes": "instructorIds,partnerIds"}
        data = _api_get(session, COURSES_ENDPOINT, params)
        if not data:
            logger.error("Failed to fetch courses at start=%d, stopping pagination", start)
            break
        elements = data.get("elements", [])
        if not elements:
            break
        courses.extend(elements)
        logger.info("Fetched %d courses (total so far: %d)", len(elements), len(courses))
        paging = data.get("paging", {})
        nxt = paging.get("next")
        if nxt is None or len(elements) < API_PAGE_SIZE:
            break
        start = nxt if isinstance(nxt, int) else start + API_PAGE_SIZE
        time.sleep(API_DELAY)
    logger.info("Total courses from API: %d", len(courses))
    return courses


def fetch_instructors(session: cloudscraper.CloudScraper,
                      instructor_ids: list[str]) -> dict[str, str]:
    """Batch-fetch instructor names. Returns {id: fullName}."""
    if not instructor_ids:
        return {}
    mapping: dict[str, str] = {}
    batch_size = 50
    for i in range(0, len(instructor_ids), batch_size):
        batch = instructor_ids[i:i + batch_size]
        ids_param = ",".join(batch)
        params = {"ids": ids_param, "fields": "fullName,firstName,lastName"}
        data = _api_get(session, INSTRUCTORS_ENDPOINT, params)
        if data:
            for elem in data.get("elements", []):
                eid = str(elem.get("id", ""))
                name = elem.get("fullName", "")
                if not name:
                    fn = elem.get("firstName", "")
                    ln = elem.get("lastName", "")
                    name = f"{fn} {ln}".strip()
                if eid and name:
                    mapping[eid] = name
        time.sleep(API_DELAY)
    logger.info("Fetched %d instructor names", len(mapping))
    return mapping


def fetch_partners(session: cloudscraper.CloudScraper,
                   partner_ids: list[str]) -> dict[str, str]:
    """Batch-fetch partner/university names. Returns {id: name}."""
    if not partner_ids:
        return {}
    mapping: dict[str, str] = {}
    batch_size = 50
    for i in range(0, len(partner_ids), batch_size):
        batch = partner_ids[i:i + batch_size]
        ids_param = ",".join(batch)
        params = {"ids": ids_param, "fields": "name"}
        data = _api_get(session, PARTNERS_ENDPOINT, params)
        if data:
            for elem in data.get("elements", []):
                eid = str(elem.get("id", ""))
                name = elem.get("name", "")
                if eid and name:
                    mapping[eid] = name
        time.sleep(API_DELAY)
    logger.info("Fetched %d partner names", len(mapping))
    return mapping


# ── COURSE PAGE SCRAPER ──────────────────────────────────────────────
def fetch_course_page_data(session: cloudscraper.CloudScraper,
                           slug: str) -> dict[str, Any]:
    """Fetch a course page and extract JSON-LD + Apollo state metadata.

    Returns dict with: description, rating_count, avg_rating,
    price, last_update, duration, level, enrollment_count.
    """
    result: dict[str, Any] = {
        "description": None, "rating_count": None, "avg_rating": None,
        "price": None, "last_update": None, "duration": None,
        "level": None, "enrollment_count": None,
    }
    url = f"{COURSE_PAGE_BASE}/{slug}"
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=30,
                               headers={**HEADERS, "Accept": "text/html"})
            if resp.status_code == 429:
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning("429 on page %s. Waiting %ds", slug, wait)
                time.sleep(wait)
                continue
            if resp.status_code in (503, 502):
                logger.warning("HTTP %d on page %s. Retrying...", resp.status_code, slug)
                time.sleep(5)
                continue
            if resp.status_code == 404:
                logger.warning("404 for course page: %s", slug)
                return result
            if resp.status_code != 200:
                logger.warning("HTTP %d for course page: %s", resp.status_code, slug)
                return result
            break
        except Exception as exc:
            logger.error("Connection error fetching page %s: %s", slug, exc)
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
            else:
                return result
    else:
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Extract JSON-LD ──
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            ld = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        # Handle array of JSON-LD objects
        if isinstance(ld, list):
            for item in ld:
                if isinstance(item, dict) and item.get("@type") in ("Course", "Product"):
                    ld = item
                    break
            else:
                continue
        if not isinstance(ld, dict):
            continue
        t = ld.get("@type", "")
        if t not in ("Course", "Product", "WebPage"):
            continue

        result["description"] = ld.get("description") or result["description"]
        agg = ld.get("aggregateRating")
        if isinstance(agg, dict):
            try:
                result["avg_rating"] = float(agg.get("ratingValue", 0)) or None
            except (ValueError, TypeError):
                pass
            # Coursera uses ratingCount (not reviewCount) in JSON-LD
            for key in ("ratingCount", "reviewCount"):
                try:
                    val = int(agg.get(key, 0))
                    if val:
                        result["rating_count"] = val
                        break
                except (ValueError, TypeError):
                    pass
        offers = ld.get("offers")
        if isinstance(offers, dict):
            result["price"] = _extract_price(offers)
        elif isinstance(offers, list) and offers:
            result["price"] = _extract_price(offers[0])
        dm = ld.get("dateModified") or ld.get("datePublished")
        if dm:
            result["last_update"] = _parse_date(dm)
        tr = ld.get("timeRequired")
        if tr:
            result["duration"] = _parse_duration(tr)
        el = ld.get("educationalLevel")
        if el:
            result["level"] = el
        break  # Use first matching JSON-LD

    # ── Extract Apollo state for fields not in JSON-LD ──
    page_text = resp.text
    _extract_apollo_state(page_text, result)

    # Enrollment count fallback: look in page text
    if result["enrollment_count"] is None:
        result["enrollment_count"] = _extract_enrollment(soup)

    return result


def _extract_apollo_state(page_text: str, result: dict) -> None:
    """Parse embedded Apollo/script state for duration, ratings, last update."""
    # Look for the largest script tag which typically has Apollo state
    # Extract specific fields using regex (faster than full JSON parse)

    # Rating count fallback
    if result["rating_count"] is None:
        m = re.search(r'"ratingCount":\s*(\d+)', page_text)
        if m:
            try:
                result["rating_count"] = int(m.group(1))
            except ValueError:
                pass

    # Duration: prefer estimatedWorkload (human-readable), fallback to totalDuration
    if result["duration"] is None:
        m = re.search(r'"estimatedWorkload":\s*"([^"]+)"', page_text)
        if m:
            # Decode unicode escapes like \u002F -> /
            raw = m.group(1).encode().decode('unicode_escape', errors='ignore')
            result["duration"] = raw
        else:
            # Try totalDuration (ISO 8601)
            m = re.search(r'"totalDuration":\s*"(PT[^"]+)"', page_text)
            if m:
                result["duration"] = _parse_duration(m.group(1))

    # Last update: try launchedAt or updatedAt
    if result["last_update"] is None:
        for key in ("contentLastRefreshed", "updatedAt", "launchedAt"):
            m = re.search(r'"' + key + r'":\s*"([^"]+)"', page_text)
            if m:
                parsed = _parse_date(m.group(1))
                if parsed:
                    result["last_update"] = parsed
                    break


def _extract_price(offers: dict) -> str:
    """Parse an offers dict into a price string.

    Coursera JSON-LD typically uses 'category' (Free / Partially Free / Paid)
    instead of a numeric 'price' field.  We handle both cases.
    """
    # 1. Try numeric price first
    price = offers.get("price")
    if price is not None and str(price).strip() not in ("", "0"):
        try:
            p = float(price)
            if p == 0:
                return "Free"
            currency = offers.get("priceCurrency", "USD")
            return f"${p:.2f}" if currency == "USD" else f"{p:.2f} {currency}"
        except (ValueError, TypeError):
            return str(price)

    # 2. Fall back to category field
    category = offers.get("category", "")
    if category:
        cat_lower = category.strip().lower()
        if cat_lower == "free":
            return "Free"
        if "partially" in cat_lower or "freemium" in cat_lower:
            return "Free (Audit) / Paid (Certificate)"
        if cat_lower in ("paid", "premium"):
            return "Paid (Subscription)"
        return category.strip()

    return "Free"


def _parse_date(raw: str) -> str | None:
    """Try to parse a date string into YYYY-MM-DD."""
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Last resort: extract YYYY-MM-DD with regex
    m = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    return m.group(1) if m else None


def _parse_duration(raw: str) -> str:
    """Parse ISO 8601 duration or return raw string."""
    if not raw:
        return ""
    m = re.match(r"P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?"
                 r"(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", raw)
    if not m or not any(m.groups()):
        return raw.strip()
    parts = []
    y, mo, w, d, h, mi, s = m.groups()
    if y: parts.append(f"{y} year{'s' if int(y) != 1 else ''}")
    if mo: parts.append(f"{mo} month{'s' if int(mo) != 1 else ''}")
    if w: parts.append(f"{w} week{'s' if int(w) != 1 else ''}")
    if d: parts.append(f"{d} day{'s' if int(d) != 1 else ''}")
    if h: parts.append(f"{h} hour{'s' if int(h) != 1 else ''}")
    if mi: parts.append(f"{mi} minute{'s' if int(mi) != 1 else ''}")
    if s: parts.append(f"{s} second{'s' if int(s) != 1 else ''}")
    return ", ".join(parts) if parts else raw.strip()


def _extract_enrollment(soup: BeautifulSoup) -> int | None:
    """Try to extract enrollment count from page HTML."""
    # Common patterns: "1,234,567 already enrolled", "X students"
    text = soup.get_text(" ", strip=True)
    patterns = [
        r"([\d,]+)\s+(?:already\s+)?enroll",
        r"([\d,]+)\s+student",
        r"([\d,]+)\s+learner",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


# ── NORMALIZERS ──────────────────────────────────────────────────────
def normalize_level(raw_level: str | None) -> str:
    """Map any level string to: Beginner / Intermediate / Advanced / Mixed / Unknown."""
    if not raw_level:
        return "Unknown"
    key = raw_level.strip().lower()
    for token, normalized in LEVEL_MAP.items():
        if token in key:
            return normalized
    return "Unknown"


def normalize_course_type(raw_type: str | None) -> str:
    """Map API courseType to human-readable string."""
    if not raw_type:
        return "Course"
    key = raw_type.strip().lower()
    return COURSE_TYPE_MAP.get(key, "Course")


def normalize_price(price_str: str | None) -> str:
    """Clean up price string for output.

    When price is unavailable, default to the most common Coursera model.
    """
    if not price_str:
        return "Free (Audit) / Paid (Certificate)"
    return price_str


# ── RECORD BUILDER ───────────────────────────────────────────────────
def build_course_record(api_data: dict, page_data: dict,
                        instructors: dict[str, str],
                        partners: dict[str, str]) -> dict:
    """Merge all data sources into one record matching OUTPUT_COLUMNS."""
    slug = api_data.get("slug", "")
    course_url = f"{COURSE_PAGE_BASE}/{slug}" if slug else ""

    # Language
    langs = api_data.get("primaryLanguages", [])
    lang_code = langs[0] if langs else ""
    language = LANG_MAP.get(lang_code, lang_code.capitalize() if lang_code else "")

    # Skills from domainTypes
    domain_types = api_data.get("domainTypes", [])
    skills = []
    for dt in domain_types:
        if isinstance(dt, dict):
            sub = dt.get("subdomainId", "")
            dom = dt.get("domainId", "")
            if sub:
                skills.append(sub.replace("-", " ").title())
            elif dom:
                skills.append(dom.replace("-", " ").title())
    skill_str = ", ".join(dict.fromkeys(skills)) if skills else ""

    # Instructors
    iids = api_data.get("instructorIds", [])
    instr_names = [instructors[str(iid)] for iid in iids if str(iid) in instructors]
    instructor_str = ", ".join(instr_names)

    # Description: prefer page data (richer), fall back to API
    description = page_data.get("description") or api_data.get("description", "") or ""

    # Level
    level = normalize_level(page_data.get("level"))

    # Price
    price = normalize_price(page_data.get("price"))

    return {
        "course_id": str(api_data.get("id", "")),
        "Course_Title": api_data.get("name", ""),
        "Course_URL": course_url,
        "Platform": "Coursera",
        "Language": language,
        "Description": description,
        "Skill": skill_str,
        "Level": level,
        "Price": price,
        "No. of Reviews / Ratings": page_data.get("rating_count"),
        "No. of Students enrolled": page_data.get("enrollment_count"),
        "Programming Instructor": instructor_str,
        "Last_Update": page_data.get("last_update") or "",
        "Type_of_Course": normalize_course_type(api_data.get("courseType")),
        "Duration": page_data.get("duration") or "",
    }


# ── OUTPUT ───────────────────────────────────────────────────────────
def save_outputs(records: list[dict]) -> None:
    """Write CSV and JSON outputs, then delete checkpoint file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS,
                                quoting=csv.QUOTE_NONNUMERIC,
                                extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            clean = {}
            for col in OUTPUT_COLUMNS:
                val = rec.get(col)
                clean[col] = "" if val is None else val
            writer.writerow(clean)
    logger.info("CSV written to %s (%d records)", CSV_PATH, len(records))

    # JSON
    json_records = []
    for rec in records:
        jr = {}
        for col in OUTPUT_COLUMNS:
            jr[col] = rec.get(col)
        json_records.append(jr)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(json_records, f, indent=2, ensure_ascii=False, default=str)
    logger.info("JSON written to %s (%d records)", JSON_PATH, len(records))

    # Delete checkpoint on success
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)
        logger.info("Checkpoint file deleted (run complete)")


# ── MAIN ─────────────────────────────────────────────────────────────
def main() -> None:
    """Orchestrate the full scrape pipeline."""
    import argparse
    parser = argparse.ArgumentParser(description="Coursera course scraper")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max courses to scrape (0 = all)")
    args = parser.parse_args()

    setup_logging()
    logger.info("=" * 60)
    logger.info("Coursera Scraper starting at %s", datetime.now().isoformat())
    logger.info("=" * 60)

    session = _create_session()
    scraped_ids = load_checkpoint()

    # Step 1: Fetch all courses from API
    logger.info("Step 1: Fetching course catalog from API...")
    all_courses = fetch_all_courses_from_api(session)
    if not all_courses:
        logger.error("No courses fetched from API. Exiting.")
        return

    if args.limit > 0:
        all_courses = all_courses[:args.limit]
        logger.info("Limiting to first %d courses (--limit)", args.limit)

    # Step 2: Collect all instructor and partner IDs for batch fetch
    logger.info("Step 2: Fetching instructor and partner data...")
    all_instructor_ids: set[str] = set()
    all_partner_ids: set[str] = set()
    for c in all_courses:
        for iid in c.get("instructorIds", []):
            all_instructor_ids.add(str(iid))
        for pid in c.get("partnerIds", []):
            all_partner_ids.add(str(pid))

    instructors = fetch_instructors(session, list(all_instructor_ids))
    partners = fetch_partners(session, list(all_partner_ids))

    # Step 3: Load existing partial results if resuming
    partial_records: list[dict] = []
    if scraped_ids and os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                partial_records = json.load(f)
            logger.info("Loaded %d partial records from previous run", len(partial_records))
        except Exception:
            partial_records = []

    records = list(partial_records)
    total = len(all_courses)
    skipped = 0
    failed = 0
    new_scraped = 0

    # Step 4: Scrape each course page for supplemental data
    logger.info("Step 3: Scraping individual course pages for supplemental data...")
    for idx, course in enumerate(all_courses, 1):
        cid = str(course.get("id", ""))
        slug = course.get("slug", "")
        name = course.get("name", "Unknown")

        if cid in scraped_ids:
            skipped += 1
            continue

        print(f"\rScraping course {idx}/{total}: {name[:60]:<60}", end="", flush=True)
        logger.debug("Scraping course %d/%d: %s (id=%s, slug=%s)",
                      idx, total, name, cid, slug)

        try:
            page_data = fetch_course_page_data(session, slug) if slug else {
                "description": None, "rating_count": None, "avg_rating": None,
                "price": None, "last_update": None, "duration": None,
                "level": None, "enrollment_count": None,
            }
            record = build_course_record(course, page_data, instructors, partners)
            records.append(record)
            save_checkpoint(cid)
            new_scraped += 1
        except Exception as exc:
            logger.error("Failed to process course %s (%s): %s", cid, name, exc)
            failed += 1

        # Rate limit between page fetches
        time.sleep(random.uniform(PAGE_DELAY_MIN, PAGE_DELAY_MAX))

        # Periodic save every 100 courses
        if new_scraped > 0 and new_scraped % 100 == 0:
            logger.info("Periodic save: %d records so far", len(records))
            try:
                _periodic_save(records)
            except Exception as exc:
                logger.warning("Periodic save failed: %s", exc)

    print()  # Newline after progress
    logger.info("=" * 60)
    logger.info("Scraping complete!")
    logger.info("  Total courses in catalog: %d", total)
    logger.info("  Newly scraped:            %d", new_scraped)
    logger.info("  Skipped (checkpoint):     %d", skipped)
    logger.info("  Failed:                   %d", failed)
    logger.info("  Total records:            %d", len(records))
    logger.info("=" * 60)

    # Step 5: Save final outputs
    if records:
        save_outputs(records)
        logger.info("Done. Output files in %s/", OUTPUT_DIR)
    else:
        logger.warning("No records to save.")


def _periodic_save(records: list[dict]) -> None:
    """Save intermediate results without deleting checkpoint."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump([{col: r.get(col) for col in OUTPUT_COLUMNS} for r in records],
                  f, indent=2, ensure_ascii=False, default=str)


if __name__ == "__main__":
    main()
