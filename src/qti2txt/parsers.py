"""XML parsing utilities for QTI questions."""

from .helpers import html_to_cleantext
import defusedxml.ElementTree as ET
import logging
from .config_questions import question_config

logger = logging.getLogger(__name__)


class XMLCanvasParser:
    """Create quiz questions. They have a different format based on their type."""

    def __init__(self, xml_file):
        self.xml_file = xml_file
        try:
            self.tree = ET.parse(xml_file)
            self.root = self.tree.getroot()
            # Null check
            if self.root is None:
                logger.error(
                    f"Failed to get root element from {xml_file}. Every XML needs a root elem so your XML is probably corrupted."
                )
                raise ValueError(f"Invalid XML file: {xml_file}")
        except ET.ParseError as e:
            logger.error(f"XML parsing error in {xml_file}: {e}")
            self.root = None
            raise
        except Exception as e:
            logger.error(f"Error initializing XMLCanvasParser with {xml_file}: {e}")
            self.root = None
            raise


    #def get_feedback_general(self):


    """Let's identify a question node, then loop through its content. In doing so, we weill extract out the following: (1) the Question Type, (2) the Points Possible, (3) the Question Text, (4) the Choices Text and their Identifier, and (5) the Correct Answer using the Identifier, and (6) maybe the question ID (not sure if this is needed)"""

    # Extract details from each question
    def extract_question_details(self):
        question_details = []
        # Add null check for self.root
        if self.root is None:
            logger.error("XML root is None - cannot extract question details")
            return question_details

        # Go through each question and ..
        for item in self.root.findall(".//item[@title='Question']"):
            # get the question type
            question_type = None
            for question in item.findall(".//qtimetadatafield"):
                # get fieldlabel with null check
                fieldlabel_elem = question.find("fieldlabel")
                fieldlabel = (
                    fieldlabel_elem.text if fieldlabel_elem is not None else None
                )

                if fieldlabel == "question_type":
                    question_type = question.find("fieldentry").text
                    break

            # get the points possible w/ null check
            points_possible = None
            for points in item.findall(".//qtimetadatafield"):
                fieldlabel_elem = points.find("fieldlabel")
                fieldlabel = (
                    fieldlabel_elem.text if fieldlabel_elem is not None else None
                )

                if fieldlabel == "points_possible":
                    points_possible_elem = points.find("fieldentry")
                    points_possible = (
                        points_possible_elem.text
                        if points_possible_elem is not None
                        else None
                    )
                    break
            
            # get the general feedback for the question <itemfeedback ident="general_fb">
            feedback_general = None
            feedback_elem = item.find(".//itemfeedback[@ident='general_fb']/flow_mat/material/mattext")
            if feedback_elem is not None and feedback_elem.text is not None:
                feedback_general = html_to_cleantext(feedback_elem.text)

            # get the question text. It will be teh first item in the material tag
            question_text = None
            material = item.find(".//material")  # use find instead of findall
            if material is not None:
                mattext = material.find("mattext")
                if mattext is not None:
                    question_text = mattext.text
                    question_text = html_to_cleantext(question_text)

            # Comes from config_question.py QTIConfig class. Check the available questions
            if question_type not in question_config.supported_question_types:
                logger.warning(
                    f"Warning. This quiz contains a {question_type}. This type of question is not currently handled by this script. Sorry."
                )
                continue

            elif question_type == "short_answer_question":
                correct_answers = []
                for varequal in item.findall(".//conditionvar/varequal"):
                    if varequal.text:
                        correct_answers.append(varequal.text.strip())
                logger.info(f"Short answer correct answers: {correct_answers}")

            elif question_type in ["essay_question", "text_only_question"]:
                pass

            elif question_type in [
                "multiple_choice_question",
                "true_false_question",
                "multiple_answers_question",
            ]:
                choices = []
                for response_label in item.findall(".//response_label"):
                    ident = response_label.get("ident")
                    choice_text = response_label.find(".//mattext").text
                    clean_choice_text = html_to_cleantext(
                        choice_text
                    )  # Clean the HTML from choice_text
                    choices.append({"text": clean_choice_text, "ident": ident})

                """get the correct answer via its ID. In the case of True or False, only the correct answer is supplied. In the case of multi-select, wrong answers are surrounded with a "not" tag. Check size of correct choices. If it is greater than 1, then we need to identify the wrong answer. We can do this by identifying the varequal in the NOT tag and the removing it from the correct choices list.  """
                total_choices = []
                incorrect_choices = []
                correct_choices = []

                for answer in item.iter("varequal"):
                    total_choices.append(answer.text)
                if len(total_choices) == 1:
                    correct_choices.append(answer.text)
                elif len(total_choices) > 1:
                    for wrong_answer in item.iter("not"):
                        incorrect_choices.append(wrong_answer[0].text)
                    correct_choices = list(set(total_choices) - set(incorrect_choices))
                else:
                    pass
                logger.info("Question type: %s", question_type)
                logger.info("Correct choices: %s", correct_choices)

            # MATCHING QUESTION HANDLING
            elif question_type == "matching_question":
                match_question_data = {
                    "questions": [],  # Group 1
                    "answers": [],  # Group 2
                    "correct_matches": [],
                }

                # Collect data (left side)
                for response_lid in item.findall(".//response_lid"):
                    # Question (Group 1)
                    q_ident = response_lid.attrib["ident"]
                    # q_ident = response_lid.get("ident")
                    q_material = response_lid.find("./material/mattext")
                    if q_material is not None and q_material.text is not None:
                        q_text = q_material.text.strip()
                    else:
                        q_text = q_ident

                    match_question_data["questions"].append(
                        {"q_ident": q_ident, "text": q_text}
                    )

                    # Answers (Group 2) - all response labels under this response_lid are the other match (answers)
                    for response_label in response_lid.findall(
                        ".//render_choice/response_label"
                    ):
                        a_ident = response_label.get("ident")
                        a_material = response_label.find(".//mattext")
                        if a_material is not None and a_material.text is not None:
                            a_text = a_material.text.strip()
                        else:
                            a_text = a_ident

                        # Group 2 (right group) will have duplicates so check if it exists. If not, append.
                        match_data = {"a_ident": a_ident, "text": a_text}
                        if match_data not in match_question_data["answers"]:
                            match_question_data["answers"].append(match_data)

                # Collect correct matches. This is put later in the conditionvar of the XML
                for varequal in item.findall(".//conditionvar/varequal"):
                    question_id = varequal.get("respident")
                    answer_id = (
                        f"response_{varequal.text.strip()}" if varequal.text else None
                    )

                    if question_id and answer_id:
                        match_question_data["correct_matches"].append(
                            {"question_id": question_id, "answer_id": answer_id}
                        )

                # Build correct_answers as a list of "question_text -> answer_text" strings
                correct_answers = []
                # lookup dictionaries for question_id and answer_id to their text
                q_lookup = {
                    q["q_ident"]: q["text"] for q in match_question_data["questions"]
                }
                a_lookup = {
                    a["a_ident"]: a["text"] for a in match_question_data["answers"]
                }

                for match in match_question_data["correct_matches"]:
                    qid = match["question_id"]
                    aid = match["answer_id"].replace("response_", "", 1)
                    q_text = q_lookup.get(qid, qid)
                    a_text = a_lookup.get(aid, aid)
                    correct_answers.append(f"{q_text} -> {a_text}")

                logger.info(
                    f"Parsed matching question: {len(match_question_data['questions'])} questions, "
                    f"{len(match_question_data['answers'])} answers, {len(match_question_data['correct_matches'])} matches"
                )

            elif question_type in ["numerical_question"]:
                # init values
                correct_answers = []
                ans_exact = None
                ans_min = None
                ans_max = None
                ans_margin = None

                conditionvar = item.find(".//conditionvar")

                if conditionvar is not None:
                    # Try to find varequal directly under conditionvar (or its children)
                    conditionvar_exact = conditionvar.find(".//varequal")
                    if conditionvar_exact is not None:
                        ans_exact = float(conditionvar_exact.text.strip())
                        # print(ans_exact)
                        logger.info(f"Exact answer found in {conditionvar}")

                    # Get range bounds
                    conditiongte = conditionvar.find(".//vargte")
                    conditionlte = conditionvar.find(".//varlte")

                    if conditiongte is not None:
                        ans_min = float(conditiongte.text.strip())
                        logger.info(f"Minimum value: {ans_min}")

                    if conditionlte is not None:
                        ans_max = float(conditionlte.text.strip())
                        logger.info(f"Maximum value: {ans_max}")

                    # Calculate margin of error. If no exact answer, but there is a min and max, then this is a range question. TODO: Simplify since I'm catching an exact answer already
                    if (
                        ans_exact is None
                        and ans_min is not None
                        and ans_max is not None
                    ):
                        if ans_min != ans_max:
                            logger.info(f"Answer range: {ans_min} to {ans_max}")
                        else:
                            # If min equals max, treat as exact answer
                            ans_exact = ans_min
                            logger.info(f"Exact answer (from range): {ans_exact}")

                    # Calculate margin of error. If there is an exact answer and ans =min = max, then we have an exact answer and don't need to provide margin of error. ELSE: if not (ans == min == max), then we have an exact answer w/ a margin of error.

                    if (
                        ans_exact is not None
                        and ans_min is not None
                        and ans_max is not None
                    ):
                        if ans_min == ans_max == ans_exact:
                            ans_margin = 0.0
                        else:
                            # Calculate margin as difference from exact to bounds
                            margin_low = abs(ans_exact - ans_min)
                            margin_high = abs(ans_max - ans_exact)
                            ans_margin = max(margin_low, margin_high)
                            logger.info(f"Answer margin: +- {ans_margin}")

                # Let's store the above data
                numerical_answer = {}
                if ans_exact is not None:
                    numerical_answer["exact"] = ans_exact
                if ans_margin is not None:  # check if there is a margin of error
                    # Round margin to at least 0.0001 <- Smallest amount allowed by CANVAS, unless it's exactly 0.0
                    if ans_margin == 0.0:  # rounds to .0001 when margin is 0.0
                        rounded_margin = 0.0
                    else:
                        rounded_margin = max(round(ans_margin, 4), 0.0001)
                    numerical_answer["margin"] = rounded_margin
                if ans_min is not None and ans_max is not None and ans_min != ans_max:
                    numerical_answer["range"] = [ans_min, ans_max]

                correct_answers.append(numerical_answer)
                logger.info(f"Numerical answer data: {numerical_answer}")

            # Get the ids since these will be used to x-ref the answers.
            elif question_type in ["fill_in_multiple_blanks_question"]:
                blanks = {}
                for response_lid in item.findall(".//response_lid"):
                    blank_ident = response_lid.get("ident")  # e.g., response_number1
                    blank_label_elem = response_lid.find(
                        "./material/mattext"
                    )  # <mattext>number1</mattext>
                    blank_label = (
                        blank_label_elem.text
                        if blank_label_elem is not None
                        else blank_ident
                    )
                    blank_choices = []
                    for response_label in response_lid.findall(".//response_label"):
                        choice_ident = response_label.get(
                            "ident"
                        )  # ident num in response_label
                        mattext_elem = response_label.find(".//mattext")  # the Answer
                        choice_text = (
                            mattext_elem.text if mattext_elem is not None else ""
                        )
                        clean_choice_text = html_to_cleantext(choice_text)
                        blank_choices.append(
                            {"ident": choice_ident, "text": clean_choice_text}
                        )
                    blanks[blank_label] = (
                        blank_choices  # map s blank in question to choices
                    )

            # Build the question dictionary based on question type
            question_dict = {
                "question_type": question_type,
                "points_possible": points_possible,
                "question_text": question_text,
                "feedback_general": feedback_general
            }

            # For question types without explicit choices, we can just add the question data
            if question_type in [
                "short_answer_question",
                "numerical_question",
                "matching_question",
            ]:
                question_dict["correct_answers"] = correct_answers
                logger.info(f"data for {question_type} appended")

            elif question_type in ["essay_question", "file_upload_question"]:
                pass

            # Add choices and correct_choices for supported types
            elif question_type in [
                "multiple_choice_question",
                "true_false_question",
                "multiple_answers_question",
            ]:
                question_dict["choices"] = choices
                question_dict["correct_choices"] = correct_choices

            elif question_type in ["fill_in_multiple_blanks_question"]:
                # not sure about how to store this data
                simple_blanks = {}
                for blank_label, choices in blanks.items():
                    # If only one choice, just store the text, else store list of texts
                    texts = [c["text"] for c in choices]
                    simple_blanks[blank_label] = texts[0] if len(texts) == 1 else texts
                question_dict["multiple_blanks_answers"] = simple_blanks

            question_details.append(question_dict)
        return question_details
