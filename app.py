from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import datetime
import pickle, numpy as np, os, json

app = Flask(__name__)
app.secret_key = 'healthai_secret_2024_ruban_dev'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'healthai.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login_page'

with app.app_context():
    db.create_all()
    # If you have a function to seed the database (like seeding admin accounts), call it here too.

# ─── MODELS ───────────────────────────────────────────────
class User(UserMixin, db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=False)
    email        = db.Column(db.String(120), unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)
    role         = db.Column(db.String(20), default='user')
    avatar       = db.Column(db.String(10), default='U')
    phone        = db.Column(db.String(20), default='')
    blood_group  = db.Column(db.String(5), default='')
    age          = db.Column(db.Integer, default=0)
    address      = db.Column(db.String(200), default='')
    bio          = db.Column(db.String(300), default='')
    specialization = db.Column(db.String(100), default='')
    experience   = db.Column(db.String(50), default='')
    is_banned    = db.Column(db.Boolean, default=False)
    is_active_user = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    last_login   = db.Column(db.DateTime, default=datetime.utcnow)

class Appointment(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    patient_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    doctor_name  = db.Column(db.String(100))
    patient_name = db.Column(db.String(100))
    date         = db.Column(db.String(50))
    time         = db.Column(db.String(20))
    reason       = db.Column(db.String(200))
    status       = db.Column(db.String(20), default='pending')
    notes        = db.Column(db.Text, default='')
    fee          = db.Column(db.Float, default=500.0)
    paid         = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class Prescription(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    patient_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_name  = db.Column(db.String(100))
    patient_name = db.Column(db.String(100))
    medicines    = db.Column(db.Text)
    instructions = db.Column(db.Text)
    diagnosis    = db.Column(db.String(200))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    sender_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender_name  = db.Column(db.String(100))
    content      = db.Column(db.Text)
    read         = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_name = db.Column(db.String(100))
    items        = db.Column(db.Text)
    total        = db.Column(db.Float)
    status       = db.Column(db.String(20), default='processing')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class HealthRecord(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symptoms     = db.Column(db.Text)
    diagnosis    = db.Column(db.String(100))
    confidence   = db.Column(db.Float)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class Medicine(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100))
    category     = db.Column(db.String(50))
    price        = db.Column(db.Float)
    stock        = db.Column(db.Integer, default=100)
    img          = db.Column(db.String(10), default='💊')
    desc         = db.Column(db.String(200))
    active       = db.Column(db.Boolean, default=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ─── ML MODEL ─────────────────────────────────────────────
with open('model/model.pkl','rb') as f: ml_model = pickle.load(f)
with open('model/label_encoder.pkl','rb') as f: le = pickle.load(f)
SYMPTOM_KEYS = ['fever','cough','headache','fatigue','sore_throat','body_ache','nausea','runny_nose']

DISEASE_INFO = {
    'Flu':      {'description':'Influenza is a viral infection attacking your respiratory system.','severity':'Moderate','advice':'Rest, stay hydrated, take fever reducers.','color':'#e74c3c'},
    'Cold':     {'description':'A mild viral infection of the nose and throat.','severity':'Mild','advice':'Rest, drink fluids, use OTC cold remedies.','color':'#3498db'},
    'Migraine': {'description':'An intense recurring headache, often with nausea.','severity':'Moderate','advice':'Rest in a dark quiet room, stay hydrated.','color':'#9b59b6'}
}

CHATBOT_RESPONSES = {
    'hello':'Hello! I am MedBot. How can I help you today?',
    'hi':'Hi! Tell me your symptoms and I will help analyze them.',
    'fever':'Fever indicates possible infection. If above 103°F seek medical attention immediately.',
    'cough':'Persistent cough over 2 weeks needs medical attention.',
    'headache':'Could be tension, migraine or cluster type. Use Symptom Checker for analysis.',
    'tired':'Fatigue can signal anemia, thyroid issues or infections.',
    'help':'I can analyze symptoms, guide you to specialists, and provide health tips!',
    'thanks':'You are welcome! Stay healthy.',
    'pain':'Describe the location and nature of pain. Use Symptom Checker for detailed analysis.',
    'doctor':'Go to Appointments tab to book with a specialist.',
    'medicine':'Check our Medicine Store for a wide range of medications.',
}

# ─── PAGE ROUTES ──────────────────────────────────────────
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('route_by_role'))
    return render_template('intro.html')

@app.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('route_by_role'))
    return render_template('login.html')

@app.route('/route')
@login_required
def route_by_role():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    elif current_user.role == 'developer':
        return redirect(url_for('dev_dashboard'))
    else:
        return redirect(url_for('patient_dashboard'))

@app.route('/dashboard')
@login_required
def patient_dashboard():
    if current_user.role not in ['user']:
        return redirect(url_for('route_by_role'))
    return render_template('index.html', user=current_user)

@app.route('/doctor')
@login_required
def doctor_dashboard():
    if current_user.role not in ['doctor']:
        return redirect(url_for('route_by_role'))
    return render_template('doctor.html', user=current_user)

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role not in ['admin']:
        return redirect(url_for('route_by_role'))
    return render_template('admin.html', user=current_user)

@app.route('/developer')
@login_required
def dev_dashboard():
    if current_user.role not in ['developer']:
        return redirect(url_for('route_by_role'))
    return render_template('developer.html', user=current_user)

# ─── AUTH APIs ────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error':'Email already registered'}), 400
    user = User(
        name=data['name'], email=data['email'],
        password=generate_password_hash(data['password']),
        role=data.get('role','user'),
        avatar=data['name'][0].upper()
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message':'Account created!'})

@app.route('/api/login', methods=['POST'])
def do_login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'error':'Invalid email or password'}), 401
    if user.is_banned:
        return jsonify({'error':'Account suspended. Contact admin.'}), 403
    user.last_login = datetime.utcnow()
    db.session.commit()
    login_user(user)
    redirects = {'admin':'/admin','doctor':'/doctor','developer':'/developer'}
    return jsonify({'message':'Login successful','role':user.role,'name':user.name,
                    'redirect': redirects.get(user.role, '/dashboard')})

