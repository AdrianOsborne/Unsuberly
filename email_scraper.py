# email_scraper.py

import re
import os
import base64
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urllib.parse import unquote

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def find_message_body(parts):
    for part in parts:
        if part['mimeType'] == 'text/plain' or part['mimeType'] == 'text/html':
            if 'data' in part['body']:
                return base64.urlsafe_b64decode(part['body']['data'].encode('ASCII')).decode('utf-8')
        if 'parts' in part:
            return find_message_body(part['parts'])
    return ""

def get_unsubscribe_link(msg_str):
    unsubscribe_phrases = ['unsubscribe', 'preferences', 'opt-out']
    links = re.findall(r'(https?://[^\s]+)', msg_str)
    unsubscribe_links = {link.split('//')[1].split('/')[0]: link for link in links if any(phrase in unquote(link).lower() for phrase in unsubscribe_phrases)}
    return unsubscribe_links

def find_unsubscribe_link_in_headers(headers):
    for header in headers:
        if header['name'].lower() == 'list-unsubscribe':
            unsubscribe_links = re.findall(r'<(http[s]?://[^\s]+)>', header['value'])
            if unsubscribe_links:
                return unsubscribe_links[0]
    return None

def extract_senders_and_unsubscribe(service, process_count, user_id='me', progress_callback=None, include_labels=None, done_callback=None, cancel_flag=False):  # Added cancel_flag parameter
    start_time = time.time()

    if include_labels is None:
        include_labels = ['INBOX', 'SPAM', 'TRASH']
    
    domain_unsubscribe_links = {}
    domain_header_unsubscribe_links = {}
    processed_messages = 0
    
    for label_id in include_labels:
        next_page_token = None
        while processed_messages < process_count and not cancel_flag:  # Check cancel_flag
            try:
                response = service.users().messages().list(userId=user_id, labelIds=[label_id], maxResults=100, pageToken=next_page_token, includeSpamTrash=True).execute()
            except HttpError as error:
                print(f'An error occurred: {error}')
                break

            messages = response.get('messages', [])
            if not messages:
                print("No messages found.")
                break

            for message in messages:
                msg = service.users().messages().get(userId=user_id, id=message['id'], format='full').execute()
                headers = msg.get('payload', {}).get('headers', [])
                msg_str = find_message_body(msg['payload']['parts']) if 'parts' in msg['payload'] else ""
                
                body_unsubscribe_link = get_unsubscribe_link(msg_str)
                header_unsubscribe_link = find_unsubscribe_link_in_headers(headers)
                
                sender_email = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown Sender')
                domain = sender_email.split('@')[-1].lower()
                
                if isinstance(body_unsubscribe_link, list):
                    domain_unsubscribe_links[domain] = body_unsubscribe_link[0] if body_unsubscribe_link else None
                elif isinstance(body_unsubscribe_link, dict):
                    domain_unsubscribe_links[domain] = next(iter(body_unsubscribe_link.values())) if body_unsubscribe_link else None
                
                if header_unsubscribe_link:
                    domain_header_unsubscribe_links[domain] = header_unsubscribe_link

                processed_messages += 1
                if progress_callback:
                    progress_callback(processed_messages, process_count)
                if processed_messages >= process_count:
                    break

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
    
    end_time = time.time()
    
    if done_callback:
        done_callback(domain_unsubscribe_links, domain_header_unsubscribe_links)

    return domain_unsubscribe_links, domain_header_unsubscribe_links
