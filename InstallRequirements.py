import os
import subprocess
import sys
import re
from importlib.metadata import distributions, version, PackageNotFoundError

def get_installed_packages():
    """Get a dict of installed packages and their versions."""
    try:
        return {dist.metadata['Name'].lower(): dist.version for dist in distributions()}
    except Exception as e:
        print(f"Warning: Could not read installed packages: {e}")
        return {}

def parse_requirement_line(line):
    """Parse a single requirement line and extract package name and version spec."""
    line = line.strip()
    
    # Skip empty lines, comments, and URLs
    if not line or line.startswith('#') or line.startswith('http'):
        return None
    
    # Handle package[extras] format
    package_part = line.split('[')[0] if '[' in line else line
    
    # Extract package name and version specifier
    match = re.match(r'^([a-zA-Z0-9_-]+)(.*)', package_part)
    if match:
        package_name = match.group(1).lower().replace('_', '-')
        version_spec = match.group(2).strip()
        return {
            'name': package_name,
            'spec': line,
            'version_spec': version_spec
        }
    return None

def parse_requirements(requirements_path):
    """Parse requirements.txt and return list of package info."""
    packages = []
    try:
        with open(requirements_path, 'r', encoding='utf-8') as f:
            for line in f:
                parsed = parse_requirement_line(line)
                if parsed:
                    packages.append(parsed)
    except Exception as e:
        print(f"Error reading requirements.txt: {e}")
        return []
    return packages

def is_package_satisfied(package_info, installed_packages):
    """Check if a package requirement is satisfied."""
    pkg_name = package_info['name']
    version_spec = package_info['version_spec']
    
    # Check if package is installed
    if pkg_name not in installed_packages:
        return False
    
    # If no version specified, package is installed so it's satisfied
    if not version_spec or version_spec.startswith('['):
        return True
    
    # For version specs, we'll let pip handle the complexity
    # Only skip if exact version match (==)
    if version_spec.startswith('=='):
        required_version = version_spec.replace('==', '').strip()
        installed_version = installed_packages[pkg_name]
        return installed_version == required_version
    
    # For other operators (>=, <=, ~=, etc.), let pip verify
    # This is safer than trying to implement version comparison
    return False

def check_requirements_satisfied(required_packages, installed_packages):
    """Check which packages need to be installed."""
    packages_to_install = []
    
    for pkg_info in required_packages:
        if not is_package_satisfied(pkg_info, installed_packages):
            packages_to_install.append(pkg_info['spec'])
    
    return packages_to_install

def install_packages(packages_to_install):
    """Install packages using pip with optimized flags."""
    if not packages_to_install:
        return True
    
    # Create a temporary requirements file for missing packages
    temp_req_file = None
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_req_file = f.name
            f.write('\n'.join(packages_to_install))
        
        print(f"Installing {len(packages_to_install)} package(s)...")
        
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            "-q",  # Quiet mode
            "-r", temp_req_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return True
        else:
            # If quiet install fails, try verbose to show errors
            print("Error occurred. Retrying with detailed output...")
            cmd_verbose = [
                sys.executable, "-m", "pip", "install",
                "--disable-pip-version-check",
                "-r", temp_req_file
            ]
            result = subprocess.run(cmd_verbose)
            return result.returncode == 0
            
    except Exception as e:
        print(f"Error during installation: {e}")
        return False
    finally:
        # Clean up temp file
        if temp_req_file and os.path.exists(temp_req_file):
            try:
                os.remove(temp_req_file)
            except:
                pass

def install_requirements_fallback(requirements_path):
    """Fallback method: direct pip install from requirements.txt."""
    print("Using fallback installation method...")
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--disable-pip-version-check",
        "-r", requirements_path
    ]
    result = subprocess.run(cmd)
    return result.returncode == 0

def install_requirements():
    """Install requirements with speed optimization and compatibility fallback."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    requirements_path = os.path.join(script_dir, "requirements.txt")

    # Check if requirements.txt exists
    if not os.path.isfile(requirements_path):
        print("No requirements.txt found in the script directory.")
        return

    print(f"Checking requirements from {requirements_path}...")
    
    # Try optimized method first
    try:
        # Get currently installed packages
        installed_packages = get_installed_packages()
        
        # Parse requirements
        required_packages = parse_requirements(requirements_path)
        
        if not required_packages:
            print("No valid packages found in requirements.txt")
            return
        
        # Check which packages need installation
        packages_to_install = check_requirements_satisfied(required_packages, installed_packages)
        
        if not packages_to_install:
            print("✓ All requirements already satisfied.")
            return
        
        # Install missing packages
        success = install_packages(packages_to_install)
        
        if success:
            print("✓ All requirements installed successfully.")
        else:
            print("Optimized install failed, trying fallback...")
            if install_requirements_fallback(requirements_path):
                print("✓ Requirements installed via fallback method.")
            else:
                print("✗ Installation failed.")
                sys.exit(1)
                
    except Exception as e:
        # If optimized method fails, fall back to standard pip install
        print(f"Optimization failed ({e}), using standard installation...")
        if install_requirements_fallback(requirements_path):
            print("✓ Requirements installed successfully.")
        else:
            print("✗ Installation failed.")
            sys.exit(1)

if __name__ == "__main__":
    install_requirements()