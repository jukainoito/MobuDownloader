# coding:utf-8

from PyQt5.QtCore import (Qt, QAbstractTableModel, QModelIndex, QVariant)

'''
from https://blog.csdn.net/yy123xiang/article/details/78739975
'''


class TableModel(QAbstractTableModel):
    def __init__(self, parent=None, data=[]):
        super().__init__(parent)
        self.tableData = data
        self.columnLabels = ["", "章节", "页数", "状态"]
        self.columnKeys = ["sel", "episode", "pageSize", "status"]

    def rowCount(self, QModelIndex):
        return len(self.tableData)

    def columnCount(self, QModelIndex):
        return len(self.columnLabels)-2

    def data(self, index, role):
        row = index.row()
        col = index.column()
        if role == Qt.DisplayRole:
            return self.tableData[row][self.columnKeys[col+1]]
        elif role == Qt.CheckStateRole:
            if col == 0:
                return Qt.Checked if self.tableData[row][self.columnKeys[0]] is True else Qt.Unchecked
        return QVariant()

    def setData(self, index, value, role):
        row = index.row()
        col = index.column()
        if role == Qt.CheckStateRole and col == 0:
            self.tableData[row][self.columnKeys[0]] = True if value == Qt.Checked else False
        return True

    def flags(self, index):
        if index.column() == 0:
            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
        return Qt.ItemIsEnabled

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.columnLabels[section+1]

    def headerClick(self, isOn):
        self.beginResetModel()
        for index in range(len(self.tableData)):
            self.tableData[index][self.columnKeys[0]] = isOn
        self.endResetModel()

    def flush(self):
        self.beginResetModel()
        self.endResetModel()

