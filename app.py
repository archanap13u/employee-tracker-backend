from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import jwt
import datetime
import os

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:8000", "https://employee-tracker-frontend.vercel.app"]}})

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///tracker.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='offline')
    active_time = db.Column(db.Float, default=0.0)
    idle_time = db.Column(db.Float, default=0.0)
    productivity = db.Column(db.Integer, default=0)
    current_activity = db.Column(db.String(200), default='')
    last_active = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class AppUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_name = db.Column(db.String(100), nullable=False)
    time_spent = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(50), default='neutral')
    icon = db.Column(db.String(10), default='💻')

class WebsiteUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), nullable=False)
    time_spent = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(50), default='neutral')
    visits = db.Column(db.Integer, default=0)

with app.app_context():
    db.create_all()
    if not User.query.first():
        hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
        db.session.add(User(username='admin', password=hashed_password))
    if not Employee.query.first():
        db.session.add(Employee(name='Sarah Johnson', status='active', active_time=6.5, idle_time=0.5, productivity=92, current_activity='VS Code - React Development'))
        db.session.add(Employee(name='Michael Chen', status='idle', active_time=5.8, idle_time=1.2, productivity=78, current_activity='Idle for 8 minutes'))
        db.session.add(Employee(name='Emily Davis', status='active', active_time=6.2, idle_time=0.8, productivity=88, current_activity='Figma - UI Design'))
        db.session.add(Employee(name='James Wilson', status='active', active_time=7.1, idle_time=0.4, productivity=95, current_activity='Chrome - Documentation'))
        db.session.add(Employee(name='Lisa Brown', status='offline', active_time=4.5, idle_time=0.5, productivity=65, current_activity='Not clocked in'))
    if not AppUsage.query.first():
        db.session.add(AppUsage(app_name='VS Code', time_spent=4.5, category='productive', icon='💻'))
        db.session.add(AppUsage(app_name='Chrome', time_spent=3.2, category='neutral', icon='🌐'))
        db.session.add(AppUsage(app_name='Slack', time_spent=1.8, category='neutral', icon='💬'))
        db.session.add(AppUsage(app_name='Figma', time_spent=2.5, category='productive', icon='🎨'))
    if not WebsiteUsage.query.first():
        db.session.add(WebsiteUsage(url='github.com', time_spent=2.5, category='productive', visits=45))
        db.session.add(WebsiteUsage(url='stackoverflow.com', time_spent=1.8, category='productive', visits=32))
        db.session.add(WebsiteUsage(url='gmail.com', time_spent=1.2, category='neutral', visits=28))
    db.session.commit()

def authenticate_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ')[1]
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return User.query.filter_by(username=data['username']).first()
    except:
        return None

@app.route('/')
def home():
    return {"message": "Employee Tracker Backend API"}, 200

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and bcrypt.check_password_hash(user.password, data['password']):
        token = jwt.encode({
            'username': user.username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({'token': token})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/employees', methods=['GET'])
def get_employees():
    user = authenticate_token()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    employees = Employee.query.all()
    return jsonify({
        'employees': [
            {
                'id': emp.id,
                'name': emp.name,
                'status': emp.status,
                'activeTime': emp.active_time,
                'idleTime': emp.idle_time,
                'productivity': emp.productivity,
                'currentActivity': emp.current_activity,
                'lastActive': emp.last_active.isoformat()
            } for emp in employees
        ]
    })

@app.route('/api/analytics/productivity', methods=['GET'])
def get_productivity():
    user = authenticate_token()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    employees = Employee.query.all()
    active = len([e for e in employees if e.status == 'active'])
    total_hours = sum(e.active_time for e in employees)
    avg_productivity = sum(e.productivity for e in employees) / len(employees) if employees else 0
    return jsonify({
        'total_employees': len(employees),
        'active_employees': active,
        'avg_productivity': round(avg_productivity, 1),
        'total_work_hours': round(total_hours, 1)
    })

@app.route('/api/analytics/applications', methods=['GET'])
def get_applications():
    user = authenticate_token()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    apps = AppUsage.query.all()
    return jsonify([
        {
            'app': app.app_name,
            'time': app.time_spent,
            'category': app.category,
            'icon': app.icon
        } for app in apps
    ])

@app.route('/api/analytics/websites', methods=['GET'])
def get_websites():
    user = authenticate_token()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    websites = WebsiteUsage.query.all()
    return jsonify([
        {
            'url': w.url,
            'time': w.time_spent,
            'category': w.category,
            'visits': w.visits
        } for w in websites
    ])

@app.route('/api/reports/generate', methods=['POST'])
def generate_report():
    user = authenticate_token()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    emp_id = data.get('employeeId')
    range_type = data.get('range', 'today')
    employees = Employee.query.filter_by(id=emp_id).all() if emp_id else Employee.query.all()
    total_hours = sum(e.active_time for e in employees)
    idle_hours = sum(e.idle_time for e in employees)
    productivity = sum(e.productivity for e in employees) / len(employees) if employees else 0
    return jsonify({
        'range': range_type,
        'total_hours': round(total_hours, 1),
        'active_hours': round(total_hours - idle_hours, 1),
        'idle_hours': round(idle_hours, 1),
        'productivity': round(productivity, 1),
        'daily_breakdown': [
            {'day': day, 'active': round(total_hours/5, 1), 'idle': round(idle_hours/5, 1), 'productivity': round(productivity, 1)}
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        ]
    })

@app.route('/api/settings/update', methods=['POST'])
def update_settings():
    user = authenticate_token()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    return jsonify({'message': 'Settings updated successfully', 'settings': data})

@app.route('/downloads/<platform>', methods=['GET'])
def download_agent(platform):
    return jsonify({'message': f'Downloading {platform} agent. In production, serve actual file.'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)