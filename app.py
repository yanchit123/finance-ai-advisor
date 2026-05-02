from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os, uuid, json
from pathlib import Path
from datetime import datetime

load_dotenv()
app = Flask(__name__)
CORS(app)

# ── Data Persistence ──────────────────────────────
DATA_FILE = 'transactions.json'

def load_transactions():
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_transactions(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

transactions = load_transactions()

# ── IBM Watson ────────────────────────────────────
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

# ── Routes ────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html')

# ── CHAT ─────────────────────────────────────────
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
    if any(w in msg for w in ['health','score']):
        return "💚 Your financial health score is based on your spending patterns. Add expenses to see your score!"
    if any(w in msg for w in ['tax','itr','return']):
        return "📑 Save tax using 80C (PPF, ELSS, LIC) up to ₹1.5 lakh. Want more tax saving tips?"
    if any(w in msg for w in ['emergency','fund']):
        return "🆘 Keep 6 months of expenses as emergency fund in a liquid account. This is your safety net!"
    return "I can help with 💰 budgeting, 🎯 saving, 📈 investing, 💳 debt, 📑 tax. What do you need?"

# ── NLU ANALYZE ──────────────────────────────────
@app.route('/analyze', methods=['POST'])
def analyze():
    text = request.json.get('text', '')
    if len(text.strip()) < 5:
        return jsonify({'error': 'Please enter more text'}), 400
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

# ── TRANSACTIONS ──────────────────────────────────
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
    save_transactions(transactions)
    return jsonify({'success': True})

@app.route('/transactions/delete', methods=['POST'])
def delete_txn():
    txn_id = request.json.get('id')
    global transactions
    transactions = [t for t in transactions if t['id'] != txn_id]
    save_transactions(transactions)
    return jsonify({'success': True})

# ── SUMMARY ───────────────────────────────────────
@app.route('/summary', methods=['GET'])
def summary():
    cats = {}
    total = 0
    for t in transactions:
        cats[t['category']] = cats.get(t['category'], 0) + t['amount']
        total += t['amount']
    return jsonify({'categories': cats, 'total': round(total, 2)})

# ── HEALTH SCORE ──────────────────────────────────
@app.route('/health-score', methods=['GET'])
def health_score():
    total = sum(t['amount'] for t in transactions)
    cats = {}
    for t in transactions:
        cats[t['category']] = cats.get(t['category'], 0) + t['amount']

    score = 100
    if total > 0:
        if (cats.get('Entertainment', 0) + cats.get('Shopping', 0)) / total > 0.3:
            score -= 20
        if cats.get('Food', 0) / total > 0.4:
            score -= 15
        if cats.get('Bills', 0) / total > 0.3:
            score -= 10

    if score >= 80:
        status = "Excellent 🟢"
        tip = "Great job! You are managing money well."
    elif score >= 60:
        status = "Good 🟡"
        tip = "Good progress! Try reducing non-essential spending."
    else:
        status = "Needs Work 🔴"
        tip = "Consider cutting down on Shopping and Entertainment."

    return jsonify({'score': max(score, 0), 'status': status, 'tip': tip})

# ── MONTHLY REPORT ────────────────────────────────
@app.route('/monthly-report', methods=['GET'])
def monthly_report():
    month = datetime.now().strftime('%Y-%m')
    monthly = [t for t in transactions if t['date'].startswith(month)]
    total = sum(t['amount'] for t in monthly)
    cats = {}
    for t in monthly:
        cats[t['category']] = cats.get(t['category'], 0) + t['amount']
    return jsonify({
        'month': datetime.now().strftime('%B %Y'),
        'total': round(total, 2),
        'count': len(monthly),
        'categories': cats
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)