"""Generate realistic health insurance policy PDFs for testing ingestion, tables, and versions."""

from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import io

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def draw_table(page, x0, y0, col_widths, rows, row_height=26, header_bg=(0.92, 0.94, 0.98)):
    total_w = sum(col_widths)
    total_h = row_height * len(rows)

    # Header background fill
    page.draw_rect(fitz.Rect(x0, y0, x0 + total_w, y0 + row_height), color=None, fill=header_bg)

    # Outer border
    page.draw_rect(fitz.Rect(x0, y0, x0 + total_w, y0 + total_h), color=(0.2, 0.2, 0.2), width=1.0)

    # Horizontal grid lines
    for i in range(1, len(rows)):
        y = y0 + i * row_height
        page.draw_line(fitz.Point(x0, y), fitz.Point(x0 + total_w, y), color=(0.4, 0.4, 0.4), width=0.8)

    # Vertical grid lines
    x = x0
    for w in col_widths[:-1]:
        x += w
        page.draw_line(fitz.Point(x, y0), fitz.Point(x, y0 + total_h), color=(0.4, 0.4, 0.4), width=0.8)

    # Text cells
    for r_idx, row in enumerate(rows):
        cur_x = x0
        cur_y = y0 + r_idx * row_height + row_height * 0.65
        is_head = (r_idx == 0)
        font_size = 9.5 if is_head else 9.0
        for c_idx, cell in enumerate(row):
            page.insert_text((cur_x + 6, cur_y), str(cell), fontsize=font_size)
            cur_x += col_widths[c_idx]

    return y0 + total_h


def add_header_footer(page, doc_title, page_num, total_pages):
    # Header
    page.insert_text((50, 40), doc_title, fontsize=8.5, color=(0.4, 0.4, 0.4))
    page.draw_line(fitz.Point(50, 45), fitz.Point(545, 45), color=(0.7, 0.7, 0.7), width=0.5)

    # Footer
    page.draw_line(fitz.Point(50, 805), fitz.Point(545, 805), color=(0.7, 0.7, 0.7), width=0.5)
    page.insert_text((50, 818), f"Policy Terms & Conditions | Page {page_num} of {total_pages}",
                     fontsize=8.5, color=(0.4, 0.4, 0.4))


