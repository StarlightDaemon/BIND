"""
ABMG RSS Feed Server

Lightweight Flask server that reads magnets.txt and serves it as:
- RSS 2.0 feed at /feed.xml
- Simple web UI at /
- Health check at /health
"""

from flask import Flask, Response, render_template_string
from datetime import datetime
import os
from typing import List, Dict
import re

app = Flask(__name__)

# Configuration
MAGNETS_FILE = os.getenv('MAGNETS_FILE', 'magnets.txt')
FEED_TITLE = "ABMG - AudioBookBay Magnets"
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
        info['title'] = dn_match.group(1).replace('+', ' ')
    
    # Extract trackers
    trackers = re.findall(r'[&?]tr=([^&]+)', magnet_url)
    info['trackers'] = trackers
    
    return info


def read_magnets() -> List[Dict[str, str]]:
    """
    Read magnets from magnets.txt and parse them.
    Returns list of magnet info dicts.
    """
    magnets = []
    
    if not os.path.exists(MAGNETS_FILE):
        return magnets
    
    try:
        with open(MAGNETS_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if line and line.startswith('magnet:'):
                magnet_info = parse_magnet_link(line)
                magnets.append(magnet_info)
        
        # Return most recent first, limit to MAX_ITEMS
        return magnets[-MAX_ITEMS:][::-1]
    
    except Exception as e:
        print(f"Error reading magnets file: {e}")
        return []


@app.route('/')
def index():
    """Simple web UI showing recent magnet links"""
    magnets = read_magnets()
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ABMG - Magnet Links</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                padding: 30px;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 32px;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 14px;
            }
            .stats {
                display: flex;
                gap: 20px;
                margin-bottom: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
            }
            .stat-box {
                flex: 1;
                text-align: center;
            }
            .stat-value {
                font-size: 32px;
                font-weight: bold;
                color: #667eea;
            }
            .stat-label {
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .magnet-list {
                list-style: none;
            }
            .magnet-item {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
                transition: all 0.3s;
            }
            .magnet-item:hover {
                border-color: #667eea;
                box-shadow: 0 4px 12px rgba(102,126,234,0.15);
            }
            .magnet-title {
                font-size: 16px;
                font-weight: 600;
                color: #333;
                margin-bottom: 8px;
            }
            .magnet-hash {
                font-family: 'Courier New', monospace;
                font-size: 12px;
                color: #666;
                background: #f5f5f5;
                padding: 4px 8px;
                border-radius: 4px;
                display: inline-block;
            }
            .magnet-link {
                display: inline-block;
                margin-top: 10px;
                padding: 8px 16px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-size: 13px;
                transition: background 0.3s;
            }
            .magnet-link:hover {
                background: #764ba2;
            }
            .rss-link {
                display: inline-block;
                margin-top: 20px;
                padding: 12px 24px;
                background: #28a745;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
            }
            .rss-link:hover {
                background: #218838;
            }
            .empty-state {
                text-align: center;
                padding: 60px 20px;
                color: #999;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧲 ABMG - AudioBookBay Magnet Grabber</h1>
            <p class="subtitle">Automatically collected audiobook magnet links</p>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value">{{ magnet_count }}</div>
                    <div class="stat-label">Total Magnets</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">RSS</div>
                    <div class="stat-label">Feed Available</div>
                </div>
            </div>
            
            <a href="/feed.xml" class="rss-link">📡 Subscribe to RSS Feed</a>
            
            {% if magnets %}
            <h2 style="margin: 30px 0 15px 0; color: #333;">Recent Magnets</h2>
            <ul class="magnet-list">
                {% for magnet in magnets %}
                <li class="magnet-item">
                    <div class="magnet-title">{{ magnet.title }}</div>
                    <div class="magnet-hash">{{ magnet.hash }}</div>
                    <a href="{{ magnet.magnet }}" class="magnet-link">Open Magnet Link</a>
                </li>
                {% endfor %}
            </ul>
            {% else %}
            <div class="empty-state">
                <h2>No magnet links yet</h2>
                <p>The daemon will start collecting links soon...</p>
            </div>
            {% endif %}
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html, magnets=magnets, magnet_count=len(magnets))


@app.route('/feed.xml')
def feed():
    """RSS 2.0 feed of magnet links"""
    magnets = read_magnets()
    
    # Build RSS 2.0 XML
    rss_items = []
    for magnet in magnets:
        pub_date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        guid = magnet['hash']
        
        item = f"""
        <item>
            <title><![CDATA[{magnet['title']}]]></title>
            <link>{magnet['magnet']}</link>
            <guid isPermaLink="false">{guid}</guid>
            <pubDate>{pub_date}</pubDate>
            <description><![CDATA[Magnet link for: {magnet['title']}]]></description>
            <enclosure url="{magnet['magnet']}" type="application/x-bittorrent" />
        </item>
        """
        rss_items.append(item.strip())
    
    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
        <title>{FEED_TITLE}</title>
        <link>http://localhost:5000</link>
        <description>{FEED_DESCRIPTION}</description>
        <language>en-us</language>
        <lastBuildDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</lastBuildDate>
        <atom:link href="http://localhost:5000/feed.xml" rel="self" type="application/rss+xml" />
        
        {''.join(rss_items)}
    </channel>
</rss>
"""
    
    return Response(rss_xml, mimetype='application/rss+xml')


@app.route('/health')
def health():
    """Health check endpoint"""
    magnets = read_magnets()
    return {
        'status': 'ok',
        'magnet_count': len(magnets),
        'magnets_file': MAGNETS_FILE,
        'magnets_file_exists': os.path.exists(MAGNETS_FILE)
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    print(f"Starting ABMG RSS Server on {host}:{port}")
    print(f"RSS Feed: http://{host}:{port}/feed.xml")
    print(f"Web UI: http://{host}:{port}/")
    
    app.run(host=host, port=port, debug=False)
