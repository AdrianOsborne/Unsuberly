import sys
import webbrowser
from PyQt5.QtWidgets import (
    QApplication, QTableWidget, QTableWidgetItem, QPushButton, QVBoxLayout, QWidget, QMainWindow
)
from PyQt5.QtCore import Qt

def load_unsubscribe_links(filepath):
    sender_unsubscribe_links = {}
    with open(filepath, 'r') as file:
        for line in file:
            parts = line.strip().split(': ')
            if len(parts) == 2:
                domain, link = parts
                sender_unsubscribe_links[domain] = link
    return sender_unsubscribe_links

class UnsubscribeList(QMainWindow):
    def __init__(self, sender_unsubscribe_links):
        super().__init__()
        self.sender_unsubscribe_links = sender_unsubscribe_links
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Unsubscribe List')
        self.setGeometry(100, 100, 800, 600)

        self.tableWidget = QTableWidget()
        self.tableWidget.setRowCount(len(self.sender_unsubscribe_links))
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setHorizontalHeaderLabels(['Domain', 'Unsubscribe Link', 'Use Gmail Unsubscribe', 'Delete All Emails'])

        for i, (domain, link) in enumerate(self.sender_unsubscribe_links.items()):
            self.tableWidget.setItem(i, 0, QTableWidgetItem(domain))
            self.tableWidget.setItem(i, 1, QTableWidgetItem(link))
            
            gmail_unsubscribe_button = QPushButton('Unsubscribe')
            gmail_unsubscribe_button.clicked.connect(lambda _, d=domain: self.use_gmail_unsubscribe(d))
            self.tableWidget.setCellWidget(i, 2, gmail_unsubscribe_button)

            delete_button = QPushButton('Delete')
            delete_button.clicked.connect(lambda _, d=domain: self.delete_emails(d))
            self.tableWidget.setCellWidget(i, 3, delete_button)

        self.setCentralWidget(self.tableWidget)

    def use_gmail_unsubscribe(self, domain):
        # Implement the functionality to use Gmail's unsubscribe feature
        print(f"Unsubscribing from {domain} using Gmail's feature")

    def delete_emails(self, domain):
        # Implement the functionality to delete all emails from the domain
        print(f"Deleting all emails from {domain}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    unsubscribe_links = load_unsubscribe_links('unsubscribe_links.txt')
    ex = UnsubscribeList(unsubscribe_links)
    ex.show()
    sys.exit(app.exec_())
