"""Smart follow-up questions (no AI).

After every answer we look at the schemes we just showed. If some of them say "Need more info",
we ask about the ONE detail that would settle the most of them (e.g. "category" for students).
If no unknown detail would change the result, we ask nothing.

Each question comes with tap-to-answer options. Tapping an option sends {"set": {...}} so the
backend stores the value directly, without an AI call. Numeric answers use ranges whose edges
match the rule limits in schemes.json (e.g. income Rs 2.5 / 3.5 / 4.5 / 8 lakh), and we store the
range's upper value so the rules give the same result as the exact number would.
"""

STATES = ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
          "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
          "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
          "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
          "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep",
          "Puducherry"]


def _opt(en, hi, **values):
    return {"label": en, "label_hi": hi, "set": values}


def _yes_no(field):
    return [_opt("Yes", "हाँ", **{field: True}), _opt("No", "नहीं", **{field: False})]


# field -> question (en/hi), options, and input hint ("number"/"text" = user can also type)
Q = {
    "occupation": {
        "en": "Are you a farmer, a student, or starting/running a business?",
        "hi": "क्या आप किसान हैं, छात्र हैं, या कोई व्यापार शुरू कर रहे हैं / चला रहे हैं?",
        "options": [_opt("🌾 Farmer", "🌾 किसान", occupation="farmer"), _opt("🎓 Student", "🎓 छात्र", occupation="student"),
                    _opt("🏪 Business", "🏪 व्यापार", occupation="entrepreneur")]},
    "state": {
        "en": "Which state do you live in?", "hi": "आप किस राज्य में रहते हैं?",
        "options": [_opt(s, s, state=s) for s in STATES]},
    "age": {
        "en": "What is your age?", "hi": "आपकी उम्र क्या है?", "input": "number",
        "options": []},  # typing a number is quicker than picking a range here
    "annual_income": {
        "en": "Roughly what is your family's yearly income?", "hi": "आपके परिवार की सालाना आय लगभग कितनी है?",
        "options": [_opt("Up to ₹2.5 lakh", "₹2.5 लाख तक", annual_income=250000),
                    _opt("₹2.5–3.5 lakh", "₹2.5–3.5 लाख", annual_income=350000),
                    _opt("₹3.5–4.5 lakh", "₹3.5–4.5 लाख", annual_income=450000),
                    _opt("₹4.5–8 lakh", "₹4.5–8 लाख", annual_income=800000),
                    _opt("More than ₹8 lakh", "₹8 लाख से ज़्यादा", annual_income=900000)]},
    "category": {
        "en": "Which category do you belong to?", "hi": "आप किस वर्ग से हैं?",
        "options": [_opt("General", "सामान्य", category="general"), _opt("OBC", "ओबीसी", category="obc"),
                    _opt("SC", "एससी", category="sc"), _opt("ST", "एसटी", category="st"), _opt("EWS", "ईडब्ल्यूएस", category="ews")]},
    "land_acres": {
        "en": "How much farmland do you own?", "hi": "आपके पास कितनी खेती की ज़मीन है?", "input": "number",
        "options": [_opt("No land of my own", "अपनी ज़मीन नहीं", land_acres=0),
                    _opt("Up to 5 acres (2 hectares)", "5 एकड़ (2 हेक्टेयर) तक", land_acres=4.9),
                    _opt("More than 5 acres", "5 एकड़ से ज़्यादा", land_acres=6)]},
    "course": {
        "en": "Which course are you studying?", "hi": "आप कौन सा कोर्स पढ़ रहे हैं?", "input": "text",
        "options": [_opt("B.Tech / BE", "B.Tech / BE", course="B.Tech"), _opt("Diploma", "डिप्लोमा", course="Diploma"),
                    _opt("BA / BSc / BCom", "BA / BSc / BCom", course="BA/BSc/BCom"),
                    _opt("Agriculture degree", "कृषि डिग्री", course="B.Sc Agriculture"),
                    _opt("MBA / MCA", "MBA / MCA", course="MBA/MCA"),
                    _opt("School (Class 9–12)", "स्कूल (कक्षा 9–12)", course="School", school_student=True)]},
    "business_type": {
        "en": "What kind of business is it?", "hi": "आपका व्यापार किस तरह का है?", "input": "text",
        "options": [_opt("Food processing", "खाद्य प्रसंस्करण", business_type="food processing"),
                    _opt("Manufacturing", "निर्माण", business_type="manufacturing"),
                    _opt("Shop / service", "दुकान / सेवा", business_type="shop/service"),
                    _opt("Tailoring / handicraft", "सिलाई / हस्तशिल्प", business_type="tailoring/handicraft"),
                    _opt("Tech startup", "टेक स्टार्टअप", business_type="tech startup")]},
    "gender": {
        "en": "Are you male or female?", "hi": "आप पुरुष हैं या महिला?",
        "options": [_opt("Female", "महिला", gender="female"), _opt("Male", "पुरुष", gender="male")]},
    "disability": {
        "en": "Do you have a disability of 40% or more?", "hi": "क्या आपको 40% या उससे ज़्यादा दिव्यांगता है?",
        "options": _yes_no("disability")},
    "shg_member": {
        "en": "Are you a member of a women Self Help Group (SHG)?", "hi": "क्या आप किसी महिला स्वयं सहायता समूह (SHG) की सदस्य हैं?",
        "options": _yes_no("shg_member")},
    "top_institution": {
        "en": "Are you admitted to a top institute like an IIT, NIT, IIM or AIIMS?", "hi": "क्या आपका दाख़िला IIT, NIT, IIM या AIIMS जैसे बड़े संस्थान में है?",
        "options": _yes_no("top_institution")},
    "class12_top20": {
        "en": "Were you in the top 20% of your Class 12 board exam?", "hi": "क्या आप कक्षा 12 बोर्ड परीक्षा में टॉप 20% में थे?",
        "options": _yes_no("class12_top20")},
    "class12_top1": {
        "en": "Were you in the top 1% of your Class 12 board (or have a JEE/NEET rank or NTSE/KVPY)?",
        "hi": "क्या आप कक्षा 12 बोर्ड में टॉप 1% में थे (या JEE/NEET रैंक / NTSE/KVPY)?",
        "options": _yes_no("class12_top1")},
    "school_student": {
        "en": "Are you studying in school (Class 9–12)?", "hi": "क्या आप स्कूल (कक्षा 9–12) में पढ़ रहे हैं?",
        "options": _yes_no("school_student")},
    "swanath_category": {
        "en": "Are you an orphan, or did a parent die of COVID-19 or in armed forces service?",
        "hi": "क्या आप अनाथ हैं, या माता-पिता में से किसी की मृत्यु COVID-19 से या सेना/अर्धसैनिक सेवा में हुई?",
        "options": _yes_no("swanath_category")},
    "dpiit_recognised": {
        "en": "Is your startup recognised by DPIIT (less than 2 years old)?", "hi": "क्या आपका स्टार्टअप DPIIT से मान्यता प्राप्त है (2 साल से कम पुराना)?",
        "options": _yes_no("dpiit_recognised")},
}
# Last tie-break: common, easy questions first.
PRIORITY = ["state", "age", "annual_income", "category", "land_acres", "course", "business_type", "gender",
            "disability", "school_student", "top_institution", "class12_top20", "class12_top1", "shg_member",
            "swanath_category", "dpiit_recognised"]


