from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QCheckBox, 
    QTreeWidget, QTreeWidgetItem, QPushButton, QScrollArea, QLabel, QFrame, QApplication, QStyle, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QThread
import os

class Card(QWidget):
    def __init__(self, start_path=".", initial_state=None, parent=None):
        super().__init__(parent)
        
        if initial_state:
            self.current_path = os.path.abspath(initial_state.get("path", start_path))
        else:
            self.current_path = os.path.abspath(start_path)
            
        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)

        # 1. Search Section
        self.search_layout = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search...")
        self.regex_check = QCheckBox("Regex")
        
        self.search_layout.addWidget(self.search_entry)
        self.search_layout.addWidget(self.regex_check)
        self.layout.addLayout(self.search_layout)

        # 2. Copy Buttons
        self.copy_layout = QHBoxLayout()
        self.copy_name_btn = QPushButton("Copy Name")
        self.copy_no_ext_btn = QPushButton("Copy Name (No Ext)")
        self.copy_path_btn = QPushButton("Copy Path")
        self.copy_layout.addWidget(self.copy_name_btn)
        self.copy_layout.addWidget(self.copy_no_ext_btn)
        self.copy_layout.addWidget(self.copy_path_btn)
        self.layout.addLayout(self.copy_layout)

        # 3. File List
        self.file_list = QTreeWidget()
        self.file_list.setHeaderLabels(["Name", "Path"]) # Hidden path column for logic
        self.file_list.setColumnHidden(1, True) 
        self.file_list.setAlternatingRowColors(True)
        self.layout.addWidget(self.file_list)

        # 4. Path Navigation (Vertical Indented)
        self.path_scroll = QScrollArea()
        self.path_scroll.setWidgetResizable(True)
        self.path_container = QWidget()
        self.path_layout = QVBoxLayout(self.path_container)
        self.path_layout.setAlignment(Qt.AlignTop)
        self.path_layout.setContentsMargins(0, 0, 0, 0)
        self.path_layout.setSpacing(2)
        
        self.path_scroll.setWidget(self.path_container)
        self.layout.addWidget(self.path_scroll)

        # 5. Path Entry (Bottom)
        self.path_layout_bottom = QHBoxLayout()
        self.path_entry_bottom = QLineEdit()
        self.path_entry_bottom.setPlaceholderText("Full Path")
        self.browse_btn = QPushButton("Browse")
        self.path_layout_bottom.addWidget(self.path_entry_bottom)
        self.path_layout_bottom.addWidget(self.browse_btn)
        self.layout.addLayout(self.path_layout_bottom)
        
        # Connect signals
        self.file_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.search_entry.textChanged.connect(self.refresh_file_list)
        self.regex_check.stateChanged.connect(self.refresh_file_list)
        self.path_entry_bottom.returnPressed.connect(self.on_path_entry_return)
        self.browse_btn.clicked.connect(self.browse_directory)
        
        self.copy_name_btn.clicked.connect(lambda: self.copy_to_clipboard("name"))
        self.copy_no_ext_btn.clicked.connect(lambda: self.copy_to_clipboard("no_ext"))
        self.copy_path_btn.clicked.connect(lambda: self.copy_to_clipboard("path"))

        # Apply initial state if provided
        if initial_state:
            self.search_entry.setText(initial_state.get("search_text", ""))
            self.regex_check.setChecked(initial_state.get("use_regex", False))

        # Initial Load
        self.refresh_ui()

    def get_state(self):
        return {
            "path": self.current_path,
            "search_text": self.search_entry.text(),
            "use_regex": self.regex_check.isChecked()
        }

    def refresh_ui(self):
        self.path_entry_bottom.setText(self.current_path)
        self.update_path_nav()
        self.refresh_file_list()

    def update_path_nav(self):
        # Clear existing
        for i in reversed(range(self.path_layout.count())):
            self.path_layout.itemAt(i).widget().setParent(None)

        # Build path components
        path = self.current_path
        parts = []
        while True:
            parent, tail = os.path.split(path)
            if tail:
                parts.insert(0, (path, tail))
            else:
                if parent:
                    parts.insert(0, (parent, parent))
                break
            path = parent
        
        # Add buttons with indentation
        for i, (full_path, name) in enumerate(parts):
            btn = QPushButton(name if name else split_path)
            
            indent_px = i * 10
            btn.setStyleSheet(f"text-align: left; padding-left: {indent_px}px; border: none; hover: {{ background: #ddd; }}")
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)
            # Lambda capture binding
            btn.clicked.connect(lambda checked=False, p=full_path: self.navigate_to(p))
            
            self.path_layout.addWidget(btn)

        # Update height
        self.path_container.adjustSize()
        # Calculate height: somewhat heuristic or use sizeHint if valid
        # Layout needs a moment, but adjustSize usually forces calculation
        # Let's try explicit calculation to be sure:
        # 30px approximate per button?
        # Better: use sizeHint
        h = self.path_container.sizeHint().height()
        # Cap max height to avoid taking too much space (e.g. 150px)
        # But user said "minimum necessary", so expanding is good, but scrolling if HUGE.
        max_h = 200
        target_h = min(h, max_h)
        # Add a little padding for borders if needed
        self.path_scroll.setFixedHeight(target_h + 5)

    def refresh_file_list(self):
        # Stop existing thread if running
        try:
            if hasattr(self, 'loader_thread') and self.loader_thread:
                if self.loader_thread.isRunning():
                    self.loader_thread.stop()
                    self.loader_thread.wait()
        except RuntimeError:
            pass
        self.loader_thread = None

        self.file_list.clear() # Clear immediately for feedback
        
        search_text = self.search_entry.text()
        use_regex = self.regex_check.isChecked()
        
        self.loader_thread = FileLoaderThread(self.current_path, search_text, use_regex)
        self.loader_thread.batch_ready.connect(self.add_batch_to_list)
        self.loader_thread.finished.connect(self.loader_thread.deleteLater)
        self.loader_thread.start()

    def add_batch_to_list(self, items):
        # items is a list of (name, is_dir, full_path)
        for name, is_dir, full_path in items:
            tree_item = QTreeWidgetItem(self.file_list)
            tree_item.setText(0, name)

            if is_dir:
                tree_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
            else:
                tree_item.setIcon(0, self.style().standardIcon(QStyle.SP_FileIcon))
            
            tree_item.setText(1, full_path)

    def navigate_to(self, path):
        if os.path.isdir(path):
            self.current_path = path
            self.refresh_ui()

    def on_path_entry_return(self):
        path = self.path_entry_bottom.text()
        if os.path.isdir(path):
            self.navigate_to(path)

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory", self.current_path)
        if dir_path:
            self.navigate_to(dir_path)

    def on_item_double_clicked(self, item, column):
        path = item.text(1)
        if os.path.isdir(path):
            self.navigate_to(path)
        else:
            try:
                os.startfile(path)
            except Exception as e:
                print(f"Failed to open {path}: {e}")
            
    def copy_to_clipboard(self, mode):
        item = self.file_list.currentItem()
        if not item: return
        
        full_path = item.text(1)
        text_to_copy = ""
        
        if mode == "path":
            text_to_copy = full_path
        elif mode == "name":
            text_to_copy = os.path.basename(full_path)
        elif mode == "no_ext":
            base = os.path.basename(full_path)
            name, _ = os.path.splitext(base)
            text_to_copy = name
            
        QApplication.clipboard().setText(text_to_copy)

class FileLoaderThread(QThread):
    batch_ready = Signal(list) # List of (name, is_dir, full_path)
    
    def __init__(self, path, search_text, use_regex):
        super().__init__()
        self.path = path
        self.search_text = search_text
        self.use_regex = use_regex
        self._is_running = True
        
    def run(self):
        import re
        pattern = None
        if self.search_text:
            if self.use_regex:
                try:
                    pattern = re.compile(self.search_text)
                except re.error:
                    pass 
            else:
                pattern = self.search_text.lower()

        def match(name):
            if not self.search_text: return True
            if self.use_regex:
                return pattern.search(name) is not None if pattern else False
            else:
                return pattern in name.lower()

        try:
            batch = []
            with os.scandir(self.path) as it:
                for entry in it:
                    if not self._is_running: break
                    if match(entry.name):
                        batch.append((entry.name, entry.is_dir(), entry.path))
                        
                        if len(batch) >= 100:
                            self.batch_ready.emit(batch)
                            batch = []
                            self.msleep(10)
            
            if batch:
                self.batch_ready.emit(batch)
                
        except Exception as e:
            print(f"Error accessing {self.path}: {e}")

    def stop(self):
        self._is_running = False
