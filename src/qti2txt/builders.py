"""Quiz building utilities for creating text output."""

import re
import urllib.parse
import logging

logger = logging.getLogger(__name__)


class QuizBuilder:
    """
    Class that takes data from the quiz title and description and the questions and creates the quiz
    """

    def __init__(self, tag_values, question_details, output_dir):
        self.tag_values = tag_values
        self.question_details = question_details
        self.output_dir = output_dir

    # First, we will write the Title, Header, and Options to a .txt file
    def get_quiz_filename(self):
        if "title" in self.tag_values:
            quiz_title = self.output_dir / f"{self.tag_values['title']}".strip()
            quiz_file_name = f"{quiz_title}.txt"
            return quiz_file_name
        else:
            logger.warning(
                "The quiz needs a title so your quiz will receive a default title."
            )
            return "untitled_quiz.txt"

    def create_quiz_header(self):
        if "title" in self.tag_values:
            quiz_file_name = self.get_quiz_filename()  # returns default title if None
            with open(quiz_file_name, "w", encoding="utf-8") as f:
                f.write(f"Quiz title: {self.tag_values['title']}\n")
                f.write(f"Quiz description: {self.tag_values['description']}\n")
                f.write(f"shuffle answers: {self.tag_values['shuffle_answers']}\n")
                f.write(
                    f"show correct answers: {self.tag_values['show_correct_answers']}\n"
                )
                # TODO: Need to add if clause since one depends on the other
                # f.write(f"one question at a time: {tag_values['one_question_at_a_time']}\n")
                # f.write(f"can't go back: {tag_values['cant_go_back']}\n\n")

    # Next, let's feed in the questions
    def create_quiz_questions(self):
        quiz_file_name = self.get_quiz_filename()  # returns default title if None
        with open(quiz_file_name, "a", encoding="utf-8", newline="") as f:
            for question in self.question_details:
                f.write(f"\n1. {question['question_text']}\n")

                if question["question_type"] in (
                    "true_false_question",
                    "multiple_choice_question",
                ):
                    choice_counter = 0
                    for choice in question["choices"]:
                        choice_letter = chr(97 + choice_counter)
                        # Check if it is correct using ident number and write to file
                        if choice["ident"] in question["correct_choices"]:
                            f.write(f"*{choice_letter}) {choice['text']}\n")
                        else:
                            f.write(f"{choice_letter}) {choice['text']}\n")
                        choice_counter += 1
                        # Multi-select question

                elif question["question_type"] == "multiple_answers_question":
                    for choice in question["choices"]:
                        if choice["ident"] in question["correct_choices"]:
                            f.write(f"[*] {choice['text']}\n")
                        else:
                            f.write(f"[] {choice['text']}\n")
                elif question["question_type"] == "short_answer_question":
                    for answer in question["correct_answers"]:
                        f.write(f"* {answer}\n")
                elif question["question_type"] == "numerical_question":
                    for answers in question["correct_answers"]:
                        if "exact" in answers and answers.get("margin", 0.0) == 0.0:
                            f.write(f"= {answers['exact']}\n")
                        elif "exact" in answers and answers.get("margin", 0.0) != 0.0:
                            f.write(f"= {answers['exact']} +- {answers['margin']}\n")
                        elif "range" in answers:
                            f.write(f"= {answers['range']}\n")

                elif question["question_type"] == "matching_question":
                    for answer in question["correct_answers"]:
                        f.write("m. " + answer + "\n")

                elif question["question_type"] == "essay_question":
                    f.write("____\n")

                elif question["question_type"] == "file_upload_question":
                    f.write("^^^^\n")

                elif question["question_type"] == "text_only_question":
                    f.write("\n")

                elif question["question_type"] == "fill_in_multiple_blanks_question":
                    for blank_label, answers in question[
                        "multiple_blanks_answers"
                    ].items():
                        f.write(f"* {blank_label}: ")
                        if isinstance(answers, list):
                            f.write("".join(str(ans) for ans in answers))
                        else:
                            f.write(str(answers))
                        f.write("\n")
                    pass
                if question["feedback_general"] is not None:
                    f.write(f"... {question["feedback_general"]}\n")

    def convert_latex_format(self):
        """Convert Canvas LaTeX image format to dollar sign LaTeX format."""
        # TODO: This isn't ideal since I'm fixing the file after it is created. Better to do this on specific chunks that would have Latex before writing it.

        quiz_file_name = self.get_quiz_filename()

        try:
            # Read the file
            with open(quiz_file_name, "r", encoding="utf-8") as f:
                content = f.read()

            # Pattern to match ![LaTeX: \\frac{m}{s^2}](url1)
            latex_pattern = r"!\[LaTeX:\s*([^\]]+)\]\([^)]+\)"

            def replace_latex(match):
                latex_code = match.group(1)
                # URL decode the LaTeX (Canvas uses double encoding)
                latex_code = urllib.parse.unquote(latex_code)
                latex_code = urllib.parse.unquote(latex_code)
                # Fix double \\
                latex_code = latex_code.replace("\\\\", "\\")
                return f"${latex_code}$"

            # Replace all LaTeX matches
            updated_content = re.sub(latex_pattern, replace_latex, content)

            # Only rewrite if changes were made
            if updated_content != content:
                with open(quiz_file_name, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                logger.info(f"Converted LaTeX formatting in {quiz_file_name}")

        except Exception as e:
            logger.error(f"Error converting LaTeX format: {e}")