# Study questions only make sense for students ("Which course are you studying?" to a farmer is odd).
STUDENT_ONLY = {"school_student", "class12_top20", "class12_top1", "top_institution", "swanath_category"}
# Same field, different wording for non-students: farmers/business owners are asked about a qualification
# (only Agri-Clinics uses "course" outside student schemes: it needs an agriculture degree/diploma).
NON_STUDENT = {
    "course": {
        "en": "Do you have a degree or diploma in agriculture (or veterinary/horticulture)?",
        "hi": "क्या आपके पास कृषि (या पशु चिकित्सा/बागवानी) में डिग्री या डिप्लोमा है?",
        "options": [_opt("Yes", "हाँ", course="agriculture graduate"), _opt("No", "नहीं", course="no agriculture degree")]},
}


# After this many follow-ups, only ask when one answer settles 2+ schemes (rare scholarships each need
# their own yes/no detail; asking all of them one by one gets tiring).
SOFT_LIMIT = 3
# Personal questions are only worth asking when they settle 2+ schemes, and always come with a reason.
PERSONAL = {"gender", "category", "disability"}
WHY = {
    "gender": {"en": "Some schemes are only for women.", "hi": "कुछ योजनाएँ केवल महिलाओं के लिए हैं।"},
    "category": {"en": "Many scholarships depend on category.", "hi": "कई छात्रवृत्तियाँ वर्ग पर निर्भर करती हैं।"},
    "disability": {"en": "Some schemes are for people with disabilities.", "hi": "कुछ योजनाएँ दिव्यांग लोगों के लिए हैं।"},
}


