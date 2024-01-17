
class FormatterKeys(object):
    PROJ = "proj"
    EPI = "epi"
    SHOT = "shot"
    ASSET_TYPE = "asset_type"
    NAME = "name"
    STAMP = "stamp"


class __FormatterKeys(object):
    PROJ = "{" + FormatterKeys.PROJ + "}"
    EPI = "{" + FormatterKeys.EPI + "}"
    SHOT = "{" + FormatterKeys.SHOT + "}"
    ASSET_TYPE = "{" + FormatterKeys.ASSET_TYPE + "}"
    NAME = "{" + FormatterKeys.NAME + "}"
    STAMP = "{" + FormatterKeys.STAMP + "}"


REFERENCE_DRIVE = "W:"
EPISODE_ROOT = "W:/workspsace/unreal/EPISODES/"
SOURCE_MAYA_FILES = "W:/workspsace/unreal/EPISODES/{f.EPI}/IFD/*/*_*_*_v??.ma".format(f=__FormatterKeys)
CACHE_OUTPUT = "W:/workspsace/unreal/EPISODES/{f.EPI}/Alembic/{f.SHOT}/{f.ASSET_TYPE}/{f.NAME}".format(f=__FormatterKeys)
MAYA_BATCH = "C:/Program Files/Autodesk/Maya2020/bin/mayabatch.exe"

LOGGING_PATH = "W:/workspsace/cache_manager_logs/cache_manager_{f.STAMP}.log".format(f=__FormatterKeys)
MAYA_LOG_PATH = "W:/workspsace/cache_manager_logs/{f.EPI}/{f.NAME}_maya_log.log".format(f=__FormatterKeys)

SUCCESS_CODE = "CACHE_JOB_IS_SUCCESSFUL_BY_CACHE_MANAGER"
TRACEBACK_TRACKER = "~~~TRACE-TRACEBACK~~~"
LOG_PATH_ENV = "CACHE_MANAGER_TOOL_LOG_PATH"

# LOG_VIEWER = "explorer"
LOG_VIEWER = "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"
