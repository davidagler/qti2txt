import xml.etree.ElementTree as ET
from helpers import *
import constants as c
import csv
import subprocess
import os
from pathlib import Path

def get_other_file_from_folder(folder_path):
    """
    Get the name of the other file in the specified folder, excluding the known file.
    """
    folder = Path(folder_path)
    files = [file for file in folder.iterdir() if file.is_file() and file.name != c.QUIZ_HEADER_XML_NAME]

    if len(files) < 1:
        raise ValueError("The folder must contain at least one other file besides the known file.")

    return files[0].name


class NamespaceStripper:
    """AI generated Class to strip namespaces from XML tags."""
    @staticmethod
    def strip_namespace(tag):
        """Remove the namespace from a tag."""
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag

    def remove_namespace_from_file(self, input_file, output_file):
        """Parse the XML, strip namespaces, and write to a new file."""
        tree = ET.parse(input_file)
        root = tree.getroot()

        for elem in root.iter():
            elem.tag = self.strip_namespace(elem.tag)
            elem.attrib = {self.strip_namespace(k): v for k, v in elem.attrib.items()}
        tree.write(output_file)

class XMLCanvasParser:
        '''Create quiz questions. They have a different format based on their type.'''
        def __init__(self, xml_file):
            self.tree = ET.parse(xml_file)
            self.root = self.tree.getroot()

        '''Let's identify a question node, then loop through its content. In doing so, we weill extract out the following: (1) the Question Type, (2) the Points Possible, (3) the Question Text, (4) the Choices Text and their Identifier, and (5) the Correct Answer using the Identifier, and (6) maybe the question ID (not sure if this is needed)'''

        # Extract details from each question
        def extract_question_details(self):
            question_details = []
            # Go through each question and ... 
            for item in self.root.findall(".//item[@title='Question']"):
                # get the id
                question_id = item.get('ident') # Not currently used
                # get the question type
                question_type = None 
                for question in item.findall(".//qtimetadatafield"):
                    fieldlabel = question.find('fieldlabel').text
                    if fieldlabel == 'question_type':
                        question_type = question.find('fieldentry').text
                        break
                # get the points possible
                points_possible = None
                for points in item.findall(".//qtimetadatafield"):
                    fieldlabel = points.find('fieldlabel').text
                    if fieldlabel == 'points_possible':
                        points_possible = points.find('fieldentry').text
                        break

                # get the question text. It will be teh first item in the material tag
                question_text = None
                material = item.find(".//material") # use find instead of findall
                if material is not None:
                    mattext = material.find('mattext')
                    if mattext is not None:
                        question_text = mattext.text
                        question_text = html_to_cleantext(question_text)

                # get the choices with their ID
                choices = []
                for response_label in item.findall(".//response_label"):
                    ident = response_label.get('ident')
                    choice_text = response_label.find(".//mattext").text
                    choices.append({'text': choice_text, 'ident': ident})
                
                '''get the correct answer via its ID. In the case of True or False, only the correct answer is supplied. In the case of multi-select, wrong answers are surrounded with a "not" tag. Check size of correct choices. If it is greater than 1, then we need to identify the wrong answer. We can do this by identifying the varequal in the NOT tag and the removing it from the correct choices list.  '''
                total_choices = []
                incorrect_choices =[]
                correct_choices = []

                for answer in item.iter("varequal"):
                    total_choices.append(answer.text)
                if len(total_choices) == 1:
                    correct_choices.append(answer.text)
                elif len(total_choices)>1:
                    for wrong_answer in item.iter("not"):
                        incorrect_choices.append(wrong_answer[0].text)
                    correct_choices = list(set(total_choices) - set(incorrect_choices))
                else:
                    pass
                print(question_type, correct_choices)

                # Let's put everything in a list of dicts:
                question_details.append({
                    #'question_id': question_id,
                    'question_type': question_type,                
                    'points_possible': points_possible,                
                    'question_text': question_text,
                    'choices': choices,
                    'correct_choices': correct_choices
                })
            return question_details

