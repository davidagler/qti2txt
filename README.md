# QTI2TEXT

This project processes QTI (Question and Test Interoperability) quiz data. It strips namespaces from XML files, parses the data, and generates quiz questions in a .txt format that is compatible for converting back into a QTI file using [text2qti](https://github.com/gpoore/text2qti). I created it because I needed to pull quiz questions from a CANVAS quiz so I could edit them as plaintext files and then add additional questions. The code is a mess but it might be helpful if you are in a bind.

## Use

To use, copy the code, from a QTI file add the folder with two files in it (one of which will be `assessment_meta.xml`), run the `run.py` script in the terminal, enter the file path of the folder. It should output quiz.txt and question_details.csv files. In addition, you can uncomment `convert_to_qti()` function to test whether the quiz converts back into a QTI file.

## Features

- Strips namespaces from XML files.
- Parses QTI quiz data for a limited number of question types: Multiple-Choice, True/False (as a Multiple-Choice question), and Multi-Answer questions.
- Generates quiz questions in a text format.

## TODO

- Support for other question types
- Intake of entire QTI .zip, not just a folder from the .zip file

## Requirements

- Python 3.x
- `defusedxml` for XML parsing.
