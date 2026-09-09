"""File processing utilities for QTI conversion."""

import logging
import tempfile
import zipfile
from pathlib import Path

import defusedxml.ElementTree as ET

from .err import Qti2txtError

logger = logging.getLogger(__name__)


class NamespaceStripper:
    "Returns a clean XML file w/o namespace aka url prefixing the XML tags"

    @staticmethod
    def strip_namespace(tag):
        """Elems in the parsed tree have a namespace. Example: <Element '{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}presentation' To make these easier to deal with, check if } is in the tag, do just 1 split at }, and then take everything after the tag"""
        if "}" in tag:
            return tag.split("}", 1)[
                1
            ]  # [1] rather than [0] since we want the tag rather than the namespace
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
    def _get_resource_file_hrefs(resource):
        """Return all file hrefs for a resource."""
        hrefs = []
        for resource_file in resource.findall("file"):
            href = resource_file.get("href")
            if href:
                hrefs.append(href)
        return hrefs

    @staticmethod
    def _select_quiz_xml_href(hrefs):
        """
        Select the primary quiz XML href from a list of resource files.
        Prefer non-metadata XML files.
        """
        for href in hrefs:
            lower_href = href.lower()
            if lower_href.endswith(".xml") and not lower_href.endswith(
                "assessment_meta.xml"
            ):
                return href
        for href in hrefs:
            if href.lower().endswith(".xml"):
                return href
        return hrefs[0] if hrefs else None

    @staticmethod
    def _select_metadata_xml_href(hrefs):
        """
        Select the metadata XML href from a list of resource files.
        Prefer assessment_meta.xml.
        """
        for href in hrefs:
            if href.lower().endswith("assessment_meta.xml"):
                return href
        for href in hrefs:
            lower_href = href.lower()
            if lower_href.endswith(".xml") and "meta" in lower_href:
                return href
        for href in hrefs:
            if href.lower().endswith(".xml"):
                return href
        return hrefs[0] if hrefs else None

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
            xml_str = ET.tostring(root).decode("utf-8")
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

                quiz_hrefs = FileProcessor._get_resource_file_hrefs(resource)
                quiz_href = FileProcessor._select_quiz_xml_href(quiz_hrefs)

                dependency_hrefs = []
                for dependency in resource.findall("dependency"):
                    dep_id = dependency.get("identifierref")
                    dep_resource = resources_by_id.get(dep_id)
                    if dep_resource is None:
                        continue
                    dependency_hrefs.extend(
                        FileProcessor._get_resource_file_hrefs(dep_resource)
                    )

                dependency_href = FileProcessor._select_metadata_xml_href(
                    dependency_hrefs
                )

                # Fallback for exports where metadata is bundled directly with
                # quiz XML instead of listed as a dependency resource.
                if dependency_href is None:
                    dependency_href = FileProcessor._select_metadata_xml_href(
                        quiz_hrefs
                    )

                if quiz_href and dependency_href:
                    quiz_pairs.append((quiz_href, dependency_href))
                    logger.info(f"Here are the refs: {quiz_href}, {dependency_href}")
                else:
                    logger.warning(
                        "Skipping quiz resource due to missing quiz/dependency XML refs"
                    )

            if not quiz_pairs:
                raise Qti2txtError("No quiz XML resources were found in the manifest.")

            return quiz_pairs
        finally:
            # Clean up the temporary file
            tmp_path = Path(tmp_file_path)
            if tmp_path.exists():
                tmp_path.unlink()
