import click
import time
import schedule
import logging
import os
from datetime import datetime
from src.core.scraper import BindScraper

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BIND")

@click.group()
def cli():
    """Book Indexing Network Daemon (BIND)"""
    pass

@cli.command()
@click.option('--interval', default=60, help='Check interval in minutes')
@click.option('--output-dir', default='magnets', help='Directory to store magnet files')
def daemon(interval, output_dir):
    """Run in daemon mode to auto-grab new torrents"""
    logger.info(f"Starting BIND Daemon (Interval: {interval}m)")
    logger.info(f"Output directory: {output_dir}/")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    scraper = BindScraper()
    
    def job():
        logger.info("Checking for new uploads...")
        books = scraper.get_recent_books()
        logger.info(f"Found {len(books)} recent books.")
        
        # Date-based filename for daily rotation
        today = datetime.now().strftime('%Y-%m-%d')
        magnet_file = os.path.join(output_dir, f'magnets_{today}.txt')
        
        for book in books:
            logger.info(f"Processing: {book['title']}")
            
            info_hash = scraper.extract_info_hash(book['link'])
            if info_hash:
                # Use centralized generator with full tracker list
                magnet = BindScraper.generate_magnet(info_hash, book['title'])
                logger.info(f"Generated Magnet: {magnet}")
                
                # Save to date-based file
                with open(magnet_file, "a", encoding='utf-8') as f:
                    f.write(f"{magnet}\n")
                logger.info(f"Saved to {magnet_file}")
            else:
                logger.warning(f"Failed to extract hash for {book['title']}")

    schedule.every(interval).minutes.do(job)
    
    # Run once immediately
    job()
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    cli()
