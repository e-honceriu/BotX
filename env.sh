#!/bin/bash

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "Environment variables loaded successfully."
else
    echo ".env file not found!"
fi