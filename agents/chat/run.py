#!/usr/bin/env python3
"""Simple launch script for the AutoGen Chat Application.

This script provides a convenient way to start the application with
proper error handling and user-friendly messages.
"""

import sys
import os
import subprocess
from pathlib import Path

def check_requirements():
    """Check if basic requirements are met."""
    # Check Python version
    if sys.version_info < (3, 13):
        print("❌ Python 3.13+ is required")
        print(f"Current version: {sys.version}")
        return False
    
    # Check if .env file exists
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if not env_file.exists():
        if env_example.exists():
            print("⚠️  .env file not found")
            print(f"Please copy {env_example} to .env and configure your settings:")
            print(f"cp {env_example} .env")
        else:
            print("⚠️  Neither .env nor env.example found")
            print("Please create a .env file with your OPENAI_API_KEY")
        return False
    
    return True

def install_dependencies():
    """Install required dependencies."""
    try:
        print("📦 Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def main():
    """Main entry point for the launcher."""
    print("🚀 AutoGen Chat Application Launcher")
    print("=" * 40)
    
    # Check basic requirements
    if not check_requirements():
        print("\n❌ Requirements not met. Please fix the issues above.")
        sys.exit(1)
    
    # Ask user if they want to install dependencies
    install_deps = input("\n📦 Install/update dependencies? (y/N): ").lower().strip()
    if install_deps in ['y', 'yes']:
        if not install_dependencies():
            sys.exit(1)
    
    # Launch the application
    print("\n🚀 Starting AutoGen Chat Application...")
    print("This may take a moment to initialize...")
    print("\n" + "=" * 40)
    
    try:
        # Import and run the main app
        from app import main
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Application stopped by user")
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("Please install dependencies: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
