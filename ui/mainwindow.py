from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QAction, QCloseEvent
from utils.config import ConfigManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Parallel Filer")
        self.resize(1200, 800)

        # Central Widget & Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Splitter for Cards
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False) # Keep cards visible
        self.main_layout.addWidget(self.splitter)

        # Config
        self.config_manager = ConfigManager()

        # Menu Bar
        self.setup_menu()
        
        # Load Session
        self.load_session()

    def closeEvent(self, event: QCloseEvent):
        self.save_session()
        super().closeEvent(event)

    def save_session(self):
        cards_state = []
        for i in range(self.splitter.count()):
            widget = self.splitter.widget(i)
            # Check if it is a Card (it might be other widgets if we add them later, safe check)
            if hasattr(widget, 'get_state'):
                cards_state.append(widget.get_state())
        
        self.config_manager.save_session(cards_state)

    def load_session(self):
        session_data = self.config_manager.load_session()
        loaded = False
        
        if session_data and "cards" in session_data:
            cards = session_data["cards"]
            if cards:
                from ui.card import Card
                for card_state in cards:
                    card = Card(initial_state=card_state)
                    self.splitter.addWidget(card)
                loaded = True
        
        # If nothing loaded, add default card
        if not loaded:
            self.add_card()
        else:
             # Distribute width equally if loaded fresh
            count = self.splitter.count()
            if count > 0:
                width_per_card = self.width() // count # approximate
                self.splitter.setSizes([width_per_card] * count)

    def setup_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        add_card_action = QAction("Add Card", self)
        add_card_action.triggered.connect(self.add_card)
        file_menu.addAction(add_card_action)

    def add_card(self):
        from ui.card import Card
        import os
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop):
            desktop = os.path.expanduser("~")
            
        card = Card(start_path=desktop)
        self.splitter.addWidget(card)
        
        # Distribute width equally
        count = self.splitter.count()
        if count > 0:
            width_per_card = self.splitter.width() // count
            self.splitter.setSizes([width_per_card] * count)
