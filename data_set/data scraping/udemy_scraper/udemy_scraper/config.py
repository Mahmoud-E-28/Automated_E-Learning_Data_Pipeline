"""
Udemy Scraper Configuration
"""
from pathlib import Path

# ========== ENDPOINTS ==========
GRAPHQL_URL        = "https://www.udemy.com/api/2024-01/graphql/"
PRICING_URL        = "https://www.udemy.com/api-2.0/pricing/"
COURSE_DETAILS_URL = "https://www.udemy.com/api-2.0/courses/{course_id}/"

# ========== COOKIE ==========
def load_cookie() -> str:
    cookie_file = Path(__file__).parent / "cookie.txt"
    if not cookie_file.exists():
        raise FileNotFoundError("❌ cookie.txt not found!")
    return cookie_file.read_text(encoding="utf-8").strip()

UDEMY_COOKIE = load_cookie()

# ========== HEADERS ==========
HEADERS = {
    "accept":             "*/*",
    "accept-language":    "en-US,en;q=0.9",
    "content-type":       "application/json",
    "origin":             "https://www.udemy.com",
    "referer":            "https://www.udemy.com/courses/development/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
    ),
    "sec-ch-ua":          '"Google Chrome";v="148", "Not.A/Brand";v="8", "Chromium";v="148"',
    "sec-ch-ua-mobile":   "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest":     "empty",
    "sec-fetch-mode":     "cors",
    "sec-fetch-site":     "same-origin",
    "cookie":             UDEMY_COOKIE,
}


MAIN_CATEGORIES = {
    "Development":          "288",
    "Business":             "268",
    "Finance & Accounting": "328",
    "IT & Software":        "294",
    "Office Productivity":  "292",
    "Personal Development": "296",
    "Design":               "270",
    "Marketing":            "290",
    "Lifestyle":            "284",
    "Photography & Video":  "274",
    "Health & Fitness":     "278",
    "Music":                "276",
    "Teaching & Academics": "300",
}

COURSE_DETAIL_FIELDS = ",".join([
    "title",
    "description",
    "num_subscribers",
    "instructional_level",
    "content_info",
    "primary_subcategory",
    "topics",               # ✅ Skills الصح
])

# ========== SCRAPING SETTINGS ==========
PAGE_SIZE          = 16
MAX_API_PAGES      = 625       
PRICING_BATCH_SIZE = 50
REQUEST_DELAY      = 0.5       
RETRY_ATTEMPTS     = 3
RETRY_DELAY        = 5
MAX_WORKERS        = 10      
REQUEST_TIMEOUT    = 20      

# ========== OUTPUT ==========
OUTPUT_CSV = "data/udemy_courses.csv"
STATE_FILE = "data/state.json"
LOG_FILE   = "logs/scraper.log"

# ========== TEST MODE ==========
TEST_MODE  = False            
TEST_PAGES = 2