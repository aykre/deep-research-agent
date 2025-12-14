"""Prompt management utilities."""

from pathlib import Path


def load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory.

    Args:
        name: Name of the prompt file (without .txt extension)

    Returns:
        The prompt template as a string
    """
    prompt_path = Path(__file__).parent / f"{name}.txt"
    return prompt_path.read_text()
