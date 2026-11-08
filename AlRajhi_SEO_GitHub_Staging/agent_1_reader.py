"""
agent_1_reader.py  v6.0
=======================
Agent 1 — Reader / Extractor

Role: fetch, extract, clean, structure, save, hand off to Agent 2.
Does NOT analyze, interpret, generate, optimize, or critique.

Steps:
  1. Fetch HTML robustly (retry + Arabic content validation)
  2. Extract title and meta description
  3. Extract headings (document order)
  4. Extract CTA texts
  5. Extract main_description + body_content
  6. Derive keywords_used (frequency-filtered)
  7. Derive top_phrases (frequency-filtered)
  8. Save clean JSON → agent_1_output.json
"""

import re
import json
import time

import requests
from bs4 import BeautifulSoup
from collections import Counter

from utils import (
    fetch_page,
    clean_arabic_text,
    ARABIC_RE,
    ARABIC_STOPWORDS,
    is_noise_line,
)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

OUTPUT_FILE    = "agent_1_output.json"
MIN_BODY_CHARS = 300

OUR_PAGES = {
    "vehicle_insurance": {
        "product": "تأمين المركبات",
        "url": "https://www.alrajhitakaful.com/ar/personal/car-insurance",
    },
    "home_insurance": {
        "product": "تأمين المنزل ومقتنياته",
        "url": "https://www.alrajhitakaful.com/ar/personal/home-insurance",
    },
}

COMPETITOR_PAGES = {
    "vehicle_insurance": [
        {"name": "bcare_vehicle",   "brand": "Bcare",
         "url": "https://www.bcare.com.sa/car-insurance"},
        {"name": "tameeni_vehicle", "brand": "Tameeni",
         "url": "https://www.tameeni.com/ar"},
    ],
    "home_insurance": [
        {"name": "tameeni_home",  "brand": "Tameeni",
         "url": "https://www.tameeni.com/ar/home"},
        {"name": "bcare_home",    "brand": "Bcare",
         "url": "https://www.bcare.com.sa/home-insurance"},
        {"name": "tawuniya_home", "brand": "Tawuniya",
         "url": "https://www.tawuniya.com/ar/individuals/products/property-casualty/home-insurance"},
    ],
}

# Strong browser headers — reduces bot-rejection rate
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}

# Only strip tags that NEVER contain real page content
_NOISE_TAGS = [
    'footer', 'script', 'style', 'noscript',
    'iframe', 'svg', 'link', 'meta',
    'figure', 'figcaption', 'picture', 'source',
]

# Additional noise patterns beyond utils.NOISE_PATTERNS
_EXTRA_NOISE = re.compile(
    r'(cookie|كوكي|loading|خطأ|error|404|403|'
    r'whatsapp|واتساب|تليجرام|telegram|'
    r'instagram|انستغرام|twitter|تويتر|'
    r'copyright|©|\d{4}\s*جميع)',
    re.IGNORECASE | re.UNICODE,
)


# ─────────────────────────────────────────────
# STEP 1 — ROBUST FETCH
# ─────────────────────────────────────────────

def _arabic_word_count(soup) -> int:
    text = soup.get_text()
    return len(ARABIC_RE.findall(text))


