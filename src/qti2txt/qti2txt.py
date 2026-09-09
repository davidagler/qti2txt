import argparse
import csv
import logging
import shutil
import tempfile
import time
import urllib.parse
import uuid
from pathlib import Path

import defusedxml.ElementTree as ET

from .builders import QuizBuilder
from .config_logging import primary_logger, startup_logger
from .err import Qti2txtError
from .helpers import html_to_cleantext
from .parsers import XMLCanvasParser
from .processors import FileProcessor, NamespaceStripper

logger = logging.getLogger(__name__)


def main():
    # init logging

    def write_to_csv(csv_file, question_details):
        """Write question details to a CSV file."""
        if not question_details:
            logger.info("No question details to write to CSV")
            return

        # because diff fields based on question types, I need to get all the keys first
        all_fieldnames = set()
        for detail in question_details:
            all_fieldnames.update(detail.keys())
        fieldnames = sorted(all_fieldnames)

        with open(csv_file, mode="w", newline="", encoding="UTF-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for detail in question_details:
                writer.writerow(detail)
        logger.info(f"Question details saved to {csv_file}")

    # Function to delete temporary files
    def delete_temp_files(XML_STRIPPED_FILE, XML_NAMESPACE_FILE):
        try:
            XML_STRIPPED_FILE.unlink()
            logger.info(f"Removed {XML_STRIPPED_FILE}")
            XML_NAMESPACE_FILE.unlink()
            logger.info(f"Removed {XML_NAMESPACE_FILE}")
        except FileNotFoundError:
            logger.warning("Could not find tmp files to delete")
        except Exception as e:
            logger.warning(f"Error deleting temporary files: {e}")

    # Copy bundled Canvas assets so rewritten image links resolve for text2qti.
    def copy_web_resources(tmp_folder_path, output_path):
        tmp_root = Path(tmp_folder_path)
        destination_dir = output_path / "web_resources"
        copy_sources = []

        # Canvas exports commonly bundle assets in web_resources/.
        source_web_resources = tmp_root / "web_resources"
        if source_web_resources.exists():
            copy_sources.append((source_web_resources, destination_dir))

        # text2qti exports can bundle media directly as top-level images/ (or Images/).
        for image_dir_name in ("images", "Images"):
            source_images = tmp_root / image_dir_name
            if source_images.exists():
                copy_sources.append((source_images, destination_dir / image_dir_name))

        if not copy_sources:
            logger.info(
                "No media asset folders found in archive (expected web_resources/ or images/)."
            )
            return
        try:
            for source_dir, target_dir in copy_sources:
                shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
            # text2qti uses markdown parsing for local images; create encoded aliases
            # for filenames with parentheses so markdown links can use %28/%29 paths.
            for file_path in destination_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                name = file_path.name
                if "(" not in name and ")" not in name:
                    continue
                encoded_name = urllib.parse.quote(name, safe=" -._")
                if encoded_name == name:
                    continue
                encoded_path = file_path.with_name(encoded_name)
                if not encoded_path.exists():
                    shutil.copy2(file_path, encoded_path)
            logger.info(f"Copied media assets to {destination_dir}")
        except Exception as e:
            logger.warning(f"Could not copy media assets into {destination_dir}: {e}")

    # Init argparse
    def create_CLI():
        parser = argparse.ArgumentParser(
            description="Convert QTI quiz files to readable text format",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
            Examples:
            %(prog)s -f quiz.zip                    # Convert to current directory
            %(prog)s -f quiz.zip -o ./output        # Convert to output directory  
            %(prog)s -f quiz.zip -v --keep-tmp      # Verbose with temp files kept
                    """,
        )
        parser.add_argument(
            "-f",
            "--file",
            dest="folder_path",
            type=Path,
            required=True,
            help="Path to QTI zip file.",
        )
        parser.add_argument(
            "-o",
            "--output",
            dest="output_path",
            required=False,
            type=Path,
            help="Output path for .txt files.",
        )
        parser.add_argument(
            "-v", "--verbose", action="store_true", help="Enable verbose logging"
        )
        parser.add_argument(
            "-kxml",
            "--keeptmpxml",
            dest="keep_tmp_xml",
            action="store_true",
            help="Keeps temporary xml files created in the process of creating the quiz.",
        )
        return parser

    # init basic logging
    startup_logger()
    cli_parser = create_CLI()
    args = cli_parser.parse_args()

    # -v --verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not Path(args.folder_path).is_file():
        logger.critical(
            f"Error: The file {args.folder_path} does not exist. Check the path."
        )
        raise Qti2txtError(f"The file {args.folder_path} does not exist.")
    if not Path(args.folder_path).suffix.lower() == ".zip":
        logger.critical("QTI file must be a .zip file")
        raise ValueError("QTI file must be a .zip file")

    # -o --output
    if args.output_path:
        output_dir = Path(args.output_path)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory created at {output_dir.resolve()}")
        except Exception as e:
            logger.critical(f"Could not create output directory {output_dir}: {e}")
            raise Qti2txtError(f"Could not create output directory {output_dir}") from e
    else:
        # Default to current working directory if no output path is specified
        output_dir = Path.cwd()

    # primary logger
    primary_logger(output_dir, args.verbose)

    # Create a tmp directory, unzip the file, and get the resources
    with tempfile.TemporaryDirectory() as tmp_folder:
        logger.info(f"Created temporary directory at {tmp_folder}")
        try:
            FileProcessor.unzip_file(args.folder_path, tmp_folder)
        except Exception as e:
            logger.critical(f"Error unzipping QTI file: {e}")
            return

        copy_web_resources(tmp_folder, output_dir)

        # Get manifest file
        manifest_file = "imsmanifest.xml"
        manifest_path = Path(tmp_folder) / manifest_file
        if not manifest_path.is_file():
            logger.critical(
                "No quiz manifest found in the zip file. Expected file: imsmanifest.xml"
            )
            raise Qti2txtError(
                "No quiz manifest found in the zip file. Expected file: imsmanifest.xml"
            )

        # Get quiz pair hrefs from the manifest file
        quiz_pairs = FileProcessor.get_resource_hrefs(manifest_path)
        quiz_count = len(quiz_pairs)
        logger.info(f"There are {quiz_count} to process.")

        quiz_data = []

        # start (1, (href1.xml, href2.xml)
        for q, (first_href, second_href) in enumerate(quiz_pairs, 1):
            logger.info(f"Processing quiz {q}/{quiz_count}.")
            logger.info(f"First resource href: {first_href}")
            logger.info(f"Second resource href: {second_href}")

            # folder = Path(folder_path)
            QUIZ_QUESTIONS_XML_NAME = first_href
            QUIZ_HEADER_XML_NAME = second_href

            timestamp = int(time.time())
            unique_id = str(uuid.uuid4())[:8]  # shortened, last 8 char random UUID
            XML_STRIPPED_FILE = (
                output_dir / f"qti2txt_stripped_{timestamp}_{unique_id}.xml"
            )
            XML_NAMESPACE_FILE = (
                output_dir / f"qti2txt_output_{timestamp}_{unique_id}.xml"
            )

            # Strip Namespace from both files
            stripper = NamespaceStripper()
            stripper.remove_namespace_from_file(
                f"{tmp_folder}/{QUIZ_HEADER_XML_NAME}", XML_NAMESPACE_FILE
            )

            stripper.remove_namespace_from_file(
                f"{tmp_folder}/{QUIZ_QUESTIONS_XML_NAME}", XML_STRIPPED_FILE
            )

            # Create the tree and get the root
            tree = ET.parse(XML_NAMESPACE_FILE)
            root = tree.getroot()

            # Create dict to store values, load in elems, and then print to new file
            tag_values = {}

            # Iterate to get desired tags
            if root is not None:
                for elem in root.iter():
                    if elem.tag in [
                        "title",
                        "description",
                        "shuffle_answers",
                        "show_correct_answers",
                    ]:  # Add more as needed 'one_question_at_a_time', "cant_go_back"
                        tag_values[elem.tag] = elem.text

            # Clean up the quiz description
            if "description" in tag_values:
                description = tag_values["description"]
                if description:  # Check if description is not empty or None
                    tag_values["description"] = html_to_cleantext(description)
                else:
                    tag_values["description"] = ""

            # Parse the stripped file
            xlparser = XMLCanvasParser(XML_STRIPPED_FILE)
            question_details = xlparser.extract_question_details()

            # Add quiz id to each question for CSV output
            for detail in question_details:
                detail["quiz_name"] = tag_values.get("title", f"Quiz_{q}")

            # Build the quiz
            quiz_builder = QuizBuilder(tag_values, question_details, output_dir)
            quiz_builder.create_quiz_header()
            quiz_builder.create_quiz_questions()
            quiz_builder.convert_latex_format()

            # All the data for the CSV
            quiz_data.extend(question_details)
            logger.info(
                f"Quiz {q} titled '{tag_values.get('title', 'Untitled')}' processed."
            )

            # Delete temp xml files
            if args.keep_tmp_xml is False:
                delete_temp_files(XML_STRIPPED_FILE, XML_NAMESPACE_FILE)

    # Write CSV
    CSV_FILE_PATH = output_dir / "question_details.csv"
    write_to_csv(CSV_FILE_PATH, quiz_data)


if __name__ == "__main__":
    main()
