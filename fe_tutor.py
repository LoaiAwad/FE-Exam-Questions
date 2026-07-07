"""
FE Exam Tutor - v1
-------------------
Loads the question bank (fe_bank.json), quizzes the student, grades answers
(multiple-choice directly, open-ended via Claude), and shows a final score.

Usage:
    python fe_tutor.py
"""

import json
import random
import sys
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

BANK_FILE = "fe_bank.json"


def load_questions():
    with open(BANK_FILE, encoding="utf-8") as f:
        topics = json.load(f)

    flat = []
    for topic_name, t in topics.items():
        for q in t["questions"]:
            flat.append(q)
    return flat, list(topics.keys())


def choose_topic(topic_names):
    print("\nAvailable topics:")
    print("  0. All topics")
    for i, name in enumerate(topic_names, start=1):
        print(f"  {i}. {name}")

    while True:
        choice = input("\nPick a topic number: ").strip()
        if choice == "0":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(topic_names):
            return topic_names[int(choice) - 1]
        print("Please enter a valid number.")


def ask_count(max_available):
    while True:
        raw = input(f"\nHow many questions do you want to attempt (1-{max_available})? ").strip()
        if raw.isdigit() and 1 <= int(raw) <= max_available:
            return int(raw)
        print("Please enter a valid number.")


def print_question(q, idx, total):
    print(f"\n--- Question {idx}/{total} [{q['id']}] ---")
    print(q["prompt"])
    if q["type"] == "multiple_choice":
        for letter in ["A", "B", "C", "D", "E"]:
            if letter in q["options"]:
                print(f"  ({letter}) {q['options'][letter]}")


def grade_answer(q, student_answer):
    """Grades the student's answer as simply correct or incorrect, with a
    brief explanation. Multiple-choice is checked directly against the known
    answer letter (fast, free, no API call). Open-ended answers are graded
    by Claude against the reference solution."""
    if q["type"] == "multiple_choice":
        # Accept just the letter, or a letter followed by extra reasoning --
        # only the first non-space character is checked.
        given_letter = student_answer.strip().upper()[:1]
        correct = given_letter == q["answer"]
        feedback = f"Correct answer: ({q['answer']}) {q['options'].get(q['answer'], '')}"
        return correct, feedback

    # Open-ended: ask Claude for a straightforward right/wrong judgment
    prompt = f"""You are grading a student's answer to an FE (Fundamentals of
Engineering) exam practice question.

Question: {q['prompt']}

Reference solution/explanation: {q['solution']}

Student's answer: {student_answer}

Decide if the student's final answer is correct (matches the reference
solution's result/conclusion). Minor rounding/wording/notation differences
are fine, and different but mathematically equivalent forms of the same
answer are fine. Do not require the student to show their work -- judge the
final answer only.

Respond with ONLY a JSON object, no other text, in this exact format:
{{"correct": true or false, "feedback": "one short sentence explaining the correct answer"}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(text)
        return bool(result["correct"]), result["feedback"]
    except (json.JSONDecodeError, KeyError, ValueError):
        return False, f"(Could not auto-grade cleanly) Raw response: {text}"


# Kept as an alias so eval_runner.py (which imports grade_open_ended by name)
# continues to work unchanged.
grade_open_ended = grade_answer


def main():
    questions, topic_names = load_questions()

    topic_choice = choose_topic(topic_names)
    if topic_choice:
        pool = [q for q in questions if q["topic"] == topic_choice]
    else:
        pool = questions

    if not pool:
        print("No questions found for that topic.")
        sys.exit(1)

    count = ask_count(len(pool))
    session_questions = random.sample(pool, count)

    correct_count = 0

    for idx, q in enumerate(session_questions, start=1):
        print_question(q, idx, count)
        student_answer = input("\nYour answer: ").strip()

        if q["type"] == "open_ended":
            print("(Grading your answer with Claude...)")
        correct, feedback = grade_answer(q, student_answer)

        if correct:
            print("✅ Correct!")
            correct_count += 1
        else:
            print("❌ Wrong.")
        print(feedback)

    # Final summary
    pct = round(100 * correct_count / count)
    print("\n" + "=" * 40)
    print(f"🎉 Congratulations, you completed the session!")
    print(f"Score: {correct_count} / {count} correct ({pct}%)")
    print("=" * 40)


if __name__ == "__main__":
    main()
