from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
CORS(app, supports_credentials=True)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    stage = db.Column(db.String(100))
    abstract = db.Column(db.Text)

class Collaborator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    project_name = db.Column(db.String(150), nullable=False)

# User Routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'User already exists'}), 400
    hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_user = User(username=data['username'], password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and bcrypt.check_password_hash(user.password_hash, data['password']):
        return jsonify({'message': 'Login successful'}), 200
    return jsonify({'message': 'Invalid username or password'}), 401

@app.route('/api/change-password', methods=['POST'])
def change_password():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and bcrypt.check_password_hash(user.password_hash, data['currentPassword']):
        user.password_hash = bcrypt.generate_password_hash(data['newPassword']).decode('utf-8')
        db.session.commit()
        return jsonify({'message': 'Password changed successfully'})
    return jsonify({'message': 'Incorrect current password'}), 400

# Collaborator Routes
@app.route('/api/collaborators', methods=['POST'])
def add_collaborator():
    data = request.json
    new_collaborator = Collaborator(
        name=data['name'],
        email=data['email'],
        role=data['role'],
        project_name=data['project_name']
    )
    db.session.add(new_collaborator)
    db.session.commit()
    return jsonify({'message': 'Collaborator added successfully'}), 201

@app.route('/api/collaborators', methods=['GET'])
def get_collaborators():
    collaborators = Collaborator.query.all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'email': c.email,
        'role': c.role,
        'project_name': c.project_name
    } for c in collaborators])

# Add project-specific collaborator
@app.route('/api/projects/<int:project_id>/collaborators', methods=['POST'])
def add_project_collaborator(project_id):
    data = request.json
    if not data.get('name') or not data.get('role'):
        return jsonify({'message': 'Name and role are required'}), 400
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404
    new_collab = Collaborator(
        name=data['name'],
        email=data.get('email', ''),
        role=data['role'],
        project_name=project.name
    )
    db.session.add(new_collab)
    db.session.commit()
    return jsonify({'message': 'Collaborator added successfully'}), 201

# Get collaborators for a specific project
@app.route('/api/projects/<int:project_id>/collaborators', methods=['GET'])
def get_project_collaborators(project_id):
    project = Project.query.get(project_id)
    if not project:
        return jsonify([])  # return empty list if project doesn't exist
    collaborators = Collaborator.query.filter_by(project_name=project.name).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'email': c.email,
        'role': c.role
    } for c in collaborators])

# Delete collaborator by ID
@app.route('/api/collaborators/<int:collab_id>', methods=['DELETE'])
def delete_collaborator(collab_id):
    collab = Collaborator.query.get_or_404(collab_id)
    db.session.delete(collab)
    db.session.commit()
    return jsonify({'message': 'Collaborator deleted successfully'})

# Automatically create default user (admin/password123) if not exists
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        hashed_pw = bcrypt.generate_password_hash("password123").decode('utf-8')
        new_user = User(username="admin", password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        print("✅ Default user 'admin' created with password 'password123'")

# Run the server
if __name__ == '__main__':
    app.run(debug=True)