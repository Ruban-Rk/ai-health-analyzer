from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pickle
import numpy as np

app = Flask(__name__)
CORS(app)

with open('model/model.pkl', 'rb') as f:
    model = pickle.load(f)
with open('model/label_encoder.pkl', 'rb') as f:
    le = pickle.load(f)

SYMPTOM_KEYS = ['fever','cough','headache','fatigue','sore_throat','body_ache','nausea','runny_nose']

DISEASE_INFO = {
    'Flu': {
        'description': 'Influenza is a viral infection that attacks your respiratory system.',
        'severity': 'Moderate',
        'advice': 'Rest, stay hydrated, take fever reducers. See a doctor if symptoms worsen.',
        'color': '#e74c3c'
    },
    'Cold': {
        'description': 'Common cold is a mild viral infection of the nose and throat.',
        'severity': 'Mild',
        'advice': 'Rest, drink fluids, use over-the-counter cold remedies.',
        'color': '#3498db'
    },
    'Migraine': {
        'description': 'A migraine is an intense recurring headache, often with nausea.',
        'severity': 'Moderate',
        'advice': 'Rest in a dark quiet room, stay hydrated, consider pain relief medication.',
        'color': '#9b59b6'
    }
}

CHATBOT_RESPONSES = {
    'hello': 'Hello! I am your AI Health Assistant. Please describe your symptoms and I will help analyze them.',
    'hi': 'Hi there! Tell me your symptoms and I will do a health analysis for you.',
    'fever': 'Fever is a common symptom of infections. How long have you had it? Also check the Symptom Checker tab.',
    'cough': 'A cough can indicate respiratory issues. Is it dry or with phlegm? Use the Symptom Checker for a full analysis.',
    'headache': 'Headaches have many causes. Is it throbbing or constant? Check the Symptom Checker tab for more insight.',
    'tired': 'Fatigue can signal many conditions. How long have you felt this way? Try the Symptom Checker.',
    'help': 'I can help analyze your symptoms! Use the Symptom Checker tab to select your symptoms, or just tell me how you feel.',
    'thanks': 'You are welcome! Remember I am an AI assistant — always consult a real doctor for medical advice.',
    'bye': 'Take care and stay healthy! Remember to consult a doctor for professional medical advice.',
}

def get_chatbot_response(message):
    message_lower = message.lower()
    for keyword, response in CHATBOT_RESPONSES.items():
        if keyword in message_lower:
            return response
    symptoms_mentioned = [s for s in SYMPTOM_KEYS if s.replace('_', ' ') in message_lower or s in message_lower]
    if symptoms_mentioned:
        return f"I noticed you mentioned: {', '.join(symptoms_mentioned)}. Go to the Symptom Checker tab and select these for a full AI analysis!"
    return "I understand you may not be feeling well. Could you describe your symptoms more? Or use the Symptom Checker tab for a detailed analysis."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')
    response = get_chatbot_response(message)
    return jsonify({'response': response, 'status': 'ok'})

@app.route('/api/predict', methods=['POST'])
def predict():
    data = request.get_json()
    symptoms = data.get('symptoms', {})
    features = np.array([[int(symptoms.get(s, 0)) for s in SYMPTOM_KEYS]])
    prediction_encoded = model.predict(features)[0]
    probabilities = model.predict_proba(features)[0]
    disease = le.inverse_transform([prediction_encoded])[0]
    confidence = round(float(max(probabilities)) * 100, 1)
    all_probs = {
        le.inverse_transform([i])[0]: round(float(p) * 100, 1)
        for i, p in enumerate(probabilities)
    }
    info = DISEASE_INFO.get(disease, {})
    return jsonify({
        'disease': disease,
        'confidence': confidence,
        'probabilities': all_probs,
        'description': info.get('description', ''),
        'severity': info.get('severity', ''),
        'advice': info.get('advice', ''),
        'color': info.get('color', '#333'),
        'status': 'ok'
    })

@app.route('/api/stats', methods=['GET'])
def stats():
    return jsonify({
        'symptom_frequency': {
            'Fever': 65, 'Cough': 58, 'Headache': 45,
            'Fatigue': 72, 'Sore Throat': 38, 'Body Ache': 41,
            'Nausea': 33, 'Runny Nose': 29
        },
        'disease_distribution': {'Flu': 40, 'Cold': 35, 'Migraine': 25},
        'monthly_cases': {
            'Jan': 120, 'Feb': 98, 'Mar': 145, 'Apr': 87,
            'May': 63, 'Jun': 55, 'Jul': 48, 'Aug': 52,
            'Sep': 78, 'Oct': 110, 'Nov': 134, 'Dec': 160
        },
        'status': 'ok'
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
