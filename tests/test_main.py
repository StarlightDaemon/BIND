import subprocess, sys

def test_main_module_is_importable():
    # Import the module to get coverage on the import statement
    import src.__main__
    
    result = subprocess.run(
        [sys.executable, "-m", "src", "--help"],
        capture_output=True, text=True, cwd="/mnt/e/BIND"
    )
    assert result.returncode == 0
    assert "BIND" in result.stdout or "Usage" in result.stdout
