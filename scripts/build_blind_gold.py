"""Build data/gold/gold_questions_blind.csv: a harder companion benchmark.

Why: in the main gold set almost every question names the product and the version, so
retrieval is easy (Hit@5 is near 100% even for the baseline) and no stage can show a gain.
The blind set keeps the same answers, documents and pages but

  * rewords each question in natural language (low word overlap with the source text),
  * removes version numbers, page numbers and clause numbers,
  * names the plan only casually ("the Apex plan"), as a customer would,
  * adds 25 near-miss unanswerable questions (related topics that are NOT in the documents).

Rows start as `drafted`. Check evidence with scripts/check_gold_evidence.py, search the PDFs for
each unanswerable question, then mark rows verified. The main gold file is never edited.
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data/gold/gold_questions.csv"
OUT = ROOT / "data/gold/gold_questions_blind.csv"

# original id -> casual paraphrase without version, page or clause hints
PARAPHRASES = {
    # table lookups
    "Q001": "How much will my Apex plan pay per day towards the hospital room?",
    "Q002": "Is there a daily cap on intensive care charges in the Apex plan?",
    "Q003": "For how many days before admission does the Apex plan cover my medical expenses?",
    "Q005": "What is the most the Apex plan pays for an ambulance each time I am hospitalised?",
    "Q006": "How much does the Apex plan pay for Ayurveda and other AYUSH treatment?",
    "Q007": "Does the Apex plan put a limit on day care procedures?",
    "Q012": "How long must I wait before the Apex plan pays for an illness that is not an accident?",
    "Q013": "How many months do I have to wait for cataract surgery to be covered on the Apex plan?",
    "Q014": "When can I claim for hernia or piles treatment on the Apex plan?",
    "Q016": "After how long does the Apex plan cover a joint replacement?",
    "Q017": "How long is the wait for conditions I already had when I bought the Apex plan?",
    "Q018": "What is the most the Apex plan pays per eye for cataract surgery?",
    "Q021": "How often can I get a free annual health check-up on the Silver wellness plan?",
    "Q024": "What is the biggest renewal discount I can earn through steps on the Gold wellness plan?",
    "Q026": "How much worldwide emergency cover does the Gold wellness plan give?",
    "Q028": "What is the daily limit on ICU charges under the Harbor wellness plan?",
    "Q032": "How much air ambulance cover does the Gold wellness plan include?",
    "Q033": "How much does the critical illness rider pay out if I am diagnosed with cancer?",
    "Q036": "How many days must I survive after a heart attack to claim under the critical illness rider?",
    "Q038": "What does the critical illness rider pay for kidney failure needing dialysis?",
    "Q040": "What commission does an agent in the Silver tier earn?",
    # plain text
    "Q043": "How far back does the Apex plan look when deciding if a condition was pre-existing?",
    "Q044": "How many days do I have to cancel the Apex plan and get my premium back after buying it?",
    "Q046": "Will the Apex plan pay for cosmetic surgery?",
    "Q047": "Does the Apex plan pay if someone deliberately injures themselves?",
    "Q048": "How much does the Apex plan pay for maternity?",
    "Q050": "Is surgery for weight loss covered by the Apex plan?",
    "Q052": "How early must I tell the insurer before a planned hospital stay on the Apex plan?",
    "Q053": "How soon must I report an emergency admission on the Apex plan?",
    "Q054": "How long after I leave hospital do I have to send in my claim papers on the Apex plan?",
    "Q055": "Do older customers pay part of the bill themselves on the Apex plan?",
    "Q056": "How much does my cover grow each year I make no claim on the Apex plan?",
    "Q057": "What is the ceiling on the no-claim growth in cover on the Apex plan?",
    "Q059": "Does the Harbor wellness plan make senior citizens pay a share of the bill?",
    "Q062": "How do I cancel the Harbor wellness plan after buying it, within the free-look window?",
    "Q063": "How long is the initial waiting period on the critical illness rider?",
    # cross references (the answer needs two places)
    "Q066": "On the Apex plan, how long must I stay in hospital for it to count as inpatient treatment, and what is the daily room limit?",
    "Q067": "How does the Apex plan's definition of a pre-existing condition line up with the waiting period for such conditions?",
    "Q071": "What waiting period and money limit does the Apex plan set for cataract surgery?",
    "Q073": "How does the maternity waiting period on the Apex plan compare with its general initial waiting period?",
    "Q079": "What does the critical illness rider pay for a major organ transplant, and what extra donor cost does its endorsement add?",
    # comparisons
    "Q081": "Did the daily room rent limit on the Apex plan go up or down between the older and newer version?",
    "Q083": "How did the number of days of pre-hospital cover change between the old and new Apex plan?",
    "Q086": "How did the cataract waiting period change between the old and new Apex plan?",
    "Q088": "Which version of the Apex plan has the shorter wait for conditions declared at purchase?",
    "Q090": "How did the co-payment for senior citizens change between the two Apex versions?",
}

# Related to topics the documents cover, but the specific fact is NOT in any document.
# Absence was checked against the text of the generator script (scripts/generate_sample_pdfs.py);
# confirm it again in the PDFs before marking these verified.
NEAR_MISS = [
    "Is IVF or other fertility treatment covered on the Apex plan?",
    "Does the Apex plan cover treatment for COVID-19?",
    "Does the Apex plan pay for veterinary treatment for my pet?",
    "Can I move my existing policy from another insurer to the Apex plan and keep my waiting periods?",
    "How many network hospitals can I get cashless treatment at?",
    "Can a newborn baby be added to the Harbor wellness plan, and from what age?",
    "Do I get a premium discount if I pay for two years upfront?",
    "Does the Apex plan cover treatment at home instead of in hospital?",
    "Can I get a second medical opinion paid for by the Apex plan?",
    "Does the Harbor wellness plan include doctor consultations by video call?",
    "Is treatment for a surrogate pregnancy covered under the Apex plan?",
    "What would the premium be for a family of two adults and two children?",
    "Is treatment for depression or other mental illness covered on the Apex plan?",
    "Does the Apex plan cover treatment for HIV or AIDS?",
    "Is there a loyalty discount for renewing the Apex plan five years in a row?",
    "Does the Apex plan pay for laser eye surgery to remove my glasses?",
    "Are hearing aids or spectacles covered on the Harbor wellness plan?",
    "Can I choose a no-claim discount instead of the cumulative bonus on the Apex plan?",
    "Does the Harbor wellness plan include cancer screening for people over 60?",
    "Are routine vaccinations for children covered on the Apex plan?",
    "Within how many days does the insurer promise to settle a claim once documents arrive?",
    "Can I lower my premium by choosing a deductible on the Apex plan?",
    "Which ombudsman office should I write to if I am unhappy with a claim decision?",
    "Is GST charged on the premium for the Harbor wellness plan?",
    "Does the critical illness rider cover stem cell transplants for sickle cell disease?",
]


def main() -> int:
    with GOLD.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields, rows = list(reader.fieldnames or []), list(reader)
    by_id = {r["id"]: r for r in rows}
    missing = sorted(set(PARAPHRASES) - set(by_id))
    if missing:
        print(f"Unknown source ids: {missing}")
        return 1
    out = []
    for i, (qid, text) in enumerate(PARAPHRASES.items(), start=1):
        r = dict(by_id[qid])
        r.update(id=f"B{i:03d}", question=text, status="drafted",
                 notes=f"paraphrase of {qid}; no version, page or clause hints")
        out.append(r)
    n = len(out)
    for j, text in enumerate(NEAR_MISS, start=1):
        out.append({"id": f"B{n + j:03d}", "type": "unanswerable", "question": text,
                    "doc_id": "", "page": "", "gold_answer": "not in the documents",
                    "evidence_text": "", "doc_id_2": "", "page_2": "", "answerable": "no",
                    "status": "drafted", "notes": "near-miss; confirm absence in the PDFs"})
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(out)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(out)} questions "
          f"({n} answerable paraphrases, {len(NEAR_MISS)} near-miss unanswerable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
