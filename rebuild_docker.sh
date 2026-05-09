#!/bin/bash

# If --reset-db is passed as an argument, wipe everything
if [[ "$1" == "--reset-db" ]]; then
  echo "Resetting database and removing all containers/volumes..."
  docker compose down -v --remove-orphans
else
  echo "Preserving existing database and containers. Skipping docker compose down."
fi

# Rebuild images (important!)
docker compose build

# Start DB
docker compose up -d db

# Run migrations
docker compose run --rm migrate

# Import data
docker compose run --rm import

# Start app
docker compose up app
