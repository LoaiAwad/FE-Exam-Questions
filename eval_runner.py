"""
Eval harness for the FE tutor's open-ended grading.
------------------------------------------------------
Runs each test case in test_cases.json through the tutor's grading logic
(grade_open_ended, imported from fe_tutor.py) and compares it against the
human-labeled ground truth. Reports overall accuracy, plus a breakdown of
false positives (tutor said correct, human says wrong -- the risky kind)
and false negatives (tutor said wrong, human says correct).

Usage:
    python eval_runner.py
(Run this in the same folder as fe_bank.json, test_cases.json, and fe_tutor.py)
"""

import json
from fe_tutor import grade_open_ended

with open("fe_bank.json", encoding="utf-8") as f:
    topics = json.load(f)

# flatten to a lookup by id
questions_by_id = {}
for t in topics.values():
    for q in t["questions"]:
        questions_by_id[q["id"]] = q

with open("test_cases.json", encoding="utf-8") as f:
    test_cases = json.load(f)

results = []

for case in test_cases:
    q = questions_by_id.get(case["id"])
    if not q:
        print(f"WARNING: question {case['id']} not found in fe_bank.json, skipping")
        continue

    predicted_score, feedback = grade_open_ended(q, case["student_answer"])
    expected_score = case["expected_score"]
    match = predicted_score == expected_score

    results.append({
        "id": case["id"],
        "expected": expected_score,
        "predicted": predicted_score,
        "match": match,
        "tutor_feedback": feedback,
        "note": case.get("note", ""),
    })

# Summary
total = len(results)
exact_matches = sum(1 for r in results if r["match"])
over_graded = [r for r in results if r["predicted"] > r["expected"]]   # tutor too generous
under_graded = [r for r in results if r["predicted"] < r["expected"]]  # tutor too harsh

print(f"\n{'=' * 50}")
print(f"EVAL RESULTS: {exact_matches}/{total} exact matches with human judgment ({round(100*exact_matches/total)}%)")
print(f"{'=' * 50}\n")

print(f"Over-graded (tutor gave MORE credit than deserved -- the risky kind): {len(over_graded)}")
for r in over_graded:
    print(f"  - {r['id']}: expected {r['expected']}, got {r['predicted']}")
    print(f"    Note: {r['note']}")
    print(f"    Tutor feedback: {r['tutor_feedback']}")

print(f"\nUnder-graded (tutor gave LESS credit than deserved): {len(under_graded)}")
for r in under_graded:
    print(f"  - {r['id']}: expected {r['expected']}, got {r['predicted']}")
    print(f"    Note: {r['note']}")
    print(f"    Tutor feedback: {r['tutor_feedback']}")

with open("eval_report.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nFull results saved to eval_report.json")
