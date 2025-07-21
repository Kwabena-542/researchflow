import os
from flask import Flask, jsonify, request, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import datetime

app = Flask(__name__)

# Enhanced Database configuration for PostgreSQL/SQLite compatibility
def get_database_url():
    """Get and validate database URL"""
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        print("WARNING: DATABASE_URL not found, using SQLite fallback")
        return 'sqlite:///database.db'
    
    print(f"Original DATABASE_URL: {DATABASE_URL}")
    
    # Handle Render's PostgreSQL URL format with pg8000 driver
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+pg8000://', 1)
    elif DATABASE_URL.startswith('postgresql://'):
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+pg8000://', 1)
    
    print(f"Updated DATABASE_URL: {DATABASE_URL}")
    
    # Additional validation for common URL issues
    if not DATABASE_URL.startswith(('postgresql+pg8000://', 'sqlite://')):
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

# Force database table creation when app starts
def init_db():
    """Initialize database tables"""
    try:
        print("Creating database tables...")
        
        # Check database connection first
        from sqlalchemy import text
        result = db.session.execute(text('SELECT 1')).fetchone()
        print(f"Database connection test: {result}")
        
        # Drop and recreate all tables to ensure clean state
        print("Dropping existing tables...")
        db.drop_all()
        
        print("Creating new tables...")
        db.create_all()
        
        # Verify tables were created
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Available tables after creation: {tables}")
        
        # Verify specific tables exist
        if 'project' in tables and 'collaborator' in tables:
            print("✅ All required tables created successfully!")
        else:
            print("❌ Some tables missing!")
            print(f"Expected: ['project', 'collaborator'], Got: {tables}")
        
        # Test table access
        try:
            projects_count = db.session.execute(text('SELECT COUNT(*) FROM project')).scalar()
            print(f"Project table accessible, count: {projects_count}")
        except Exception as e:
            print(f"Error accessing project table: {e}")
            
        print("Database initialization completed")
        
    except Exception as e:
        print(f"Error creating database tables: {e}")
        import traceback
        traceback.print_exc()
        
        # Try alternative approach
        try:
            print("Attempting alternative table creation...")
            with db.engine.connect() as conn:
                db.metadata.create_all(conn)
            print("Alternative table creation completed")
        except Exception as e2:
            print(f"Alternative approach also failed: {e2}")

# Initialize database tables
with app.app_context():
    init_db()

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
    """Serve the main dashboard interface"""
    return render_template('frontend.html')

@app.route('/api-info')
def api_info():
    """API information endpoint"""
    db_type = 'PostgreSQL' if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite'
    return jsonify({
        'message': 'Research Dashboard API is running!',
        'endpoints': {
            'dashboard': '/',
            'projects': '/api/projects',
            'collaborators': '/api/projects/<id>/collaborators',
            'send_email': '/api/send-email'
        },
        'frontend': 'Dashboard is served at the root URL: /',
        'database': db_type,
        'status': 'healthy'
    })

@app.route('/debug/tables')
def debug_tables():
    """Debug endpoint to check table status"""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        # Get table details
        table_info = {}
        for table_name in tables:
            try:
                columns = inspector.get_columns(table_name)
                table_info[table_name] = [col['name'] for col in columns]
            except Exception as e:
                table_info[table_name] = f"Error: {e}"
        
        # Test queries
        test_results = {}
        try:
            project_count = db.session.execute(text('SELECT COUNT(*) FROM project')).scalar()
            test_results['project_count'] = project_count
        except Exception as e:
            test_results['project_error'] = str(e)
            
        try:
            collab_count = db.session.execute(text('SELECT COUNT(*) FROM collaborator')).scalar()
            test_results['collaborator_count'] = collab_count
        except Exception as e:
            test_results['collaborator_error'] = str(e)
        
        return jsonify({
            'database_url': app.config['SQLALCHEMY_DATABASE_URI'][:50] + "...",
            'available_tables': tables,
            'table_details': table_info,
            'test_results': test_results,
            'models_defined': ['Project', 'Collaborator']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug/create-tables')
def debug_create_tables():
    """Force table creation"""
    try:
        init_db()
        return jsonify({'message': 'Table creation attempted, check logs'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard')
def dashboard_redirect():
    """Redirect /dashboard to root for backward compatibility"""
    return redirect('/')

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
        print(f"Received project data: {data}")  # Debug logging
        
        # Validate required fields
        if not data or not data.get('name'):
            return jsonify({'error': 'Project name is required'}), 400
        
        new_project = Project(
            name=data['name'].strip(),
            stage=data.get('stage', '').strip(),
            abstract=data.get('abstract', '').strip(),
            field=data.get('field', '').strip(),
            priority=data.get('priority', '').strip(),
            deadline=data.get('deadline', '').strip()
        )
        
        print(f"Creating project: {new_project.name}")  # Debug logging
        db.session.add(new_project)
        db.session.commit()
        print("Project created successfully")  # Debug logging
        
        return jsonify({'message': 'Project created successfully'}), 201
    except Exception as e:
        print(f"Error creating project: {e}")
        print(f"Error type: {type(e)}")
        print(f"Request data: {request.get_json()}")  # More debug info
        db.session.rollback()
        return jsonify({'error': f'Failed to create project: {str(e)}'}), 500

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
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
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
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting server on port {port}")
    print(f"Dashboard available at: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)  # Enable debug for local development