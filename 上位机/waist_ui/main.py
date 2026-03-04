# coding: utf-8
"""
主程序入口
初始化应用程序，创建主窗口
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName('康复医疗仪表盘')

    # 加载样式
    qss_file = Path(__file__).parent / 'resource' / 'light' / 'demo.qss'
    if qss_file.exists():
        with open(qss_file, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    # 创建主窗口
    w = MainWindow()
    w.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
