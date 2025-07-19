import os
from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import datetime
import re

app = Flask(__name__)

# Enhanced Database configuration for PostgreSQL/SQLite compatibility
def get_database_url():
    """Get and validate database URL"""
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        print("WARNING: DATABASE_URL not found, using SQLite fallback")
        return 'sqlite:///database.db'
    
    print(f"Original DATABASE_URL: {DATABASE_URL}")
    
    # Handle Render's PostgreSQL URL format
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        print(f"Updated DATABASE_URL: {DATABASE_URL}")
    
    # Additional validation for common URL issues
    if not DATABASE_URL.startswith(('postgresql://', 'sqlite://')):
        print(f"WARNING: Unrecognized database URL format: {DATABASE_URL}")
        print("Falling back to SQLite")
        return 'sqlite:///database.db'
    
    return DATABASE_URL

# Set database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Initialize extensions
db = SQLAlchemy(app)
CORS(app)

# Data Models
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    field = db.Column(db.String(100))
    stage = db.Column(db.String(50))
    abstract = db.Column(db.Text)
    priority = db.Column(db.String(10))  # "High", "Medium", "Low"
    deadline = db.Column(db.String(10))  # Format: "YYYY-MM-DD"
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Collaborator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    role = db.Column(db.String(100))

# Routes
@app.route('/')
def index():
    db_type = 'PostgreSQL' if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite'
    return jsonify({
        'message': 'Research Dashboard API is running!',
        'endpoints': {
            'projects': '/api/projects',
            'collaborators': '/api/projects/<id>/collaborators',
            'send_email': '/api/send-email'
        },
        'frontend': 'Upload and open frontend.html in your browser',
        'database': db_type,
        'status': 'healthy'
    })

@app.route('/api/projects', methods=['GET'])
def get_projects():
    try:
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
    except Exception as e:
        print(f"Error fetching projects: {e}")
        return jsonify({'error': 'Failed to fetch projects'}), 500

@app.route('/api/projects', methods=['POST'])
def create_project():
    try:
        data = request.json
        new_project = Project(
            name=data['name'],
            stage=data.get('stage', ''),
            abstract=data.get('abstract', ''),
            field=data.get('field', ''),
            priority=data.get('priority', ''),
            deadline=data.get('deadline', '')
        )
        db.session.add(new_project)
        db.session.commit()
        return jsonify({'message': 'Project created successfully'}), 201
    except Exception as e:
        print(f"Error creating project: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create project'}), 500

@app.route('/api/projects/<int:id>', methods=['PUT'])
def update_project(id):
    try:
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
    except Exception as e:
        print(f"Error updating project: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update project'}), 500

@app.route('/api/projects/<int:id>', methods=['DELETE'])
def delete_project(id):
    try:
        project = Project.query.get_or_404(id)
        db.session.delete(project)
        db.session.commit()
        return jsonify({'message': 'Project deleted successfully'})
    except Exception as e:
        print(f"Error deleting project: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete project'}), 500

@app.route('/api/projects/<int:project_id>/collaborators', methods=['POST'])
def add_collaborator(project_id):
    try:
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
    except Exception as e:
        print(f"Error adding collaborator: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add collaborator'}), 500

@app.route('/api/projects/<int:project_id>/collaborators', methods=['GET'])
def get_collaborators(project_id):
    try:
        collaborators = Collaborator.query.filter_by(project_id=project_id).all()
        return jsonify([{
            'id': c.id,
            'name': c.name,
            'email': c.email,
            'role': c.role
        } for c in collaborators])
    except Exception as e:
        print(f"Error fetching collaborators: {e}")
        return jsonify({'error': 'Failed to fetch collaborators'}), 500

@app.route('/api/collaborators/<int:collab_id>', methods=['DELETE'])
def delete_collaborator(collab_id):
    try:
        collaborator = Collaborator.query.get_or_404(collab_id)
        db.session.delete(collaborator)
        db.session.commit()
        return jsonify({'message': 'Collaborator deleted successfully'})
    except Exception as e:
        print(f"Error deleting collaborator: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete collaborator'}), 500

# EMAIL ENDPOINT
@app.route('/api/send-email', methods=['POST'])
def send_email():
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        data = request.json
        
        # Email configuration - Use environment variables for security
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587
        EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
        EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
        
        if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
            return jsonify({
                'success': False, 
                'message': 'Email configuration not found. Please set EMAIL_ADDRESS and EMAIL_PASSWORD environment variables.'
            }), 500
        
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
University of Nebraska-Lincoln
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
        print(f"Email error: {e}")
        return jsonify({'success': False, 'message': f'Email error: {str(e)}'}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        db_status = 'healthy'
        db_type = 'PostgreSQL' if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite'
    except Exception as e:
        print(f"Database health check failed: {e}")
        db_status = 'unhealthy'
        db_type = 'unknown'
    
    return jsonify({
        'status': 'healthy' if db_status == 'healthy' else 'degraded',
        'database_status': db_status,
        'database_type': db_type,
        'timestamp': datetime.datetime.utcnow().isoformat()
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# Run Server
if __name__ == '__main__':
    try:
        with app.app_context():
            print("Creating database tables...")
            db.create_all()
            print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")
    
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)  # Set debug=False for production