def generate_apex_v1():
    dest = RAW_DIR / "apex_health_v1.pdf"
    doc = fitz.open()
    total_pages = 6
    title = "Apex General Insurance - Apex Health Shield Policy (Version 1 - 2022)"

    # --- Page 1: Definitions ---
    p1 = doc.new_page(width=595, height=842)
    add_header_footer(p1, title, 1, total_pages)
    p1.insert_text((50, 80), "Apex Health Shield - Comprehensive Health Policy", fontsize=15)
    p1.insert_text((50, 105), "Policy Wordings (Edition: January 2022, Version 1)", fontsize=11, color=(0.2, 0.3, 0.6))
    
    y = 140
    p1.insert_text((50, y), "## Section 1. Definitions and Preliminary Interpretations", fontsize=12)
    y += 25
    definitions = [
        "1.1 Inpatient Hospitalisation means admission into a Hospital for a minimum contiguous period of 24 consecutive hours.",
        "1.2 Hospital means any institution established for inpatient care that has at least 15 in-patient beds in towns having a population of more than 10,000 and 10 beds in all other places, with qualified medical staff present round the clock.",
        "1.3 Pre-existing Disease (PED) means any condition, ailment or injury or related condition for which the Insured Person had signs or symptoms, or was diagnosed, or received medical advice or treatment within 48 months prior to policy inception.",
        "1.4 Free-Look Period means the specified period of 15 days from the date of receipt of the Policy document by the policyholder to review terms and opt to cancel.",
        "1.5 Grace Period means the specified period of 30 days immediately following the premium due date during which a payment can be made to maintain policy continuity.",
        "1.6 Co-payment means a cost-sharing requirement under this policy that provides that the Policyholder will bear a specified percentage of the admissible claim amount.",
    ]
    for d in definitions:
        rect = fitz.Rect(50, y, 545, y + 45)
        p1.insert_textbox(rect, d, fontsize=9.5)
        y += 50

    # --- Page 2: Inpatient Benefits Schedule (Table) ---
    p2 = doc.new_page(width=595, height=842)
    add_header_footer(p2, title, 2, total_pages)
    p2.insert_text((50, 80), "## Section 2. Inpatient Hospitalisation Benefits and Limits", fontsize=12)
    p2.insert_textbox(fitz.Rect(50, 100, 545, 140),
                      "The following table defines the specific monetary limits, allowances and day limits applicable under Apex Health Shield Version 1.",
                      fontsize=9.5)
    
    rows = [
        ["Benefit Component", "Coverage Limit / Sub-limit (v1)", "Waiting Period"],
        ["Room Rent Sub-limit", "Rs. 5,000 per day", "None"],
        ["ICU / ICCU Charges", "Rs. 10,000 per day", "None"],
        ["Pre-Hospitalisation Cover", "30 days prior to admission", "Linked to illness"],
        ["Post-Hospitalisation Cover", "60 days following discharge", "Linked to illness"],
        ["Road Ambulance Charges", "Rs. 2,000 per hospitalisation", "None"],
        ["AYUSH Treatment Cover", "Up to 50% of Sum Insured", "Linked to illness"],
        ["Day Care Procedures", "Covered up to Sum Insured for 540 listed procedures", "Initial 30 days"],
        ["Organ Donor Expenses", "Covered up to Rs. 1,00,000 per policy year", "24 months"],
        ["Daily Hospital Cash Allowance", "Rs. 1,000 per day (maximum 10 days)", "Initial 30 days"]
    ]
    y = draw_table(p2, 50, 150, [170, 210, 115], rows, row_height=26)

    p2.insert_textbox(fitz.Rect(50, y + 20, 545, y + 80),
                      "Note on Room Rent Sub-limit: If the Insured occupies a room with room rent exceeding Rs. 5,000 per day, proportionate deductions shall apply to associate medical expenses.",
                      fontsize=9)

    # --- Page 3: Waiting Periods (Table) ---
    p3 = doc.new_page(width=595, height=842)
    add_header_footer(p3, title, 3, total_pages)
    p3.insert_text((50, 80), "## Section 3. Waiting Periods and Specific Moratoria", fontsize=12)
    p3.insert_textbox(fitz.Rect(50, 100, 545, 140),
                      "No claim shall be admissible under this policy until the expiry of the respective waiting periods specified below.",
                      fontsize=9.5)

    wp_rows = [
        ["Category", "Specific Condition / Procedure", "Waiting Period (v1)"],
        ["Initial Waiting Period", "All illnesses except accidental bodily injury", "30 days"],
        ["Specific Ailment", "Cataract surgery and treatment", "24 months"],
        ["Specific Ailment", "Hernia, Hydrocele, Piles and Fistula", "24 months"],
        ["Specific Ailment", "Benign Prostatic Hypertrophy (BPH)", "24 months"],
        ["Specific Ailment", "Joint Replacement Surgery (unless accidental)", "36 months"],
        ["Pre-existing Disease", "Pre-existing diseases declared at inception", "48 months"]
    ]
    y = draw_table(p3, 50, 150, [150, 220, 125], wp_rows, row_height=26)

    p3.insert_textbox(fitz.Rect(50, y + 25, 545, y + 90),
                      "Clause 3.4 Cataract Sub-limit: The maximum payable amount for cataract surgery under Version 1 is capped at Rs. 40,000 per eye.",
                      fontsize=9.5)

    # --- Page 4: Exclusions ---
    p4 = doc.new_page(width=595, height=842)
    add_header_footer(p4, title, 4, total_pages)
    p4.insert_text((50, 80), "## Section 4. Exclusions under the Policy", fontsize=12)
    
    y = 110
    exclusions = [
        "4.1 Cosmetic Surgery: Treatment or surgery for aesthetic reasons, change of appearance, or plastic surgery is excluded unless required reconstructive surgery following accidental bodily injury or burn trauma.",
        "4.2 Self-Inflicted Injury: Claims directly or indirectly arising from intentional self-inflicted injury, suicide attempt, or hazardous adventure sports are strictly non-payable.",
        "4.3 Maternity and Childbirth: Inpatient medical expenses for maternity, childbirth, cesarean section, prenatal or postnatal care are excluded under Version 1.",
        "4.4 Dental Treatment: Dental treatment or surgery of any kind is excluded unless requiring hospitalisation arising solely from an accidental injury.",
        "4.5 Weight Loss Treatment: Treatments related to obesity, bariatric surgery, dietary control or dietary supplements are excluded.",
        "4.6 Investigation and Evaluation: Admission primarily for diagnostic, radiological or laboratory examinations without active inpatient medical treatment is excluded."
    ]
    for e in exclusions:
        p4.insert_textbox(fitz.Rect(50, y, 545, y + 45), e, fontsize=9.5)
        y += 52

    # --- Page 5: Claims Procedure ---
    p5 = doc.new_page(width=595, height=842)
    add_header_footer(p5, title, 5, total_pages)
    p5.insert_text((50, 80), "## Section 5. Claims Intimation, Procedure and Policy Terms", fontsize=12)

    terms = [
        ("5.1 Planned Hospitalisation Notice:", "The insured or representative must notify the insurer at least 48 hours prior to planned admission at a network hospital."),
        ("5.2 Emergency Admission Notice:", "Notice must be provided within 24 hours of emergency hospitalisation or before discharge, whichever is earlier."),
        ("5.3 Free-Look Period Duration:", "A free-look period of 15 days is allowed from the date of physical or electronic receipt of the policy schedule. If no claim was made, premium is refunded subject to minimal administrative charges."),
        ("5.4 Grace Period for Renewal:", "A grace period of 30 days is permissible for renewal of the policy. Coverage will not be active for illnesses occurring during the unpaid grace gap, but continuity benefits are preserved."),
        ("5.5 Documentation Checklist:", "Original completed claim form, hospital discharge summary, itemized hospital bill with payment receipts, diagnostic lab reports, doctor's prescription, and pharmacy payment vouchers must be submitted within 30 days of discharge.")
    ]
    y = 110
    for h, b in terms:
        p5.insert_text((50, y), h, fontsize=10)
        p5.insert_textbox(fitz.Rect(50, y + 5, 545, y + 40), b, fontsize=9.5)
        y += 50

    # --- Page 6: Co-payment & Cumulative Bonus ---
    p6 = doc.new_page(width=595, height=842)
    add_header_footer(p6, title, 6, total_pages)
    p6.insert_text((50, 80), "## Section 6. Cost Sharing, Co-Payment and Cumulative Bonus", fontsize=12)

    y = 110
    p6.insert_text((50, y), "6.1 Mandatory Senior Co-payment (v1):", fontsize=10)
    p6.insert_textbox(fitz.Rect(50, y + 5, 545, y + 45),
                      "For insured persons who are 65 years of age or older at the date of entry, a mandatory co-payment of 20% shall apply to each and every admissible claim amount.",
                      fontsize=9.5)
    y += 55

    p6.insert_text((50, y), "6.2 Cumulative Bonus (v1):", fontsize=10)
    p6.insert_textbox(fitz.Rect(50, y + 5, 545, y + 55),
                      "For every claim-free policy year, the base Sum Insured shall be increased by 10%, subject to a maximum cumulative bonus of 50% of the base Sum Insured. If a claim is paid, the bonus reduces by 10% at renewal.",
                      fontsize=9.5)
    y += 65

    p6.insert_text((50, y), "6.3 Organ Donor Expense Support:", fontsize=10)
    p6.insert_textbox(fitz.Rect(50, y + 5, 545, y + 50),
                      "Hospitalisation expenses incurred for organ donation harvesting from a living donor are payable up to a limit of Rs. 1,00,000, provided the organ is for the insured recipient.",
                      fontsize=9.5)

    doc.save(dest)
    doc.close()
    print("Generated:", dest)


