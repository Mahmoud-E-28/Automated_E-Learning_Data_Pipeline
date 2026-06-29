"""
Udemy API Client مع Concurrency
"""
from curl_cffi import requests as curl_requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging
from threading import Lock
from config import (
    GRAPHQL_URL, PRICING_URL, COURSE_DETAILS_URL,
    HEADERS, PAGE_SIZE, REQUEST_DELAY,
    RETRY_ATTEMPTS, RETRY_DELAY, MAX_WORKERS,
    REQUEST_TIMEOUT
)

logger = logging.getLogger(__name__)


GRAPHQL_QUERY = """
query BrowseCourseSearch(
  $page: NonNegativeInt!,
  $pageSize: MaxResultsPerPage!,
  $sortOrder: CourseSearchSortType,
  $filters: CourseSearchFilters,
  $context: CourseSearchContext!
) {
  courseSearch(
    page: $page,
    pageSize: $pageSize,
    sortOrder: $sortOrder,
    filters: $filters,
    context: $context
  ) {
    count
    pageCount
    page
    results {
      course {
        id
        title
        headline
        urlCourseLanding
        locale
        level
        updatedOn
        durationInSeconds
        isFree
        isPracticeTestCourse
        instructors { id name }
        rating { average count }
      }
    }
    filterOptions {
      label
      key
      buckets {
        label
        value
        key
        countWithFilterApplied
      }
    }
  }
}
"""


# ========== SESSION (Thread-safe) ==========
session = curl_requests.Session(impersonate="chrome120")
session.headers.update(HEADERS)
session_lock = Lock()


def make_request(method, url, **kwargs):
    """Generic request with retry"""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = session.request(
                method, url,
                timeout=REQUEST_TIMEOUT,
                **kwargs
            )

            if response.status_code == 403:
                if "Just a moment" in response.text[:500]:
                    logger.error(
                        "⚠️  Cloudflare Challenge! Cookie expired - get new cookie!"
                    )
                    return None

            
            if response.status_code == 400:
                logger.error(
                    f"❌ HTTP 400 Bad Request for {url} | "
                    f"Response: {response.text[:300]}"
                )
                return None

            response.raise_for_status()
            data = response.json()

           
            if isinstance(data, dict) and "errors" in data:
                real_errors = [
                    e for e in data["errors"]
                    if "inSubscriptions" not in str(e.get("path", ""))
                ]
                if real_errors:
                    logger.warning(f"GraphQL errors: {real_errors[:2]}")

            return data

        except Exception as e:
            logger.warning(
                f"Attempt {attempt + 1} failed for {url}: {str(e)[:150]}"
            )
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                logger.error(f"All retries failed: {url}")
                return None


def fetch_courses_page(filters: dict, page: int = 0):
    
    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {
            "page": page,
            "pageSize": PAGE_SIZE,
            "sortOrder": "REVIEWS",
            "context": {"triggerType": "BROWSE_CATEGORY"},
            "filters": filters,
        }
    }

    data = make_request("POST", GRAPHQL_URL, json=payload)

    if data and "data" in data and data["data"].get("courseSearch"):
        return data["data"]["courseSearch"]

    return None


def fetch_course_details(course_id):
  
    fields = ",".join([
        "description",
        "num_subscribers",
        "num_reviews",
        "instructional_level",
        "content_info",
        "primary_category",
        "primary_subcategory",
        "topics",              
        "title",
        "headline",
        "is_paid",
        "locale",
    ])

    url = COURSE_DETAILS_URL.format(course_id=course_id)
    return make_request("GET", url, params={"fields[course]": fields})


def fetch_prices_bulk(course_ids: list):

    if not course_ids:
        return {}

    params = {
        "course_ids": ",".join(str(cid) for cid in course_ids),
        "fields[pricing_result]": "price,list_price,discount_percent_for_display",
    }

    data = make_request("GET", PRICING_URL, params=params)

    if data and "courses" in data:
        return data["courses"]
    return {}


def fetch_details_concurrent(course_ids: list):
  
    results = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_id = {
            executor.submit(fetch_course_details, cid): cid
            for cid in course_ids
        }
        for future in as_completed(future_to_id):
            cid = future_to_id[future]
            try:
                results[cid] = future.result()
            except Exception as e:
                logger.warning(f"Failed details for {cid}: {str(e)[:80]}")
                results[cid] = None

    return results