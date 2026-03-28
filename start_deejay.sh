#!/bin/bash

# Add Homebrew to PATH
eval "$(/opt/homebrew/bin/brew shellenv)"

# Change to app directory
cd /Users/dwardo/deejay-app

# Load environment variables from .env
set -a
source .env
set +a

# Activate virtual environment
source venv/bin/activate

# Start gunicorn on port 8081
exec gunicorn -w 4 -b 0.0.0.0:8081 --access-logfile /Users/dwardo/deejay-app/access.log --error-logfile /Users/dwardo/deejay-app/error.log app:app
