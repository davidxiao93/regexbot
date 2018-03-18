import os
import time
import re
from slackclient import SlackClient

# instantiate Slack client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# constants
RTM_READ_DELAY = 0.1 # 1 second delay between reading from RTM



def handle_message(slack_event):
    message_text = slack_event["text"]
    message_channel = slack_event["channel"]

    # TODO: regex processing here

    slack_client.api_call(
        "chat.postMessage",
        channel=message_channel,
        text=message_text
    )

def handle_next_events(slack_events):
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event and "text" in event:
            handle_message(event)


if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("Starter Bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            handle_next_events(slack_client.rtm_read())
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")
