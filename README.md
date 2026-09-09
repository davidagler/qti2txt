# QTI2TEXT

[<img src="https://badges.ws/pypi/v/qti2txt"/>](https://github.com/davidagler/qti2txt)
[<img src="https://badges.ws/github/last-commit/davidagler/qti2txt"/>](https://github.com/davidagler/qti2txt)
[<img src="https://badges.ws/github/l/davidagler/qti2txt"/>](https://github.com/davidagler/qti2txt)
[<img src="https://badges.ws/github/lang/davidagler/qti2txt"/>](https://github.com/davidagler/qti2txt)

qti2txt converts quizzes exported from [Canvas](https://www.instructure.com/canvas) in [QTI-format](https://en.wikipedia.org/wiki/QTI) (version 1.2) into plaintext files. This is useful if you want ownership over your quizzes, if you are moving them to a different LMS, plan to use them for a paper exam, or edit them and reupload them using [text2qti](https://github.com/gpoore/text2qti).

This project processes QTI (Question and Test Interoperability) quiz data. It strips namespaces from XML files, parses the data, and generates quiz questions in a .txt format that is *mostly* compatible with text2qti.

## Installation

Install **Python 3.13** or greater. You can download it from [python.org](https://www.python.org/).

qti2txt can be installed as follows:

```bash
pip install qti2txt
```

or

```bash
python3 -m pip install qti2txt
```

or using `uv`:

```bash
uv add qti2txt
```

## Usage

To use qti2txt, you'll need a `.zip` file in QTI format. You can obtain one by exporting it from CANVAS as follows:

1. Select your course in CANVAS.
1. Click `Settings`
1. Select `Export Course Content`
1. Select `Quiz`
1. Select the quizzes you want to export.
1. Click `Create Export`

Canvas will now export a `.zip` file containing the XML data (you may need to refresh your browser). Now that you have your `.zip` file.

In the terminal:

```bash
qti2txt -f YOUR_QTI_FILEPATH_HERE.zip 
```

Other command-line options include:

- `-o` or `--output`: specifies the output directory for the quiz files
- `-kxml` or `--keeptmpxml`: keeps the temporary xml files created in the process of creating the quiz. The default is to try to delete these files.
- `-v` or `verbose`: verbose logging

Some basic recipes.

Quizzes and csv file are saved to a folder titled `output`:

```bash
qti2txt -f YOUR_QTI_FILE_HERE.zip -o output

```

Quizzes, a csv file, and temporary .xml files are saved to a folder titled `output`, verbose logging is on:

```bash
qti2txt -f YOUR_QTI_FILE_HERE.zip -o output -v -kxml

```

## Features

- Strips namespaces from XML files.
- Generates quiz questions in a text format.
- Extracts resources (e.g., imgs, gifs, etc.) from quizzes.
- Replaces Wiris/Canvas data-mathml image tags (not raw mathml) with inline LaTeX.
- Parses QTI quiz data for a limited number of question types:

  - ✅ Multiple-Choice
  - ✅ True/False (as a Multiple-Choice question)
  - ✅ Fill-in-the-blank (processed as a short-answer question)
  - ✅ Fill-in-multiple-blanks (note: not used in text2qti)
  - ✅ Multi-Answer questions
  - 🟡 Matching. Complete w/o distractors
  - 🚧 Multiple dropdowns
  - 🟡 Numerical Answer. Partial functionality: Exact Answer, Range, Exact Answer with margin of error.
  - ❌ Formula question
  - ✅ Essay
  - ✅ File upload_question
  - ✅ Text only question
  - ✅ Incorporate LaTeX
  - 🟡 Feedback on Question. Presently, there is only General feedback on the question. There is no question-specific feedback or feedback if Correct or feedback if Incorrect.

## Requirements

- Python 3.x
- `defusedxml` for XML parsing.
- `html2text`
- `mathml-to-latex>=1.0.0`

## Resources

1. [Get Marked](https://digitaliser.getmarked.ai/docs/) - API for converting docx, QTI, and Moodle XML quiz file into simplified JSON
1. [text2qti](https://github.com/gpoore/text2qti)