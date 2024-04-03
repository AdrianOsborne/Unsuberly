import re
import os
import base64
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urllib.parse import unquote, quote_plus

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
    links = re.findall(r'(https?://[^\s]+)', msg_str)
    return [link for link in links if 'unsubscribe' in unquote(link).lower()]

def find_unsubscribe_link_in_headers(headers):
    unsubscribe_header = next((header for header in headers if header['name'].lower() == 'list-unsubscribe'), None)
    if unsubscribe_header:
        links = re.findall(r'<(http[s]?://[^\s]+)>', unsubscribe_header['value'])
        return links[0] if links else None
    return None

def extract_senders_and_unsubscribe(service, process_count, user_id='me', progress_callback=None, include_labels=None, done_callback=None):
    start_time = time.time()

    if include_labels is None:
        include_labels = ['INBOX', 'SPAM', 'TRASH']
    
    domain_unsubscribe_links = {}
    domain_header_unsubscribe_links = {}
    processed_messages = 0
    
    for label_id in include_labels:
        next_page_token = None
        while processed_messages < process_count:
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
                
                if body_unsubscribe_link:
                    domain_unsubscribe_links[domain] = body_unsubscribe_link[0]
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
        done_callback(processed_messages, end_time - start_time)

def main(process_count, progress_callback=None, done_callback=None):
    service = get_gmail_service()
    extract_senders_and_unsubscribe(service, process_count, progress_callback=progress_callback, done_callback=done_callback)

if __name__ == '__main__':
    process_count = 100  # Example process count
    main(process_count)