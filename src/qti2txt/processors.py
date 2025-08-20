"""File processing utilities for QTI conversion."""

import tempfile
import zipfile
import defusedxml.ElementTree as ET
from pathlib import Path
import logging
from .err import Qti2txtError

logger = logging.getLogger(__name__)


class NamespaceStripper:
    "Returns a clean XML file w/o namespace aka url prefixing the XML tags"
    @staticmethod
    def strip_namespace(tag):
        """Elems in the parsed tree have a namespace. Example: <Element '{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}presentation' To make these easier to deal with, check if } is in the tag, do just 1 split at }, and then take everything after the tag"""
        if "}" in tag:
            return tag.split("}", 1)[1] # [1] rather than [0] since we want the tag rather than the namespace
        return tag 

    def remove_namespace_from_file(self, input_file, output_file):
        """Parse the XML, strip namespaces, and write to a new file."""
        try:
            tree = ET.parse(input_file)
            root = tree.getroot()

            for elem in root.iter() if root is not None else []:
                elem.tag = self.strip_namespace(elem.tag)
                elem.attrib = {
                    self.strip_namespace(k): v for k, v in elem.attrib.items()
                }
            tree.write(output_file)
        except ET.ParseError as e:
            logger.error(f"Issue parsing error: {e}")


class FileProcessor:
    @staticmethod
    def unzip_file(zip_path, extract_to):
        """QTI file comes as zip so let's unzip the file to the specified directory."""
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)

    @staticmethod
    def get_resource_hrefs(manifest_path):
        """Get the href attributes from the first and second resources in the manifest."""
        # open the imsmanifest.xml file
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file_path = tmp_file.name
        try:
            # Strip the namespace using NamespaceStripper
            stripper = NamespaceStripper()
            stripper.remove_namespace_from_file(manifest_path, tmp_file_path)

            # Ensure the temporary file is closed before parsing
            tmp_file.close()

            # Debug statement to check if the file exists
            if not Path(tmp_file_path).exists():
                raise FileNotFoundError(
                    f"Temporary file {tmp_file_path} does not exist."
                )

            # Parse the stripped XML file
            tree = ET.parse(tmp_file_path)
            root = tree.getroot()
            xml_str = ET.tostring(root).decode('utf-8')
            logger.debug("Entire XML tree:")  # for debugging purposes.
            logger.debug(xml_str)

            # Find resources
            resources = root.findall(".//resource")
            if len(resources) < 2:
                raise Qti2txtError("The manifest does not contain enough resources.")
            

            # The manifest file will store quizzes in pairs. They need to be extracted. Extracted as a tuple (first_href, second_href)
            quiz_pairs = []
            for i in range(0, len(resources), 2):
                if i + 1 < len(resources):  # check if there is pair
                    # null checks
                    first_file = resources[i].find("file")
                    second_file = resources[i + 1].find("file")

                    if first_file is not None and second_file is not None:
                        first_href = first_file.get("href")
                        second_href = second_file.get("href")
                        quiz_pairs.append(
                            (first_href, second_href)
                        )  # appending as tuple
                        logger.info(f"Here are the refs: {first_href}, {second_href}")
                    else:
                        logger.warning(
                            "Missing files or refs in manifest file required for Quiz extraction"
                        )

            return quiz_pairs
        finally:
            # Clean up the temporary file
            tmp_path = Path(tmp_file_path)
            if tmp_path.exists():
                tmp_path.unlink()