@app.route('/api/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message':'Logged out'})

@app.route('/api/current-user')
@login_required
def get_current_user():
    return jsonify({
        'id':current_user.id, 'name':current_user.name,
        'email':current_user.email, 'role':current_user.role,
        'avatar':current_user.avatar, 'phone':current_user.phone,
        'blood_group':current_user.blood_group, 'age':current_user.age,
        'address':current_user.address, 'bio':current_user.bio,
        'specialization':current_user.specialization,
        'experience':current_user.experience,
        'created_at':current_user.created_at.strftime('%d %b %Y')
    })

@app.route('/api/update-profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    current_user.name    = data.get('name', current_user.name)
    current_user.phone   = data.get('phone', current_user.phone)
    current_user.age     = data.get('age', current_user.age)
    current_user.blood_group = data.get('blood_group', current_user.blood_group)
    current_user.address = data.get('address', current_user.address)
    current_user.bio     = data.get('bio', current_user.bio)
    current_user.specialization = data.get('specialization', current_user.specialization)
    current_user.experience = data.get('experience', current_user.experience)
    db.session.commit()
    return jsonify({'message':'Profile updated!'})

# ─── CHAT APIs ────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message','').lower()
    for kw, resp in CHATBOT_RESPONSES.items():
        if kw in message:
            return jsonify({'response': resp})
    symptoms_found = [s for s in SYMPTOM_KEYS if s.replace('_',' ') in message or s in message]
    if symptoms_found:
        return jsonify({'response': f"I noticed: {', '.join(symptoms_found)}. Use Symptom Checker for full AI analysis!"})
    return jsonify({'response':"Describe your symptoms or ask about a condition and I will help!"})

@app.route('/api/send-message', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    msg = Message(
        sender_id=current_user.id,
        receiver_id=data['receiver_id'],
        sender_name=current_user.name,
        content=data['content']
    )
    db.session.add(msg)
    db.session.commit()
    return jsonify({'message':'Sent!', 'id':msg.id,
                    'time':msg.created_at.strftime('%H:%M')})

@app.route('/api/get-messages/<int:other_id>')
@login_required
def get_messages(other_id):
    msgs = Message.query.filter(
        ((Message.sender_id==current_user.id) & (Message.receiver_id==other_id)) |
        ((Message.sender_id==other_id) & (Message.receiver_id==current_user.id))
    ).order_by(Message.created_at.asc()).all()
    Message.query.filter_by(receiver_id=current_user.id, sender_id=other_id, read=False).update({'read':True})
    db.session.commit()
    return jsonify({'messages':[{
        'id':m.id, 'sender_id':m.sender_id, 'sender_name':m.sender_name,
        'content':m.content, 'time':m.created_at.strftime('%H:%M %d %b'),
        'is_mine': m.sender_id == current_user.id
    } for m in msgs]})

@app.route('/api/get-contacts')
@login_required
def get_contacts():
    if current_user.role in ['admin','developer']:
        users = User.query.filter(User.id != current_user.id).all()
    elif current_user.role == 'doctor':
        patient_ids = db.session.query(Appointment.patient_id).filter_by(doctor_name=current_user.name).distinct()
        users = User.query.filter(User.id.in_(patient_ids)).all()
        admins = User.query.filter_by(role='admin').all()
        users = list(users) + admins
    else:
        doctor_users = User.query.filter_by(role='doctor').all()
        admins = User.query.filter_by(role='admin').all()
        users = list(doctor_users) + admins
    return jsonify({'contacts':[{
        'id':u.id, 'name':u.name, 'role':u.role, 'avatar':u.avatar,
        'unread': Message.query.filter_by(sender_id=u.id, receiver_id=current_user.id, read=False).count()
    } for u in users]})

# ─── SYMPTOM / ML APIs ────────────────────────────────────
@app.route('/api/predict', methods=['POST'])
@login_required
def predict():
    data = request.get_json()
    symptoms = data.get('symptoms',{})
    features = np.array([[int(symptoms.get(s,0)) for s in SYMPTOM_KEYS]])
    pred_enc   = ml_model.predict(features)[0]
    probs      = ml_model.predict_proba(features)[0]
    disease    = le.inverse_transform([pred_enc])[0]
    confidence = round(float(max(probs))*100,1)
    all_probs  = {le.inverse_transform([i])[0]: round(float(p)*100,1) for i,p in enumerate(probs)}
    info = DISEASE_INFO.get(disease,{})
    record = HealthRecord(user_id=current_user.id, symptoms=str(symptoms),
                          diagnosis=disease, confidence=confidence)
    db.session.add(record)
    db.session.commit()
    return jsonify({'disease':disease,'confidence':confidence,'probabilities':all_probs,
                    'description':info.get('description',''),'severity':info.get('severity',''),
                    'advice':info.get('advice',''),'color':info.get('color','#333')})

@app.route('/api/stats')
def stats():
    return jsonify({
        'symptom_frequency':{'Fever':65,'Cough':58,'Headache':45,'Fatigue':72,'Sore Throat':38,'Body Ache':41,'Nausea':33,'Runny Nose':29},
        'disease_distribution':{'Flu':40,'Cold':35,'Migraine':25},
        'monthly_cases':{'Jan':120,'Feb':98,'Mar':145,'Apr':87,'May':63,'Jun':55,'Jul':48,'Aug':52,'Sep':78,'Oct':110,'Nov':134,'Dec':160},
        'age_groups':{'0-18':15,'19-35':32,'36-50':28,'51-65':18,'65+':7},
        'recovery_rate':{'Flu':87,'Cold':95,'Migraine':78}
    })

# ─── APPOINTMENT APIs ─────────────────────────────────────
@app.route('/api/doctors')
def get_doctors():
    doctors = User.query.filter_by(role='doctor', is_banned=False).all()
    default_slots = ['9:00 AM','10:00 AM','11:00 AM','2:00 PM','3:00 PM','4:00 PM']
    return jsonify({'doctors':[{
        'id':d.id, 'name':d.name, 'spec':d.specialization or 'General Physician',
        'exp':d.experience or '5 yrs', 'rating':4.8, 'avatar':d.avatar,
        'slots': default_slots, 'fee': 500
    } for d in doctors]})

@app.route('/api/appointment', methods=['POST'])
@login_required
def book_appointment():
    data = request.get_json()
    appt = Appointment(
        patient_id=current_user.id, patient_name=current_user.name,
        doctor_name=data['doctor'], date=data['date'],
        time=data['time'], reason=data['reason'],
        fee=data.get('fee',500)
    )
    db.session.add(appt)
    db.session.commit()
    return jsonify({'message':'Appointment booked!','id':appt.id})

@app.route('/api/my-appointments')
@login_required
def my_appointments():
    appts = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.created_at.desc()).all()
    return jsonify({'appointments':[{
        'id':a.id,'doctor':a.doctor_name,'date':a.date,'time':a.time,
        'reason':a.reason,'status':a.status,'fee':a.fee,'paid':a.paid,
        'notes':a.notes
    } for a in appts]})

@app.route('/api/pay-appointment/<int:appt_id>', methods=['POST'])
@login_required
def pay_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.patient_id != current_user.id:
        return jsonify({'error':'Unauthorized'}), 403
    appt.paid = True
    db.session.commit()
    return jsonify({'message':'Payment successful!'})

# ─── DOCTOR APIs ──────────────────────────────────────────
@app.route('/api/doctor/appointments')
@login_required
def doctor_appointments():
    if current_user.role != 'doctor':
        return jsonify({'error':'Unauthorized'}), 403
    appts = Appointment.query.filter_by(doctor_name=current_user.name).order_by(Appointment.created_at.desc()).all()
    return jsonify({'appointments':[{
        'id':a.id,'patient':a.patient_name,'patient_id':a.patient_id,
        'date':a.date,'time':a.time,'reason':a.reason,
        'status':a.status,'fee':a.fee,'paid':a.paid,
        'created':a.created_at.strftime('%d %b %Y')
    } for a in appts]})

@app.route('/api/doctor/update-appointment/<int:appt_id>', methods=['POST'])
@login_required
def update_appointment(appt_id):
    if current_user.role != 'doctor':
        return jsonify({'error':'Unauthorized'}), 403
    data = request.get_json()
    appt = Appointment.query.get_or_404(appt_id)
    appt.status = data.get('status', appt.status)
    appt.notes  = data.get('notes', appt.notes)
    db.session.commit()
    return jsonify({'message':'Updated!'})

@app.route('/api/doctor/patients')
@login_required
def doctor_patients():
    if current_user.role != 'doctor':
        return jsonify({'error':'Unauthorized'}), 403
    patient_ids = db.session.query(Appointment.patient_id).filter_by(doctor_name=current_user.name).distinct()
    patients = User.query.filter(User.id.in_(patient_ids)).all()
    return jsonify({'patients':[{
        'id':p.id,'name':p.name,'email':p.email,'age':p.age,
        'blood_group':p.blood_group,'phone':p.phone,'avatar':p.avatar
    } for p in patients]})

@app.route('/api/doctor/patient-records/<int:patient_id>')
@login_required
def patient_records(patient_id):
    if current_user.role != 'doctor':
        return jsonify({'error':'Unauthorized'}), 403
    records = HealthRecord.query.filter_by(user_id=patient_id).order_by(HealthRecord.created_at.desc()).all()
    appts   = Appointment.query.filter_by(patient_id=patient_id, doctor_name=current_user.name).all()
    return jsonify({
        'records':[{'diagnosis':r.diagnosis,'confidence':r.confidence,'date':r.created_at.strftime('%d %b %Y')} for r in records],
        'appointments':[{'date':a.date,'time':a.time,'reason':a.reason,'status':a.status} for a in appts]
    })

@app.route('/api/doctor/prescribe', methods=['POST'])
@login_required
def prescribe():
    if current_user.role != 'doctor':
        return jsonify({'error':'Unauthorized'}), 403
    data = request.get_json()
    rx = Prescription(
        patient_id=data['patient_id'], doctor_id=current_user.id,
        doctor_name=current_user.name,
        patient_name=User.query.get(data['patient_id']).name,
        medicines=data['medicines'], instructions=data['instructions'],
        diagnosis=data['diagnosis']
    )
    db.session.add(rx)
    db.session.commit()
    return jsonify({'message':'Prescription sent!','id':rx.id})

@app.route('/api/doctor/earnings')
@login_required
def doctor_earnings():
    if current_user.role != 'doctor':
        return jsonify({'error':'Unauthorized'}), 403
    appts = Appointment.query.filter_by(doctor_name=current_user.name).all()
    total    = sum(a.fee for a in appts if a.paid)
    pending  = sum(a.fee for a in appts if not a.paid and a.status=='confirmed')
    return jsonify({'total_earned':total,'pending':pending,
                    'total_appointments':len(appts),
                    'confirmed':len([a for a in appts if a.status=='confirmed']),
                    'pending_count':len([a for a in appts if a.status=='pending'])})

@app.route('/api/my-prescriptions')
@login_required
def my_prescriptions():
    rxs = Prescription.query.filter_by(patient_id=current_user.id).order_by(Prescription.created_at.desc()).all()
    return jsonify({'prescriptions':[{
        'id':r.id,'doctor':r.doctor_name,'diagnosis':r.diagnosis,
        'medicines':r.medicines,'instructions':r.instructions,
        'date':r.created_at.strftime('%d %b %Y')
    } for r in rxs]})

# ─── MEDICINE / STORE APIs ────────────────────────────────
@app.route('/api/medicines')
def get_medicines():
    category = request.args.get('category','all')
    search   = request.args.get('search','').lower()
    q = Medicine.query.filter_by(active=True)
    if category != 'all':
        q = q.filter_by(category=category)
    meds = q.all()
    if search:
        meds = [m for m in meds if search in m.name.lower() or search in m.desc.lower()]
    return jsonify({'medicines':[{'id':m.id,'name':m.name,'category':m.category,
        'price':m.price,'stock':m.stock,'img':m.img,'desc':m.desc} for m in meds]})

@app.route('/api/order', methods=['POST'])
@login_required
def place_order():
    data  = request.get_json()
    order = Order(user_id=current_user.id, patient_name=current_user.name,
                  items=json.dumps(data['items']), total=data['total'])
    db.session.add(order)
    db.session.commit()
    return jsonify({'message':'Order placed!','order_id':order.id})

@app.route('/api/my-orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return jsonify({'orders':[{
        'id':o.id,'items':json.loads(o.items),'total':o.total,
        'status':o.status,'date':o.created_at.strftime('%d %b %Y')
    } for o in orders]})

