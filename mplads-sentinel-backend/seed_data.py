"""
Seed the database with realistic MPLADS-like works and pre-computed ML outputs.
Run: python seed_data.py
"""
import json
import random
import math
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import engine, Base, SessionLocal
from app.models.work import Work, WorkSimilarity

# ── Reproducible seed ─────────────────────────────────────────────────────────
random.seed(42)

# ── Reference data ────────────────────────────────────────────────────────────
STATES_DATA = [
    ("Uttar Pradesh", [
        ("Lucknow",    "Lucknow",    "Ananya Sharma"),
        ("Kanpur",     "Kanpur",     "Vikram Singh"),
        ("Varanasi",   "Varanasi",   "Priya Mishra"),
        ("Allahabad",  "Allahabad",  "Rajesh Gupta"),
        ("Meerut",     "Meerut",     "Suresh Yadav"),
    ]),
    ("Maharashtra", [
        ("Mumbai North", "Mumbai",   "Deepa Kulkarni"),
        ("Pune",          "Pune",    "Amit Desai"),
        ("Nagpur",        "Nagpur",  "Nisha Patil"),
    ]),
    ("Bihar", [
        ("Patna",      "Patna",      "Sanjay Kumar"),
        ("Gaya",       "Gaya",       "Meena Devi"),
        ("Muzaffarpur","Muzaffarpur","Ravi Shankar"),
    ]),
    ("Madhya Pradesh", [
        ("Bhopal",     "Bhopal",     "Kiran Verma"),
        ("Indore",     "Indore",     "Ramesh Chouhan"),
        ("Gwalior",    "Gwalior",    "Sunita Tiwari"),
    ]),
    ("Karnataka", [
        ("Bengaluru North", "Bengaluru", "Arjun Reddy"),
        ("Mysuru",           "Mysuru",   "Lakshmi Rao"),
    ]),
    ("Delhi", [
        ("New Delhi",  "New Delhi",  "Pankaj Joshi"),
        ("North Delhi","New Delhi",  "Seema Kapoor"),
    ]),
    ("Rajasthan", [
        ("Jaipur",     "Jaipur",     "Mohan Sharma"),
        ("Jodhpur",    "Jodhpur",    "Kavita Bhatt"),
    ]),
]

CATEGORIES = [
    "Road / Bridge Construction",
    "School Building",
    "Primary Health Centre",
    "Community Hall",
    "Water Supply / Borewell",
    "Sports Complex",
    "Library Construction",
    "Irrigation Canal",
    "Drainage / Sanitation",
    "Cremation Ground Development",
]

AGENCIES = [
    "District Panchayat", "Municipal Corporation", "PWD", "Jal Nigam",
    "Education Dept.", "Health Dept.", "Rural Engineering Dept.",
    "DRDA", "Nagar Palika", "Block Development Office",
]

STATUSES = ["In Progress", "Completed", "Delayed", "Stalled", "Under Tendering"]

HOUSES = ["Lok Sabha"] * 8 + ["Rajya Sabha"] * 2   # 80% Lok Sabha


def work_name(category, district):
    templates = {
        "Road / Bridge Construction": [
            f"Construction of Road in {district}",
            f"Four-Lane Road Upgrade — {district}",
            f"Village Connectivity Bridge, {district}",
        ],
        "School Building": [
            f"Government School Building, {district}",
            f"Primary School Renovation — {district}",
            f"Multi-Purpose School Block, {district}",
        ],
        "Primary Health Centre": [
            f"PHC Construction — {district}",
            f"Rural Health Sub-Centre, {district}",
        ],
        "Community Hall": [
            f"Gram Panchayat Community Hall, {district}",
            f"Multi-Purpose Community Centre — {district}",
        ],
        "Water Supply / Borewell": [
            f"Community Water Facility, {district}",
            f"Drinking Water Borewell — {district}",
            f"Overhead Water Tank, {district}",
        ],
        "Sports Complex": [f"Sports Complex Development — {district}"],
        "Library Construction": [f"Public Library Construction, {district}"],
        "Irrigation Canal": [f"Minor Irrigation Canal, {district}"],
        "Drainage / Sanitation": [f"Storm Drainage Improvement, {district}"],
        "Cremation Ground Development": [f"Cremation Ground Development — {district}"],
    }
    opts = templates.get(category, [f"{category} work, {district}"])
    return random.choice(opts)


