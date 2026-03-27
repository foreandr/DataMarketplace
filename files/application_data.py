BASE = r"C:\Users\forea\Documents\DataMarketplace\files"

RESUME = f"{BASE}\\Andre Foreman Resume.pdf"

COVER_LETTERS = {
    "swe":     f"{BASE}\\Andre_Foreman_Cover_Letter_SWE.pdf",
    "general": f"{BASE}\\Andre_Foreman_Cover_Letter_General.pdf",
}

BODIES = {
    "swe": lambda title, board: f"""Hi Hiring Team,

I found your posting for {title} on {board} and wanted to reach out. Please find my resume and cover letter attached.

I am a software engineer with a background in mathematics, full stack development, and data systems. My project portfolio is available at foreandr.github.io. I would welcome the opportunity to speak further about the role.

To confirm: I am a Canadian citizen, fully authorized to work in Canada, and I have relevant experience for this position.

Best regards,
Andre Foreman
519-636-3173
foreandr@gmail.com""",

    "general": lambda title, board: f"""Hi Hiring Team,

I came across your posting for {title} on {board} and am writing to express my interest. Please find my resume and cover letter attached.

I bring a background in software development, mathematics, and high performance sport. I am a hard worker, a fast learner, and I take quality seriously. I would welcome the chance to speak further about how I can contribute.

To confirm: I am a Canadian citizen, fully authorized to work in Canada, and I have relevant experience for this position.

Best regards,
Andre Foreman
519-636-3173
foreandr@gmail.com""",
}


def generate_application(job_title, job_board, cover_letter_type="swe"):
    """
    Returns a dict with everything needed to send an application email.

    Args:
        job_title (str):          e.g. "Data Analyst"
        job_board (str):          e.g. "Indeed"
        cover_letter_type (str):  "swe" or "general"

    Returns:
        dict with keys: subject, body, attachments
    """
    return {
        "subject":     f"Application for {job_title} — Andre Foreman",
        "body":        BODIES[cover_letter_type](job_title, job_board),
        "attachments": [RESUME, COVER_LETTERS[cover_letter_type]],
    }

'''
how to use :

from email_generator import generate_application

app = generate_application(job_title="Data Analyst", job_board="Indeed", cover_letter_type="swe")
# app["subject"], app["body"], app["attachments"]

'''