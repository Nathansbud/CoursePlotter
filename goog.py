import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

def make_token(scope, cred_name):
    creds = None

    token_path = os.path.join(os.getcwd(), "credentials" + os.sep + cred_name + "_token.pickle")
    cred_path = os.path.join(os.getcwd(), "credentials" + os.sep + cred_name + ".json")

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, scope)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    return creds

# DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
# drive_token = make_token(DRIVE_SCOPES, "drive")
# drive = build('drive', 'v3', credentials=drive_token)

SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
sheets_token = make_token(SHEETS_SCOPES, "sheets")
sheets = build('sheets', 'v4', credentials=sheets_token)

def write_sheet(sheet, values, r='', mode="ROWS"):
    sheets.spreadsheets().values().update(spreadsheetId=sheet, range=r, valueInputOption="RAW", body={
        'values':values,
        'majorDimension':mode
    }).execute()

def get_sheet(sheet, r='', mode='ROWS'):
    if len(r) > 0:
        return sheets.spreadsheets().values().get(spreadsheetId=sheet, range=r, majorDimension=mode).execute()
    return sheets.spreadsheets().get(spreadsheetId=sheet).execute()

def index_to_column(idx):
    major = chr(65 + floor(idx / 26 - 1)) if idx > 25 else ""
    minor = chr(65 + idx % 26)
    return str(major + minor)