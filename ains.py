import json
import time
import re
import os
import logging
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from groq import Groq
from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError as PlaywrightTimeout

# ===========================
# 1. CONFIGURATION
# ===========================
@dataclass
class Config:
    """Centralized configuration for easy customization."""
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_model: str = "llama-3.3-70b-versatile"
    
    base_dir: str = field(default_factory=lambda: os.path.dirname(os.path.abspath(__file__)))
    json_file: str = "book_malay.json"
    progress_file: str = "progress.json"
    log_file: str = "automation.log"
    user_data_dir: str = "ains_stealth_profile"
    screenshots_dir: str = "error_screenshots"
    duplicates_file: str = "duplicates_detected.json"
    
    page_load_timeout: int = 30000
    action_delay: float = 0.5
    retry_delay: float = 2.0
    max_retries: int = 3
    short_delay: float = 0.3
    page_transition_wait: float = 1.0
    modal_wait: float = 0.8  # Optimized for speed
    swal_wait: float = 0.5   # Optimized for speed
    
    default_language: str = "English"
    default_category: str = "Fiksyen"
    book_type: str = "buku"
    
    save_progress: bool = True
    dry_run: bool = False
    verbose: bool = True
    auto_continue: bool = True
    debug_mode: bool = False
    strict_mode: bool = False
    use_ai_verification: bool = True
    fallback_to_simple_detection: bool = True
    skip_book_type_if_on_phase1: bool = True
    add_to_favorites: bool = True
    max_books_to_process: int = 30  # Automatically stop after 30 books
    
    # Enhanced Features
    use_ai_error_recovery: bool = True
    max_recovery_attempts: int = 3
    ai_recovery_wait: float = 1.0
    check_for_duplicates: bool = True
    skip_duplicates: bool = True
    take_screenshots_on_error: bool = False
    auto_retry_on_network_error: bool = True
    adaptive_delays: bool = True
    validate_before_submit: bool = True
    auto_recover_session: bool = True
    max_session_recovery_attempts: int = 3
    health_check_interval: int = 10
    
    ains_url: str = "https://ains.moe.gov.my/"
    
    def get_path(self, filename: str) -> str:
        return os.path.join(self.base_dir, filename)


class BookStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    DUPLICATE = "duplicate"


class FormPhase(Enum):
    INITIAL = "initial"
    BOOK_TYPE_SELECT = "book_type_select"
    PHASE_1_BASIC = "phase_1_basic"
    PHASE_2_SUMMARY = "phase_2_summary"
    PHASE_3_EMPTY = "phase_3_empty"
    PHASE_4_SUBMIT = "phase_4_submit"
    PHASE_5_CONFIRM = "phase_5_confirm"
    FAVORITES = "favorites"
    SUCCESS = "success"
    UNKNOWN = "unknown"


# ===========================
# 2. LANGUAGE DETECTION
# ===========================
class LanguageDetector:
    """Detect language of book content."""
    
    MALAY_WORDS = [
        'dan', 'yang', 'untuk', 'dengan', 'ini', 'itu', 'adalah', 'dalam',
        'pada', 'ke', 'dari', 'oleh', 'akan', 'telah', 'dapat', 'ada',
        'satu', 'mereka', 'kita', 'kami', 'saya', 'anda', 'dia', 'beliau',
        'tetapi', 'jika', 'atau', 'kerana', 'sebagai', 'juga', 'lebih',
        'sebuah', 'buku', 'cerita', 'kisah', 'tentang', 'mengenai'
    ]
    
    ENGLISH_WORDS = [
        'the', 'and', 'for', 'with', 'this', 'that', 'is', 'are', 'was',
        'were', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can',
        'a', 'an', 'of', 'to', 'in', 'on', 'at', 'by', 'from', 'about',
        'book', 'story', 'novel', 'author', 'chapter', 'page'
    ]
    
    CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff]')
    ARABIC_PATTERN = re.compile(r'[\u0600-\u06ff]')
    TAMIL_PATTERN = re.compile(r'[\u0b80-\u0bff]')
    
    LANGUAGE_MAP = {
        'english': 'English',
        'en': 'English',
        'eng': 'English',
        'malay': 'Bahasa Melayu',
        'melayu': 'Bahasa Melayu',
        'bahasa melayu': 'Bahasa Melayu',
        'ms': 'Bahasa Melayu',
        'my': 'Bahasa Melayu',
        'chinese': 'Bahasa Cina',
        'mandarin': 'Bahasa Cina',
        'zh': 'Bahasa Cina',
        'tamil': 'Bahasa Tamil',
        'ta': 'Bahasa Tamil',
        'arabic': 'Bahasa Arab',
        'ar': 'Bahasa Arab',
    }
    
    @classmethod
    def detect(cls, book: Dict, default: str = "English") -> str:
        """Detect language from book data."""
        for field_name in ['language', 'lang', 'bahasa', 'Language', 'LANGUAGE']:
            if field_name in book and book[field_name]:
                lang = str(book[field_name]).lower().strip()
                if lang in cls.LANGUAGE_MAP:
                    return cls.LANGUAGE_MAP[lang]
                for key, value in cls.LANGUAGE_MAP.items():
                    if key in lang or lang in key:
                        return value
        
        text_parts = [
            str(book.get('title', '')),
            str(book.get('summary', '')),
            str(book.get('synopsis', '')),
            str(book.get('description', '')),
            str(book.get('rumusan', '')),
            str(book.get('moral', '')),
            str(book.get('pengajaran', '')),
        ]
        text = ' '.join(text_parts).lower()
        
        if not text.strip():
            return default
        
        if cls.CHINESE_PATTERN.search(text):
            return 'Bahasa Cina'
        if cls.TAMIL_PATTERN.search(text):
            return 'Bahasa Tamil'
        if cls.ARABIC_PATTERN.search(text):
            return 'Bahasa Arab'
        
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        words_lower = [w.lower() for w in words]
        
        malay_count = sum(1 for w in words_lower if w in cls.MALAY_WORDS)
        english_count = sum(1 for w in words_lower if w in cls.ENGLISH_WORDS)
        
        total_words = len(words_lower) if words_lower else 1
        malay_ratio = malay_count / total_words
        english_ratio = english_count / total_words
        
        if english_ratio > malay_ratio and english_ratio > 0.05:
            return 'English'
        elif malay_ratio > english_ratio and malay_ratio > 0.05:
            return 'Bahasa Melayu'
        elif english_ratio > 0.02:
            return 'English'
        elif malay_ratio > 0.02:
            return 'Bahasa Melayu'
        
        return default


# ===========================
# 3. SAFE INPUT FUNCTIONS
# ===========================
def safe_input(prompt: str) -> Optional[str]:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return None


def safe_confirm(prompt: str, default: bool = False) -> bool:
    result = safe_input(prompt)
    if result is None:
        return default
    return result.lower().strip() in ('y', 'yes')


def safe_pause(message: str = "Press Enter to continue..."):
    try:
        input(message)
    except (EOFError, KeyboardInterrupt):
        pass


# ===========================
# 4. JSON EXTRACTION UTILITY (SHARED)
# ===========================
def extract_json_from_text(text: str) -> Optional[Dict]:
    """Shared JSON extraction utility - no more code duplication!"""
    if not text:
        return None
    
    # Try parsing as clean JSON first
    try:
        clean = re.sub(r"```json\s*", "", text)
        clean = re.sub(r"```\s*", "", clean).strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        pass
    
    # Try extracting JSON object from text
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass
    
    return None


def escape_js_string(text: str) -> str:
    """Safely escape string for JavaScript injection."""
    return json.dumps(text)


# ===========================
# 5. CUSTOM EXCEPTIONS
# ===========================
class UnrecoverableError(Exception):
    pass


class APIKeyError(UnrecoverableError):
    pass


class NavigationError(Exception):
    pass


class PhaseVerificationError(Exception):
    pass


class SessionExpiredError(Exception):
    pass


class NetworkError(Exception):
    pass


class DuplicateBookError(Exception):
    pass


class BookSubmittedError(Exception):
    """Raised when book was submitted but navigation failed - NOT a failure!"""
    pass