def compute_risk(sanctioned, expenditure, progress, status, expected_pct):
    """Simple risk scoring logic — mimics what an ML model would produce."""
    score = 0
    indicators = []

    # 1. Cost deviation
    if sanctioned and sanctioned > 0 and expenditure is not None:
        dev = (expenditure - sanctioned) / sanctioned * 100
        if abs(dev) >= 40:
            cost_score = min(int(abs(dev) * 1.2), 100)
            indicators.append({"name": "Cost Deviation", "level": "High", "score": cost_score,
                                "description": f"Expenditure deviates {dev:+.1f}% from sanctioned amount"})
            score += 40
        elif abs(dev) >= 20:
            cost_score = min(int(abs(dev) * 0.8), 70)
            indicators.append({"name": "Cost Deviation", "level": "Medium", "score": cost_score,
                                "description": f"Expenditure deviates {dev:+.1f}% from sanctioned amount"})
            score += 20

    # 2. Progress delay
    if progress is not None and expected_pct is not None:
        delay = expected_pct - progress
        if delay >= 40:
            prog_score = min(int(delay * 1.5), 100)
            indicators.append({"name": "Progress Delay", "level": "High", "score": prog_score,
                                "description": f"Work is {delay:.0f}% behind expected progress"})
            score += 35
        elif delay >= 20:
            prog_score = min(int(delay * 1.0), 70)
            indicators.append({"name": "Progress Delay", "level": "Medium", "score": prog_score,
                                "description": f"Work is {delay:.0f}% behind expected progress"})
            score += 15

    # 3. Stalled status
    if status == "Stalled":
        indicators.append({"name": "Work Stalled", "level": "High", "score": 85,
                            "description": "Work has been recorded as stalled with no recent progress"})
        score += 25

    # 4. Similarity concern (probabilistic for seed data)
    if random.random() < 0.25:
        sim_score = random.randint(55, 80)
        indicators.append({"name": "Potential Similarity", "level": "Medium", "score": sim_score,
                            "description": "Semantic similarity to other recorded works detected"})
        score += 10

    score = min(score + random.randint(-5, 8), 100)
    score = max(score, 0)

    if score >= 70:
        level = "High"
        risk_status = "Requires Review"
    elif score >= 40:
        level = "Medium"
        risk_status = "Monitor Closely"
    else:
        level = "Low"
        risk_status = "Normal"

    # Isolation Forest anomaly score (lower = more anomalous; normal > -0.1)
    # Works with high risk get lower (more anomalous) IF scores
    if score >= 70:
        anomaly_score = round(-0.15 - random.uniform(0, 0.25), 4)
        is_anomaly = True
    elif score >= 50:
        anomaly_score = round(-0.05 - random.uniform(0, 0.1), 4)
        is_anomaly = random.random() < 0.4
    else:
        anomaly_score = round(0.05 + random.uniform(0, 0.15), 4)
        is_anomaly = False

    return score, level, risk_status, anomaly_score, is_anomaly, indicators


