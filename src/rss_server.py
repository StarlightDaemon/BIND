"""
BIND RSS Feed Server

Lightweight Flask server that reads magnets.txt and serves it as:
- RSS 2.0 feed at /feed.xml
- Simple web UI at /
- Health check at /health
"""

from flask import Flask, Response, render_template_string, request
from datetime import datetime
import os
from typing import List, Dict
import re
import glob
import fcntl
from xml.sax.saxutils import escape

app = Flask(__name__)

# Configuration
MAGNETS_DIR = os.getenv('MAGNETS_DIR', 'magnets')
FEED_TITLE = "BIND - Book Indexing Network"
FEED_DESCRIPTION = "Automatically collected audiobook magnet links"
MAX_ITEMS = 100


def parse_magnet_link(magnet_url: str) -> Dict[str, str]:
    """
    Extract information from a magnet link.
    Returns dict with hash, title, and trackers.
    """
    info = {
        'magnet': magnet_url,
        'hash': '',
        'title': 'Unknown',
        'trackers': []
    }
    
    # Extract info hash
    hash_match = re.search(r'urn:btih:([a-fA-F0-9]+)', magnet_url)
    if hash_match:
        info['hash'] = hash_match.group(1)
    
    # Extract display name
    dn_match = re.search(r'[&?]dn=([^&]+)', magnet_url)
    if dn_match:
        # Decode URL encoding (e.g., %3A → :, %2C → ,, %E2%80%99 → ')
        from urllib.parse import unquote_plus
        info['title'] = unquote_plus(dn_match.group(1))
    
    # Extract trackers
    trackers = re.findall(r'[&?]tr=([^&]+)', magnet_url)
    info['trackers'] = trackers
    
    return info


def read_magnets() -> List[Dict[str, str]]:
    """
    Read magnets from all date-based files in magnets directory.
    Returns list of magnet info dicts, most recent first.
    """
    magnets = []
    
    # Create directory if it doesn't exist
    os.makedirs(MAGNETS_DIR, exist_ok=True)
    
    # Find all magnet files (magnets_YYYY-MM-DD.txt)
    magnet_files = glob.glob(os.path.join(MAGNETS_DIR, 'magnets_*.txt'))
    
    # Sort by filename (date) descending
    magnet_files.sort(reverse=True)
    
    try:
        for file_path in magnet_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Acquire shared lock to prevent reading partial writes from daemon
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    lines = f.readlines()
                finally:
                    # Release lock (also auto-released on file close)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            for line in lines:
                line = line.strip()
                if line and line.startswith('magnet:'):
                    magnet_info = parse_magnet_link(line)
                    magnets.append(magnet_info)
                    
                    # Limit to MAX_ITEMS
                    if len(magnets) >= MAX_ITEMS:
                        return magnets
        
        return magnets
    
    except Exception as e:
        print(f"Error reading magnet files: {e}")
        return []


