# QTI2TEXT

This project processes QTI (Question and Test Interoperability) quiz data. It strips namespaces from XML files, parses the data, and generates quiz questions in a .txt format that is compatible for converting back into a QTI file using [text2qti](https://github.com/gpoore/text2qti). I created it because I needed to pull quiz questions from a CANVAS quiz so I could edit them as plaintext files, add additional questions, and then use text2qti to reupload a new quiz. The code is a mess but it might be helpful if you are in a bind.

## Use

To use, run the `run.py` script in the terminal, enter the file path of the QTI export (this will be a `.zip` file). The program will output three files: a `.csv` file and a `.txt` file. Optionally, you can uncomment the `convert_to_qti()` function to turn it back into a QTI file. This is useful for debugging.

## Features

- Strips namespaces from XML files.
- Parses QTI quiz data for a limited number of question types: Multiple-Choice, True/False (as a Multiple-Choice question), and Multi-Answer questions.
- Generates quiz questions in a text format.

## TODO

- Support for other question types
- Simple flet GUI

## Requirements

- Python 3.x
- `defusedxml` for XML parsing.
