#!/usr/bin/env python3

import os
import sys
import re
from collections import Counter

import requests


API_URL = "https://api.github.com/search/code"


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

    query = "[reagent.core"
    headers = build_headers(token)
    params = {
        "q": query,
        "per_page": 100,
        "page": 1,
    }

    print(f"Fetching results for query: '{query}'...")
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from GitHub: {e}", file=sys.stderr)
        sys.exit(1)

    data = response.json()
    items = data.get("items", [])

    print(f"Found {len(items)} items on the first page.\n")

    aliases = []
    for item in items:
        for match in item.get("text_matches", []):
            fragment = match.get("fragment", "")
            found = re.findall(r'\[reagent\.core[^\]]*\]', fragment)
            for alias_form in found:
                normalized_alias = re.sub(r'\s+', ' ', alias_form).strip()
                aliases.append(normalized_alias)

    alias_counts = Counter(aliases)

    for alias, count in alias_counts.most_common():
        print(f"{count:<5} {alias}")


if __name__ == "__main__":
    main()
