# regexbot
A simple Python-powered Slackbot-like bot for Slack with support for Regexes

Regexes are configured by a Google Sheet, 'A2:B'
Column C is a status column to let you know if a regex is accepted or not

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
  - Column B -> Destination regex. Responses will be created with this. 
    - Use \n for regex group n
  - Column C -> Status. Given by regexbot and will indicate to you if the regex was successfully compiled. 
    - You should not manually modify this column. Regexbot will overwrite all values upon reloading
- Start the script
- In Slack, call the command "@regexbot reload" to make regexbot reload the google sheet when desired. 

Notes
- A regex limit of 256 is in place to ensure that the messages generated aren't stupidly long
