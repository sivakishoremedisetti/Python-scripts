import os
import maya.cmds as cmds
import config
import app_logger
import utils


LOGGER = app_logger.get_logger(__name__)
LOGGER.info("-----------------------------------------------")
LOGGER.info("-------------- MAYA PROCESS START -------------")
LOGGER.info("-----------------------------------------------")


CACHE_NODE = "GEO"


class CacheExporter(object):
    def __init__(self, project, episode, maya_file_path, reference_nodes, is_camera_cache):
        self.project = project
        self.episode = episode
        self.maya_file_path = maya_file_path
        self.shot = os.path.basename(self.maya_file_path).split("_")[2]
        self.reference_nodes = reference_nodes
        self.is_camera_cache = is_camera_cache

        self.camera_name = "{}{}_camCt".format(self.episode, self.shot).lower()

    def create_error_tag(self, message):
        print "{0}{1}{0}".format(config.TRACEBACK_TRACKER, message)

    def open_maya_file(self):
        if os.path.exists(self.maya_file_path):
            pass
            try:
                LOGGER.info("opening maya file: {}".format(self.maya_file_path))
                cmds.file(self.maya_file_path, o=True, f=True)
                LOGGER.info("file opened")
            except:
                LOGGER.info("file opened with error")

        else:
            message = "Unable to open maya file, file not found: {}".format(self.maya_file_path)
            os.environ["CACHE_MANAGER_PROCESS_EXPECTED_ERROR"] = "1"
            raise Exception(message)

    def check_file(self):
        is_ready_for_cache = True
        unloaded_reference = []
        cache_node_missing_reference = []

        for reference_node in self.reference_nodes:
            if not cmds.referenceQuery(reference_node, il=True):
                unloaded_reference.append(reference_node)

        for reference_node in self.reference_nodes:
            if cmds.referenceQuery(reference_node, il=True):
                namespace = cmds.referenceQuery(reference_node, namespace=True).strip(":")
                node_name = "{}:{}".format(namespace, CACHE_NODE)
                if not cmds.objExists(node_name):
                    cache_node_missing_reference.append(node_name)

        if unloaded_reference:
            LOGGER.critical("unable to process cache process, unloaded reference found:{}\n\t".format(
                "\n\t".join(unloaded_reference)
            ))
            is_ready_for_cache = False

        if cache_node_missing_reference:
            LOGGER.critical("unable to process cache process, cache group not found:{}\n\t".format(
                "\n\t".join(cache_node_missing_reference)
            ))
            is_ready_for_cache = False

        if self.is_camera_cache:
            if not cmds.objExists(CAMERA_NAME):
                LOGGER.critical("unable to process cache process, camera '{}' not found.".format(CAMERA_NAME))
                is_ready_for_cache = False

        return is_ready_for_cache

    def get_asset_type(self, path):
        if "/char/" in path.lower():
            return "Char"
        else:
            return "Prop"

    def export_cache(self, reference_node):
        namespace = cmds.referenceQuery(reference_node, namespace=True).strip(":")
        start_frame = cmds.playbackOptions(q=True, ast=True)
        end_frame = cmds.playbackOptions(q=True, aet=True)
        reference_path = cmds.referenceQuery(reference_node, f=True)

        asset_type = self.get_asset_type(reference_path)

        formatter = {
            config.FormatterKeys.PROJ: self.project,
            config.FormatterKeys.EPI: self.episode,
            config.FormatterKeys.SHOT: self.shot,
            config.FormatterKeys.ASSET_TYPE: asset_type,
            config.FormatterKeys.NAME: namespace + ".abc",
            config.FormatterKeys.STAMP: "",
        }

        output_path = config.CACHE_OUTPUT.format(**formatter).replace("\\", "/")

        node_to_export = cmds.ls("{}:{}".format(namespace, "GEO"), l=True)

        if node_to_export:
            LOGGER.info("exporting cache at {}".format(output_path))
            dirname = os.path.dirname(output_path)
            if not os.path.exists(dirname):
                os.makedirs(dirname)

            self.export_alembic(node_to_export[0], output_path, start_frame, end_frame)

    def export_alembic(self, meshes, path, start_frame, end_frame):
        cmd = "j=frameRange {s_frame} {e_frame} -uvWrite -writeFaceSets -writeVisibility -dataFormat ogawa {root} -file {path}".format(
            root="-root ".join(meshes), path=path, s_frame=start_frame, e_frame=end_frame
        )

        cmds.AbcExport(cmd)
        LOGGER.info("cache exported.")

    def export_camera_cache(self):
        formatter = {
            config.FormatterKeys.PROJ: self.project,
            config.FormatterKeys.EPI: self.episode,
            config.FormatterKeys.SHOT: self.shot,
            config.FormatterKeys.ASSET_TYPE: "Cam",
            config.FormatterKeys.NAME: "{}_{}.fbx".format(self.episode, self.shot),
            config.FormatterKeys.STAMP: "",
        }
        cache_path = config.CACHE_OUTPUT.format(**formatter)

        dirname = os.path.dirname(cache_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        self.export_fbx(CAMERA_NAME, cache_path)

    def export_fbx(self, node, path):
        cmds.select(node)
        cmds.file(path, es=True, f=True, typ="FBX export")
        LOGGER.info("cache exported path: {}".format(path))

    def load_required_plugins(self):
        cmds.loadPlugin("fbxmaya")
        cmds.loadPlugin("AbcImport")

    def doit(self):
        self.load_required_plugins()
        self.open_maya_file()

        if not self.check_file():
            os.environ["CACHE_MANAGER_PROCESS_EXPECTED_ERROR"] = "1"
            raise Exception("skipping cache process")

        for reference_node in self.reference_nodes:
            LOGGER.info("exporting cache for {}".format(reference_node))
            self.export_cache(reference_node)

        self.export_camera_cache()

        print config.SUCCESS_CODE

        LOGGER.info("-----------------------------------------------")
        LOGGER.info("-------------- MAYA PROCESS DONE --------------")
        LOGGER.info("-----------------------------------------------")


@utils.safe_run
def main(project, episode, maya_file_path, reference_nodes, is_camera_cache):
    reference_nodes = reference_nodes.split(",")
    is_camera_cache = bool(int(is_camera_cache))
    LOGGER.info("argument get in maya\n\tproject:{}\n\tepisode:{}\n\tmaya_file_path:{}\n\treference_nodes:{}\n\tis_camera_cache:{}".format(
        project, episode, maya_file_path, reference_nodes, is_camera_cache
    ))
    LOGGER.info("Total Reference to cache: {}, camera cache: {}".format(len(reference_nodes), is_camera_cache))
    print "project:", project
    print "episode:", episode
    print "maya_file_path:", maya_file_path
    print "reference_nodes:", reference_nodes
    print "is_camera_cache:", is_camera_cache

    instance = CacheExporter(project, episode, maya_file_path, reference_nodes, is_camera_cache)
    instance.doit()


