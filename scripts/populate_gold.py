"""Script to generate the complete 100-question gold benchmark in data/gold/gold_questions.csv."""

from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parent.parent
GOLD_CSV = ROOT / "data" / "gold" / "gold_questions.csv"

# Target breakdown (100 questions):
# table_lookup: 40 (0.40)
# plain_text: 25 (0.25)
# cross_reference: 15 (0.15)
# compare_two: 10 (0.10)
# unanswerable: 10 (0.10)

questions = []


def add_q(qid, qtype, question, doc_id, page, gold_answer, evidence_text,
          doc_id_2="", page_2="", answerable="yes", status="drafted", notes=""):
    questions.append({
        "id": qid,
        "type": qtype,
        "question": question,
        "doc_id": doc_id,
        "page": str(page) if page != "" else "",
        "gold_answer": gold_answer,
        "evidence_text": evidence_text,
        "doc_id_2": doc_id_2,
        "page_2": str(page_2) if page_2 != "" else "",
        "answerable": answerable,
        "status": status,
        "notes": notes,
    })


# -------------------------------------------------------------------------------------------------
# 1. TABLE LOOKUP (40 questions: Q001 to Q040)
# -------------------------------------------------------------------------------------------------

# APEX_HEALTH_V2 Page 2: Inpatient Benefits Schedule Table
add_q(
    "Q001", "table_lookup",
    "What is the daily room rent sub-limit under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 2,
    "Under Version 2, the room rent sub-limit is Rs. 7,500 per day.",
    "Room Rent Sub-limit | Rs. 7,500 per day | None"
)
add_q(
    "Q002", "table_lookup",
    "What is the ICU or ICCU daily charges limit under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 2,
    "There is no sub-limit for ICU / ICCU charges; actual charges are covered up to the Sum Insured.",
    "ICU / ICCU Charges | No sub-limit (actual charges up to Sum Insured) | None"
)
add_q(
    "Q003", "table_lookup",
    "How many days of pre-hospitalisation expenses are covered under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 2,
    "Pre-hospitalisation is covered for 60 days prior to admission.",
    "Pre-Hospitalisation Cover | 60 days prior to admission | Linked to illness"
)
add_q(
    "Q004", "table_lookup",
    "How many days of post-hospitalisation expenses are covered under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 2,
    "Post-hospitalisation is covered for 90 days following discharge.",
    "Post-Hospitalisation Cover | 90 days following discharge | Linked to illness"
)
add_q(
    "Q005", "table_lookup",
    "What is the road ambulance limit per hospitalisation under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 2,
    "Road ambulance charges are covered up to Rs. 3,500 per hospitalisation.",
    "Road Ambulance Charges | Rs. 3,500 per hospitalisation | None"
)
add_q(
    "Q006", "table_lookup",
    "What is the coverage limit for AYUSH treatments under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 2,
    "AYUSH treatment is covered up to 100% of the Sum Insured.",
    "AYUSH Treatment Cover | Up to 100% of Sum Insured | Linked to illness"
)
add_q(
    "Q007", "table_lookup",
    "What is the coverage limit for day care procedures under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 2,
    "Day care procedures are covered up to the Sum Insured for all day care procedures.",
    "Day Care Procedures | Covered up to Sum Insured for all day care procedures | Initial 30 days"
)
add_q(
    "Q008", "table_lookup",
    "What is the annual limit for organ donor expenses in the benefits table of Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 2,
    "Organ donor expenses are covered up to Rs. 2,00,000 per policy year.",
    "Organ Donor Expenses | Covered up to Rs. 2,00,000 per policy year | 12 months"
)
add_q(
    "Q009", "table_lookup",
    "What is the daily hospital cash allowance and maximum days covered under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 2,
    "Daily hospital cash allowance is Rs. 2,00,000 per day for a maximum of 15 days.",
    "Daily Hospital Cash Allowance | Rs. 2,000 per day (maximum 15 days) | Initial 30 days"
)
add_q(
    "Q010", "table_lookup",
    "What waiting period applies to organ donor expenses in the inpatient schedule of Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 2,
    "The waiting period for organ donor expenses is 12 months.",
    "Organ Donor Expenses | Covered up to Rs. 2,00,000 per policy year | 12 months"
)
add_q(
    "Q011", "table_lookup",
    "What waiting period applies to the daily hospital cash allowance in the inpatient schedule of Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 2,
    "The waiting period for the daily hospital cash allowance is the initial 30 days.",
    "Daily Hospital Cash Allowance | Rs. 2,000 per day (maximum 15 days) | Initial 30 days"
)