@app.route('/api/my-records')
@login_required
def my_records():
    records = HealthRecord.query.filter_by(user_id=current_user.id).order_by(HealthRecord.created_at.desc()).limit(20).all()
    return jsonify({'records':[{
        'diagnosis':r.diagnosis,'confidence':r.confidence,
        'date':r.created_at.strftime('%d %b %Y %H:%M')
    } for r in records]})

# ─── ADMIN APIs ───────────────────────────────────────────
@app.route('/api/admin/users')
@login_required
def admin_get_users():
    if current_user.role not in ['admin','developer']:
        return jsonify({'error':'Unauthorized'}), 403
    users = User.query.all()
    return jsonify({'users':[{
        'id':u.id,'name':u.name,'email':u.email,'role':u.role,
        'is_banned':u.is_banned,'avatar':u.avatar,
        'created_at':u.created_at.strftime('%d %b %Y'),
        'last_login':u.last_login.strftime('%d %b %Y') if u.last_login else 'Never',
        'phone':u.phone,'age':u.age
    } for u in users]})

@app.route('/api/admin/update-user/<int:user_id>', methods=['POST'])
@login_required
def admin_update_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'error':'Unauthorized'}), 403
    data = request.get_json()
    user = User.query.get_or_404(user_id)
    if 'role' in data:      user.role      = data['role']
    if 'is_banned' in data: user.is_banned = data['is_banned']
    db.session.commit()
    return jsonify({'message':'User updated!'})

