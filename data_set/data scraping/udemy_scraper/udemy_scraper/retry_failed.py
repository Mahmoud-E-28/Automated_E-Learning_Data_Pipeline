import re
import time
import logging
import pandas as pd
from pathlib import Path
from curl_cffi import requests as curl_requests
from config import HEADERS, COURSE_DETAIL_FIELDS, COURSE_DETAILS_URL, OUTPUT_CSV

# إعدادات اللوج
LOG_FILE = "logs/scraper.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("logs/retry_script.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RetryScript")

session = curl_requests.Session(impersonate="chrome120")
session.headers.update(HEADERS)

def extract_failed_ids(log_path):
    """استخراج IDs الكورسات اللي فشلت من اللوج"""
    failed_ids = set()
    pattern = r'All retries failed: .*api-2.0/courses/(\d+)/'
    
    if not Path(log_path).exists():
        logger.error(f"Log file not found: {log_path}")
        return []

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.search(pattern, line)
            if match:
                failed_ids.add(match.group(1))
                
    return list(failed_ids)

def smart_request(course_id):
    """طلب الداتا مع Exponential Backoff"""
    url = COURSE_DETAILS_URL.format(course_id=course_id)
    params = {"fields[course]": COURSE_DETAIL_FIELDS}
    
    max_retries = 5
    base_delay = 2

    for attempt in range(max_retries):
        try:
            response = session.get(url, params=params, timeout=25)
            status = response.status_code

            if status == 200:
                return response.json()
            elif status == 404:
                logger.warning(f"Course {course_id} is 404. Skipping.")
                return None
            elif status in [403, 429]:
                wait_time = 45 * (attempt + 1)
                logger.warning(f"Rate limited (Status {status}) on {course_id}. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            elif status in [500, 502, 503]:
                wait_time = base_delay * (2 ** attempt)
                logger.warning(f"Server error {status} on {course_id}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                response.raise_for_status()

        except Exception as e:
            wait_time = base_delay * (2 ** attempt)
            logger.error(f"Attempt {attempt+1} failed for {course_id}: {str(e)[:100]}")
            time.sleep(wait_time)

    return None

def run_recovery():
    logger.info("🚀 Starting Recovery Process...")
    
    failed_ids = extract_failed_ids(LOG_FILE)
    if not failed_ids:
        logger.info("✅ No failed REST API courses found in logs.")
        return

    if not Path(OUTPUT_CSV).exists():
        logger.error(f"❌ Main CSV not found: {OUTPUT_CSV}")
        return

    # 1. قراءة الملف الأساسي
    logger.info(f"📂 Loading main CSV: {OUTPUT_CSV}")
    df = pd.read_csv(OUTPUT_CSV)
    df.columns = df.columns.str.strip() # تنظيف الأسماء

    # 2. تعيين أسماء الأعمدة بناءً على ملفك الفعلي
    id_col = 'course_id'  # ده اللي شغال في ملفك
    df[id_col] = df[id_col].astype(str)
    
    # 3. فلترة الـ IDs
    valid_ids = [cid for cid in failed_ids if cid in df[id_col].values]
    
    logger.info(f"🎯 Found {len(valid_ids)} courses to fix in CSV. Starting...")
    
    updated_count = 0
    
    for idx, cid in enumerate(valid_ids):
        logger.info(f"🔄 Processing [{idx+1}/{len(valid_ids)}] - ID: {cid}")
        data = smart_request(cid)
        
        if data:
            try:
                # تجهيز البيانات بأسماء الحقول اللي يوديمي بيبعتها
                topics_data = data.get('topics', [])
                skills_str = ', '.join([t.get('title', '') for t in topics_data]) if isinstance(topics_data, list) else ""
                
                # إيجاد الصف الصحيح في الشيت
                row_idx = df.index[df[id_col] == cid].tolist()[0]
                
                # تحديث الأعمدة بناءً على الـ Structure بتاعك
                # أنا استخدمت الأسماء اللي ظهرت في الـ Terminal عندك (Description, Skills, etc.)
                df.at[row_idx, 'Description'] = data.get('description', '')
                df.at[row_idx, 'Skills']      = skills_str
                df.at[row_idx, 'Level']       = data.get('instructional_level', '')
                
                # تحديث عدد الطلاب لو فاضي
                df.at[row_idx, 'No_of_Students_enrolled'] = data.get('num_subscribers', 0)

                updated_count += 1
                
                # Save Progress كل 10 صفوف
                if updated_count % 10 == 0:
                    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
                    logger.info(f"💾 Checkpoint: {updated_count} rows updated and saved.")
            
            except Exception as ex:
                logger.error(f"❌ Error updating row for ID {cid}: {ex}")

        time.sleep(1.5) # هدوء عشان الـ Block
        
    if updated_count > 0:
        df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        logger.info(f"🎉 SUCCESS! Total records fixed: {updated_count}")
    else:
        logger.info("ℹ️ No records were updated.")

if __name__ == "__main__":
    run_recovery()