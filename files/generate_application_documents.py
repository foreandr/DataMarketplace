from __future__ import annotations

import html
from pathlib import Path
from playwright.sync_api import sync_playwright


BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"

RESUME_PDF = BASE_DIR / "Andre Foreman Resume.pdf"
TECH_COVER_PDF = BASE_DIR / "Andre Foreman Cover Letter.pdf"
GENERAL_COVER_PDF = BASE_DIR / "Andre_Foreman_Cover_Letter.pdf"

RESUME_DATA = {
    "name": "Andre Foreman",
    "email": "foreandr@gmail.com",
    "portfolio": "foreandr.github.io",
    "education": [
        {
            "institution": "Trent University",
            "detail": "B.Sc. in Mathematics, 2024-2026",
        },
        {
            "institution": "Fanshawe College of Applied Arts and Technology",
            "detail": "Advanced Diploma in Computer Programming and Analysis, 2020-2023",
        },
        {
            "institution": "Volleyball Canada",
            "detail": "Canadian National Excellence Program, 2017-2020",
        },
        {
            "institution": "Fanshawe College of Applied Arts and Technology",
            "detail": "Diploma in General Arts and Sciences, 2015-2017",
        },
    ],
    "experience": [
        {
            "role": "Security",
            "company": "The Social",
            "period": "Present",
            "description": (
                "Screen legal documentation, verify identification, and manage guest entry "
                "with a high standard of compliance while coordinating smooth access for "
                "reservations and high-profile guests."
            ),
        },
        {
            "role": "Office Manager & Software Engineer",
            "company": "QuickQr",
            "period": "2024",
            "description": (
                "Built automation for a Django REST API QR platform so schema changes flowed "
                "through the wider system automatically, saving hundreds of hours of manual "
                "rework. Managed payroll, bookkeeping, and QuickBooks operations to ensure "
                "staff were paid accurately and on time, including holidays, then developed "
                "an internal QuickBooks-like tool tailored to company workflows."
            ),
        },
        {
            "role": "Software Engineer",
            "company": "Reload Strathroy",
            "period": "2023",
            "description": (
                "Developed a large-scale automation and analytics tool that pulled vehicle "
                "listings from hundreds of websites, analyzed pricing across markets, and "
                "helped identify the cheapest make-and-model opportunities across North America."
            ),
        },
        {
            "role": "Security",
            "company": "The Ceeps and Barney's",
            "period": "2023",
            "description": (
                "Maintained a safe venue environment by monitoring crowds, resolving issues "
                "professionally, and working closely with staff to enforce entry, safety, and "
                "capacity policies during busy service hours."
            ),
        },
        {
            "role": "Software Engineering Intern",
            "company": "Perimeter Institute for Theoretical Physics",
            "period": "2022",
            "description": (
                "Created a mosaic-generation tool that rendered names using black hole image "
                "data and automated a custom email response workflow tied to inbound messages "
                "to the institute, turning a timely public outreach idea into a scalable process."
            ),
        },
        {
            "role": "Software Engineering Intern",
            "company": "A & L Laboratories",
            "period": "2022",
            "description": (
                "Automated a daily agronomy reporting workflow that collected reports, routed "
                "specific data to chemists, captured returned lab data, and produced finished "
                "outputs, eliminating roughly four hours of morning manual work each day."
            ),
        },
        {
            "role": "Game QA Intern",
            "company": "BetaDwarf",
            "period": "2021",
            "description": (
                "Brought more than 4,000 hours of hands-on game experience to testing, helping "
                "the team surface gameplay issues, improve balance, and refine player-facing design."
            ),
        },
        {
            "role": "Seasonal Associate",
            "company": "Walmart",
            "period": "2020",
            "description": (
                "Worked as an essential frontline employee during the COVID-19 pandemic, "
                "supporting customers and maintaining stock flow in a high-volume retail setting."
            ),
        },
        {
            "role": "Professional Athlete",
            "company": "Volleyball Canada",
            "period": "August 2017 - March 2020",
            "description": (
                "Represented Canada in elite international competition, balancing high-performance "
                "training with team execution, discipline, and consistent results under pressure."
            ),
        },
        {
            "role": "Clinic Intern",
            "company": "Fowler Kennedy Sports Medicine Clinic",
            "period": "2019",
            "description": (
                "Supported clinical staff with athlete care, treatment preparation, and rehab "
                "tracking in a fast-paced sports medicine environment."
            ),
        },
    ],
    "certifications": [
        "Standard First Aid & CPR (Level C) - Canadian Red Cross",
        "Private Investigative License - Ontario Ministry of the Solicitor General",
    ],
}