# APEX_HEALTH_V2 Page 3: Waiting Periods Table & Note
add_q(
    "Q012", "table_lookup",
    "What is the initial waiting period for illnesses other than accidental injury under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 3,
    "The initial waiting period is 30 days for all illnesses except accidental bodily injury.",
    "Initial Waiting Period | All illnesses except accidental bodily injury | 30 days"
)
add_q(
    "Q013", "table_lookup",
    "What is the waiting period for cataract surgery under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 3,
    "The waiting period for cataract surgery and treatment is 12 months.",
    "Specific Ailment | Cataract surgery and treatment | 12 months"
)
add_q(
    "Q014", "table_lookup",
    "What is the waiting period for hernia and piles under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 3,
    "The waiting period for hernia, hydrocele, piles and fistula is 24 months.",
    "Specific Ailment | Hernia, Hydrocele, Piles and Fistula | 24 months"
)
add_q(
    "Q015", "table_lookup",
    "What is the waiting period for Benign Prostatic Hypertrophy (BPH) under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 3,
    "The waiting period for Benign Prostatic Hypertrophy (BPH) is 24 months.",
    "Specific Ailment | Benign Prostatic Hypertrophy (BPH) | 24 months"
)
add_q(
    "Q016", "table_lookup",
    "What is the waiting period for joint replacement surgery under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 3,
    "The waiting period for joint replacement surgery (unless accidental) is 24 months.",
    "Specific Ailment | Joint Replacement Surgery (unless accidental) | 24 months"
)
add_q(
    "Q017", "table_lookup",
    "What is the waiting period for pre-existing diseases declared at inception under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 3,
    "The waiting period for pre-existing diseases declared at inception is 36 months.",
    "Pre-existing Disease | Pre-existing diseases declared at inception | 36 months"
)
add_q(
    "Q018", "table_lookup",
    "What is the monetary capping limit per eye for cataract surgery under Clause 3.4 of Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 3,
    "Under Clause 3.4, cataract surgery is capped at Rs. 60,000 per eye.",
    "Clause 3.4 Cataract Sub-limit (v2): Under Version 2, cataract surgery waiting period is reduced to 12 months with limit enhanced to Rs. 60,000 per eye."
)

# HARBOR_WELLNESS_BROCHURE Page 1: Plan Comparison Table
add_q(
    "Q019", "table_lookup",
    "What are the base Sum Insured options available under Harbor Wellness Silver?",
    "HARBOR_WELLNESS_BROCHURE", 1,
    "The base Sum Insured options under Harbor Wellness Silver are Rs. 5 Lakhs and Rs. 10 Lakhs.",
    "Base Sum Insured Options | Rs. 5 Lakhs, 10 Lakhs | Rs. 25 Lakhs, 50 Lakhs"
)
add_q(
    "Q020", "table_lookup",
    "What are the base Sum Insured options available under Harbor Wellness Gold?",
    "HARBOR_WELLNESS_BROCHURE", 1,
    "The base Sum Insured options under Harbor Wellness Gold are Rs. 25 Lakhs and Rs. 50 Lakhs.",
    "Base Sum Insured Options | Rs. 5 Lakhs, 10 Lakhs | Rs. 25 Lakhs, 50 Lakhs"
)
add_q(
    "Q021", "table_lookup",
    "How often is the annual health check-up covered under Harbor Wellness Silver?",
    "HARBOR_WELLNESS_BROCHURE", 1,
    "Under Harbor Wellness Silver, annual health check-up is covered once per year.",
    "Annual Health Check-up | Covered once per year | Covered twice per year"
)
add_q(
    "Q022", "table_lookup",
    "How often is the annual health check-up covered under Harbor Wellness Gold?",
    "HARBOR_WELLNESS_BROCHURE", 1,
    "Under Harbor Wellness Gold, annual health check-up is covered twice per year.",
    "Annual Health Check-up | Covered once per year | Covered twice per year"
)
add_q(
    "Q023", "table_lookup",
    "What is the maximum wellness renewal discount based on steps for Harbor Wellness Silver?",
    "HARBOR_WELLNESS_BROCHURE", 1,
    "The wellness renewal discount for Harbor Wellness Silver is up to 10% based on steps.",
    "Wellness Renewal Discount | Up to 10% based on steps | Up to 20% based on steps"
)
add_q(
    "Q024", "table_lookup",
    "What is the maximum wellness renewal discount based on steps for Harbor Wellness Gold?",
    "HARBOR_WELLNESS_BROCHURE", 1,
    "The wellness renewal discount for Harbor Wellness Gold is up to 20% based on steps.",
    "Wellness Renewal Discount | Up to 10% based on steps | Up to 20% based on steps"
)
add_q(
    "Q025", "table_lookup",
    "Is worldwide emergency cover included in Harbor Wellness Silver?",
    "HARBOR_WELLNESS_BROCHURE", 1,
    "Worldwide emergency cover is not included in Harbor Wellness Silver.",
    "Worldwide Emergency Cover | Not included | Included up to $50,000"
)
add_q(
    "Q026", "table_lookup",
    "What is the coverage limit for worldwide emergency cover under Harbor Wellness Gold?",
    "HARBOR_WELLNESS_BROCHURE", 1,
    "Worldwide emergency cover is included up to $50,000 under Harbor Wellness Gold.",
    "Worldwide Emergency Cover | Not included | Included up to $50,000"
)

