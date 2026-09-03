import os
from datetime import timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    projects = db.relationship("Project", backref="owner", cascade="all, delete-orphan")


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    color = db.Column(db.String(20), nullable=False, default="#e66b4d")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    tasks = db.relationship("Task", backref="project", cascade="all, delete-orphan")


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text, default="")
    priority = db.Column(db.String(20), nullable=False, default="medium")
    completed = db.Column(db.Boolean, nullable=False, default=False)
    due_date = db.Column(db.String(20), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False, index=True)


def serialize_project(project):
    return {"id": project.id, "name": project.name, "color": project.color,
            "task_count": len(project.tasks), "completed_count": sum(t.completed for t in project.tasks)}


def serialize_task(task):
    return {"id": task.id, "title": task.title, "notes": task.notes or "", "priority": task.priority,
            "completed": task.completed, "due_date": task.due_date, "project_id": task.project_id,
            "project_name": task.project.name if task.project else ""}


def current_user():
    return db.session.get(User, int(get_jwt_identity()))


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///focusflow.db").replace("postgres://", "postgresql://", 1),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "development-secret-change-me"),
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=24),
    )
    if test_config:
        app.config.update(test_config)
    CORS(app)
    db.init_app(app)
    JWTManager(app)
    with app.app_context():
        db.create_all()

    @app.post("/api/auth/signup")
    def signup():
        body = request.get_json() or {}
        name, email, password = body.get("name", "").strip(), body.get("email", "").lower().strip(), body.get("password", "")
        if not name or not email or len(password) < 6:
            return jsonify(error="Name, email, and a password of at least 6 characters are required"), 400
        if User.query.filter_by(email=email).first():
            return jsonify(error="An account with that email already exists"), 409
        user = User(name=name, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return jsonify(user={"id": user.id, "name": user.name, "email": user.email}, token=create_access_token(identity=str(user.id))), 201

    @app.post("/api/auth/login")
    def login():
        body = request.get_json() or {}
        user = User.query.filter_by(email=body.get("email", "").lower().strip()).first()
        if not user or not check_password_hash(user.password_hash, body.get("password", "")):
            return jsonify(error="Invalid email or password"), 401
        return jsonify(user={"id": user.id, "name": user.name, "email": user.email}, token=create_access_token(identity=str(user.id)))

    @app.get("/api/auth/me")
    @jwt_required()
    def me():
        user = current_user()
        return jsonify(user={"id": user.id, "name": user.name, "email": user.email})

    @app.get("/api/projects")
    @jwt_required()
    def list_projects():
        projects = Project.query.filter_by(user_id=int(get_jwt_identity())).order_by(Project.id).all()
        return jsonify(projects=[serialize_project(project) for project in projects])

    @app.post("/api/projects")
    @jwt_required()
    def create_project():
        body = request.get_json() or {}
        name = body.get("name", "").strip()
        if not name:
            return jsonify(error="Project name is required"), 400
        project = Project(name=name, color=body.get("color", "#e66b4d"), user_id=int(get_jwt_identity()))
        db.session.add(project)
        db.session.commit()
        return jsonify(project=serialize_project(project)), 201

    @app.patch("/api/projects/<int:project_id>")
    @jwt_required()
    def update_project(project_id):
        project = Project.query.filter_by(id=project_id, user_id=int(get_jwt_identity())).first_or_404()
        body = request.get_json() or {}
        project.name = body.get("name", project.name).strip()
        project.color = body.get("color", project.color)
        db.session.commit()
        return jsonify(project=serialize_project(project))

    @app.delete("/api/projects/<int:project_id>")
    @jwt_required()
    def delete_project(project_id):
        project = Project.query.filter_by(id=project_id, user_id=int(get_jwt_identity())).first_or_404()
        db.session.delete(project)
        db.session.commit()
        return "", 204

    @app.get("/api/tasks")
    @jwt_required()
    def list_tasks():
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = min(max(request.args.get("per_page", 8, type=int), 1), 50)
        query = Task.query.join(Project).filter(Project.user_id == int(get_jwt_identity()))
        project_id = request.args.get("project_id", type=int)
        if project_id:
            query = query.filter(Task.project_id == project_id)
        pagination = query.order_by(Task.completed.asc(), Task.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
        return jsonify(tasks=[serialize_task(task) for task in pagination.items], page=page, per_page=per_page, pages=pagination.pages, total=pagination.total)

    @app.post("/api/tasks")
    @jwt_required()
    def create_task():
        body = request.get_json() or {}
        project = Project.query.filter_by(id=body.get("project_id"), user_id=int(get_jwt_identity())).first()
        if not project or not body.get("title", "").strip():
            return jsonify(error="A valid project and task title are required"), 400
        task = Task(title=body["title"].strip(), notes=body.get("notes", ""), priority=body.get("priority", "medium"), due_date=body.get("due_date"), project_id=project.id)
        db.session.add(task)
        db.session.commit()
        return jsonify(task=serialize_task(task)), 201

    @app.patch("/api/tasks/<int:task_id>")
    @jwt_required()
    def update_task(task_id):
        task = Task.query.join(Project).filter(Task.id == task_id, Project.user_id == int(get_jwt_identity())).first_or_404()
        body = request.get_json() or {}
        for field in ("title", "notes", "priority", "due_date", "completed"):
            if field in body:
                setattr(task, field, body[field])
        db.session.commit()
        return jsonify(task=serialize_task(task))

    @app.delete("/api/tasks/<int:task_id>")
    @jwt_required()
    def delete_task(task_id):
        task = Task.query.join(Project).filter(Task.id == task_id, Project.user_id == int(get_jwt_identity())).first_or_404()
        db.session.delete(task)
        db.session.commit()
        return "", 204

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
