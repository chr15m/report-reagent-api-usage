#!/usr/bin/env python3

import os
import sys
import re
import time
from collections import Counter

import requests


API_URL = "https://api.github.com/search/code"
MAX_PAGES = 10


def build_headers(token=None):
    headers = {"Accept": "application/vnd.github.text-match+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def main():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set.", file=sys.stderr)
        sys.exit(1)

    queries_to_count = ["[reagent.core", "[reagent.dom"]
    headers = build_headers(token)

    for query in queries_to_count:
        print(f"\n--- Counting aliases for: {query} ---\n")
        all_items = []
        for page in range(1, MAX_PAGES + 1):
            params = {
                "q": query,
                "per_page": 100,
                "page": page,
            }

            print(f"Fetching page {page} for query: '{query}'...")
            try:
                response = requests.get(
                    API_URL, headers=headers, params=params, timeout=30
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"Error fetching data from GitHub: {e}", file=sys.stderr)
                sys.exit(1)

            limit = response.headers.get("X-RateLimit-Limit")
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            print(
                f"  [rate_limit] limit={limit}, remaining={remaining}, reset={reset}"
            )

            data = response.json()
            items = data.get("items", [])
            all_items.extend(items)

            if not items:
                print("No more items found, stopping.")
                break

            # Avoid hitting rate limits
            if remaining and int(remaining) <= 1:
                if reset:
                    reset_time = int(reset)
                    sleep_duration = max(0, reset_time - time.time()) + 1
                    print(
                        f"  [rate_limit] Rate limit low, sleeping for {sleep_duration:.2f} seconds"
                    )
                    time.sleep(sleep_duration)
            else:
                # Respect secondary rate limits
                time.sleep(2)

        print(f"Found {len(all_items)} items in total.\n")

        aliases = []
        for item in all_items:
            for match in item.get("text_matches", []):
                fragment = match.get("fragment", "")
                pattern = f"{re.escape(query)}[^\]]*\]"
                found = re.findall(pattern, fragment)
                for alias_form in found:
                    normalized_alias = re.sub(r"\s+", " ", alias_form).strip()
                    aliases.append(normalized_alias)

        alias_counts = Counter(aliases)

        for alias, count in alias_counts.most_common():
            print(f"{count:<5} {alias}")


if __name__ == "__main__":
    main()
