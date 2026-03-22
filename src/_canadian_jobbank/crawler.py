"""Crawler for _canadian_jobbank."""
from __future__ import annotations

import re
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, List
import random
from hyperSel import instance, parser

try:
    from _canadian_jobbank.jsonify import CanadianJobbankJsonify
    from _canadian_jobbank.schema import SCHEMA
except ModuleNotFoundError:
    import sys
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from _canadian_jobbank.jsonify import CanadianJobbankJsonify
    from _canadian_jobbank.schema import SCHEMA

# ── ANSI colours ──────────────────────────────────────────────────────────────
R  = '\033[0m'
BD = '\033[1m'
GR = '\033[92m'
YL = '\033[93m'
CY = '\033[96m'
RD = '\033[91m'
WH = '\033[97m'

PUSH_INTERVAL = 600
BASE_URL      = "https://www.jobbank.gc.ca"

DEFAULT_KEYWORDS = [
    "administrative", "warehouse", "driver", "cook", "cleaner",
    "cashier", "labourer", "technician", "nurse", "security",
    "receptionist", "clerk", "secretary", "assistant", "coordinator",
    "executive", "manager", "supervisor", "director", "lead",
    "representative", "associate", "specialist", "consultant", "analyst",
    "auditor", "accountant", "bookkeeper", "payroll", "billing",
    "finance", "banking", "teller", "underwriter", "actuary",
    "marketing", "sales", "retail", "merchandiser", "buyer",
    "planner", "estimator", "scheduler", "dispatcher", "logistics",
    "inventory", "shipping", "receiving", "forklift", "operator",
    "machinist", "welder", "electrician", "plumber", "carpenter",
    "painter", "roofer", "mason", "mechanic", "millwright",
    "engineer", "architect", "designer", "drafter", "surveyor",
    "developer", "programmer", "coder", "software", "hardware",
    "network", "systems", "database", "cybersecurity", "support",
    "helpdesk", "tester", "quality", "inspector", "compliance",
    "legal", "paralegal", "attorney", "lawyer", "counsel",
    "medical", "doctor", "physician", "surgeon", "dentist",
    "pharmacist", "therapist", "paramedic", "caregiver", "nanny",
    "teacher", "instructor", "professor", "tutor", "coach",
    "trainer", "facilitator", "recruiter", "hr", "human",
    "janitor", "landscaper", "gardener", "arborist", "custodian",
    "server", "bartender", "host", "barista", "baker",
    "chef", "butcher", "dishwasher", "steward", "concierge",
    "valet", "porter", "attendant", "courier", "delivery",
    "trucker", "chauffeur", "pilot", "captain", "deckhand",
    "stewardess", "flight", "agent", "broker", "realtor",
    "appraiser", "adjuster", "collector", "investigator", "detective",
    "officer", "patrol", "firefighter", "lifeguard", "volunteer",
    "intern", "apprentice", "trainee", "junior", "senior",
    "principal", "staff", "faculty", "editor", "writer",
    "journalist", "author", "copywriter", "translator", "interpreter",
    "artist", "illustrator", "photographer", "videographer", "animator",
    "producer", "curator", "librarian", "archivist", "clergyman",
    "pastor", "priest", "rabbi", "monk", "nun",
    "scientist", "biologist", "chemist", "physicist", "geologist",
    "ecologist", "meteorologist", "astronomer", "statistician", "mathematician",
    "sociologist", "psychologist", "counselor", "worker", "advocate",
    "lobbyist", "politician", "diplomat", "ambassador", "clerical",
    "data", "entry", "typing", "transcription", "filing",
    "mail", "courier", "messenger", "janitorial", "maintenance",
    "repair", "installation", "assembly", "production", "manufacturing",
    "fabrication", "packaging", "sorting", "stacking", "loading",
    "unloading", "hauling", "lifting", "moving", "transport",
    "automotive", "aviation", "maritime", "railroad", "transit",
    "utility", "telecommunications", "broadcasting", "publishing", "printing",
    "advertising", "media", "entertainment", "hospitality", "tourism",
    "recreation", "sports", "fitness", "wellness", "spa",
    "salon", "barber", "stylist", "esthetician", "makeup",
    "tailor", "seamstress", "upholsterer", "shoemaker", "jeweler",
    "florist", "pet", "groomer", "veterinary", "kennel",
    "farm", "ranch", "agriculture", "forestry", "mining",
    "quarrying", "drilling", "excavation", "construction", "demolition",
    "surveying", "inspection", "safety", "environmental", "sanitation",
    "recycling", "waste", "water", "energy", "solar",
    "wind", "nuclear", "chemical", "pharmaceutical", "biotech",
    "semiconductor", "electronics", "aerospace", "defense", "military",
    "government", "public", "nonprofit", "charity", "foundation",
    "education", "training", "library", "museum", "gallery",
    "theater", "music", "dance", "film", "radio",
    "television", "internet", "e-commerce", "retail", "wholesale",
    "distribution", "brokerage", "insurance", "real", "estate",
    "leasing", "rental", "property", "facility", "asset",
    "wealth", "investment", "equity", "venture", "capital",
    "strategy", "operations", "process", "project", "program",
    "product", "brand", "account", "customer", "client",
    "relationship", "success", "experience", "support", "service",
    "outreach", "engagement", "communication", "relations", "affairs",
    "policy", "research", "development", "innovation", "digital",
    "transformation", "cloud", "security", "infrastructure", "architecture",
    "engineering", "manufacturing", "supply", "chain", "procurement",
    "sourcing", "vendor", "contract", "legal", "regulatory",
    "ethics", "risk", "fraud", "loss", "prevention",
    "safety", "health", "occupational", "wellness", "benefits",
    "compensation", "talent", "acquisition", "learning", "culture",
    "diversity", "inclusion", "equity", "accessibility", "sustainability",
    "governance", "stewardship", "impact", "growth", "performance",
    "metrics", "analytics", "intelligence", "insights", "reporting",
    "dashboard", "visualization", "modeling", "simulation", "optimization",
    "automation", "robotics", "artificial", "intelligence", "machine",
    "learning", "deep", "neural", "natural", "language",
    "vision", "audio", "video", "graphics", "interface",
    "experience", "usability", "accessibility", "interaction", "content",
    "strategy", "management", "curation", "moderation", "community",
    "social", "influence", "growth", "retention", "monetization",
    "subscription", "partnership", "alliance", "ecosystem", "platform",
    "marketplace", "payments", "fintech", "insurtech", "proptech",
    "edtech", "healthtech", "biotech", "cleantech", "agtech",
    "foodtech", "traveltech", "adtech", "martech", "hrtech",
    "enterprise", "consumer", "business", "industrial", "commercial",
    "residential", "global", "regional", "local", "remote",
    "hybrid", "onsite", "freelance", "contract", "temporary",
    "permanent", "full-time", "part-time", "seasonal", "internship",
    "residency", "fellowship", "scholarship", "grants", "funding",
    "budgeting", "forecasting", "treasury", "tax", "audit",
    "compliance", "standards", "quality", "assurance", "control",
    "testing", "validation", "verification", "certification", "accreditation",
    "licensing", "permitting", "zoning", "planning", "development",
    "redevelopment", "renovation", "restoration", "conservation", "preservation",
    "reclamation", "remediation", "emergency", "crisis", "disaster",
    "relief", "humanitarian", "aid", "development", "advocacy",
    "activism", "organizing", "campaign", "election", "voter",
    "legislative", "judicial", "executive", "administrative", "regulatory",
    "enforcement", "protection", "intelligence", "surveillance", "investigation",
    "forensics", "evidence", "testimony", "litigation", "arbitration",
    "mediation", "negotiation", "settlement", "contract", "agreement",
    "treaty", "protocol", "convention", "charter", "constitution",
    "bylaw", "ordinance", "statute", "regulation", "guideline",
    "policy", "procedure", "standard", "best", "practice",
    "framework", "methodology", "approach", "philosophy", "theory",
    "concept", "principle", "value", "mission", "vision",
    "goal", "objective", "target", "milestone", "deadline",
    "priority", "task", "activity", "process", "workflow",
    "pipeline", "cycle", "lifecycle", "roadmap", "strategy",
    "tactic", "execution", "implementation", "deployment", "launch",
    "rollout", "migration", "integration", "configuration", "customization",
    "optimization", "maintenance", "support", "troubleshooting", "resolution",
    "escalation", "incident", "problem", "change", "release"
]
random.shuffle(DEFAULT_KEYWORDS)