def generate_works() -> list[Work]:
    works = []
    work_num = 100

    for state, constituencies in STATES_DATA:
        for constituency, district, mp_name in constituencies:
            n_works = random.randint(3, 6)
            for _ in range(n_works):
                work_num += 1
                work_id = f"MPL-2026-{work_num:05d}"
                category = random.choice(CATEGORIES)
                house = random.choice(HOUSES)
                status = random.choices(
                    STATUSES, weights=[35, 30, 20, 10, 5], k=1
                )[0]
                progress = random.randint(0, 100)

                # Financial (in INR lakhs)
                sanctioned = round(random.uniform(10, 50), 2)
                # Expenditure — sometimes over/under
                exp_factor = random.choices(
                    [0.5, 0.8, 1.0, 1.1, 1.3, 1.6],
                    weights=[5, 25, 35, 15, 15, 5],
                    k=1,
                )[0]
                expenditure = round(sanctioned * exp_factor, 2)
                recommended = round(sanctioned * random.uniform(0.9, 1.1), 2)

                # Expected completion %
                expected_pct = random.randint(30, 100) if status != "Stalled" else progress + 30

                risk_score, risk_level, risk_status, anomaly_score, is_anomaly, indicators = compute_risk(
                    sanctioned, expenditure, progress, status, expected_pct
                )

                proposed = f"2024-{random.randint(1,12):02d}-01"
                expected = f"2026-{random.randint(1,12):02d}-01"

                w = Work(
                    id=work_id,
                    name=work_name(category, district),
                    description=(
                        f"Development of {category.lower()} infrastructure in {district} constituency "
                        f"under MPLADS scheme (House: {house}). "
                        f"Executing agency: {random.choice(AGENCIES)}."
                    ),
                    house=house,
                    mp_name=mp_name,
                    state=state,
                    constituency=constituency,
                    district=district,
                    category=category,
                    executing_agency=random.choice(AGENCIES),
                    status=status,
                    recommended_amount=recommended,
                    sanctioned_amount=sanctioned,
                    expenditure=expenditure,
                    progress=progress,
                    proposed_date=proposed,
                    expected_completion=expected,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    risk_status=risk_status,
                    anomaly_score=anomaly_score,
                    is_anomaly=is_anomaly,
                    risk_indicators_json=json.dumps(indicators),
                )
                works.append(w)

    # Ensure a few guaranteed high-risk works for demo
    demo_works = [
        Work(
            id="MPL-2026-00125",
            name="Government School Building, Lucknow",
            description="Construction of Government Higher Secondary School building in Lucknow constituency under MPLADS (Lok Sabha). Executing agency: Education Dept.",
            house="Lok Sabha", mp_name="Ananya Sharma", state="Uttar Pradesh",
            constituency="Lucknow", district="Lucknow", category="School Building",
            executing_agency="Education Dept.", status="Delayed",
            recommended_amount=45.0, sanctioned_amount=44.5, expenditure=71.5,
            progress=38, proposed_date="2024-03-01", expected_completion="2025-12-01",
            risk_score=82, risk_level="High", risk_status="Requires Review",
            anomaly_score=-0.312, is_anomaly=True,
            risk_indicators_json=json.dumps([
                {"name": "Cost Deviation", "level": "High", "score": 91,
                 "description": "Expenditure exceeds sanctioned amount by 60.7%"},
                {"name": "Progress Delay", "level": "Medium", "score": 67,
                 "description": "Work is 42% behind expected progress timeline"},
                {"name": "Potential Similarity", "level": "Medium", "score": 63,
                 "description": "Semantic similarity detected with MPL-2026-00128"},
            ]),
        ),
        Work(
            id="MPL-2026-00128",
            name="Public Library Construction, Kanpur",
            description="Construction of a modern public library facility in Kanpur. Executing agency: Municipal Corporation.",
            house="Lok Sabha", mp_name="Vikram Singh", state="Uttar Pradesh",
            constituency="Kanpur", district="Kanpur", category="Library Construction",
            executing_agency="Municipal Corporation", status="Stalled",
            recommended_amount=32.0, sanctioned_amount=30.0, expenditure=14.5,
            progress=22, proposed_date="2024-06-01", expected_completion="2026-03-01",
            risk_score=76, risk_level="High", risk_status="Requires Review",
            anomaly_score=-0.267, is_anomaly=True,
            risk_indicators_json=json.dumps([
                {"name": "Progress Delay", "level": "High", "score": 84,
                 "description": "Work is stalled at 22% with no recent updates"},
                {"name": "Work Stalled", "level": "High", "score": 85,
                 "description": "Work officially marked stalled — no recent progress recorded"},
                {"name": "Cost Deviation", "level": "Medium", "score": 58,
                 "description": "Expenditure is significantly below expected at this stage"},
            ]),
        ),
        Work(
            id="MPL-2026-00127",
            name="Community Water Facility, Meerut",
            description="Construction of community drinking water facility including overhead tank in Meerut. Executing agency: Jal Nigam.",
            house="Lok Sabha", mp_name="Suresh Yadav", state="Uttar Pradesh",
            constituency="Meerut", district="Meerut", category="Water Supply / Borewell",
            executing_agency="Jal Nigam", status="In Progress",
            recommended_amount=28.0, sanctioned_amount=27.5, expenditure=36.8,
            progress=61, proposed_date="2024-09-01", expected_completion="2026-06-01",
            risk_score=61, risk_level="Medium", risk_status="Monitor Closely",
            anomaly_score=-0.091, is_anomaly=False,
            risk_indicators_json=json.dumps([
                {"name": "Cost Deviation", "level": "Medium", "score": 68,
                 "description": "Expenditure exceeds sanctioned by 33.8%"},
                {"name": "Potential Similarity", "level": "Medium", "score": 63,
                 "description": "Similar works detected in the same category and district"},
            ]),
        ),
        Work(
            id="MPL-2026-00131",
            name="Rural Health Centre, Agra",
            description="Construction of Primary Health Centre in rural Agra. Executing agency: Health Dept.",
            house="Lok Sabha", mp_name="Ananya Sharma", state="Uttar Pradesh",
            constituency="Allahabad", district="Agra", category="Primary Health Centre",
            executing_agency="Health Dept.", status="In Progress",
            recommended_amount=38.0, sanctioned_amount=37.0, expenditure=41.5,
            progress=55, proposed_date="2024-01-01", expected_completion="2025-10-01",
            risk_score=54, risk_level="Medium", risk_status="Monitor Closely",
            anomaly_score=-0.045, is_anomaly=False,
            risk_indicators_json=json.dumps([
                {"name": "Cost Deviation", "level": "Medium", "score": 62,
                 "description": "Expenditure is 12.2% above sanctioned amount"},
                {"name": "Progress Delay", "level": "Low", "score": 38,
                 "description": "Minor delay detected relative to expected timeline"},
            ]),
        ),
    ]
    # Remove any generated works with the same IDs
    gen_ids = {w.id for w in demo_works}
    works = [w for w in works if w.id not in gen_ids]
    works.extend(demo_works)
    return works


