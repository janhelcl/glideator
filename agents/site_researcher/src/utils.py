from datetime import datetime
from typing import List, Any, Dict


def get_current_date():
    """Get current date in a readable format."""
    return datetime.now().strftime("%B %d, %Y")