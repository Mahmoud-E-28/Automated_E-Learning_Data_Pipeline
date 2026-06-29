"""
Scraper الرئيسي - مع Subcategory & Topic Splitting + Checkpointing
"""
import json
import time
import logging
import pandas as pd
from pathlib import Path
from tqdm import tqdm

from config import (
    REQUEST_DELAY, PRICING_BATCH_SIZE, OUTPUT_CSV,
    MAX_API_PAGES, TEST_MODE, TEST_PAGES
)
from api_client import (
    fetch_courses_page, fetch_prices_bulk, fetch_details_concurrent
)
from parser import parse_course
from state import State

logger = logging.getLogger(__name__)


def chunked(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def save_to_csv(rows: list):
    if not rows:
        return
    df = pd.DataFrame(rows)
    file_exists = Path(OUTPUT_CSV).exists()
    df.to_csv(
        OUTPUT_CSV,
        mode='a',
        header=not file_exists,
        index=False,
        encoding='utf-8-sig'
    )


def make_filter_key(filters: dict) -> str:
    return json.dumps(filters, sort_keys=True)


def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return value


def scrape_filter(filters: dict, label: str, state: State, depth: int = 0):
    indent = "  " * depth
    filter_key = make_filter_key(filters)

    if state.is_filter_complete(filter_key):
        logger.info(f"{indent}⏭️  [{label}] Already complete, skipping")
        return 0

    first_page = fetch_courses_page(filters, page=0)
    if not first_page:
        logger.error(f"{indent}❌ [{label}] Failed to fetch first page")
        return 0

    total_count = first_page.get("count", 0)
    page_count  = min(first_page.get("pageCount", 0), MAX_API_PAGES)

    logger.info(
        f"{indent}📂 [{label}] Total: {total_count:,} | Pages: {page_count}"
    )

    # ============= SPLIT BY SUBCATEGORY =============
    if (
        total_count >= 10000
        and "subcategoryIds" not in filters
        and "topicIds" not in filters
    ):
        logger.info(
            f"{indent}🔀 [{label}] Too many courses, splitting by subcategory..."
        )

        filter_options = first_page.get("filterOptions", []) or []
        subcategories  = []
        for opt in filter_options:
            if opt and opt.get("key") == "subcategory":
                subcategories = opt.get("buckets", []) or []
                break

        if not subcategories:
            logger.warning(f"{indent}⚠️  No subcategories found!")
        else:
            scraped = 0
            for sub in subcategories:
                sub_filter = {
                    **filters,
                    "subcategoryIds": [safe_int(sub["value"])]
                }
                scraped += scrape_filter(
                    sub_filter,
                    label=f"{label} > {sub['label']}",
                    state=state,
                    depth=depth + 1,
                )

            state.mark_filter_complete(filter_key)
            state.save()
            return scraped

    # ============= SPLIT BY TOPIC =============
    if total_count >= 10000 and "topicIds" not in filters:
        logger.info(
            f"{indent}🔀 [{label}] Too many, splitting by topic..."
        )

        filter_options = first_page.get("filterOptions", []) or []
        topics = []
        for opt in filter_options:
            if opt and opt.get("key") == "courseLabel":
                topics = opt.get("buckets", []) or []
                break

        if not topics:
            logger.warning(f"{indent}⚠️  No topics found!")
        else:
            scraped = 0
            for topic in topics:
                topic_filter = {
                    **filters,
                    "topicIds": [safe_int(topic["value"])]
                }
                scraped += scrape_filter(
                    topic_filter,
                    label=f"{label} > {topic['label']}",
                    state=state,
                    depth=depth + 1,
                )

            state.mark_filter_complete(filter_key)
            state.save()
            return scraped

    # ============= NORMAL SCRAPE =============
    if TEST_MODE:
        page_count = min(page_count, TEST_PAGES)

    start_page = state.get_progress(filter_key)
    if start_page > 0:
        logger.info(f"{indent}♻️  Resuming from page {start_page}")

    total_scraped = 0

    for page_num in tqdm(
        range(start_page, page_count),
        desc=f"{label[:50]}",
        leave=False,
    ):
        if page_num == 0 and start_page == 0:
            page_data = first_page
        else:
            page_data = fetch_courses_page(filters, page=page_num)
            time.sleep(REQUEST_DELAY)

        if not page_data or not page_data.get("results"):
            continue

        results        = page_data["results"]
        graphql_courses = [r["course"] for r in results if r.get("course")]
        new_courses    = [c for c in graphql_courses if not state.is_seen(c["id"])]

        if not new_courses:
            state.set_progress(filter_key, page_num + 1)
            continue

        course_ids = [c["id"] for c in new_courses]

        # ── Pricing (Bulk) ──────────────────────────────
        prices_map = {}
        for batch in chunked(course_ids, PRICING_BATCH_SIZE):
            batch_prices = fetch_prices_bulk(batch)
            prices_map.update(batch_prices)

        # ── Details (Concurrent) ────────────────────────
        # ✅ details فيها topics دلوقتي بعد إصلاح fetch_course_details()
        details_map = fetch_details_concurrent(course_ids)

        # ── Build Rows ──────────────────────────────────
        rows = []
        for course in new_courses:
            cid = course["id"]
            row = parse_course(
                graphql_course=course,
                details=details_map.get(cid),
                pricing=prices_map.get(str(cid)),
            )
            rows.append(row)
            state.add_seen(cid)

        save_to_csv(rows)
        state.set_progress(filter_key, page_num + 1)

        if page_num % 5 == 0:
            state.save()

        total_scraped += len(rows)

    state.mark_filter_complete(filter_key)
    state.save()

    logger.info(
        f"{indent}✅ [{label}] Done. Scraped {total_scraped} new courses."
    )
    return total_scraped