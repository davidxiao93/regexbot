
import time
import re
from slackclient import SlackClient
from sheetclient import SheetClient

import pprint
pp = pprint.PrettyPrinter(indent=4)
import random

RTM_READ_DELAY = 0.1 # 0.1 second delay between reading from RTM
MAX_LENGTH = 2048
SNIPPET_CHAR_THRESHOLD = 512
SNIPPET_LINE_THRESHOLD = 8
RETRY_SENDS = 10

class RegexBot:

    def __init__(self, sheet_id, slack_bot_token):
        self.sheet_client = SheetClient(sheet_id)
        self.slack_client = SlackClient(slack_bot_token)
        self.slack_bot_id = None
        self.compiled_regex_list = []

    def start(self):
        print("Initialising regexes")
        self.load_regexes()

        if self.slack_client.rtm_connect(with_team_state=False):
            print("Starter Bot connected and running!")
            # Read bot's user ID by calling Web API method `auth.test`
            self.starterbot_id = self.slack_client.api_call("auth.test")["user_id"]
            while True:
                self.handle_next_events(self.slack_client.rtm_read())
                time.sleep(RTM_READ_DELAY)
        else:
            print("Connection failed. Exception traceback printed above.")

    def load_regexes(self):
        self.compiled_regex_list = []
        self.sheet_client.clear_status()
        raw_regex_list = self.sheet_client.get_regexes()
        regex_dict = {}
        compiled_regex_count = 0
        self.sheet_client.update_status(["Checking"] * len(raw_regex_list))
        message_list = []
        for i, row in enumerate(raw_regex_list):
            message = "Accepted"
            if len(row) >= 2 and len(row[0].strip()) == 0 and len(row[1].strip()) == 0:
                message = ""
            elif len(row) < 2 or len(row[0].strip()) == 0 or len(row[1].strip()) == 0:
                message = "Empty Cell"
            elif len(row[0].strip()) > MAX_LENGTH or len(row[1].strip()) > MAX_LENGTH:
                message = "Regex too long: " + str(len(row[0].strip())) + ", " + str(len(row[1].strip())) + ", maximum is " + str(MAX_LENGTH)
            else:
                source_regex = row[0].strip()
                destination_regex = row[1].strip()
                try:
                    compiled_regex = re.compile(source_regex)
                    if compiled_regex not in regex_dict:
                        regex_dict[compiled_regex] = []
                        compiled_regex_count += 1
                    regex_dict[compiled_regex].append(destination_regex)
                except re.error as e:
                    message = "Error compiling regex"
            message_list.append(message)
        self.sheet_client.update_status(message_list)
        for compiled_regex, destination_regexes in regex_dict.items():
            self.compiled_regex_list.append((compiled_regex, destination_regexes))

    def handle_response(self, response):
        if response["ok"] is False and response["headers"]["Retry-After"]:
            # The `Retry-After` header will tell you how long to wait before retrying
            delay = int(response["headers"]["Retry-After"])
            print("Rate limited. Retrying in " + str(delay) + " seconds")
            time.sleep(delay)
            return False
        return True

    def send_message(self, channel, message, is_plain, original_event):
        thread_ts = None
        if "thread_ts" in original_event:
            thread_ts = original_event["thread_ts"]
        if thread_ts is None:
            if is_plain:
                return self.slack_client.api_call(
                    "chat.postMessage",
                    channel=channel,
                    text=message
                )

            else:
                return self.slack_client.api_call(
                    "files.upload",
                    channels=channel,
                    content=message
                )
        else:

            if not is_plain:
                message = "Cannot send Snippets in a Thread. This is a Slack limitation"
                return self.slack_client.api_call(
                    "chat.postEphemeral",
                    channel=channel,
                    text=message,
                    user=original_event["user"]
                )

            else:
                reply_broadcast = None
                if "reply_broadcast" in original_event:
                    reply_broadcast = original_event["reply_broadcast"]
                if reply_broadcast is None:
                    return self.slack_client.api_call(
                        "chat.postMessage",
                        channel=channel,
                        text=message,
                        thread_ts=thread_ts
                    )
                else:
                    return self.slack_client.api_call(
                        "chat.postMessage",
                        channel=channel,
                        text=message,
                        thread_ts=thread_ts,
                        reply_broadcast=reply_broadcast
                    )

    def retryable_send_message(self, channel, message, is_plain, original_event):
        got_successful_response = False
        attempts = 0
        while not got_successful_response:
            got_successful_response = self.handle_response(self.send_message(channel, message, is_plain, original_event))
            if attempts > RETRY_SENDS:
                print("Failed to send message after", RETRY_SENDS, "attempts!")
                break

    def handle_message(self, slack_event):
        message_text = slack_event["text"]
        message_channel = slack_event["channel"]
        if message_text == "<@" + str(self.starterbot_id) + "> reload":
            # If the exact message "@regexbot reload" is seen, then reload the regexes
            self.load_regexes()
            return

        for source_regex, destination_regexes in self.compiled_regex_list:
            try:
                maybe_match = source_regex.search(message_text)
                if maybe_match:
                    new_message = re.sub(source_regex, random.choice(destination_regexes), maybe_match.group(0))
                    is_plain_message = len(new_message) < SNIPPET_CHAR_THRESHOLD and len(new_message.split('\n')) < SNIPPET_LINE_THRESHOLD
                    self.retryable_send_message(message_channel, new_message, is_plain_message, slack_event)
                    return
            except re.error as e:
                print("Regex Error!", e)
                continue

    def handle_next_events(self, slack_events):
        for event in slack_events:
            if event["type"] == "message" and not "subtype" in event and "text" in event:
                self.handle_message(event)
