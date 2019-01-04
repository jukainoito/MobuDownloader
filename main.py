# coding:utf-8

import sys
from PyQt5.QtWidgets import (QWidget, QApplication, QPushButton, QLineEdit, QLabel,
                             QAbstractItemView, QTableView, QMessageBox)
from PyQt5.QtCore import (Qt, QThread, pyqtSignal)
from PyQt5.QtGui import (QStandardItemModel, QStandardItem)
from widgets import *
from manga_site import *

from urllib.parse import urlparse
import time


class InfoWorker(QThread):
    finSignal = pyqtSignal(dict)

    def __init__(self, downloadObj, parent=None):
        QThread.__init__(self, parent)
        self.downloadObj = downloadObj

    def run(self):
        data = self.downloadObj.info()
        self.finSignal.emit(data)


class DownloadWorker(QThread):
    finSignal = pyqtSignal()
    flushSignal = pyqtSignal()

    def __init__(self, downloadObj, data, parent=None):
        QThread.__init__(self, parent)
        self.downloadObj = downloadObj
        self.data = data

    def run(self):
        self.downloadObj.download(self.data)
        while True:
            if self.downloadObj.done():
                break
            self.flushSignal.emit()
            time.sleep(1)
        self.finSignal.emit()


class App(QWidget):
     
    def __init__(self):
        super().__init__()

        self.title = "mobu tool v0.03 - only support mangapoke and ComicWalker"
        self.left = 100
        self.top = 100
        self.width = 500
        self.height = 350

        self.data = []

        self.url_edit = QLineEdit(self)
        self.url_btn = QPushButton("获取", self)
        self.download_btn = QPushButton("下载", self)
        self.title_label = QLabel(" ", self)
        self.table_view = QTableView(self)
        self.table_model = TableModel(self.table_view, self.data)

        self.init_ui()

        # self.siteClass = None
        self.downloadObj = None
        # self.raw_data = None
        self.info_worker = None
        self.download_worker = None
        self.raw_data = None

    def init_ui(self):
        self.setWindowFlags(Qt.Window |
                            Qt.CustomizeWindowHint |
                            Qt.WindowMinimizeButtonHint |
                            Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint
                            # | Qt.WindowStaysOnTopHint
                            )
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setWindowTitle(self.title)
        self.setFixedSize(self.width, self.height)

        # self.url_edit = QLineEdit(self)
        self.url_edit.setStyleSheet("color: black;")
        self.url_edit.setPlaceholderText("请输入目标网址")
        self.url_edit.setGeometry(5, 5, 410, 32)

        # self.url_btn = QPushButton("获取", self)
        self.url_btn.setGeometry(420, 5, 70, 32)
        self.url_btn.clicked.connect(self.get_info)

        # self.download_btn = QPushButton("下载", self)
        self.download_btn.setGeometry(420, 40, 70, 32)
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.download)

        # self.title_label = QLabel(" ", self)
        # self.title_label.setGeometry(5, 70, 490, 32)
        self.title_label.setGeometry(5, 40, 400, 32)

        # self.table_view = QTableView(self)
        # self.table_view.setGeometry(5, 100, 490, 240)
        self.table_view.setGeometry(5, 80, 490, 270)
        self.table_view.setStyleSheet("color: black;")
        self.table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # self.table_model = TableModel(self.table_view, self.data)
        self.table_view.setModel(self.table_model)
        header = CheckBoxHeader()

        self.table_view.setHorizontalHeader(header)

        header.clicked.connect(self.table_model.headerClick)

        header = self.table_view.horizontalHeader()

        header.resizeSection(0, 383)
        # header.resizeSection(1, 50)
        # header.resizeSection(2, 50)
        header.resizeSection(1, 70)

        self.show()

    def get_info(self):
        self.get_info_start()

        url = self.url_edit.text()
        site = self.get_site(url)

        if site in sites.keys():
            siteClass = sites[site]
            self.downloadObj = siteClass(url)
            # self.raw_data = self.downloadObj.info()
            # self.set_info(self.downloadObj.info())
            self.info_worker = InfoWorker(downloadObj=self.downloadObj)
            self.info_worker.finSignal.connect(self.set_info)
            self.info_worker.start()

        else:
            QMessageBox.warning(self, "warning", "Unsupport site", QMessageBox.Cancel)
            self.get_info_end()

    @staticmethod
    def get_site(url):
        if url.find(r'//') == -1:
            url = '//' + url
        netloc = urlparse(url).netloc
        return netloc

    def get_info_start(self):
        self.url_btn.setEnabled(False)
        self.url_edit.setEnabled(False)
        self.title_label.setText(" ")

    def get_info_end(self):
        self.url_btn.setEnabled(True)
        self.url_edit.setEnabled(True)
        self.download_btn.setEnabled(True)

    def set_info(self, manga_data):
        self.raw_data = manga_data
        self.set_title(manga_data["title"])
        self.data.clear()
        self.data.extend(manga_data["episodes"])
        self.table_model.flush()
        self.get_info_end()

    def set_title(self, title):
        self.title_label.setText(title)
        self.title_label.setToolTip(title)

    def download(self):
        count = self.download_start()
        if count != 0:
            self.set_download_status(True)
            # self.downloadObj.download(self.raw_data)
            self.download_worker = DownloadWorker(self.downloadObj, self.raw_data)
            self.download_worker.flushSignal.connect(self.table_model.flush)
            self.download_worker.finSignal.connect(self.download_end)
            self.download_worker.start()
        else:
            self.download_end()

    def download_start(self):
        count = 0
        for episode in self.raw_data["episodes"]:
            if episode["sel"]:
                count += 1
                episode["status"] = "准备"
        self.table_model.flush()

        return count

    def download_end(self):
        for episode in self.raw_data["episodes"]:
            if episode["sel"]:
                episode["status"] = "完成"
        self.set_download_status(False)
        QMessageBox.information(self, "下载完成", "下载完成", QMessageBox.Ok)

    def set_download_status(self, flag):
        self.url_edit.setEnabled(not flag)
        self.url_btn.setEnabled(not flag)
        self.download_btn.setEnabled(not flag)


if __name__ == '__main__':
     
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
