from storage import initialize_database, search_screenshots


def main() -> None:
    initialize_database()
    query = input("Search your screenshots: ")

    if not query.strip():
        print("Please enter a search term.")
        return

    matches = search_screenshots(query)

    if not matches:
        print("No matching screenshots found.")
        return

    print(f"\nFound {len(matches)} matching screenshot(s):")

    for screenshot_id, file_path in matches:
        print(f"{screenshot_id}: {file_path}")


if __name__ == "__main__":
    main()