@app.route('/api/admin/delete-user/<int:user_id>', methods=['DELETE'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'error':'Unauthorized'}), 403
    user = User.query.get_or_404(user_id)
    if user.role in ['admin','developer']:
        return jsonify({'error':'Cannot delete admin or developer'}), 403
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message':'User deleted!'})

@app.route('/api/admin/all-appointments')
@login_required
def admin_all_appointments():
    if current_user.role not in ['admin','developer']:
        return jsonify({'error':'Unauthorized'}), 403
    appts = Appointment.query.order_by(Appointment.created_at.desc()).all()
    return jsonify({'appointments':[{
        'id':a.id,'patient':a.patient_name,'doctor':a.doctor_name,
        'date':a.date,'time':a.time,'reason':a.reason,
        'status':a.status,'fee':a.fee,'paid':a.paid
    } for a in appts]})

@app.route('/api/admin/all-orders')
@login_required
def admin_all_orders():
    if current_user.role not in ['admin','developer']:
        return jsonify({'error':'Unauthorized'}), 403
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return jsonify({'orders':[{
        'id':o.id,'patient':o.patient_name,'total':o.total,
        'status':o.status,'date':o.created_at.strftime('%d %b %Y'),
        'items':json.loads(o.items)
    } for o in orders]})

@app.route('/api/admin/update-order/<int:order_id>', methods=['POST'])
@login_required
def admin_update_order(order_id):
    if current_user.role != 'admin':
        return jsonify({'error':'Unauthorized'}), 403
    data = request.get_json()
    order = Order.query.get_or_404(order_id)
    order.status = data.get('status', order.status)
    db.session.commit()
    return jsonify({'message':'Order updated!'})

