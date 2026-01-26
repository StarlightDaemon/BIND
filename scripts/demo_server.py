"""
BIND Demo Server (No Working Mode)
Hosts the Starlight Carbon aligned Web UI with static demo data.
"""

import os
from flask import Flask, render_template

# Path configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')
TEMPLATE_DIR = os.path.join(SRC_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)

# Mock Data (Starlight Carbon Themed)
DEMO_MAGNETS = [
    {
        'title': 'Starlight Carbon: Design Systems for Agents (Audiobook)',
        'hash': '460D081A237189F739BACBFC0F1C9C30ADCAAB9FED927AA2A90B7B4891AFC05B',
        'magnet': 'magnet:?xt=urn:btih:460d081a237189f739bacbfc0f1c9c30adcaab9fed927aa2a90b7b4891afc05b&dn=Starlight%20Carbon'
    },
    {
        'title': 'Governance Kit v1.0.0 Deployment Handbook',
        'hash': 'B3921E94A7B82C1D0F32E410A8C5B92D73F1A02C',
        'magnet': 'magnet:?xt=urn:btih:b3921e94a7b82c1d0f32e410a8c5b92d73f1a02c&dn=Governance%20Kit'
    },
    {
        'title': 'The Hex Hunter: A Field Guide to Forensic Auditing',
        'hash': 'C8212A34F5B6E7D8C9A0B1C2D3E4F5A6B7C8D9E0',
        'magnet': 'magnet:?xt=urn:btih:c8212a34f5b6e7d8c9a0b1c2d3e4f5a6b7c8d9e0&dn=Hex%20Hunter'
    }
]

@app.route('/')
def index():
    return render_template(
        'index.html',
        magnets=DEMO_MAGNETS,
        magnet_count=1242,
        display_count=len(DEMO_MAGNETS)
    )

if __name__ == '__main__':
    port = 5051
    print(f"--- BIND DEMO MODE ---")
    print(f"Review UI at: http://localhost:{port}/")
    app.run(host='0.0.0.0', port=port, debug=False)
