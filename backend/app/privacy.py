"""Personal-data masking (Responsible AI).

JanSahayak never needs Aadhaar, phone, bank, PAN or e-mail details. If a user types one anyway, we mask it
at the front door (main.py), BEFORE the message reaches the AI service, the session, traces or LangSmith.
Normal profile numbers (age, income, acres, class) are left alone: they are short or written with commas.

Order matters: phone numbers first (10 digits starting 6-9, optional +91/0), then Aadhaar (12 digits,
grouped 4-4-4 or not), then any other long digit run (9-18 digits = bank account).
"""
import re

_PATTERNS = [
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("phone", re.compile(r"(?<!\d)(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")),
    ("aadhaar", re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")),
    ("pan", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.I)),
    ("account", re.compile(r"(?<!\d)\d{9,18}(?!\d)")),
]
_LABEL = {"email": "[email removed]", "phone": "[phone number removed]", "aadhaar": "[Aadhaar number removed]",
          "pan": "[PAN removed]", "account": "[account number removed]"}

NOTICE = {
    "en": "🔒 For your safety I removed a personal number from your message. You never need to share Aadhaar, "
          "phone, bank or PAN details here.",
    "hi": "🔒 आपकी सुरक्षा के लिए मैंने आपके संदेश से एक निजी नंबर हटा दिया है। यहाँ आधार, फ़ोन, बैंक या PAN "
          "की जानकारी देने की ज़रूरत नहीं है।",
}


def redact(text: str) -> tuple[str, list[str]]:
    """Return (masked text, kinds of data found), e.g. ('My Aadhaar is [Aadhaar number removed]', ['aadhaar'])."""
    found = []
    for kind, pat in _PATTERNS:
        text, n = pat.subn(_LABEL[kind], text)
        if n:
            found.append(kind)
    return text, found
