BASE = r"C:\Users\forea\Documents\DataMarketplace\files"

RESUME = f"{BASE}\\Andre Foreman Resume.pdf"

COVER_LETTERS = {
    "swe":     f"{BASE}\\Andre Foreman Cover Letter.pdf",
    "general": f"{BASE}\\Andre_Foreman_Cover_Letter.pdf",
}

BODIES = {
    "swe": lambda title, board: f"""Hello,

My name is Andre Foreman. I found your posting for {title} and wanted to reach out. Please find my resume and cover letter attached.

I am a software engineer with a background in mathematics and the humanities.

If you would like a deeper look at what I am capable of, my portfolio at foreandr.github.io highlights my software experience with many projects you can browse.

To confirm: I am a Canadian citizen, fully authorized to work in Canada, and I have relevant experience for this position.

Best regards,
Andre Foreman
519-636-3173
foreandr@gmail.com""",

    "general": lambda title, board: f"""Hello,

My name is Andre Foreman. I found your posting for {title}  and wanted to reach out. Please find my resume and cover letter attached.

I would welcome the opportunity to work with your team. My background is in software engineering, mathematics, and the humanities, and I take quality and reliability seriously. I was also a national team athlete.

If you would like a deeper look at what I am capable of, my portfolio is available at foreandr.github.io with many projects you can browse.

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
        "subject":     f"Application for {job_title.title()} role — Andre Foreman",
        "body":        BODIES[cover_letter_type](job_title, job_board),
        "attachments": [RESUME, COVER_LETTERS[cover_letter_type]],
    }

'''
how to use :

from email_generator import generate_application

app = generate_application(job_title="Data Analyst", job_board="Indeed", cover_letter_type="swe")
# app["subject"], app["body"], app["attachments"]

'''
