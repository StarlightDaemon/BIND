
import json
import hashlib
import os
import subprocess
import re
from datetime import datetime

# Configuration
PROJECT_ROOT = "../.."  # Relative to scripts/governance
VALIDATOR_DIR = "."
OUTPUT_FILE = "compliance-evidence.json"

def run_validator():
    """Run the TypeScript validator and return the output."""
    try:
        result = subprocess.run(
            ["npm", "run", "validate"], 
            cwd=VALIDATOR_DIR, 
            capture_output=True, 
            text=True, 
            check=False
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def scan_tokens(root_dir):
    """Scan HTML/CSS/JS files for Starlight token usage."""
    token_usage = []
    token_pattern = re.compile(r'var\(--([a-zA-Z0-9-]+)\)')
    
    for subdir, dirs, files in os.walk(root_dir):
        if 'node_modules' in subdir or 'venv' in subdir or '.git' in subdir:
            continue
            
        for file in files:
            if file.endswith(('.html', '.css', '.js')):
                filepath = os.path.join(subdir, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = token_pattern.findall(content)
                        for match in matches:
                            token_usage.append({
                                "file": os.path.relpath(filepath, root_dir),
                                "token": match
                            })
                except Exception:
                    pass
    return token_usage

def calculate_structure_digest(root_dir):
    """Calculate a hash of the directory structure."""
    file_list = []
    for subdir, dirs, files in os.walk(root_dir):
        if 'node_modules' in subdir or 'venv' in subdir or '.git' in subdir or '__pycache__' in subdir:
            continue
        for file in files:
            file_list.append(os.path.relpath(os.path.join(subdir, file), root_dir))
    
    file_list.sort()
    manifest = "\n".join(file_list).encode('utf-8')
    return hashlib.sha256(manifest).hexdigest()

def main():
    print(f"🔍 Starting Audit Collection...")
    
    # 1. Run Validator
    print("Running Governance Validator...")
    validator_result = run_validator()
    
    # 2. Scan Tokens
    abs_root = os.path.abspath(PROJECT_ROOT)
    print(f"Scanning codebase at {abs_root}...")
    token_usage = scan_tokens(abs_root)
    
    # 3. Structure Digest
    digest = calculate_structure_digest(abs_root)
    
    # 4. Generate Bundle
    evidence = {
        "meta": {
            "auditor": "Agent (Builder)",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "generator": "custom-collect_audit.py"
        },
        "dependency_manifest": {
            "framework": "flask (python)",
            "design_system": "starlight-governance-kit (manual injection)"
        },
        "calculated_token_usage": {
            "total_references": len(token_usage),
            "sample": token_usage[:10]  # First 10 for brevity
        },
        "validator_receipt": {
            "passed": validator_result["success"],
            "log": validator_result["stdout"][-500:] if validator_result["stdout"] else "" # Last 500 chars
        },
        "structure_digest": digest
    }
    
    # Write to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(evidence, f, indent=2)
        
    print(f"✅ Evidence generated at {os.path.abspath(OUTPUT_FILE)}")
    # Print for the user to copy
    print("\n--- EVIDENCE BUNDLE START ---")
    print(json.dumps(evidence, indent=2))
    print("--- EVIDENCE BUNDLE END ---\n")

if __name__ == "__main__":
    main()
