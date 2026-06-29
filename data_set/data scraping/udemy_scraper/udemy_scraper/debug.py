"""
Debug Script - باستخدام curl_cffi
"""
import json
from pathlib import Path
from curl_cffi import requests as curl_requests

# ══════════════════════════════════════════════════════════
# Cookie
# ══════════════════════════════════════════════════════════
cookie_file = Path("cookie.txt")
if not cookie_file.exists():
    print("❌ cookie.txt not found!")
    exit()

cookie = cookie_file.read_text(encoding="utf-8").strip()

print("=" * 60)
print("🔍 DEBUG INFO")
print("=" * 60)
print(f"Cookie length           : {len(cookie)} characters")
print(f"Contains cf_clearance   : {'cf_clearance'  in cookie}")
print(f"Contains __udmy_2_v57r  : {'__udmy_2_v57r' in cookie}")
print(f"Contains __cf_bm        : {'__cf_bm'        in cookie}")
print(f"Contains access_token   : {'access_token'   in cookie}")
print("=" * 60)

if 'cf_clearance' not in cookie:
    print("\n⚠️  cf_clearance missing! جدد الـ Cookie من المتصفح.")
    exit()

# ══════════════════════════════════════════════════════════
# Session
# ══════════════════════════════════════════════════════════
headers = {
    "accept":          "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type":    "application/json",
    "origin":          "https://www.udemy.com",
    "referer":         "https://www.udemy.com/courses/development/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    ),
    "cookie": cookie,
}

session = curl_requests.Session(impersonate="chrome120")
session.headers.update(headers)


# ══════════════════════════════════════════════════════════
# Test 1: Pricing Endpoint
# ══════════════════════════════════════════════════════════
print("\n🧪 Test 1: Pricing endpoint")
try:
    r = session.get(
        "https://www.udemy.com/api-2.0/pricing/"
        "?course_ids=567828&fields[pricing_result]=price",
        timeout=30,
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        print(f"   ✅ SUCCESS! {r.text[:200]}")
    else:
        print(f"   ❌ {r.text[:200]}")
except Exception as e:
    print(f"   ❌ Error: {e}")


# ══════════════════════════════════════════════════════════
# Test 2: Course Details (بدون topics)
# ══════════════════════════════════════════════════════════
print("\n🧪 Test 2: Course Details (basic fields)")
try:
    r = session.get(
        "https://www.udemy.com/api-2.0/courses/567828/"
        "?fields[course]=title,num_subscribers,instructional_level,"
        "content_info,description,primary_subcategory",
        timeout=30,
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        print(f"   ✅ SUCCESS! {r.text[:200]}")
    else:
        print(f"   ❌ {r.text[:200]}")
except Exception as e:
    print(f"   ❌ Error: {e}")


# ══════════════════════════════════════════════════════════
# Test 3: GraphQL Health Check
# ══════════════════════════════════════════════════════════
print("\n🧪 Test 3: GraphQL health check")
try:
    r = session.post(
        "https://www.udemy.com/api/2024-01/graphql/",
        json={"query": "query { __typename }", "variables": {}},
        timeout=30,
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        print(f"   ✅ SUCCESS! {r.text[:200]}")
    else:
        print(f"   ❌ {r.text[:200]}")
except Exception as e:
    print(f"   ❌ Error: {e}")


# ══════════════════════════════════════════════════════════
# Test 4: GraphQL - topics field
# ══════════════════════════════════════════════════════════
print("\n🧪 Test 4: GraphQL - topics vs learningOutcomes")

SKILLS_TEST_QUERY = """
query BrowseCourseSearch(
  $pageId: String!
  $pageSize: Int!
) {
  courseSearch(
    pageId: $pageId
    pageSize: $pageSize
  ) {
    courses {
      edges {
        node {
          id
          title
          topics {
            id
            title
          }
          learningOutcomes
        }
      }
    }
    totalCount
  }
}
"""

try:
    r = session.post(
        "https://www.udemy.com/api/2024-01/graphql/",
        json={
            "query": SKILLS_TEST_QUERY,
            "variables": {
                "pageId": "288",   # Development
                "pageSize": 3,
            },
        },
        timeout=30,
    )
    print(f"   Status: {r.status_code}")

    if r.status_code == 200:
        data = r.json()

        if data.get("errors"):
            print(f"   ⚠️  GraphQL Errors: {data['errors']}")
        else:
            edges = (
                data.get("data", {})
                    .get("courseSearch", {})
                    .get("courses", {})
                    .get("edges", [])
            )
            total = (
                data.get("data", {})
                    .get("courseSearch", {})
                    .get("totalCount", 0)
            )
            print(f"   ✅ SUCCESS! Total courses: {total}")
            print()

            for i, edge in enumerate(edges, 1):
                node  = edge.get("node", {})
                topics = node.get("topics") or []
                lo     = node.get("learningOutcomes") or []
                skills = " | ".join(
                    t.get("title", "") for t in topics if t.get("title")
                )

                print(f"   📌 [{i}] {node.get('title', 'N/A')[:55]}")

                if skills:
                    print(f"       ✅ topics (Skills)     : {skills}")
                else:
                    print(f"       ⚠️  topics              : فاضي في GraphQL")

                if lo:
                    print(f"       ❌ learningOutcomes[0] : {str(lo[0])[:70]}...")
                else:
                    print(f"       ℹ️  learningOutcomes    : فاضي")
                print()
    else:
        print(f"   ❌ {r.text[:300]}")

except Exception as e:
    print(f"   ❌ Error: {e}")


# ══════════════════════════════════════════════════════════
# Test 5: REST API - topics field ✅ (الجديد)
# ══════════════════════════════════════════════════════════
print("\n🧪 Test 5: REST API - topics field (Skills من REST)")
try:
    r = session.get(
        "https://www.udemy.com/api-2.0/courses/567828/"
        "?fields[course]=title,topics",
        timeout=30,
    )
    print(f"   Status: {r.status_code}")

    if r.status_code == 200:
        data   = r.json()
        topics = data.get("topics") or []

        if topics:
            skills = " | ".join(
                t.get("title", "") for t in topics if t.get("title")
            )
            print(f"   ✅ Topics found   : {skills}")
            print(f"   📌 Course Title   : {data.get('title', 'N/A')}")
        else:
            print(f"   ⚠️  topics فاضي في REST API كمان!")
            print(f"   🔎 Raw response   : {str(data)[:300]}")
    else:
        print(f"   ❌ {r.text[:200]}")

except Exception as e:
    print(f"   ❌ Error: {e}")


# ══════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("✅ Debug Done!")
print("=" * 60)
print("""
📋 تفسير النتايج:
  Test 1 ✅ → Pricing API شغال
  Test 2 ✅ → Course Details شغال
  Test 3 ✅ → GraphQL شغال
  Test 4 ✅ → topics في GraphQL موجودة  → Skills هتتملا تلقائياً
  Test 4 ⚠️ → topics فاضي في GraphQL   → هيروح لـ Test 5
  Test 5 ✅ → topics في REST موجودة    → Skills هتتملا من REST
  Test 5 ⚠️ → topics فاضي في REST كمان → Skills هتفضل فاضي (أحسن من غلط)
""")