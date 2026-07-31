"""
Generates a 20-document fictional 'Contoso Corp' HR/benefits/procedures
corpus across four formats (md, html, docx, pdf) for Use Case 1.

Run once: python generate_corpus.py
Outputs into corpus/generated/{markdown,html,docx,pdf}/
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
            "This handbook describes the policies, benefits, and procedures that apply to all Contoso Corp employees, effective January 1, 2026. It is maintained by the People Operations team and reviewed annually, or sooner if a material change in law or company practice requires it.",
            "It supersedes all prior versions, including any handbook or policy summary distributed before January 1, 2026. Where a specific team's policy differs from this handbook, the team policy governs only if it has been approved in writing by HR and filed with the central Policy Register.",
            "Nothing in this handbook constitutes an employment contract or a guarantee of continued employment. Contoso Corp is an at-will employer in every jurisdiction where at-will employment is legally permitted.",
        ]),
        ("Who This Applies To", [
            "This handbook applies to all full-time and part-time employees of Contoso Corp in the United States, including employees on approved leave. Contractors, consultants, and interns should refer to their engagement agreement or internship agreement for applicable terms, since many handbook sections (PTO, 401(k), health benefits) do not extend to non-employee workers.",
            "Employees working under a collective bargaining agreement should refer to that agreement first; where the agreement is silent, this handbook applies as a supplement, not a replacement.",
        ]),
        ("How to Use This Handbook", [
            "Each section is self-contained and cross-references related policies where relevant (for example, the Paid Time Off Policy references the Parental Leave Policy for leave that extends beyond standard PTO). If you cannot find an answer here, contact HR at hr@contoso-corp.example or ask the Knowledge Assistant, which is grounded in this same document set.",
            "Policy updates are announced company-wide by email at least 2 weeks before taking effect, except where a change is required immediately by law.",
        ]),
    ]),
    ("Paid Time Off Policy", [
        ("Accrual", [
            "Full-time employees accrue 1.5 days of paid time off (PTO) per month, for a total of 18 days per year. Accrual is calculated on the last day of each calendar month and posted to the employee's PTO balance within 3 business days.",
            "Part-time employees accrue PTO on a pro-rated basis according to scheduled hours: an employee scheduled for 20 hours per week (50% of full-time) accrues 0.75 days per month.",
            "PTO accrual begins on an employee's first day of employment; there is no waiting period. However, newly accrued PTO cannot be used until an employee has completed 30 days of employment, except in the case of a documented medical emergency.",
        ]),
        ("Rollover", [
            "Employees may roll over up to 5 unused PTO days into the following calendar year. Any balance above 5 days is forfeited on December 31st unless local law requires otherwise (for example, California and several other states prohibit use-it-or-lose-it PTO policies, and employees in those states carry over their full unused balance).",
            "Rolled-over days must be used by March 31st of the new year or they are forfeited; the standard 5-day cap does not reset until that date.",
        ]),
        ("Requesting Time Off", [
            "Submit PTO requests through the Contoso HR portal at least 5 business days in advance for planned absences. Same-day requests for illness do not require advance notice, but should be reported to your manager before your shift start time, or as soon as reasonably possible.",
            "Requests during Contoso Corp's peak season (the last two weeks of December) require manager approval at least 3 weeks in advance and are granted on a first-requested, first-approved basis.",
            "Managers must respond to a PTO request within 2 business days; a request that is neither approved nor denied within that window is automatically approved.",
        ]),
        ("Unused PTO at Termination", [
            "Upon voluntary or involuntary termination, Contoso Corp pays out accrued and unused PTO at the employee's final base rate of pay, in accordance with state law. This payout is included in the employee's final paycheck.",
            "Employees terminated for cause forfeit any rolled-over PTO from a prior year but still receive payout for PTO accrued in the current calendar year, where required by state law.",
        ]),
    ]),
    ("Remote Work Policy", [
        ("Eligibility", [
            "Employees whose role has been designated 'remote-eligible' by their department head may work remotely up to 5 days per week. Roles requiring on-site equipment, in-person client contact, or physical presence for security/compliance reasons (e.g., handling regulated hardware) are not remote-eligible, regardless of the employee's preference.",
            "Remote eligibility is reviewed at each performance cycle and can be revoked if an employee's role responsibilities change to require more on-site presence.",
        ]),
        ("Equipment", [
            "Contoso Corp provides a laptop, monitor, and a one-time $300 home office stipend for remote-eligible employees, disbursed through payroll within the first full pay cycle after a remote work agreement is signed. Requests for additional equipment (a second monitor, ergonomic chair, keyboard) go through the IT Service Desk and are evaluated case by case.",
            "Employees are responsible for maintaining a secure and adequately private workspace; company equipment used at home remains company property and must be returned upon separation, per the Offboarding Procedure.",
        ]),
        ("Core Hours", [
            "Remote employees must be reachable during core hours of 10:00 AM to 3:00 PM in their local time zone, Monday through Friday, excluding company holidays. Outside of core hours, employees may structure their schedule flexibly as long as they meet their weekly hour commitment and attend any meetings their manager designates as mandatory.",
            "Employees working across more than one time zone from their team (e.g., a distributed team spanning Eastern and Pacific time) should agree on a shared core-hours overlap with their manager in writing.",
        ]),
        ("Working From Outside the Country", [
            "Working from outside the United States for more than 20 consecutive business days requires prior approval from HR and Legal due to tax and employment law implications. Requests must be submitted at least 30 days before the intended travel date using the International Remote Work Request Form.",
            "Approval is not guaranteed and depends on whether Contoso Corp has a registered business presence or applicable tax treaty in the destination country; some countries are excluded entirely due to sanctions or data residency restrictions.",
        ]),
    ]),
    ("Code of Conduct", [
        ("Professional Behavior", [
            "Contoso Corp employees are expected to treat colleagues, clients, and vendors with respect and professionalism at all times, both in person and in digital communication, including internal chat tools, email, and video calls.",
            "Disagreements about work product or approach are expected and healthy; personal attacks, public humiliation, or retaliatory behavior in response to disagreement are not tolerated and are grounds for disciplinary action up to termination.",
        ]),
        ("Conflicts of Interest", [
            "Employees must disclose any financial or personal relationship that could reasonably be seen as influencing a business decision, using the Conflict of Interest Disclosure Form, filed with Compliance within 10 business days of the relationship arising or being recognized.",
            "Common examples requiring disclosure: a close family member employed by a vendor Contoso Corp is evaluating, a personal financial stake in a competitor, or a side business that could be seen as competing with Contoso Corp's services.",
        ]),
        ("Gifts and Entertainment", [
            "Employees may accept gifts from vendors or clients valued under $75. Gifts above this threshold must be declined or reported to your manager and Compliance within 5 business days of receipt; reported gifts over $75 are typically redirected to a company-wide raffle or charitable donation rather than kept personally.",
            "Cash or cash-equivalent gifts (gift cards, cryptocurrency) of any amount must always be declined, with no exception for value.",
        ]),
        ("Reporting Concerns", [
            "Concerns about conduct violations can be reported confidentially through the Contoso Ethics Hotline at 1-800-555-0142 or ethics@contoso-corp.example. Reports may be made anonymously, and the hotline is operated by an independent third party, not by Contoso Corp's own HR team.",
            "Retaliation against a good-faith reporter is strictly prohibited and is itself grounds for termination, regardless of the reporter's role or seniority relative to the person retaliating.",
        ]),
    ]),
    ("Parental Leave Policy", [
        ("Eligibility", [
            "All full-time employees are eligible for paid parental leave after 90 days of continuous employment, regardless of gender or the method of family growth (birth, adoption, or surrogacy). Part-time employees working at least 20 hours per week are eligible for a pro-rated version of the same benefit.",
        ]),
        ("Duration and Pay", [
            "Birthing parents receive 16 weeks of fully paid leave, which can begin up to 2 weeks before the expected due date if medically necessary. Non-birthing parents and adoptive parents receive 10 weeks of fully paid leave.",
            "Leave must be taken within 12 months of the birth or placement date and may be split into two blocks with manager approval — for example, 6 weeks immediately after birth and the remaining 4 weeks taken later in the first year.",
            "Parental leave runs concurrently with any leave required under the Family and Medical Leave Act (FMLA) where the employee is FMLA-eligible; it does not stack on top of FMLA leave to extend total job-protected time beyond what FMLA and this policy separately provide.",
        ]),
        ("Benefits Continuation", [
            "Health, dental, and vision benefits continue uninterrupted during parental leave at the employee's normal contribution rate; Contoso Corp continues to pay its employer share as if the employee were actively working.",
            "401(k) contributions pause during unpaid portions of leave (if any) but resume automatically upon return to active payroll status, with no re-enrollment required.",
        ]),
    ]),
]

DOCS_HTML = [
    ("Expense Reimbursement Policy", [
        ("Submitting Expenses", [
            "Submit expense reports through the Contoso Expense portal within 30 days of the expense date. Reports submitted after 60 days will not be reimbursed except in extenuating circumstances approved in writing by Finance leadership.",
            "Each report requires a business justification, the associated project or client code, and an itemized receipt for any line item over the receipt threshold described below.",
        ]),
        ("Receipts", [
            "Original itemized receipts are required for any single expense over $25. Credit card statements alone are not sufficient documentation, since they do not itemize what was purchased.",
            "Digital receipts (photographed or forwarded email receipts) are accepted as long as the total amount, vendor name, and date are legible.",
        ]),
        ("Meal Limits", [
            "Meal reimbursement is capped at $20 for breakfast, $25 for lunch, and $45 for dinner per person, including tax and tip, while traveling on approved company business. Alcohol is not reimbursable as part of a solo meal expense.",
            "Meals with clients or prospects may be submitted under Business Entertainment rather than the standard meal caps, but require listing all attendees and the business purpose, and require manager pre-approval if the total exceeds $200 per person.",
        ]),
        ("Non-Reimbursable Items", [
            "Contoso Corp does not reimburse alcohol for solo meals, traffic or parking fines, personal entertainment, or spa services, regardless of business context.",
            "Personal upgrades (seat upgrades not required for medical reasons, hotel room upgrades beyond standard) are also non-reimbursable and must be paid for out of pocket, with only the standard-rate portion reimbursed if a receipt shows a blended charge.",
        ]),
    ]),
    ("Travel Policy", [
        ("Booking Travel", [
            "All flights and hotels for business travel must be booked through the Contoso Travel Portal (powered by Concur) to ensure duty-of-care coverage, meaning Contoso Corp always knows where traveling employees are in the event of an emergency.",
            "Booking outside the portal is permitted only when the portal genuinely cannot fulfill the itinerary (e.g., a small regional carrier not listed), and requires notifying the Travel Desk within 24 hours of booking so the trip is still logged for duty-of-care purposes.",
        ]),
        ("Airfare Class", [
            "Economy class is standard for flights under 6 hours. Premium economy is permitted for flights over 6 hours. Business class requires VP-level pre-approval and is only available for flights over 8 hours or for employees with a documented medical accommodation.",
        ]),
        ("Hotel Limits", [
            "Standard nightly hotel rate limits are $220 in major metro areas (New York, San Francisco, Chicago) and $160 elsewhere in the continental United States. Rates above these limits require manager approval in advance, noting the reason (e.g., conference-mandated hotel, no lower-cost option within a reasonable distance).",
        ]),
        ("Ground Transportation", [
            "Rideshare and taxi are preferred over rental cars for trips under 3 days. Rental cars require a stated business justification in the expense report and should be booked at the economy or compact tier unless the trip involves transporting equipment or more than 2 colleagues.",
        ]),
    ]),
    ("Health Insurance Benefits Guide", [
        ("Plan Options", [
            "Contoso Corp offers three medical plan tiers: the PPO Plus plan, the PPO Standard plan, and the High-Deductible Health Plan (HDHP) with a company-funded Health Savings Account. All three plans use the same nationwide provider network.",
            "The PPO Plus plan has the lowest deductible and highest monthly premium; the HDHP has the highest deductible but the lowest premium, offset partly by Contoso Corp's annual HSA contribution of $750 for employee-only coverage or $1,500 for family coverage.",
        ]),
        ("Company Contribution", [
            "Contoso Corp covers 80% of the employee-only premium and 60% of the premium for dependents, across all three plan tiers. The remaining premium is deducted pre-tax from each paycheck in equal installments across the plan year.",
        ]),
        ("Enrollment Windows", [
            "New hires have 30 days from their start date to enroll; coverage begins on the first day of the month following enrollment. Open enrollment for all employees runs each year from November 1 through November 15, with changes effective January 1.",
        ]),
        ("Qualifying Life Events", [
            "Marriage, divorce, birth or adoption of a child, and loss of other coverage all qualify for a special enrollment period outside the standard windows, within 30 days of the event. Supporting documentation (marriage certificate, birth certificate, loss-of-coverage letter) must be submitted with the enrollment change.",
        ]),
    ]),
    ("Dental and Vision Benefits", [
        ("Dental Coverage", [
            "The Contoso dental plan covers preventive care (cleanings, exams, X-rays) at 100%, basic procedures (fillings) at 80%, and major procedures (crowns, root canals) at 50%, after a $50 annual deductible per covered individual.",
            "The plan has an annual maximum benefit of $2,000 per covered individual; costs above that maximum in a plan year are the employee's responsibility.",
        ]),
        ("Vision Coverage", [
            "Vision coverage includes one eye exam per year at 100%, and a $150 allowance toward frames or contact lenses every 12 months. Designer frame upgrades beyond the allowance are available at a negotiated discount through the plan's partner retailers.",
        ]),
        ("Orthodontia", [
            "Orthodontic treatment for dependents under 19 is covered at 50%, up to a lifetime maximum of $2,000 per covered individual. Adult orthodontia is not covered under the standard plan.",
        ]),
    ]),
    ("401(k) Retirement Plan Summary", [
        ("Company Match", [
            "Contoso Corp matches 100% of employee 401(k) contributions up to the first 4% of eligible pay, and 50% of the next 2%, for a maximum company match of 5% when an employee contributes at least 6% of eligible pay.",
            "Matching contributions are calculated and deposited each pay period, not as a single annual true-up, so employees who front-load contributions early in the year should confirm they are not missing match dollars later in the year — Contoso Corp does perform a true-up calculation in January of the following year to correct any shortfall.",
        ]),
        ("Vesting Schedule", [
            "Employee contributions are always 100% vested. Company matching contributions vest over 3 years: 0% in year one, 50% in year two, and 100% after three years of service. Unvested matching funds are forfeited if an employee leaves before full vesting.",
        ]),
        ("Eligibility and Enrollment", [
            "Employees become eligible to enroll in the 401(k) plan on the first day of the month following 30 days of employment, and are auto-enrolled at a 3% contribution rate unless they opt out or select a different rate within their first 45 days.",
        ]),
    ]),
]

DOCS_DOCX = [
    ("Employee Referral Program", [
        ("Referral Bonus Amounts", [
            "Employees who refer a successful candidate for a standard role receive a $1,500 referral bonus. Referrals for hard-to-fill engineering or leadership roles earn a $3,000 bonus, as designated on the current Hard-to-Fill Roles list maintained by Talent Acquisition.",
        ]),
        ("Payout Timing", [
            "Referral bonuses are paid in two installments: 50% after the referred employee's 90th day, and the remaining 50% after their 6-month anniversary, provided both the referring employee and the referred employee remain active Contoso Corp employees at each payout date.",
            "If the referring employee leaves the company before a payout date, that installment is forfeited; it is not paid out to the departed employee retroactively.",
        ]),
        ("Eligibility", [
            "All active full-time employees are eligible to refer candidates, except employees on the Talent Acquisition team (whose role already involves recruiting) and hiring managers referring into their own open requisitions, to avoid a conflict of interest.",
        ]),
    ]),
    ("Performance Review Process", [
        ("Review Cadence", [
            "Contoso Corp conducts formal performance reviews twice per year: a mid-year check-in in June that is developmental and not tied to compensation, and an annual review in December that informs compensation decisions for the following year.",
        ]),
        ("Rating Scale", [
            "Employees are rated on a 4-point scale: Exceeds Expectations, Meets Expectations, Partially Meets Expectations, and Does Not Meet Expectations. Ratings are based on both what was achieved (goals) and how it was achieved (values and collaboration).",
        ]),
        ("Calibration", [
            "Manager ratings go through a cross-team calibration session before being finalized, to ensure consistent application of the rating scale across departments and prevent rating inflation or deflation in any single team.",
            "Employees may request a rating explanation meeting with their manager within 5 business days of receiving a final rating, particularly if the calibrated rating differs from the manager's initial proposed rating.",
        ]),
    ]),
    ("Anti-Harassment and Non-Discrimination Policy", [
        ("Policy Statement", [
            "Contoso Corp prohibits discrimination or harassment based on race, color, religion, sex, national origin, age, disability, sexual orientation, gender identity, or any other status protected by applicable federal, state, or local law. This applies to hiring, promotion, compensation, and every other term of employment.",
        ]),
        ("Reporting Process", [
            "Employees who experience or witness harassment should report it to their manager, HR Business Partner, or the confidential Ethics Hotline immediately. Reports are investigated within 10 business days by a trained investigator who is not in the reporting employee's direct chain of command.",
        ]),
        ("Non-Retaliation", [
            "Contoso Corp strictly prohibits retaliation against anyone who reports a concern in good faith or participates in an investigation, even if the investigation does not substantiate the original complaint.",
        ]),
    ]),
    ("IT Acceptable Use Policy", [
        ("Company Devices", [
            "Company-issued laptops and phones are for business use, with incidental personal use permitted as long as it does not interfere with work or violate other policies (for example, incidental personal use must not involve illegal content or excessive personal streaming that degrades network performance for others).",
        ]),
        ("Prohibited Activity", [
            "Employees may not install unauthorized software, disable endpoint security tools (antivirus, disk encryption, mobile device management), or use company systems to access illegal content. Violations may result in immediate loss of system access pending investigation.",
        ]),
        ("Password Requirements", [
            "All Contoso accounts require multi-factor authentication and a password of at least 14 characters, rotated every 180 days. Password reuse across the last 10 passwords is blocked by the identity system.",
        ]),
    ]),
    ("Data Security and Confidentiality Policy", [
        ("Data Classification", [
            "Contoso Corp classifies data into three tiers: Public, Internal, and Confidential. Customer PII and financial records are always classified Confidential, regardless of which system they are stored in.",
        ]),
        ("Handling Confidential Data", [
            "Confidential data may not be stored on personal devices, personal cloud storage, or transmitted over unencrypted channels. Confidential data leaving the company (e.g., shared with an approved third-party vendor) requires a signed data processing agreement on file with Legal.",
        ]),
        ("Incident Reporting", [
            "Suspected data breaches must be reported to security@contoso-corp.example within 1 hour of discovery, per the Incident Response Runbook. Delayed reporting can affect Contoso Corp's ability to meet legal breach-notification deadlines, so timeliness matters more than certainty — report suspected incidents even before they are confirmed.",
        ]),
    ]),
]

DOCS_PDF = [
    ("Onboarding Checklist for New Hires", [
        ("Before Day One", [
            "IT provisions your laptop and accounts 3 business days before your start date. HR sends your offer packet and I-9 form for e-signature, which must be completed within 3 business days of the start date per federal requirements.",
        ]),
        ("Week One", [
            "New hires complete Contoso 101 orientation, benefits enrollment, and meet with their manager to set 30-60-90 day goals. IT security training and the Code of Conduct acknowledgment must also be completed within the first week.",
        ]),
        ("First 90 Days", [
            "Managers conduct check-ins at 30, 60, and 90 days. The first formal performance conversation happens at the 90-day mark, which also marks the end of the introductory period referenced in several other policies (e.g., 401(k) eligibility, parental leave eligibility).",
        ]),
        ("Buddy Program", [
            "Every new hire is assigned a peer buddy from a different team for their first 60 days, to provide an informal point of contact outside the direct reporting line for questions about culture and unwritten norms.",
        ]),
    ]),
    ("Offboarding Procedure", [
        ("Final Pay", [
            "Departing employees receive their final paycheck, including any unused PTO payout, on the next regularly scheduled payroll date after their last day, or sooner where required by state law (several states require final pay immediately or within 72 hours for involuntary terminations).",
        ]),
        ("Equipment Return", [
            "All company equipment (laptop, monitor, badge) must be returned within 5 business days of the last day of employment via prepaid shipping label provided by IT. Unreturned equipment may be deducted from final pay where permitted by state law.",
        ]),
        ("Benefits After Departure", [
            "Health benefits end on the last day of the month of departure. COBRA continuation coverage information is mailed within 14 days, and the departing employee has 60 days from the COBRA notice to elect continuation coverage.",
        ]),
        ("Exit Interview", [
            "Departing employees are invited to an optional exit interview with HR, conducted separately from the employee's manager, to gather candid feedback on their experience at Contoso Corp.",
        ]),
    ]),
    ("Workplace Safety Guidelines", [
        ("Office Safety", [
            "All Contoso offices maintain marked emergency exits, fire extinguishers inspected quarterly, and a designated floor warden for each office level responsible for coordinating evacuations during drills and real emergencies.",
        ]),
        ("Reporting Incidents", [
            "Any workplace injury, however minor, must be reported to Facilities and HR within 24 hours using the Incident Report Form, even if the employee does not seek medical treatment, so that any pattern of hazards can be identified early.",
        ]),
        ("Ergonomics", [
            "Employees may request a free ergonomic assessment of their home or office workstation through the Workplace Safety team. Assessments typically result in recommendations for chair height, monitor position, and keyboard placement, and may result in approval for an ergonomic equipment purchase.",
        ]),
        ("Emergency Procedures", [
            "In the event of a fire alarm, employees must evacuate immediately via the nearest marked exit and gather at their office's designated assembly point; re-entry is not permitted until the floor warden or emergency services confirm it is safe.",
        ]),
    ]),
    ("Tuition Reimbursement Program", [
        ("Eligibility", [
            "Full-time employees with at least 6 months of tenure are eligible for tuition reimbursement for courses related to their current role or a reasonable career path at Contoso Corp, as determined jointly by the employee and their manager.",
        ]),
        ("Reimbursement Amount", [
            "Contoso Corp reimburses up to $5,250 per calendar year for tuition, required textbooks, and course fees, upon proof of a passing grade (C or better, or Pass in pass/fail courses). Amounts above $5,250 in a calendar year are reimbursed but treated as taxable income per IRS rules on employer education assistance.",
        ]),
        ("Approval Process", [
            "Submit the Tuition Reimbursement Pre-Approval Form to your manager and HR before the course start date; reimbursement requests without prior approval will be denied regardless of the grade earned.",
        ]),
        ("Repayment on Departure", [
            "Employees who voluntarily resign within 12 months of receiving tuition reimbursement must repay the reimbursed amount on a prorated basis, as outlined in the Tuition Reimbursement Agreement signed at approval time.",
        ]),
    ]),
    ("Employee Assistance Program Guide", [
        ("What the EAP Covers", [
            "The Contoso Employee Assistance Program (EAP) provides up to 6 free confidential counseling sessions per issue, per year, for employees and their household members. Sessions can be used for a range of concerns including stress, grief, relationship issues, and substance use.",
        ]),
        ("Additional Services", [
            "The EAP also offers free legal consultations (up to 1 hour per matter), financial planning sessions, and childcare/eldercare referral services, all administered by the same third-party provider as the counseling benefit.",
        ]),
        ("How to Access", [
            "Call the EAP support line at 1-800-555-0199, available 24/7, or visit the EAP portal linked from the Contoso benefits page. All contact is confidential and not shared with Contoso Corp, including whether a given employee has used the service at all.",
        ]),
        ("Crisis Support", [
            "For an immediate mental health crisis, the EAP line offers a dedicated crisis option available at the same number, staffed by licensed clinicians who can also connect the caller to local emergency services if needed.",
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