@app.route('/api/admin/medicines', methods=['GET'])
@login_required
def admin_medicines():
    if current_user.role not in ['admin','developer']:
        return jsonify({'error':'Unauthorized'}), 403
    meds = Medicine.query.all()
    return jsonify({'medicines':[{
        'id':m.id,'name':m.name,'category':m.category,
        'price':m.price,'stock':m.stock,'img':m.img,
        'desc':m.desc,'active':m.active
    } for m in meds]})

@app.route('/api/admin/add-medicine', methods=['POST'])
@login_required
def admin_add_medicine():
    if current_user.role != 'admin':
        return jsonify({'error':'Unauthorized'}), 403
    data = request.get_json()
    med = Medicine(name=data['name'],category=data['category'],
                   price=data['price'],stock=data['stock'],
                   img=data.get('img','💊'),desc=data['desc'])
    db.session.add(med)
    db.session.commit()
    return jsonify({'message':'Medicine added!','id':med.id})

@app.route('/api/admin/update-medicine/<int:med_id>', methods=['POST'])
@login_required
def admin_update_medicine(med_id):
    if current_user.role != 'admin':
        return jsonify({'error':'Unauthorized'}), 403
    data = request.get_json()
    med = Medicine.query.get_or_404(med_id)
    for field in ['name','category','price','stock','desc','active']:
        if field in data: setattr(med, field, data[field])
    db.session.commit()
    return jsonify({'message':'Medicine updated!'})

