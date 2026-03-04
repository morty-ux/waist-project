<!-- Copilot instructions for the PySide6 QFluentWidgets demo app -->
# 项目速览与 AI 助手指南

这是一个 **PySide6 + QFluentWidgets** GUI 演示工程，采用现代 Fluent Design System。下面的要点让 AI 编码代理快速理解架构并避免常见陷阱。

## 核心架构

### 两个应用入口（需知道区别）
- **`demo.py`**（推荐）：完整演示应用，展示 QFluentWidgets 的所有能力
  - 使用 `FramelessWindow` + `NavigationInterface`（侧边栏导航）
  - 支持深色/浅色主题切换（QSS 文件驱动）
  - 特点：页面多、导航复杂、主题管理集中
  
- **`main.py`**：简化示例，使用传统 `QMainWindow`
  - 使用生成的 UI 类 `Ui_MainWindow`（来自 `ui_untitled.py`）
  - 仅作参考用途，实际开发通常扩展 `demo.py` 的模式

### 核心依赖与版本
```
PySide6          # Qt Python 绑定
qfluentwidgets   # 微软 Fluent Design 组件库（按钮、导航、对话框等）
qframelesswindow # 无边框窗口 + 自定义标题栏
```

### 文件职责
| 文件 | 用途 | 编辑规则 |
|------|------|--------|
| `demo.py` | 主应用逻辑与 UI 容器 | **直接编辑** ✓ |
| `main.py` | 传统 QMainWindow 示例 | 参考用，勿改 |
| `untitled.ui` | Qt Designer 源文件 | **直接编辑** ✓（设计器） |
| `ui_untitled.py` | 由 `pyside6-uic` 自动生成 | **禁止手工编辑** ✗ |
| `resource/*/demo.qss` | 主题样式表（Light/Dark） | **直接编辑** ✓（修改颜色/字体） |

## 关键工作流

### 1. UI 修改流程
如需修改 UI 布局（按钮、输入框位置等）：
```bash
# 步骤 1: 用 Qt Designer 打开 untitled.ui
# 步骤 2: 进行设计修改
# 步骤 3: 重新生成 Python 文件
pyside6-uic untitled.ui -o ui_untitled.py

# 步骤 4: 在 main.py 中继承 Ui_MainWindow 并添加逻辑
```

### 2. 主题定制流程（推荐方式）
修改应用全局外观时，编辑 QSS 文件而非硬编码 StyleSheet：
```
resource/
├── light/demo.qss    # 浅色主题配置
└── dark/demo.qss     # 深色主题配置
```

示例修改（在 `resource/light/demo.qss`）：
```css
Widget {
    border-left: 1px solid rgb(6, 104, 240);      /* 修改左边框色 */
    background-color: rgb(255, 255, 255);         /* 修改背景 */
}
```

`demo.py` 中自动加载主题：
```python
def setQss(self):
    color = 'dark' if isDarkTheme() else 'light'
    with open(f'resource/{color}/demo.qss', encoding='utf-8') as f:
        self.setStyleSheet(f.read())
```

### 3. 导航与页面管理
`demo.py` 使用 `QStackedWidget` + `NavigationInterface` 管理多页面：
```python
self.stackWidget = QStackedWidget(self)
self.navigationInterface = NavigationInterface(self)

# 添加页面
self.addSubInterface(self.musicInterface, FIF.MUSIC, 'Music library')

# 支持嵌套导航（父子关系）
self.addSubInterface(self.albumInterface1, FIF.ALBUM, 'Album 1', 
                     parent=self.albumInterface)
```

切换页面时 `stackWidget` 自动翻页，`NavigationInterface` 更新高亮项。

## 常见陷阱与规则

