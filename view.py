import os
import sys
from PySide2 import QtWidgets, QtCore, QtGui
from functools import partial
import datetime
import subprocess
import threading
import config
LOG_PATH = config.LOGGING_PATH.format(**{config.FormatterKeys.STAMP: datetime.datetime.now().strftime("%Y_%m_%d__%H_%M_%S")})
os.environ[config.LOG_PATH_ENV] = LOG_PATH
from ui import cache_manager_ui
import core
import app_logger
import utils


LOGGER = app_logger.get_logger(__name__, file=LOG_PATH)


class CustomFileView(QtWidgets.QListWidgetItem):

    maya_file = None  # type: core.MayaFile

    def __init__(self, maya_file):
        super(CustomFileView, self).__init__()
        self.maya_file = maya_file

        self.setText(self.maya_file.display)
        self.setToolTip(self.maya_file.file_path)


class CustomReferencesView(QtWidgets.QListWidgetItem):
    reference_instance = None  # type: core.Reference

    def __init__(self, reference_instance):
        super(CustomReferencesView, self).__init__()
        self.reference_instance = reference_instance

        self.setText(self.reference_instance.display)
        self.setToolTip("({}), {}".format(
            "Cacheable" if self.reference_instance.is_cacheable else "Not Cacheable",
            self.reference_instance.reference_path)
        )

        if not self.reference_instance.is_cacheable:
            self.setBackgroundColor("#aeafb0")
            self.setFlags(~QtCore.Qt.ItemIsSelectable)


class SortType(object):
    DEFAULT = "default"
    STATUS = "status"
    FILE_NAME = "file_name"


class CustomJobView(QtWidgets.QListWidgetItem):
    job_instance = None  # type: core.Job

    def __init__(self, job_instance):
        super(CustomJobView, self).__init__()
        self.job_instance = job_instance

        self.setText(self.job_instance.display_name)
        self.setToolTip(self.job_instance.tool_tip)

        self.change_color(self.job_instance.status)
        self.job_instance.SIGNAL.connect(self.change_color)

    def change_color(self, status):
        if status == core.Job.IP:
            self.setBackgroundColor("#e8e846")
        elif status == core.Job.DONE:
            self.setBackgroundColor("#4fdb58")
        elif status == core.Job.ERROR:
            self.setBackgroundColor("#e84646")
        elif status == core.Job.IN_QUEUE:
            self.setBackgroundColor("#aeafb0")


class JobRunner(threading.Thread):
    def __init__(self, job_signal):
        super(JobRunner, self).__init__()
        self.job_signal = job_signal
        self.jobs_to_run = []

    def run(self):
        self.job_signal.emit(True)
        for job in self.jobs_to_run:
            job.execute()
        self.job_signal.emit(False)