@app.route('/api/admin/delete-medicine/<int:med_id>', methods=['DELETE'])
@login_required
def admin_delete_medicine(med_id):
    if current_user.role != 'admin':
        return jsonify({'error':'Unauthorized'}), 403
    med = Medicine.query.get_or_404(med_id)
    db.session.delete(med)
    db.session.commit()
    return jsonify({'message':'Medicine deleted!'})

@app.route('/api/admin/analytics')
@login_required
def admin_analytics():
    if current_user.role not in ['admin','developer']:
        return jsonify({'error':'Unauthorized'}), 403
    total_users   = User.query.count()
    total_doctors = User.query.filter_by(role='doctor').count()
    total_appts   = Appointment.query.count()
    total_orders  = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total)).scalar() or 0
    appt_revenue  = db.session.query(db.func.sum(Appointment.fee)).filter_by(paid=True).scalar() or 0
    return jsonify({
        'total_users':total_users,'total_doctors':total_doctors,
        'total_appointments':total_appts,'total_orders':total_orders,
        'total_revenue':round(total_revenue,2),'appointment_revenue':round(appt_revenue,2),
        'banned_users':User.query.filter_by(is_banned=True).count(),
        'pending_appointments':Appointment.query.filter_by(status='pending').count()
    })

# ─── DEVELOPER APIs ───────────────────────────────────────
@app.route('/api/dev/db-stats')
@login_required
def dev_db_stats():
    if current_user.role != 'developer':
        return jsonify({'error':'Unauthorized'}), 403
    return jsonify({
        'tables':['user','appointment','prescription','message','order','health_record','medicine'],
        'counts':{
            'users':User.query.count(),
            'appointments':Appointment.query.count(),
            'prescriptions':Prescription.query.count(),
            'messages':Message.query.count(),
            'orders':Order.query.count(),
            'health_records':HealthRecord.query.count(),
            'medicines':Medicine.query.count()
        }
    })

@app.route('/api/dev/logs')
@login_required
def dev_logs():
    if current_user.role != 'developer':
        return jsonify({'error':'Unauthorized'}), 403
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_appts = Appointment.query.order_by(Appointment.created_at.desc()).limit(5).all()
    return jsonify({
        'recent_signups':[{'name':u.name,'role':u.role,'date':u.created_at.strftime('%d %b %H:%M')} for u in recent_users],
        'recent_appointments':[{'patient':a.patient_name,'doctor':a.doctor_name,'date':a.date,'status':a.status} for a in recent_appts]
    })
