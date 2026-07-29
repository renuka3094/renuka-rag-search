"""
Generates a 20-document fictional 'Contoso Corp' HR/benefits/procedures
corpus across four formats (md, html, docx, pdf) for Use Case 1.

Run once: python generate_corpus.py
Outputs into corpus/{markdown,html,docx,pdf}/
"""
import textwrap
from pathlib import Path

from docx import Document as DocxDocument
from docx.shared import Pt
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).parent / "generated"
(ROOT / "markdown").mkdir(parents=True, exist_ok=True)
(ROOT / "html").mkdir(parents=True, exist_ok=True)
(ROOT / "docx").mkdir(parents=True, exist_ok=True)
(ROOT / "pdf").mkdir(parents=True, exist_ok=True)

# Each doc: (title, [(heading, paragraphs[])])
DOCS_MARKDOWN = [
    ("Employee Handbook Introduction", [
        ("Welcome to Contoso Corp", [
            "This handbook describes the policies, benefits, and procedures that apply to all Contoso Corp employees, effective January 1, 2026.",
            "It supersedes all prior versions. Where a specific team's policy differs from this handbook, the team policy governs only if it has been approved in writing by HR.",
        ]),
        ("Who This Applies To", [
            "This handbook applies to all full-time and part-time employees of Contoso Corp in the United States. Contractors and interns should refer to their engagement agreement for applicable terms.",
        ]),
        ("How to Use This Handbook", [
            "Each section is self-contained. If you cannot find an answer here, contact HR at hr@contoso-corp.example or ask the Knowledge Assistant.",
        ]),
    ]),
    ("Paid Time Off Policy", [
        ("Accrual", [
            "Full-time employees accrue 1.5 days of paid time off (PTO) per month, for a total of 18 days per year.",
            "Part-time employees accrue PTO on a pro-rated basis according to scheduled hours.",
            "PTO accrual begins on an employee's first day of employment; there is no waiting period.",
        ]),
        ("Rollover", [
            "Employees may roll over up to 5 unused PTO days into the following calendar year. Any balance above 5 days is forfeited on December 31st unless local law requires otherwise.",
        ]),
        ("Requesting Time Off", [
            "Submit PTO requests through the Contoso HR portal at least 5 business days in advance for planned absences. Same-day requests for illness do not require advance notice, but should be reported to your manager before your shift start time.",
        ]),
        ("Unused PTO at Termination", [
            "Upon voluntary or involuntary termination, Contoso Corp pays out accrued and unused PTO at the employee's final base rate of pay, in accordance with state law.",
        ]),
    ]),
    ("Remote Work Policy", [
        ("Eligibility", [
            "Employees whose role has been designated 'remote-eligible' by their department head may work remotely up to 5 days per week. Roles requiring on-site equipment or in-person client contact are not remote-eligible.",
        ]),
        ("Equipment", [
            "Contoso Corp provides a laptop, monitor, and a one-time $300 home office stipend for remote-eligible employees. Requests for additional equipment go through the IT Service Desk.",
        ]),
        ("Core Hours", [
            "Remote employees must be reachable during core hours of 10:00 AM to 3:00 PM in their local time zone, Monday through Friday, excluding company holidays.",
        ]),
        ("Working From Outside the Country", [
            "Working from outside the United States for more than 20 consecutive business days requires prior approval from HR and Legal due to tax and employment law implications.",
        ]),
    ]),
    ("Code of Conduct", [
        ("Professional Behavior", [
            "Contoso Corp employees are expected to treat colleagues, clients, and vendors with respect and professionalism at all times, both in person and in digital communication.",
        ]),
        ("Conflicts of Interest", [
            "Employees must disclose any financial or personal relationship that could reasonably be seen as influencing a business decision, using the Conflict of Interest Disclosure Form.",
        ]),
        ("Gifts and Entertainment", [
            "Employees may accept gifts from vendors or clients valued under $75. Gifts above this threshold must be declined or reported to your manager and Compliance.",
        ]),
        ("Reporting Concerns", [
            "Concerns about conduct violations can be reported confidentially through the Contoso Ethics Hotline at 1-800-555-0142 or ethics@contoso-corp.example. Retaliation against a good-faith reporter is strictly prohibited.",
        ]),
    ]),
    ("Parental Leave Policy", [
        ("Eligibility", [
            "All full-time employees are eligible for paid parental leave after 90 days of continuous employment, regardless of gender or the method of family growth (birth, adoption, or surrogacy).",
        ]),
        ("Duration and Pay", [
            "Birthing parents receive 16 weeks of fully paid leave. Non-birthing parents and adoptive parents receive 10 weeks of fully paid leave.",
            "Leave must be taken within 12 months of the birth or placement date and may be split into two blocks with manager approval.",
        ]),
        ("Benefits Continuation", [
            "Health, dental, and vision benefits continue uninterrupted during parental leave at the employee's normal contribution rate.",
        ]),
    ]),
]