def _fetch_requests(url: str, retries: int = 3) -> BeautifulSoup | None:
    """requests with retry, proper encoding, and Arabic content check."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=20, allow_redirects=True)
            resp.raise_for_status()

            # Detect encoding from HTML meta charset before decoding
            raw_bytes = resp.content
            charset_match = re.search(
                rb'charset=["\']?([\w-]+)', raw_bytes[:4096], re.I
            )
            if charset_match:
                detected = charset_match.group(1).decode('ascii', errors='ignore')
                try:
                    html = raw_bytes.decode(detected, errors='replace')
                except (LookupError, UnicodeDecodeError):
                    html = raw_bytes.decode('utf-8', errors='replace')
            else:
                html = raw_bytes.decode('utf-8', errors='replace')

            soup = BeautifulSoup(html, 'html.parser')
            if _arabic_word_count(soup) >= 20:
                return soup

        except requests.RequestException:
            pass

        if attempt < retries - 1:
            time.sleep(2 ** attempt)  # 1s, 2s backoff

    return None


def fetch_robust(url: str) -> BeautifulSoup | None:
    """
    Fetch strategy:
      1. requests with retry + Arabic content validation
      2. utils.fetch_page (Selenium fallback) if requests returns thin content
    """
    soup = _fetch_requests(url)
    if soup and _arabic_word_count(soup) >= 50:
        return soup

    # Selenium fallback for JS-heavy pages
    print("    [INFO] Falling back to Selenium ...")
    return fetch_page(url)


# ─────────────────────────────────────────────
# STEP 2 — TITLE
# ─────────────────────────────────────────────

def extract_title(soup) -> str:
    # <title> tag — strip site name appended after | or -
    tag = soup.find('title')
    if tag:
        raw = clean_arabic_text(tag.get_text())
        # Keep only the part before the first separator if it contains Arabic
        for sep in [' | ', ' - ', ' – ', ' — ']:
            if sep in raw:
                part = raw.split(sep)[0].strip()
                if ARABIC_RE.search(part) and len(part) > 5:
                    return part
        if ARABIC_RE.search(raw) and raw:
            return raw

    for attrs in [
        {'property': 'og:title'},
        {'name': 'twitter:title'},
        {'itemprop': 'name'},
    ]:
        tag = soup.find('meta', attrs=attrs)
        if tag:
            t = clean_arabic_text(tag.get('content', ''))
            if t and ARABIC_RE.search(t):
                return t

    h1 = soup.find('h1')
    if h1:
        t = clean_arabic_text(h1.get_text())
        if t:
            return t

    return ""


# ─────────────────────────────────────────────
# STEP 2 — META DESCRIPTION
# ─────────────────────────────────────────────

def extract_meta_description(soup) -> str:
    for attrs in [
        {'name': 'description'},
        {'name': 'Description'},
        {'property': 'og:description'},
        {'name': 'twitter:description'},
        {'itemprop': 'description'},
    ]:
        tag = soup.find('meta', attrs=attrs)
        if tag:
            val = clean_arabic_text(tag.get('content', ''))
            if val and ARABIC_RE.search(val):
                return val
    return ""


# ─────────────────────────────────────────────
# STEP 3 — HEADINGS (document order)
# ─────────────────────────────────────────────

def extract_headings(soup) -> list:
    headings = []
    seen = set()
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        text = clean_arabic_text(tag.get_text(separator=' ', strip=True))
        if (text and len(text) > 4
                and not is_noise_line(text)
                and not _EXTRA_NOISE.search(text)
                and text not in seen):
            seen.add(text)
            headings.append({"level": tag.name, "text": text})
    return headings


# ─────────────────────────────────────────────
# STEP 4 — CTA TEXTS
# ─────────────────────────────────────────────

_ACTION_KEYWORDS = [
    'احصل', 'اشتر', 'قارن', 'ابدأ', 'اطلب', 'تواصل',
    'سجل', 'اشترك', 'تقدم', 'احجز', 'عرض', 'اكتشف',
    'احسب', 'تحقق', 'جرب', 'انضم', 'اعرف', 'استفسر',
    'ابحث', 'اختر', 'اشتراك', 'تقديم', 'طلب',
]

_BTN_CLASS_RE = re.compile(r'\b(btn|button|cta|action|call)\b', re.I)


def extract_cta_texts(soup) -> list:
    ctas = []
    seen = set()

    def _add(text: str):
        text = clean_arabic_text(text)
        if text and 3 < len(text) < 80 and ARABIC_RE.search(text) and text not in seen:
            seen.add(text)
            ctas.append(text)

    # <button> tags
    for btn in soup.find_all('button'):
        _add(btn.get_text(separator=' ', strip=True))

    # <a> and <div>/<span> with role="button"
    for tag in soup.find_all(attrs={'role': 'button'}):
        _add(tag.get_text(separator=' ', strip=True))

    # Elements with button-like CSS classes
    for tag in soup.find_all(class_=_BTN_CLASS_RE):
        _add(tag.get_text(separator=' ', strip=True))

    # <a> with action-oriented Arabic text
    for a in soup.find_all('a'):
        text = clean_arabic_text(a.get_text(separator=' ', strip=True))
        if (text and 3 < len(text) < 80
                and ARABIC_RE.search(text)
                and text not in seen
                and any(kw in text for kw in _ACTION_KEYWORDS)):
            seen.add(text)
            ctas.append(text)

    # <input type="submit|button">
    for inp in soup.find_all('input', type=['submit', 'button']):
        _add(inp.get('value', ''))

    return ctas[:25]


# ─────────────────────────────────────────────
# STEPS 5 — BODY CONTENT + MAIN DESCRIPTION
# ─────────────────────────────────────────────

# Ordered list of content container strategies
_CONTENT_SELECTORS = [
    ('tag',   'main'),
    ('role',  'main'),
    ('tag',   'article'),
    ('id_re', r'(content|main|body|page|app|wrapper)'),
    ('cls_re',r'(content|main|body|page|container|wrapper|inner)'),
    ('tag',   'section'),
]

def _find_main_area(soup):
    for strategy, value in _CONTENT_SELECTORS:
        if strategy == 'tag':
            el = soup.find(value)
        elif strategy == 'role':
            el = soup.find(attrs={'role': value})
        elif strategy == 'id_re':
            el = soup.find(id=re.compile(value, re.I))
        elif strategy == 'cls_re':
            el = soup.find(class_=re.compile(value, re.I))
        else:
            el = None
        if el:
            return el
    return soup.body or soup


def _is_useful(text: str, seen: set) -> bool:
    if not text or len(text) < 15:
        return False
    if is_noise_line(text):
        return False
    if _EXTRA_NOISE.search(text):
        return False
    if not ARABIC_RE.search(text):
        return False
    # Skip if it's fully contained inside an already-seen longer text
    if any(text in s for s in seen):
        return False
    if text in seen:
        return False
    return True


def extract_body(soup) -> tuple:
    """
    Returns (main_description, body_content, missing_reason).
    Extracts real visible content only — no analysis, no generation.
    """
    # Work on a copy so we don't corrupt the soup used by other extractors
    soup = BeautifulSoup(str(soup), 'html.parser')

    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    main_area = _find_main_area(soup)

    lines = []
    seen: set[str] = set()

    # Tier 1: paragraphs and block text — highest value
    for tag in main_area.find_all(['p', 'blockquote', 'li', 'td', 'th']):
        text = clean_arabic_text(tag.get_text(separator=' ', strip=True))
        if _is_useful(text, seen):
            seen.add(text)
            lines.append(text)

    # Tier 2: headings — structural context
    for tag in main_area.find_all(['h1', 'h2', 'h3', 'h4']):
        text = clean_arabic_text(tag.get_text(separator=' ', strip=True))
        if _is_useful(text, seen):
            seen.add(text)
            lines.append(text)

    # Tier 3: divs and spans — only if still thin
    if len('\n'.join(lines)) < MIN_BODY_CHARS:
        for tag in main_area.find_all(['div', 'span', 'label']):
            # Skip containers that duplicate their own p/li children (already captured)
            if tag.find(['p', 'li']):
                continue
            text = clean_arabic_text(tag.get_text(separator=' ', strip=True))
            if _is_useful(text, seen):
                seen.add(text)
                lines.append(text)

    if not lines:
        return "", "", "no_arabic_content_found"

    body_content = '\n'.join(lines[:150])

    # main_description: longest paragraph-length text (80–600 chars)
    candidates = [l for l in lines if 80 <= len(l) <= 600]
    main_description = max(candidates or lines, key=len)

    missing_reason = "" if len(body_content) >= MIN_BODY_CHARS else "thin_content"
    return main_description, body_content, missing_reason


# ─────────────────────────────────────────────
# STEPS 6 & 7 — KEYWORDS + PHRASES
# ─────────────────────────────────────────────

def extract_keywords(text: str, top_n: int = 25, min_freq: int = 2) -> list:
    tokens = ARABIC_RE.findall(text)
    filtered = [t for t in tokens if t not in ARABIC_STOPWORDS and len(t) >= 3]
    counts = Counter(filtered)
    # Prefer words that appear at least min_freq times; fall back if too few
    candidates = [(w, c) for w, c in counts.most_common() if c >= min_freq]
    if len(candidates) < 10:
        candidates = counts.most_common(top_n)
    return [w for w, _ in candidates[:top_n]]


def extract_phrases(text: str, top_n: int = 15, min_freq: int = 2) -> list:
    tokens = ARABIC_RE.findall(text)
    # Only words of 3+ chars reduce noise from particles
    meaningful = [t for t in tokens if len(t) >= 3]

    phrases = []

    for i in range(len(meaningful) - 1):
        a, b = meaningful[i], meaningful[i + 1]
        if a not in ARABIC_STOPWORDS or b not in ARABIC_STOPWORDS:
            phrase = f"{a} {b}"
            if len(phrase) >= 8 and not is_noise_line(phrase):
                phrases.append(phrase)

    for i in range(len(meaningful) - 2):
        a, b, c = meaningful[i], meaningful[i + 1], meaningful[i + 2]
        if sum(1 for w in (a, b, c) if w not in ARABIC_STOPWORDS) >= 2:
            phrase = f"{a} {b} {c}"
            if len(phrase) >= 10 and not is_noise_line(phrase):
                phrases.append(phrase)

    counts = Counter(phrases)
    # Prefer repeated phrases; fall back if too few repeated ones
    candidates = [(ph, c) for ph, c in counts.most_common() if c >= min_freq]
    if len(candidates) < 5:
        candidates = counts.most_common(top_n)
    return [ph for ph, _ in candidates[:top_n]]


# ─────────────────────────────────────────────
# EXTRACTION PIPELINE
# ─────────────────────────────────────────────

def _empty(url: str, reason: str) -> dict:
    return {
        "url"              : url,
        "fetch_status"     : "failed",
        "title"            : "",
        "meta_description" : "",
        "headings"         : [],
        "cta_texts"        : [],
        "main_description" : "",
        "body_content"     : "",
        "keywords_used"    : [],
        "top_phrases"      : [],
        "missing_reason"   : reason,
    }


def extract_page(url: str, label: str = "") -> dict:
    print(f"\n  ► {label or url}")

    # STEP 1: Fetch
    soup = fetch_robust(url)
    if soup is None:
        print("    ✗ fetch failed")
        return _empty(url, "fetch_failed")

    # STEP 2: Title + meta
    title            = extract_title(soup)
    meta_description = extract_meta_description(soup)

    # STEP 3: Headings
    headings = extract_headings(soup)

    # STEP 4: CTAs
    cta_texts = extract_cta_texts(soup)

    # STEP 5: Body
    main_description, body_content, missing_reason = extract_body(soup)

    # Fallback: if body empty but headings exist, use headings as body
    if not body_content and headings:
        body_content     = '\n'.join(h['text'] for h in headings)
        main_description = max(headings, key=lambda h: len(h['text']))['text']
        missing_reason   = "body_from_headings"

    # STEPS 6 & 7: Keywords + phrases from all extracted text combined
    combined = clean_arabic_text(" ".join([
        title,
        meta_description,
        " ".join(h['text'] for h in headings),
        main_description,
        body_content,
    ]))
    keywords_used = extract_keywords(combined, top_n=25)
    top_phrases   = extract_phrases(combined, top_n=15)

    body_len = len(body_content)
    print(f"    title        : {title[:65] or '(missing)'}")
    print(f"    meta_desc    : {(meta_description[:80] + '...') if len(meta_description) > 80 else meta_description or '(missing)'}")
    print(f"    headings     : {len(headings)}")
    print(f"    cta_texts    : {len(cta_texts)}")
    print(f"    body_chars   : {body_len}")
    print(f"    keywords     : {len(keywords_used)}")
    print(f"    phrases      : {len(top_phrases)}")
    if missing_reason:
        print(f"    ⚠ missing    : {missing_reason}")

    return {
        "url"              : url,
        "fetch_status"     : "success",
        "title"            : title,
        "meta_description" : meta_description,
        "headings"         : headings,
        "cta_texts"        : cta_texts,
        "main_description" : main_description,
        "body_content"     : body_content,
        "keywords_used"    : keywords_used,
        "top_phrases"      : top_phrases,
        "missing_reason"   : missing_reason,
    }


# ─────────────────────────────────────────────
# AGENT RUNNER
# ─────────────────────────────────────────────

def run_agent_1() -> dict:
    print("=" * 60)
    print("AGENT 1 v6.0 — Reader / Extractor")
    print("=" * 60)

    output = {
        "agent"           : "agent_1_reader",
        "version"         : "6.0",
        "timestamp"       : time.strftime("%Y-%m-%dT%H:%M:%S"),
        "min_body_chars"  : MIN_BODY_CHARS,
        "our_pages"       : {},
        "competitor_pages": {},
    }

    print("\n[1/2] Our pages ...")
    for key, cfg in OUR_PAGES.items():
        print(f"\n  Product: {cfg['product']}")
        data = extract_page(cfg["url"], f"ours / {cfg['product']}")
        data["product"] = cfg["product"]
        output["our_pages"][key] = data
        time.sleep(2)

    print("\n[2/2] Competitor pages ...")
    for key, competitors in COMPETITOR_PAGES.items():
        product_label = OUR_PAGES[key]["product"]
        output["competitor_pages"][key] = []
        for comp in competitors:
            print(f"\n  Competitor: {comp['brand']} — {product_label}")
            data = extract_page(comp["url"], f"{comp['brand']} / {product_label}")
            data["competitor_name"]  = comp["name"]
            data["competitor_brand"] = comp["brand"]
            data["product"]          = product_label
            output["competitor_pages"][key].append(data)
            time.sleep(2)

    return output


# ─────────────────────────────────────────────
# STEP 8 — SAVE OUTPUT
# ─────────────────────────────────────────────

def save_output(data: dict, path: str = OUTPUT_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  ✓ Saved → {path}")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    result = run_agent_1()

    print("\n" + "=" * 60)
    print("AGENT 1 — Summary")
    print("=" * 60)

    print("\nOur Pages:")
    for k, v in result["our_pages"].items():
        chars  = len(v.get("body_content", ""))
        status = "OK" if chars >= MIN_BODY_CHARS else "THIN"
        reason = v.get("missing_reason", "")
        print(f"  [{status}] {k}: {chars} chars{(' — ' + reason) if reason else ''}")

    print("\nCompetitor Pages:")
    for key, pages in result["competitor_pages"].items():
        for p in pages:
            chars  = len(p.get("body_content", ""))
            status = "OK" if chars >= MIN_BODY_CHARS else "THIN"
            brand  = p.get("competitor_brand", "?")
            reason = p.get("missing_reason", "")
            print(f"  [{status}] [{key}] {brand}: {chars} chars{(' — ' + reason) if reason else ''}")

    save_output(result)