def compute_similarities(works: list[Work]) -> list[WorkSimilarity]:
    """Simple category + state based similarity for seed data."""
    sims = []
    work_map = {w.id: w for w in works}

    for w in works:
        same_category = [
            o for o in works
            if o.id != w.id and o.category == w.category
        ]
        # Sort by amount proximity
        same_category.sort(key=lambda o: abs((o.sanctioned_amount or 0) - (w.sanctioned_amount or 0)))
        top = same_category[:5]
        for o in top:
            # Compute similarity (0–1): same category baseline + state bonus + amount proximity
            base = 0.55
            if o.state == w.state:
                base += 0.15
            if o.constituency == w.constituency:
                base += 0.10
            # Amount proximity bonus
            max_amt = max(w.sanctioned_amount or 1, o.sanctioned_amount or 1)
            diff = abs((w.sanctioned_amount or 0) - (o.sanctioned_amount or 0))
            amt_sim = 1 - min(diff / max_amt, 1)
            base += amt_sim * 0.15
            base = round(min(base + random.uniform(-0.03, 0.03), 0.98), 3)
            sims.append(WorkSimilarity(work_id=w.id, similar_work_id=o.id, similarity_score=base))

    # Add fixed high-similarity pairs for demo
    extra = [
        ("MPL-2026-00125", "MPL-2026-00128", 0.87),
        ("MPL-2026-00125", "MPL-2026-00131", 0.74),
        ("MPL-2026-00128", "MPL-2026-00127", 0.71),
        ("MPL-2026-00127", "MPL-2026-00131", 0.68),
        ("MPL-2026-00131", "MPL-2026-00125", 0.74),
        ("MPL-2026-00128", "MPL-2026-00125", 0.87),
    ]
    existing = {(s.work_id, s.similar_work_id) for s in sims}
    for wid, sid, score in extra:
        if wid in work_map and sid in work_map and (wid, sid) not in existing:
            sims.append(WorkSimilarity(work_id=wid, similar_work_id=sid, similarity_score=score))
            existing.add((wid, sid))

    return sims


def seed():
    print("Creating tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        print("Generating works...")
        works = generate_works()
        db.add_all(works)
        db.commit()
        print(f"  → {len(works)} works seeded")

        print("Computing similarities...")
        for w in works:
            db.refresh(w)
        sims = compute_similarities(works)
        db.add_all(sims)
        db.commit()
        print(f"  → {len(sims)} similarity records seeded")

        # Print summary
        high = sum(1 for w in works if w.risk_level == "High")
        medium = sum(1 for w in works if w.risk_level == "Medium")
        low = sum(1 for w in works if w.risk_level == "Low")
        print(f"\n✓ Seeding complete: {len(works)} works | High: {high} | Medium: {medium} | Low: {low}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