def generate_apex_v2():
    dest = RAW_DIR / "apex_health_v2.pdf"
    doc = fitz.open()
    total_pages = 6
    title = "Apex General Insurance - Apex Health Shield Policy (Version 2 - 2024 Revised)"

    # --- Page 1: Definitions ---
    p1 = doc.new_page(width=595, height=842)
    add_header_footer(p1, title, 1, total_pages)
    p1.insert_text((50, 80), "Apex Health Shield - Comprehensive Health Policy", fontsize=15)
    p1.insert_text((50, 105), "Policy Wordings (Edition: March 2024, Version 2 - Enhanced Edition)", fontsize=11, color=(0.2, 0.3, 0.6))
    
    y = 140
    p1.insert_text((50, y), "## Section 1. Definitions and Preliminary Interpretations", fontsize=12)
    y += 25
    definitions = [
        "1.1 Inpatient Hospitalisation means admission into a Hospital for a minimum contiguous period of 24 consecutive hours.",
        "1.2 Hospital means any institution established for inpatient care that has at least 15 in-patient beds in towns having a population of more than 10,000 and 10 beds in all other places, with qualified medical staff present round the clock.",
        "1.3 Pre-existing Disease (PED) means any condition, ailment or injury or related condition for which the Insured Person had signs or symptoms, or was diagnosed, or received medical advice or treatment within 36 months prior to policy inception.",
        "1.4 Free-Look Period means the specified period of 15 days from the date of receipt of the Policy document by the policyholder to review terms and opt to cancel.",
        "1.5 Grace Period means the specified period of 30 days immediately following the premium due date during which a payment can be made to maintain policy continuity.",
        "1.6 Co-payment means a cost-sharing requirement under this policy that provides that the Policyholder will bear a specified percentage of the admissible claim amount.",
    ]
    for d in definitions:
        p1.insert_textbox(fitz.Rect(50, y, 545, y + 45), d, fontsize=9.5)
        y += 50

    # --- Page 2: Inpatient Benefits Schedule (Table - REVISED) ---
    p2 = doc.new_page(width=595, height=842)
    add_header_footer(p2, title, 2, total_pages)
    p2.insert_text((50, 80), "## Section 2. Inpatient Hospitalisation Benefits and Limits", fontsize=12)
    p2.insert_textbox(fitz.Rect(50, 100, 545, 140),
                      "The following table defines the enhanced monetary limits, allowances and day limits applicable under Apex Health Shield Version 2.",
                      fontsize=9.5)
    
    rows = [
        ["Benefit Component", "Coverage Limit / Sub-limit (v2)", "Waiting Period"],
        ["Room Rent Sub-limit", "Rs. 7,500 per day", "None"],
        ["ICU / ICCU Charges", "No sub-limit (actual charges up to Sum Insured)", "None"],
        ["Pre-Hospitalisation Cover", "60 days prior to admission", "Linked to illness"],
        ["Post-Hospitalisation Cover", "90 days following discharge", "Linked to illness"],
        ["Road Ambulance Charges", "Rs. 3,500 per hospitalisation", "None"],
        ["AYUSH Treatment Cover", "Up to 100% of Sum Insured", "Linked to illness"],
        ["Day Care Procedures", "Covered up to Sum Insured for all day care procedures", "Initial 30 days"],
        ["Organ Donor Expenses", "Covered up to Rs. 2,00,000 per policy year", "12 months"],
        ["Daily Hospital Cash Allowance", "Rs. 2,000 per day (maximum 15 days)", "Initial 30 days"]
    ]
    y = draw_table(p2, 50, 150, [170, 210, 115], rows, row_height=26)

    p2.insert_textbox(fitz.Rect(50, y + 20, 545, y + 80),
                      "Note on Room Rent (v2 Revision): Version 2 increases the daily room rent allowance to Rs. 7,500 per day. For Single Private AC rooms up to this limit, no proportionate deductions apply.",
                      fontsize=9)

    # --- Page 3: Waiting Periods (Table - REVISED) ---
    p3 = doc.new_page(width=595, height=842)
    add_header_footer(p3, title, 3, total_pages)
    p3.insert_text((50, 80), "## Section 3. Waiting Periods and Specific Moratoria", fontsize=12)
    p3.insert_textbox(fitz.Rect(50, 100, 545, 140),
                      "No claim shall be admissible under this policy until the expiry of the respective waiting periods specified below.",
                      fontsize=9.5)

    wp_rows = [
        ["Category", "Specific Condition / Procedure", "Waiting Period (v2)"],
        ["Initial Waiting Period", "All illnesses except accidental bodily injury", "30 days"],
        ["Specific Ailment", "Cataract surgery and treatment", "12 months"],
        ["Specific Ailment", "Hernia, Hydrocele, Piles and Fistula", "24 months"],
        ["Specific Ailment", "Benign Prostatic Hypertrophy (BPH)", "24 months"],
        ["Specific Ailment", "Joint Replacement Surgery (unless accidental)", "24 months"],
        ["Pre-existing Disease", "Pre-existing diseases declared at inception", "36 months"]
    ]
    y = draw_table(p3, 50, 150, [150, 220, 125], wp_rows, row_height=26)

    p3.insert_textbox(fitz.Rect(50, y + 25, 545, y + 90),
                      "Clause 3.4 Cataract Sub-limit (v2): Under Version 2, cataract surgery waiting period is reduced to 12 months with limit enhanced to Rs. 60,000 per eye.",
                      fontsize=9.5)

    # --- Page 4: Exclusions ---
    p4 = doc.new_page(width=595, height=842)
    add_header_footer(p4, title, 4, total_pages)
    p4.insert_text((50, 80), "## Section 4. Exclusions and Maternity Addition", fontsize=12)
    
    y = 110
    exclusions = [
        "4.1 Cosmetic Surgery: Treatment or surgery for aesthetic reasons, change of appearance, or plastic surgery is excluded unless required reconstructive surgery following accidental bodily injury.",
        "4.2 Self-Inflicted Injury: Claims directly or indirectly arising from intentional self-inflicted injury, suicide attempt, or hazardous adventure sports are strictly non-payable.",
        "4.3 Maternity Benefit (New in v2): Inpatient medical expenses for maternity and normal or cesarean delivery are covered up to Rs. 50,000 per delivery after a waiting period of 24 months, for up to 2 deliveries.",
        "4.4 Dental Treatment: Dental treatment or surgery of any kind is excluded unless requiring hospitalisation arising solely from an accidental injury.",
        "4.5 Weight Loss Treatment: Treatments related to obesity, bariatric surgery, dietary control or dietary supplements are excluded.",
        "4.6 Investigation and Evaluation: Admission primarily for diagnostic, radiological or laboratory examinations without active inpatient medical treatment is excluded."
    ]
    for e in exclusions:
        p4.insert_textbox(fitz.Rect(50, y, 545, y + 45), e, fontsize=9.5)
        y += 52

    # --- Page 5: Claims Procedure ---
    p5 = doc.new_page(width=595, height=842)
    add_header_footer(p5, title, 5, total_pages)
    p5.insert_text((50, 80), "## Section 5. Claims Intimation, Procedure and Policy Terms", fontsize=12)

    terms = [
        ("5.1 Planned Hospitalisation Notice:", "The insured or representative must notify the insurer at least 48 hours prior to planned admission at a network hospital."),
        ("5.2 Emergency Admission Notice:", "Notice must be provided within 24 hours of emergency hospitalisation or before discharge, whichever is earlier."),
        ("5.3 Free-Look Period Duration:", "A free-look period of 15 days is allowed from the date of physical or electronic receipt of the policy schedule. If no claim was made, premium is refunded subject to minimal administrative charges."),
        ("5.4 Grace Period for Renewal:", "A grace period of 30 days is permissible for renewal of the policy. Coverage will not be active for illnesses occurring during the unpaid grace gap, but continuity benefits are preserved."),
        ("5.5 Documentation Checklist:", "Original completed claim form, hospital discharge summary, itemized hospital bill with payment receipts, diagnostic lab reports, doctor's prescription, and pharmacy payment vouchers must be submitted within 30 days of discharge.")
    ]
    y = 110
    for h, b in terms:
        p5.insert_text((50, y), h, fontsize=10)
        p5.insert_textbox(fitz.Rect(50, y + 5, 545, y + 40), b, fontsize=9.5)
        y += 50

    # --- Page 6: Co-payment & Cumulative Bonus ---
    p6 = doc.new_page(width=595, height=842)
    add_header_footer(p6, title, 6, total_pages)
    p6.insert_text((50, 80), "## Section 6. Cost Sharing, Co-Payment and Cumulative Bonus", fontsize=12)

    y = 110
    p6.insert_text((50, y), "6.1 Mandatory Senior Co-payment (v2 Reduced):", fontsize=10)
    p6.insert_textbox(fitz.Rect(50, y + 5, 545, y + 45),
                      "Under Version 2, the mandatory co-payment for insured persons aged 65 years and above is reduced to 10% per admissible claim.",
                      fontsize=9.5)
    y += 55

    p6.insert_text((50, y), "6.2 Enhanced Cumulative Bonus (v2):", fontsize=10)
    p6.insert_textbox(fitz.Rect(50, y + 5, 545, y + 55),
                      "For every claim-free policy year under Version 2, the base Sum Insured increases by 20%, up to a maximum cumulative bonus of 100% of the base Sum Insured.",
                      fontsize=9.5)
    y += 65

    p6.insert_text((50, y), "6.3 Organ Donor Expense Support (v2):", fontsize=10)
    p6.insert_textbox(fitz.Rect(50, y + 5, 545, y + 50),
                      "Hospitalisation expenses incurred for organ donation harvesting from a living donor are payable up to an enhanced limit of Rs. 2,00,000.",
                      fontsize=9.5)

    doc.save(dest)
    doc.close()
    print("Generated:", dest)