# ===========================
# 6. LOGGING SETUP
# ===========================
def setup_logging(config: Config) -> logging.Logger:
    # Use getLogger for proper logging hierarchy
    logger = logging.getLogger("BookAutomation")
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    fh = logging.FileHandler(config.get_path(config.log_file), encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if config.debug_mode else logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


# ===========================
# 7. DUPLICATE TRACKER
# ===========================
class DuplicateTracker:
    """Track and detect duplicate books."""
    
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.duplicates_path = config.get_path(config.duplicates_file)
        self.duplicates = self._load()
    
    def _load(self) -> Dict:
        if os.path.exists(self.duplicates_path):
            try:
                with open(self.duplicates_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Ensure required keys exist
                    data.setdefault("detected", [])
                    data.setdefault("book_signatures", {})
                    return data
            except json.JSONDecodeError:
                self.logger.warning("Duplicates file corrupted, starting fresh")
        return {"detected": [], "book_signatures": {}}
    
    def save(self):
        try:
            with open(self.duplicates_path, 'w', encoding='utf-8') as f:
                json.dump(self.duplicates, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.warning(f"Could not save duplicates file: {e}")
    
    def get_signature(self, book: Dict) -> str:
        """Create a unique signature for a book."""
        title = str(book.get('title', '')).lower().strip()
        author = str(book.get('author', '')).lower().strip()
        # Remove special characters and extra spaces
        title = re.sub(r'[^\w\s]', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        author = re.sub(r'[^\w\s]', '', author)
        author = re.sub(r'\s+', ' ', author).strip()
        return f"{title}|{author}"
    
    def is_duplicate(self, book: Dict) -> bool:
        """Check if book is likely a duplicate."""
        signature = self.get_signature(book)
        return signature in self.duplicates.get("book_signatures", {})
    
    def mark_as_processed(self, book: Dict, index: int):
        """Mark a book as processed to detect future duplicates."""
        signature = self.get_signature(book)
        if "book_signatures" not in self.duplicates:
            self.duplicates["book_signatures"] = {}
        
        self.duplicates["book_signatures"][signature] = {
            "index": index,
            "title": book.get('title', ''),
            "author": book.get('author', ''),
            "timestamp": datetime.utcnow().isoformat() + "Z"  # UTC time
        }
        self.save()
    
    def mark_as_duplicate(self, book: Dict, index: int):
        """Mark a book as duplicate."""
        if "detected" not in self.duplicates:
            self.duplicates["detected"] = []
        
        self.duplicates["detected"].append({
            "index": index,
            "title": book.get('title', ''),
            "author": book.get('author', ''),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "signature": self.get_signature(book)
        })
        self.save()


# ===========================
# 8. PROGRESS TRACKER (FIXED)
# ===========================
class ProgressTracker:
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.progress_path = config.get_path(config.progress_file)
        self.data = self._load()
        self.session_start = datetime.now()
        self.books_this_session = 0
        self.failures_this_session = 0
        self.duplicates_this_session = 0
    
    def _load(self) -> Dict:
        default_data = {
            "last_completed_index": -1,
            "books": {},
            "session_start": datetime.now().isoformat(),
            "stats": {"success": 0, "failed": 0, "skipped": 0, "duplicate": 0},
            "total_time_seconds": 0
        }
        
        if os.path.exists(self.progress_path):
            try:
                with open(self.progress_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Ensure all required keys exist (fixes old progress files)
                    data.setdefault("last_completed_index", -1)
                    data.setdefault("books", {})
                    data.setdefault("session_start", datetime.now().isoformat())
                    data.setdefault("total_time_seconds", 0)
                    
                    # Ensure all stat keys exist
                    stats = data.setdefault("stats", {})
                    stats.setdefault("success", 0)
                    stats.setdefault("failed", 0)
                    stats.setdefault("skipped", 0)
                    stats.setdefault("duplicate", 0)
                    
                    return data
            except json.JSONDecodeError:
                self.logger.warning("Progress file corrupted, starting fresh")
        
        return default_data
    
    def save(self):
        try:
            with open(self.progress_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.warning(f"Could not save progress file: {e}")
    
    def mark_book(self, index: int, title: str, status: BookStatus, error: str = None):
        key = str(index)
        
        # Check if already recorded with same status to avoid double-counting
        previous_status = self.data["books"].get(key, {}).get("status")
        
        self.data["books"][key] = {
            "title": title,
            "status": status.value,
            "error": error,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Only update stats if status changed
        if previous_status != status.value:
            # Decrement previous status if exists
            if previous_status:
                try:
                    prev_enum = BookStatus(previous_status)
                    if prev_enum == BookStatus.SUCCESS:
                        self.data["stats"]["success"] = max(0, self.data["stats"]["success"] - 1)
                    elif prev_enum == BookStatus.FAILED:
                        self.data["stats"]["failed"] = max(0, self.data["stats"]["failed"] - 1)
                    elif prev_enum == BookStatus.SKIPPED:
                        self.data["stats"]["skipped"] = max(0, self.data["stats"]["skipped"] - 1)
                    elif prev_enum == BookStatus.DUPLICATE:
                        self.data["stats"]["duplicate"] = max(0, self.data["stats"]["duplicate"] - 1)
                except ValueError:
                    pass
            
            # Increment new status
            if status == BookStatus.SUCCESS:
                self.data["last_completed_index"] = index
                self.data["stats"]["success"] += 1
                self.books_this_session += 1
            elif status == BookStatus.FAILED:
                self.data["stats"]["failed"] += 1
                self.failures_this_session += 1
            elif status == BookStatus.SKIPPED:
                self.data["stats"]["skipped"] += 1
            elif status == BookStatus.DUPLICATE:
                self.data["stats"]["duplicate"] += 1
                self.duplicates_this_session += 1
        
        self.save()
    
    def is_book_completed(self, index: int) -> bool:
        """Check if a book was already successfully completed."""
        key = str(index)
        book_data = self.data["books"].get(key, {})
        return book_data.get("status") == BookStatus.SUCCESS.value
    
    def get_start_index(self) -> int:
        return self.data["last_completed_index"] + 1
    
    def get_stats(self) -> Dict:
        return self.data["stats"]
    
    def reset(self):
        self.data = {
            "last_completed_index": -1,
            "books": {},
            "session_start": datetime.now().isoformat(),
            "stats": {"success": 0, "failed": 0, "skipped": 0, "duplicate": 0},
            "total_time_seconds": 0
        }
        self.save()
        self.logger.info("📍 Progress reset - will start from beginning")
    
    def get_eta(self, current_index: int, total_books: int) -> str:
        if self.books_this_session == 0:
            return "Calculating..."
        
        elapsed = (datetime.now() - self.session_start).total_seconds()
        avg_time = elapsed / self.books_this_session
        remaining = total_books - current_index - 1
        eta_seconds = avg_time * remaining
        
        if eta_seconds < 60:
            return f"{int(eta_seconds)}s"
        elif eta_seconds < 3600:
            return f"{int(eta_seconds / 60)}m {int(eta_seconds % 60)}s"
        else:
            hours = int(eta_seconds / 3600)
            minutes = int((eta_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def get_session_summary(self) -> str:
        elapsed = datetime.now() - self.session_start
        minutes = int(elapsed.total_seconds() / 60)
        seconds = int(elapsed.total_seconds() % 60)
        
        if self.books_this_session > 0:
            avg = elapsed.total_seconds() / self.books_this_session
            avg_str = f"{avg:.1f}s/book"
        else:
            avg_str = "N/A"
        
        return f"Time: {minutes}m {seconds}s | Books: {self.books_this_session} | Avg: {avg_str} | Duplicates: {self.duplicates_this_session}"
    
    def get_submitted_books(self) -> List[Tuple[int, str, str]]:
        """Get list of successfully submitted books: (index, title, timestamp)"""
        submitted = []
        for key, book_data in self.data.get("books", {}).items():
            if book_data.get("status") == BookStatus.SUCCESS.value:
                submitted.append((
                    int(key),
                    book_data.get("title", f"Book {key}"),
                    book_data.get("timestamp", "Unknown")
                ))
        # Sort by index
        submitted.sort(key=lambda x: x[0])
        return submitted
    
    def reset_keep_submitted(self):
        """Reset start index to 0 but keep submitted books record for skipping."""
        # Only reset the start index, keep everything else
        self.data["last_completed_index"] = -1
        self.data["session_start"] = datetime.now().isoformat()
        # Reset session counters
        self.books_this_session = 0
        self.failures_this_session = 0
        self.duplicates_this_session = 0
        self.save()
        self.logger.info("📍 Start index reset to beginning (submitted books will be skipped)")


# ===========================
# 9. AI DUPLICATE DETECTOR
# ===========================
class AIDuplicateDetector:
    """AI-powered duplicate detection in the system."""
    
    def __init__(self, client: Groq, model: str, logger: logging.Logger):
        self.client = client
        self.model = model
        self.logger = logger
    
    def check_if_exists(self, page: Page, book: Dict) -> Tuple[bool, str]:
        """
        Use AI to analyze if the book already exists in the system.
        """
        try:
            page_text = page.inner_text("body")
            
            # Quick check for obvious duplicate messages
            duplicate_keywords = [
                'sudah wujud',
                'already exists',
                'duplicate',
                'pendua',
                'rekod sedia ada',
                'telah didaftarkan'
            ]
            
            page_text_lower = page_text.lower()
            for keyword in duplicate_keywords:
                if keyword in page_text_lower:
                    self.logger.info(f"   🔍 Quick check: Found '{keyword}' in page")
                    return True, f"Duplicate keyword found: {keyword}"
            
            # AI-powered deep analysis
            if self.client:
                prompt = f"""Analyze this webpage to determine if it shows that a book already exists in the system.

BOOK TO CHECK:
Title: {book.get('title', '')}
Author: {book.get('author', '')}

PAGE CONTENT (first 2000 chars):
{page_text[:2000]}

Look for:
1. Duplicate warning messages
2. "Already exists" messages
3. Similar book already in system
4. Error messages about existing records
5. Messages in Malay or English indicating duplication

Respond with JSON:
{{
    "is_duplicate": true/false,
    "confidence": 0.0-1.0,
    "reason": "explanation of why/why not",
    "evidence": "specific text that indicates duplication"
}}
"""
                
                completion = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model,
                    temperature=0.1,
                    max_tokens=300,
                )
                
                response_text = completion.choices[0].message.content
                result = extract_json_from_text(response_text)
                
                if result:
                    is_dup = result.get('is_duplicate', False)
                    confidence = result.get('confidence', 0.0)
                    reason = result.get('reason', 'Unknown')
                    
                    if is_dup and confidence > 0.7:
                        self.logger.info(f"   🤖 AI detected duplicate (conf: {confidence:.2f}): {reason}")
                        return True, reason
            
            return False, "No duplicate detected"
            
        except Exception as e:
            self.logger.debug(f"Duplicate detection error: {e}")
            return False, "Detection failed"


# ===========================
# 10. AI ERROR ANALYZER
# ===========================
class AIErrorAnalyzer:
    """AI-powered error analysis and recovery system."""
    
    def __init__(self, client: Groq, model: str, logger: logging.Logger):
        self.client = client
        self.model = model
        self.logger = logger
    
    def analyze_error(self, page: Page, error_message: str, expected_action: str, current_phase: str) -> Dict[str, Any]:
        """
        Analyze an error situation using AI and suggest recovery actions.
        """
        try:
            page_state = self._capture_page_state(page)
            
            prompt = f"""You are an expert automation debugger analyzing a web automation error.

CONTEXT:
- Current Phase: {current_phase}
- Expected Action: {expected_action}
- Error Message: {error_message}

CURRENT PAGE STATE:
- Page URL: {page_state['url']}
- Page Title: {page_state['title']}
- Visible Text (first 2000 chars): {page_state['text'][:2000]}
- Available Buttons: {page_state['buttons']}
- Input Fields: {page_state['inputs']}
- Error Messages on Page: {page_state['error_messages']}
- Modals/Alerts: {page_state['modals']}

TASK:
Analyze what went wrong and suggest recovery actions. Consider:
1. Is there an error message displayed?
2. Is a modal blocking interaction?
3. Are we on the wrong page?
4. Is the expected button missing or disabled?
5. What should we do to recover?

Respond with a JSON object:
{{
    "problem_detected": "clear description of the problem",
    "likely_cause": "what probably caused this error",
    "severity": "low|medium|high|critical",
    "recovery_possible": true/false,
    "recovery_actions": [
        {{"action": "click_button", "target": "button text", "reason": "why"}},
        {{"action": "wait", "duration": 2, "reason": "why"}},
        {{"action": "refresh_page", "reason": "why"}},
        {{"action": "close_modal", "reason": "why"}},
        {{"action": "navigate_back", "reason": "why"}}
    ],
    "alternative_approach": "if recovery fails, try this instead"
}}
"""
            
            self.logger.info("🤖 AI analyzing error...")
            
            completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.2,
                max_tokens=1000,
            )
            
            response_text = completion.choices[0].message.content
            result = extract_json_from_text(response_text)
            
            if result:
                self.logger.info(f"   🔍 Problem: {result.get('problem_detected', 'Unknown')}")
                self.logger.info(f"   💡 Cause: {result.get('likely_cause', 'Unknown')}")
                self.logger.info(f"   ⚠️  Severity: {result.get('severity', 'unknown')}")
                
                if result.get('recovery_possible'):
                    self.logger.info(f"   ✅ Recovery possible: {len(result.get('recovery_actions', []))} steps")
                else:
                    self.logger.warning("   ❌ AI says recovery not possible")
                
                return result
            
            return {"recovery_possible": False, "problem_detected": "AI analysis failed"}
            
        except Exception as e:
            self.logger.error(f"AI error analysis failed: {e}")
            return {"recovery_possible": False, "problem_detected": str(e)}
    
    def _capture_page_state(self, page: Page) -> Dict[str, Any]:
        """Capture comprehensive page state for AI analysis."""
        try:
            state = {
                'url': page.url,
                'title': page.title(),
                'text': '',
                'buttons': [],
                'inputs': [],
                'error_messages': [],
                'modals': []
            }
            
            try:
                state['text'] = page.inner_text("body")
            except:
                pass
            
            try:
                elements_info = page.evaluate("""() => {
                    function isVisible(el) {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        return style.display !== 'none' && 
                               style.visibility !== 'hidden' && 
                               el.offsetParent !== null;
                    }
                    
                    const allButtons = document.querySelectorAll('button, input[type="submit"], input[type="button"], a.btn');
                    const buttons = Array.from(allButtons)
                        .filter(isVisible)
                        .map(b => ({
                            text: (b.innerText || b.value || '').substring(0, 50),
                            enabled: !b.disabled,
                            type: b.tagName
                        }));
                    
                    const allInputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
                    const inputs = Array.from(allInputs)
                        .filter(isVisible)
                        .map(i => ({
                            type: i.type || i.tagName,
                            placeholder: i.placeholder || '',
                            name: i.name || '',
                            value: i.value ? 'has_value' : 'empty'
                        }));
                    
                    const errorSelectors = ['.error', '.alert-danger', '.text-danger', '[class*="error"]'];
                    const errors = [];
                    errorSelectors.forEach(sel => {
                        const els = document.querySelectorAll(sel);
                        Array.from(els).filter(isVisible).forEach(el => {
                            errors.push(el.innerText.substring(0, 200));
                        });
                    });
                    
                    const modalSelectors = ['.modal', '.swal2-container', '[role="dialog"]'];
                    const modals = [];
                    modalSelectors.forEach(sel => {
                        const els = document.querySelectorAll(sel);
                        Array.from(els).filter(isVisible).forEach(el => {
                            modals.push({
                                type: sel,
                                text: el.innerText.substring(0, 300)
                            });
                        });
                    });
                    
                    return { buttons, inputs, errors, modals };
                }""")
                
                state['buttons'] = elements_info.get('buttons', [])
                state['inputs'] = elements_info.get('inputs', [])
                state['error_messages'] = elements_info.get('errors', [])
                state['modals'] = elements_info.get('modals', [])
                
            except Exception as e:
                self.logger.debug(f"Failed to capture elements: {e}")
            
            return state
            
        except Exception as e:
            self.logger.debug(f"Failed to capture page state: {e}")
            return {
                'url': 'unknown',
                'title': 'unknown',
                'text': '',
                'buttons': [],
                'inputs': [],
                'error_messages': [],
                'modals': []
            }


# ===========================
# 11. SIMPLE PAGE DETECTOR
# ===========================
class SimplePageDetector:
    @staticmethod
    def detect_phase_simple(page: Page, logger: logging.Logger) -> FormPhase:
        try:
            page_text = page.inner_text("body").lower()
            
            # Check for SweetAlert modals first
            try:
                swal_visible = page.evaluate("""() => {
                    const swal = document.querySelector('.swal2-container');
                    return swal && swal.offsetParent !== null;
                }""")
                
                if swal_visible:
                    swal_text = page.evaluate("""() => {
                        const swal = document.querySelector('.swal2-container');
                        return swal ? swal.innerText.toLowerCase() : '';
                    }""")
                    
                    if 'pasti' in swal_text or 'confirm' in swal_text or 'adakah anda pasti' in swal_text:
                        return FormPhase.PHASE_5_CONFIRM
                    if 'berjaya' in swal_text or 'success' in swal_text:
                        return FormPhase.SUCCESS
            except:
                pass
            
            radio_count = page.locator("input[type='radio']").count()
            input_count = page.locator("input[type='text'], input:not([type='radio']):not([type='hidden']):not([type='checkbox']), textarea").count()
            
            logger.debug(f"   Simple detection - Radios: {radio_count}, Inputs: {input_count}")
            
            # Check for favorites page
            if 'tambah ke senarai kegemaran' in page_text or ('senarai kegemaran' in page_text and 'tambah' in page_text):
                return FormPhase.FAVORITES
            
            # Check for success indicators
            if any(word in page_text for word in ['berjaya', 'successfully', 'telah berjaya', 'rekod telah']):
                return FormPhase.SUCCESS
            
            # Check for book type selection
            if 'pilih sumber bacaan' in page_text or ('jenis koleksi' in page_text and radio_count > 0):
                return FormPhase.BOOK_TYPE_SELECT
            
            if radio_count > 0:
                if 'buku' in page_text and ('e-buku' in page_text or 'ebuku' in page_text):
                    return FormPhase.BOOK_TYPE_SELECT
            
            # Check for confirmation
            if 'pasti' in page_text or 'adakah anda pasti' in page_text:
                return FormPhase.PHASE_5_CONFIRM
            
            # Check for submit page
            if 'hantar' in page_text and input_count <= 3:
                return FormPhase.PHASE_4_SUBMIT
            
            # Check for form pages
            if input_count > 0:
                if any(word in page_text for word in ['tajuk', 'penulis', 'penerbit', 'pengarang']):
                    select_count = page.locator("select").count()
                    if select_count > 0:
                        return FormPhase.PHASE_1_BASIC
                
                if any(word in page_text for word in ['rumusan', 'sinopsis', 'pengajaran', 'nilai murni']):
                    return FormPhase.PHASE_2_SUMMARY
            
            # Check for empty phase
            if input_count <= 2:
                if 'seterusnya' in page_text or 'next' in page_text:
                    return FormPhase.PHASE_3_EMPTY
            
            return FormPhase.UNKNOWN
            
        except Exception as e:
            logger.debug(f"Simple detection error: {e}")
            return FormPhase.UNKNOWN


# ===========================
# 12. PAGE ANALYZER (AI-Powered)
# ===========================
class PageAnalyzer:
    def __init__(self, client: Groq, model: str, logger: logging.Logger):
        self.client = client
        self.model = model
        self.logger = logger
    
    def analyze_page(self, page: Page) -> Tuple[FormPhase, Dict[str, Any]]:
        try:
            page_text = page.inner_text("body")[:3000]
            
            elements_info = page.evaluate("""() => {
                function isVisible(el) {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           style.opacity !== '0' &&
                           el.offsetParent !== null;
                }
                
                const allInputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
                const inputs = Array.from(allInputs).filter(isVisible);
                
                const allButtons = document.querySelectorAll('button, input[type="submit"], input[type="button"]');
                const buttons = Array.from(allButtons).filter(isVisible);
                
                const allRadios = document.querySelectorAll('input[type="radio"]');
                const radios = Array.from(allRadios).filter(isVisible);
                
                // Check for SweetAlert
                const swalContainer = document.querySelector('.swal2-container');
                const swalVisible = swalContainer && swalContainer.offsetParent !== null;
                const swalText = swalVisible ? swalContainer.innerText : '';
                
                const inputLabels = inputs.map(el => {
                    let label = '';
                    if (el.id) {
                        const labelEl = document.querySelector(`label[for="${el.id}"]`);
                        if (labelEl) label = labelEl.innerText;
                    }
                    if (!label && el.placeholder) label = el.placeholder;
                    if (!label && el.name) label = el.name;
                    return label.substring(0, 50);
                }).filter(l => l);
                
                const buttonTexts = buttons.map(b => 
                    (b.innerText || b.value || '').substring(0, 30)
                ).filter(t => t);
                
                const radioLabels = radios.map(r => {
                    let label = '';
                    if (r.id) {
                        const labelEl = document.querySelector(`label[for="${r.id}"]`);
                        if (labelEl) label = labelEl.innerText;
                    }
                    if (!label) label = r.value;
                    return label.substring(0, 50);
                }).filter(l => l);
                
                return {
                    inputCount: inputs.length,
                    inputLabels: inputLabels,
                    buttonTexts: buttonTexts,
                    radioCount: radios.length,
                    radioLabels: radioLabels,
                    swalVisible: swalVisible,
                    swalText: swalText.substring(0, 500)
                };
            }""")
            
            prompt = f"""You are analyzing a web page in a book management system to determine which phase of the form we're currently on.

PAGE TEXT (first 3000 chars):
{page_text}

PAGE ELEMENTS:
- Number of input fields: {elements_info['inputCount']}
- Input field labels: {elements_info['inputLabels']}
- Number of radio buttons: {elements_info['radioCount']}
- Radio button labels: {elements_info['radioLabels']}
- Visible buttons: {elements_info['buttonTexts']}
- SweetAlert visible: {elements_info['swalVisible']}
- SweetAlert text: {elements_info['swalText']}

POSSIBLE PHASES:
1. BOOK_TYPE_SELECT - Page with "Pilih sumber bacaan" or radio buttons for "Buku" and "E-Buku"
2. PHASE_1_BASIC - Form with fields: Tajuk, Penulis, Penerbit, Bilangan Mukasurat, and dropdowns for Kategori and Bahasa
3. PHASE_2_SUMMARY - Form with fields: Rumusan and Pengajaran
4. PHASE_3_EMPTY - Page with no input fields (or very few), just a "Seterusnya" button
5. PHASE_4_SUBMIT - Page with a "Hantar" (Submit) button
6. PHASE_5_CONFIRM - Confirmation dialog/SweetAlert with "Pasti" (Confirm) button - IMPORTANT: check swalVisible and swalText
7. FAVORITES - Page asking to add to favorites ("Tambah ke senarai kegemaran")
8. SUCCESS - Success message displayed (words like "berjaya", "successfully", "completed")
9. UNKNOWN - Cannot determine

Analyze the page and respond with ONLY a JSON object:
{{
    "phase": "BOOK_TYPE_SELECT|PHASE_1_BASIC|PHASE_2_SUMMARY|PHASE_3_EMPTY|PHASE_4_SUBMIT|PHASE_5_CONFIRM|FAVORITES|SUCCESS|UNKNOWN",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}
"""
            
            completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.1,
                max_tokens=500,
            )
            
            response_text = completion.choices[0].message.content
            result = extract_json_from_text(response_text)
            
            if result and 'phase' in result:
                phase_str = result['phase']
                try:
                    phase = FormPhase[phase_str]
                    self.logger.debug(f"🤖 AI detected: {phase.value} (conf: {result.get('confidence', 0):.2f})")
                    return phase, result
                except KeyError:
                    self.logger.warning(f"Unknown phase from AI: {phase_str}")
                    return FormPhase.UNKNOWN, result
            
            return FormPhase.UNKNOWN, {}
            
        except Exception as e:
            self.logger.debug(f"AI analysis failed: {e}")
            return FormPhase.UNKNOWN, {}


# ===========================
# 13. BOOK AUTOMATION CLASS (FULLY FIXED)
# ===========================
class BookAutomation:
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.client: Optional[Groq] = None
        self.page: Optional[Page] = None
        self.browser: Optional[BrowserContext] = None
        self.current_book_index = 0
        self.total_books = 0
        self.current_book: Optional[Dict] = None
        self.current_phase: FormPhase = FormPhase.INITIAL
        self.page_analyzer: Optional[PageAnalyzer] = None
        self.error_analyzer: Optional[AIErrorAnalyzer] = None
        self.duplicate_detector: Optional[AIDuplicateDetector] = None
        self.duplicate_tracker: Optional[DuplicateTracker] = None
        self.ai_failures = 0
        self.max_ai_failures = 5
        self.session_recovery_attempts = 0
        self.book_submitted = False  # NEW: Track if current book was submitted
        self.current_delays = {
            'action': config.action_delay,
            'retry': config.retry_delay,
            'short': config.short_delay
        }
        
        # Create screenshots directory
        if config.take_screenshots_on_error:
            os.makedirs(config.get_path(config.screenshots_dir), exist_ok=True)
    
    def initialize_ai(self) -> bool:
        if not self.config.groq_api_key:
            self.logger.error("=" * 60)
            self.logger.error("❌ GROQ_API_KEY NOT SET!")
            self.logger.error("=" * 60)
            self.logger.error("Set it in PowerShell with:")
            self.logger.error('   $env:GROQ_API_KEY = "your_api_key_here"')
            self.logger.error("=" * 60)
            return False
        
        if len(self.config.groq_api_key) < 20:
            self.logger.error("❌ GROQ_API_KEY appears invalid (too short)")
            return False
        
        try:
            self.client = Groq(api_key=self.config.groq_api_key)
            
            self.logger.info("🔌 Testing AI connection...")
            test_response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": "Reply with just: OK"}],
                model=self.config.groq_model,
                max_tokens=5
            )
            
            self.page_analyzer = PageAnalyzer(self.client, self.config.groq_model, self.logger)
            self.error_analyzer = AIErrorAnalyzer(self.client, self.config.groq_model, self.logger)
            self.duplicate_detector = AIDuplicateDetector(self.client, self.config.groq_model, self.logger)
            self.duplicate_tracker = DuplicateTracker(self.config, self.logger)
            
            self.logger.info("✅ AI connection successful!")
            self.logger.info("   🔍 Duplicate detection enabled")
            if self.config.use_ai_error_recovery:
                self.logger.info("   🛡️  AI error recovery enabled")
            return True
            
        except Exception as e:
            error_str = str(e).lower()
            if "401" in error_str or "api key" in error_str or "unauthorized" in error_str:
                self.logger.error(f"❌ Invalid API key: {e}")
            elif "connection" in error_str:
                self.logger.error(f"❌ Cannot connect to Groq API: {e}")
            else:
                self.logger.error(f"❌ AI initialization failed: {e}")
            
            if self.config.fallback_to_simple_detection:
                self.logger.warning("⚠️ Will use simple page detection instead")
                self.config.use_ai_verification = False
                self.config.use_ai_error_recovery = False
                self.config.check_for_duplicates = False
                self.duplicate_tracker = DuplicateTracker(self.config, self.logger)
                return True
            
            return False
    
    def load_books(self) -> List[Dict]:
        json_path = self.config.get_path(self.config.json_file)
        
        if not os.path.exists(json_path):
            self.logger.error(f"Book data file not found: {json_path}")
            return []
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                books = json.load(f)
            
            valid_books = []
            for i, book in enumerate(books):
                if self._validate_book(book, i):
                    valid_books.append(book)
            
            self.total_books = len(valid_books)
            self.logger.info(f"📚 Loaded {len(valid_books)}/{len(books)} valid books")
            return valid_books
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in book file: {e}")
            return []
    
    def _validate_book(self, book: Dict, index: int) -> bool:
        required = ['title']
        missing = [f for f in required if not book.get(f)]
        
        if missing:
            self.logger.warning(f"Book {index} missing fields: {missing}")
            return False
        return True
    
    def take_screenshot(self, name: str):
        """Take a screenshot for debugging."""
        if not self.config.take_screenshots_on_error or not self.page:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{name}.png"
            filepath = self.config.get_path(os.path.join(self.config.screenshots_dir, filename))
            self.page.screenshot(path=filepath)
            self.logger.debug(f"   📸 Screenshot saved: {filename}")
        except Exception as e:
            self.logger.debug(f"Screenshot failed: {e}")
    
    def check_session_validity(self) -> bool:
        """Check if session is still valid."""
        try:
            url = self.page.url
            page_text = self.page.inner_text("body").lower()
            
            # Check for login page indicators
            login_indicators = ['log in', 'login', 'sign in', 'username', 'password']
            if any(indicator in page_text for indicator in login_indicators) and 'logout' not in page_text:
                self.logger.warning("⚠️ Session appears expired (login page detected)")
                return False
            
            # Check if we're on AINS domain
            if 'ains.moe.gov.my' not in url:
                self.logger.warning(f"⚠️ Not on AINS domain: {url}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Session check failed: {e}")
            return True  # Assume valid if check fails
    
    def recover_session(self) -> bool:
        """Attempt to recover expired session."""
        if not self.config.auto_recover_session:
            return False
        
        self.logger.warning("🔄 Attempting session recovery...")
        self.session_recovery_attempts += 1
        
        if self.session_recovery_attempts >= self.config.max_session_recovery_attempts:
            self.logger.error(f"❌ Max session recovery attempts ({self.config.max_session_recovery_attempts}) exceeded")
            return False
        
        try:
            # Navigate back to AINS
            self.page.goto(self.config.ains_url)
            time.sleep(3)
            
            if self.check_session_validity():
                self.logger.info("   ✅ Session recovered!")
                self.session_recovery_attempts = 0
                return True
            
            # Need manual login
            self.logger.warning("   ⚠️ Manual login required")
            print("\n" + "=" * 60)
            print("⚠️  SESSION EXPIRED - PLEASE LOG IN AGAIN")
            print("=" * 60)
            safe_pause("Press Enter after logging in...")
            
            if self.check_session_validity():
                self.logger.info("   ✅ Session restored!")
                self.session_recovery_attempts = 0
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"   ❌ Session recovery failed: {e}")
            return False
    
    def adjust_delays(self, success: bool):
        """Dynamically adjust delays based on success/failure."""
        if not self.config.adaptive_delays:
            return
        
        if success:
            # Speed up slightly on success
            self.current_delays['action'] = max(0.5, self.current_delays['action'] * 0.95)
            self.current_delays['short'] = max(0.3, self.current_delays['short'] * 0.95)
        else:
            # Slow down on failure
            self.current_delays['action'] = min(5.0, self.current_delays['action'] * 1.2)
            self.current_delays['short'] = min(3.0, self.current_delays['short'] * 1.2)
            self.current_delays['retry'] = min(10.0, self.current_delays['retry'] * 1.1)
    
    def perform_health_check(self) -> bool:
        """Perform system health check."""
        self.logger.info("🏥 Performing health check...")
        
        try:
            # Check session
            if not self.check_session_validity():
                self.logger.warning("   ⚠️ Session invalid")
                if not self.recover_session():
                    return False
            
            # Check page responsiveness
            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                self.logger.debug("   ✓ Page responsive")
            except PlaywrightTimeout:
                self.logger.warning("   ⚠️ Page not responding")
                return False
            
            # Check AI if enabled
            if self.config.use_ai_verification and self.client:
                try:
                    test = self.client.chat.completions.create(
                        messages=[{"role": "user", "content": "OK"}],
                        model=self.config.groq_model,
                        max_tokens=5,
                    )
                    self.logger.debug("   ✓ AI connection OK")
                except Exception as e:
                    self.logger.warning(f"   ⚠️ AI connection issue: {e}")
                    # Continue anyway
            
            self.logger.info("   ✅ Health check passed")
            return True
            
        except Exception as e:
            self.logger.error(f"   ❌ Health check failed: {e}")
            return False
    
    def wait_for_page_ready(self, timeout: int = None) -> bool:
        """Wait for page to be ready - REDUCED timeouts (was 30s, now 5s max)."""
        # Use shorter timeout for form interactions (not initial page load)
        # Initial page load uses full timeout, subsequent waits use 5 seconds
        timeout = timeout or 5000  # 5 seconds instead of 30 seconds
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
            try:
                self.page.wait_for_load_state("networkidle", timeout=min(timeout, 3000))
            except PlaywrightTimeout:
                pass  # Network idle timeout is OK - page still functional
            time.sleep(self.current_delays['short'])
            return True
        except PlaywrightTimeout:
            self.logger.debug(f"Page ready timeout ({timeout}ms) - continuing anyway")
            return False
    
    def wait_for_swal_modal(self, timeout: float = 1.0) -> bool:
        """Wait for SweetAlert modal to appear - IMPROVED detection."""
        start_time = time.time()
        check_interval = 0.05  # Check every 50ms instead of 150ms
        while time.time() - start_time < timeout:
            try:
                swal_visible = self.page.evaluate("""() => {
                    const swal = document.querySelector('.swal2-popup, .swal2-modal');
                    if (!swal) return false;
                    const style = window.getComputedStyle(swal);
                    return style.display !== 'none' && style.visibility !== 'hidden';
                }""")
                if swal_visible:
                    self.logger.debug("   ✓ SweetAlert modal detected")
                    return True
            except:
                pass
            time.sleep(check_interval)
        return False
    
    def close_swal_modal(self, button_texts: List[str] = None) -> bool:
        """Close SweetAlert modal by clicking specified button - IMPROVED with proper detection."""
        if button_texts is None:
            button_texts = ["OK", "Pasti", "Ya", "Yes", "Confirm", "Tidak", "No", "Cancel", "Batal"]
        
        try:
            # Better SweetAlert visibility detection using computed styles
            swal_info = self.page.evaluate("""() => {
                const swal = document.querySelector('.swal2-popup, .swal2-modal');
                if (!swal) return { visible: false, hasButtons: 0, text: '' };
                
                const style = window.getComputedStyle(swal);
                const isVisible = style.display !== 'none' && 
                                 style.visibility !== 'hidden' && 
                                 parseFloat(style.opacity) > 0.1;
                
                if (!isVisible) return { visible: false, hasButtons: 0, text: '' };
                
                const buttons = swal.querySelectorAll('button');
                const text = (swal.innerText || '').substring(0, 300).toLowerCase();
                return { 
                    visible: true, 
                    hasButtons: buttons.length,
                    text: text
                };
            }""")
            
            if not swal_info.get('visible'):
                return False
            
            self.logger.debug(f"   📦 SweetAlert found with {swal_info.get('hasButtons')} button(s)")
            
            # Try clicking buttons in order of preference
            for btn_text in button_texts:
                btn_text_lower = btn_text.lower()
                # Use json.dumps to safely escape the string for JavaScript
                clicked = self.page.evaluate(f"""() => {{
                    const searchText = {json.dumps(btn_text_lower)};
                    const buttons = document.querySelectorAll('.swal2-popup button, .swal2-confirm, .swal2-cancel, .swal2-deny');
                    for (const btn of buttons) {{
                        const text = (btn.innerText || btn.textContent || btn.getAttribute('aria-label') || '').toLowerCase().trim();
                        if (text === searchText || text.includes(searchText)) {{
                            const style = window.getComputedStyle(btn);
                            if (style.display !== 'none' && style.visibility !== 'hidden') {{
                                btn.click();
                                return true;
                            }}
                        }}
                    }}
                    return false;
                }}""")
                
                if clicked:
                    self.logger.debug(f"   ✓ Clicked SweetAlert button: {btn_text}")
                    time.sleep(self.config.swal_wait)
                    return True
            
            # Fallback: click the first visible button if no text match
            clicked = self.page.evaluate("""() => {
                const buttons = document.querySelectorAll('.swal2-popup button');
                for (const btn of buttons) {
                    const style = window.getComputedStyle(btn);
                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }""")
            
            if clicked:
                self.logger.debug("   ✓ Clicked SweetAlert button (fallback)")
                time.sleep(self.config.swal_wait)
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"SweetAlert close failed: {e}")
            return False
    
    def close_modal_if_present(self) -> bool:
        """Close any modal dialogs that might be blocking interactions."""
        try:
            # Check if SweetAlert exists with better detection
            swal_exists = self.page.evaluate("""() => {
                const swal = document.querySelector('.swal2-popup, .swal2-modal');
                if (!swal) return false;
                const style = window.getComputedStyle(swal);
                return style.display !== 'none';
            }""")
            
            if swal_exists:
                # Try to close it
                if self.close_swal_modal(["OK", "Tutup", "Close", "Ya", "Tidak"]):
                    return True
            
            # Try generic modal close (Bootstrap)
            closed = self.page.evaluate("""() => {
                const modalCloseBtn = document.querySelector('.modal.show .btn-close, .modal.show .close, .modal.show [data-dismiss="modal"]');
                if (modalCloseBtn) {
                    modalCloseBtn.click();
                    return true;
                }
                return false;
            }""")
            
            if closed:
                self.logger.debug("   ✓ Closed modal")
                time.sleep(self.config.modal_wait)
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Modal close attempt failed: {e}")
            return False
    
    def detect_current_phase(self) -> Tuple[FormPhase, Dict]:
        # Check for SweetAlert first (quick check) - IMPROVED detection
        try:
            swal_info = self.page.evaluate("""() => {
                const swal = document.querySelector('.swal2-popup, .swal2-modal');
                if (!swal) return { visible: false, text: '' };
                
                const style = window.getComputedStyle(swal);
                const isVisible = style.display !== 'none' &&
                                 style.visibility !== 'hidden' &&
                                 parseFloat(style.opacity) > 0.1;
                
                if (!isVisible) return { visible: false, text: '' };
                
                const text = (swal.innerText || swal.textContent || '').toLowerCase();
                return {
                    visible: true,
                    text: text.substring(0, 500)
                };
            }""")
            
            if swal_info.get('visible'):
                swal_text = swal_info.get('text', '')
                # Check for confirmation (must add Pasti/Confirm types)
                if any(x in swal_text for x in ['pasti', 'adakah anda pasti', 'confirm', 'are you sure']):
                    return FormPhase.PHASE_5_CONFIRM, {"method": "swal_quick", "swal_text": swal_text[:100]}
                # Check for success
                if any(x in swal_text for x in ['berjaya', 'success', 'telah berjaya', 'submitted', 'saved']):
                    return FormPhase.SUCCESS, {"method": "swal_quick", "swal_text": swal_text[:100]}
                # Generic SweetAlert visible - return its text for debugging
                self.logger.debug(f"   📦 SweetAlert visible: {swal_text[:50]}...")
        except Exception as e:
            self.logger.debug(f"SweetAlert detection error: {e}")
        
        if self.config.use_ai_verification and self.ai_failures < self.max_ai_failures and self.page_analyzer:
            try:
                phase, details = self.page_analyzer.analyze_page(self.page)
                if phase != FormPhase.UNKNOWN:
                    self.ai_failures = 0
                    return phase, details
                else:
                    self.ai_failures += 1
            except Exception as e:
                self.logger.debug(f"AI detection failed: {e}")
                self.ai_failures += 1
        
        if self.ai_failures >= self.max_ai_failures:
            if self.config.use_ai_verification:
                self.logger.warning(f"⚠️ Switching to simple detection (AI failed {self.ai_failures}x)")
                self.config.use_ai_verification = False
        
        if self.config.fallback_to_simple_detection:
            self.logger.debug("   Using simple detection...")
            phase = SimplePageDetector.detect_phase_simple(self.page, self.logger)
            return phase, {"method": "simple", "phase": phase.value}
        
        return FormPhase.UNKNOWN, {}
    
    def execute_recovery_action(self, action: Dict) -> bool:
        """Execute a recovery action suggested by AI."""
        action_type = action.get('action', '')
        
        try:
            if action_type == 'click_button':
                target = action.get('target', '')
                self.logger.info(f"   🔧 Recovery: Clicking '{target}'")
                return self.click_button_safe([target], force_js=True)
            
            elif action_type == 'wait':
                duration = action.get('duration', 2)
                self.logger.info(f"   ⏳ Recovery: Waiting {duration}s")
                time.sleep(duration)
                return True
            
            elif action_type == 'refresh_page':
                self.logger.info("   🔄 Recovery: Refreshing page")
                self.page.reload()
                self.wait_for_page_ready()
                return True
            
            elif action_type == 'close_modal':
                self.logger.info("   ❌ Recovery: Closing modal")
                self.close_modal_if_present()
                return True
            
            elif action_type == 'navigate_back':
                self.logger.info("   ⬅️  Recovery: Going back")
                self.page.go_back()
                self.wait_for_page_ready()
                return True
            
            else:
                self.logger.warning(f"   ⚠️  Unknown recovery action: {action_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"   ❌ Recovery action failed: {e}")
            return False
    
    def attempt_ai_recovery(self, error: Exception, expected_action: str, phase: str) -> bool:
        """Use AI to analyze error and attempt recovery."""
        if not self.config.use_ai_error_recovery or not self.error_analyzer:
            return False
        
        self.logger.info("🤖 Attempting AI-powered error recovery...")
        
        try:
            self.take_screenshot(f"error_{phase}_{self.current_book_index}")
            
            analysis = self.error_analyzer.analyze_error(
                self.page,
                str(error),
                expected_action,
                phase
            )
            
            if not analysis.get('recovery_possible'):
                self.logger.warning("   ❌ AI says recovery not possible")
                return False
            
            recovery_actions = analysis.get('recovery_actions', [])
            if not recovery_actions:
                self.logger.warning("   ⚠️  No recovery actions suggested")
                return False
            
            self.logger.info(f"   📋 Executing {len(recovery_actions)} recovery steps...")
            
            for i, action in enumerate(recovery_actions):
                self.logger.info(f"   Step {i+1}/{len(recovery_actions)}: {action.get('action', 'unknown')}")
                self.logger.debug(f"      Reason: {action.get('reason', 'N/A')}")
                
                if not self.execute_recovery_action(action):
                    self.logger.warning(f"   ⚠️  Step {i+1} failed, trying next...")
                    continue
                
                time.sleep(self.config.ai_recovery_wait)
            
            time.sleep(self.config.action_delay)
            detected_phase, _ = self.detect_current_phase()
            
            if detected_phase != FormPhase.UNKNOWN:
                self.logger.info(f"   ✅ Recovery successful! Now on: {detected_phase.value}")
                return True
            else:
                self.logger.warning("   ⚠️  Recovery attempted but page state unclear")
                
                alt_approach = analysis.get('alternative_approach', '')
                if alt_approach:
                    self.logger.info(f"   💡 Alternative: {alt_approach}")
                
                return False
                
        except Exception as e:
            self.logger.error(f"   ❌ AI recovery failed: {e}")
            return False
    
    def check_for_duplicate(self, book: Dict) -> Tuple[bool, str]:
        """
        Check if book is a duplicate using multiple methods.
        Returns: (is_duplicate, reason)
        """
        if not self.config.check_for_duplicates:
            return False, ""
        
        # Method 1: Check local cache
        if self.duplicate_tracker and self.duplicate_tracker.is_duplicate(book):
            reason = "Already processed in this session"
            self.logger.info(f"   🔍 Duplicate (local): {reason}")
            return True, reason
        
        # Method 2: AI-powered page analysis
        if self.config.use_ai_verification and self.duplicate_detector:
            try:
                is_dup, reason = self.duplicate_detector.check_if_exists(self.page, book)
                if is_dup:
                    self.logger.info(f"   🔍 Duplicate (AI): {reason}")
                    return True, reason
            except Exception as e:
                self.logger.debug(f"AI duplicate check failed: {e}")
        
        return False, ""
    
    def validate_form_before_submit(self, phase: str) -> Tuple[bool, List[str]]:
        """
        Validate form fields before submission.
        Returns: (is_valid, list of issues)
        """
        if not self.config.validate_before_submit:
            return True, []
        
        issues = []
        
        try:
            # Check for empty required fields
            empty_fields = self.page.evaluate("""() => {
                const inputs = document.querySelectorAll('input[required], textarea[required], select[required]');
                const empty = [];
                inputs.forEach(input => {
                    if (!input.value || input.value.trim() === '') {
                        const label = document.querySelector(`label[for="${input.id}"]`);
                        empty.push(label ? label.innerText : input.name || 'Unknown field');
                    }
                });
                return empty;
            }""")
            
            if empty_fields:
                issues.append(f"Empty required fields: {', '.join(empty_fields)}")
            
            # Check for validation errors on page
            errors = self.page.evaluate("""() => {
                const errorElements = document.querySelectorAll('.error, .invalid-feedback, .text-danger');
                return Array.from(errorElements)
                    .filter(el => el.offsetParent !== null)
                    .map(el => el.innerText.substring(0, 100));
            }""")
            
            if errors:
                issues.append(f"Validation errors: {'; '.join(errors)}")
            
            if issues:
                self.logger.warning(f"   ⚠️ Form validation issues: {issues}")
                return False, issues
            
            self.logger.debug("   ✓ Form validation passed")
            return True, []
            
        except Exception as e:
            self.logger.debug(f"Form validation check failed: {e}")
            return True, []  # Assume valid if check fails
    
    def click_button_safe(self, button_texts: List[str], wait_after: float = None, force_js: bool = False) -> bool:
        """Safely click button by text."""
        wait_time = wait_after if wait_after is not None else self.current_delays['action']
        self.close_modal_if_present()
        
        for btn_text in button_texts:
            try:
                # Try Playwright's get_by_role first
                if not force_js:
                    button = self.page.get_by_role("button", name=btn_text, exact=False).first
                    if button.is_visible(timeout=1000):
                        button.click(timeout=5000)
                        time.sleep(wait_time)
                        try:
                            self.page.wait_for_load_state("networkidle", timeout=3000)
                        except:
                            pass
                        return True
            except Exception:
                pass
        
        # JavaScript fallback
        for btn_text in button_texts:
            try:
                btn_text_lower = btn_text.lower().strip()
                clicked = self.page.evaluate(f"""() => {{
                    const st = {json.dumps(btn_text_lower)};
                    for (const tag of ['button', 'a', 'input']) {{
                        for (const el of document.querySelectorAll(tag)) {{
                            const t = ((el.innerText || el.value || el.textContent || '') + '').toLowerCase();
                            if (t.includes(st)) {{ el.click(); return true; }}
                        }}
                    }}
                    return false;
                }}""")
                if clicked:
                    time.sleep(wait_time)
                    try:
                        self.page.wait_for_load_state("networkidle", timeout=3000)
                    except:
                        pass
                    return True
            except Exception:
                pass
        
        return False
    
    # ===========================
    
    def handle_favorites_page(self) -> bool:
        """Handle the favorites page that appears after success - FIXED logic."""
        self.logger.info("⭐ Favorites Page")
        
        try:
            time.sleep(self.config.modal_wait)
            
            # Wait for page to stabilize
            try:
                self.page.wait_for_load_state("networkidle", timeout=2000)
            except:
                pass
            
            if self.config.add_to_favorites:
                # === TRY TO ADD TO FAVORITES ===
                add_buttons = [
                    "Tambah ke senarai kegemaran",  # Malay - Full text
                    "Tambah kegemaran",  # Malay - Short text
                    "Tambah",  # Malay - Just "Add"
                    "Add to favorites",  # English - Full text
                    "Add",  # English - Just "Add"
                    "Ya",  # Malay - "Yes"
                    "Yes",  # English - "Yes"
                ]
                
                success = self.click_button_safe(add_buttons, force_js=False)
                if not success:
                    # SweetAlert might be visible
                    success = self.close_swal_modal(["Tambah", "Add", "Ya", "Yes"])
                
                if success:
                    self.logger.info("   ✅ Added to favorites")
                    time.sleep(0.5)
                else:
                    self.logger.warning("   ⚠️ Could not detect add button - modal might auto-close")
            else:
                # === TRY TO SKIP/CLOSE FAVORITES ===
                skip_buttons = [
                    "Tidak",  # Malay - "No"
                    "Batal",  # Malay - "Cancel"
                    "Langkau",  # Malay - "Skip"
                    "Tutup",  # Malay - "Close"
                    "No",  # English - "No"
                    "Cancel",  # English - "Cancel"
                    "Skip",  # English - "Skip"
                    "Close",  # English - "Close"
                ]
                
                success = self.click_button_safe(skip_buttons, force_js=False)
                if not success:
                    # SweetAlert might be visible
                    success = self.close_swal_modal(skip_buttons)
                
                if success:
                    self.logger.info("   ⏭️ Skipped favorites")
                    time.sleep(0.5)
                else:
                    # Try OK as last resort
                    if self.close_swal_modal(["OK"]):
                        self.logger.info("   ⏭️ Closed favorites with OK")
                    else:
                        self.logger.warning("   ⚠️ Could not detect skip button - modal might auto-close")
            
            # Verify modal closed by checking it's gone
            time.sleep(0.5)
            modal_still_visible = self.page.evaluate("""() => {
                const swal = document.querySelector('.swal2-popup, .swal2-modal');
                if (!swal) return false;
                const style = window.getComputedStyle(swal);
                return style.display !== 'none';
            }""")
            
            if modal_still_visible:
                self.logger.debug("   Modal still visible, closing...")
                self.close_modal_if_present()
            
            time.sleep(self.current_delays['action'])
            return True
            
        except Exception as e:
            self.logger.warning(f"   ⚠️ Favorites handling error: {e}")
            # Try to recover by closing any modal
            self.close_modal_if_present()
            return True  # Don't fail the whole book for this
    
    def navigate_to_new_book_form(self) -> bool:
        """Navigate to start a new book entry - the main fix for 'must select buku/e-buku manually'."""
        self.logger.info("🔄 Navigating to new book form...")
        
        max_attempts = 15
        for attempt in range(max_attempts):
            try:
                time.sleep(self.current_delays['short'])
                detected_phase, _ = self.detect_current_phase()
                
                self.logger.debug(f"   Attempt {attempt + 1}: Current phase = {detected_phase.value}")
                
                # Success conditions
                if detected_phase == FormPhase.BOOK_TYPE_SELECT:
                    self.logger.info("   ✅ Ready for new book (book type selection)")
                    return True
                
                if detected_phase == FormPhase.PHASE_1_BASIC:
                    self.logger.info("   ✅ Ready for new book (Phase 1)")
                    return True
                
                # Handle different pages
                if detected_phase == FormPhase.SUCCESS:
                    self.logger.debug("   On success page, looking for next actions...")
                    
                    # Close any success SweetAlert
                    if self.close_swal_modal(["OK", "Tutup", "Close"]):
                        time.sleep(self.current_delays['short'])
                        continue
                    
                    # Look for "Tambah Rekod" or similar buttons
                    nav_buttons = [
                        "Tambah Rekod Baru",
                        "Tambah Rekod", 
                        "Rekod Seterusnya",
                        "Rekod Baru",
                        "Tambah Bahan",
                        "Seterusnya",
                        "OK"
                    ]
                    
                    for btn in nav_buttons:
                        if self.click_button_safe([btn], force_js=True):
                            self.logger.debug(f"   Clicked '{btn}', waiting for navigation...")
                            # Wait for page to actually navigate
                            time.sleep(self.current_delays['action'])
                            try:
                                self.page.wait_for_load_state("networkidle", timeout=3000)
                            except:
                                pass
                            break
                    
                    continue
                
                elif detected_phase == FormPhase.FAVORITES:
                    self.handle_favorites_page()
                    continue
                
                elif detected_phase == FormPhase.PHASE_5_CONFIRM:
                    # Shouldn't be here during navigation, but handle it
                    self.logger.debug("   On confirm page during navigation, skipping...")
                    # Don't try to interact, just wait and let page settle
                    time.sleep(self.current_delays['action'])
                    continue
                
                elif detected_phase in [FormPhase.PHASE_3_EMPTY, FormPhase.PHASE_4_SUBMIT]:
                    # We're in the middle of a form, something went wrong
                    self.logger.debug("   In middle of form, trying navigation...")
                    
                    # Try clicking various navigation elements
                    nav_tried = False
                    for btn in ["Kembali", "Back", "Batal", "Cancel"]:
                        if self.click_button_safe([btn], force_js=True):
                            nav_tried = True
                            break
                    
                    if not nav_tried:
                        # Try refreshing or going to main URL
                        self.logger.debug("   Trying to navigate via sidebar/menu...")
                        menu_clicked = self.page.evaluate("""() => {
                            // Look for sidebar/menu items
                            const menuItems = document.querySelectorAll('a[href*="koleksi"], a[href*="bahan"], .nav-link, .sidebar-link');
                            for (const item of menuItems) {
                                const text = item.innerText.toLowerCase();
                                if (text.includes('tambah') || text.includes('koleksi') || text.includes('bahan')) {
                                    item.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")
                        
                        if menu_clicked:
                            self.logger.debug("   Clicked menu item, waiting for page load...")
                            time.sleep(self.current_delays['action'])
                            try:
                                self.page.wait_for_load_state("networkidle", timeout=3000)
                            except:
                                pass
                    
                    continue
                
                else:
                    # Unknown phase - try common actions
                    self.logger.debug(f"   Unknown phase, trying common navigation...")
                    
                    # Close any modals first
                    self.close_modal_if_present()
                    
                    # Try common navigation buttons
                    common_buttons = [
                        ["OK"],
                        ["Tambah Rekod", "Tambah Rekod Baru"],
                        ["Seterusnya", "Next"],
                        ["Kembali", "Back"],
                    ]
                    
                    clicked = False
                    for button_list in common_buttons:
                        if self.click_button_safe(button_list, force_js=True):
                            clicked = True
                            break
                    
                    if not clicked:
                        # Try finding a link to add new record
                        self.page.evaluate("""() => {
                            const links = document.querySelectorAll('a');
                            for (const link of links) {
                                const text = link.innerText.toLowerCase();
                                if (text.includes('tambah') && (text.includes('rekod') || text.includes('bahan'))) {
                                    link.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")
                    
                    time.sleep(self.current_delays['action'])
                
            except Exception as e:
                self.logger.warning(f"   ⚠️  Navigation error (attempt {attempt + 1}): {e}")
                time.sleep(self.current_delays['short'])
        
        # Final check
        detected_phase, _ = self.detect_current_phase()
        if detected_phase in [FormPhase.BOOK_TYPE_SELECT, FormPhase.PHASE_1_BASIC]:
            self.logger.info(f"   ✅ Successfully navigated to {detected_phase.value}")
            return True
        
        # If stuck at success or favorites, try closing them
        if detected_phase in [FormPhase.SUCCESS, FormPhase.FAVORITES]:
            self.logger.debug(f"   Still at {detected_phase.value}, closing...")
            self.close_modal_if_present()
            time.sleep(self.current_delays['action'])
            detected_phase, _ = self.detect_current_phase()
            if detected_phase in [FormPhase.BOOK_TYPE_SELECT, FormPhase.PHASE_1_BASIC]:
                return True
        
        self.logger.error(f"   ❌ Could not navigate to new book form (stuck at: {detected_phase.value})")
        return False
    
    def handle_book_type_selection(self) -> bool:
        """Handle Phase 0: Book type selection (Buku/E-Buku) - SIMPLE SINGLE ACTION."""
        self.logger.info("📖 Phase 0: Book Type Selection")
        
        try:
            detected_phase, _ = self.detect_current_phase()
            
            # If already on Phase 1 or other phase, we're good
            if detected_phase != FormPhase.BOOK_TYPE_SELECT:
                self.logger.debug(f"   ℹ️ Not on book type page (on {detected_phase.value}), skipping")
                return True
            
            # Single simple action: Click Buku/E-Buku card
            self.logger.debug("   Clicking Buku/E-Buku card...")
            buku_card = self.page.locator('text="Buku/E-Buku"').first
            
            if buku_card.is_visible():
                buku_card.click()
                time.sleep(0.3)
            
            # Click Next button
            self.logger.debug("   Clicking Next button...")
            self.click_button_safe(["Seterusnya", "Next"], force_js=True)
            time.sleep(self.current_delays['short'])
            
            self.logger.info("   ✅ Phase 0 complete")
            return True
            
        except Exception as e:
            self.logger.debug(f"   ⚠️ Phase 0 error: {e}")
            return False

            
        except Exception as e:
            self.logger.error(f"   ❌ Phase 0 error: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return False
    
    def handle_phase_1_basic(self, book: Dict) -> bool:
        """Handle Phase 1: Basic info."""
        self.logger.info("📝 Phase 1: Basic Information")
        
        try:
            phase_data = {
                'tajuk': book.get('title', ''),
                'penulis': book.get('author', ''),
                'pengarang': book.get('author', ''),
                'penerbit': book.get('publisher', ''),
                'bilangan mukasurat': str(book.get('pages', '')),
                'halaman': str(book.get('pages', '')),
            }
            
            self._fill_form_fields(phase_data)
            
            # Fill dropdowns (check return value)
            if not self._fill_dropdowns(book):
                self.logger.debug("   ⚠️ Some dropdowns may not have been filled")
            
            # Validate before proceeding
            is_valid, issues = self.validate_form_before_submit("Phase 1")
            if not is_valid:
                self.logger.warning(f"   ⚠️ Validation issues: {issues}")
                self.take_screenshot(f"phase1_validation_fail_{self.current_book_index}")
            
            time.sleep(self.current_delays['short'])
            
            if not self.config.dry_run:
                if not self.click_button_safe(["Seterusnya", "Next"], force_js=True):
                    self.logger.warning("   ⚠️ Could not find 'Seterusnya' button")
                    return False
            
            self.logger.info("   ✅ Phase 1 complete")
            return True
            
        except Exception as e:
            self.logger.error(f"   ❌ Error in Phase 1: {e}")
            self.take_screenshot(f"phase1_error_{self.current_book_index}")
            if self.attempt_ai_recovery(e, "complete Phase 1 basic info form", "PHASE_1_BASIC"):
                return True
            raise
    
    def handle_phase_2_summary(self, book: Dict) -> bool:
        """Handle Phase 2: Summary and moral."""
        self.logger.info("📝 Phase 2: Summary & Moral")
        
        try:
            phase_data = {
                'rumusan': book.get('summary', book.get('synopsis', book.get('rumusan', ''))),
                'sinopsis': book.get('summary', book.get('synopsis', '')),
                'pengajaran': book.get('moral', book.get('pengajaran', '')),
                'moral': book.get('moral', ''),
                'nilai murni': book.get('moral', book.get('pengajaran', '')),
            }
            
            self._fill_form_fields(phase_data)
            
            # Validate before proceeding
            is_valid, issues = self.validate_form_before_submit("Phase 2")
            if not is_valid:
                self.logger.warning(f"   ⚠️ Validation issues: {issues}")
                self.take_screenshot(f"phase2_validation_fail_{self.current_book_index}")
            
            time.sleep(self.current_delays['short'])
            
            if not self.config.dry_run:
                if not self.click_button_safe(["Seterusnya", "Next"], force_js=True):
                    self.logger.warning("   ⚠️ Could not find 'Seterusnya' button")
                    return False
            
            self.logger.info("   ✅ Phase 2 complete")
            return True
            
        except Exception as e:
            self.logger.error(f"   ❌ Error in Phase 2: {e}")
            self.take_screenshot(f"phase2_error_{self.current_book_index}")
            if self.attempt_ai_recovery(e, "complete Phase 2 summary form", "PHASE_2_SUMMARY"):
                return True
            raise
    
    def handle_phase_3_empty(self) -> bool:
        """Handle Phase 3: Empty page."""
        self.logger.info("📝 Phase 3: Additional Info (Empty)")
        
        try:
            if not self.config.dry_run:
                if not self.click_button_safe(["Seterusnya", "Next"], force_js=True):
                    self.logger.warning("   ⚠️ Could not find 'Seterusnya' button")
                    return False
            
            self.logger.info("   ✅ Phase 3 complete")
            return True
            
        except Exception as e:
            self.logger.error(f"   ❌ Error in Phase 3: {e}")
            if self.attempt_ai_recovery(e, "skip Phase 3 empty page", "PHASE_3_EMPTY"):
                return True
            raise
    
    def handle_phase_4_submit(self) -> bool:
        """Handle Phase 4: Submit."""
        self.logger.info("📤 Phase 4: Submit")
        
        try:
            # Final validation
            is_valid, issues = self.validate_form_before_submit("Phase 4")
            if not is_valid:
                self.logger.warning(f"   ⚠️ Pre-submit validation issues: {issues}")
                self.take_screenshot(f"phase4_validation_fail_{self.current_book_index}")
            
            if not self.config.dry_run:
                if not self.click_button_safe(["Hantar", "Submit"], wait_after=1.5, force_js=True):
                    self.logger.error("   ❌ Could not find 'Hantar' button")
                    return False
            
            self.logger.info("   ✅ Clicked 'Hantar'")
            return True
            
        except Exception as e:
            self.logger.error(f"   ❌ Error in Phase 4: {e}")
            self.take_screenshot(f"phase4_error_{self.current_book_index}")
            if self.attempt_ai_recovery(e, "click Hantar button", "PHASE_4_SUBMIT"):
                return True
            raise
    
    def handle_phase_5_confirm(self) -> bool:
        """Handle Phase 5: Confirmation - OPTIMIZED VERSION."""
        self.logger.info("✔️ Phase 5: Confirm")
        
        try:
            if not self.config.dry_run:
                # Wait briefly for SweetAlert to appear
                self.logger.debug("   Waiting for confirmation dialog...")
                self.wait_for_swal_modal(timeout=1.5)
                
                # Optimized: Single comprehensive button finder
                confirm_buttons = ["Pasti", "Ya", "Yes", "Confirm", "OK", "Sahkan"]
                
                # Combined search: Find ALL confirm-like buttons in one JS call
                clicked = self.page.evaluate(f"""() => {{
                    const confirmWords = ['pasti', 'ya', 'yes', 'confirm', 'ok', 'sahkan'];
                    
                    // Priority 1: SweetAlert buttons
                    const swalButtons = document.querySelectorAll(
                        '.swal2-confirm, .swal2-actions button, .swal2-popup button'
                    );
                    for (const btn of swalButtons) {{
                        const text = (btn.innerText || btn.textContent || '').toLowerCase().trim();
                        if (confirmWords.some(word => text.includes(word) || text === word)) {{
                            btn.click();
                            return 'swal:' + text;
                        }}
                    }}
                    
                    // Priority 2: Regular buttons
                    const allButtons = document.querySelectorAll('button, input[type="button"], input[type="submit"]');
                    for (const btn of allButtons) {{
                        const text = (btn.innerText || btn.value || btn.textContent || '').toLowerCase().trim();
                        if (confirmWords.some(word => text.includes(word) || text === word)) {{
                            btn.click();
                            return 'btn:' + text;
                        }}
                    }}
                    
                    return null;
                }}""")
                
                if clicked:
                    self.logger.info(f"   ✅ Confirmed submission ({clicked})")
                    self.book_submitted = True
                    time.sleep(0.3)  # Brief wait for modal to close
                    return True
                
                # Fast fallback: Check if already past confirmation
                page_text = self.page.inner_text("body").lower()
                if 'berjaya' in page_text or 'success' in page_text:
                    self.logger.info("   ℹ️ Success detected - book was submitted!")
                    self.book_submitted = True
                    return True
                
                # Last resort: Try simple detection
                detected_phase, _ = self.detect_current_phase()
                if detected_phase in [FormPhase.SUCCESS, FormPhase.FAVORITES]:
                    self.logger.info(f"   ℹ️ Already on {detected_phase.value} (auto-confirmed)")
                    self.book_submitted = True
                    return True
                
                # If we get here, button not found
                self.logger.warning("   ⚠️ Could not find confirmation button")
                self.take_screenshot(f"phase5_no_pasti_{self.current_book_index}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"   ❌ Error in Phase 5: {e}")
            self.take_screenshot(f"phase5_error_{self.current_book_index}")
            if self.attempt_ai_recovery(e, "click Pasti confirmation button", "PHASE_5_CONFIRM"):
                self.book_submitted = True
                return True
            raise
    
    def handle_success_and_navigation(self) -> bool:
        """Handle success page and navigate back to start - FULLY AUTOMATED VERSION."""
        self.logger.info("🎉 Success - Preparing for Next Book")
        
        # Give page time to update
        time.sleep(self.current_delays['action'])
        
        # Mark as processed to avoid duplicates
        if self.duplicate_tracker and self.current_book:
            self.duplicate_tracker.mark_as_processed(self.current_book, self.current_book_index)
        
        # Close modals and handle post-success screens
        modal_attempts = 0
        while modal_attempts < 5:
            modal_attempts += 1
            detected_phase, _ = self.detect_current_phase()
            
            self.logger.debug(f"   Post-success phase check (attempt {modal_attempts}): {detected_phase.value}")
            
            if detected_phase == FormPhase.SUCCESS:
                self.logger.debug("   ✓ Closing success modal...")
                self.close_swal_modal(["OK", "Tutup", "Close"])
                self.click_button_safe(["OK", "Tutup", "Close"], force_js=True)
                time.sleep(self.current_delays['short'])
            
            elif detected_phase == FormPhase.FAVORITES:
                self.logger.debug("   ✓ Handling favorites page...")
                self.handle_favorites_page()
                time.sleep(self.current_delays['short'])
            
            elif detected_phase in [FormPhase.BOOK_TYPE_SELECT, FormPhase.PHASE_1_BASIC]:
                self.logger.info(f"   ✅ Ready for next book ({detected_phase.value})")
                return True
            
            else:
                self.logger.debug(f"   Current phase: {detected_phase.value}")
                time.sleep(self.current_delays['short'])
        
        # If we've tried multiple times, check if we're ready
        detected_phase, _ = self.detect_current_phase()
        if detected_phase in [FormPhase.BOOK_TYPE_SELECT, FormPhase.PHASE_1_BASIC]:
            return True
        
        self.logger.warning(f"⚠️ Post-success state unclear ({detected_phase.value}), attempting navigation...")
        return self.navigate_to_new_book_form()
    
    # ===========================
    # FORM FILLING HELPERS
    # ===========================
    
    def _fill_form_fields(self, field_data: Dict[str, str]) -> bool:
        filled_count = 0
        
        for label, value in field_data.items():
            if not value:
                continue
            
            value = str(value).strip()
            if len(value) > 2000:
                value = value[:2000] + "..."
            
            if self._fill_field_by_label(label, value):
                filled_count += 1
                self.logger.debug(f"   ✓ Filled '{label}': {value[:50]}...")
        
        self.logger.info(f"   ✏️ Filled {filled_count} fields")
        return filled_count > 0
    
    def _fill_field_by_label(self, label: str, value: str) -> bool:
        strategies = [
            lambda: self.page.get_by_label(label, exact=False).first,
            lambda: self.page.locator(f"input[placeholder*='{label}' i]").first,
            lambda: self.page.locator(f"textarea[placeholder*='{label}' i]").first,
            lambda: self.page.locator(f"input[name*='{label}' i]").first,
            lambda: self.page.locator(f"textarea[name*='{label}' i]").first,
        ]
        
        for strategy in strategies:
            try:
                element = strategy()
                if element.count() > 0 and element.is_visible(timeout=1000):
                    element.clear()
                    element.fill(value)
                    return True
            except Exception:
                continue
        
        return False
    
    def _fill_dropdowns(self, book: Dict) -> bool:
        try:
            selects = self.page.locator("select")
            count = selects.count()
            
            if count == 0:
                return True
            
            self.logger.debug(f"   📋 Found {count} dropdown(s)")
            
            detected_language = LanguageDetector.detect(book, self.config.default_language)
            self.logger.debug(f"   🌐 Language: {detected_language}")
            
            success_count = 0
            
            for i in range(count):
                try:
                    select = selects.nth(i)
                    
                    if not select.is_visible(timeout=1000):
                        continue
                    
                    select_id = select.get_attribute("id") or ""
                    select_name = select.get_attribute("name") or ""
                    identifier = (select_id + select_name).lower()
                    
                    options = select.evaluate("""el => {
                        return Array.from(el.options).map(o => ({
                            value: o.value,
                            text: o.text,
                            index: o.index
                        }));
                    }""")
                    
                    selected = False
                    
                    if any(x in identifier for x in ['bahasa', 'language', 'lang']):
                        selected = self._select_option_fuzzy(select, options, detected_language)
                        if selected:
                            self.logger.debug(f"   ✓ Language: {detected_language}")
                    
                    elif any(x in identifier for x in ['kategori', 'category', 'jenis', 'type', 'genre']):
                        book_category = book.get('category', book.get('genre', self.config.default_category))
                        selected = self._select_option_fuzzy(select, options, book_category)
                        if selected:
                            self.logger.debug(f"   ✓ Category: {book_category}")
                    
                    else:
                        # Select first non-empty option
                        try:
                            if len(options) > 1:
                                select.select_option(index=1, timeout=2000)
                                selected = True
                        except:
                            pass
                    
                    if selected:
                        success_count += 1
                            
                except Exception as e:
                    self.logger.debug(f"   ⚠️ Dropdown {i} failed: {e}")
                    continue
            
            return success_count > 0 or count == 0
            
        except Exception as e:
            self.logger.warning(f"   ⚠️ Dropdown handling failed: {e}")
            return False
    
    def _select_option_fuzzy(self, select, options: List[Dict], target: str) -> bool:
        target_lower = target.lower().strip()
        
        # Exact match
        for opt in options:
            if opt['text'].lower().strip() == target_lower:
                try:
                    select.select_option(value=opt['value'], timeout=2000)
                    return True
                except:
                    pass
        
        # Partial match
        for opt in options:
            opt_text = opt['text'].lower().strip()
            if target_lower in opt_text or opt_text in target_lower:
                try:
                    select.select_option(value=opt['value'], timeout=2000)
                    return True
                except:
                    pass
        
        # Word match
        target_words = target_lower.split()
        for opt in options:
            opt_text = opt['text'].lower()
            if any(word in opt_text for word in target_words if len(word) > 2):
                try:
                    select.select_option(value=opt['value'], timeout=2000)
                    return True
                except:
                    pass
        
        return False
    
    # ===========================
    # MAIN BOOK PROCESSING (FIXED)
    # ===========================
    
    def process_book(self, book: Dict, index: int, tracker: ProgressTracker) -> bool:
        """Process a single book through all phases - FIXED VERSION."""
        title = book.get('title', f'Book {index}')
        self.current_book_index = index
        self.current_book = book
        self.book_submitted = False  # Reset for each book
        
        progress = f"[{index + 1}/{self.total_books}]"
        eta = tracker.get_eta(index, self.total_books)
        detected_lang = LanguageDetector.detect(book, self.config.default_language)
        
        self.logger.info("=" * 70)
        self.logger.info(f"📖 {progress} {title[:50]}{'...' if len(title) > 50 else ''}")
        self.logger.info(f"   🌐 {detected_lang} | ⏱️ ETA: {eta}")
        self.logger.info("=" * 70)
        
        try:
            # Health check periodically
            if index % self.config.health_check_interval == 0 and index > 0:
                if not self.perform_health_check():
                    self.logger.warning("   ⚠️ Health check failed, but continuing...")
            
            # Check session validity
            if not self.check_session_validity():
                if not self.recover_session():
                    raise SessionExpiredError("Session expired and could not recover")
            
            self.wait_for_page_ready()
            time.sleep(self.current_delays['short'])
            
            # Check for duplicates
            if self.config.check_for_duplicates:
                is_dup, reason = self.check_for_duplicate(book)
                if is_dup:
                    if self.config.skip_duplicates:
                        self.logger.warning(f"⏭️  SKIPPING DUPLICATE: {reason}")
                        if self.duplicate_tracker:
                            self.duplicate_tracker.mark_as_duplicate(book, index)
                        tracker.mark_book(index, title, BookStatus.DUPLICATE, reason)
                        return True  # Return True because we handled it correctly
                    else:
                        self.logger.warning(f"⚠️  Possible duplicate: {reason} (continuing anyway)")
            
            # Phase 0: Book Type Selection - SINGLE ATTEMPT
            try:
                if not self.handle_book_type_selection():
                    self.logger.warning("⚠️ Phase 0 validation issue, but continuing...")
            except Exception as e:
                self.logger.debug(f"⚠️ Phase 0 exception: {e}")
            
            # Phase 1: Basic Info
            if not self.handle_phase_1_basic(book):
                self.logger.error("❌ Failed at Phase 1")
                return False
            
            # Phase 2: Summary
            if not self.handle_phase_2_summary(book):
                self.logger.error("❌ Failed at Phase 2")
                return False
            
            # Phase 3: Empty Page
            if not self.handle_phase_3_empty():
                self.logger.error("❌ Failed at Phase 3")
                return False
            
            # Phase 4: Submit
            if not self.handle_phase_4_submit():
                self.logger.error("❌ Failed at Phase 4")
                return False
            
            # Phase 5: Confirm
            if not self.handle_phase_5_confirm():
                # Check if book was actually submitted
                if self.book_submitted:
                    self.logger.info("   ℹ️ Book was submitted despite button issue")
                else:
                    self.logger.error("❌ Failed at Phase 5")
                    return False
            
            # Handle success and navigate to next book
            if not self.handle_success_and_navigation():
                # Book was submitted, navigation just failed
                if self.book_submitted:
                    self.logger.warning("⚠️ Navigation issue after success (book was saved)")
                    # Try one more time to navigate
                    time.sleep(self.current_delays['action'])
                    self.navigate_to_new_book_form()
                else:
                    self.logger.warning("⚠️ Navigation issue (will try next book)")
            
            self.logger.info(f"✅ '{title[:40]}' completed!")
            self.adjust_delays(True)  # Speed up on success
            return True
            
        except KeyboardInterrupt:
            raise
        except UnrecoverableError:
            raise
        except Exception as e:
            self.adjust_delays(False)  # Slow down on failure
            self.logger.error(f"❌ Error: {e}")
            self.take_screenshot(f"book_error_{index}")
            
            # Check if book was actually submitted
            if self.book_submitted:
                self.logger.info("   ℹ️ Book appears to have been submitted before error")
                # Try to navigate for next book
                try:
                    self.navigate_to_new_book_form()
                except:
                    pass
                return True
            
            # Final recovery attempt
            if self.config.use_ai_error_recovery:
                self.logger.info("🤖 Attempting final error recovery...")
                if self.attempt_ai_recovery(e, "complete book entry", "UNKNOWN"):
                    self.logger.info("   ✅ Recovered! Trying to continue...")
                    if self.navigate_to_new_book_form():
                        return True
            
            import traceback
            self.logger.debug(traceback.format_exc())
            return False
    
    def cleanup(self):
        if self.browser:
            try:
                self.browser.close()
                self.logger.debug("Browser closed")
            except Exception as e:
                self.logger.warning(f"Cleanup error: {e}")
            finally:
                self.browser = None
                self.page = None


# ===========================
# 14. MAIN EXECUTION
# ===========================
def print_banner():
    print("\n" + "=" * 70)
    print("  📚 AINS BOOK AUTOMATION v5.1 - FULLY FIXED EDITION")
    print("  " + "-" * 66)
    print("  Automated book entry for AINS library system")
    print("  ")
    print("  🔧 FIXES IN THIS VERSION:")
    print("    ✓ Fixed 'Pasti' button detection (SweetAlert)")
    print("    ✓ Fixed navigation after book completion")
    print("    ✓ Fixed progress tracking (no false failures)")
    print("    ✓ Fixed duplicate detection stats")
    print("    ✓ Fixed JavaScript injection vulnerability")
    print("    ✓ Fixed favorites page handling")
    print("    ✓ Auto book type selection after each book")
    print("    ✓ Better modal/SweetAlert handling")
    print("=" * 70 + "\n")


def show_startup_menu(tracker: ProgressTracker, books: list, logger: logging.Logger) -> Tuple[int, bool]:
    """
    Show startup menu to let user choose:
    - Start from beginning or resume
    - Whether to skip already submitted books
    
    Returns: (start_index, skip_submitted)
    """
    submitted_books = tracker.get_submitted_books()
    total_books = len(books)
    # Filter out submitted records that refer to indexes no longer present
    raw_submitted_count = len(submitted_books)
    submitted_books = [t for t in submitted_books if 0 <= t[0] < total_books]
    stale_count = raw_submitted_count - len(submitted_books)
    if stale_count > 0:
        logger.warning(f"Found {stale_count} submitted entries outside current book list; ignoring them")
    
    print("\n" + "=" * 70)
    print("📋 STARTUP OPTIONS")
    print("-" * 70)
    
    if submitted_books:
        print(f"\n✅ Previously submitted books: {len(submitted_books)} of {total_books}")
        print("-" * 50)
        
        # Show first 10 and last 5 if there are many
        if len(submitted_books) > 15:
            for idx, title, timestamp in submitted_books[:10]:
                print(f"   [{idx+1}] {title[:45]}...")
            print(f"   ... ({len(submitted_books) - 15} more) ...")
            for idx, title, timestamp in submitted_books[-5:]:
                print(f"   [{idx+1}] {title[:45]}...")
        else:
            for idx, title, timestamp in submitted_books:
                print(f"   [{idx+1}] {title[:50]}")
        
        print("-" * 50)
        print(f"\n📊 Current progress: Last completed = Book #{tracker.data['last_completed_index'] + 1}")
        print(f"   Would resume from Book #{tracker.get_start_index() + 1}")
        
        print("\n🎯 Choose how to start:")
        print("   [1] 🔄 FRESH START - Reset everything, start from Book #1")
        print("   [2] ⏭️  START FROM BEGINNING - Skip already submitted books")
        print("   [3] ▶️  RESUME - Continue from where you left off")
        print("   [4] 📍 CUSTOM - Start from a specific book number")
        print("   [0] ❌ EXIT - Cancel and exit")
        print("=" * 70)
        
        while True:
            choice = safe_input("\n>>> Enter your choice (1/2/3/4/0): ")
            if choice is None or choice == "0":
                print("Exiting...")
                return -1, False  # Signal to exit
            
            if choice == "1":
                # Fresh start - reset everything
                tracker.reset()
                logger.info("📍 Fresh start - all progress reset")
                print("\n✅ Progress reset. Will start from Book #1")
                return 0, False
            
            elif choice == "2":
                # Start from beginning but skip submitted
                tracker.reset_keep_submitted()
                logger.info(f"📍 Starting from beginning, will skip {len(submitted_books)} submitted books")
                print(f"\n✅ Will start from Book #1, skipping {len(submitted_books)} already submitted books")
                return 0, True
            
            elif choice == "3":
                # Resume from last position (original behavior)
                start_idx = tracker.get_start_index()
                logger.info(f"📍 Resuming from Book #{start_idx + 1}")
                print(f"\n✅ Resuming from Book #{start_idx + 1}")
                return start_idx, True
            
            elif choice == "4":
                # Custom start index
                custom = safe_input(f"   Enter book number to start from (1-{total_books}): ")
                if custom is None:
                    continue
                try:
                    custom_idx = int(custom) - 1  # Convert to 0-based
                    if 0 <= custom_idx < total_books:
                        skip = safe_confirm("   Skip already submitted books? (y/n): ", default=True)
                        if skip:
                            tracker.reset_keep_submitted()
                        logger.info(f"📍 Custom start from Book #{custom_idx + 1}, skip={skip}")
                        print(f"\n✅ Will start from Book #{custom_idx + 1}")
                        return custom_idx, skip
                    else:
                        print(f"   ⚠️  Invalid book number. Enter 1-{total_books}")
                except ValueError:
                    print("   ⚠️  Please enter a valid number")
            
            else:
                print("   ⚠️  Invalid choice. Please enter 1, 2, 3, 4, or 0")
    
    else:
        # No previous progress
        print("\n📭 No previous progress found.")
        print(f"   Will process all {total_books} books starting from Book #1")
        print("\n   Press Enter to continue or Ctrl+C to exit...")
        if safe_input("") is None:
            return -1, False
        return 0, False


def main():
    print_banner()
    
    config = Config()
    logger = setup_logging(config)
    tracker = ProgressTracker(config, logger)
    automation = BookAutomation(config, logger)
    
    logger.info("🚀 Starting AINS Book Automation v5.1...")
    logger.info(f"   📂 Working directory: {config.base_dir}")
    logger.info(f"   📄 Book data file: {config.json_file}")
    logger.info(f"   📖 Book type: {config.book_type}")
    logger.info(f"   ⭐ Add to favorites: {config.add_to_favorites}")
    logger.info(f"   🔍 Duplicate detection: {config.check_for_duplicates}")
    logger.info(f"   ⏭️  Skip duplicates: {config.skip_duplicates}")
    logger.info(f"   🛡️  AI error recovery: {config.use_ai_error_recovery}")
    logger.info(f"   📸 Screenshots on error: {config.take_screenshots_on_error}")
    logger.info(f"   ⚡ Adaptive delays: {config.adaptive_delays}")
    
    # Handle command line arguments
    if "--reset" in sys.argv:
        tracker.reset()
    
    if "--debug" in sys.argv:
        config.debug_mode = True
        # Update console handler level
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(logging.DEBUG)
        logger.info("   🔧 Debug mode enabled")
    
    if "--favorites" in sys.argv:
        config.add_to_favorites = True
        logger.info("   ⭐ Will add books to favorites")
    
    if "--no-ai-recovery" in sys.argv:
        config.use_ai_error_recovery = False
        logger.info("   ⚠️  AI error recovery disabled")
    
    if "--no-duplicate-check" in sys.argv:
        config.check_for_duplicates = False
        logger.info("   ⚠️  Duplicate checking disabled")
    
    if "--screenshots" in sys.argv:
        config.take_screenshots_on_error = True
        os.makedirs(config.get_path(config.screenshots_dir), exist_ok=True)
        logger.info("   📸 Screenshot capture enabled")
    
    if "--help" in sys.argv:
        print("\nUsage: python script.py [options]")
        print("\nOptions:")
        print("  --reset              Reset progress, start from beginning")
        print("  --debug              Enable debug logging")
        print("  --favorites          Add books to favorites after entry")
        print("  --no-ai-recovery     Disable AI error recovery")
        print("  --no-duplicate-check Disable duplicate detection")
        print("  --screenshots        Save screenshots on errors")
        print("  --help               Show this help message")
        return
    
    # Initialize AI
    if not automation.initialize_ai():
        if not config.fallback_to_simple_detection:
            logger.error("❌ Cannot proceed without AI")
            return
    
    # Load books
    books = automation.load_books()
    if not books:
        logger.error("❌ No books to process.")
        return
    
    # Show language statistics
    lang_stats = {}
    for book in books:
        lang = LanguageDetector.detect(book, config.default_language)
        lang_stats[lang] = lang_stats.get(lang, 0) + 1
    
    logger.info("📊 Language distribution:")
    for lang, count in sorted(lang_stats.items(), key=lambda x: -x[1]):
        logger.info(f"   {lang}: {count} books")
    
    # Show startup menu and let user choose how to start
    start_index, skip_submitted = show_startup_menu(tracker, books, logger)
    
    # Exit if user chose to cancel
    if start_index < 0:
        logger.info("User chose to exit")
        return
    
    # Calculate remaining books accounting for skip behavior
    if skip_submitted:
        completed_count = sum(1 for i in range(start_index, len(books)) if tracker.is_book_completed(i))
        remaining_count = len(books) - start_index - completed_count
    else:
        completed_count = 0
        remaining_count = len(books) - start_index
    
    logger.info(f"\n📍 Will start from Book #{start_index + 1}")
    if skip_submitted and completed_count > 0:
        logger.info(f"   ⏭️  Will skip {completed_count} already submitted books")
    logger.info(f"   📚 Books to process: {remaining_count}")
    
    playwright_instance = None
    
    try:
        playwright_instance = sync_playwright().start()
        
        browser = playwright_instance.chromium.launch_persistent_context(
            user_data_dir=config.get_path(config.user_data_dir),
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            ignore_default_args=["--enable-automation"],
            viewport=None,
        )
        
        automation.browser = browser
        automation.page = browser.pages[0] if browser.pages else browser.new_page()
        
        # Navigate to AINS and wait for load
        logger.info(f"🌐 Navigating to {config.ains_url}...")
        automation.page.goto(config.ains_url)
        automation.wait_for_page_ready()
        
        print("\n" + "=" * 70)
        print("🔐 MANUAL LOGIN & SETUP REQUIRED")
        print("-" * 70)
        print("1. Log in to AINS with your credentials")
        print("2. Navigate to: Koleksi > Tambah Bahan")
        print("3. You should see Buku/e-Buku selection")
        print("   (OR already on the form - system will detect)")
        print("4. Press ENTER when ready to start automation")
        print("")
        print("💡 FEATURES IN v5.1:")
        if config.check_for_duplicates:
            print("   ✓ Duplicate detection - skips already entered books")
        if config.use_ai_error_recovery:
            print("   ✓ AI error recovery - auto-fixes problems")
        if config.adaptive_delays:
            print("   ✓ Adaptive delays - speeds up over time")
        if config.take_screenshots_on_error:
            print("   ✓ Error screenshots - saves debug images")
        print(f"   ✓ Continuous operation - processes all {len(books) - start_index} remaining books")
        print(f"   ✓ Auto book type selection - no manual intervention needed")
        print(f"   ✓ Improved SweetAlert handling - better Pasti detection")
        print("=" * 70)
        
        user_input = safe_input("\n>>> Press Enter to Start Automation... ")
        if user_input is None:
            logger.info("Cancelled by user")
            return
        
        logger.info("\n🎬 " + "=" * 60)
        logger.info("   AUTOMATION STARTED - FULLY AUTOMATED MODE")
        logger.info("=" * 64 + "\n")
        
        # Main processing loop
        books_processed = 0
        consecutive_failures = 0
        max_consecutive_failures = 10  # Warn but don't stop
        
        for i in range(start_index, len(books)):
            book = books[i]
            title = book.get('title', f'Book {i}')
            
            # Skip already completed books
            if tracker.is_book_completed(i):
                logger.info(f"⏭️  Skipping already completed: [{i+1}/{len(books)}] {title[:40]}")
                continue
            
            try:
                success = automation.process_book(book, i, tracker)
                
                if success:
                    tracker.mark_book(i, title, BookStatus.SUCCESS)
                    consecutive_failures = 0
                    books_processed += 1
                    
                    # Check if we've reached the maximum books to process
                    if books_processed >= config.max_books_to_process:
                        logger.info(f"\n✅ Reached maximum books to process ({config.max_books_to_process}), stopping automation")
                        break
                else:
                    # Check if it's a duplicate (already marked by process_book)
                    book_status = tracker.data["books"].get(str(i), {}).get("status")
                    if book_status == BookStatus.DUPLICATE.value:
                        logger.info("   ⏭️  Duplicate handled, moving to next...")
                        consecutive_failures = 0  # Don't count as failure
                    else:
                        tracker.mark_book(i, title, BookStatus.FAILED, "Processing failed")
                        consecutive_failures += 1
                        logger.warning(f"   ⚠️  Failed (consecutive: {consecutive_failures}), continuing...")
                
                # Warn on too many consecutive failures
                if consecutive_failures >= max_consecutive_failures:
                    logger.warning(f"⚠️  {consecutive_failures} consecutive failures!")
                    logger.warning("   Consider checking the page manually.")
                    
                    # Ask if user wants to continue
                    if consecutive_failures % max_consecutive_failures == 0:
                        print(f"\n⚠️  {consecutive_failures} consecutive failures detected.")
                        if not safe_confirm("Continue anyway? (y/n, default=y): ", default=True):
                            logger.info("Stopping due to failures")
                            break
                    
            except KeyboardInterrupt:
                logger.info("\n⏸️ Paused by user (Ctrl+C)")
                
                # Save current progress
                if automation.book_submitted:
                    tracker.mark_book(i, title, BookStatus.SUCCESS)
                    logger.info(f"   ✅ Current book was submitted, marked as success")
                else:
                    tracker.mark_book(i, title, BookStatus.FAILED, "User interrupted")
                
                print("\n" + "=" * 50)
                print("Options:")
                print("  1. Continue from next book")
                print("  2. Retry current book")
                print("  3. Exit")
                print("=" * 50)
                
                choice = safe_input("Choice (1/2/3): ")
                
                if choice == "1":
                    logger.info("Continuing from next book...")
                    continue
                elif choice == "2":
                    logger.info("Retrying current book...")
                    i -= 1  # Will be incremented by loop
                    continue
                else:
                    logger.info("Exiting...")
                    break
                    
            except SessionExpiredError as e:
                logger.error(f"\n⛔ Session expired: {e}")
                tracker.mark_book(i, title, BookStatus.FAILED, str(e))
                
                if automation.recover_session():
                    logger.info("   ✅ Session recovered, continuing...")
                    # Retry current book
                    continue
                else:
                    logger.error("   ❌ Could not recover session")
                    print("\n⚠️  Please log in again and press Enter to continue...")
                    safe_pause()
                    if automation.check_session_validity():
                        continue
                    else:
                        break
                
            except UnrecoverableError as e:
                logger.error(f"\n⛔ Unrecoverable error: {e}")
                tracker.mark_book(i, title, BookStatus.FAILED, str(e))
                break
                
            except Exception as e:
                logger.error(f"\n❌ Unexpected error: {e}")
                tracker.mark_book(i, title, BookStatus.FAILED, str(e))
                
                import traceback
                logger.debug(traceback.format_exc())
                
                # Continue with next book
                consecutive_failures += 1
                logger.info("   🔄 Continuing with next book...")
                
                # Try to get back to a good state
                try:
                    automation.close_modal_if_present()
                    automation.navigate_to_new_book_form()
                except:
                    pass
        
        # ===========================
        # FINAL SUMMARY
        # ===========================
        stats = tracker.get_stats()
        session_info = tracker.get_session_summary()
        
        print("\n")
        logger.info("=" * 70)
        logger.info("📊 AUTOMATION COMPLETE - FINAL SUMMARY")
        logger.info("-" * 70)
        logger.info(f"   ✅ Successful:  {stats['success']}")
        logger.info(f"   ❌ Failed:      {stats['failed']}")
        logger.info(f"   🔁 Duplicates:  {stats['duplicate']}")
        logger.info(f"   ⏩ Skipped:     {stats['skipped']}")
        logger.info(f"   📚 Total:       {stats['success'] + stats['failed'] + stats['duplicate'] + stats['skipped']}")
        logger.info("-" * 70)
        logger.info(f"   📈 {session_info}")
        
        # Success rate
        total_attempted = stats['success'] + stats['failed']
        if total_attempted > 0:
            success_rate = (stats['success'] / total_attempted) * 100
            logger.info(f"   🎯 Success rate: {success_rate:.1f}%")
        
        logger.info("=" * 70)
        
        # Save final progress
        tracker.save()
        
        print("\n🔒 Browser will close in 10 seconds...")
        print("   (Press Ctrl+C to keep browser open)")
        
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            print("\n💡 Browser kept open for inspection.")
            print("   Close manually when done.")
            safe_pause("\nPress Enter to exit program...")
        
    except KeyboardInterrupt:
        logger.info("\n⏸️ Interrupted by user")
        
    except Exception as e:
        logger.error(f"\n💥 Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    finally:
        # Final cleanup
        logger.info("\n🧹 Cleaning up...")
        
        # Save progress one more time
        try:
            tracker.save()
            logger.info("   ✅ Progress saved")
        except Exception as e:
            logger.warning(f"   ⚠️ Could not save progress: {e}")
        
        # Close browser
        automation.cleanup()
        
        # Stop playwright
        if playwright_instance:
            try:
                playwright_instance.stop()
                logger.info("   ✅ Playwright stopped")
            except Exception as e:
                logger.debug(f"Playwright stop: {e}")
        
        logger.info("✅ Done! Goodbye.")


# ===========================
# 15. ENTRY POINT
# ===========================
if __name__ == "__main__":
    main()

