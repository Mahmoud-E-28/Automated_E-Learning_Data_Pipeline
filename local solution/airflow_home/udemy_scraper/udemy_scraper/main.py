
import signal
import sys
import logging
from pathlib import Path

from config import LOG_FILE, MAIN_CATEGORIES, STATE_FILE
from scraper import scrape_filter
from state import State


_state_global = None


def setup_logging():
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def signal_handler(sig, frame):
    """Graceful shutdown - يحفظ الـ state ويخرج"""
    print("\n\n🛑 Interrupted! Saving state...")
    if _state_global:
        _state_global.save()
        stats = _state_global.stats()
        print(f"💾 Saved! Total scraped so far: {stats['total_seen']:,} courses")
        print(f"📂 Completed filters: {stats['completed_filters']}")
    print("✅ Safe to exit. Run again to resume.")
    sys.exit(0)


def main():
    global _state_global
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("=" * 60)
    logger.info("🚀 Udemy Scraper Started")
    logger.info("=" * 60)
    
   
    state = State(STATE_FILE)
    _state_global = state
    
    initial_stats = state.stats()
    if initial_stats["total_seen"] > 0:
        logger.info(f"♻️  Resuming. Already have {initial_stats['total_seen']:,} courses")
    
   
    total = 0
    for category_name, page_id in MAIN_CATEGORIES.items():
        logger.info(f"\n{'=' * 60}")
        logger.info(f"📁 Starting Category: {category_name}")
        logger.info(f"{'=' * 60}")
        
        try:
            count = scrape_filter(
                filters={"pageId": page_id},
                label=category_name,
                state=state
            )
            total += count
        except Exception as e:
            logger.error(f"❌ Error in {category_name}: {e}")
            state.save()
            continue
    
    # Final save
    state.save()
    
    final_stats = state.stats()
    logger.info("=" * 60)
    logger.info(f"🏁 Done! Total unique courses: {final_stats['total_seen']:,}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()