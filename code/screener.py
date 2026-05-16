import re

INJECTION_PATTERNS = [
    r"ignore\s+(previous|prior|above|all)\s+(instructions|prompts|rules)",
    r"(reveal|show|display|output|print)\s+(your|the|all)\s+(instructions|rules|prompt|system|internal|logic)",
    r"règles\s+internes",
    r"logique\s+exacte",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(if|a|an)",
    r"forget\s+(everything|all|your)",
    r"override\s+(your|the|all)",
    r"documents?\s+récupérés",
]

MALICIOUS_PATTERNS = [
    r"(delete|remove|erase)\s+(all|every)\s+files?",
    r"rm\s+-rf",
    r"format\s+(disk|drive|hard)",
    r"give\s+me\s+(the\s+)?code\s+to\s+(delete|hack|exploit|destroy)",
    r"(hack|exploit|attack|ddos|crack)\s+(into|the|a)",
]

OFF_TOPIC_PATTERNS = [
    r"(who|what)\s+(is|was)\s+the\s+(name\s+of\s+the\s+)?(actor|actress|director|singer|president)",
    r"(recipe|cook|weather|sports?\s+score)",
    r"(write|compose)\s+(me\s+)?(a\s+)?(poem|song|story|essay)",
]

PLEASANTRY_PATTERNS = [
    r"^(thank\s*you|thanks|thx|ty|cheers|great|awesome|perfect|ok|okay|cool|got\s+it|appreciate)(\s+(for|so much|a lot)[\w\s]*)?[.!]?\s*$",
    r"^(hi|hello|hey|good\s+(morning|afternoon|evening))[\s!.]*$",
]


def _matches_any(text: str, patterns: list[str]) -> bool:
    text_lower = text.lower().strip()
    return any(re.search(p, text_lower) for p in patterns)


def prescreen(issue: str, subject: str = "", company: str = "") -> dict | None:
    """
    Returns a pre-filled response dict if the ticket can be handled without LLM,
    or None to continue to retrieval.
    """
    combined = f"{issue} {subject}".strip()

    if _matches_any(combined, INJECTION_PATTERNS):
        return {
            "status": "replied",
            "product_area": "general_support",
            "response": "I can help with support questions related to our products. Please describe your specific issue and I'll do my best to assist you.",
            "justification": "Detected prompt injection attempt. Returning safe generic response.",
            "request_type": "invalid",
        }

    if _matches_any(combined, MALICIOUS_PATTERNS):
        return {
            "status": "replied",
            "product_area": "general_support",
            "response": "This request is outside the scope of our support services. We can help with questions about HackerRank, Claude, or Visa products.",
            "justification": "Malicious request detected — outside support scope.",
            "request_type": "invalid",
        }

    if _matches_any(issue.strip(), PLEASANTRY_PATTERNS):
        return {
            "status": "replied",
            "product_area": "general_support",
            "response": "Happy to help! Let us know if you have any other questions.",
            "justification": "Pleasantry with no actionable request.",
            "request_type": "invalid",
        }

    if _matches_any(combined, OFF_TOPIC_PATTERNS):
        return {
            "status": "replied",
            "product_area": "general_support",
            "response": "I'm sorry, this is outside the scope of our support capabilities. We can help with questions about HackerRank, Claude, or Visa products.",
            "justification": "Off-topic — unrelated to any supported product.",
            "request_type": "invalid",
        }

    return None
