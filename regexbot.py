import os
import time
import re
from slackclient import SlackClient
from sheetclient import SheetClient

if "SHEET_ID" not in os.environ:
    print("Run \"export SHEET_ID = \'<your google sheet Id>\'\" first")

if "SLACK_BOT_TOKEN" not in os.environ:
    print("Run \"export SLACK_BOT_TOKEN = \'<your slackbot token>\'\" first")

sheet_id = os.environ.get("SHEET_ID")
slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")

sheet_client = SheetClient(sheet_id)
raw_regex_dict = sheet_client.get_regexes()

# instantiate Slack client
slack_client = SlackClient(slack_bot_token)
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

RTM_READ_DELAY = 0.1 # 0.1 second delay between reading from RTM

compiled_regex_dict = {}

def handle_message(slack_event):
    message_text = slack_event["text"]
    message_channel = slack_event["channel"]
    for source_regex, destination_regex in compiled_regex_dict.items():
        try:
            if source_regex.search(message_text):
                new_message = re.sub(source_regex, destination_regex, message_text)

                slack_client.api_call(
                    "chat.postMessage",
                    channel=message_channel,
                    text=new_message
                )
                return
        except re.error as e:
            print("Error!", e)
            continue

def handle_next_events(slack_events):
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event and "text" in event:
            handle_message(event)

if __name__ == "__main__":
    print("Initialising regexes")
    for regex, result in raw_regex_dict.items():
        try:
            compiled_regex_dict[re.compile(regex)] = result
        except re.error as e:
            print("Error with regex: ", regex, result, e)
            continue

    if slack_client.rtm_connect(with_team_state=False):
        print("Starter Bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            handle_next_events(slack_client.rtm_read())
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")
