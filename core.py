import os
import file_parser
import random
import time
import maya_launcher
import app_logger
import config
import glob
from PySide2.QtCore import QObject, Signal

LOGGER = app_logger.get_logger(__name__)


class MayaFile(object):

    def __init__(self, project, episode, file_path):
        self.project = project
        self.episode = episode
        self.file_path = file_path
        self.file_name = os.path.basename(self.file_path)
        self.shot = self.file_name.split("_")[2]

        self.references = []
        self._get_reference_info()
        self.display = "{} | {} references".format(self.file_name, len(self.references))

    def _get_reference_info(self):
        reference_data = file_parser.get_reference_info_from_file(self.file_path)

        for reference in reference_data:
            instance = Reference(
                self.project,
                self.episode,
                self.shot,
                reference["namespace"],
                reference["refnode"],
                reference["path"],
            )
            self.references.append(instance)

        self.references.append(Reference(self.project, self.episode, self.shot, "Camera", "Camera", ""))


class Reference(object):
    def __init__(self, project, episode, shot, ns, rn, path):
        self.project = project
        self.episode = episode
        self.shot = shot
        self.namespace = ns
        self.reference_node = rn
        self.reference_path = path
        self.display = "{} | {}".format(self.reference_node, self.namespace)

    def check_for_cache(self):
        formatter = {
            config.FormatterKeys.PROJ: self.project,
            config.FormatterKeys.EPI: self.episode,
            config.FormatterKeys.SHOT: self.shot,
            config.FormatterKeys.ASSET_TYPE: self.asset_type,
            config.FormatterKeys.NAME: self.namespace + ".abc",
            config.FormatterKeys.STAMP: "",
        }
        output_path = config.CACHE_OUTPUT.format(**formatter).replace("\\", "/")

    @property
    def asset_type(self):
        if "/char/" in self.reference_path:
            return "Char"

        elif "/prop/" in self.reference_path:
            return "Prop"

        elif not self.reference_path:
            return "Camera"

        else:
            return "Unknown"

    @property
    def is_cacheable(self):
        return self.asset_type in ["Char", "Prop", "Camera"]

    def __repr__(self):
        return "<{}>".format(self.reference_node)


class Job(QObject):
    ALL_REFERENCE = "ALL"
    DONE = "done"
    IP = "ip"
    ERROR = "error"
    IN_QUEUE = "queue"
    SIGNAL = Signal(str)

    def __init__(self, project, epsoide, maya_file_instance, selected_reference):
        super(Job, self).__init__()
        self.project = project
        self.epsoide = epsoide
        self.maya_file_instance = maya_file_instance  # type: MayaFile
        self.selected_reference = selected_reference  # type: list[Reference]
        self.reference_to_cache_count = "All cacheable" if len(self.reference_to_cache) == len(self.maya_file_instance.references) else len(self.reference_to_cache)
        # self.status = random.choice([self.IN_QUEUE, self.IP, self.ERROR, self.DONE])
        self.status = self.IN_QUEUE

        self.display_name = "{} | reference for cache: {}".format(self.maya_file_instance.file_name, self.reference_to_cache_count)
        self.tool_tip = "status: {} | reference to cache: {}".format(self.status, ", ".join([
            i.reference_node for i in self.reference_to_cache
        ]))

    @property
    def reference_to_cache(self):
        if self.selected_reference != self.ALL_REFERENCE:
            return self.selected_reference

        else:
            return [i for i in self.maya_file_instance.references if i.is_cacheable]

    def execute(self):
        if self.status == self.IN_QUEUE:
            self.status = self.IP
            self.SIGNAL.emit(self.status)
            reference_to_cache = [i.reference_node for i in self.reference_to_cache if not i.asset_type == "Camera"]
            is_camera_cache = False
            for ref in self.reference_to_cache:
                if ref.asset_type == "Camera":
                    is_camera_cache = True
            status = maya_launcher.execute_cache_job(self.project,
                                                     self.epsoide,
                                                     self.maya_file_instance.file_path,
                                                     reference_to_cache,
                                                     is_camera_cache)
            if status:
                self.status = self.DONE

            else:
                self.status = self.ERROR
            self.SIGNAL.emit(self.status)

        else:
            LOGGER.warning("skipping {} status is {}".format(self, self.status))

    def __eq__(self, other):
        is_reference_to_cache_match = self.reference_to_cache_count == other.reference_to_cache_count
        if is_reference_to_cache_match:
            for ref in self.reference_to_cache:  # type: Reference
                match_found = False
                for otherRef in other.reference_to_cache:  # type: Reference
                    if all([ref.reference_path == otherRef.reference_path,
                            ref.reference_node == otherRef.reference_node]):
                        match_found = True
                if not match_found:
                    is_reference_to_cache_match = False
                    break

        return all([
            self.maya_file_instance.file_name == other.maya_file_instance.file_name,
            is_reference_to_cache_match,
        ])

    def __repr__(self):
        return "Job(file={}, reference_nodes={})".format(self.maya_file_instance.file_name, self.reference_to_cache)


def get_maya_files(project, episode):
    """

    :param project:
    :type project: str
    :param episode:
    :type episode: str
    :return:
    :rtype: list[MayaFile]
    """
    formatter = {
        config.FormatterKeys.PROJ: project,
        config.FormatterKeys.EPI: episode,
    }

    pattern = config.SOURCE_MAYA_FILES.format(**formatter)
    maya_files = glob.glob(pattern) or []
    return [MayaFile(project, episode, f) for f in maya_files]


def get_project_list():
    root = config.REFERENCE_DRIVE
    return [folder for folder in os.listdir(root) if os.path.isdir(os.path.join(root, folder))]


def get_epsoide_list():
    root = os.path.join(config.EPISODE_ROOT)
    return [folder for folder in os.listdir(root) if os.path.isdir(os.path.join(root, folder))]


