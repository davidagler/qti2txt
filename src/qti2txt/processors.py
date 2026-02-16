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
            raise Qti2txtError(f"Could not parse XML file: {input_file}") from e


class FileProcessor:
    @staticmethod
    def _get_resource_file_href(resource):
        """Return the first file href for a resource, if present."""
        resource_file = resource.find("file")
        if resource_file is None:
            return None
        return resource_file.get("href")

    @staticmethod
    def unzip_file(zip_path, extract_to):
        """QTI file comes as zip so let's unzip the file to the specified directory."""
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)

    @staticmethod
    def get_resource_hrefs(manifest_path):
        """Get `(quiz_xml_href, metadata_xml_href)` tuples from a manifest."""
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
            if len(resources) < 1:
                raise Qti2txtError("The manifest does not contain enough resources.")

            resources_by_id = {}
            for resource in resources:
                resource_id = resource.get("identifier")
                if resource_id:
                    resources_by_id[resource_id] = resource

            # Canvas marks actual quiz payload resources with imsqti_xml* types.
            quiz_pairs = []
            for resource in resources:
                resource_type = (resource.get("type") or "").lower()
                if "imsqti_xml" not in resource_type:
                    continue

                quiz_href = FileProcessor._get_resource_file_href(resource)
                dependency = resource.find("dependency")
                dependency_href = None
                if dependency is not None:
                    dep_id = dependency.get("identifierref")
                    dep_resource = resources_by_id.get(dep_id)
                    if dep_resource is not None:
                        dependency_href = FileProcessor._get_resource_file_href(
                            dep_resource
                        )

                if quiz_href and dependency_href:
                    quiz_pairs.append((quiz_href, dependency_href))
                    logger.info(f"Here are the refs: {quiz_href}, {dependency_href}")
                else:
                    logger.warning(
                        "Skipping quiz resource due to missing quiz/dependency XML refs"
                    )

            if not quiz_pairs:
                raise Qti2txtError(
                    "No quiz XML resources were found in the manifest."
                )

            return quiz_pairs
        finally:
            # Clean up the temporary file
            tmp_path = Path(tmp_file_path)
            if tmp_path.exists():
                tmp_path.unlink()
