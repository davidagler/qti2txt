import html2text
import re


# Clean up HTML
def html_to_cleantext(html_text):
    if html_text is None:
        return ""
    if not isinstance(html_text, str):
        html_text = str(html_text)

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    h.single_line_break = True
    clean_text = h.handle(html_text)  # convert
    if clean_text is None:
        return ""
    clean_text = re.sub(r"\s+", " ", clean_text)  # remove extra spaces
    return clean_text


# Renumber text file
def renumber_file(file_path):
    with open(file_path, "r") as file:
        lines = file.readlines()

    new_lines = []
    question_number = 1

    for line in lines:
        # Match lines that start with a number followed by a period and a space
        if re.match(r"^\d+\.\s", line):
            new_line = re.sub(r"^\d+\.\s", f"{question_number}. ", line)
            new_lines.append(new_line)
            question_number += 1
        else:
            new_lines.append(line)

    with open(file_path, "w") as file:
        file.writelines(new_lines)