TECH_COVER_BODY = [
    (
        "I am a software engineer completing a B.Sc. in Mathematics at Trent University, "
        "with an Advanced Diploma in Computer Programming and Analysis from Fanshawe College. "
        "My background includes backend systems, internal tooling, automation, analytics, and "
        "full-stack product work."
    ),
    (
        "One of the strongest indicators of how I work is the software I have already shipped. "
        "I have built roughly one hundred public applications across different domains, many of "
        "which can be reviewed through my portfolio and GitHub presence. Those projects have "
        "generated real-world results, including approximately $30,000 in revenue, and they reflect "
        "my ability to solve practical problems for users."
    ),
    (
        "In professional settings, I have built automation that saved hundreds of hours, created "
        "internal business software, worked across data-heavy systems, and delivered tools that "
        "reduced manual effort for teams. I enjoy difficult problem solving, and I take ownership "
        "of getting useful systems into production."
    ),
    (
        "I would welcome the opportunity to contribute that same mindset to your team. Thank you "
        "for your consideration."
    ),
]

GENERAL_COVER_BODY = [
    (
        "My background spans software engineering, mathematics, operations, and high-performance "
        "team environments. I have built internal tools, automation systems, reporting workflows, "
        "and public-facing software, and I bring a practical, disciplined approach to the work I take on."
    ),
    (
        "Beyond traditional employment experience, I have written roughly one hundred public applications, "
        "many of which are available through my portfolio and GitHub presence. Those projects have solved "
        "real problems for people and have generated approximately $30,000 in revenue, which reflects both "
        "initiative and proven problem-solving ability."
    ),
    (
        "I was also a national team athlete, which taught me how to perform under pressure, stay accountable "
        "to a team, and maintain a high standard every day. I would be glad to bring that same reliability, "
        "work ethic, and adaptability to your organization."
    ),
    (
        "Thank you for your time and consideration. I would welcome the opportunity to speak further."
    ),
]


def paragraph(text: str) -> str:
    return f"<p>{html.escape(text)}</p>"


def render_resume_html() -> str:
    education_html = "".join(
        f"""
        <div class="entry">
          <div class="entry-head">
            <div class="role">{html.escape(item['institution'])}</div>
          </div>
          <div class="description">{html.escape(item['detail'])}</div>
        </div>
        """
        for item in RESUME_DATA["education"]
    )

    experience_html = "".join(
        f"""
        <div class="entry">
          <div class="entry-head">
            <div class="role">{html.escape(item['role'])}</div>
            <div class="meta">{html.escape(item['company'])} | {html.escape(item['period'])}</div>
          </div>
          <div class="description">{html.escape(item['description'])}</div>
        </div>
        """
        for item in RESUME_DATA["experience"]
    )

    certifications_html = "".join(
        f"<div class=\"cert-item\">{html.escape(item)}</div>"
        for item in RESUME_DATA["certifications"]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Andre Foreman Resume</title>
  <style>
    @page {{
      size: Letter;
      margin: 0.45in 0.55in;
    }}
    body {{
      font-family: "Times New Roman", Times, serif;
      color: #111;
      margin: 0;
      font-size: 10.5pt;
      line-height: 1.16;
    }}
    .page {{
      max-width: 7.4in;
      margin: 0 auto;
    }}
    h1 {{
      margin: 0;
      font-size: 19pt;
      text-align: center;
      font-weight: bold;
    }}
    .contact {{
      margin-top: 4px;
      text-align: center;
      font-size: 10.5pt;
    }}
    .section {{
      margin-top: 11px;
    }}
    .section-title {{
      font-size: 11.5pt;
      font-weight: bold;
      text-transform: uppercase;
      border-bottom: 1px solid #111;
      padding-bottom: 2px;
      margin-bottom: 6px;
      letter-spacing: 0.02em;
    }}
    .entry {{
      margin-bottom: 5px;
    }}
    .entry-head {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
    }}
    .role {{
      font-weight: bold;
      font-size: 10.7pt;
    }}
    .meta {{
      text-align: right;
      font-size: 10pt;
      white-space: nowrap;
    }}
    .description {{
      margin-top: 1px;
    }}
    .cert-item {{
      margin-bottom: 2px;
    }}
  </style>
