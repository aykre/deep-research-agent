"""URL filtering utilities for rejecting ad and tracking URLs."""

import re

# Known ad/tracking URL patterns
AD_PATTERNS = [
    r"bing\.com/aclick",
    r"doubleclick\.net",
    r"googleadservices\.com",
    r"ads\..*",
    r".*\.ad\.",
    r"click\..*",
    r"tracker\..*",
    r"affiliate\..*",
    r"youtube\.com",
    r"youtu\.be",
]

# Compile patterns for efficiency
COMPILED_AD_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in AD_PATTERNS]


def is_ad_or_tracking_url(url: str) -> bool:
    """Check if URL matches known ad/tracking patterns.

    Args:
        url: The URL to check

    Returns:
        True if URL appears to be an ad/tracking link, False otherwise
    """
    # Check against all patterns
    for pattern in COMPILED_AD_PATTERNS:
        if pattern.search(url):
            return True
    return False


def filter_ad_urls(urls: list[str]) -> tuple[list[str], list[str]]:
    """Filter out ad/tracking URLs from a list.

    Args:
        urls: List of URLs to filter

    Returns:
        Tuple of (clean_urls, rejected_urls)
    """
    clean_urls = []
    rejected_urls = []

    for url in urls:
        if is_ad_or_tracking_url(url):
            rejected_urls.append(url)
        else:
            clean_urls.append(url)

    return clean_urls, rejected_urls
