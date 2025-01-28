#!/usr/bin/env python3
"""
Script to install project dependencies and set up development environment.
"""

import os
import sys
import subprocess
import venv
from pathlib import Path

def create_venv(venv_path):
    """Create a new virtual environment."""
    print(f"Creating virtual environment at {venv_path}")
    venv.create(venv_path, with_pip=True)

def install_requirements(venv_path):
    """Install requirements using pip."""
    # Get the correct pip path
    if sys.platform == 'win32':
        pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
    else:
        pip_path = os.path.join(venv_path, 'bin', 'pip')

    # Install requirements
    print("Installing dependencies...")
    subprocess.run([pip_path, 'install', '-r', 'requirements.txt'], check=True)
    subprocess.run([pip_path, 'install', '-r', 'requirements-dev.txt'], check=True)

    # Install local wheels from vendor directory
    vendor_dir = Path('vendor')
    if vendor_dir.exists():
        wheels = list(vendor_dir.glob('*.whl'))
        if wheels:
            print("Installing vendor packages...")
            subprocess.run([pip_path, 'install', *[str(w) for w in wheels]], check=True)

def main():
    """Main installation process."""
    try:
        # Project root directory
        project_root = Path(__file__).parent.parent
        os.chdir(project_root)

        # Create and activate virtual environment
        venv_path = project_root / 'venv'
        if not venv_path.exists():
            create_venv(venv_path)
        
        # Install dependencies
        install_requirements(venv_path)
        
        print("\nSetup completed successfully!")
        print("\nTo activate the virtual environment:")
        if sys.platform == 'win32':
            print(f"    {venv_path}\\Scripts\\activate.bat")
        else:
            print(f"    source {venv_path}/bin/activate")

    except subprocess.CalledProcessError as e:
        print(f"Error during dependency installation: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()