</head>
<body>
  <div class="page">
    <h1>{html.escape(RESUME_DATA['name'])}</h1>
    <div class="contact">{html.escape(RESUME_DATA['email'])} | {html.escape(RESUME_DATA['portfolio'])}</div>

    <section class="section">
      <div class="section-title">Education</div>
      {education_html}
    </section>

    <section class="section">
      <div class="section-title">Work History</div>
      {experience_html}
    </section>

    <section class="section">
      <div class="section-title">Certifications</div>
      {certifications_html}
    </section>
  </div>
</body>
</html>
"""


def render_cover_html(title: str, body_paragraphs: list[str]) -> str:
    paragraphs = "".join(paragraph(text) for text in body_paragraphs)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    @page {{
      size: Letter;
      margin: 0.8in;
    }}
    body {{
      font-family: "Times New Roman", Times, serif;
      color: #111;
      margin: 0;
      font-size: 12pt;
      line-height: 1.35;
    }}
    .page {{
      max-width: 6.9in;
      margin: 0 auto;
    }}
    .header {{
      margin-bottom: 22px;
    }}
    .name {{
      font-size: 16pt;
      font-weight: bold;
      margin-bottom: 3px;
    }}
    .contact {{
      font-size: 11.5pt;
    }}
    p {{
      margin: 0 0 12px 0;
    }}
    .closing {{
      margin-top: 22px;
    }}
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <div class="name">Andre Foreman</div>
      <div class="contact">foreandr@gmail.com | foreandr.github.io</div>
    </div>
    {paragraphs}
    <p class="closing">Sincerely,<br>Andre Foreman</p>
  </div>
</body>
</html>
"""


def write_html_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def export_pdf(html_path: Path, pdf_path: Path) -> None:
    file_url = html_path.resolve().as_uri()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(file_url, wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            format="Letter",
            print_background=True,
            margin={
                "top": "0in",
                "right": "0in",
                "bottom": "0in",
                "left": "0in",
            },
        )
        browser.close()


def write_resume_text_snapshot() -> None:
    lines = [
        RESUME_DATA["name"],
        RESUME_DATA["email"],
        RESUME_DATA["portfolio"],
        "",
        "Education",
        "--------------",
        "",
    ]
    for item in RESUME_DATA["education"]:
        lines.extend([item["institution"], item["detail"], ""])

    lines.extend(["Work History", "--------------", ""])
    for item in RESUME_DATA["experience"]:
        lines.extend(
            [
                item["role"],
                f"{item['company']}, {item['period']}",
                item["description"],
                "",
            ]
        )

    lines.extend(["Certifications", "--------------", ""])
    lines.extend(RESUME_DATA["certifications"])
    lines.append("")

    (BASE_DIR / "resume.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    TEMP_DIR.mkdir(exist_ok=True)

    resume_html = TEMP_DIR / "andre_foreman_resume.html"
    tech_cover_html = TEMP_DIR / "andre_foreman_cover_letter_tech.html"
    general_cover_html = TEMP_DIR / "andre_foreman_cover_letter_general.html"

    write_html_file(resume_html, render_resume_html())
    write_html_file(
        tech_cover_html,
        render_cover_html("Andre Foreman Cover Letter", TECH_COVER_BODY),
    )
    write_html_file(
        general_cover_html,
        render_cover_html("Andre Foreman General Cover Letter", GENERAL_COVER_BODY),
    )

    write_resume_text_snapshot()

    export_pdf(resume_html, RESUME_PDF)
    export_pdf(tech_cover_html, TECH_COVER_PDF)
    export_pdf(general_cover_html, GENERAL_COVER_PDF)


if __name__ == "__main__":
    main()
