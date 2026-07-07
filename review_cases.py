"""
Prints each eval test case together with its full question text and
reference solution, so you can review the ground-truth labels easily.

Usage:
    python review_cases.py
"""

import json

with open("fe_bank.json", encoding="utf-8") as f:
    topics = json.load(f)

questions_by_id = {}
for t in topics.values():
    for q in t["questions"]:
        questions_by_id[q["id"]] = q

with open("test_cases.json", encoding="utf-8") as f:
    test_cases = json.load(f)

for i, case in enumerate(test_cases, start=1):
    q = questions_by_id.get(case["id"])
    print("=" * 70)
    print(f"[{i}/{len(test_cases)}]  {case['id']}")
    print("=" * 70)
    if q:
        print("QUESTION:", q["prompt"])
        print("\nREFERENCE SOLUTION:", q["solution"])
    else:
        print("(question not found in fe_bank.json)")
    print(f"\nSTUDENT ANSWER: {case['student_answer']}")
    print(f"PROPOSED SCORE: {case['expected_score']} (1.0=full, 0.5=half, 0.0=none)")
    print(f"NOTE: {case['note']}")
    print()
