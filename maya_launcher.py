import subprocess
import config
import os
import app_logger


LOGGER = app_logger.get_logger(__name__)


def execute_cache_job(project, epsoide, maya_file_path, reference_nodes, is_camera_cache):
    maya_log_name = os.path.basename(os.path.splitext(maya_file_path)[0])

    maya_log_path = config.MAYA_LOG_PATH.format(**{
        config.FormatterKeys.NAME: maya_log_name,
        config.FormatterKeys.EPI: epsoide,
    }).replace("\\", "/")

    log_dir = os.path.dirname(maya_log_path)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    command = '\"{app}\" -log \"{log}\" -command \"python(\\"from cacheManager import maya_operations;maya_operations.main(\\\\\\"{project}\\\\\\", \\\\\\"{epsoide}\\\\\\", \\\\\\"{file}\\\\\\", \\\\\\"{rnodes}\\\\\\", \\\\\\"{cam}\\\\\\")\\")\"'.format(
        app=config.MAYA_BATCH,
        log=maya_log_path,
        file=maya_file_path.replace("\\", "/"),
        rnodes=",".join(reference_nodes),
        project=project,
        epsoide=epsoide,
        cam="1" if is_camera_cache else "0"
    )

    module_path = os.path.dirname(os.path.dirname(__file__))

    if os.environ.get("PYTHONPATH"):
        os.environ["PYTHONPATH"] = "{};{}".format(os.environ["PYTHONPATH"], module_path)

    else:
        os.environ["PYTHONPATH"] = module_path

    os.environ["CACHE_MANAGER_PROCESS_EXPECTED_ERROR"] = "0"

    LOGGER.info("command: {}".format(command))
    result, error = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()

    if error:
        LOGGER.critical("error running subprocess error is below:\n{}".format(error))
        return False

    if config.SUCCESS_CODE not in result:
        if os.environ["CACHE_MANAGER_PROCESS_EXPECTED_ERROR"] == "0":
            LOGGER.critical("Unexpected error came, such like maya crash etc.")

        return False

    return True


if __name__ == '__main__':
    execute_cache_job("C:/Users/VIRU/Downloads/Project/Project/Ep101/Ep101/IFD/Sh020/pta_ep101_sh020_cl01_v00.ma", ["nodeRN", "node2RN"])