# HARBOR_WELLNESS_BROCHURE Page 2: Inpatient Hospitalisation Table
add_q(
    "Q027", "table_lookup",
    "What room category entitlement is provided under Harbor Wellness Advantage?",
    "HARBOR_WELLNESS_BROCHURE", 2,
    "The room category is Single Private Room up to Sum Insured with no room rent capping.",
    "Room Category | Single Private Room (Up to Sum Insured) | No room rent capping"
)
add_q(
    "Q028", "table_lookup",
    "What is the daily ICU charges limit under Harbor Wellness Advantage?",
    "HARBOR_WELLNESS_BROCHURE", 2,
    "Under Harbor Wellness Advantage, actual ICU charges incurred are covered with no daily limit.",
    "ICU Charges | Actual charges incurred | No daily limit"
)
add_q(
    "Q029", "table_lookup",
    "How many days of pre-hospitalisation expenses are covered under Harbor Wellness Advantage?",
    "HARBOR_WELLNESS_BROCHURE", 2,
    "Pre-hospitalisation expenses are covered for 60 days prior to hospitalisation.",
    "Pre-hospitalisation | 60 days prior to hospitalisation | Medical expenses"
)
add_q(
    "Q030", "table_lookup",
    "How many days of post-hospitalisation expenses are covered under Harbor Wellness Advantage?",
    "HARBOR_WELLNESS_BROCHURE", 2,
    "Post-hospitalisation expenses are covered for 180 days after discharge.",
    "Post-hospitalisation | 180 days after discharge | Extended recovery support"
)
add_q(
    "Q031", "table_lookup",
    "What is the normal road ambulance coverage limit under Harbor Wellness Advantage?",
    "HARBOR_WELLNESS_BROCHURE", 2,
    "Normal road ambulance is covered up to Rs. 5,000 per hospitalisation.",
    "Ambulance Charges | Up to Rs. 5,000 per hospitalisation | Air ambulance up to 5 Lakhs (Gold)"
)
add_q(
    "Q032", "table_lookup",
    "What is the air ambulance limit for the Gold variant under Harbor Wellness Advantage?",
    "HARBOR_WELLNESS_BROCHURE", 2,
    "Air ambulance is covered up to Rs. 5 Lakhs for the Gold variant.",
    "Ambulance Charges | Up to Rs. 5,000 per hospitalisation | Air ambulance up to 5 Lakhs (Gold)"
)

# SPECIAL_RIDER_SCANNED Page 1: Critical Illness Schedule Table
add_q(
    "Q033", "table_lookup",
    "What is the lump-sum benefit payable for Cancer of Specified Severity under the Critical Illness Rider?",
    "SPECIAL_RIDER_SCANNED", 1,
    "The lump-sum benefit for Cancer of Specified Severity is 100% of the Rider Sum Insured.",
    "Cancer of Specified Severity | 100% of Rider Sum Insured | 30 days"
)
add_q(
    "Q034", "table_lookup",
    "What survival period is required to claim for Cancer of Specified Severity under the Critical Illness Rider?",
    "SPECIAL_RIDER_SCANNED", 1,
    "A survival period of 30 days is required.",
    "Cancer of Specified Severity | 100% of Rider Sum Insured | 30 days"
)
add_q(
    "Q035", "table_lookup",
    "What benefit is payable for First Heart Attack (Myocardial Infarction) under the Critical Illness Rider?",
    "SPECIAL_RIDER_SCANNED", 1,
    "The benefit payable is 100% of the Rider Sum Insured.",
    "First Heart Attack (Myocardial Infarction) | 100% of Rider Sum Insured | 30 days"
)
add_q(
    "Q036", "table_lookup",
    "What survival period is required for a First Heart Attack claim under the Critical Illness Rider?",
    "SPECIAL_RIDER_SCANNED", 1,
    "A survival period of 30 days is required.",
    "First Heart Attack (Myocardial Infarction) | 100% of Rider Sum Insured | 30 days"
)
add_q(
    "Q037", "table_lookup",
    "What is the lump-sum payout for Open Chest CABG under the Critical Illness Rider?",
    "SPECIAL_RIDER_SCANNED", 1,
    "The payout for Open Chest CABG is 100% of the Rider Sum Insured.",
    "Open Chest CABG | 100% of Rider Sum Insured | 30 days"
)
add_q(
    "Q038", "table_lookup",
    "What is the benefit payable for Kidney Failure Requiring Dialysis under the Critical Illness Rider?",
    "SPECIAL_RIDER_SCANNED", 1,
    "The benefit payable is 100% of the Rider Sum Insured.",
    "Kidney Failure Requiring Dialysis | 100% of Rider Sum Insured | 30 days"
)
add_q(
    "Q039", "table_lookup",
    "What survival period is required for Major Organ or Bone Marrow Transplant under the Critical Illness Rider?",
    "SPECIAL_RIDER_SCANNED", 1,
    "A survival period of 30 days is required.",
    "Major Organ / Bone Marrow Transplant | 100% of Rider Sum Insured | 30 days"
)

# AGENT_GUIDE_FAKE Page 1: Commission Table
add_q(
    "Q040", "table_lookup",
    "What is the commission percentage for the Silver tier in the Internal Agent Guide?",
    "AGENT_GUIDE_FAKE", 1,
    "The Silver tier commission rate is 7% for selling 11 to 25 policies per quarter.",
    "| Silver | 11 to 25 | 7% |"
)


# -------------------------------------------------------------------------------------------------
# 2. PLAIN TEXT (25 questions: Q041 to Q065)
# -------------------------------------------------------------------------------------------------

# APEX_HEALTH_V2 Definitions (Page 1)
add_q(
    "Q041", "plain_text",
    "How is Inpatient Hospitalisation defined in Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 1,
    "Inpatient Hospitalisation means admission into a Hospital for a minimum contiguous period of 24 consecutive hours.",
    "1.1 Inpatient Hospitalisation means admission into a Hospital for a minimum contiguous period of 24 consecutive hours."
)
add_q(
    "Q042", "plain_text",
    "What is the minimum bed requirement for a Hospital in towns with a population over 10,000 under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 1,
    "A Hospital must have at least 15 in-patient beds in towns having a population of more than 10,000.",
    "has at least 15 in-patient beds in towns having a population of more than 10,000 and 10 beds in all other places"
)
add_q(
    "Q043", "plain_text",
    "What is the lookback time window for Pre-existing Disease (PED) diagnosis in Apex Health Shield Version 2 definitions?",
    "APEX_HEALTH_V2", 1,
    "The lookback window for Pre-existing Disease is within 36 months prior to policy inception.",
    "1.3 Pre-existing Disease (PED) means any condition, ailment or injury or related condition for which the Insured Person had signs or symptoms, or was diagnosed, or received medical advice or treatment within 36 months prior to policy inception."
)
add_q(
    "Q044", "plain_text",
    "What is the duration of the Free-Look Period defined in Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 1,
    "The Free-Look Period is 15 days from the date of receipt of the Policy document.",
    "1.4 Free-Look Period means the specified period of 15 days from the date of receipt of the Policy document by the policyholder to review terms and opt to cancel."
)
add_q(
    "Q045", "plain_text",
    "What is the definition of Grace Period under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 1,
    "Grace Period means the specified period of 30 days immediately following the premium due date to maintain policy continuity.",
    "1.5 Grace Period means the specified period of 30 days immediately following the premium due date during which a payment can be made to maintain policy continuity."
)

