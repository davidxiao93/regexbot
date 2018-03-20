# Based off https://developers.google.com/sheets/api/quickstart/python

import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import pprint
pp = pprint.PrettyPrinter(indent=4)
import time

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Regexbot'

class SheetClient:
    def __init__(self, sheet_id):
        self.credentials = self.__get_credentials()
        self.sheet_id = sheet_id
        http = self.credentials.authorize(httplib2.Http())
        discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
        self.service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)

        # To prevent us exceeding the api quota, use a cache if the request to reload happened too soon since the last update
        self.cached_regexes = None
        self.cache_expires = 0

    def get_regexes(self):
        now = int(round(time.time() * 1000))
        if self.cached_regexes is not None and now < self.cache_expires:
            return self.cached_regexes

        # Need to refresh
        range_name = 'Data!A2:B'
        result = self.service.spreadsheets().values().get(
            spreadsheetId = self.sheet_id,
            range = range_name,
            valueRenderOption = "FORMULA"
        ).execute()
        values = result.get('values', [])
        return_list = []
        if not values:
            print("WARNING: No regexes")
        else:
            for row in values:
                return_list.append(row)
        self.cached_regexes = return_list
        self.cache_expires = now+1000 # cache expires in one second
        return return_list

    def update_status(self, row, message):
        range_name = 'Data!C' + str(row)
        self.service.spreadsheets().values().update(
            spreadsheetId = self.sheet_id,
            range = range_name,
            body = {"range": range_name,"values": [ [ message ] ]},
            valueInputOption = "USER_ENTERED"
        ).execute()

    def clear_status(self):
        range_name = 'Data!C1:C'
        self.service.spreadsheets().values().clear(
            spreadsheetId=self.sheet_id,
            range=range_name,
            body={}
        ).execute()

    def __get_credentials(self):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'sheets.googleapis.com-python-quickstart.json')

        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            credentials = tools.run_flow(flow, store, None)
            print('Storing credentials to ' + credential_path)
        return credentials