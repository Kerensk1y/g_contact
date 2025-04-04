import os
import csv
import json
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Устанавливаем путь к файлу с учетными данными OAuth 2.0
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
SCOPES = ['https://www.googleapis.com/auth/contacts.readonly']

# Функция для аутентификации и создания службы API
def authenticate_google_api():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as token:
            creds_info = json.load(token)
            try:
                creds = Credentials.from_authorized_user_info(creds_info, SCOPES)
            except ValueError as e:
                print(f"Error loading credentials: {e}")
                creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=52571)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('people', 'v1', credentials=creds)

# Функция для загрузки контактов и их группировки по ярлыкам
def download_contacts(service):
    results = service.people().connections().list(
        resourceName='people/me',
        pageSize=1000,
        personFields='names,emailAddresses,phoneNumbers,memberships,biographies'
    ).execute()
    
    connections = results.get('connections', [])
    label_groups = {}
    
    for person in connections:
        if 'memberships' in person:
            for membership in person['memberships']:
                label = membership['metadata'].get('source', {}).get('id', 'no_label')
                name = person.get('names', [{}])[0].get('displayName', 'No Name')
                emails = [email['value'] for email in person.get('emailAddresses', [])]
                phones = [phone['value'] for phone in person.get('phoneNumbers', [])]
                notes = person.get('biographies', [{}])[0].get('value', 'No Notes')
                
                if label not in label_groups:
                    label_groups[label] = []
                
                label_groups[label].append({
                    'Name': name, 
                    'Emails': ', '.join(emails),
                    'Phones': ', '.join(phones),
                    'Notes': notes
                })
    
    return label_groups

# Функция для сохранения контактов в файлы CSV
def save_contacts_to_csv(label_groups):
    if not os.path.exists('contacts'):
        os.makedirs('contacts')
    
    for label, contacts in label_groups.items():
        filename = os.path.join('contacts', f'{label}.csv')
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['Name', 'Emails', 'Phones', 'Notes'])
            writer.writeheader()
            writer.writerows(contacts)

# Основная функция для выполнения всей логики
def main():
    service = authenticate_google_api()
    label_groups = download_contacts(service)
    save_contacts_to_csv(label_groups)

if __name__ == '__main__':
    main()