DOCS_HTML = [
    ("Expense Reimbursement Policy", [
        ("Submitting Expenses", [
            "Submit expense reports through the Contoso Expense portal within 30 days of the expense date. Reports submitted after 60 days will not be reimbursed except in extenuating circumstances approved by Finance.",
        ]),
        ("Receipts", [
            "Original itemized receipts are required for any single expense over $25. Credit card statements alone are not sufficient documentation.",
        ]),
        ("Meal Limits", [
            "Meal reimbursement is capped at $20 for breakfast, $25 for lunch, and $45 for dinner per person, including tax and tip, while traveling on approved company business.",
        ]),
        ("Non-Reimbursable Items", [
            "Contoso Corp does not reimburse alcohol for solo meals, traffic or parking fines, personal entertainment, or spa services, regardless of business context.",
        ]),
    ]),
    ("Travel Policy", [
        ("Booking Travel", [
            "All flights and hotels for business travel must be booked through the Contoso Travel Portal (powered by Concur) to ensure duty-of-care coverage.",
        ]),
        ("Airfare Class", [
            "Economy class is standard for flights under 6 hours. Premium economy is permitted for flights over 6 hours. Business class requires VP-level pre-approval.",
        ]),
        ("Hotel Limits", [
            "Standard nightly hotel rate limits are $220 in major metro areas (New York, San Francisco, Chicago) and $160 elsewhere in the continental United States.",
        ]),
        ("Ground Transportation", [
            "Rideshare and taxi are preferred over rental cars for trips under 3 days. Rental cars require a stated business justification in the expense report.",
        ]),
    ]),
    ("Health Insurance Benefits Guide", [
        ("Plan Options", [
            "Contoso Corp offers three medical plan tiers: the PPO Plus plan, the PPO Standard plan, and the High-Deductible Health Plan (HDHP) with a company-funded Health Savings Account.",
        ]),
        ("Company Contribution", [
            "Contoso Corp covers 80% of the employee-only premium and 60% of the premium for dependents, across all three plan tiers.",
        ]),
        ("Enrollment Windows", [
            "New hires have 30 days from their start date to enroll. Open enrollment for all employees runs each year from November 1 through November 15, with changes effective January 1.",
        ]),
        ("Qualifying Life Events", [
            "Marriage, divorce, birth or adoption of a child, and loss of other coverage all qualify for a special enrollment period outside the standard windows, within 30 days of the event.",
        ]),
    ]),
    ("Dental and Vision Benefits", [
        ("Dental Coverage", [
            "The Contoso dental plan covers preventive care (cleanings, exams, X-rays) at 100%, basic procedures (fillings) at 80%, and major procedures (crowns, root canals) at 50%, after a $50 annual deductible.",
        ]),
        ("Vision Coverage", [
            "Vision coverage includes one eye exam per year at 100%, and a $150 allowance toward frames or contact lenses every 12 months.",
        ]),
        ("Orthodontia", [
            "Orthodontic treatment for dependents under 19 is covered at 50%, up to a lifetime maximum of $2,000 per covered individual.",
        ]),
    ]),
    ("401(k) Retirement Plan Summary", [
        ("Company Match", [
            "Contoso Corp matches 100% of employee 401(k) contributions up to the first 4% of eligible pay, and 50% of the next 2%, for a maximum company match of 5%.",
        ]),
        ("Vesting Schedule", [
            "Employee contributions are always 100% vested. Company matching contributions vest over 3 years: 0% in year one, 50% in year two, and 100% after three years of service.",
        ]),
        ("Eligibility and Enrollment", [
            "Employees become eligible to enroll in the 401(k) plan on the first day of the month following 30 days of employment, and are auto-enrolled at a 3% contribution rate unless they opt out.",
        ]),
    ]),
]

