# regexbot
A simple Python-powered Slackbot-like bot for Slack with support for Regexes

Regexes are configured by a Google Sheet, 'A2:B'

Setup:
- Follow Steps 1 and 2 from https://developers.google.com/sheets/api/quickstart/python
- move client_secret.json to root directory
- run `export SLACK_BOT_TOKEN='<your slackbot token>`
- run `export SHEET_ID='<your google sheet id>`
- run `python3 ./regexbot.py`