class QuizBuilder:
    '''
    Class that takes data from the quiz title and description and the questions and put them together
    '''
    def __init__(self, tag_values, question_details):
        self.tag_values = tag_values
        self.question_details = question_details

    # First, we will write the Title, Header, and Options to a .txt file
    def create_quiz_header(self):
        if 'title' in self.tag_values:
            with open('quiz.txt', 'w', encoding='utf-8') as f:
                f.write(f"Quiz title: {self.tag_values['title']}\n")
                f.write(f"Quiz description: {self.tag_values['description']}\n")
                f.write(f"shuffle answers: {self.tag_values['shuffle_answers']}\n")
                f.write(f"show correct answers: {self.tag_values['show_correct_answers']}\n")
                # TODO: Need to add if clause since one depends on the other
                #f.write(f"one question at a time: {tag_values['one_question_at_a_time']}\n")
                #f.write(f"can't go back: {tag_values['cant_go_back']}\n\n")

    # Next, let's feed in the questions
    def create_quiz_questions(self):
        with open('quiz.txt', 'a', encoding='utf-8', newline="") as f:
            for question in self.question_details:
                f.write(f"\n1. {question['question_text']}\n")
                # Create the choices and identify the correct answer 
                # T/F or Multiple-Choice One Answer
                if question['question_type'] in ('true_false_question', 'multiple_choice_question'):
                    choice_counter = 0
                    for choice in question['choices']:
                        choice_letter = chr(97 + choice_counter)
                        # Check if it is correct using ident number and write to file
                        if choice['ident'] in question['correct_choices']:
                            f.write(f"*{choice_letter}) {choice['text']}\n")
                        else:
                            f.write(f"{choice_letter}) {choice['text']}\n")
                        choice_counter += 1
                        # Multi-select question
                elif question['question_type'] == 'multiple_answers_question':
                    for choice in question['choices']:
                        if choice['ident'] in question['correct_choices']:
                            f.write(f"[*] {choice['text']}\n")
                        else:
                            f.write(f"[] {choice['text']}\n")
                    pass

                #f.write(f"{question['question_type']}\n")

# Function to delete temporary files
def delete_temp_files():
    try:
        os.remove('output.xml')
        os.remove('stripped.xml')
        print("Temporary files deleted successfully.")
    except FileNotFoundError as e:
        print(f"Error: {e}")

def main():
    # There are two files so we will strip the namespace from both files
    folder_path = input("Enter the path to the folder containing the QTI quiz data. This will be in the export file and contain two files: ")
    folder = Path(folder_path)
    QUIZ_QUESTIONS_XML_NAME = get_other_file_from_folder(folder_path)

    # Strip Namespace from both files
    stripper = NamespaceStripper()
    stripper.remove_namespace_from_file(f"{folder}/{c.QUIZ_HEADER_XML_NAME}", 'output.xml')
    stripper.remove_namespace_from_file(f"{folder}/{QUIZ_QUESTIONS_XML_NAME}", 'stripped.xml')

    # Create the tree and get the root
    tree = ET.parse('output.xml')
    root = tree.getroot()

    # Create dict to store values, load in elems, and then print to new file
    tag_values = {}

    # Iterate to get desired tags
    for elem in root.iter():
        if elem.tag in ['title', 'description', 'shuffle_answers', 'show_correct_answers']:  # Add more as needed 'one_question_at_a_time', "cant_go_back" 
            tag_values[elem.tag] = elem.text

    # Clean up the quiz description
    if 'description' in tag_values:
        tag_values['description'] = html_to_cleantext(tag_values['description'])

    # Parse the stripped file and run the function
    xlparser = XMLCanvasParser('stripped.xml')
    question_details = xlparser.extract_question_details()

    # Extract to CSV for testing
    csv_file = 'question_details.csv'

    def write_to_csv(csv_file):
        with open(csv_file, mode='w', newline='', encoding="UTF-8") as f:
            if question_details:
                writer = csv.DictWriter(f, fieldnames=question_details[0].keys())
                writer.writeheader()
                for detail in question_details:
                    writer.writerow(detail)
        print(f"Question details saved to {csv_file}")

    write_to_csv(csv_file)

    # Let's build the quiz
    quiz_builder = QuizBuilder(tag_values, question_details)
    quiz_builder.create_quiz_header()
    quiz_builder.create_quiz_questions()

    # TODO: Check if ingest allows for 1. 1.1 . or need to include function that writes 1. , 2. , 3. 

    # Next, let's test by seeing if our quiz.txt will work with text2qti
    def convert_to_qti():
        result = subprocess.run(['text2qti', 'quiz.txt'], capture_output=True, text=True)
        if result.returncode == 0:
            print("Conversion to QTI format successful.")
        else:
            print("Conversion to QTI format failed.")
            print(result.stderr)

    #convert_to_qti() # Uncomment for reconvert. Used for testing
    delete_temp_files()

if __name__ == "__main__":
    main()