from app.search.setup import setup_foods_index


def main():
    setup_foods_index()
    print("Meilisearch initialized")


if __name__ == "__main__":
    main()
