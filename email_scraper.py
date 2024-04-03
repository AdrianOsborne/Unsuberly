import re
import os
import base64
import time
from collections import Counter
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urllib.parse import unquote
from tqdm import tqdm

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']

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

def backoff_handler(wait_time):
    print(f"Waiting for {wait_time} seconds due to rate limit.")
    time.sleep(wait_time)

def get_user_confirmation(avg_time_per_message):
    default_number_of_messages = 500
    
    while True:
        user_input = input(f"Enter the number of messages you want to process (default is {default_number_of_messages}): ")
        number_of_messages = default_number_of_messages if not user_input.strip() else user_input
        
        try:
            number_of_messages = int(number_of_messages)
            if number_of_messages <= 0:
                raise ValueError("Number of messages must be greater than 0.")
        except ValueError as e:
            print(f"Invalid input: {e}. Please enter a valid number.")
            continue
        
        estimated_time = number_of_messages * avg_time_per_message / 60
        
        confirm = input(f"The operation will process {number_of_messages} messages and is estimated to take approximately {estimated_time:.2f} minutes. Do you want to proceed? (yes/no): ")
        if confirm.lower() in ['yes', 'y']:
            return number_of_messages
        elif confirm.lower() in ['no', 'n']:
            print("Operation cancelled. Please enter a new number of messages to process.")
        else:
            print("Invalid input. Please respond with 'yes' or 'no'. Aborting operation.")

def calculate_and_update_averages(process_count, start_time):
    total_time = time.time() - start_time
    if process_count > 0:
        average_time_per_message = total_time / process_count
    else:
        print("No messages were processed, so average time cannot be calculated.")
        return
    
    with open('average_times.txt', 'a') as f:
        f.write(f"{average_time_per_message}\n")
    
    with open('average_times.txt', 'r') as f:
        times = [float(line.strip()) for line in f if line.strip()]
    
    if times:
        new_overall_average = sum(times) / len(times)
        with open('cumulative_average_time.txt', 'w') as f:
            f.write(f"{new_overall_average}")

def get_message_count(service, user_id, label_ids=[]):
    try:
        total_messages = 0
        next_page_token = None
        while True:
            response = service.users().messages().list(userId=user_id, labelIds=label_ids, maxResults=500, pageToken=next_page_token, fields="nextPageToken,messages(id)").execute()
            messages = response.get('messages', [])
            total_messages += len(messages)
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        return total_messages
    except Exception as e:
        print(f"Failed to get message count: {e}")
        return 0

def extract_senders_and_unsubscribe(service, process_count, user_id='me'):
    label_ids = ['INBOX', 'SPAM', 'TRASH']
    total_messages = sum(get_message_count(service, user_id, [label]) for label in label_ids)
    process_count = min(process_count, total_messages)
    print(f"Total messages to process: {process_count} out of {total_messages} total messages.")

    domain_unsubscribe_links = {}
    processed_messages = 0
    pbar = tqdm(total=process_count, desc="Processing messages")
    start_time = time.time()  # Start time measurement

    for label_id in label_ids:
        if processed_messages >= process_count:
            break
        next_page_token = None
        while processed_messages < process_count:
            batch_size = min(500, process_count - processed_messages)
            response = service.users().messages().list(userId=user_id, labelIds=[label_id], maxResults=batch_size, pageToken=next_page_token, includeSpamTrash=True).execute()
            messages = response.get('messages', [])
            if not messages:
                break

            for message in messages:
                if processed_messages >= process_count:
                    break
                try:
                    msg = service.users().messages().get(userId=user_id, id=message['id'], format='full').execute()
                    if 'parts' in msg['payload']:
                        msg_str = find_message_body(msg['payload']['parts'])
                    else:
                        msg_str = base64.urlsafe_b64decode(msg['payload']['body']['data'].encode('ASCII')).decode('utf-8')

                    unsubscribe_links = get_unsubscribe_link(msg_str)
                    headers = msg.get('payload', {}).get('headers', [])
                    sender_email = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown Sender')
                    domain = sender_email.split('@')[-1].lower()

                    if unsubscribe_links:
                        domain_unsubscribe_links.setdefault(domain, []).extend(unsubscribe_links)
                except HttpError as error:
                    if error.resp.status == 429:
                        backoff_handler(1)
                finally:
                    processed_messages += 1
                    pbar.update(1)

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

    pbar.close()
    calculate_and_update_averages(process_count, start_time)

    with open('unsubscribe_links.txt', 'w') as file:
        for domain, links in domain_unsubscribe_links.items():
            link_counts = Counter(links)
            most_common_link = link_counts.most_common(1)[0][0] if link_counts else None
            least_specific_link = min(links, key=len) if links else None
            chosen_link = most_common_link if most_common_link and link_counts[most_common_link] > 1 else least_specific_link
            file.write(f"{domain}: {chosen_link}\n")

    print("\nScrape Completed. All messages processed.")

if __name__ == '__main__':
    gmail_service = get_gmail_service()

    # Load the existing average processing time
    try:
        with open('cumulative_average_time.txt', 'r') as f:
            avg_time_per_message = float(f.read().strip())
    except (FileNotFoundError, ValueError):
        avg_time_per_message = 0.5  # Fallback to default if unable to load

    number_of_messages_to_process = get_user_confirmation(avg_time_per_message)
    print(f"Proceeding to process {number_of_messages_to_process} messages...")
    extract_senders_and_unsubscribe(gmail_service, number_of_messages_to_process)

    os.system('python unsubscribe_gui.py')