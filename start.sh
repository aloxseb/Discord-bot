#!/bin/bash

# Detect environment
echo "Detecting environment..."
if [ -n "$REPL_ID" ]; then
    echo "Running on Replit"
    IS_REPLIT=true
elif [ -n "$RAILWAY_STATIC_URL" ]; then
    echo "Running on Railway"
    IS_RAILWAY=true
else
    echo "Running on generic environment"
fi

# Install FFmpeg if needed
if [ "$IS_REPLIT" = true ]; then
    echo "Installing FFmpeg for Replit..."
    pip install python-ffmpeg
elif [ "$IS_RAILWAY" = true ]; then
    echo "Installing FFmpeg for Railway..."
    apt-get update && apt-get install -y ffmpeg
else
    # Check if FFmpeg is installed
    if ! command -v ffmpeg &> /dev/null; then
        echo "FFmpeg not found. Attempting to install..."
        
        # Try to detect the OS
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            
            if [ "$ID" = "debian" ] || [ "$ID" = "ubuntu" ] || [ "$ID_LIKE" = "debian" ]; then
                echo "Detected Debian/Ubuntu, installing FFmpeg..."
                apt-get update && apt-get install -y ffmpeg
            elif [ "$ID" = "fedora" ] || [ "$ID_LIKE" = "fedora" ]; then
                echo "Detected Fedora, installing FFmpeg..."
                dnf install -y ffmpeg
            elif [ "$ID" = "centos" ] || [ "$ID" = "rhel" ]; then
                echo "Detected CentOS/RHEL, installing FFmpeg..."
                yum install -y ffmpeg
            else
                echo "Unsupported OS for automatic FFmpeg installation."
                echo "Please install FFmpeg manually."
            fi
        else
            echo "Could not detect OS. Please install FFmpeg manually."
        fi
    else
        echo "FFmpeg is already installed."
    fi
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Start the bot
echo "Starting the Discord bot..."
python bot.py 