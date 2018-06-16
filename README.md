# regexbot
A simple Python-powered Slackbot-like bot for Slack with support for Regexes

Regexes are configured by a Google Sheet, 'A2:F'
Column G is a status column to let you know if a regex is accepted or not

Setup:
- Follow Steps 1 and 2 from https://developers.google.com/sheets/api/quickstart/python
- move client_secret.json to root directory
- run `export SLACK_BOT_TOKEN='<your slackbot token>`
- run `export SHEET_ID='<your google sheet id>`
- run `python3 ./regexbot.py`

Usage:
- Populate a google sheet with your source and destination regexes.
  - Sheet name is "Data"
  - Column A -> Source regex. Messages will be matched against this
  - Column B -> Source channel. Regexbot will only respond if the messaage it sees matches one of the channels listed here. Blank for any channel. Parameters should be the channels name without the #. It is comma seperated
  - Column C -> Source user. Regexbot will only respond if the message it sees matches one of the users listed here. Blank for any user. Parameters should be the person's username without the @. It is comma seperated
  - Column D -> Destination regex. Responses will be created with this.
    - Use \n for regex group n 
  - Column E -> Destination Icon. Optional. Can be emojis (e.g. `:+1:`, the two colons are required) or urls. This is to set the avatar icon for the sent message
  - Column F -> Destination Username. Optional. This is to set the avatar username for the sent image
  - Column G -> Status. Given by regexbot and will indicate to you if the regex was successfully compiled. 
    - You should not manually modify this column. Regexbot will overwrite all values upon reloading
- Start the script
- In Slack, call the command "@regexbot reload" to make regexbot reload the google sheet when desired. 

Notes
- A regex limit of 256 is in place to ensure that the messages generated aren't stupidly long