@app.route('/')
def index():
    """Simple web UI showing recent magnet links"""
    magnets = read_magnets()
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BIND - Magnet Links</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            /*!
             * Vesper UI Design System v1.0
             * For BIND Web UI Implementation
             */

            /* ============================================
               CSS VARIABLES
               ============================================ */
            :root {
              /* Colors - Neutrals */
              --white: #ffffff;
              --gray-50: #f5f7f9;
              --gray-100: #e1e8ed;
              --gray-400: #636e72;
              --gray-700: #2d3436;
              --black: #000000;

              /* Colors - Brand */
              --primary: #06a0ff;
              --primary-dark: #0087d2;

              /* Colors - Status */
              --success: #1b5e20;
              --success-light: #a5d6a7;
              --error: #c62828;
              --warning: #f57c00;
              --info: #0277bd;

              /* Semantic Mapping */
              --bg: var(--gray-50);
              --bg-secondary: var(--white);
              --text: var(--gray-700);
              --text-secondary: var(--gray-400);
              --border: var(--gray-100);
              --accent: var(--primary);
              --accent-hover: var(--primary-dark);

              /* Typography */
              --font-primary: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
              --font-mono: 'SF Mono', Consolas, 'Courier New', monospace;
              --text-xs: 0.75rem;
              --text-sm: 0.875rem;
              --text-base: 1rem;
              --text-lg: 1.125rem;
              --text-xl: 1.25rem;
              --text-2xl: 1.75rem;
              --text-3xl: 2rem;
              --font-normal: 400;
              --font-medium: 500;
              --font-semibold: 600;
              --font-bold: 700;

              /* Spacing (8px scale) */
              --space-1: 0.25rem;
              --space-2: 0.5rem;
              --space-3: 0.75rem;
              --space-4: 1rem;
              --space-5: 1.25rem;
              --space-6: 1.5rem;
              --space-8: 2rem;
              --space-10: 2.5rem;
              --space-12: 3rem;

              /* Border Radius */
              --radius-sm: 6px;
              --radius-md: 12px;
              --radius-lg: 16px;
              --radius-xl: 24px;
              --radius-full: 9999px;

              /* Shadows */
              --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06);
              --shadow-md: 0 2px 6px rgba(0, 0, 0, 0.08);
              --shadow-lg: 0 4px 12px rgba(0, 0, 0, 0.1);
              --shadow-xl: 0 12px 32px rgba(0, 0, 0, 0.18);

              /* Animation */
              --ease-standard: cubic-bezier(0.4, 0.0, 0.2, 1);
              --ease-out: cubic-bezier(0.0, 0.0, 0.2, 1);
              --ease-in: cubic-bezier(0.4, 0.0, 1, 1);
            }

            /* ============================================
               BASE RESET
               ============================================ */
            * {
              box-sizing: border-box;
              margin: 0;
              padding: 0;
            }

            body {
              font-family: var(--font-primary);
              background: var(--bg);
              color: var(--text);
              line-height: 1.6;
              -webkit-font-smoothing: antialiased;
              padding: var(--space-8) 0;
            }

            /* ============================================
               LAYOUT
               ============================================ */
            .container {
              max-width: 960px;
              margin: 0 auto;
              padding: 0 var(--space-6);
            }

            .container-lg {
              max-width: 1200px;
              margin: 0 auto;
              padding: 0 var(--space-6);
            }

            /* ============================================
               GRIDS
               ============================================ */
            .grid-auto {
              display: grid;
              grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
              gap: var(--space-6);
            }

            @media (max-width: 640px) {
              .grid-auto {
                grid-template-columns: 1fr;
              }
            }

            .grid-2 { 
              display: grid;
              grid-template-columns: repeat(2, 1fr); 
              gap: var(--space-6);
            }

            @media (max-width: 640px) {
              .grid-2 {
                grid-template-columns: 1fr;
              }
            }

            .grid-3 { 
              display: grid;
              grid-template-columns: repeat(3, 1fr); 
              gap: var(--space-6);
            }

            /* ============================================
               BUTTONS
               ============================================ */
            .btn {
              padding: var(--space-2) var(--space-4);
              border-radius: var(--radius-md);
              font-weight: var(--font-semibold);
              font-size: var(--text-base);
              font-family: var(--font-primary);
              border: none;
              cursor: pointer;
              transition: all 0.2s var(--ease-standard);
              display: inline-block;
              text-decoration: none;
              text-align: center;
            }

            .btn-primary {
              background: var(--accent);
              color: var(--white);
            }

            .btn-primary:hover {
              background: var(--accent-hover);
            }

            .btn-sm {
              padding: var(--space-1) var(--space-3);
              font-size: var(--text-sm);
            }

            .btn:disabled {
              opacity: 0.5;
              cursor: not-allowed;
            }

            /* ============================================
               CARDS
               ============================================ */
            .card {
              background: var(--white);
              border: 1px solid var(--border);
              border-radius: var(--radius-md);
              padding: var(--space-6);
              transition: all 0.2s var(--ease-standard);
            }

            .card:hover {
              border-color: var(--accent);
              transform: translateY(-2px);
              box-shadow: var(--shadow-md);
            }

            .card-compact {
              padding: var(--space-4) var(--space-5);
            }
        </style>
    </head>
    <body>
        <div class="container-lg">
            <div style="margin-bottom: var(--space-8);">
                <h1 style="color: var(--text); font-size: var(--text-3xl); margin-bottom: var(--space-2); font-weight: var(--font-bold);">
                    📚 BIND - Book Indexing Network Daemon
                </h1>
                <p style="color: var(--text-secondary); font-size: var(--text-base);">
                    Automatically collected audiobook magnet links
                </p>
            </div>
            
            <div class="grid-2" style="margin-bottom: var(--space-8);">
                <div class="card card-compact" style="text-align: center;">
                    <div style="font-size: var(--text-3xl); font-weight: var(--font-bold); color: var(--accent);">
                        {{ magnet_count }}
                    </div>
                    <div style="font-size: var(--text-xs); color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; margin-top: var(--space-2);">
                        Total Magnets
                    </div>
                </div>
                <div class="card card-compact" style="text-align: center;">
                    <div style="font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--success);">
                        ✓ RSS
                    </div>
                    <div style="font-size: var(--text-xs); color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; margin-top: var(--space-2);">
                        Feed Available
                    </div>
                </div>
            </div>
            
            <a href="/feed.xml" class="btn btn-primary" style="margin-bottom: var(--space-8);">📡 Subscribe to RSS Feed</a>
            
            {% if magnets %}
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: var(--space-6);">
                <h2 style="color: var(--text); font-size: var(--text-2xl); font-weight: var(--font-semibold); margin: 0;">
                    Recent Magnets
                </h2>
                {% if display_count < magnet_count %}
                <p style="color: var(--text-secondary); font-size: var(--text-sm); margin: 0;">
                    Showing {{ display_count }} of {{ magnet_count }} • <a href="/feed.xml" style="color: var(--accent); text-decoration: none;">View all in RSS →</a>
                </p>
                {% endif %}
            </div>
            <div class="grid-auto">
                {% for magnet in magnets %}
                <div class="card">
                    <h3 style="margin-bottom: var(--space-2); color: var(--text); font-size: var(--text-lg); font-weight: var(--font-semibold);">
                        {{ magnet.title }}
                    </h3>
                    <code style="display: block; margin-bottom: var(--space-4); font-size: var(--text-xs); color: var(--text-secondary); font-family: var(--font-mono); background: var(--gray-50); padding: var(--space-2); border-radius: var(--radius-sm); word-break: break-all;">
                        {{ magnet.hash }}
                    </code>
                    <a href="{{ magnet.magnet }}" class="btn btn-primary btn-sm">
                        Open Magnet Link
                    </a>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="card" style="text-align: center; padding: var(--space-12);">
                <h2 style="color: var(--text-secondary); margin-bottom: var(--space-4); font-size: var(--text-xl);">
                    No magnet links yet
                </h2>
                <p style="color: var(--text-secondary); font-size: var(--text-base);">
                    The daemon will start collecting links soon...
                </p>
            </div>
            {% endif %}
        </div>
    </body>
    </html>
    """
    
    # Limit display to 20 most recent magnets
    display_magnets = magnets[:20]
    total_count = len(magnets)
    
    return render_template_string(html, 
                                 magnets=display_magnets, 
                                 magnet_count=total_count,
                                 display_count=len(display_magnets))


@app.route('/feed.xml')
def feed():
    """RSS 2.0 feed of magnet links"""
    magnets = read_magnets()
    
    # Get base URL - auto-detect from request or use env override
    base_url = os.getenv('BASE_URL')
    if not base_url:
        # Auto-detect from incoming request (works in Proxmox LXC, Docker, localhost)
        base_url = f"http://{request.host}"
    
    # Build RSS 2.0 XML
    rss_items = []
    for magnet in magnets:
        pub_date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        guid = magnet['hash']
        
        # Properly escape magnet link for XML (handles &, <, >, ", ')
        magnet_escaped = escape(magnet['magnet'])
        
        # Escape ]]> in CDATA content to prevent breaking CDATA block
        title_safe = magnet['title'].replace(']]>', ']]]]><![CDATA[>')
        
        item = f"""
        <item>
            <title><![CDATA[{title_safe}]]></title>
            <link>{magnet_escaped}</link>
            <guid isPermaLink="false">{guid}</guid>
            <pubDate>{pub_date}</pubDate>
            <description><![CDATA[Magnet link for: {title_safe}]]></description>
            <enclosure url="{magnet_escaped}" type="application/x-bittorrent" />
        </item>
        """
        rss_items.append(item.strip())
    
    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
        <title>{FEED_TITLE}</title>
        <link>{base_url}</link>
        <description>{FEED_DESCRIPTION}</description>
        <language>en-us</language>
        <lastBuildDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</lastBuildDate>
        <atom:link href="{base_url}/feed.xml" rel="self" type="application/rss+xml" />
        
        {''.join(rss_items)}
    </channel>
</rss>
"""
    
    return Response(rss_xml, mimetype='application/rss+xml')


@app.route('/health')
def health():
    """Health check endpoint"""
    magnets = read_magnets()
    
    # Get list of magnet files for stats (sorted by date, newest first)
    magnet_files = sorted(glob.glob(os.path.join(MAGNETS_DIR, 'magnets_*.txt')), reverse=True)
    
    # Safely get latest file (defensive against empty list)
    latest_file = None
    if magnet_files:
        latest_file = os.path.basename(magnet_files[0])
    
    return {
        'status': 'ok',
        'magnet_count': len(magnets),
        'magnets_dir': MAGNETS_DIR,
        'magnet_files_count': len(magnet_files),
        'latest_file': latest_file
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    print(f"Starting BIND RSS Server on {host}:{port}")
    print(f"RSS Feed: http://{host}:{port}/feed.xml")
    print(f"Web UI: http://{host}:{port}/")
    
    app.run(host=host, port=port, debug=False)
