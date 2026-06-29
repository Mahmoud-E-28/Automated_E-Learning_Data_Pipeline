"""
Discover Topic Filter Field - بنجرب أسماء مختلفة
"""
from pathlib import Path
from curl_cffi import requests as curl_requests

cookie = Path("cookie.txt").read_text(encoding="utf-8").strip()

headers = {
    "accept": "*/*",
    "content-type": "application/json",
    "origin": "https://www.udemy.com",
    "referer": "https://www.udemy.com/courses/development/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "cookie": cookie,
}

session = curl_requests.Session(impersonate="chrome120")
session.headers.update(headers)

QUERY = """
query Test($filters: CourseSearchFilters, $context: CourseSearchContext!) {
  courseSearch(page: 0, pageSize: 1, filters: $filters, context: $context) {
    count
  }
}
"""

# نجرب أسماء كتيرة
candidates = [
    "courseLabelIds",
    "courseLabel",
    "courseLabels",
    "topicIds",
    "topicId",
    "topics",
    "labelIds",
    "labels",
    "tagIds",
    "tags",
]

print("🔍 Testing different field names for Topic filter...\n")

# Filter بـ Web Development subcategory + Python topic (id=7380)
TOPIC_VALUE = 7380

for field_name in candidates:
    filters = {
        "pageId": "288",
        "subcategoryIds": [8],
        field_name: [TOPIC_VALUE]
    }
    
    payload = {
        "query": QUERY,
        "variables": {
            "filters": filters,
            "context": {"triggerType": "BROWSE_CATEGORY"}
        }
    }
    
    try:
        r = session.post(
            "https://www.udemy.com/api/2024-01/graphql/",
            json=payload,
            timeout=15
        )
        data = r.json()
        
        if "errors" in data:
            err_msg = data["errors"][0].get("message", "")[:120]
            if "not defined" in err_msg or "is not defined" in err_msg:
                print(f"❌ {field_name:<25} → field NOT exists")
            elif "got invalid value" in err_msg:
                print(f"⚠️  {field_name:<25} → exists but wrong format: {err_msg[:80]}")
            else:
                print(f"❓ {field_name:<25} → {err_msg[:100]}")
        else:
            count = data.get("data", {}).get("courseSearch", {}).get("count", "?")
            print(f"✅ {field_name:<25} → SUCCESS! count={count}")
    except Exception as e:
        print(f"💥 {field_name:<25} → Exception: {str(e)[:80]}")


print("\n🔍 Testing with non-list values:\n")
for field_name in ["courseLabel", "topicId", "topic"]:
    filters = {
        "pageId": "288",
        "subcategoryIds": [8],
        field_name: TOPIC_VALUE
    }
    
    payload = {
        "query": QUERY,
        "variables": {
            "filters": filters,
            "context": {"triggerType": "BROWSE_CATEGORY"}
        }
    }
    
    try:
        r = session.post(
            "https://www.udemy.com/api/2024-01/graphql/",
            json=payload,
            timeout=15
        )
        data = r.json()
        
        if "errors" in data:
            err_msg = data["errors"][0].get("message", "")[:120]
            if "not defined" in err_msg:
                print(f"❌ {field_name:<25} → NOT exists")
            else:
                print(f"⚠️  {field_name:<25} → {err_msg[:100]}")
        else:
            count = data.get("data", {}).get("courseSearch", {}).get("count", "?")
            print(f"✅ {field_name:<25} → SUCCESS! count={count}")
    except Exception as e:
        print(f"💥 {field_name:<25} → {str(e)[:80]}")