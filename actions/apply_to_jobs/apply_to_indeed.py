"""
actions/apply_to_jobs/apply_to_indeed.py

Fetch easy-apply Indeed jobs matching software keywords, then apply.
"""
from __future__ import annotations

import msvcrt
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any
import time
import requests
from hyperSel import instance, parser, log
import random
from collections import defaultdict
from datetime import date, datetime
from selenium.webdriver.support.ui import Select as SeleniumSelect

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from some_keywords import SOFTWARE_KEYWORDS

# ── Job titles that are auto-skipped (case-insensitive substring match) ───── #
SKIP_KEYWORDS: list[str] = [
    "senior",
    "manager",
    "management",
    "cnc",
    "numerical",
]

INDEED_DB   = ROOT / "src/_indeed_jobs/database.sqlite"
APPLIED_DB  = ROOT / "src/_indeed_jobs/applied_jobs.sqlite"


# ── ANSI colour helpers ───────────────────────────────────────────────────── #
_R  = "\033[91m"   # bright red
_G  = "\033[92m"   # bright green
_Y  = "\033[93m"   # bright yellow
_C  = "\033[96m"   # bright cyan
_M  = "\033[95m"   # bright magenta
_B  = "\033[1m"    # bold
_X  = "\033[0m"    # reset


def get_indeed_easy_apply_jobs() -> list[dict[str, Any]]:
    if not INDEED_DB.exists():
        print(f"Indeed DB not found: {INDEED_DB}")
        return []

    kw_clauses = " OR ".join(["LOWER(title) LIKE ?" ] * len(SOFTWARE_KEYWORDS))
    params: list[Any] = [f"%{kw.lower()}%" for kw in SOFTWARE_KEYWORDS]

    sql = f"""
        SELECT * FROM items
        WHERE is_easy_apply = 1
          AND ({kw_clauses})
    """

    conn = sqlite3.connect(INDEED_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ── Applied-jobs DB ───────────────────────────────────────────────────────── #

def _extract_jk(url: str) -> str | None:
    """Pull the 'jk' job-key from any Indeed URL — the stable canonical ID."""
    m = re.search(r'[?&]jk=([a-zA-Z0-9]+)', url or "")
    return m.group(1) if m else None


def init_applied_db() -> None:
    """Create the applied_jobs table if it doesn't exist yet."""
    APPLIED_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(APPLIED_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applied_jobs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            jk          TEXT,
            title       TEXT,
            company     TEXT,
            url         TEXT,
            applied_at  TEXT
        )
    """)
    conn.commit()
    conn.close()


def already_applied(job: dict) -> bool:
    """
    Dedup check.  Matches on jk (canonical ID) first, then falls back to
    normalised title + company so minor URL changes don't let dupes through.
    """
    if not APPLIED_DB.exists():
        return False
    url     = job.get("url", "")
    title   = (job.get("title",   "") or "").lower().strip()
    company = (job.get("company", "") or "").lower().strip()
    jk      = _extract_jk(url)
    conn = sqlite3.connect(APPLIED_DB)
    try:
        if jk:
            if conn.execute("SELECT 1 FROM applied_jobs WHERE jk=?", (jk,)).fetchone():
                return True
        if title and company:
            if conn.execute(
                "SELECT 1 FROM applied_jobs WHERE LOWER(title)=? AND LOWER(company)=?",
                (title, company),
            ).fetchone():
                return True
    finally:
        conn.close()
    return False


def record_application(job: dict) -> None:
    """Insert a successfully submitted job into applied_jobs with a timestamp."""
    url        = job.get("url", "")
    jk         = _extract_jk(url)
    title      = job.get("title",   "")
    company    = job.get("company", "")
    applied_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(APPLIED_DB)
    try:
        conn.execute(
            "INSERT INTO applied_jobs (jk, title, company, url, applied_at) VALUES (?,?,?,?,?)",
            (jk, title, company, url, applied_at),
        )
        conn.commit()
    finally:
        conn.close()
    _log(f"  -> RECORDED application: jk={jk!r}  title={title!r}  applied_at={applied_at}")


# ── Pause / skip CLI ──────────────────────────────────────────────────────── #

def _check_pause_key() -> bool:
    """Non-blocking check: returns True if 'p' or 'P' was pressed."""
    if msvcrt.kbhit():
        key = msvcrt.getch()
        if key in (b'p', b'P'):
            return True
    return False


def _show_pause_menu() -> str:
    """
    Show a coloured pause menu.
    Returns 'c' (continue) or 's' (skip current job).
    """
    bar = f"{_R}{'=' * 54}{_X}"
    print(f"\n{bar}")
    print(f"{_B}{_Y}   ⏸   PAUSED — CHOOSE AN ACTION{_X}")
    print(bar)
    print(f"   {_G}[C]{_X}  {_B}Continue{_X} — keep going with current job")
    print(f"   {_C}[S]{_X}  {_B}Skip{_X}     — abandon this job, move to next")
    print(bar)
    while True:
        raw = input(f"   {_B}Your choice (C / S): {_X}").strip().lower()
        if raw in ("c", "s"):
            print(f"\n   {_M}>> {raw.upper()} selected.{_X}\n")
            return raw
        print(f"   {_Y}  !! Please type C or S then Enter{_X}")


# ── Smart field defaults ──────────────────────────────────────────────────── #
DUMMY_TEXT       = "n/a"
NEXT_BTN_XPATH   = '//*[@id="mosaic-provider-module-apply-questions"]/div/div/button'
SUBMIT_BTN_XPATH = '//*[@id="mosaic-provider-module-apply-preview"]/div/div/div[3]/button'

# ── Pre-written long-form answers ─────────────────────────────────────────── #
_WORK_AUTH_ANSWER = (
    "I am a Canadian citizen and am fully authorized to work in Canada without any "
    "restrictions. I do not require, nor will I in the future require, employer "
    "sponsorship to work in Canada."
)

_PORTFOLIO_ANSWER = (
    "My portfolio is available at https://foreandr.github.io/, featuring 40+ interactive "
    "tools spanning data visualization, mathematics, graph networks, and game theory. "
    "One of the more complex user journeys I simplified was the World Data suite — users "
    "previously had to cross-reference IMF, World Bank, and WHO datasets across separate "
    "platforms; I consolidated everything into a single interactive 3D globe and flat "
    "choropleth map with unified controls, turning a multi-tab research workflow into a "
    "single spatial exploration experience. "
    "The result was a dramatically lower barrier to entry for non-specialist users trying "
    "to make sense of global economic and resource data."
)

_AI_UX_ANSWER = (
    "I integrate AI across the full development and design cycle rather than at a single "
    "stage — Claude for architecture decisions, code review, and writing clear technical "
    "documentation; GitHub Copilot and Codex for accelerating implementation so prototypes "
    "go from idea to working demo in hours instead of days; and Gemini/Bard for quick "
    "research synthesis when I need to survey a domain fast. "
    "For visual and UX work I use generative image tools to explore interface directions "
    "early, which lets me validate concepts with stakeholders before committing to "
    "high-fidelity builds. "
    "The net effect is a dramatically compressed feedback loop — I can ship a testable "
    "prototype, gather real user signal, and iterate in the same time it used to take "
    "just to finish the initial spec."
)

_COVER_LETTER = (
    "I am a software engineer with 3+ years of experience building full-stack web "
    "applications, data dashboards, and interactive tooling. My portfolio at "
    "https://foreandr.github.io/ demonstrates hands-on work across Python, JavaScript, "
    "React, and data visualization. I thrive in fast-moving environments, communicate "
    "clearly across technical and non-technical stakeholders, and am eager to bring "
    "that energy to your team. I look forward to the opportunity."
)

_WHY_THIS_COMPANY = (
    "I am drawn to this role because it aligns well with my background in software "
    "engineering and my genuine interest in building tools that solve real problems. "
    "I bring strong technical fundamentals, a bias toward shipping, and a habit of "
    "investing in code quality and documentation so the next person on the codebase "
    "has a good time. I believe I can contribute meaningfully from day one."
)

_DESCRIBE_YOURSELF = (
    "I am a full-stack software engineer who enjoys working across the entire product "
    "lifecycle — from shaping requirements and architecting solutions to shipping, "
    "monitoring, and iterating. I have a strong foundation in Python and JavaScript, "
    "build side projects obsessively, and use AI tooling daily to stay productive. "
    "I communicate well, learn fast, and care about the quality of what I ship."
)

_STRENGTHS_ANSWER = (
    "My key strengths are problem decomposition, rapid prototyping, and clear "
    "technical communication. I break large ambiguous problems into concrete steps, "
    "build working prototypes quickly to validate assumptions early, and document "
    "decisions so teams stay aligned. I am also highly self-directed — I do not need "
    "close supervision to stay productive and focused."
)

_WEAKNESSES_ANSWER = (
    "I sometimes over-engineer early-stage solutions by thinking too far ahead. "
    "I have learned to counteract this by deliberately time-boxing exploration phases "
    "and shipping a simpler version first, then iterating based on real feedback "
    "rather than hypothetical requirements."
)

_TOOLS_GENERIC = (
    "I have worked on several projects requiring this skill set, applying it across "
    "full-stack development, data pipelines, and interactive tooling — you can see "
    "examples at https://foreandr.github.io/. I am comfortable working independently "
    "and in collaborative team environments and have used these tools across multiple "
    "stages of the software development lifecycle."
)

# ── Favourite libraries / frameworks per ecosystem ────────────────────────── #
_FAV_LIBRARY_BY_TECH: dict[str, str] = {
    # JavaScript / frontend
    "javascript":   "React — it solves declarative UI state management and component "
                    "reuse, making complex interfaces predictable and easy to reason "
                    "about. I have used it extensively across projects at "
                    "https://foreandr.github.io/.",
    "js":           "React — declarative, component-based, and composable. It removes "
                    "the pain of manually syncing DOM state with application state.",
    "react":        "React — combined with hooks it gives a clean mental model for "
                    "side effects and state. Most of my interactive tools at "
                    "https://foreandr.github.io/ are React-based.",
    "typescript":   "Zod — it brings runtime type validation that mirrors your static "
                    "types, eliminating an entire class of runtime surprises at API "
                    "boundaries.",
    "frontend":     "React with Tailwind CSS — React for component logic and Tailwind "
                    "for utility-first styling. The combination lets me move fast "
                    "without fighting a CSS architecture.",
    "css":          "Tailwind CSS — utility-first classes keep styles co-located with "
                    "markup and eliminate the naming-ceremony overhead of BEM or CSS "
                    "modules.",
    "ui":           "React — see my interactive portfolio at https://foreandr.github.io/ "
                    "for examples of complex reactive UIs I have built.",
    "node":         "Express.js — minimal, unopinionated, and pairs naturally with "
                    "middleware composition. For heavier projects I reach for Fastify "
                    "for its schema-validation performance.",
    "angular":      "RxJS — the reactive streams model maps perfectly to async "
                    "event-driven Angular applications and makes complex data flows "
                    "composable and testable.",
    "vue":          "Pinia — cleaner than Vuex, TypeScript-friendly, and its store "
                    "definitions read almost like plain objects.",
    # Python
    "python":       "Pandas — for data wrangling nothing else comes close; the "
                    "DataFrame abstraction is expressive enough for 90% of ETL work "
                    "without leaving Python. For web I reach for FastAPI.",
    "django":       "Django REST Framework — it turns model definitions directly into "
                    "serialisable API endpoints with minimal boilerplate.",
    "flask":        "Flask-SQLAlchemy — the ORM integration makes database work "
                    "feel native to the Flask request lifecycle.",
    "fastapi":      "Pydantic — FastAPI is built on it, and having request/response "
                    "models validated automatically at the boundary eliminates a huge "
                    "class of runtime bugs.",
    # Data / ML
    "data":         "Pandas + Plotly — Pandas for transformation and Plotly for "
                    "interactive visualisation. Several charts at "
                    "https://foreandr.github.io/ are built with this stack.",
    "machine learning": "scikit-learn — consistent fit/predict API across every "
                    "algorithm makes experimentation fast and reproducible.",
    "ml":           "scikit-learn — the Pipeline abstraction is especially useful for "
                    "keeping feature engineering and modelling steps decoupled.",
    # Backend / infra
    "java":         "Spring Boot — autoconfiguration drastically reduces boilerplate "
                    "and its ecosystem (Security, Data JPA, Actuator) covers almost "
                    "every enterprise concern out of the box.",
    "kotlin":       "Ktor — lightweight, coroutine-native, and feels like idiomatic "
                    "Kotlin rather than a Java framework with Kotlin syntax on top.",
    "php":          "Laravel — Eloquent ORM, Artisan scaffolding, and first-class "
                    "queue/job support make it the most productive PHP ecosystem "
                    "for full applications.",
    "ruby":         "Rails ActiveRecord — convention over configuration at its best; "
                    "migrations + associations + scopes cover most data-access "
                    "patterns with minimal code.",
    "go":           "Go-Chi — a lightweight router that stays close to the stdlib "
                    "http.Handler interface without imposing opinions on project "
                    "structure.",
    "rust":         "Tokio — async runtime that makes writing high-throughput "
                    "network services safe and ergonomic without sacrificing "
                    "Rust's ownership guarantees.",
    # DB / infra
    "sql":          "PostgreSQL with window functions — recursive CTEs and window "
                    "functions cover analytical query patterns I would otherwise "
                    "push to application code.",
    "graphql":      "Apollo Client — its caching layer and React hooks integration "
                    "reduce data-fetching boilerplate significantly.",
    "testing":      "pytest — fixtures + parametrise decorators make test suites "
                    "expressive and easy to maintain. I pair it with pytest-mock "
                    "for isolation.",
    "devops":       "Docker Compose — local multi-service orchestration without "
                    "Kubernetes overhead is invaluable during development.",
}

_FAV_LIBRARY_GENERIC = (
    "My go-to is React for frontend work and FastAPI or Express.js on the backend. "
    "React solves declarative UI state management and component reuse, while FastAPI "
    "gives schema-validated endpoints with almost no boilerplate. "
    "You can see both in action across projects at https://foreandr.github.io/."
)


def _fav_library_answer(label: str) -> str:
    """Return a tailored favourite-library answer based on tech mentioned in label."""
    l = label.lower()
    for key, answer in _FAV_LIBRARY_BY_TECH.items():
        if key in l:
            return answer
    return _FAV_LIBRARY_GENERIC


def _tools_experience_answer(label: str) -> str:
    """
    Extract the specific technology name from the question label and return
    a tailored experience blurb (always mentions the portfolio). Falls back
    to the generic answer.
    """
    _TECH_MAP = {
        "python":        "Python",
        "javascript":    "JavaScript",
        "typescript":    "TypeScript",
        "react":         "React",
        "angular":       "Angular",
        "vue":           "Vue.js",
        "node":          "Node.js",
        "next.js":       "Next.js",
        "nuxt":          "Nuxt.js",
        "java":          "Java",
        "c#":            "C#",
        "c++":           "C++",
        "php":           "PHP",
        "ruby":          "Ruby",
        "golang":        "Go",
        "go ":           "Go",
        "rust":          "Rust",
        "swift":         "Swift",
        "kotlin":        "Kotlin",
        "sql":           "SQL",
        "mysql":         "MySQL",
        "postgresql":    "PostgreSQL",
        "postgres":      "PostgreSQL",
        "mongodb":       "MongoDB",
        "redis":         "Redis",
        "elasticsearch": "Elasticsearch",
        "aws":           "AWS",
        "azure":         "Azure",
        "gcp":           "GCP",
        "google cloud":  "Google Cloud",
        "docker":        "Docker",
        "kubernetes":    "Kubernetes",
        "terraform":     "Terraform",
        "git":           "Git",
        "jenkins":       "Jenkins",
        "graphql":       "GraphQL",
        "rest api":      "REST APIs",
        "django":        "Django",
        "flask":         "Flask",
        "fastapi":       "FastAPI",
        "spring":        "Spring",
        "express":       "Express.js",
        "agile":         "Agile",
        "scrum":         "Scrum",
        "jira":          "Jira",
        "figma":         "Figma",
        "photoshop":     "Photoshop",
        "linux":         "Linux",
        "bash":          "Bash / shell scripting",
        "powershell":    "PowerShell",
        "selenium":      "Selenium",
        "pytest":        "pytest",
        "jest":          "Jest",
        "sass":          "Sass / SCSS",
        "tailwind":      "Tailwind CSS",
        "webpack":       "Webpack",
        "ci/cd":         "CI/CD pipelines",
    }
    l = label.lower()
    for key, display in _TECH_MAP.items():
        if key in l:
            return (
                f"I have worked on several projects utilizing {display}, including "
                f"building production-grade applications and tooling — examples are "
                f"visible at https://foreandr.github.io/. I am comfortable with "
                f"{display} in both independent and team settings and have applied "
                f"it across multiple stages of the software development lifecycle."
            )
    return _TOOLS_GENERIC


def _next_month_first() -> str:
    """Return YYYY-MM-DD for the 1st of next month."""
    today = date.today()
    month = today.month % 12 + 1
    year  = today.year + (1 if today.month == 12 else 0)
    return f"{year}-{month:02d}-01"


def _default_for_label(label: str) -> str:
    """
    Map a question label / question text to a sensible canned answer.
    Ordered from most-specific (long-form content checks) to least-specific.
    """
    l = label.lower()

    # ── 0. Long-form / paragraph questions ────────────────────────────── #
    if ("authorization" in l or "work authorization" in l) and ("canada" in l or "sponsor" in l):
        return _WORK_AUTH_ANSWER
    if "confirm your current work authorization" in l or "require employer sponsorship" in l:
        return _WORK_AUTH_ANSWER
    if "portfolio" in l and ("describe" in l or "complex" in l or "journey" in l):
        return _PORTFOLIO_ANSWER
    if ("prototyping" in l or "user testing" in l or "asset generation" in l or "ux workflow" in l) \
            and ("ai" in l or "artificial intelligence" in l or "speed" in l):
        return _AI_UX_ANSWER
    if "use ai to" in l or "ai workflow" in l or ("ai" in l and "workflow" in l):
        return _AI_UX_ANSWER
    if "cover letter" in l:
        return _COVER_LETTER
    if "why do you want" in l or "why are you interested" in l or "why this company" in l \
            or "why this role" in l or "why this position" in l:
        return _WHY_THIS_COMPANY
    if "describe yourself" in l or "tell us about yourself" in l or "tell me about yourself" in l \
            or "brief introduction" in l:
        return _DESCRIBE_YOURSELF
    if "strength" in l and ("your" in l or "key" in l or "greatest" in l):
        return _STRENGTHS_ANSWER
    if "weakness" in l or "area of improvement" in l or "areas for improvement" in l:
        return _WEAKNESSES_ANSWER
    if ("describe" in l or "explain" in l or "tell us" in l or "elaborate" in l) \
            and ("experience with" in l or "experience in" in l or "background in" in l
                 or "skills" in l or "tool" in l or "technolog" in l):
        return _tools_experience_answer(l)
    if "share your portfolio" in l or "provide your portfolio" in l \
            or "portfolio link" in l or "portfolio url" in l:
        return "https://foreandr.github.io/"

    # ── 0b. Skill rating (must come before experience numeric check) ───── #
    # "How would you rate your X skills?"  "Rate your proficiency in X"
    # "Skill level for X"  "Your level of expertise in X"
    _SKILL_RATING_TRIGGERS = (
        "how would you rate", "rate your", "rate yourself",
        "skill level", "proficiency level", "level of proficiency",
        "level of expertise", "your expertise", "your proficiency",
        "self-rate", "self rate",
    )
    if any(t in l for t in _SKILL_RATING_TRIGGERS):
        return "Advanced"

    # ── 0c. Favourite library / framework / tool questions ─────────────── #
    _FAV_TRIGGERS = (
        "favourite", "favorite", "preferred library", "preferred framework",
        "preferred tool", "go-to library", "go-to framework", "go to library",
        "what library", "what framework",
    )
    if any(t in l for t in _FAV_TRIGGERS):
        if "library" in l or "framework" in l or "tool" in l \
                or "stack" in l or "language" in l:
            return _fav_library_answer(l)

    # ── 0d. "Do you have / Have you" questions ─────────────────────────── #
    # Criminal / sponsor exceptions must be caught FIRST (section 1 below).
    # Check them inline here so we don't accidentally return "Yes" for those.
    _BAD_CONTEXT = {
        "criminal", "convicted", "felony", "offence", "offense",
        "sponsor", "sponsorship", "visa", "work permit",
        "how many", "how long", "years of", "years working",
        "years using", "years with", "years in",
    }
    _HAVE_TRIGGERS = (
        "do you have", "have you", "are you able to", "can you",
        "will you", "are you willing", "are you open to",
        "are you comfortable", "are you experienced",
    )
    # Degree "please specify" questions → give the actual degree text
    _DEGREE_SPECIFY = ("bachelor", "degree in", "diploma in", "specify")
    if any(t in l for t in _HAVE_TRIGGERS) and not any(k in l for k in _BAD_CONTEXT):
        if any(t in l for t in _DEGREE_SPECIFY) and ("specify" in l or "which" in l or "what" in l):
            return "Bachelor's in Mathematics, Advanced Diploma in Computer Programming and Analysis"
        return "Yes"

    # ── 1. Work eligibility / legal / sponsorship ─────────────────────── #
    if "sponsor" in l or "sponsorship" in l or "require.*visa" in l:
        return "No"
    if "visa" in l and ("require" in l or "need" in l or "future" in l):
        return "No"
    if "work permit" in l and ("require" in l or "need" in l):
        return "No"
    if "criminal" in l or "convicted" in l or "felony" in l or "offence" in l or "offense" in l:
        return "No"
    if "background check" in l:
        return "Yes"
    if "drug test" in l or "drug screen" in l:
        return "Yes"
    if "legally authorized" in l or "legally eligible" in l or "legally able" in l:
        return "Yes"
    if "right to work" in l:
        return "Yes"
    if "eligible to work" in l or "authorized to work" in l:
        return "Yes"
    if "citizen" in l and "canada" in l:
        return "Yes"
    if "permanent resident" in l:
        return "Yes"
    if "non-compete" in l or "non compete" in l:
        return "No"
    if "conflict of interest" in l:
        return "No"

    # ── 2. Personal / contact ──────────────────────────────────────────── #
    if l.strip() in ("first name", "given name", "firstname"):
        return "Andre"
    if l.strip() in ("last name", "surname", "family name", "lastname"):
        return "Fore"
    if l.strip() in ("full name", "your name", "name"):
        return "Andre Fore"
    if "middle name" in l or "middle initial" in l:
        return "n/a"
    if "phone" in l or "telephone" in l or "mobile" in l or "cell" in l:
        return "5196363173"
    if "email" in l:
        return "foreandr@gmail.com"
    if "gender" in l or "pronouns" in l or "sex " in l:
        return "Prefer not to say"
    if "date of birth" in l or "birth date" in l or "dob" in l:
        return "n/a"
    if "age " in l or l.strip() == "age":
        return "n/a"
    if "nationality" in l:
        return "Canadian"
    if "ethnicity" in l or "race " in l or "racial" in l:
        return "Prefer not to say"
    if "veteran" in l or "military" in l:
        return "No"
    if "disability" in l or "disabled" in l or "accommodation" in l:
        return "No"

    # ── 3. Location / relocation ───────────────────────────────────────── #
    if "linkedin"                                              in l: return "n/a"
    if "date available"                                        in l: return _next_month_first()
    if "start date" in l or "available to start" in l or "when can you start" in l:
        return _next_month_first()
    if "postal"      in l or "zip"                            in l: return "n5v 4e1"
    if "state"       in l or "province"                       in l: return "Ontario"
    if l.strip() in ("city", "city*", "current city", "city of residence"):
        return "London"
    if "city"                                                  in l: return "London"
    if "address line 2" in l or "apt" in l or "suite" in l or "unit" in l:
        return "n/a"
    if "address"                                               in l: return "745 Railton"
    if "willing to relocate" in l or "open to relocate" in l or "relocation" in l:
        return "Yes"
    if "willing to commute" in l or "able to commute" in l or "commute" in l:
        return "Yes"
    if "remote" in l and ("prefer" in l or "open" in l or "willing" in l or "work" in l):
        return "Yes"
    if "hybrid" in l:
        return "Yes"
    if "on-site" in l or "onsite" in l or "in-office" in l or "in office" in l:
        return "Yes"

    # ── 4. Compensation ────────────────────────────────────────────────── #
    if "pay"           in l or "salary"    in l or "wage"     in l: return "80000"
    if "expected"      in l and ("rate" in l or "compen" in l):     return "80000"
    if "current salary" in l or "current compensation" in l:        return "75000"
    if "hourly rate" in l or "rate per hour" in l or "$/hr" in l:   return "38"
    if "desired pay" in l or "desired salary" in l:                 return "80000"

    # ── 5. Availability / schedule ────────────────────────────────────── #
    if "notice period" in l or "how much notice" in l or "how soon" in l:
        return "2 weeks"
    if "hours per week" in l or "hours/week" in l:
        return "40"
    if "full.time" in l or "full time" in l:
        return "Yes"
    if "part.time" in l or "part time" in l:
        return "No"
    if "overtime" in l:
        return "Yes"
    if "weekend" in l:
        return "Yes"
    if "shift" in l and ("work" in l or "prefer" in l or "available" in l):
        return "Any shift"
    if "available immediate" in l or "immediately available" in l:
        return "No — 2 weeks notice required"

    # ── 6. Education ───────────────────────────────────────────────────── #
    if "education" in l or "highest level" in l or ("level" in l and "degree" in l):
        return "Bachelor's Degree"
    if "university" in l or "college" in l or "institution" in l or "school name" in l:
        return "University of Western Ontario"
    if "field of study" in l or "major" in l or "program" in l or "discipline" in l:
        return "Computer Science"
    if "graduation" in l and ("year" in l or "date" in l):
        return "2022"
    if "gpa" in l or "grade point" in l:
        return "3.5"

    # ── 7. Experience — numeric (text inputs / number inputs) ─────────── #
    # Catches "years of experience", "how many years", "X years experience", etc.
    if "experience" in l or "years of" in l or "how many years" in l \
            or "years working" in l or "years using" in l or "years with" in l \
            or "years in" in l:
        return "3"

    # ── 8. Specific tech / tool years (also caught above but belt+suspenders) #
    _TECH_TOKENS = [
        "python", "javascript", "typescript", "react", "angular", "vue", "node",
        "java", "c#", "c++", "php", "ruby", "golang", "rust", "swift", "kotlin",
        "sql", "mysql", "postgresql", "mongodb", "redis", "aws", "azure", "gcp",
        "docker", "kubernetes", "terraform", "git", "jenkins", "graphql", "django",
        "flask", "fastapi", "spring", "express", "agile", "scrum", "jira", "figma",
        "linux", "bash", "selenium", "sass", "tailwind", "webpack",
    ]
    for tok in _TECH_TOKENS:
        if tok in l:
            # If they are asking for a number of years with the tech
            if "year" in l or "how long" in l or "how many" in l:
                return "3"
            # Otherwise it's a descriptive question
            return _tools_experience_answer(l)

    # ── 9. Role / company / job-specific ──────────────────────────────── #
    if l.strip() == "job title":                                    return "Software Engineer"
    if l.strip() in ("company", "company name", "employer"):       return "QuickQr"
    if "current job title" in l or "current position" in l or "current role" in l:
        return "Software Engineer"
    if "current company" in l or "current employer" in l:         return "QuickQr"
    if "website" in l or "blog" in l or "portfolio" in l:
        return "https://foreandr.github.io/"
    if "github" in l or "gitlab" in l or "bitbucket" in l:
        return "https://github.com/foreandr"
    if "referred" in l or "referral" in l or "referred by" in l:  return "n/a"
    if "how did you hear" in l or "how did you find" in l:        return "Indeed"

    # ── 10. Catch-all ─────────────────────────────────────────────────── #
    return DUMMY_TEXT


# ── Radio / checkbox intent rules ─────────────────────────────────────────── #

# Any of these in the question text → try to click "No"
_PREFER_NO = {
    "sponsor", "visa", "sponsorship", "require.*visa",
    "criminal", "convicted", "felony", "offence", "offense",
    "non-compete", "conflict of interest",
}

# Any of these → try to click "Yes"
# Note: _PREFER_NO is checked first, so criminal/sponsor questions are
# still answered "No" even though "do you have" would match here.
_PREFER_YES = {
    # Work eligibility
    "authorized", "eligible", "legally", "citizen",
    "right to work", "background check", "drug test",
    "permanent resident", "legally able", "legally authorized",
    "work in canada",
    # Availability / logistics
    "commute", "relocate", "remote", "hybrid", "overtime",
    "full.time", "full time",
    # Generic "do you have / have you" questions
    "do you have", "have you", "are you able to",
    "are you willing", "are you open to",
    "are you comfortable", "are you experienced",
    # Degree / qualification
    "bachelor", "degree", "diploma", "certified", "certification",
    # Experience / tools / skills
    "experience with", "experience in", "worked with", "worked on",
    "used", "implemented", "developed", "familiar with",
    "knowledge of", "proficient",
}


_SKILL_RATING_TRIGGERS = (
    "how would you rate", "rate your", "rate yourself",
    "skill level", "proficiency level", "level of proficiency",
    "level of expertise", "your expertise", "your proficiency",
    "self-rate", "self rate",
)

# Ordered preference: try each in turn until one matches an option value or label
_SKILL_RATING_PREFERRED = ("advanced", "proficient", "senior", "intermediate", "4", "3")


def _pick_radio_to_click(inputs, q_text: str):
    """
    Return the radio/checkbox <input> soup tag to click, based on question text.

    Priority:
      1. Skill-rating questions  → prefer Advanced / Proficient / Intermediate
      2. _PREFER_NO keywords     → click "No"
      3. _PREFER_YES keywords    → click "Yes"
      4. Fallback                → first option
    """
    l = q_text.lower()

    # ── Skill-rating radio (Beginner / Intermediate / Advanced / Expert) ── #
    if any(t in l for t in _SKILL_RATING_TRIGGERS):
        for preferred in _SKILL_RATING_PREFERRED:
            for inp in inputs:
                val      = inp.get("value", "").lower()
                lbl_text = (inp.parent.get_text(strip=True) if inp.parent else "").lower()
                if preferred in val or preferred in lbl_text:
                    return inp
        # Nothing matched preferred; still avoid "beginner" / "no experience"
        for inp in inputs:
            val = inp.get("value", "").lower()
            if "begin" not in val and "no exp" not in val and "none" not in val:
                return inp
        return inputs[-1] if inputs else None   # last option tends to be highest

    # ── Yes / No questions ────────────────────────────────────────────── #
    target = None
    for kw in _PREFER_NO:
        if re.search(kw, l):
            target = "no"
            break
    if target is None:
        for kw in _PREFER_YES:
            if re.search(kw, l):
                target = "yes"
                break
    if target:
        for inp in inputs:
            if inp.get("value", "").lower() == target:
                return inp

    return inputs[0] if inputs else None


def _orphan_question_text(options_container) -> str:
    """
    For radio/checkbox groups NOT wrapped in a <fieldset>, walk up the DOM
    to find the nearest preceding sibling or ancestor text that looks like
    the question label.
    """
    node = options_container
    for _ in range(4):
        if node is None:
            break
        for sib in node.previous_siblings:
            if not hasattr(sib, "get_text"):
                continue
            t = sib.get_text(strip=True)
            if t:
                return t
        node = node.parent
    return "(unknown question)"


def _log(msg: str) -> None:
    """Print and write to the hyperSel log file."""
    print(msg)
    log.log_function(log_string=msg)


# ── Question parser / filler ──────────────────────────────────────────────── #

def parse_and_fill_questions(browser, soup) -> None:
    """
    Walk every form element on the current Indeed application page.
    Prints + logs each question and the value filled.
    Uses hyperSel browser methods exclusively (no raw selenium calls).
    """
    _log("\n" + "=" * 60)
    _log("PARSING QUESTIONS ON PAGE")
    _log("=" * 60)

    # ------------------------------------------------------------------ #
    # 0. ORPHAN RADIO / CHECKBOX GROUPS  (not inside a <fieldset>)        #
    # ------------------------------------------------------------------ #
    fieldset_input_ids = {
        inp.get("id", "")
        for fs in soup.find_all("fieldset")
        for inp in fs.find_all("input")
    }
    orphan_groups: dict[str, list] = defaultdict(list)
    for inp in soup.find_all("input", type=lambda t: t in ("radio", "checkbox")):
        if inp.get("id", "") not in fieldset_input_ids:
            orphan_groups[inp.get("name", "")].append(inp)

    _log(f"\n  [orphan radio/checkbox groups found: {len(orphan_groups)}]")
    for name, inputs in orphan_groups.items():
        options_container = inputs[0].parent.parent
        q_text   = _orphan_question_text(options_container)
        to_click = _pick_radio_to_click(inputs, q_text)
        _log(f"\n  QUESTION (orphan radio): {q_text!r}  name={name!r}")
        for inp in inputs:
            inp_id   = inp.get("id", "")
            val      = inp.get("value", "?")
            lbl_text = inp.parent.get_text(strip=True) if inp.parent else val
            _log(f"    [radio]  id={inp_id!r}  value={val!r}  label={lbl_text!r}")

        if to_click is not None:
            chosen_id  = to_click.get("id", "")
            chosen_val = to_click.get("value", "?")
            if chosen_id:
                xpath = f'//*[@id="{chosen_id}"]'
                try:
                    browser.click_element(by_type="xpath", value=xpath, timeout=3)
                    _log(f"    -> ANSWERED: {chosen_val!r}  xpath={xpath!r}")
                except Exception as e:
                    _log(f"    -> could not click {chosen_val!r}: {e}")

    # ------------------------------------------------------------------ #
    # 1. FIELDSETS  →  radio groups & checkbox groups                     #
    # ------------------------------------------------------------------ #
    fieldsets = soup.find_all("fieldset")
    _log(f"\n  [fieldsets found: {len(fieldsets)}]")
    for fieldset in fieldsets:
        legend   = fieldset.find("legend")
        q_text   = legend.get_text(strip=True) if legend else "(no legend)"
        inputs   = fieldset.find_all("input", type=lambda t: t in ("radio", "checkbox"))
        to_click = _pick_radio_to_click(inputs, q_text)
        _log(f"\n  QUESTION (fieldset): {q_text!r}")

        for inp in inputs:
            inp_id   = inp.get("id", "")
            lbl_tag  = fieldset.find("label", attrs={"for": inp_id})
            lbl_text = lbl_tag.get_text(strip=True) if lbl_tag else inp.get("value", "?")
            _log(f"    [{inp.get('type')}]  id={inp_id!r}  label={lbl_text!r}")

        if to_click is not None:
            chosen_id  = to_click.get("id", "")
            chosen_val = to_click.get("value", "?")
            if chosen_id:
                xpath = f'//*[@id="{chosen_id}"]'
                try:
                    browser.click_element(by_type="xpath", value=xpath, timeout=3)
                    _log(f"    -> ANSWERED: {chosen_val!r}  xpath={xpath!r}")
                except Exception as e:
                    _log(f"    -> could not click {chosen_val!r}: {e}")

    # ------------------------------------------------------------------ #
    # 2. TEXT / NUMBER / EMAIL / TEL inputs  (skip radio/checkbox/hidden) #
    # ------------------------------------------------------------------ #
    skip_types = {"radio", "checkbox", "submit", "hidden", "button", "file", "image", "reset"}
    text_inputs = [
        i for i in soup.find_all("input")
        if i.get("type", "text").lower() not in skip_types
    ]
    _log(f"\n  [text-like inputs found: {len(text_inputs)}]")
    for inp in text_inputs:
        inp_id   = inp.get("id", "")
        lbl_tag  = soup.find("label", attrs={"for": inp_id})
        q_text   = lbl_tag.get_text(strip=True) if lbl_tag else inp.get("placeholder", inp.get("name", "?"))
        inp_type = inp.get("type", "text")
        value    = _default_for_label(q_text)
        _log(f"\n  QUESTION (input/{inp_type}): {q_text!r}  id={inp_id!r}")
        if inp_id:
            xpath = f'//*[@id="{inp_id}"]'
            try:
                browser.clear_and_enter_text(by_type="xpath", value=xpath, content_to_enter=value, timeout=3)
                _log(f"    -> ANSWERED: {value!r}  xpath={xpath!r}")
            except Exception as e:
                _log(f"    -> could not fill: {e}")

    # ------------------------------------------------------------------ #
    # 3. SELECT dropdowns                                                 #
    # ------------------------------------------------------------------ #
    selects = soup.find_all("select")
    _log(f"\n  [selects found: {len(selects)}]")
    for sel in selects:
        sel_id  = sel.get("id", "")
        lbl_tag = soup.find("label", attrs={"for": sel_id})
        q_text  = lbl_tag.get_text(strip=True) if lbl_tag else sel.get("name", "?")
        options = sel.find_all("option")
        _log(f"\n  QUESTION (select): {q_text!r}  id={sel_id!r}")
        for opt in options:
            _log(f"    option  value={opt.get('value')!r}  text={opt.get_text(strip=True)!r}")

        if not sel_id:
            continue
        xpath = f'//*[@id="{sel_id}"]'
        try:
            el      = browser.get_elements(by_type="xpath", value=xpath, condition="visible", timeout=3)
            sel_obj = SeleniumSelect(el)
            l       = q_text.lower()
            non_empty = [o for o in options if o.get("value", "").strip()]

            def _pick_by_text(fragments: list[str]):
                """Find the first option whose display text contains any fragment."""
                for frag in fragments:
                    for o in non_empty:
                        if frag.lower() in o.get_text(strip=True).lower():
                            return o
                return None

            # ── Skill rating dropdowns ─────────────────────────────────── #
            if any(t in l for t in _SKILL_RATING_TRIGGERS):
                hit = None
                for preferred in _SKILL_RATING_PREFERRED:
                    hit = next(
                        (o for o in non_empty
                         if preferred in o.get_text(strip=True).lower()
                         or preferred in o.get("value", "").lower()),
                        None,
                    )
                    if hit:
                        break
                # avoid beginner if nothing else matched
                if hit is None:
                    hit = next(
                        (o for o in non_empty
                         if "begin" not in o.get_text(strip=True).lower()
                         and "no exp" not in o.get_text(strip=True).lower()),
                        non_empty[-1] if non_empty else None,
                    )
                if hit:
                    sel_obj.select_by_value(hit["value"])
                    _log(f"    -> ANSWERED (skill rating): {hit.get_text(strip=True)!r}  xpath={xpath!r}")

            elif "country" in l or "nation" in l:
                sel_obj.select_by_visible_text("Canada")
                _log(f"    -> ANSWERED: 'Canada'  xpath={xpath!r}")

            elif "education" in l or "highest level" in l or ("level" in l and "degree" in l):
                hit = _pick_by_text(["Bachelor", "bachelor"])
                if hit:
                    sel_obj.select_by_value(hit["value"])
                    _log(f"    -> ANSWERED (education): {hit.get_text(strip=True)!r}  xpath={xpath!r}")
                else:
                    _log(f"    -> could not find Bachelor option for education select")

            elif "experience" in l or "years of" in l or "how many years" in l \
                    or "years with" in l or "years using" in l or "years in" in l:
                # Prefer an option containing "3"; accept "2-3", "3-5", "3+" etc.
                hit = next(
                    (o for o in non_empty if "3" in o.get_text(strip=True) or "3" in o.get("value", "")),
                    None,
                )
                if hit is None:
                    hit = non_empty[0] if non_empty else None
                if hit:
                    sel_obj.select_by_value(hit["value"])
                    _log(f"    -> ANSWERED (experience): {hit.get_text(strip=True)!r}  xpath={xpath!r}")

            elif "sponsor" in l or "visa" in l or "sponsorship" in l:
                hit = _pick_by_text(["No", "no", "Not required", "I do not"])
                if hit:
                    sel_obj.select_by_value(hit["value"])
                    _log(f"    -> ANSWERED (sponsor/visa): {hit.get_text(strip=True)!r}  xpath={xpath!r}")
                elif non_empty:
                    sel_obj.select_by_value(non_empty[0]["value"])
                    _log(f"    -> ANSWERED (fallback): {non_empty[0].get_text(strip=True)!r}  xpath={xpath!r}")

            elif "gender" in l or "pronouns" in l:
                hit = _pick_by_text(["Prefer not", "Decline", "Rather not"])
                if hit:
                    sel_obj.select_by_value(hit["value"])
                    _log(f"    -> ANSWERED (gender): {hit.get_text(strip=True)!r}  xpath={xpath!r}")
                elif non_empty:
                    sel_obj.select_by_value(non_empty[0]["value"])

            elif "ethnicity" in l or "race" in l:
                hit = _pick_by_text(["Prefer not", "Decline", "Rather not", "No answer"])
                if hit:
                    sel_obj.select_by_value(hit["value"])
                    _log(f"    -> ANSWERED (ethnicity): {hit.get_text(strip=True)!r}  xpath={xpath!r}")
                elif non_empty:
                    sel_obj.select_by_value(non_empty[0]["value"])

            elif "province" in l or "state" in l:
                hit = _pick_by_text(["Ontario", "ON"])
                if hit:
                    sel_obj.select_by_value(hit["value"])
                    _log(f"    -> ANSWERED (province): {hit.get_text(strip=True)!r}  xpath={xpath!r}")
                elif non_empty:
                    sel_obj.select_by_value(non_empty[0]["value"])

            else:
                if non_empty:
                    sel_obj.select_by_value(non_empty[0]["value"])
                    _log(f"    -> ANSWERED: {non_empty[0]['value']!r}  xpath={xpath!r}")

        except Exception as e:
            _log(f"    -> could not select: {e}")

    # ------------------------------------------------------------------ #
    # 4. TEXTAREAS  (skip hidden / non-interactable ones like recaptcha)  #
    # ------------------------------------------------------------------ #
    textareas = soup.find_all("textarea")
    _log(f"\n  [textareas found: {len(textareas)}]")
    for ta in textareas:
        ta_id   = ta.get("id", "")
        lbl_tag = soup.find("label", attrs={"for": ta_id})
        q_text  = lbl_tag.get_text(strip=True) if lbl_tag else ta.get("name", "?")
        _log(f"\n  QUESTION (textarea): {q_text!r}  id={ta_id!r}")
        if "recaptcha" in ta_id.lower() or "recaptcha" in q_text.lower():
            _log("    -> skipping recaptcha textarea")
            continue
        value = _default_for_label(q_text)
        if ta_id:
            xpath = f'//*[@id="{ta_id}"]'
            try:
                browser.clear_and_enter_text(by_type="xpath", value=xpath, content_to_enter=value, timeout=3)
                _log(f"    -> ANSWERED: {value!r}  xpath={xpath!r}")
            except Exception as e:
                _log(f"    -> could not fill textarea: {e}")

    _log("\n" + "=" * 60 + "\n")


# ── Button helpers ────────────────────────────────────────────────────────── #

def click_submit_button(browser) -> bool:
    """
    Try to click the final Submit button on the preview/review page.
    Returns True if the URL changed after clicking.
    Returns False silently if the button is not present yet.
    """
    url_before = browser.WEBDRIVER.current_url
    try:
        browser.click_element(by_type="xpath", value=SUBMIT_BTN_XPATH, timeout=3)
        time.sleep(2)
        url_after = browser.WEBDRIVER.current_url
        if url_after != url_before:
            _log(f"  -> SUBMITTED! URL changed to: {url_after}")
            return True
        _log("  -> Submit button clicked but URL did not change — may need another action.")
    except Exception:
        pass
    return False


def click_next_button(browser) -> bool:
    """
    Click the Next / Continue button on the application form.
    Retries up to 5 times.  Returns True if the URL changed (page advanced).
    """
    url_before = browser.WEBDRIVER.current_url
    for attempt in range(1, 6):
        try:
            browser.click_element(by_type="xpath", value=NEXT_BTN_XPATH, timeout=3)
            time.sleep(2)
            url_after = browser.WEBDRIVER.current_url
            if url_after != url_before:
                _log(f"  -> Next clicked, URL changed to: {url_after}")
                return True
            _log(f"  -> URL unchanged after attempt {attempt}, retrying...")
        except Exception as e:
            _log(f"  -> Next button not found / not clickable (attempt {attempt}): {e}")
            break
    return False


# ── Main ──────────────────────────────────────────────────────────────────── #

def main() -> None:
    init_applied_db()
    jobs = get_indeed_easy_apply_jobs()
    random.shuffle(jobs)
    jobs.sort(key=lambda j: 0 if "data" in (j.get("title") or "").lower() else 1)
    print(f"Found {len(jobs)} easy-apply Indeed jobs matching keywords.")
    print(f"{_Y}TIP: Press {_B}P{_X}{_Y} at any time to pause and get options.{_X}\n")

    browser = instance.Browser(
        driver_choice="selenium",
        headless=False,
        zoom_level=100,
    )
    browser.init_browser()
    browser.go_to_site("https://ca.indeed.com/")
    input("I AM NOW LOGGED IN ")

    for job in jobs:
        url   = job.get("url")
        title = job.get("title", "?")
        print(f"\n{_C}{'─'*60}{_X}")
        print(f"{_B}JOB:{_X} {title}")
        print(f"{_B}URL:{_X} {url}")

        # ── Auto-skip unwanted job titles ─────────────────────────────── #
        title_lower = title.lower()
        matched_kw = next((kw for kw in SKIP_KEYWORDS if kw in title_lower), None)
        if matched_kw:
            _log(f"  -> AUTO-SKIPPING (keyword={matched_kw!r}): {title!r}")
            record_application(job)   # mark as seen so it won't appear again
            continue

        # ── Skip already-applied jobs ──────────────────────────────────── #
        if already_applied(job):
            jk = _extract_jk(url or "")
            _log(f"  -> SKIPPING (already applied): jk={jk!r}  title={title!r}")
            continue

        time.sleep(2)
        browser.go_to_site(url)
        soup = browser.return_current_soup()
        print("len(str(soup))", len(str(soup)))
        if "we can't find this page" in str(soup).lower():
            print("Page not found, skipping.")
            continue

        print("BEGINNING APPLICATION PROCESS")
        log.checkpoint()
        apply_now_xpath = (
            "/html/body/div/div/div[2]/div[3]/div/div/div[1]/div[2]/div[5]"
            "/div[1]/div/div/div/div/span/div/button"
        )
        try:
            browser.click_element(by_type="xpath", value=apply_now_xpath)
        except Exception as e:
            _log(f"  -> Could not click Apply Now button — skipping job. Error: {e}")
            continue

        loop_count   = 0
        _skip_job    = False   # set True by pause-menu 'S'

        while True:

            # ── P key → pause menu ─────────────────────────────────────── #
            if _check_pause_key():
                choice = _show_pause_menu()
                if choice == "s":
                    _log(f"  -> USER SKIPPED job: {url!r}")
                    _skip_job = True
                    break
                # else 'c' — just continue

            loop_count += 1
            time.sleep(2)

            # ── Human-assist gate: stuck for 20 iterations ─────────────── #
            if loop_count > 20:
                _log(f"\n  !! LOOPED {loop_count} TIMES — likely needs human input.")
                input("  >> Handle anything on screen then press ENTER to continue... ")
                loop_count = 0

            soup        = browser.return_current_soup()
            current_url = browser.WEBDRIVER.current_url
            print("CURRENT URL", current_url)

            # ── Successful submission ──────────────────────────────────── #
            if "your application has been submitted" in str(soup).lower():
                _log("  -> 'Your application has been submitted!' detected — moving to next job.")
                record_application(job)
                break

            # ── Resume-selection page ──────────────────────────────────── #
            if current_url == (
                "https://smartapply.indeed.com/beta/indeedapply/form"
                "/resume-selection-module/resume-selection"
            ):
                log.checkpoint()
                for i in range(1, 7):
                    btn_xpath = (
                        f'//*[@id="mosaic-provider-module-apply-resume-selection"]'
                        f"/div/div/div/div/form/div/button[{i}]"
                    )
                    try:
                        browser.click_element(by_type="xpath", value=btn_xpath, timeout=3)
                        time.sleep(2)
                        print("BREAKING INNER LOOP (resume selected)")
                        break
                    except Exception as e:
                        print(f"  Error clicking resume button [{i}]: {e}")
                        continue

            # ── Parse + fill every visible input field ─────────────────── #
            parse_and_fill_questions(browser, soup)

            # ── Try final submit (only works on preview page) ──────────── #
            if click_submit_button(browser):
                _log("  -> Application submitted — moving to next job.")
                record_application(job)
                break

            # ── Advance to next page ───────────────────────────────────── #
            click_next_button(browser)

        if _skip_job:
            continue   # outer for-loop: move to next job


if __name__ == "__main__":
    main()
