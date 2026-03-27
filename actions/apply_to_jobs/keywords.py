"""
actions/apply_to_jobs/keywords.py

Two keyword sets:
  SOFTWARE_KEYWORDS  — remote software roles (title-search only, >= 7 chars,
                       no bare generics, no non-technical roles)
  PLACEMENT_KEYWORDS — internship / co-op / summer student roles filtered
                       to a specific geographic area (see main.py)
"""

SOFTWARE_KEYWORDS = [
    # Software / general
    "software developer",
    "software engineer",
    "software programmer",
    "software architect",
    "application developer",
    "application engineer",
    "systems developer",
    "systems software",
    "full stack developer",
    "full stack engineer",
    "fullstack developer",

    # Web / frontend / backend
    "web developer",
    "web engineer",
    "frontend developer",
    "frontend engineer",
    "backend developer",
    "backend engineer",

    # Mobile
    "mobile developer",
    "mobile engineer",
    "iOS developer",
    "Android developer",
    "app developer",

    # Data
    "data analyst",
    "data engineer",
    "data scientist",
    "data architect",
    "data developer",
    "database developer",
    "database administrator",
    "database engineer",
    "ETL developer",
    "BI developer",
    "business intelligence developer",
    "analytics engineer",
    "reporting analyst",
    "quantitative analyst",
    "SQL developer",
    "Spark developer",

    # DevOps / infrastructure / cloud
    "DevOps engineer",
    "site reliability engineer",
    "platform engineer",
    "infrastructure engineer",
    "cloud engineer",
    "cloud architect",
    "solutions architect",
    "systems architect",
    "Kubernetes engineer",
    "Terraform engineer",
    "Azure developer",

    # ML / AI
    "machine learning engineer",
    "ML engineer",
    "AI engineer",
    "deep learning engineer",
    "computer vision engineer",
    "NLP engineer",
    "artificial intelligence engineer",

    # QA / testing / automation
    "QA engineer",
    "quality assurance engineer",
    "test engineer",
    "automation engineer",
    "test automation",

    # Security
    "security engineer",
    "cybersecurity engineer",
    "penetration tester",
    "application security",

    # Networking
    "network engineer",
    "network developer",

    # Embedded / firmware
    "embedded developer",
    "embedded systems engineer",
    "firmware engineer",

    # Integration / API
    "integration engineer",
    "API developer",

    # Game dev
    "game developer",
    "game engineer",
    "graphics programmer",

    # CRM / ERP / enterprise
    "CRM developer",
    "ERP developer",
    "Salesforce developer",
    "SAP developer",

    # Technologies as roles (specific enough to be unambiguous)
    "JavaScript developer",
    "TypeScript developer",
    "Python developer",
    "Java developer",
    "React developer",
    "Angular developer",
    "Go developer",
    "PHP developer",
    "Swift developer",
    "Ruby developer",
    "Rust developer",
    "dotnet developer",
    "C# developer",
]

# ── internship / co-op / summer student keywords ──────────────────────────────
# Used with a city-based location filter (ON cities) rather than remote_only.
#
# Real job titles rarely read "software intern" — they read things like
# "Software Developer Intern" or "Co-op Student – Data".  These bare terms
# matched against the title column, combined with the city/province filter,
# keep results tight without over-engineering the compound phrases.
PLACEMENT_KEYWORDS = [
    # Placement-type words (broad — the city filter narrows the noise)
    "intern",
    "internship",
    "co-op",
    "coop",
    "summer student",
    "student position",
    "work placement",

    # Junior / entry-level software titles (specific enough on their own)
    "junior developer",
    "junior engineer",
    "junior software developer",
    "junior software engineer",
    "junior web developer",
    "junior data analyst",
    "junior data engineer",
    "entry level developer",
    "entry level engineer",
    "entry level software",
    "new grad developer",
    "new grad engineer",
    "graduate developer",
    "graduate engineer",
    "graduate software",
    "associate developer",
    "associate engineer",
    "associate software",
]
