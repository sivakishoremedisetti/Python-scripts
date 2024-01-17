import os
import sys
import logging
import config

try:
    import maya.cmds.about

    _in_maya = True
except Exception:
    _in_maya = False

MSG_FORMAT = "%(asctime)s %(name)s %(levelname)s : %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Levels - same as logging module
CRITICAL = 50
FATAL = CRITICAL
ERROR = 40
WARNING = 30
WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0


def get_logger(name, shell=False, maya=_in_maya, file=None, level=INFO):
    """
    Get logger - mimicing the usage of logging.getLogger()
        name(str) : logger name
        shell(bol): output to shell
        maya(bol) : output to maya editor
        nuke(bol) : output to nuke editor
        file(str) : output to given filename
        level(int): logger level
    """
    if not file:
        file = os.environ[config.LOG_PATH_ENV]

    if file:
        dirname = os.path.dirname(file)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    return Logger(name, shell, maya, file, level)


class Logger():
    """
    """

    def __init__(self, name, shell=True, maya=False, file=None, level=INFO):
        """
        Init Logger
        """

        self.__name = name
        self.__logger = logging.getLogger(name)
        self.__logger.setLevel(level)

        if self.__logger.handlers:
            return

        # Format
        format = logging.Formatter(MSG_FORMAT, DATE_FORMAT)

        # Shell:
        if shell:
            stream_hdlr = ShellHandler()
            stream_hdlr.setFormatter(format)
            self.__logger.addHandler(stream_hdlr)

        # File:
        if file:
            file_hdlr = logging.FileHandler(file)
            file_hdlr.setFormatter(format)
            self.__logger.addHandler(file_hdlr)

        # Maya:
        if maya and _in_maya:
            maya_hdlr = MayaHandler()
            maya_hdlr.setFormatter(format)
            self.__logger.addHandler(maya_hdlr)

    def __repr__(self):
        """
        string representation.
        """
        return "%s(%s Level:%i)" % (self.__class__, self.__name, self.level)

    def __getattr__(self, attr):
        """
        Use logging.Logger attributes.
        """
        if hasattr(self.__logger, attr):
            return getattr(self.__logger, attr)
        else:
            raise AttributeError("No attribute %s" % attr)

    def debug(self, msg):
        self.__logger.debug(msg)

    def info(self, msg):
        self.__logger.info(msg)

    def warning(self, msg):
        self.__logger.warning(msg)

    def fatal(self, msg):
        self.__logger.fatal(msg)

    def critical(self, msg):
        self.__logger.critical(msg)


class ShellHandler(logging.Handler):
    """
    Shell Handler - emits logs to shell only.
    by passing maya and nuke editors by using sys.__stdout__
    """

    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):

        try:
            sys.__stdout__.write("%s\n" % self.format(record))
        except IOError:
            sys.stdout.write("%s\n" % self.format(record))


class MayaHandler(logging.Handler):
    """
    Maya Handler - emits logs into maya's script editor.
    warning will emit maya.cmds.warning()
    critical and fatal would popup msg dialog to alert of the error.
    """

    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):

        # Formated message:
        msg = self.format(record)

        if record.funcName == "warning":
            maya.cmds.warning("\n" + msg)

        elif record.funcName in ["critical", "fatal"]:
            sys.stdout.write("\n" + msg + "\n")

        else:
            sys.stdout.write(msg + "\n")


if __name__ == '__main__':
    log = get_logger("logger_name", shell=True)
    log.setLevel(logging.DEBUG)
    log.debug('debug msg')
    log.info('info msg')
    log.warning('warning msg')
    log.fatal('fatal msg')