def _banner(lines: list[str], color: str = CY) -> None:
    width  = max(len(l) for l in lines) + 6
    border = color + BD + "█" * width + R
    print(f"\n{border}")
    for line in lines:
        pad = width - len(line) - 4
        print(f"{color}{BD}██  {WH}{line}{' ' * pad}{color}██{R}")
    print(f"{border}\n")


class CanadianJobbankCrawler:
    def __init__(self, name: str = "_canadian_jobbank"):
        self.name          = name
        self._last_push    = time.time()
        self._total_rows   = 0
        self._keywords_done = 0

    # ── Git push ───────────────────────────────────────────────────────────────

    def _push_to_github(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            subprocess.run(["git", "add", f"src/{self.name}/database.sqlite"],
                           cwd=repo_root, check=True)
            subprocess.run(["git", "commit", "-m",
                            f"data: {self.name} auto-push {now} | rows={self._total_rows}"],
                           cwd=repo_root, check=True)
            subprocess.run(["git", "push"], cwd=repo_root, check=True)
        except subprocess.CalledProcessError:
            pass
        self._last_push = time.time()

    def _maybe_push(self) -> None:
        if time.time() - self._last_push >= PUSH_INTERVAL:
            self._push_to_github()

    # ── Main run ───────────────────────────────────────────────────────────────

    def run(self, keywords: List[str] | None = None) -> None:
        keywords = keywords or DEFAULT_KEYWORDS
        total_keywords = len(keywords)

        browser = instance.Browser(
            driver_choice='selenium',
            headless=True,
            zoom_level=100,
        )
        browser.init_browser()
        browser.go_to_site("https://foreandr.github.io/")

        for i, keyword in enumerate(keywords, 1):
            try:
                total_data = self._process_keyword(browser, keyword)

                '''
                for j in total_data:
                    print(len(j), j)
                    print("-")
                '''


                jsonifier  = CanadianJobbankJsonify(self.name)
                clean_data = jsonifier.run_analysis(total_data, print_samples=True)
                
                '''
                _banner([
                    f"  PARSED RECORDS FOR: {keyword.upper()}",
                    f"  Raw rows   : {len(total_data)}",
                    f"  Parsed OK  : {jsonifier.processed_count}",
                    f"  Skipped    : {jsonifier.skipped_count}",
                ], color=CY)
                '''

                '''
                for idx, rec in enumerate(clean_data, 1):
                    print(
                        f"{YL}[{idx}/{len(clean_data)}]{R} "
                        f"{BD}{rec.get('title', '???')}{R}\n"
                        f"  company    : {rec.get('company')}\n"
                        f"  location   : {rec.get('location_raw')}\n"
                        f"  pay        : ${rec.get('pay')}/hr\n"
                        f"  lmia       : {rec.get('is_lmia')}\n"
                        f"  direct     : {rec.get('is_direct_apply')}\n"
                        f"  work_mode  : {rec.get('work_mode')}\n"
                        f"  source     : {rec.get('source')}\n"
                        f"  posted_date: {rec.get('posted_date')}\n"
                        f"  url        : {rec.get('url')}\n"
                    )
                '''
                #input(f"{BD}------- press ENTER to store {len(clean_data)} records and continue ------- {R}")

                inserted = self._store_clean_data(clean_data)
                self._total_rows   += inserted
                self._keywords_done += 1

            except Exception as e:
                print(f"{RD}[ERROR] keyword={keyword}: {e}{R}")

            pct      = f"{i}/{total_keywords}"
            db_total = self._db_total_rows()
            print(f"[{pct}] {self.name} | keyword={keyword} | db_rows={db_total}")
            self._maybe_push()

        browser.close_browser()
        self._push_to_github()

    # ── Scraping ───────────────────────────────────────────────────────────────

    def _process_keyword(self, browser: Any, keyword: str) -> List[List[Any]]:
        search_url = (
            f"{BASE_URL}/jobsearch/jobsearch"
            f"?searchstring={keyword.replace(' ', '+')}"
            f"&sort=M"   # sort by most recent
        )
        browser.go_to_site(search_url)
        time.sleep(1.5)
        return self._paginate_and_scrape(browser)

    def _paginate_and_scrape(self, browser: Any) -> List[List[Any]]:
        total_data  = []
        page        = 0
        max_pages   = 40   # safety cap

        while page < max_pages:
            soup     = browser.return_current_soup()
            raw_rows = parser.main(soup)
            total_data.extend(raw_rows)
            # Dedup within session
            total_data = [list(x) for x in {tuple(x) for x in total_data}]

            page += 1

            # Try to click "Load more results" button
            button_xpath = '//*[@id="moreresultbutton"]'
            try:
                browser.scroll_to_bottom()
                time.sleep(0.5)
                browser.click_element("xpath", button_xpath, 3)
                time.sleep(1.5)
            except Exception:
                break   # no more pages

        return total_data

    # ── Storage ────────────────────────────────────────────────────────────────

    def _store_clean_data(self, clean_data: Any) -> int:
        db_path = self._db_path()
        conn    = sqlite3.connect(str(db_path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(SCHEMA.create_table_sql())
        for stmt in SCHEMA.create_indexes_sql():
            conn.execute(stmt)

        # Ensure all schema columns exist (safe for re-runs against old DB)
        existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(items);").fetchall()]
        for field in SCHEMA.fields:
            if field.name not in existing_cols:
                default = f" DEFAULT {field.default_sql}" if field.default_sql else ""
                conn.execute(f"ALTER TABLE items ADD COLUMN {field.name} {field.type}{default};")

        rows = []
        if isinstance(clean_data, list):
            for item in clean_data:
                if not isinstance(item, dict):
                    continue
                if not item.get("crawled_at"):
                    item["crawled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rows.append([item.get(k) for k in SCHEMA.field_names()])

        if rows:
            placeholders = ", ".join(["?"] * len(SCHEMA.field_names()))
            columns      = ", ".join(SCHEMA.field_names())
            conn.executemany(
                f"INSERT OR IGNORE INTO items ({columns}) VALUES ({placeholders});",
                rows,
            )
        conn.commit()
        conn.close()
        return len(rows)

    def _db_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / "src" / self.name / "database.sqlite"

    def _db_total_rows(self) -> int:
        db_path = self._db_path()
        if not db_path.exists():
            return 0
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        try:
            row = conn.execute("SELECT COUNT(*) FROM items;").fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()


# ── dedup helper ───────────────────────────────────────────────────────────────

def dedup_database(db_path: Path | None = None) -> int:
    if db_path is None:
        db_path = Path(__file__).resolve().parents[2] / "src" / "_canadian_jobbank" / "database.sqlite"
    if not db_path.exists():
        print(f"  {RD}DB not found:{R} {db_path}")
        return 0
    conn   = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    before = conn.execute("SELECT COUNT(*) FROM items;").fetchone()[0]
    conn.execute("""
        DELETE FROM items
        WHERE rowid NOT IN (
            SELECT MIN(rowid) FROM items GROUP BY url
        );
    """)
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM items;").fetchone()[0]
    conn.close()
    deleted = before - after
    _banner([
        "DEDUP COMPLETE",
        f"  Before : {before:,}",
        f"  After  : {after:,}",
        f"  Deleted: {deleted:,} duplicate rows",
    ], color=GR)
    return deleted


if __name__ == "__main__":
    CanadianJobbankCrawler().run()