# ─── NEW FEATURES ─────────────────────────────────────────

@app.route('/api/bmi', methods=['POST'])
def calculate_bmi():
    data = request.get_json()
    weight = float(data['weight'])
    height = float(data['height']) / 100
    bmi = round(weight / (height ** 2), 1)
    if bmi < 18.5:
        category = 'Underweight'
        color = '#06b6d4'
        advice = 'Consider a nutrient-rich diet. Consult a nutritionist.'
    elif bmi < 25:
        category = 'Normal weight'
        color = '#10b981'
        advice = 'Great! Maintain your healthy lifestyle.'
    elif bmi < 30:
        category = 'Overweight'
        color = '#f59e0b'
        advice = 'Consider more physical activity and a balanced diet.'
    else:
        category = 'Obese'
        color = '#ef4444'
        advice = 'Please consult a doctor for a health plan.'
    return jsonify({'bmi': bmi, 'category': category,
                    'color': color, 'advice': advice})

@app.route('/api/notifications')
@login_required
def get_notifications():
    notifs = []
    appts = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.created_at.desc()).limit(5).all()
    for a in appts:
        if a.status == 'confirmed':
            notifs.append({'type':'success','title':'Appointment Confirmed','msg':f'Dr. {a.doctor_name} confirmed your appointment on {a.date}','time':a.created_at.strftime('%H:%M')})
        elif a.status == 'rejected':
            notifs.append({'type':'error','title':'Appointment Rejected','msg':f'Dr. {a.doctor_name} rejected your request','time':a.created_at.strftime('%H:%M')})
    rxs = Prescription.query.filter_by(patient_id=current_user.id).order_by(Prescription.created_at.desc()).limit(3).all()
    for r in rxs:
        notifs.append({'type':'info','title':'New Prescription','msg':f'Dr. {r.doctor_name} sent you a prescription for {r.diagnosis}','time':r.created_at.strftime('%H:%M')})
    msgs = Message.query.filter_by(receiver_id=current_user.id, read=False).order_by(Message.created_at.desc()).limit(3).all()
    for m in msgs:
        notifs.append({'type':'info','title':'New Message','msg':f'{m.sender_name}: {m.content[:40]}...','time':m.created_at.strftime('%H:%M')})
    return jsonify({'notifications': notifs[:8], 'unread': len(notifs)})

@app.route('/api/blood-donors')
@login_required
def blood_donors():
    blood_group = request.args.get('blood_group', '')
    users = User.query.filter_by(is_banned=False).all()
    donors = []
    for u in users:
        if u.blood_group and (not blood_group or u.blood_group == blood_group):
            donors.append({
                'name': u.name, 'blood_group': u.blood_group,
                'phone': u.phone or 'Not provided',
                'avatar': u.avatar
            })
    return jsonify({'donors': donors})

@app.route('/api/health-news')
def health_news():
    news = [
        {'title':'WHO reports decline in global malaria cases in 2024','source':'WHO','time':'2h ago','category':'Global Health','color':'#4f8ef7'},
        {'title':'New AI model predicts diabetes risk with 94% accuracy','source':'Nature Medicine','time':'4h ago','category':'AI & Health','color':'#a855f7'},
        {'title':'Study links daily walking to 30% lower heart disease risk','source':'Lancet','time':'6h ago','category':'Cardiology','color':'#10b981'},
        {'title':'India launches new nationwide vaccination drive for 2025','source':'Health Ministry','time':'8h ago','category':'Vaccination','color':'#f59e0b'},
        {'title':'Breakthrough in Alzheimer treatment shows promising results','source':'NEJM','time':'12h ago','category':'Neurology','color':'#ef4444'},
        {'title':'Mental health apps usage surges 45% post pandemic','source':'JAMA','time':'1d ago','category':'Mental Health','color':'#ec4899'},
        {'title':'New antibiotic discovered after 30 years of research','source':'Science','time':'1d ago','category':'Antibiotics','color':'#06b6d4'},
        {'title':'Exercise reduces depression risk by 43% says new study','source':'BMJ','time':'2d ago','category':'Mental Health','color':'#10b981'},
    ]
    return jsonify({'news': news})

