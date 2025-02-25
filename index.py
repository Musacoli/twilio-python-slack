import os
import slack
import re
from dotenv import load_dotenv
from flask import Flask, request, Response
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

load_dotenv()
app = Flask(__name__)

slack_token = os.getenv("SLACK_BOT_TOKEN")
slack_client = slack.WebClient(slack_token)
twilio_client = Client()


@app.route('/incoming/twilio', methods=['POST'])
def send_incoming_message():
    from_number = request.form['From']
    sms_message = request.form['Body']
    message = f"Text message from {from_number}: {sms_message}"
    slack_message = slack_client.chat_postMessage(
        channel='#-ops-2fa-notifications', text=message, icon_emoji=':robot_face:')
    response = MessagingResponse()
    return Response(response.to_xml(), mimetype="text/html"), 200


@app.route('/incoming/slack', methods=['POST'])
def send_incoming_slack():
    attributes = request.get_json()
    if 'challenge' in attributes:
        return Response(attributes['challenge'], mimetype="text/plain")
    incoming_slack_message_id, slack_message, channel = parse_message(attributes)
    if incoming_slack_message_id and slack_message:
        to_number = get_to_number(incoming_slack_message_id, channel)
        if to_number:
            messages = twilio_client.messages.create(
                to=to_number, from_=os.getenv("TWILIO_NUMBER"), body=slack_message)
        return Response(), 200
    return Response(), 200


def parse_message(attributes):
    if 'event' in attributes and 'thread_ts' in attributes['event']:
        return attributes['event']['thread_ts'], attributes['event']['text'], attributes['event']['channel']
    return None, None, None


def get_to_number(incoming_slack_message_id, channel):
    data = slack_client.conversations_history(channel=channel, latest=incoming_slack_message_id, limit=1, inclusive=1)
    if 'subtype' in data['messages'][0] and data['messages'][0]['subtype'] == 'bot_message':
        text = data['messages'][0]['text']
        phone_number = extract_phone_number(text)
        return phone_number
    return None


def extract_phone_number(text):
    data = re.findall(r'\w+', text)
    if len(data) >= 4:
        return data[3]
    return None


if __name__ == '__main__':
    app.run()
