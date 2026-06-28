from __future__ import annotations

import json
import random
from pathlib import Path
from typing import TypedDict

import streamlit as st


DATA_FILE = Path(__file__).with_name("quiz_data.json")


class Question(TypedDict):
    id: str
    question: str
    options: list[str]
    answer: str


class QuizData(TypedDict):
    questions: list[Question]


def load_quiz_data(data_file: Path = DATA_FILE) -> QuizData:
    with data_file.open(encoding="utf-8") as file:
        raw_data = json.load(file)

    if not isinstance(raw_data, dict):
        raise ValueError("quiz_data.json must contain a top-level object.")

    questions = raw_data.get("questions")
    if not isinstance(questions, list):
        raise ValueError("quiz_data.json must contain a 'questions' list.")

    validated_questions: list[Question] = []
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            raise ValueError(f"Question {index} must be an object.")

        question_id = question.get("id")
        prompt = question.get("question")
        options = question.get("options")
        answer = question.get("answer")

        if not isinstance(question_id, str) or not question_id.strip():
            raise ValueError(f"Question {index} must have a non-empty string id.")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Question {index} must have a non-empty question.")
        if not isinstance(options, list) or len(options) != 4:
            raise ValueError(f"Question {index} must have exactly four options.")
        if not all(isinstance(option, str) and option.strip() for option in options):
            raise ValueError(f"Question {index} options must all be non-empty strings.")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(f"Question {index} answer must be a non-empty string.")

        normalized_options = [option.strip() for option in options]
        normalized_answer = answer.strip()
        if normalized_answer not in normalized_options:
            raise ValueError(f"Question {index} answer must match one of the options.")

        validated_questions.append(
            {
                "id": question_id.strip(),
                "question": prompt.strip(),
                "options": normalized_options,
                "answer": normalized_answer,
            }
        )

    return {"questions": validated_questions}


def save_quiz_data(quiz_data: QuizData, data_file: Path = DATA_FILE) -> None:
    with data_file.open("w", encoding="utf-8") as file:
        json.dump(quiz_data, file, ensure_ascii=False, indent=2)


def get_next_question_id(questions: list[Question]) -> str:
    numeric_ids: list[int] = []
    for question in questions:
        try:
            numeric_ids.append(int(question["id"]))
        except ValueError:
            continue

    return str(max(numeric_ids, default=0) + 1)


def reset_quiz_session_state(questions: list[Question]) -> None:
    quiz_order = list(range(len(questions)))
    random.shuffle(quiz_order)

    st.session_state["quiz_order"] = quiz_order
    st.session_state["current_index"] = 0
    st.session_state["score"] = 0
    st.session_state["streak"] = 0
    st.session_state["max_streak"] = 0
    st.session_state["answers"] = {}


def initialize_quiz_session_state(questions: list[Question]) -> None:
    quiz_order = st.session_state.get("quiz_order")
    is_valid_order = (
        isinstance(quiz_order, list)
        and len(quiz_order) == len(questions)
        and all(isinstance(index, int) for index in quiz_order)
        and set(quiz_order) == set(range(len(questions)))
    )
    if not is_valid_order:
        reset_quiz_session_state(questions)
        return

    current_index = st.session_state.get("current_index")
    if not isinstance(current_index, int) or current_index < 0 or current_index > len(quiz_order):
        st.session_state["current_index"] = 0

    for key in ("score", "streak", "max_streak"):
        value = st.session_state.get(key)
        if not isinstance(value, int) or value < 0:
            st.session_state[key] = 0

    answers = st.session_state.get("answers")
    if not isinstance(answers, dict):
        st.session_state["answers"] = {}
        return

    valid_question_ids = {question["id"] for question in questions}
    normalized_answers: dict[str, str] = {}
    for question_id, selected_option in answers.items():
        if not isinstance(question_id, str) or not isinstance(selected_option, str):
            continue
        if question_id in valid_question_ids:
            normalized_answers[question_id] = selected_option
    st.session_state["answers"] = normalized_answers


def render_quiz_mode(questions: list[Question]) -> None:
    st.subheader("クイズに挑戦")
    st.caption(f"現在 {len(questions)} 問の問題が登録されています。")

    if not questions:
        st.warning("問題がまだ登録されていません。先に「問題を追加」モードで登録してください。")
        return

    initialize_quiz_session_state(questions)
    quiz_order: list[int] = st.session_state["quiz_order"]
    current_index: int = st.session_state["current_index"]

    if current_index >= len(quiz_order):
        st.success("全問の出題が完了しました。")
        if st.button("もう一度シャッフルして挑戦する"):
            reset_quiz_session_state(questions)
            st.rerun()
        return

    current_question = questions[quiz_order[current_index]]
    st.markdown(f"### 第 {current_index + 1} / {len(quiz_order)} 問")
    st.write(current_question["question"])

    answers: dict[str, str] = st.session_state["answers"]
    selected_option = answers.get(current_question["id"])
    selected_index = (
        current_question["options"].index(selected_option)
        if selected_option in current_question["options"]
        else None
    )
    selected = st.radio(
        "選択肢を選んでください",
        current_question["options"],
        index=selected_index,
        key=f"quiz-option-{current_question['id']}",
    )
    if selected is not None:
        answers[current_question["id"]] = selected
        st.session_state["answers"] = answers

    previous_col, next_col = st.columns(2)
    with previous_col:
        if st.button("前の問題", disabled=current_index == 0):
            st.session_state["current_index"] = max(0, current_index - 1)
            st.rerun()

    with next_col:
        next_label = "結果へ進む" if current_index == len(quiz_order) - 1 else "次の問題"
        if st.button(next_label):
            st.session_state["current_index"] = current_index + 1
            st.rerun()


def render_add_mode(quiz_data: QuizData) -> None:
    st.subheader("問題を追加")
    st.caption("問題文・4つの選択肢・正解を入力して JSON に保存します。")

    with st.form("add-question-form"):
        question_text = st.text_input("問題文")
        options = [st.text_input(f"選択肢 {index}") for index in range(1, 5)]
        answer_index = st.selectbox("正解", options=range(1, 5), format_func=lambda index: f"選択肢 {index}")
        submitted = st.form_submit_button("問題を登録する")

    if not submitted:
        return

    normalized_question = question_text.strip()
    normalized_options = [option.strip() for option in options]
    if not normalized_question:
        st.error("問題文を入力してください。")
        return
    if any(not option for option in normalized_options):
        st.error("4つすべての選択肢を入力してください。")
        return

    new_question: Question = {
        "id": get_next_question_id(quiz_data["questions"]),
        "question": normalized_question,
        "options": normalized_options,
        "answer": normalized_options[answer_index - 1],
    }
    quiz_data["questions"].append(new_question)
    save_quiz_data(quiz_data)

    st.success(f"「{new_question['question']}」を登録しました。")
    st.json(new_question, expanded=False)


def main() -> None:
    st.set_page_config(page_title="テスト対策4択クイズアプリ", page_icon="📝")
    st.title("📝 自分専用！テスト対策4択クイズアプリ")

    quiz_data = load_quiz_data()
    mode = st.sidebar.radio("モードを選択", ("クイズに挑戦", "問題を追加"))

    if mode == "クイズに挑戦":
        render_quiz_mode(quiz_data["questions"])
        return

    render_add_mode(quiz_data)


if __name__ == "__main__":
    main()
