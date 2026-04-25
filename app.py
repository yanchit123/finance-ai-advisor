from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os, uuid
from datetime import datetime

load_dotenv()
app = Flask(__name__)
CORS(app)

transactions = []

def get_assistant():
    from ibm_watson import AssistantV2
    from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
    auth = IAMAuthenticator(os.getenv('WATSON_API_KEY'))
    a = AssistantV2(version='2023-06-15', authenticator=auth)
    a.set_service_url(os.getenv('WATSON_URL'))
    return a

def get_nlu():
    from ibm_watson import NaturalLanguageUnderstandingV1
    from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
    auth = IAMAuthenticator(os.getenv('NLU_API_KEY'))
    n = NaturalLanguageUnderstandingV1(version='2022-04-07', authenticator=auth)
    n.set_service_url(os.getenv('NLU_URL'))
    return n

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    try:
        assistant = get_assistant()
        sess = assistant.create_session(
            assistant_id=os.getenv('WATSON_ASSISTANT_ID')
        ).get_result()
        sid = sess['session_id']

        resp = assistant.message(
            assistant_id=os.getenv('WATSON_ASSISTANT_ID'),
            session_id=sid,
            input={'message_type': 'text', 'text': user_message}
        ).get_result()

        assistant.delete_session(
            assistant_id=os.getenv('WATSON_ASSISTANT_ID'),
            session_id=sid
        )

        reply = "I'm here to help!"
        for item in resp.get('output', {}).get('generic', []):
            if item.get('response_type') == 'text':
                reply = item['text']
                break
        return jsonify({'reply': reply})

    except Exception as e:
        print("Watson error:", e)
        return jsonify({'reply': smart_reply(user_message)})

def smart_reply(msg):
    msg = msg.lower()
    if any(w in msg for w in ['hi','hello','hey']):
        return "Hello! 👋 I'm your Finance Advisor. Ask me about budgeting, saving, or investing!"
    if any(w in msg for w in ['budget','spend']):
        return "💰 Use the 50/30/20 rule: 50% needs, 30% wants, 20% savings. Want details?"
    if any(w in msg for w in ['invest','sip','stock','mutual']):
        return "📈 Start with SIP in mutual funds — low risk, 8-12% annual returns. Want to know more?"
    if any(w in msg for w in ['save','saving','goal']):
        return "🎯 Automate savings on salary day! Save first, spend the rest."
    if any(w in msg for w in ['debt','loan','emi','credit']):
        return "💳 Pay high-interest debt first (credit cards). Always pay more than minimum!"
    if any(w in msg for w in ['expense','track']):
        return "📊 Use the Add Expense form on the left to log your spending!"
    return "I can help with 💰 budgeting, 🎯 saving, 📈 investing, 💳 debt. What do you need?"

@app.route('/analyze', methods=['POST'])
def analyze():
    text = request.json.get('text', '')
    if len(text.strip()) < 5:
        return jsonify({'error': 'Enter more text'}), 400
    try:
        from ibm_watson.natural_language_understanding_v1 import Features, KeywordsOptions, SentimentOptions, EntitiesOptions
        nlu = get_nlu()
        result = nlu.analyze(
            text=text,
            features=Features(
                keywords=KeywordsOptions(limit=5),
                sentiment=SentimentOptions(),
                entities=EntitiesOptions(limit=5)
            )
        ).get_result()
        return jsonify(result)
    except Exception as e:
        print("NLU error:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/transactions', methods=['GET'])
def get_txns():
    return jsonify(transactions)

@app.route('/transactions', methods=['POST'])
def add_txn():
    data = request.json
    txn = {
        'id': str(uuid.uuid4()),
        'amount': float(data.get('amount', 0)),
        'category': data.get('category', 'Other'),
        'description': data.get('description', ''),
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    transactions.append(txn)
    return jsonify({'success': True})

@app.route('/summary', methods=['GET'])
def summary():
    cats = {}
    total = 0
    for t in transactions:
        cats[t['category']] = cats.get(t['category'], 0) + t['amount']
        total += t['amount']
    return jsonify({'categories': cats, 'total': round(total, 2)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)