# APEX_HEALTH_V2 Exclusions (Page 4)
add_q(
    "Q046", "plain_text",
    "Is cosmetic surgery covered under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 4,
    "Cosmetic surgery is excluded unless it is required reconstructive surgery following accidental bodily injury.",
    "4.1 Cosmetic Surgery: Treatment or surgery for aesthetic reasons, change of appearance, or plastic surgery is excluded unless required reconstructive surgery following accidental bodily injury."
)
add_q(
    "Q047", "plain_text",
    "Are claims for self-inflicted injury or suicide attempt payable under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 4,
    "No, claims arising from intentional self-inflicted injury, suicide attempt, or hazardous adventure sports are strictly non-payable.",
    "4.2 Self-Inflicted Injury: Claims directly or indirectly arising from intentional self-inflicted injury, suicide attempt, or hazardous adventure sports are strictly non-payable."
)
add_q(
    "Q048", "plain_text",
    "What maternity benefit coverage is provided under Section 4.3 of Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 4,
    "Maternity expenses are covered up to Rs. 50,000 per delivery after a waiting period of 24 months, for up to 2 deliveries.",
    "4.3 Maternity Benefit (New in v2): Inpatient medical expenses for maternity and normal or cesarean delivery are covered up to Rs. 50,000 per delivery after a waiting period of 24 months, for up to 2 deliveries."
)
add_q(
    "Q049", "plain_text",
    "Under what condition is dental treatment covered under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 4,
    "Dental treatment is excluded unless requiring hospitalisation arising solely from an accidental injury.",
    "4.4 Dental Treatment: Dental treatment or surgery of any kind is excluded unless requiring hospitalisation arising solely from an accidental injury."
)
add_q(
    "Q050", "plain_text",
    "Are weight loss treatments and bariatric surgery covered under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 4,
    "Weight loss treatments, bariatric surgery, dietary control or dietary supplements are excluded.",
    "4.5 Weight Loss Treatment: Treatments related to obesity, bariatric surgery, dietary control or dietary supplements are excluded."
)
add_q(
    "Q051", "plain_text",
    "Are hospital admissions primarily for diagnostic evaluations covered under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 4,
    "No, admission primarily for diagnostic, radiological or laboratory examinations without active inpatient medical treatment is excluded.",
    "4.6 Investigation and Evaluation: Admission primarily for diagnostic, radiological or laboratory examinations without active inpatient medical treatment is excluded."
)

# APEX_HEALTH_V2 Claims Procedure (Page 5)
add_q(
    "Q052", "plain_text",
    "How much advance notice is required for planned hospitalisation under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 5,
    "Notice must be given to the insurer at least 48 hours prior to planned admission at a network hospital.",
    "5.1 Planned Hospitalisation Notice: The insured or representative must notify the insurer at least 48 hours prior to planned admission at a network hospital."
)
add_q(
    "Q053", "plain_text",
    "When must notice of emergency hospitalisation be provided under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 5,
    "Notice must be provided within 24 hours of emergency hospitalisation or before discharge, whichever is earlier.",
    "5.2 Emergency Admission Notice: Notice must be provided within 24 hours of emergency hospitalisation or before discharge, whichever is earlier."
)
add_q(
    "Q054", "plain_text",
    "Within how many days after discharge must claim documents be submitted under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 5,
    "Claim documentation must be submitted within 30 days of discharge.",
    "5.5 Documentation Checklist: Original completed claim form, hospital discharge summary, itemized hospital bill with payment receipts, diagnostic lab reports, doctor's prescription, and pharmacy payment vouchers must be submitted within 30 days of discharge."
)

# APEX_HEALTH_V2 Cost Sharing (Page 6)
add_q(
    "Q055", "plain_text",
    "What mandatory co-payment applies to senior citizens aged 65 and above under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 6,
    "A mandatory co-payment of 10% applies to each admissible claim for insured persons aged 65 years and above.",
    "6.1 Mandatory Senior Co-payment (v2 Reduced): Under Version 2, the mandatory co-payment for insured persons aged 65 years and above is reduced to 10% per admissible claim."
)
add_q(
    "Q056", "plain_text",
    "What is the cumulative bonus percentage increase per claim-free year under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 6,
    "The base Sum Insured increases by 20% for every claim-free policy year.",
    "6.2 Enhanced Cumulative Bonus (v2): For every claim-free policy year under Version 2, the base Sum Insured increases by 20%, up to a maximum cumulative bonus of 100% of the base Sum Insured."
)
add_q(
    "Q057", "plain_text",
    "What is the maximum cumulative bonus limit under Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 6,
    "The maximum cumulative bonus is capped at 100% of the base Sum Insured.",
    "up to a maximum cumulative bonus of 100% of the base Sum Insured."
)
add_q(
    "Q058", "plain_text",
    "What is the expense limit for living organ donor harvesting under Clause 6.3 of Apex Health Shield Version 2?",
    "APEX_HEALTH_V2", 6,
    "Living donor harvesting hospitalisation expenses are payable up to an enhanced limit of Rs. 2,00,000.",
    "6.3 Organ Donor Expense Support (v2): Hospitalisation expenses incurred for organ donation harvesting from a living donor are payable up to an enhanced limit of Rs. 2,00,000."
)

