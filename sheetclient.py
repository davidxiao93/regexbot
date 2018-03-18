# Based off https://developers.google.com/sheets/api/quickstart/python

import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Regexbot'

class SheetClient:
    def __init__(self, sheet_id):
        self.credentials = self.__get_credentials()
        self.sheet_id = sheet_id
        http = self.credentials.authorize(httplib2.Http())
        discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
        self.service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)

    def get_regexes(self):
        range_name = 'A2:B'
        result = self.service.spreadsheets().values().get(spreadsheetId=self.sheet_id, range=range_name).execute()
        values = result.get('values', [])

        if not values:
            print("WARNING: No regexes")
            return {}
        else:
            return_dict = {}
            for row in values:
                return_dict[row[0]] = row[1]
            return return_dict

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