| 陷阱 | 后果 | 解决方案 |
|------|------|--------|
| 直接修改 `ui_untitled.py` | 下次重新生成时被覆盖 | 仅编辑 `.ui` 或继承 UI 类 |
| 硬编码 StyleSheet 覆盖 QFW 样式 | 主题切换时样式混乱，交互态不同步 | 编辑 QSS 文件或用 `setThemeColor()` |
| 导入 `Ui_LoginWindow` (main.py 中的旧名) | 导入错误崩溃 | 改为 `from ui_untitled import Ui_MainWindow` |
| 在非 QFluentWidgets 组件上强制应用 QFW 主题 | 颜色不协调或无效果 | 使用 `FluentWidget`, `PushButton`, `LineEdit` 等 QFW 组件 |

## 运行 & 调试

### 环境配置
```powershell
# Windows PowerShell - 激活虚拟环境
E:/QT for Python/venv/Scripts/Activate.ps1

# 或直接用完整路径
& "E:/QT for Python/venv/Scripts/python.exe" "e:/QT for Python/pyside/demo.py"
```

### 常用命令速查
```bash
# 运行主应用
python demo.py

# 重新生成 UI 类（修改 .ui 后）
pyside6-uic untitled.ui -o ui_untitled.py

# 安装/更新依赖
pip install PySide6 qfluentwidgets qframelesswindow

# 翻译生成（如需多语言）
pyside6-lupdate *.py -ts translations.ts
```

## 架构参考图
```
Window (FramelessWindow)
  ├─ TitleBar (StandardTitleBar)
  ├─ NavigationInterface (左侧栏)
  │   ├─ Navigation Items (Music, Video, Albums...)
  │   └─ Bottom Items (Settings, Avatar...)
  └─ StackedWidget (内容区)
      ├─ Widget(Search Interface)
      ├─ Widget(Music Interface)
      └─ ... 更多页面
```

## 关键代码位置
- **应用入口主逻辑**: [demo.py](demo.py#L24)（`Window.__init__` 方法）
- **页面切换逻辑**: [demo.py](demo.py#L152)（`switchTo` 方法）
- **主题管理**: [demo.py](demo.py#L145)（`setQss` 方法）
- **主题文件（Light）**: [resource/light/demo.qss](resource/light/demo.qss)
- **主题文件（Dark）**: [resource/dark/demo.qss](resource/dark/demo.qss)

---

## AI 代理工作流指南

### 修改 UI 布局或逻辑时
1. **优先编辑 `demo.py`** 而非 `main.py`（demo 是功能完整的参考实现）
2. **不要直接改 `ui_untitled.py`**（自动生成文件）
3. 若需修改 UI 设计器中的元素，编辑 `untitled.ui` 后重新生成

### 修改主题、颜色或样式时
1. **优先编辑 QSS 文件** (`resource/light/demo.qss`, `resource/dark/demo.qss`)
2. **避免硬编码 StyleSheet** 覆盖 QFluentWidgets 组件样式
3. 若需动态颜色切换，使用 `setThemeColor()` API 而非 `setStyleSheet()`

### 添加新页面或功能时
```python
# 1. 创建页面类（继承 QFrame）
self.newPage = Widget('My New Page', self)

# 2. 添加到 StackedWidget
self.addSubInterface(self.newPage, FIF.ICON_NAME, 'Page Label')

# 3. 若需要嵌套，传入 parent 参数
self.addSubInterface(child, FIF.ICON, 'Child', parent=self.newPage)
```

## 颜色配置速查表

| 组件 | Light 配置 | Dark 配置 | 编辑位置 |
|------|----------|---------|--------|
| 页面左边框 | `rgb(6, 104, 240)` 蓝 | `rgb(197, 205, 214)` 灰 | `resource/*/demo.qss` |
| 页面背景 | `rgb(255, 255, 255)` 白 | `rgb(255, 255, 255)` 白 | `resource/*/demo.qss` |
| 窗口背景 | `rgb(152, 153, 154)` 灰 | `rgb(200, 200, 200)` 灰 | `resource/*/demo.qss` |

修改后运行 `python demo.py` 即可看到实时效果。
