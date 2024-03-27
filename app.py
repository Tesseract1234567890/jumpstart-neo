from flask import Flask, render_template, request, jsonify
import slack, os
from pathlib import Path
from dotenv import load_dotenv
import re
import json
import requests
from googleapiclient.discovery import build
from datetime import datetime

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

client = slack.WebClient(token=os.environ["SLACK_TOKEN"])

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/alt')
def alt():
    return render_template('alt.html')

@app.route('/get_announcements', methods = ['GET'])

def ReturnMessagePlaintext():
    if(request.method == 'GET'):
        channel_name = "announcements"
        conversation_id = None
        try:
            for result in client.conversations_list():
                if conversation_id is not None:
                    break
                for channel in result["channels"]:
                    if channel["name"] == channel_name:
                        conversation_id = channel["id"]
                        break
            
            result = client.conversations_history(
                channel=conversation_id,
                inclusive=True,
                oldest="0",
                limit=1
            )

            message = result["messages"][0]

            # Extracting sender name
            sender_id = message["user"]
            sender_info = client.users_info(token=os.environ["SLACK_TOKEN"], user=sender_id)
            sender_name = sender_info['user']['real_name']

            # Extracting timestamp
            timestamp = message["ts"]
            formatted_timestamp = datetime.fromtimestamp(float(timestamp)).strftime('%m/%d/%Y %H:%M:%S')

            text = message["text"]
            name_pattern = r'<@(.*?)>'
            role_pattern = r'<!(.*?)>'

            def name_injector(matchobj):
                return "<span class='mention'>" + client.users_info(token=os.environ["SLACK_TOKEN"], user=matchobj.group(1))['user']['real_name'] + "</span>"
        
            def role_vaporizer(matchobj):
                return "<span class='role'><strong>@" + matchobj.group(1) + "</strong></span>"

            text = re.sub(r'\*(.*?)\*', r'<b>\1</b>', text)  # Bold
            text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)  # Italics
            text = re.sub(r'\n', r'<br><br>', text)  # Newlines
            text = re.sub(r'`(.*?)`', r'<code>\1</code>', text) # Code blocks
            text = re.sub(r'<(https?:\/\/(?:\w+\.)?\w+\.\w+(?:\/\S*?)?)>', r'<a href="\1">\1</a>', text) # Links

            message_data = {
                "sender_name": sender_name,
                "timestamp": formatted_timestamp,
                "message_text": re.sub(role_pattern, role_vaporizer, re.sub(name_pattern, name_injector, text))
            }

            message_data['message_text'] = re.sub(r'@subteam\^.{9}\|', "", message_data['message_text'])

            return jsonify(message_data)

        except Exception as e:
            print(f"Error: {e}")
    
@app.route('/get_events', methods = ['GET'])

def ReturnEvents():
    def get_events():
        api_key = os.environ["GAPI_KEY"]
        calendar_id = os.environ["CALENDAR_URL"]

        service = build('calendar', 'v3', developerKey=api_key)

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=(datetime.utcnow()).isoformat() + 'Z',
            showDeleted=False,
            singleEvents=True,
            maxResults=8,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
            events = "Epic Fail"

        return events
    return get_events()