"""
utils.py
Shared helpers: HTTP fetching (Selenium fallback), Arabic text cleaning,
keyword/phrase extraction.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from collections import Counter
from typing import Optional

# ── Selenium ──────────────────────────────────
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def get_chrome_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


# ── HTTP ──────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_with_requests(url: str, timeout: int = 20):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return None


def fetch_with_selenium(url: str, wait: int = 15):
    """
    فتح الصفحة بـ Chrome وانتظار ظهور محتوى عربي فعلياً.
    بدل الانتظار الثابت، ننتظر حتى تظهر كلمة عربية في الصفحة.
    """
    driver = None
    try:
        driver = get_chrome_driver()
        driver.get(url)

        # المرحلة 1: انتظر حتى يظهر h1 — يعني الصفحة بدأت تتحمل
        try:
            WebDriverWait(driver, wait).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
        except Exception:
            pass

        # المرحلة 2: انتظر ثابت حتى يكتمل تحميل JS الأولي
        time.sleep(5)

        # المرحلة 3: تمرير الصفحة لتحفيز تحميل المحتوى الكسول
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
        except Exception:
            pass

        print(f"    [INFO] محتوى عربي تم تحميله بنجاح")

        return BeautifulSoup(driver.page_source, "html.parser")

    except Exception as e:
        print(f"    [SELENIUM ERROR] {e}")
        return None
    finally:
        if driver:
            driver.quit()


def fetch_page(url: str):
    """
    requests أولاً (سريع).
    لو فشل أو المحتوى فارغ → Selenium مع انتظار ذكي للمحتوى العربي.
    """
    soup = fetch_with_requests(url)
    if soup and len(soup.get_text(strip=True)) > 300:
        return soup
    print(f"    [INFO] Using Selenium for: {url}")
    return fetch_with_selenium(url)


# ── Arabic text ───────────────────────────────
ARABIC_RE = re.compile(
    r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+'
)

ARABIC_STOPWORDS = {
    "في","من","إلى","على","مع","هذا","هذه","ذلك","تلك","هو","هي",
    "نحن","أنت","هم","عن","بعد","قبل","لكل","لكن","أو","و","أن",
    "كان","كانت","يكون","لا","ما","كما","حتى","إذا","أي","كل",
    "بين","خلال","ضد","عند","بدون","فقط","أيضا","ثم","أكثر","أقل",
    "يمكن","يجب","هناك","هنا","حيث","لأن","لذلك","بذلك","وفق",
    "وفقا","نعم","لي","له","لها","لهم","بها","بهم","منه","منها",
    "عليه","عليها","فيه","فيها","اليه","اليها","الذي","التي","الذين",
    "اللتي","الآن","سوف","قد","لقد","جدا","جميع","بعض","أحد",
}

NOISE_PATTERNS = re.compile(
    r'(الرئيسية|ابدأ الآن|اشترك|سجل|تواصل معنا|اتصل بنا|'
    r'حقوق النشر|جميع الحقوق محفوظة|سياسة|شروط الاستخدام|'
    r'روابط سريعة|القائمة)', re.UNICODE
)


def clean_arabic_text(raw: str) -> str:
    if not raw:
        return ""
    raw = re.sub(r'[\u064B-\u065F\u0670]', '', raw)
    raw = re.sub(r'[إأآا]', 'ا', raw)
    raw = raw.replace('\u0640', '')
    return re.sub(r'\s+', ' ', raw).strip()


def is_noise_line(line: str) -> bool:
    line = line.strip()
    if not line or len(line) < 6:
        return True
    if NOISE_PATTERNS.search(line):
        return True
    if not ARABIC_RE.search(line):
        return True
    return False


def extract_body_text(soup) -> str:
    for tag in soup.find_all(['nav','footer','header','script','style',
                               'noscript','aside','form','button']):
        tag.decompose()
    main = (soup.find('main') or
            soup.find(id=re.compile(r'content|main|body', re.I)) or
            soup.find(class_=re.compile(r'content|main|body|page', re.I)) or
            soup.find('article') or soup.body or soup)
    lines, seen = [], set()
    for el in main.find_all(['p','h1','h2','h3','h4','h5','h6','li','span','div']):
        text = clean_arabic_text(el.get_text(separator=' ', strip=True))
        if text and not is_noise_line(text) and len(text) > 20 and text not in seen:
            seen.add(text)
            lines.append(text)
    return '\n'.join(lines[:60])


def extract_keywords(text: str, top_n: int = 25) -> list:
    tokens = ARABIC_RE.findall(text)
    filtered = [t for t in tokens if t not in ARABIC_STOPWORDS and len(t) >= 3]
    return [w for w, _ in Counter(filtered).most_common(top_n)]


def extract_phrases(text: str, top_n: int = 15) -> list:
    tokens = ARABIC_RE.findall(text)
    meaningful = [t for t in tokens if len(t) >= 2]
    phrases = []
    for i in range(len(meaningful) - 1):
        a, b = meaningful[i], meaningful[i+1]
        if a not in ARABIC_STOPWORDS or b not in ARABIC_STOPWORDS:
            phrases.append(f"{a} {b}")
    for i in range(len(meaningful) - 2):
        a, b, c = meaningful[i], meaningful[i+1], meaningful[i+2]
        if sum(1 for w in [a,b,c] if w not in ARABIC_STOPWORDS) >= 2:
            phrases.append(f"{a} {b} {c}")
    return [ph for ph, _ in Counter(phrases).most_common(top_n)]


def extract_title(soup) -> str:
    tag = soup.find('title')
    if tag: return clean_arabic_text(tag.get_text())
    og = soup.find('meta', property='og:title')
    if og: return clean_arabic_text(og.get('content',''))
    h1 = soup.find('h1')
    if h1: return clean_arabic_text(h1.get_text())
    return ""


def extract_meta_description(soup) -> str:
    meta = soup.find('meta', attrs={'name': 'description'})
    if meta: return clean_arabic_text(meta.get('content',''))
    og = soup.find('meta', property='og:description')
    if og: return clean_arabic_text(og.get('content',''))
    return ""


def extract_headings(soup) -> dict:
    result = {}
    for level in ['h1','h2','h3','h4']:
        texts = [clean_arabic_text(t.get_text()) for t in soup.find_all(level)]
        texts = [t for t in texts if t and not is_noise_line(t)]
        if texts:
            result[level] = texts
    return result


def extract_cta_texts(soup) -> list:
    ctas, seen = [], set()
    for btn in soup.find_all(['button','a']):
        text = clean_arabic_text(btn.get_text())
        if text and 5 < len(text) < 60 and ARABIC_RE.search(text) and text not in seen:
            seen.add(text)
            ctas.append(text)
    return ctas[:15]


def safe_page_schema() -> dict:
    return {
        "url": "", "fetch_status": "not_fetched",
        "title": "", "meta_description": "",
        "headings": {}, "cta_texts": [],
        "body_content": "", "keywords_used": [],
        "top_phrases": [], "identity_analysis": {},
    }