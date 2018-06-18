import os
import time
from regexbot import RegexBot

if "SHEET_ID" not in os.environ:
    print("Run \"export SHEET_ID = \'<your google sheet Id>\'\" first")
    exit()

if "SLACK_BOT_TOKEN" not in os.environ:
    print("Run \"export SLACK_BOT_TOKEN = \'<your slackbot token>\'\" first")
    exit()

sheet_id = os.environ.get("SHEET_ID")
slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")

regexbot = RegexBot(sheet_id, slack_bot_token)
while True:
    try:
        regexbot.start()
    except Exception as e:
        print("Exception caught: ")
        print(e)
    finally:
        time.sleep(1)