def short_name(scheme_id: str) -> str:
    """Button-sized scheme name from schemes.json (e.g. 'PM-KMY (pension)')."""
    from .eligibility import BY_ID
    return BY_ID[scheme_id].get("short_name") or BY_ID[scheme_id]["scheme_name"]


def pick(results: list[dict], asked: list[str], occupation: str = "") -> tuple[str | None, list[str]]:
    """The unknown detail that appears in the most 'Need more info' schemes, and the IDs of those schemes."""
    ids: dict[str, list[str]] = {}
    for r in results:
        if r["status"] != "more_info_needed":
            continue
        for f in {c["field"] for c in r["conditions"] if c["result"] == "unknown"}:
            if f in Q and f not in asked and f != "occupation" and (occupation == "student" or f not in STUDENT_ONLY):
                ids.setdefault(f, []).append(r["scheme_id"])  # results are best-first, so ids[f][0] is the top card
    pos = {r["scheme_id"]: i for i, r in enumerate(results)}
    ids = {f: v for f, v in ids.items() if f not in PERSONAL or len(v) >= 2}
    if not ids:
        return None, []
    # most schemes settled first; then the one that helps the top card; then easy questions first
    field = min(ids, key=lambda f: (-len(ids[f]), pos[ids[f][0]], PRIORITY.index(f) if f in PRIORITY else 99))
    if len([a for a in asked if a != "occupation"]) >= SOFT_LIMIT and len(ids[field]) < 2:
        return None, []
    return field, ids[field]


def build(field: str, lang: str, scheme_ids: list[str] | None = None, occupation: str = "") -> dict:
    """The follow-up as sent to the screen: question text + tap options in the chat language."""
    q = NON_STUDENT[field] if occupation != "student" and field in NON_STUDENT else Q[field]
    hi = lang == "hi"
    scheme_ids = scheme_ids or []
    return {
        "field": field,
        "question": q["hi" if hi else "en"],
        "why": WHY.get(field, {}).get("hi" if hi else "en", ""),
        "helps": len(scheme_ids),
        "helps_names": [short_name(i) for i in scheme_ids[:3]],  # "Helps check: PM-KMY, KCC"
        "input": q.get("input"),
        "options": [{"label": o["label_hi" if hi else "label"], "set": o["set"]} for o in q["options"]],
    }


def which_scheme(scheme_ids: list[str], lang: str) -> dict:
    """'Which scheme do you mean?' with one button per scheme on screen."""
    return {
        "field": "scheme",
        "question": "किस योजना के बारे में?" if lang == "hi" else "Which scheme do you mean?",
        "why": "", "helps": 0, "helps_names": [], "input": None,
        "options": [{"label": short_name(i), "set": {}, "scheme_id": i} for i in scheme_ids],
    }
