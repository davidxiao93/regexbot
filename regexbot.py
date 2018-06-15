
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

SOURCE_REGEX = 0
SOURCE_CHANNEL = 1
SOURCE_USER = 2
DESTINATION_REGEX = 3

VERBOSE_LOGGING = False

class RegexBot:

    def __init__(self, sheet_id, slack_bot_token):
        self.sheet_client = SheetClient(sheet_id)
        self.slack_client = SlackClient(slack_bot_token)
        self.slack_bot_id = None
        self.compiled_regex_list = []

        self.user_dict = {}         # Goes from slack user id to slack user name
        self.conversation_dict = {} # Goes from slack conversation id to slack conversation name

    def start(self):
        print("Initialising")
        self.initialise()

        if self.slack_client.rtm_connect(with_team_state=False):
            print("Starter Bot connected and running!")
            # Read bot's user ID by calling Web API method `auth.test`
            self.starterbot_id = self.slack_client.api_call("auth.test")["user_id"]
            while True:
                self.handle_next_events(self.slack_client.rtm_read())
                time.sleep(RTM_READ_DELAY)
        else:
            print("Connection failed. Exception traceback printed above.")

    def initialise(self):
        self.load_conversations()
        self.load_users()
        self.load_regexes()

    # Yes I know this is bad, but it's only called on reload and not during normal runtime
    def nasty_inverse_lookup(self, dict, lookup):
        for key, value in dict.items():
            if value == lookup:
                return key
        return None

    def check_input(self, lookup_dict, message, input):
        source_inputs = []
        unrecognised_inputs = []
        for split_input in input:
            split_input = split_input.strip()
            if len(split_input) == 0:
                continue
            key = self.nasty_inverse_lookup(lookup_dict, split_input)
            if key == None:
                unrecognised_inputs.append(split_input)
            else:
                source_inputs.append(key)
        if len(unrecognised_inputs) != 0:
            message = "Warning: Unrecognised values: " + str(unrecognised_inputs)
        return message, source_inputs

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
            if len(row) <= DESTINATION_REGEX or len(row[DESTINATION_REGEX].strip()) == 0:
                message = "Destination regex must be provided"
            elif len(row[SOURCE_REGEX].strip()) == 0:
                message = "Source regex must be provided"
            elif len(row[SOURCE_REGEX].strip()) > MAX_LENGTH or len(row[DESTINATION_REGEX].strip()) > MAX_LENGTH:
                message = "Regex too long: " + str(len(row[SOURCE_REGEX].strip())) + ", " + str(len(row[DESTINATION_REGEX].strip())) + ", maximum is " + str(MAX_LENGTH)
            else:
                source_regex = row[SOURCE_REGEX].strip()
                message, source_conversations = self.check_input(self.conversation_dict, message, row[SOURCE_CHANNEL].split(','))
                message, source_users = self.check_input(self.user_dict, message, row[SOURCE_USER].split(','))
                destination_regex = row[DESTINATION_REGEX].strip()
                try:
                    compiled_regex = re.compile(source_regex)
                    if compiled_regex not in regex_dict:
                        regex_dict[compiled_regex] = []
                        compiled_regex_count += 1
                    regex_dict[compiled_regex].append((source_conversations, source_users, destination_regex))
                except re.error as e:
                    message = "Error compiling regex"
            message_list.append(message)
        self.sheet_client.update_status(message_list)
        for compiled_regex, potential_destinations in regex_dict.items():
            self.compiled_regex_list.append((compiled_regex, potential_destinations))

    def load_conversations(self):
        conversations_list = self.slack_client.api_call(
            "conversations.list",
            exclude_archived=True,
            types='public_channel,private_channel'
        )['channels']
        for conversation in conversations_list:
            if conversation['is_member']:
                self.conversation_dict[conversation['id']] = conversation['name']
        if VERBOSE_LOGGING:
            pp.pprint(self.conversation_dict)

    def load_users(self):
        members_list = self.slack_client.api_call(
            "users.list"
        )['members']
        for member in members_list:
            if not member['is_bot'] and member['id'] != 'USLACKBOT':
                self.user_dict[member['id']] = member['name']
        if VERBOSE_LOGGING:
            pp.pprint(self.user_dict)

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

    def makeFilter(self, message_channel, message_user):
        def destinationFilter(possible_destination):
            source_channel_list = possible_destination[0]
            source_user_list = possible_destination[1]

            if len(source_channel_list) != 0:
                if message_channel not in source_channel_list:
                    return False
            if len(source_user_list) != 0:
                if message_user not in source_user_list:
                    return False

            return True
        return destinationFilter


    def handle_message(self, slack_event):
        message_text = slack_event["text"]
        message_channel = slack_event["channel"]
        message_user = slack_event["user"]
        destinationFilter = self.makeFilter(message_channel, message_user)
        if message_text == "<@" + str(self.starterbot_id) + "> reload":
            # If the exact message "@regexbot reload" is seen, then reinitialise
            self.initialise()
            return

        for source_regex, possible_destinations in self.compiled_regex_list:
            try:
                maybe_match = source_regex.search(message_text)
                if maybe_match:
                    # TODO: consider if filtering first then going through regexes would be faster
                    filtered_destinations = list(filter(destinationFilter, possible_destinations))
                    if len(filtered_destinations) == 0:
                        continue
                    selected_destination = random.choice(filtered_destinations)
                    source_conversations, source_users, destination_regex = selected_destination

                    new_message = re.sub(source_regex, destination_regex, maybe_match.group(0))
                    is_plain_message = len(new_message) < SNIPPET_CHAR_THRESHOLD and len(new_message.split('\n')) < SNIPPET_LINE_THRESHOLD
                    self.retryable_send_message(message_channel, new_message, is_plain_message, slack_event)
                    return
            except re.error as e:
                print("Regex Error!", e)
                continue

    def handle_next_events(self, slack_events):
        for event in slack_events:
            if VERBOSE_LOGGING:
                pp.pprint(event)
            if event["type"] == "message" and not "subtype" in event and "text" in event:
                self.handle_message(event)
