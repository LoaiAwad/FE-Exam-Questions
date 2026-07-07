"""
FE Exam Tutor - Web Interface (Streamlit)
-------------------------------------------
Web version of the terminal tutor. Loads fe_bank.json, lets the student
pick a topic and question count, then walks through questions one at a
time with grading (multiple-choice checked directly, open-ended graded
by Claude).

Run locally with:
    streamlit run streamlit_app.py

Deploy for free at https://streamlit.io/cloud (see README for steps).
"""

import json
import random
import streamlit as st
import anthropic

st.set_page_config(page_title="FE Exam Questions", page_icon="📘", layout="centered")

BANK_FILE = "fe_bank.json"


@st.cache_data
def load_questions():
    with open(BANK_FILE, encoding="utf-8") as f:
        topics = json.load(f)
    flat = []
    for t in topics.values():
        flat.extend(t["questions"])
    return flat, list(topics.keys())


def get_client():
    # On Streamlit Cloud, set ANTHROPIC_API_KEY under Settings -> Secrets.
    # Locally, it reads from the environment variable as before.
    api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
    if api_key:
        return anthropic.Anthropic(api_key=api_key)
    return anthropic.Anthropic()  # falls back to env var


def grade_answer(q, student_answer):
    """Correct/Wrong grading -- multiple-choice checked directly, open-ended
    graded by Claude. Mirrors the logic in fe_tutor.py."""
    if q["type"] == "multiple_choice":
        given_letter = student_answer.strip().upper()[:1]
        correct = given_letter == q["answer"]
        feedback = f"Correct answer: ({q['answer']}) {q['options'].get(q['answer'], '')}"
        return correct, feedback

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

    client = get_client()
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


# ---------- Session state setup ----------
if "stage" not in st.session_state:
    st.session_state.stage = "setup"       # setup -> quiz -> done
    st.session_state.questions = []
    st.session_state.current_idx = 0
    st.session_state.score = 0
    st.session_state.answered = False
    st.session_state.last_feedback = None
    st.session_state.last_correct = None

all_questions, topic_names = load_questions()

st.title("📘 FE Exam Questions")

# ---------- Setup stage ----------
if st.session_state.stage == "setup":
    st.write("Practice FE exam questions, graded instantly.")

    topic_choice = st.selectbox("Choose a topic", ["All topics"] + topic_names)
    pool = all_questions if topic_choice == "All topics" else [
        q for q in all_questions if q["topic"] == topic_choice
    ]

    max_q = len(pool)
    num_questions = st.number_input(
        "How many questions?", min_value=1, max_value=max_q, value=min(5, max_q)
    )

    if st.button("Start practice session", type="primary"):
        st.session_state.questions = random.sample(pool, int(num_questions))
        st.session_state.current_idx = 0
        st.session_state.score = 0
        st.session_state.stage = "quiz"
        st.session_state.answered = False
        st.rerun()

# ---------- Quiz stage ----------
elif st.session_state.stage == "quiz":
    idx = st.session_state.current_idx
    questions = st.session_state.questions
    q = questions[idx]

    st.progress((idx) / len(questions))
    st.subheader(f"Question {idx + 1} of {len(questions)}")
    st.write(q["prompt"])

    if q["type"] == "multiple_choice":
        letters = [l for l in ["A", "B", "C", "D", "E"] if l in q["options"]]
        labels = [f"({l}) {q['options'][l]}" for l in letters]
        choice_label = st.radio("Your answer:", labels, index=None, key=f"radio_{idx}")
        student_answer = None
        if choice_label:
            student_answer = choice_label[1]  # the letter
    else:
        student_answer = st.text_area("Your answer:", key=f"text_{idx}")

    col1, col2 = st.columns([1, 1])

    if not st.session_state.answered:
        if col1.button("Submit answer", type="primary"):
            if not student_answer:
                st.warning("Please choose or type an answer first.")
            else:
                with st.spinner("Grading..."):
                    correct, feedback = grade_answer(q, student_answer)
                st.session_state.answered = True
                st.session_state.last_correct = correct
                st.session_state.last_feedback = feedback
                if correct:
                    st.session_state.score += 1
                st.rerun()
        if col2.button("Exit"):
            st.session_state.questions = st.session_state.questions[:idx]
            st.session_state.stage = "done"
            st.rerun()
    else:
        if st.session_state.last_correct:
            st.success("✅ Correct!")
        else:
            st.error("❌ Wrong.")
        st.info(st.session_state.last_feedback)

        button_label = "Next question" if idx + 1 < len(questions) else "See results"
        if col1.button(button_label, type="primary"):
            st.session_state.answered = False
            if idx + 1 < len(questions):
                st.session_state.current_idx += 1
            else:
                st.session_state.stage = "done"
            st.rerun()
        if col2.button("Exit"):
            st.session_state.stage = "done"
            st.rerun()

# ---------- Done stage ----------
elif st.session_state.stage == "done":
    total = len(st.session_state.questions)
    score = st.session_state.score

    if total == 0:
        st.info("You exited before answering any questions -- no score to show.")
    else:
        pct = round(100 * score / total)
        st.balloons()
        st.success("🎉 Congratulations, you completed the session!")
        st.metric("Score", f"{score} / {total} correct", f"{pct}%")

    if st.button("Start a new session"):
        st.session_state.stage = "setup"
        st.rerun()