@app.route('/api/video-call', methods=['POST'])
@login_required
def book_video_call():
    data = request.get_json()
    appt = Appointment(
        patient_id=current_user.id,
        patient_name=current_user.name,
        doctor_name=data['doctor'],
        date=data['date'],
        time=data['time'],
        reason=f"[VIDEO CALL] {data['reason']}",
        fee=data.get('fee', 300)
    )
    db.session.add(appt)
    db.session.commit()
    return jsonify({'message':'Video call scheduled!', 'id':appt.id,
                    'meet_link':f'https://meet.healthai.com/room/{appt.id}'})

@app.route('/api/generate-report')
@login_required
def generate_report():
    records = HealthRecord.query.filter_by(user_id=current_user.id).order_by(HealthRecord.created_at.desc()).limit(10).all()
    appts   = Appointment.query.filter_by(patient_id=current_user.id).all()
    rxs     = Prescription.query.filter_by(patient_id=current_user.id).all()
    return jsonify({
        'patient': {'name':current_user.name,'email':current_user.email,'age':current_user.age,'blood_group':current_user.blood_group},
        'diagnoses': [{'diagnosis':r.diagnosis,'confidence':r.confidence,'date':r.created_at.strftime('%d %b %Y')} for r in records],
        'appointments': len(appts),
        'prescriptions': len(rxs),
        'generated_at': datetime.utcnow().strftime('%d %b %Y %H:%M')
    })

if __name__ == '__main__':
    import os
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'healthai_secret_2024_ruban_dev')
    with app.app_context():
        db.create_all()
        # Seed medicines if empty
        if Medicine.query.count() == 0:
            medicines = [
                Medicine(name='Paracetamol 500mg',category='Pain Relief',price=45,stock=150,img='💊',desc='For fever and mild pain relief'),
                Medicine(name='Cetirizine 10mg',category='Allergy',price=65,stock=80,img='💊',desc='Antihistamine for allergy symptoms'),
                Medicine(name='Amoxicillin 250mg',category='Antibiotic',price=120,stock=60,img='💊',desc='Broad spectrum antibiotic'),
                Medicine(name='Ibuprofen 400mg',category='Pain Relief',price=55,stock=200,img='💊',desc='Anti-inflammatory pain relief'),
                Medicine(name='Vitamin C 1000mg',category='Supplement',price=180,stock=300,img='🍊',desc='Immune system support'),
                Medicine(name='Omeprazole 20mg',category='Gastric',price=95,stock=120,img='💊',desc='Acid reflux and gastric issues'),
                Medicine(name='Metformin 500mg',category='Diabetes',price=75,stock=90,img='💊',desc='Blood sugar management'),
                Medicine(name='Atorvastatin 10mg',category='Cardiac',price=140,stock=75,img='❤️',desc='Cholesterol management'),
                Medicine(name='Zinc + Vitamin D',category='Supplement',price=220,stock=250,img='✨',desc='Immunity and bone health'),
                Medicine(name='Cough Syrup 100ml',category='Respiratory',price=85,stock=110,img='🍶',desc='Dry and wet cough relief'),
                Medicine(name='Eye Drops 10ml',category='Eye Care',price=65,stock=95,img='👁️',desc='Dry eye and irritation relief'),
                Medicine(name='Antacid Tablets',category='Gastric',price=40,stock=400,img='💊',desc='Instant acidity relief'),
            ]
            for m in medicines: db.session.add(m)
        # Seed default accounts
        accounts = [
            ('Admin','admin@healthai.com','admin123','admin','A'),
            ('Dr. Priya Sharma','priya@healthai.com','doctor123','doctor','P'),
            ('Dr. Arjun Mehta','arjun@healthai.com','doctor123','doctor','A'),
            ('Dr. Sneha Rao','sneha@healthai.com','doctor123','doctor','S'),
            ('Test Patient','user@healthai.com','user123','user','T'),
            ('Dev Portal','dev@healthai.com','dev123secure','developer','D'),
        ]
        for name,email,pwd,role,av in accounts:
            if not User.query.filter_by(email=email).first():
                u = User(name=name,email=email,password=generate_password_hash(pwd),
                         role=role,avatar=av)
                if role == 'doctor':
                    u.specialization = 'General Physician'
                    u.experience = '10 yrs'
                db.session.add(u)
        db.session.commit()
        print("✅ DB ready! All accounts seeded.")
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))