# HARBOR_WELLNESS_BROCHURE (Pages 1, 3, 4)
add_q(
    "Q059", "plain_text",
    "Does Harbor Wellness Advantage require a co-payment for senior citizens entering the policy?",
    "HARBOR_WELLNESS_BROCHURE", 1,
    "Harbor Wellness Advantage provides complete freedom from co-payments regardless of entry age.",
    "complete freedom from co-payments regardless of entry age."
)
add_q(
    "Q060", "plain_text",
    "What is the waiting period for pre-existing diseases under Harbor Wellness Advantage?",
    "HARBOR_WELLNESS_BROCHURE", 3,
    "Pre-existing diseases are covered after 36 months of continuous coverage.",
    "Pre-existing diseases are covered after 36 months of continuous coverage."
)
add_q(
    "Q061", "plain_text",
    "What is the waiting period and sub-limit for cataract surgery under Harbor Wellness Advantage?",
    "HARBOR_WELLNESS_BROCHURE", 3,
    "Cataract surgery has a waiting period of 24 months with a sub-limit of Rs. 50,000 per eye.",
    "Cataract surgery has a waiting period of 24 months with a sub-limit of Rs. 50,000 per eye."
)
add_q(
    "Q062", "plain_text",
    "How can a policyholder cancel their policy during the free-look period under Harbor Wellness Advantage?",
    "HARBOR_WELLNESS_BROCHURE", 4,
    "The policyholder may cancel the policy within 15 days of delivery by sending written notice.",
    "A period of 15 days from policy delivery is allowed as free-look. The policyholder may cancel by sending written notice."
)

# SPECIAL_RIDER_SCANNED (Pages 2, 3)
add_q(
    "Q063", "plain_text",
    "What is the initial waiting period for the Critical Illness Rider?",
    "SPECIAL_RIDER_SCANNED", 2,
    "The Critical Illness Rider has an initial waiting period of 90 days from inception.",
    "The Critical Illness Rider has an initial waiting period of 90 days from inception. Diagnosis of critical illness within 90 days is not covered."
)
add_q(
    "Q064", "plain_text",
    "What is the waiting period for pre-existing critical conditions under the Critical Illness Rider?",
    "SPECIAL_RIDER_SCANNED", 2,
    "Pre-existing critical conditions carry a 48-month waiting period.",
    "Pre-existing critical conditions carry a 48-month waiting period."
)
add_q(
    "Q065", "plain_text",
    "What additional donor harvesting limit is granted in Endorsement APEX-RIDER-END-2022-09?",
    "SPECIAL_RIDER_SCANNED", 3,
    "The endorsement extends inpatient donor harvesting medical expenses up to an additional Rs 1,50,000.",
    "1. Notwithstanding anything to the contrary in Section 2, the company agrees to extend inpatient donor harvesting medical expenses up to an additional Rs 1,50,000."
)


# -------------------------------------------------------------------------------------------------
# 3. CROSS REFERENCE (15 questions: Q066 to Q080)
# -------------------------------------------------------------------------------------------------

