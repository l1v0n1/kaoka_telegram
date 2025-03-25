#!/usr/bin/env python3
"""
Setup script for Kaoka Telegram Bot
This script helps set up the basic configuration for the bot.
"""
import os
import shutil
import sys

def is_ci_environment():
    """Check if running in a CI environment"""
    return os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true'

def setup_config():
    """Set up the configuration files"""
    print("Setting up Kaoka Telegram Bot...")
    
    # Check if config.py exists
    if os.path.exists('config.py'):
        # In CI, skip overwriting existing files
        if is_ci_environment():
            print("Running in CI environment. Skipping config.py overwrite check.")
            return
        
        overwrite = input("config.py already exists. Overwrite? (y/n): ")
        if overwrite.lower() != 'y':
            print("Skipping config.py setup.")
            return
    
    # Copy example config
    if os.path.exists('config.example.py'):
        shutil.copy('config.example.py', 'config.py')
        print("Created config.py from example.")
    else:
        print("Warning: config.example.py not found. Please create config.py manually.")
    
    # Check if .env exists
    if not os.path.exists('.env') and os.path.exists('.env.example'):
        shutil.copy('.env.example', '.env')
        print("Created .env from example.")
    
    print("\nSetup completed!")
    print("Please edit config.py and .env with your actual settings before running the bot.")
    print("\nTo start the bot:")
    print("1. With Python directly: python bot.py")
    print("2. With Docker: docker-compose up -d")

if __name__ == "__main__":
    setup_config() 