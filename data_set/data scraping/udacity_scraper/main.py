import os
import time
import re
import json
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

SEARCH_URL = "https://api.udacity.com/api/unified-catalog/search"
OUT_CSV = "udacity_courses_complete.csv"
CACHE_DIR = "cache"

TIMEOUT = 60
SLEEP_SEARCH = 0.20
MAX_WORKERS = 10  # عدد الـ threads المتوازية

HEADERS_SEARCH = {
    "content-type": "application/json",
    "accept": "application/json",
    "origin": "https://www.udacity.com",
    "referer": "https://www.udacity.com/catalog",
    "user-agent": "Mozilla/5.0",
}

HEADERS_NEXT = {
    "user-agent": "Mozilla/5.0",
    "accept": "application/json",
    "x-nextjs-data": "1",
}

BASE_PAYLOAD = {
    "searchText": "",
    "sortBy": "enrollment",
    "page": 0,
    "pageSize": 200,
    "keys": [],
    "skills": [],
    "schools": [],
    "semanticTypes": [],
    "rawDurations": [],
    "allowEnterpriseLPs": False,
    "enrolledOnly": False,
    "sortLPs": False,
}

# قفل للطباعة عشان متتلخبطش بين الـ threads
print_lock = Lock()


def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)


def pick(*vals):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if isinstance(v, list) and not v:
            continue
        return v
    return None


def is_taxonomy_id(s):
    """يتأكد إن القيمة مش taxonomy UUID."""
    if not isinstance(s, str):
        return False
    s = s.strip().lower()
    if s.startswith("taxonomy:"):
        return True
    if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", s):
        return True
    return False


def as_text(v):
    if v is None:
        return None

    if isinstance(v, str):
        return v.strip() or None

    if isinstance(v, list):
        out = []
        for x in v:
            if isinstance(x, str) and x.strip():
                out.append(x.strip())
            elif isinstance(x, dict):
                y = pick(
                    x.get("name"),
                    x.get("title"),
                    x.get("fullName"),
                    x.get("displayName"),
                    x.get("description"),
                    x.get("summary"),
                    x.get("text"),
                )
                if y:
                    out.append(str(y).strip())
        return ", ".join(out) if out else None

    if isinstance(v, dict):
        return pick(
            v.get("name"),
            v.get("title"),
            v.get("fullName"),
            v.get("displayName"),
            v.get("description"),
            v.get("summary"),
            v.get("text"),
        )

    return str(v)


def walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from walk(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from walk(x)


def find_value(obj, words):
    words = [w.lower() for w in words]

    for k, v in walk(obj):
        key = str(k).lower()
        if any(w in key for w in words):
            if isinstance(v, (str, int, float)) and str(v).strip():
                return v

    return None


# ============================================================
# 🆕 دوال استخراج المهارات
# ============================================================
def extract_skill_name(item):
    """يستخرج اسم المهارة من dict أو string، ويتجاهل taxonomy IDs."""
    if isinstance(item, str):
        s = item.strip()
        if s and not is_taxonomy_id(s):
            return s
        return None

    if isinstance(item, dict):
        name = pick(
            item.get("name"),
            item.get("title"),
            item.get("displayName"),
            item.get("label"),
            item.get("skillName"),
            item.get("text"),
        )
        if isinstance(name, str) and name.strip() and not is_taxonomy_id(name):
            return name.strip()
    return None


def get_skills(data, hit):
    """يجمع أسماء المهارات من كل المصادر المتاحة ويتجاهل taxonomy IDs."""
    skills = []
    seen = set()

    def add(name):
        if name:
            key = name.lower()
            if key not in seen:
                seen.add(key)
                skills.append(name)

    # 1) ابحث في كل الـ data عن مفاتيح فيها كلمة skill
    for k, v in walk(data):
        key = str(k).lower()
        if "skill" not in key:
            continue

        if isinstance(v, list):
            for item in v:
                add(extract_skill_name(item))
        elif isinstance(v, dict):
            add(extract_skill_name(v))
        elif isinstance(v, str):
            add(extract_skill_name(v))

    # 2) fallback من hit نفسه
    hit_skills = hit.get("skills") if isinstance(hit, dict) else None
    if isinstance(hit_skills, list):
        for s in hit_skills:
            add(extract_skill_name(s))

    # 3) جرّب مفاتيح إضافية شائعة
    for k in ["skillNames", "allSkills", "relatedSkills", "taughtSkills"]:
        v = hit.get(k) if isinstance(hit, dict) else None
        if isinstance(v, list):
            for s in v:
                add(extract_skill_name(s))

    return ", ".join(skills) if skills else None


# ============================================================
# 🆕 Cache helpers
# ============================================================
def cache_path(slug):
    """مسار ملف الـ cache للسلج."""
    safe_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", slug)
    return os.path.join(CACHE_DIR, f"{safe_slug}.json")


def load_from_cache(slug):
    """يحمّل الداتا من الـ cache لو موجودة."""
    path = cache_path(slug)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cached = json.load(f)
                return cached.get("data"), cached.get("path")
        except Exception:
            return None, None
    return None, None


def save_to_cache(slug, data, path):
    """يحفظ الداتا في الـ cache."""
    try:
        with open(cache_path(slug), "w", encoding="utf-8") as f:
            json.dump({"data": data, "path": path}, f, ensure_ascii=False)
    except Exception as e:
        safe_print(f"[cache-save-fail] {slug} -> {e}")


def get_build_id(session):
    html = session.get(
        "https://www.udacity.com/catalog",
        headers={"user-agent": "Mozilla/5.0"},
        timeout=TIMEOUT
    ).text

    m = re.search(r"/_next/static/([^/]+)/_buildManifest\.js", html) or \
        re.search(r"/_next/static/([^/]+)/_ssgManifest\.js", html)

    if not m:
        raise RuntimeError("Could not find Next.js buildId")

    return m.group(1)


def get_slug(hit):
    if isinstance(hit, dict) and hit.get("slug"):
        return hit["slug"]

    for v in (hit or {}).values():
        if not isinstance(v, str):
            continue

        for part in ["/course/", "/school/", "/degree/"]:
            if part in v:
                return v.split(part)[1].split("?")[0].split("#")[0].strip("/")

    return None


def get_path(hit, slug):
    for k in ["url", "catalogUrl", "path", "courseUrl", "programUrl", "absolute_url"]:
        v = hit.get(k)
        if isinstance(v, str) and v.strip():
            if v.startswith("https://www.udacity.com"):
                return v.replace("https://www.udacity.com", "")
            if v.startswith("/"):
                return v

    return f"/course/{slug}"


def get_all_hits(session):
    all_hits = []
    seen = set()
    page = 0

    while True:
        payload = dict(BASE_PAYLOAD)
        payload["page"] = page

        r = session.post(
            SEARCH_URL,
            headers=HEADERS_SEARCH,
            json=payload,
            timeout=TIMEOUT
        )
        r.raise_for_status()

        sr = r.json().get("searchResult") or {}
        hits = sr.get("hits") or []
        nb_pages = sr.get("nbPages")
        nb_hits = sr.get("nbHits")

        if not hits:
            break

        added = 0
        for h in hits:
            slug = get_slug(h)
            key = slug or json.dumps(h, sort_keys=True, ensure_ascii=False)

            if key not in seen:
                seen.add(key)
                all_hits.append(h)
                added += 1

        print(
            f"[search] page={page} hits={len(hits)} "
            f"added={added} total={len(all_hits)} "
            f"nbHits={nb_hits} nbPages={nb_pages}"
        )

        page += 1
        time.sleep(SLEEP_SEARCH)

        if nb_pages is not None and page >= nb_pages:
            break

    return all_hits


def fetch_details(session, build_id, slug, hit):
    """يجيب تفاصيل الكورس مع استخدام الـ cache."""
    # 1) جرّب من الـ cache الأول
    cached_data, cached_path = load_from_cache(slug)
    if cached_data is not None:
        return cached_data, cached_path, True  # True = from cache

    # 2) لو مش في الـ cache، اطلبه من الـ API
    paths = [
        get_path(hit, slug),
        f"/course/{slug}",
        f"/school/{slug}",
        f"/degree/{slug}",
    ]

    tried = set()
    last_error = None

    for path in paths:
        if not path or path in tried:
            continue

        tried.add(path)

        url = f"https://www.udacity.com/_next/data/{build_id}/default{path}.json"

        try:
            r = session.get(url, headers=HEADERS_NEXT, timeout=TIMEOUT)

            if r.status_code == 404:
                last_error = Exception(f"404: {url}")
                continue

            r.raise_for_status()
            data = r.json()
            save_to_cache(slug, data, path)  # 💾 احفظه في الـ cache
            return data, path, False  # False = fresh

        except Exception as e:
            last_error = e

    raise last_error


def get_price(hit, page, details):
    is_free = pick(
        hit.get("isFree"),
        hit.get("isProgramFree"),
        page.get("isFree"),
        page.get("isProgramFree"),
        details.get("isFree") if isinstance(details, dict) else None,
        details.get("isProgramFree") if isinstance(details, dict) else None,
    )

    return "Free" if is_free is True else None


def get_instructors(data, hit):
    names = []

    h = as_text(hit.get("instructors"))
    if h:
        names.append(h)

    for k, v in walk(data):
        if any(w in str(k).lower() for w in ["instructor", "mentor"]):
            t = as_text(v)
            if t:
                names.append(t)

    clean = []
    seen = set()

    for n in names:
        for part in str(n).split(","):
            part = part.strip()
            if part and part.lower() not in {"instructor", "mentor"} and part not in seen:
                seen.add(part)
                clean.append(part)

    return ", ".join(clean) if clean else None


def make_row(data, slug, hit, path):
    page = data.get("pageProps") or {}
    details = page.get("staticProgramDetailsSectionProps") or {}
    seo = page.get("seoProps") or {}
    summary = page.get("programSummary") or {}
    catalog = page.get("catalogProgramProps") or {}

    title = pick(
        hit.get("title"),
        hit.get("name"),
        page.get("title"),
        details.get("title") if isinstance(details, dict) else None,
        catalog.get("title") if isinstance(catalog, dict) else None,
        seo.get("title") if isinstance(seo, dict) else None,
    )

    course_id = pick(
        hit.get("key"),
        hit.get("id"),
        page.get("programKey"),
        page.get("programId"),
        page.get("courseId"),
        details.get("programKey") if isinstance(details, dict) else None,
        details.get("courseId") if isinstance(details, dict) else None,
        summary.get("key") if isinstance(summary, dict) else None,
        slug,
    )

    # ✅ استخدام get_skills الجديدة
    skills = get_skills(data, hit)

    review_count = pick(
        hit.get("reviewCount"),
        page.get("reviewCount"),
        details.get("reviewCount") if isinstance(details, dict) else None,
    )

    rating = pick(
        hit.get("reviewStarsAverage"),
        hit.get("rating"),
        page.get("reviewStarsAverage"),
        details.get("reviewStarsAverage") if isinstance(details, dict) else None,
    )

    if review_count is not None and rating is not None:
        reviews = f"{review_count} (avg {rating})"
    else:
        reviews = review_count

    description = pick(
        hit.get("description"),
        hit.get("summary"),
        page.get("description"),
        details.get("description") if isinstance(details, dict) else None,
        details.get("summary") if isinstance(details, dict) else None,
        seo.get("description") if isinstance(seo, dict) else None,
    )

    language = pick(
        hit.get("language"),
        hit.get("locale"),
        hit.get("lang"),
        page.get("language"),
        page.get("locale"),
        page.get("lang"),
        details.get("language") if isinstance(details, dict) else None,
        details.get("locale") if isinstance(details, dict) else None,
        seo.get("inLanguage") if isinstance(seo, dict) else None,
        summary.get("language") if isinstance(summary, dict) else None,
        find_value(data, ["language", "locale", "lang"]),
    )

    students = pick(
        hit.get("enrollment"),
        hit.get("enrollmentCount"),
        hit.get("studentCount"),
        hit.get("studentsEnrolled"),
        hit.get("learnerCount"),
        page.get("enrollmentCount"),
        page.get("studentCount"),
        page.get("studentsEnrolled"),
        page.get("learnerCount"),
        details.get("enrollmentCount") if isinstance(details, dict) else None,
        details.get("studentCount") if isinstance(details, dict) else None,
        summary.get("enrollmentCount") if isinstance(summary, dict) else None,
        summary.get("studentCount") if isinstance(summary, dict) else None,
        find_value(data, ["enroll", "student", "learner"]),
    )

    last_update = pick(
        hit.get("lastUpdated"),
        hit.get("updatedAt"),
        hit.get("lastModified"),
        page.get("lastUpdated"),
        page.get("updatedAt"),
        page.get("lastModified"),
        details.get("lastUpdated") if isinstance(details, dict) else None,
        details.get("updatedAt") if isinstance(details, dict) else None,
        summary.get("lastUpdated") if isinstance(summary, dict) else None,
        find_value(data, ["updated", "modified"]),
    )

    type_of_course = pick(
        hit.get("semanticType"),
        hit.get("type"),
        page.get("semanticType"),
        page.get("courseType"),
        details.get("semanticType") if isinstance(details, dict) else None,
        summary.get("semanticType") if isinstance(summary, dict) else None,
    )

    duration = pick(
        details.get("duration") if isinstance(details, dict) else None,
        summary.get("duration") if isinstance(summary, dict) else None,
        catalog.get("duration") if isinstance(catalog, dict) else None,
        page.get("duration"),
        hit.get("duration"),
    )

    return {
        "course_id": course_id,
        "Course_Title": title,
        "Course_URL": f"https://www.udacity.com{path}",
        "Platform": "Udacity",
        "Language": language,
        "Description": as_text(description),
        "Skill": skills,
        "Level": pick(
            hit.get("difficulty"),
            hit.get("level"),
            page.get("difficultyLevel"),
            details.get("difficulty") if isinstance(details, dict) else None,
            summary.get("difficultyLevel") if isinstance(summary, dict) else None,
        ),
        "Price": get_price(hit, page, details),
        "No. of Reviews / Ratings": reviews,
        "No. of Students enrolled": students,
        "Programming Instructor": get_instructors(data, hit),
        "Last Update": last_update,
        "Type of Course": type_of_course,
        "Duration": duration,
    }


def fallback_row(hit, slug):
    path = get_path(hit, slug)
    url = f"https://www.udacity.com{path}" if path.startswith("/") else path

    raw_skills = hit.get("skills") if isinstance(hit.get("skills"), list) else []
    clean_skills = [s for s in raw_skills if isinstance(s, str) and not is_taxonomy_id(s)]

    return {
        "course_id": pick(hit.get("key"), hit.get("id"), slug),
        "Course_Title": pick(hit.get("title"), hit.get("name")),
        "Course_URL": url,
        "Platform": "Udacity",
        "Language": pick(hit.get("language"), hit.get("locale"), hit.get("lang")),
        "Description": as_text(pick(hit.get("description"), hit.get("summary"))),
        "Skill": ", ".join(clean_skills) if clean_skills else None,
        "Level": pick(hit.get("difficulty"), hit.get("level")),
        "Price": "Free" if pick(hit.get("isFree"), hit.get("isProgramFree")) is True else None,
        "No. of Reviews / Ratings": pick(hit.get("reviewCount"), hit.get("rating")),
        "No. of Students enrolled": pick(
            hit.get("enrollment"),
            hit.get("enrollmentCount"),
            hit.get("studentCount"),
            hit.get("studentsEnrolled"),
            hit.get("learnerCount"),
        ),
        "Programming Instructor": as_text(hit.get("instructors")),
        "Last Update": pick(hit.get("lastUpdated"), hit.get("updatedAt"), hit.get("lastModified")),
        "Type of Course": pick(hit.get("semanticType"), hit.get("type")),
        "Duration": hit.get("duration"),
    }


# ============================================================
# 🆕 worker للـ Parallel processing
# ============================================================
def process_hit(hit, build_id):
    """يعالج كورس واحد (يستخدم session خاص بالـ thread)."""
    slug = get_slug(hit)
    if not slug:
        return None, "no-slug"

    # كل thread له session خاص
    session = requests.Session()

    try:
        data, path, from_cache = fetch_details(session, build_id, slug, hit)
        row = make_row(data, slug, hit, path)
        return row, "cache" if from_cache else "fresh"
    except Exception as e:
        safe_print(f"[FAIL] {slug} -> {e}")
        return fallback_row(hit, slug), "fallback"
    finally:
        session.close()


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)

    session = requests.Session()

    print("Getting buildId...")
    build_id = get_build_id(session)
    print("buildId:", build_id)

    print("Fetching catalog hits...")
    hits = get_all_hits(session)
    print("Total hits:", len(hits))

    rows = []
    stats = {"cache": 0, "fresh": 0, "fallback": 0, "no-slug": 0}
    total = len(hits)

    print(f"\\n🚀 Processing {total} courses with {MAX_WORKERS} parallel workers...\\n")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_hit, hit, build_id): i for i, hit in enumerate(hits)}

        completed = 0
        for future in as_completed(futures):
            completed += 1
            try:
                row, status = future.result()
                stats[status] = stats.get(status, 0) + 1
                if row is not None:
                    rows.append(row)
            except Exception as e:
                safe_print(f"[worker-error] {e}")

            if completed % 25 == 0 or completed == total:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                safe_print(
                    f"[progress] {completed}/{total} "
                    f"| cache={stats['cache']} fresh={stats['fresh']} "
                    f"fallback={stats['fallback']} "
                    f"| {rate:.1f} req/s | {elapsed:.1f}s elapsed"
                )

    elapsed = time.time() - start_time
    print(f"\\n✅ Done in {elapsed:.1f}s")
    print(f"   Cache hits: {stats['cache']}")
    print(f"   Fresh fetches: {stats['fresh']}")
    print(f"   Fallbacks: {stats['fallback']}")

    cols = [
        "course_id",
        "Course_Title",
        "Course_URL",
        "Platform",
        "Language",
        "Description",
        "Skill",
        "Level",
        "Price",
        "No. of Reviews / Ratings",
        "No. of Students enrolled",
        "Programming Instructor",
        "Last Update",
        "Type of Course",
        "Duration",
    ]

    df = pd.DataFrame(rows).drop_duplicates(subset=["Course_URL"], keep="first")

    for c in cols:
        if c not in df.columns:
            df[c] = None

    df = df[cols]
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    print(f"\\n💾 Saved: {len(df)} rows -> {OUT_CSV}")


if __name__ == "__main__":
    main()