add_q(
    "Q066", "cross_reference",
    "In Apex Health Shield Version 2, what minimum duration defines Inpatient Hospitalisation on Page 1, and what daily room rent limit applies on Page 2?",
    "APEX_HEALTH_V2", 1,
    "Inpatient Hospitalisation requires a minimum contiguous admission of 24 consecutive hours, and the daily room rent sub-limit is Rs. 7,500 per day.",
    "1.1 Inpatient Hospitalisation means admission into a Hospital for a minimum contiguous period of 24 consecutive hours.",
    page_2=2,
    notes="References p.1 for definition and p.2 for room rent sublimit"
)
add_q(
    "Q067", "cross_reference",
    "In Apex Health Shield Version 2, how does the Pre-existing Disease definition time window on Page 1 correspond to the PED waiting period on Page 3?",
    "APEX_HEALTH_V2", 1,
    "The definition covers conditions diagnosed or treated within 36 months prior to inception, and the waiting period schedule requires 36 months of continuous coverage before PED claims are admissible.",
    "1.3 Pre-existing Disease (PED) means any condition, ailment or injury or related condition for which the Insured Person had signs or symptoms, or was diagnosed, or received medical advice or treatment within 36 months prior to policy inception.",
    page_2=3,
    notes="References p.1 PED definition and p.3 PED waiting period"
)
add_q(
    "Q068", "cross_reference",
    "In Apex Health Shield Version 2, how is Co-payment defined on Page 1, and what specific percentage applies to senior citizens on Page 6?",
    "APEX_HEALTH_V2", 1,
    "Co-payment is defined on Page 1 as cost-sharing where the policyholder bears a specified percentage, and Page 6 sets a mandatory 10% co-payment for insured persons aged 65 and above.",
    "1.6 Co-payment means a cost-sharing requirement under this policy that provides that the Policyholder will bear a specified percentage of the admissible claim amount.",
    page_2=6,
    notes="References p.1 co-pay definition and p.6 senior co-pay clause"
)
add_q(
    "Q069", "cross_reference",
    "In Apex Health Shield Version 2, what is the initial waiting period for day care procedures on Page 2 compared to the general initial waiting period on Page 3?",
    "APEX_HEALTH_V2", 2,
    "Both the day care procedures row on Page 2 and the general initial waiting period on Page 3 specify an initial waiting period of 30 days for illnesses.",
    "Day Care Procedures | Covered up to Sum Insured for all day care procedures | Initial 30 days",
    page_2=3,
    notes="References p.2 day care waiting period and p.3 initial waiting period"
)
add_q(
    "Q070", "cross_reference",
    "In Apex Health Shield Version 2, how does the organ donor limit in the benefits table on Page 2 align with the organ donor support clause on Page 6?",
    "APEX_HEALTH_V2", 2,
    "Both the Page 2 schedule and Clause 6.3 on Page 6 establish an enhanced coverage limit of Rs. 2,00,000 for living organ donor harvesting expenses.",
    "Organ Donor Expenses | Covered up to Rs. 2,00,000 per policy year | 12 months",
    page_2=6,
    notes="References p.2 organ donor table and p.6 organ donor clause"
)
add_q(
    "Q071", "cross_reference",
    "In Apex Health Shield Version 2, what is the cataract surgery waiting period in the table on Page 3, and what sub-limit is specified in Clause 3.4 on Page 3 and Page 2?",
    "APEX_HEALTH_V2", 3,
    "The waiting period is 12 months, and Clause 3.4 caps cataract surgery at Rs. 60,000 per eye.",
    "Specific Ailment | Cataract surgery and treatment | 12 months",
    page_2=2,
    notes="References p.3 cataract table/clause and p.2 inpatient table"
)
add_q(
    "Q072", "cross_reference",
    "In Apex Health Shield Version 2, how does the accidental bodily injury exception to the waiting period on Page 3 relate to the reconstructive cosmetic surgery clause on Page 4?",
    "APEX_HEALTH_V2", 3,
    "Accidental bodily injury has no initial waiting period on Page 3, and Page 4 allows an exception for reconstructive surgery following accidental bodily injury.",
    "Initial Waiting Period | All illnesses except accidental bodily injury | 30 days",
    page_2=4,
    notes="References p.3 accidental exception and p.4 reconstructive surgery exception"
)
add_q(
    "Q073", "cross_reference",
    "In Apex Health Shield Version 2, what is the maternity benefit waiting period under Section 4.3 on Page 4 compared to the general initial waiting period on Page 3?",
    "APEX_HEALTH_V2", 4,
    "Maternity benefit requires a waiting period of 24 months under Section 4.3 on Page 4, whereas general illnesses have a 30-day initial waiting period on Page 3.",
    "4.3 Maternity Benefit (New in v2): Inpatient medical expenses for maternity and normal or cesarean delivery are covered up to Rs. 50,000 per delivery after a waiting period of 24 months, for up to 2 deliveries.",
    page_2=3,
    notes="References p.4 maternity waiting period and p.3 initial waiting period"
)
add_q(
    "Q074", "cross_reference",
    "In Apex Health Shield Version 2, what notice is required for planned admission on Page 5, and what minimum hospital stay is required on Page 1?",
    "APEX_HEALTH_V2", 5,
    "Planned admission requires at least 48 hours advance notice under Section 5.1 on Page 5, and Inpatient Hospitalisation requires a minimum stay of 24 consecutive hours under Section 1.1 on Page 1.",
    "5.1 Planned Hospitalisation Notice: The insured or representative must notify the insurer at least 48 hours prior to planned admission at a network hospital.",
    page_2=1,
    notes="References p.5 planned notice and p.1 inpatient definition"
)
add_q(
    "Q075", "cross_reference",
    "In Apex Health Shield Version 2, what is the Free-Look Period duration defined on Page 1, and what refund terms apply under Section 5.3 on Page 5?",
    "APEX_HEALTH_V2", 1,
    "The Free-Look Period is 15 days from receipt of the document, and Section 5.3 states that premium is refunded subject to minimal administrative charges if no claim was made.",
    "1.4 Free-Look Period means the specified period of 15 days from the date of receipt of the Policy document by the policyholder to review terms and opt to cancel.",
    page_2=5,
    notes="References p.1 free look definition and p.5 refund clause"
)
add_q(
    "Q076", "cross_reference",
    "In Harbor Wellness Advantage, what Sum Insured options are offered for Gold on Page 1, and what room category entitlement applies on Page 2?",
    "HARBOR_WELLNESS_BROCHURE", 1,
    "Harbor Wellness Gold offers Sum Insured options of Rs. 25 Lakhs and Rs. 50 Lakhs on Page 1, with Single Private Room entitlement up to Sum Insured with no room capping on Page 2.",
    "Base Sum Insured Options | Rs. 5 Lakhs, 10 Lakhs | Rs. 25 Lakhs, 50 Lakhs",
    page_2=2,
    notes="References p.1 Gold sum insured and p.2 room category"
)
add_q(
    "Q077", "cross_reference",
    "In Harbor Wellness Advantage, what worldwide emergency coverage is provided for Gold on Page 1, and what air ambulance limit is provided on Page 2?",
    "HARBOR_WELLNESS_BROCHURE", 1,
    "Harbor Wellness Gold provides worldwide emergency cover up to $50,000 on Page 1 and air ambulance cover up to Rs. 5 Lakhs on Page 2.",
    "Worldwide Emergency Cover | Not included | Included up to $50,000",
    page_2=2,
    notes="References p.1 emergency worldwide cover and p.2 air ambulance"
)
add_q(
    "Q078", "cross_reference",
    "In Harbor Wellness Advantage, how does the free co-payment highlight on Page 1 compare to the pre-existing disease waiting period on Page 3?",
    "HARBOR_WELLNESS_BROCHURE", 1,
    "While Page 1 provides complete freedom from co-payments regardless of age, Page 3 specifies that pre-existing diseases are covered after a 36-month waiting period.",
    "complete freedom from co-payments regardless of entry age.",
    page_2=3,
    notes="References p.1 co-pay freedom and p.3 PED waiting period"
)
add_q(
    "Q079", "cross_reference",
    "In the Critical Illness Rider, what benefit is paid for Major Organ Transplant on Page 1, and what additional donor expense is provided in the Page 3 endorsement?",
    "SPECIAL_RIDER_SCANNED", 1,
    "Major Organ Transplant pays 100% of the Rider Sum Insured on Page 1, and the Page 3 endorsement provides an additional Rs 1,50,000 for inpatient donor harvesting expenses.",
    "Major Organ / Bone Marrow Transplant | 100% of Rider Sum Insured | 30 days",
    page_2=3,
    notes="References p.1 transplant benefit and p.3 scanned endorsement"
)
add_q(
    "Q080", "cross_reference",
    "In the Critical Illness Rider, what is the initial waiting period on Page 2 compared to the organ donor waiting period in the Page 3 endorsement?",
    "SPECIAL_RIDER_SCANNED", 2,
    "The initial waiting period for critical illnesses is 90 days on Page 2, whereas the organ donor waiting period under the Page 3 endorsement is fixed at 12 months.",
    "The Critical Illness Rider has an initial waiting period of 90 days from inception.",
    page_2=3,
    notes="References p.2 initial waiting period and p.3 scanned endorsement waiting period"
)


