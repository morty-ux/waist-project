from qfluentwidgets import setThemeColor
from qfluentwidgets import FluentTranslator
from ui_myui import Ui_MainWindow

import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QIcon
from PySide6.QtCore import QLocale


class LoginWindow(QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # change theme color
        setThemeColor('#28afe9')

        # Note: AcrylicWindow-specific titlebar/windowEffect calls removed
        self.setWindowTitle('PyQt-Fluent-Widget')
        try:
            self.setWindowIcon(QIcon(":/images/logo.png"))
        except Exception:
            pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.installTranslator(FluentTranslator(QLocale()))
    w = LoginWindow()
    w.show()
    app.exec()