def generate_care_brochure():
    dest = RAW_DIR / "harbor_wellness_brochure.pdf"
    doc = fitz.open()
    total_pages = 4
    title = "Harbor Mutual Insurance - Harbor Wellness Advantage Brochure (v1)"

    p1 = doc.new_page(width=595, height=842)
    add_header_footer(p1, title, 1, total_pages)
    p1.insert_text((50, 80), "Harbor Wellness Advantage - Key Product Highlights", fontsize=15)
    p1.insert_text((50, 105), "Customer Information Brochure (Edition: 2023)", fontsize=11, color=(0.2, 0.3, 0.6))

    p1.insert_text((50, 140), "## 1. Product Overview and Eligibility", fontsize=12)
    p1.insert_textbox(fitz.Rect(50, 160, 545, 220),
                      "Harbor Wellness Advantage provides comprehensive health coverage with built-in fitness discounts, annual health check-ups from Day 1, and complete freedom from co-payments regardless of entry age.",
                      fontsize=9.5)

    rows = [
        ["Plan Feature", "Harbor Wellness Silver", "Harbor Wellness Gold"],
        ["Base Sum Insured Options", "Rs. 5 Lakhs, 10 Lakhs", "Rs. 25 Lakhs, 50 Lakhs"],
        ["Annual Health Check-up", "Covered once per year", "Covered twice per year"],
        ["Wellness Renewal Discount", "Up to 10% based on steps", "Up to 20% based on steps"],
        ["Worldwide Emergency Cover", "Not included", "Included up to $50,000"]
    ]
    draw_table(p1, 50, 240, [170, 160, 165], rows, row_height=26)

    # Page 2
    p2 = doc.new_page(width=595, height=842)
    add_header_footer(p2, title, 2, total_pages)
    p2.insert_text((50, 80), "## 2. Inpatient Hospitalisation & Day Care Procedures", fontsize=12)
    p2.insert_textbox(fitz.Rect(50, 105, 545, 170),
                      "Under Harbor Wellness Advantage, all day care treatments and inpatient hospitalisations are covered up to the Sum Insured with no proportionate room rent deductions.",
                      fontsize=9.5)

    rows2 = [
        ["Coverage Benefit", "Entitlement (Harbor Wellness)", "Remarks"],
        ["Room Category", "Single Private Room (Up to Sum Insured)", "No room rent capping"],
        ["ICU Charges", "Actual charges incurred", "No daily limit"],
        ["Pre-hospitalisation", "60 days prior to hospitalisation", "Medical expenses"],
        ["Post-hospitalisation", "180 days after discharge", "Extended recovery support"],
        ["Ambulance Charges", "Up to Rs. 5,000 per hospitalisation", "Air ambulance up to 5 Lakhs (Gold)"]
    ]
    draw_table(p2, 50, 180, [150, 210, 135], rows2, row_height=26)

    # Page 3
    p3 = doc.new_page(width=595, height=842)
    add_header_footer(p3, title, 3, total_pages)
    p3.insert_text((50, 80), "## 3. Waiting Periods and Pre-Existing Disease Terms", fontsize=12)
    p3.insert_textbox(fitz.Rect(50, 105, 545, 160),
                      "Pre-existing diseases are covered after 36 months of continuous coverage. Cataract surgery has a waiting period of 24 months with a sub-limit of Rs. 50,000 per eye.",
                      fontsize=9.5)

    # Page 4
    p4 = doc.new_page(width=595, height=842)
    add_header_footer(p4, title, 4, total_pages)
    p4.insert_text((50, 80), "## 4. Free-Look and Cancellation Policy", fontsize=12)
    p4.insert_textbox(fitz.Rect(50, 105, 545, 180),
                      "A period of 15 days from policy delivery is allowed as free-look. The policyholder may cancel by sending written notice. Grace period for premium renewal is 30 days.",
                      fontsize=9.5)

    doc.save(dest)
    doc.close()
    print("Generated:", dest)


