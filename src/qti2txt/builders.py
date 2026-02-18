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
                description = (self.tag_values.get("description") or "").strip()
                if description:
                    f.write(f"Quiz description: {description}\n")
                f.write(
                    f"shuffle answers: {self.tag_values.get('shuffle_answers', 'false')}\n"
                )
                f.write(
                    "show correct answers: "
                    f"{self.tag_values.get('show_correct_answers', 'false')}\n"
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
                            exact = answers["exact"]
                            if self.is_effectively_integer(exact):
                                f.write(f"= {int(float(exact))}\n")
                            else:
                                f.write(f"= {self.format_number(exact)} +- 0\n")
                        elif "exact" in answers and answers.get("margin", 0.0) != 0.0:
                            f.write(
                                "= "
                                f"{self.format_number(answers['exact'])} +- "
                                f"{self.format_number(answers['margin'])}\n"
                            )
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

    @staticmethod
    def normalize_canvas_filebase_links(content):
        """
        Convert Canvas IMS filebase links to local paths for text2qti.
        Example:
        ($IMS-CC-FILEBASE$/Images/foo.png?canvas_download=1)
        -> (web_resources/Images/foo.png)
        """
        filebase_pattern = re.compile(
            r"\((?:\$IMS-CC-FILEBASE\$|%24IMS-CC-FILEBASE%24)/([^)]+)\)",
            flags=re.IGNORECASE,
        )

        def replace_filebase_link(match):
            relative_path = match.group(1)
            relative_path = relative_path.split("?", 1)[0]
            relative_path = urllib.parse.unquote(relative_path).lstrip("/")
            if not relative_path.startswith("web_resources/"):
                relative_path = f"web_resources/{relative_path}"
            return f"({relative_path})"

        return filebase_pattern.sub(replace_filebase_link, content)

    @staticmethod
    def sanitize_markdown_links(content):
        """
        Normalize markdown links/images for text2qti:
        - unescape escaped parentheses in URLs
        - drop unresolved html2text placeholder links
        """

        def clean_url(url):
            url = re.sub(r"\\+([()])", r"\1", url).strip()
            if not url.startswith(("http://", "https://")):
                url = url.replace("(", "%28").replace(")", "%29")
            return url

        def replace_image(match):
            alt_text = match.group(1)
            url = clean_url(match.group(2))
            if url.startswith("LINK.PLACEHOLDER_"):
                return alt_text
            return f"![{alt_text}]({url})"

        def replace_link(match):
            link_text = match.group(1)
            url = clean_url(match.group(2))
            if url.startswith("LINK.PLACEHOLDER_"):
                return link_text
            return f"[{link_text}]({url})"

        # Image links first, then normal links.
        image_pattern = r"!\[([^\]]*)\]\(((?:\\.|[^)])+)\)"
        link_pattern = r"(?<!!)\[([^\]]*)\]\(((?:\\.|[^)])+)\)"
        content = re.sub(image_pattern, replace_image, content)
        content = re.sub(link_pattern, replace_link, content)
        return content

    @staticmethod
    def format_number(value):
        """Render numeric values without unnecessary trailing zeros."""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        if number.is_integer():
            return str(int(number))
        return format(number, "g")

    @staticmethod
    def is_effectively_integer(value):
        try:
            return float(value).is_integer()
        except (TypeError, ValueError):
            return False

    def convert_latex_format(self):
        """Convert Canvas LaTeX image format to dollar sign LaTeX format."""
        # TODO: This isn't ideal since I'm fixing the file after it is created. Better to do this on specific chunks that would have Latex before writing it.

        quiz_file_name = self.get_quiz_filename()

        try:
            # Read the file
            with open(quiz_file_name, "r", encoding="utf-8") as f:
                content = f.read()

            # Replace Canvas LaTeX image markdown with inline $...$.
            updated_content = self.replace_canvas_latex_images(content)
            updated_content = self.normalize_canvas_filebase_links(updated_content)
            updated_content = self.sanitize_markdown_links(updated_content)

            # Only rewrite if changes were made
            if updated_content != content:
                with open(quiz_file_name, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                logger.info(
                    f"Normalized Canvas links/LaTeX formatting in {quiz_file_name}"
                )

        except Exception as e:
            logger.error(f"Error converting LaTeX format: {e}")

    @staticmethod
    def replace_canvas_latex_images(content):
        """
        Convert Canvas equation-image markdown entries to inline LaTeX.
        Handles URLs with nested/escaped parentheses that regex-based matching
        can truncate.
        """
        marker = "![LaTeX:"
        output = []
        idx = 0
        content_len = len(content)

        while True:
            start = content.find(marker, idx)
            if start == -1:
                output.append(content[idx:])
                break

            output.append(content[idx:start])
            cursor = start + len(marker)

            while cursor < content_len and content[cursor].isspace():
                cursor += 1

            alt_chars = []
            while cursor < content_len:
                char = content[cursor]
                if char == "\\" and cursor + 1 < content_len:
                    alt_chars.append(char)
                    cursor += 1
                    alt_chars.append(content[cursor])
                    cursor += 1
                    continue
                if char == "]" and cursor + 1 < content_len and content[cursor + 1] == "(":
                    cursor += 2  # consume "]("
                    break
                alt_chars.append(char)
                cursor += 1
            else:
                output.append(content[start:])
                break

            # Canvas equation image URLs can contain literal ')' before query
            # args (e.g., "...)?scale=1)"). Use a delimiter-based close test.
            found_close = False
            while cursor < content_len:
                char = content[cursor]
                if char == "\\" and cursor + 1 < content_len:
                    cursor += 2
                    continue
                if char == ")":
                    next_char = content[cursor + 1] if cursor + 1 < content_len else ""
                    if (
                        not next_char
                        or next_char.isspace()
                        or next_char in ".,;:!"
                    ):
                        cursor += 1
                        found_close = True
                        break
                cursor += 1

            if not found_close:
                output.append(content[start:])
                break

            latex_code = "".join(alt_chars).strip()
            latex_code = urllib.parse.unquote(latex_code)
            latex_code = urllib.parse.unquote(latex_code)
            latex_code = latex_code.replace("\\\\", "\\")
            output.append(f"${latex_code}$")
            idx = cursor

        return "".join(output)