# -------------------------------------------------------------------------------------------------
# 4. COMPARE TWO (10 questions: Q081 to Q090)
# -------------------------------------------------------------------------------------------------

add_q(
    "Q081", "compare_two",
    "How does the daily room rent sub-limit compare between Version 1 and Version 2 of Apex Health Shield?",
    "APEX_HEALTH_V1", 2,
    "Under Version 1 the room rent sub-limit was Rs. 5,000 per day, whereas Version 2 increased it to Rs. 7,500 per day.",
    "Room Rent Sub-limit | Rs. 5,000 per day | None",
    doc_id_2="APEX_HEALTH_V2", page_2=2,
    notes="Compares room rent between v1 and v2"
)
add_q(
    "Q082", "compare_two",
    "How do the ICU charges limits differ between Version 1 and Version 2 of Apex Health Shield?",
    "APEX_HEALTH_V1", 2,
    "Version 1 capped ICU / ICCU charges at Rs. 10,000 per day, while Version 2 has no sub-limit with actual charges covered up to the Sum Insured.",
    "ICU / ICCU Charges | Rs. 10,000 per day | None",
    doc_id_2="APEX_HEALTH_V2", page_2=2,
    notes="Compares ICU charges sublimit between v1 and v2"
)
add_q(
    "Q083", "compare_two",
    "How does pre-hospitalisation expense coverage duration compare between Version 1 and Version 2 of Apex Health Shield?",
    "APEX_HEALTH_V1", 2,
    "Version 1 covered 30 days prior to admission, whereas Version 2 enhanced pre-hospitalisation cover to 60 days prior to admission.",
    "Pre-Hospitalisation Cover | 30 days prior to admission | Linked to illness",
    doc_id_2="APEX_HEALTH_V2", page_2=2,
    notes="Compares pre-hospitalisation days between v1 and v2"
)
add_q(
    "Q084", "compare_two",
    "How does post-hospitalisation expense coverage duration compare between Version 1 and Version 2 of Apex Health Shield?",
    "APEX_HEALTH_V1", 2,
    "Version 1 covered 60 days following discharge, whereas Version 2 enhanced post-hospitalisation cover to 90 days following discharge.",
    "Post-Hospitalisation Cover | 60 days following discharge | Linked to illness",
    doc_id_2="APEX_HEALTH_V2", page_2=2,
    notes="Compares post-hospitalisation days between v1 and v2"
)
add_q(
    "Q085", "compare_two",
    "How does the road ambulance limit per hospitalisation compare between Version 1 and Version 2 of Apex Health Shield?",
    "APEX_HEALTH_V1", 2,
    "Version 1 provided Rs. 2,000 per hospitalisation, while Version 2 increased the road ambulance allowance to Rs. 3,500 per hospitalisation.",
    "Road Ambulance Charges | Rs. 2,000 per hospitalisation | None",
    doc_id_2="APEX_HEALTH_V2", page_2=2,
    notes="Compares road ambulance limit between v1 and v2"
)
add_q(
    "Q086", "compare_two",
    "How did the waiting period for cataract surgery change from Version 1 to Version 2 of Apex Health Shield?",
    "APEX_HEALTH_V1", 3,
    "The waiting period for cataract surgery was reduced from 24 months in Version 1 to 12 months in Version 2.",
    "Specific Ailment | Cataract surgery and treatment | 24 months",
    doc_id_2="APEX_HEALTH_V2", page_2=3,
    notes="Compares cataract waiting period between v1 and v2"
)
add_q(
    "Q087", "compare_two",
    "How did the cataract surgery monetary sub-limit per eye change between Version 1 and Version 2 of Apex Health Shield?",
    "APEX_HEALTH_V1", 3,
    "The cataract sub-limit per eye was Rs. 40,000 in Version 1 and was increased to Rs. 60,000 in Version 2.",
    "Clause 3.4 Cataract Sub-limit: The maximum payable amount for cataract surgery under Version 1 is capped at Rs. 40,000 per eye.",
    doc_id_2="APEX_HEALTH_V2", page_2=3,
    notes="Compares cataract monetary cap between v1 and v2"
)
add_q(
    "Q088", "compare_two",
    "Which version of Apex Health Shield has a shorter waiting period for pre-existing diseases declared at inception?",
    "APEX_HEALTH_V1", 3,
    "Version 2 has a shorter waiting period of 36 months, compared to 48 months in Version 1.",
    "Pre-existing Disease | Pre-existing diseases declared at inception | 48 months",
    doc_id_2="APEX_HEALTH_V2", page_2=3,
    notes="Compares PED waiting periods between v1 and v2"
)
add_q(
    "Q089", "compare_two",
    "Do both Version 1 and Version 2 of Apex Health Shield cover maternity expenses, and how do they differ?",
    "APEX_HEALTH_V1", 4,
    "Version 1 strictly excludes maternity and childbirth, whereas Version 2 covers maternity up to Rs. 50,000 per delivery after a 24-month waiting period.",
    "4.3 Maternity and Childbirth: Inpatient medical expenses for maternity, childbirth, cesarean section, prenatal or postnatal care are excluded under Version 1.",
    doc_id_2="APEX_HEALTH_V2", page_2=4,
    notes="Compares maternity coverage between v1 and v2"
)
add_q(
    "Q090", "compare_two",
    "How did the mandatory co-payment for senior citizens aged 65 and above change between Version 1 and Version 2 of Apex Health Shield?",
    "APEX_HEALTH_V1", 6,
    "Version 1 imposed a 20% mandatory co-payment for seniors aged 65 and above, which was reduced to 10% in Version 2.",
    "For insured persons who are 65 years of age or older at the date of entry, a mandatory co-payment of 20% shall apply to each and every admissible claim amount.",
    doc_id_2="APEX_HEALTH_V2", page_2=6,
    notes="Compares senior co-payment between v1 and v2"
)