def generate_scanned_rider():
    dest = RAW_DIR / "special_rider_scanned.pdf"
    doc = fitz.open()
    total_pages = 3
    title = "Apex General Insurance - Critical Illness Rider Add-on (v1)"

    # Page 1 (text)
    p1 = doc.new_page(width=595, height=842)
    add_header_footer(p1, title, 1, total_pages)
    p1.insert_text((50, 80), "Critical Illness Rider Add-on Policy Terms", fontsize=15)
    p1.insert_text((50, 110), "## 1. Schedule of Covered Critical Illnesses", fontsize=12)
    rows = [
        ["Illness Name", "Lump-sum Benefit", "Survival Period"],
        ["Cancer of Specified Severity", "100% of Rider Sum Insured", "30 days"],
        ["First Heart Attack (Myocardial Infarction)", "100% of Rider Sum Insured", "30 days"],
        ["Open Chest CABG", "100% of Rider Sum Insured", "30 days"],
        ["Kidney Failure Requiring Dialysis", "100% of Rider Sum Insured", "30 days"],
        ["Major Organ / Bone Marrow Transplant", "100% of Rider Sum Insured", "30 days"]
    ]
    draw_table(p1, 50, 140, [180, 180, 135], rows, row_height=26)

    # Page 2 (text)
    p2 = doc.new_page(width=595, height=842)
    add_header_footer(p2, title, 2, total_pages)
    p2.insert_text((50, 80), "## 2. Rider Waiting Periods and Exclusions", fontsize=12)
    p2.insert_textbox(fitz.Rect(50, 105, 545, 180),
                      "The Critical Illness Rider has an initial waiting period of 90 days from inception. Diagnosis of critical illness within 90 days is not covered. Pre-existing critical conditions carry a 48-month waiting period.",
                      fontsize=9.5)

    # Page 3: Scanned image page (No text layer) to test OCR!
    img = Image.new("RGB", (1200, 1600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw simulated scanned text on image
    draw.text((100, 100), "SPECIAL ENDORSEMENT CLAUSE - ORGAN DONOR ENHANCEMENT", fill=(20, 20, 20))
    draw.text((100, 150), "Endorsement Reference: APEX-RIDER-END-2022-09", fill=(50, 50, 50))
    draw.text((100, 220), "This endorsement forms part of the Critical Illness Rider Add-on Policy.", fill=(30, 30, 30))
    draw.text((100, 270), "1. Notwithstanding anything to the contrary in Section 2, the company agrees to extend", fill=(30, 30, 30))
    draw.text((100, 310), "   inpatient donor harvesting medical expenses up to an additional Rs 1,50,000.", fill=(30, 30, 30))
    draw.text((100, 370), "2. The organ donor waiting period under this endorsement is fixed at 12 months.", fill=(30, 30, 30))
    draw.text((100, 430), "3. Free-look cancellation for this rider must be exercised within 15 days.", fill=(30, 30, 30))
    draw.text((100, 490), "4. Signature and Seal of Authorized Signatory, Apex General Insurance.", fill=(30, 30, 30))

    # Add border box
    draw.rectangle([80, 80, 1120, 550], outline=(40, 40, 40), width=2)

    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_bytes = img_buf.getvalue()

    p3 = doc.new_page(width=595, height=842)
    # Insert only the image, no text
    p3.insert_image(fitz.Rect(40, 40, 555, 760), stream=img_bytes)

    doc.save(dest)
    doc.close()
    print("Generated:", dest)


if __name__ == "__main__":
    generate_apex_v1()
    generate_apex_v2()
    generate_care_brochure()
    generate_scanned_rider()
    print("All sample PDFs created in data/raw/")

