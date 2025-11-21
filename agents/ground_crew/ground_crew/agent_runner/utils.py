from datetime import datetime


def get_current_date() -> str:
    """Return the current date formatted for the agent prompt."""
    return datetime.now().strftime("%B %d, %Y")


