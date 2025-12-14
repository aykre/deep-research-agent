"""Content quality validation utilities."""

from server.models import ExtractedContent
from server.utils.logging_config import get_logger

logger = get_logger(__name__)

# Minimum content thresholds
MIN_CONTENT_LENGTH = 50  # Characters
MIN_MEANINGFUL_WORDS = 10  # Words that aren't just navigation


def has_meaningful_content(extracted: ExtractedContent) -> bool:
    """Check if extracted content has meaningful information.

    Args:
        extracted: The extracted content object

    Returns:
        True if content appears meaningful, False otherwise
    """
    page_type = extracted.page_type

    # Check content based on page type
    if page_type == "article":
        content = extracted.content
        if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
            logger.info("Article has insufficient content", url=extracted.url)
            return False

        # Check for meaningful words (not just whitespace/navigation)
        words = content.split()
        if len(words) < MIN_MEANINGFUL_WORDS:
            logger.info("Article has too few words", url=extracted.url)
            return False

    elif page_type == "product":
        # Product needs at least name or description
        if not extracted.name and not extracted.description:
            logger.info("Product has no name or description", url=extracted.url)
            return False

    elif page_type == "forum_post":
        content = extracted.content
        if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
            logger.info("Forum post has insufficient content", url=extracted.url)
            return False

    elif page_type == "directory":
        # Directory needs items
        if not extracted.items or len(extracted.items) == 0:
            logger.info("Directory has no items", url=extracted.url)
            return False

    elif page_type == "other":
        content = extracted.content
        if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
            logger.info("Other page has insufficient content", url=extracted.url)
            return False

    return True
