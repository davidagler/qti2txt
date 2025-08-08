# QTI2TEXT

This project processes QTI (Question and Test Interoperability) quiz data. It strips namespaces from XML files, parses the data, and generates quiz questions in a .txt format that is compatible for converting back into a QTI file using [text2qti](https://github.com/gpoore/text2qti). I created it because I needed to pull quiz questions from a CANVAS quiz so I could edit them as plaintext files, add additional questions, and then either (1) use text2qti to reupload a new quiz or (2) use questions in classroom exams / quizzes.

The code is a mess but it might be helpful if you are in a bind.

## Use

To use, run the `run.py` script in the terminal, enter the file path of the QTI export (this will be a `.zip` file). The program will output three files: a `.csv` file and a `.txt` file. Optionally, you can uncomment the `convert_to_qti()` function to turn it back into a QTI file. This is useful for debugging.

## Features

- Strips namespaces from XML files.
- Parses QTI quiz data for a limited number of question types:

  - Multiple-Choice
  - True/False (as a Multiple-Choice question)
  - Multi-Answer questions
  - Essay (as of 8/8/25)
  - Short-answer (as of 8/8/25)
  - fill-in-blank (processed as a short-answer question)
  - Fill in Multiple Blanks (note: not used in text2qti)

- Generates quiz questions in a text format.

## TODO

Support for other question types:


- Numerical Answer

## Requirements

- Python 3.x
- `defusedxml` for XML parsing.
- `html2text`
