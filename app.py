from __future__ import annotations

import json
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


def render_quiz_mode(questions: list[Question]) -> None:
    st.subheader("クイズに挑戦")
    st.caption(f"現在 {len(questions)} 問の問題が登録されています。")

    if not questions:
        st.warning("問題がまだ登録されていません。先に「問題を追加」モードで登録してください。")
        return

    st.info("この画面では登録済み問題を確認できます。クイズの出題ロジックは次の実装で追加しやすい形にしています。")
    for question in questions:
        with st.expander(f"No.{question['id']} {question['question']}"):
            for index, option in enumerate(question["options"], start=1):
                st.write(f"{index}. {option}")
            st.caption(f"正解: {question['answer']}")


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
