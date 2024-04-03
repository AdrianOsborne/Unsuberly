# Unsuberly: Gmail Marketing Email Unsubscriber

## Project Description
Unsuberly is a tool specifically designed for Gmail users to manage their inbox by providing features to opt out of marketing emails and mass delete emails from specific senders. It scans Gmail emails for unsubscribe links and offers users the option to unsubscribe automatically. Additionally, users can mass delete emails from specific senders to declutter their inbox.

## Why is Unsuberly Useful?
In today's digital age, email inboxes are flooded with marketing emails, often causing clutter and distraction. Unsuberly provides a solution to this problem specifically for Gmail users. By automating the process of unsubscribing from marketing emails and mass deleting emails from specific senders, Unsuberly saves users valuable time and helps them maintain a clean and organized Gmail inbox. This program is particularly beneficial for individuals and businesses looking to streamline their email management process and improve productivity within the Gmail ecosystem.

## Table of Contents
1. [Project Description](#project-description)
2. [Why is Unsuberly Useful?](#why-is-unsuberly-useful)
3. [How to Install and Run the Project](#how-to-install-and-run-the-project)
4. [How to Use the Project](#how-to-use-the-project)
5. [Credits](#credits)
6. [License](#license)

## How to Install and Run the Project
1. **Get Google Credentials**:
   - Go to the [Google API Console](https://console.developers.google.com/) and create a new project.
   - Enable the Gmail API for your project.
   - Go to the "Credentials" tab and create credentials (OAuth 2.0 client ID) for a desktop application.
   - Download the credentials file (`credentials.json`) and place it in the project directory.

2. **Install Dependencies**:
   - Install the required Python dependencies by running:
     ```
     pip install google-auth google-auth-oauthlib google-api-python-client tqdm
     ```

3. **Run the Program**:
   - Execute the script using Python:
     ```
     python unsuberly.py
     ```

## How to Use the Project
- Upon running the program, you will be prompted to confirm the number of messages you want to process.
- Follow the on-screen instructions to proceed with the unsubscribe and mass delete operations.

## Additional Features
- **PyQt5 UI**: Unsuberly includes a PyQt5 user interface for a more user-friendly experience.
- **Chrome Extension (Coming Soon)**: A Chrome extension version of Unsuberly will be available soon for even easier access and integration with Gmail.

## Credits
- This project is developed by Adrian Osborne.

## License
This project is licensed under the [Open Source License](LICENSE).
