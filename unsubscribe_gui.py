# unsubscribe_gui.py

import sys
import threading
import webbrowser
from PyQt5.QtWidgets import (
    QApplication, QTableWidget, QTableWidgetItem, QPushButton, QVBoxLayout, QWidget, QMainWindow,
    QHeaderView, QProgressBar, QLineEdit, QLabel, QHBoxLayout, QCheckBox, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, QObject
from email_scraper import get_gmail_service, extract_senders_and_unsubscribe, get_unsubscribe_link

class ProgressEmitter(QObject):
    progress_updated = pyqtSignal(int, int)
    scraping_completed = pyqtSignal(dict, dict)

class UnsubscribeList(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.progress_emitter = ProgressEmitter()
        self.progress_emitter.progress_updated.connect(self.update_progress_bar)
        self.progress_emitter.scraping_completed.connect(self.scraping_done)

        self.scraping_thread = None
        self.unsubscribe_data = {}
        self.should_cancel_scraping = False  # Flag to indicate if scraping should be cancelled

    def initUI(self):
        self.setWindowTitle('Unsubly')
        self.setGeometry(100, 100, 800, 600)
        
        self.tableWidget = QTableWidget()
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(['Sender', 'Unsubscribe', 'Use Gmail unsubscribe'])
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.progress_bar = QProgressBar(self)

        self.number_input = QLineEdit(self)
        self.number_input.setPlaceholderText("Enter number of messages to process")

        self.inbox_checkbox = QCheckBox("Include emails from Inbox")
        self.inbox_checkbox.setChecked(True)
        self.spam_checkbox = QCheckBox("Include emails from Spam")
        self.trash_checkbox = QCheckBox("Include emails from Trash")
        
        scrape_button = QPushButton('Scrape Emails')
        scrape_button.clicked.connect(self.scrape_emails)

        self.estimated_time_label = QLabel("Estimated processing time will be shown here.")
        self.number_input.textChanged.connect(self.update_estimated_time)

        layout = QVBoxLayout()
        layout.addWidget(self.number_input)
        layout.addWidget(self.estimated_time_label)
        layout.addWidget(self.inbox_checkbox)
        layout.addWidget(self.spam_checkbox)
        layout.addWidget(self.trash_checkbox)
        layout.addWidget(scrape_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.tableWidget)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def scrape_emails(self):
        print("Scraping emails")
        if self.scraping_thread and self.scraping_thread.is_alive():
            # Set a flag to indicate that scraping should be cancelled
            self.should_cancel_scraping = True
            return
        
        # Reset the flag indicating cancellation
        self.should_cancel_scraping = False

        number_of_messages = int(self.number_input.text()) if self.number_input.text().isdigit() else 0
        include_labels = []
        if self.inbox_checkbox.isChecked():
            include_labels.append('INBOX')
        if self.spam_checkbox.isChecked():
            include_labels.append('SPAM')
        if self.trash_checkbox.isChecked():
            include_labels.append('TRASH')
        
        self.scraping_thread = threading.Thread(target=self.start_scraping, args=(number_of_messages, include_labels), daemon=True)
        self.scraping_thread.start()

    def start_scraping(self, number_of_messages, include_labels):
        total = self.update_total_emails()
        if int(self.number_input.text()) > total:
            self.number_input.setText(str(total))
            number_of_messages = total

        def progress_callback(current, total):
            self.progress_emitter.progress_updated.emit(current, total)
            print(f"{current} / {total}")

        def scraping_done(domain_unsubscribe_links, domain_header_unsubscribe_links):
            self.progress_emitter.scraping_completed.emit(domain_unsubscribe_links, domain_header_unsubscribe_links)

        service = get_gmail_service()
        extract_senders_and_unsubscribe(service, number_of_messages, user_id='me',
                                        progress_callback=progress_callback,
                                        include_labels=include_labels,
                                        done_callback=scraping_done,
                                        cancel_flag=self.should_cancel_scraping)  # Pass the cancel flag

    def update_progress_bar(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def scraping_done(self, domain_unsubscribe_links, domain_header_unsubscribe_links):
        self.unsubscribe_data = {
            **domain_unsubscribe_links,
            **domain_header_unsubscribe_links
        }
        self.update_table(domain_unsubscribe_links, domain_header_unsubscribe_links)


    def update_total_emails(self):
        service = get_gmail_service()
        try:
            profile = service.users().getProfile(userId='me').execute()
            total_emails = profile['messagesTotal']
            return total_emails
        except Exception as e:
            print(f"An error occurred while fetching total number of emails: {e}")
            return 0

    
    def get_total_emails_in_label(self, label_id):
        service = get_gmail_service()
        total_results = 0
        page_token = None
        try:
            while True:
                response = service.users().messages().list(userId='me', labelIds=[label_id], maxResults=100, pageToken=page_token).execute()
                messages = response.get('messages', [])
                total_results += len(messages)
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
        except Exception as e:
            print(f"An error occurred while fetching messages from label {label_id}: {e}")
        return total_results


    def update_table(self, unsubscribe_links, header_unsubscribe_links):
        self.tableWidget.setRowCount(0)

        for domain, link in unsubscribe_links.items():
            row_position = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row_position)
            self.tableWidget.setItem(row_position, 0, QTableWidgetItem(domain))

            link_btn = QPushButton('Opt-Out via link' if link else 'No Link')
            link_btn.clicked.connect(lambda _, link=link: webbrowser.open(link) if link else None)
            link_btn.setEnabled(bool(link))
            self.tableWidget.setCellWidget(row_position, 1, link_btn)

            header_link = header_unsubscribe_links.get(domain, "")
            header_link_btn = QPushButton('Opt-out through Gmail' if header_link else 'No Link')
            header_link_btn.clicked.connect(lambda _, link=header_link: webbrowser.open(link) if link else None)
            header_link_btn.setEnabled(bool(header_link))
            self.tableWidget.setCellWidget(row_position, 2, header_link_btn)

        header = self.tableWidget.horizontalHeader()
        for column in range(self.tableWidget.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.Stretch)

    def update_estimated_time(self):
        try:
            with open('cumulative_average_time.txt', 'r') as f:
                avg_time = float(f.read().strip())
            num_messages = int(self.number_input.text()) if self.number_input.text().isdigit() else 0
            estimated_time = avg_time * num_messages
            self.estimated_time_label.setText(f"Estimated processing time: {estimated_time:.2f} seconds.")
        except Exception as e:
            self.estimated_time_label.setText("Estimated processing time: N/A")

def main():
    app = QApplication(sys.argv)
    window = UnsubscribeList()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