class Main(QtWidgets.QMainWindow, cache_manager_ui.Ui_MainWindow):
    IS_JOB_RUNNING = QtCore.Signal(bool)

    @utils.safe_run
    def __init__(self):
        super(Main, self).__init__()
        self.setupUi(self)

        self.setWindowTitle("Cache Manager")

        self.populate_projects()
        self.on_project_change()
        self.connect_events()

        self.all_jobs_queue = []
        LOGGER.info("cache manager open successfully")

        if not os.path.exists(config.MAYA_BATCH):
            QtWidgets.QMessageBox.warning(self, "Maya Not Found", "Maya 2020 not found, Tool can't run.")
            self.close()

    def connect_events(self):
        self.project_combo.currentTextChanged.connect(self.on_project_change)
        self.epsoide_combo.currentTextChanged.connect(self.on_epsoide_change)
        self.files_list_w.itemSelectionChanged.connect(self.update_reference)
        self.select_all_button.clicked.connect(self.select_all_reference)
        self.deselect_all_button.clicked.connect(self.deselect_all_reference)
        self.delete_job.clicked.connect(self.delete_jobs)
        self.process_jobs.clicked.connect(self.start_process_jobs)

        self.all_assets.clicked.connect(partial(self.filter_reference, "All"))
        self.char_assets.clicked.connect(partial(self.filter_reference, "Char"))
        self.prop_assets.clicked.connect(partial(self.filter_reference, "Prop"))

        self.files_list_w.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.files_list_w.customContextMenuRequested.connect(self.files_context_menu)

        self.reference_list_w.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.reference_list_w.customContextMenuRequested.connect(self.reference_context_menu)

        self.jobs_queue_list_w.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.jobs_queue_list_w.customContextMenuRequested.connect(self.jobs_context_menu)

        self.IS_JOB_RUNNING.connect(self.switch_job_mode)

    def switch_job_mode(self, is_job_running):
        if is_job_running:
            self.enable_job_mode()

        else:
            self.disable_job_mode()

    def enable_job_mode(self):
        self.project_combo.setEnabled(False)
        self.epsoide_combo.setEnabled(False)
        self.files_list_w.setEnabled(False)
        self.reference_list_w.setEnabled(False)

    def disable_job_mode(self):
        self.project_combo.setEnabled(True)
        self.epsoide_combo.setEnabled(True)
        self.files_list_w.setEnabled(True)
        self.reference_list_w.setEnabled(True)

    def files_context_menu(self, point):
        self.files_popup_menu = QtWidgets.QMenu(self)
        action = self.files_popup_menu.addAction("Add to Queue")
        action.triggered.connect(self.create_job)
        self.files_popup_menu.exec_(self.files_list_w.mapToGlobal(point))

    def reference_context_menu(self, point):
        self.referecne_popup_menu = QtWidgets.QMenu(self)
        action = self.referecne_popup_menu.addAction("Create Job from selected")
        action.triggered.connect(self.create_job)
        self.referecne_popup_menu.exec_(self.reference_list_w.mapToGlobal(point))

    def jobs_context_menu(self, point):
        self.jobs_popup_menu = QtWidgets.QMenu(self)
        sort_options = self.jobs_popup_menu.addAction("Sorting options")
        sort_options.setEnabled(False)
        self.jobs_popup_menu.addSeparator()
        sort_by_status = self.jobs_popup_menu.addAction("by status")
        sort_by_default = self.jobs_popup_menu.addAction("by default")
        sort_by_name = self.jobs_popup_menu.addAction("by file name")
        sort_by_status.triggered.connect(partial(self.sort_jobs, SortType.STATUS))
        sort_by_default.triggered.connect(partial(self.sort_jobs, SortType.DEFAULT))
        sort_by_name.triggered.connect(partial(self.sort_jobs, SortType.FILE_NAME))

        self.jobs_popup_menu.addSeparator()
        job_options = self.jobs_popup_menu.addAction("Job options")
        self.jobs_popup_menu.addSeparator()
        job_options.setEnabled(False)
        delete_job = self.jobs_popup_menu.addAction("Delete")
        re_queue = self.jobs_popup_menu.addAction("Re-Queue")

        delete_job.triggered.connect(self.delete_jobs)
        re_queue.triggered.connect(self.re_queue_jobs)

        self.jobs_popup_menu.addSeparator()
        log_options = self.jobs_popup_menu.addAction("Log options")
        self.jobs_popup_menu.addSeparator()
        log_options.setEnabled(False)
        open_log = self.jobs_popup_menu.addAction("Open Cache manager Log")
        maya_log = self.jobs_popup_menu.addAction("Open Maya output Log")

        open_log.triggered.connect(self.open_log)
        maya_log.triggered.connect(self.open_maya_log)

        self.jobs_popup_menu.exec_(self.jobs_queue_list_w.mapToGlobal(point))

    def sort_jobs(self, sort_type):
        if sort_type == SortType.DEFAULT:
            jobs_list = self.all_jobs_queue

        elif sort_type == SortType.FILE_NAME:
            jobs_list = sorted(self.all_jobs_queue, key=lambda x: x.maya_file_instance.file_name)

        else:
            jobs_list = sorted(self.all_jobs_queue, key=lambda x: x.status)

        self.jobs_queue_list_w.clear()
        for job in jobs_list:
            item = CustomJobView(job)
            self.jobs_queue_list_w.addItem(item)

    def populate_projects(self):
        self.project_combo.addItem("Pirate Academy")
        self.project_combo.setEnabled(False)

    @utils.safe_run
    def on_project_change(self, *args):
        LOGGER.info("populating episode")
        epsoide_list = core.get_epsoide_list()

        self.epsoide_combo.blockSignals(True)

        self.epsoide_combo.clear()
        self.files_list_w.clear()
        self.reference_list_w.clear()
        self.epsoide_combo.addItems(epsoide_list)
        self.epsoide_combo.setCurrentIndex(-1)
        LOGGER.info("episode populated: {}".format(epsoide_list))

        self.epsoide_combo.blockSignals(False)

    @utils.safe_run
    def on_epsoide_change(self, *args):
        project = str(self.project_combo.currentText())
        episode = str(self.epsoide_combo.currentText())

        LOGGER.info("getting maya files for project: {}, episode: {}".format(project, episode))
        maya_files = core.get_maya_files(project, episode)
        LOGGER.info("got total files: {}".format(len(maya_files)))
        self.files_list_w.clear()
        self.reference_list_w.clear()

        for maya_file in maya_files:
            item = CustomFileView(maya_file)
            self.files_list_w.addItem(item)

        LOGGER.info("files populated")

    @utils.safe_run
    def update_reference(self, *args):
        LOGGER.info("populating references")
        selected_file = self.files_list_w.selectedItems()  # type: list[CustomFileView]
        self.reference_list_w.clear()

        if selected_file and len(selected_file) < 2:
            for reference in selected_file[0].maya_file.references:
                item = CustomReferencesView(reference)
                self.reference_list_w.addItem(item)
        LOGGER.info("references populated")

    def filter_reference(self, filter_type):
        selected_file = self.files_list_w.selectedItems()  # type: list[CustomFileView]
        self.reference_list_w.clear()

        if selected_file and len(selected_file) < 2:
            for reference in selected_file[0].maya_file.references:
                if filter_type == "All" and reference.asset_type in ["Char", "Prop", "Camera"]:
                    item = CustomReferencesView(reference)

                elif filter_type == "Char" and reference.asset_type == "Char":
                    item = CustomReferencesView(reference)

                elif filter_type == "Prop" and reference.asset_type == "Prop":
                    item = CustomReferencesView(reference)

                else:
                    continue

                self.reference_list_w.addItem(item)

    @utils.safe_run
    def create_job(self, *args):
        LOGGER.info("creating job")
        selected_files = self.files_list_w.selectedItems()  # type: list[CustomFileView]
        if selected_files and len(selected_files) < 2:
            selected_reference = [i.reference_instance for i in self.reference_list_w.selectedItems()] or core.Job.ALL_REFERENCE
        else:
            selected_reference = core.Job.ALL_REFERENCE

        project = str(self.project_combo.currentText())
        episode = str(self.epsoide_combo.currentText())

        for selected_file in selected_files:
            job = core.Job(project, episode, selected_file.maya_file, selected_reference)
            if self.check_if_job_exists(job):
                message = "Job you wanted to create, already exists in job queue. skipping:\n\tFile: {}\n\tselected reference: {}".format(
                    job.maya_file_instance.file_name, selected_reference if isinstance(selected_reference, str) else "\n\t\t".join([s.reference_node for s in selected_reference])
                )
                LOGGER.warning(message)
                QtWidgets.QMessageBox.warning(self, "Job already exists", message)
                return

            item = CustomJobView(job)
            self.jobs_queue_list_w.addItem(item)
            self.all_jobs_queue.append(job)
        LOGGER.info("job created.")

    def delete_jobs(self):
        for item in self.jobs_queue_list_w.selectedItems():
            self.jobs_queue_list_w.takeItem(self.jobs_queue_list_w.row(item))

    def re_queue_jobs(self):
        for item in self.jobs_queue_list_w.selectedItems():  # type: CustomJobView
            if item.job_instance.status == core.Job.ERROR:
                item.job_instance.status = core.Job.IN_QUEUE
                item.change_color(core.Job.IN_QUEUE)
                LOGGER.info("{} is re-queued".format(item.job_instance))
            else:
                LOGGER.warning("only error jobs can be re-queue, skipping job: {}".format(item.job_instance))

    @staticmethod
    def open_log():
        subprocess.Popen("{} file:///{}".format(config.LOG_VIEWER, LOG_PATH.replace("\\", "/")))

    def open_maya_log(self):
        for item in self.jobs_queue_list_w.selectedItems():  # type: CustomJobView
            name = os.path.basename(os.path.splitext(item.job_instance.maya_file_instance.file_path)[0])
            log_path = config.MAYA_LOG_PATH.format(**{
                config.FormatterKeys.NAME: name,
                config.FormatterKeys.EPI: item.job_instance.epsoide,
            })
            if os.path.exists(log_path):
                subprocess.Popen("{} file:///{}".format(config.LOG_VIEWER, log_path.replace("\\", "/")))

            else:
                LOGGER.warning("maya log path don't exists, {}".format(log_path))

    def check_if_job_exists(self, job):
        all_jobs = [self.jobs_queue_list_w.item(i).job_instance for i in range(self.jobs_queue_list_w.count())]
        for each_job in all_jobs:  # type: core.Job
            if each_job == job:
                return True

    def select_all_reference(self):
        self.reference_list_w.selectAll()

    def deselect_all_reference(self):
        self.reference_list_w.clearSelection()

    @utils.safe_run
    def start_process_jobs(self, *args):
        LOGGER.info("creating job runner")
        runner = JobRunner(self.IS_JOB_RUNNING)
        for i in range(self.jobs_queue_list_w.count()):
            item = self.jobs_queue_list_w.item(i)  # type: CustomJobView
            runner.jobs_to_run.append(item.job_instance)

        LOGGER.info("runner crated")
        runner.start()


if __name__ == '__main__':
    LOGGER.info("starting application")
    app = QtWidgets.QApplication(sys.argv)
    ins = Main()
    ins.show()
    app.exec_()
    LOGGER.info("application closed")
