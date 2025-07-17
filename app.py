from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

# Data Models
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    field = db.Column(db.String(100))
    stage = db.Column(db.String(50))
    abstract = db.Column(db.Text)
    priority = db.Column(db.String(10))  # Change to String: "High", "Medium", "Low"
    deadline = db.Column(db.String(10))  # Format: "YYYY-MM-DD"
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Collaborator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    role = db.Column(db.String(100))

# Routes
@app.route('/api/projects', methods=['GET'])
def get_projects():
    projects = Project.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'field': p.field,
        'stage': p.stage,
        'abstract': p.abstract,
        'priority': p.priority,
        'deadline': p.deadline,
        'created_at': p.created_at.isoformat()
    } for p in projects])

@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.json
    new_project = Project(
        name=data['name'],
        stage=data.get('stage', ''),
        abstract=data.get('abstract', ''),
        field=data.get('field', ''),
        priority=data.get('priority', ''),       # Store as "High", "Medium", "Low"
        deadline=data.get('deadline', '')        # Store as string "YYYY-MM-DD"
    )
    db.session.add(new_project)
    db.session.commit()
    return jsonify({'message': 'Project created successfully'}), 201

@app.route('/api/projects/<int:id>', methods=['PUT'])
def update_project(id):
    project = Project.query.get_or_404(id)
    data = request.json
    project.name = data.get('name', project.name)
    project.stage = data.get('stage', project.stage)
    project.abstract = data.get('abstract', project.abstract)
    project.field = data.get('field', project.field)
    project.priority = data.get('priority', project.priority)
    project.deadline = data.get('deadline', project.deadline)
    db.session.commit()
    return jsonify({'message': 'Project updated successfully'})

@app.route('/api/projects/<int:id>', methods=['DELETE'])
def delete_project(id):
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted successfully'})

@app.route('/api/projects/<int:project_id>/collaborators', methods=['POST'])
def add_collaborator(project_id):
    data = request.json
    collaborator = Collaborator(
        project_id=project_id,
        name=data['name'],
        email=data['email'],
        role=data['role']
    )
    db.session.add(collaborator)
    db.session.commit()
    return jsonify({'message': 'Collaborator added successfully'}), 201

@app.route('/api/projects/<int:project_id>/collaborators', methods=['GET'])
def get_collaborators(project_id):
    collaborators = Collaborator.query.filter_by(project_id=project_id).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'email': c.email,
        'role': c.role
    } for c in collaborators])

@app.route('/api/collaborators/<int:collab_id>', methods=['DELETE'])
def delete_collaborator(collab_id):
    collaborator = Collaborator.query.get_or_404(collab_id)
    db.session.delete(collaborator)
    db.session.commit()
    return jsonify({'message': 'Collaborator deleted successfully'})

# EMAIL ENDPOINT - NEWLY ADDED
@app.route('/api/send-email', methods=['POST'])
def send_email():
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import os
    
    try:
        data = request.json
        
        # Email configuration - Use environment variables for security
        SMTP_SERVER = "smtp.gmail.com"  # Change this for other providers
        SMTP_PORT = 587
        EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'your-email@gmail.com')
        EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'your-app-password')
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = data['to_email']
        msg['Subject'] = data['subject']
        
        # Email body
        body = f"""
Project: {data['project_name']}

{data['message']}

---
Sent from Research Dashboard
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_ADDRESS, data['to_email'], text)
        server.quit()
        
        return jsonify({'success': True, 'message': 'Email sent successfully'})
        
    except Exception as e:
        print(f"Email error: {e}")  # For debugging
        return jsonify({'success': False, 'message': str(e)}), 500

# Run Server
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)