DOCS_DOCX = [
    ("Employee Referral Program", [
        ("Referral Bonus Amounts", [
            "Employees who refer a successful candidate for a standard role receive a $1,500 referral bonus. Referrals for hard-to-fill engineering or leadership roles earn a $3,000 bonus.",
        ]),
        ("Payout Timing", [
            "Referral bonuses are paid in two installments: 50% after the referred employee's 90th day, and the remaining 50% after their 6-month anniversary, provided both employees remain active.",
        ]),
        ("Eligibility", [
            "All active full-time employees are eligible to refer candidates, except employees on the Talent Acquisition team and hiring managers referring into their own open requisitions.",
        ]),
    ]),
    ("Performance Review Process", [
        ("Review Cadence", [
            "Contoso Corp conducts formal performance reviews twice per year: a mid-year check-in in June and an annual review in December that informs compensation decisions.",
        ]),
        ("Rating Scale", [
            "Employees are rated on a 4-point scale: Exceeds Expectations, Meets Expectations, Partially Meets Expectations, and Does Not Meet Expectations.",
        ]),
        ("Calibration", [
            "Manager ratings go through a cross-team calibration session before being finalized, to ensure consistent application of the rating scale across departments.",
        ]),
    ]),
    ("Anti-Harassment and Non-Discrimination Policy", [
        ("Policy Statement", [
            "Contoso Corp prohibits discrimination or harassment based on race, color, religion, sex, national origin, age, disability, sexual orientation, gender identity, or any other status protected by applicable law.",
        ]),
        ("Reporting Process", [
            "Employees who experience or witness harassment should report it to their manager, HR Business Partner, or the confidential Ethics Hotline immediately. Reports are investigated within 10 business days.",
        ]),
        ("Non-Retaliation", [
            "Contoso Corp strictly prohibits retaliation against anyone who reports a concern in good faith or participates in an investigation.",
        ]),
    ]),
    ("IT Acceptable Use Policy", [
        ("Company Devices", [
            "Company-issued laptops and phones are for business use, with incidental personal use permitted as long as it does not interfere with work or violate other policies.",
        ]),
        ("Prohibited Activity", [
            "Employees may not install unauthorized software, disable endpoint security tools, or use company systems to access illegal content.",
        ]),
        ("Password Requirements", [
            "All Contoso accounts require multi-factor authentication and a password of at least 14 characters, rotated every 180 days.",
        ]),
    ]),
    ("Data Security and Confidentiality Policy", [
        ("Data Classification", [
            "Contoso Corp classifies data into three tiers: Public, Internal, and Confidential. Customer PII and financial records are always classified Confidential.",
        ]),
        ("Handling Confidential Data", [
            "Confidential data may not be stored on personal devices, personal cloud storage, or transmitted over unencrypted channels.",
        ]),
        ("Incident Reporting", [
            "Suspected data breaches must be reported to security@contoso-corp.example within 1 hour of discovery, per the Incident Response Runbook.",
        ]),
    ]),
]