# -------------------------------------------------------------------------------------------------
# 5. UNANSWERABLE (10 questions: Q091 to Q100)
# -------------------------------------------------------------------------------------------------

add_q(
    "Q091", "unanswerable",
    "What is the annual policy premium for a 45-year-old individual residing in Bengaluru?",
    "", "",
    "not in the documents",
    "",
    answerable="no",
    notes="Premium amounts depend on rate tables not included in policy wordings"
)
add_q(
    "Q092", "unanswerable",
    "Does Apex Health Shield cover medical treatments at Mount Elizabeth Hospital in Singapore?",
    "", "",
    "not in the documents",
    "",
    answerable="no",
    notes="International hospital network details are not provided in the policy text"
)
add_q(
    "Q093", "unanswerable",
    "What was Apex General Insurance's incurred claim ratio or claim settlement ratio for last financial year?",
    "", "",
    "not in the documents",
    "",
    answerable="no",
    notes="Public disclosure financial statistics are not in policy wordings"
)
add_q(
    "Q094", "unanswerable",
    "What is the customer support toll-free telephone number for Harbor Mutual Insurance?",
    "", "",
    "not in the documents",
    "",
    answerable="no",
    notes="Toll-free customer care phone numbers are omitted from the brochure"
)
add_q(
    "Q095", "unanswerable",
    "Does Apex Health Shield provide cover for robotic surgery procedures for prostate cancer?",
    "", "",
    "not in the documents",
    "",
    answerable="no",
    notes="Robotic prostate surgery is not specifically named in the policy wording"
)
add_q(
    "Q096", "unanswerable",
    "Is outpatient consultation for dental caries or scaling covered under Harbor Wellness Advantage?",
    "", "",
    "not in the documents",
    "",
    answerable="no",
    notes="Outpatient OPD dental consultation is not detailed in the brochure"
)
add_q(
    "Q097", "unanswerable",
    "Which hospitals in Mumbai are included in the cashless network for Apex Health Shield?",
    "", "",
    "not in the documents",
    "",
    answerable="no",
    notes="Cashless network hospital directory is maintained separately"
)
add_q(
    "Q098", "unanswerable",
    "Does Apex Health Shield provide cashless claim settlement in government municipal hospitals?",
    "", "",
    "not in the documents",
    "",
    answerable="no",
    notes="Cashless facility at specific municipal hospitals is not stated"
)
add_q(
    "Q099", "unanswerable",
    "What is the maximum tax deduction limit under Section 80D of the Income Tax Act for this policy?",
    "", "",
    "not in the documents",
    "",
    answerable="no",
    notes="Income Tax Act Section 80D statutory limits are not part of policy terms"
)
add_q(
    "Q100", "unanswerable",
    "Can the insurance premium be paid in monthly installments via bank auto-debit ECS mandate?",
    "", "",
    "not in the documents",
    "",
    answerable="no",
    notes="Installment payment frequency options are not specified in the document"
)


def write_csv():
    fieldnames = [
        "id", "type", "question", "doc_id", "page", "gold_answer", "evidence_text",
        "doc_id_2", "page_2", "answerable", "status", "notes",
    ]
    with open(GOLD_CSV, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(questions)
    print(f"Successfully wrote {len(questions)} questions to {GOLD_CSV}")


if __name__ == "__main__":
    write_csv()

