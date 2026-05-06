# 1. wipe everything
docker compose down -v --remove-orphans

# 2. rebuild images (important!)
docker compose build

# 3. start DB
docker compose up -d db

# 4. run migrations
docker compose run --rm migrate

# 5. import data
docker compose run --rm import

# 6. start app
docker compose up app