DOCS_PDF = [
    ("Onboarding Checklist for New Hires", [
        ("Before Day One", [
            "IT provisions your laptop and accounts 3 business days before your start date. HR sends your offer packet and I-9 form for e-signature.",
        ]),
        ("Week One", [
            "New hires complete Contoso 101 orientation, benefits enrollment, and meet with their manager to set 30-60-90 day goals.",
        ]),
        ("First 90 Days", [
            "Managers conduct check-ins at 30, 60, and 90 days. The first formal performance conversation happens at the 90-day mark.",
        ]),
    ]),
    ("Offboarding Procedure", [
        ("Final Pay", [
            "Departing employees receive their final paycheck, including any unused PTO payout, on the next regularly scheduled payroll date after their last day, or sooner where required by state law.",
        ]),
        ("Equipment Return", [
            "All company equipment (laptop, monitor, badge) must be returned within 5 business days of the last day of employment via prepaid shipping label provided by IT.",
        ]),
        ("Benefits After Departure", [
            "Health benefits end on the last day of the month of departure. COBRA continuation coverage information is mailed within 14 days.",
        ]),
    ]),
    ("Workplace Safety Guidelines", [
        ("Office Safety", [
            "All Contoso offices maintain marked emergency exits, fire extinguishers inspected quarterly, and a designated floor warden for each office level.",
        ]),
        ("Reporting Incidents", [
            "Any workplace injury, however minor, must be reported to Facilities and HR within 24 hours using the Incident Report Form.",
        ]),
        ("Ergonomics", [
            "Employees may request a free ergonomic assessment of their home or office workstation through the Workplace Safety team.",
        ]),
    ]),
    ("Tuition Reimbursement Program", [
        ("Eligibility", [
            "Full-time employees with at least 6 months of tenure are eligible for tuition reimbursement for courses related to their current role or a reasonable career path at Contoso Corp.",
        ]),
        ("Reimbursement Amount", [
            "Contoso Corp reimburses up to $5,250 per calendar year for tuition, required textbooks, and course fees, upon proof of a passing grade (C or better, or Pass in pass/fail courses).",
        ]),
        ("Approval Process", [
            "Submit the Tuition Reimbursement Pre-Approval Form to your manager and HR before the course start date; reimbursement requests without prior approval will be denied.",
        ]),
    ]),
    ("Employee Assistance Program Guide", [
        ("What the EAP Covers", [
            "The Contoso Employee Assistance Program (EAP) provides up to 6 free confidential counseling sessions per issue, per year, for employees and their household members.",
        ]),
        ("Additional Services", [
            "The EAP also offers free legal consultations, financial planning sessions, and childcare/eldercare referral services.",
        ]),
        ("How to Access", [
            "Call the EAP support line at 1-800-555-0199, available 24/7, or visit the EAP portal linked from the Contoso benefits page. All contact is confidential and not shared with Contoso Corp.",
        ]),
    ]),
]


def write_markdown(title, sections):
    lines = [f"# {title}\n"]
    for heading, paras in sections:
        lines.append(f"## {heading}\n")
        for p in paras:
            lines.append(p + "\n")
    path = ROOT / "markdown" / f"{_slug(title)}.md"
    path.write_text("\n".join(lines), encoding="utf-8")


def write_html(title, sections):
    body = [f"<h1>{title}</h1>"]
    for heading, paras in sections:
        body.append(f"<h2>{heading}</h2>")
        for p in paras:
            body.append(f"<p>{p}</p>")
    html = f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title></head><body>{''.join(body)}</body></html>"
    path = ROOT / "html" / f"{_slug(title)}.html"
    path.write_text(html, encoding="utf-8")


def write_docx(title, sections):
    doc = DocxDocument()
    doc.add_heading(title, level=1)
    for heading, paras in sections:
        doc.add_heading(heading, level=2)
        for p in paras:
            run = doc.add_paragraph(p)
            run.style.font.size = Pt(11)
    path = ROOT / "docx" / f"{_slug(title)}.docx"
    doc.save(str(path))


def write_pdf(title, sections):
    path = ROOT / "pdf" / f"{_slug(title)}.pdf"
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=LETTER)
    flow = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for heading, paras in sections:
        flow.append(Paragraph(heading, styles["Heading2"]))
        flow.append(Spacer(1, 6))
        for p in paras:
            flow.append(Paragraph(p, styles["BodyText"]))
            flow.append(Spacer(1, 6))
        flow.append(Spacer(1, 10))
    doc.build(flow)


def _slug(title: str) -> str:
    return title.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "-")


if __name__ == "__main__":
    for title, sections in DOCS_MARKDOWN:
        write_markdown(title, sections)
    for title, sections in DOCS_HTML:
        write_html(title, sections)
    for title, sections in DOCS_DOCX:
        write_docx(title, sections)
    for title, sections in DOCS_PDF:
        write_pdf(title, sections)

    total = len(DOCS_MARKDOWN) + len(DOCS_HTML) + len(DOCS_DOCX) + len(DOCS_PDF)
    print(f"Generated {total} documents: "
          f"{len(DOCS_MARKDOWN)} markdown, {len(DOCS_HTML)} html, "
          f"{len(DOCS_DOCX)} docx, {len(DOCS_PDF)} pdf")
