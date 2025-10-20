#!/usr/bin/env python3

import os
import sys
import time

import requests


API_URL = "https://api.github.com/search/code"


def build_headers(include_token=True, token=None):
    headers = {"Accept": "application/vnd.github.text-match+json"}
    if include_token and token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def candidate_queries(query):
    queries = []

    def add(candidate):
        if candidate not in queries:
            queries.append(candidate)

    add(query)
    if ":" not in query and not query.startswith('"'):
        add(f'"{query}"')
    return queries


def fetch_candidate_total(candidate, headers, include_token):
    params = {
        "q": candidate,
        "per_page": 1,
    }
    print(
        "[fetch_candidate_total] attempt",
        f"query={repr(candidate)}",
        f"include_token={include_token}",
    )
    response = requests.get(
        API_URL,
        headers=headers,
        params=params,
        timeout=30,
    )
    print(
        "[fetch_candidate_total] status",
        response.status_code,
        f"url={response.url}",
    )
    limit = response.headers.get("X-RateLimit-Limit")
    remaining = response.headers.get("X-RateLimit-Remaining")
    reset = response.headers.get("X-RateLimit-Reset")
    print(
        "[fetch_candidate_total] rate_limit",
        f"limit={limit}",
        f"remaining={remaining}",
        f"reset={reset}",
    )
    if remaining and int(remaining) <= 1:
        if reset:
            reset_time = int(reset)
            sleep_duration = max(0, reset_time - time.time()) + 1
            print(
                f"[fetch_candidate_total] rate limit low, sleeping for {sleep_duration:.2f} seconds"
            )
            time.sleep(sleep_duration)
    if response.status_code in [403, 422]:
        reason = ""
        try:
            payload = response.json()
            reason = payload.get("message", "")
        except requests.exceptions.JSONDecodeError:
            reason = response.text
        print(
            f"[fetch_candidate_total] skipping query with status {response.status_code}",
            f"reason='{reason}'",
            f"query={repr(candidate)}",
        )
        return None

    response.raise_for_status()
    payload = response.json()
    total_count = payload.get("total_count")
    print(
        "[fetch_candidate_total] total_count",
        total_count,
        f"query={repr(candidate)}",
        f"include_token={include_token}",
    )
    return total_count


def fetch_total_count(query):
    token = os.getenv("GITHUB_TOKEN")
    include_token_options = [True]

    best_total = None
    attempts = candidate_queries(query)

    for use_token in include_token_options:
        headers = build_headers(include_token=use_token, token=token)
        for candidate in attempts:
            total = fetch_candidate_total(candidate, headers, use_token)
            if total is None:
                continue
            if total > 0:
                return total
            if best_total is None:
                best_total = total

    return best_total


def main():
    queries = [
        "[reagent.core",
        "(rdom/render ",
        "(r/render ",
        "(r/wrap ",
        "(r/track ",
        "(r/track! ",
        "(r/reaction ",
        "(r/cursor ",
        "(r/atom ",
        "(r/with-let ",
        "(r/unsafe-html ",
    ]
    results = {}
    for query in queries:
        total_count = fetch_total_count(query)
        results[query] = total_count
        time.sleep(2)

    print("\n--- Reagent API Usage Report ---")
    for query, total_count in results.items():
        count_str = str(total_count) if total_count is not None else "Error"
        print(f"{query:<20} {count_str}")
    print("--------------------------------\n")


if __name__ == "__main__":
    main()
