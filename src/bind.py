import click
import time
import schedule
import logging
import os
from src.core.scraper import AbmgScraper

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
@click.argument('term')
def search(term):
    """Search for a book and print results"""
    logger.info(f"Searching for: {term}")
    scraper = AbmgScraper()
    results = scraper.search(term)
    for res in results:
        click.echo(f"[+] Found: {res['title']} (Hash: {res['hash']})")

@cli.command()
@click.option('--interval', default=60, help='Check interval in minutes')
def daemon(interval):
    """Run in daemon mode to auto-grab new torrents"""
    logger.info(f"Starting BIND Daemon (Interval: {interval}m)")
    
    scraper = AbmgScraper()
    
    def job():
        logger.info("Checking for new uploads...")
        books = scraper.get_recent_books()
        logger.info(f"Found {len(books)} recent books.")
        
        for book in books:
            logger.info(f"Processing: {book['title']}")
            
            info_hash = scraper.extract_info_hash(book['link'])
            if info_hash:
                # Use centralized generator with full tracker list
                magnet = AbmgScraper.generate_magnet(info_hash, book['title'])
                logger.info(f"Generated Magnet: {magnet}")
                
                # Save to file (User Request)
                with open("magnets.txt", "a") as f:
                    f.write(f"{magnet}\n")
                logger.info("Saved to magnets.txt")
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
