"""
actions/apply_to_jobs/keywords.py

Software job keywords. Rules:
  - >= 7 characters
  - title search only, so every term must be unambiguous as a job title
  - no bare generic words ("engineer", "developer", "analyst" alone are too broad)
  - no non-technical roles (management, coaching, writing, etc.)
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
