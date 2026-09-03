import pytest
from app import create_app, db


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}", "JWT_SECRET_KEY": "test"})
    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
        yield client


def auth(client, name, email):
    response = client.post("/api/auth/signup", json={"name": name, "email": email, "password": "password"})
    return response.get_json()["token"]


def test_users_cannot_access_each_others_projects(client):
    first_token = auth(client, "Ada", "ada@example.com")
    second_token = auth(client, "Lin", "lin@example.com")
    project = client.post("/api/projects", headers={"Authorization": f"Bearer {first_token}"}, json={"name": "Private work"}).get_json()["project"]
    response = client.patch(f"/api/projects/{project['id']}", headers={"Authorization": f"Bearer {second_token}"}, json={"name": "Stolen"})
    assert response.status_code == 404


def test_task_crud_and_pagination(client):
    token = auth(client, "Ada", "ada@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    project = client.post("/api/projects", headers=headers, json={"name": "Launch"}).get_json()["project"]
    task = client.post("/api/tasks", headers=headers, json={"project_id": project["id"], "title": "Write brief"}).get_json()["task"]
    assert client.get("/api/tasks?page=1&per_page=1", headers=headers).get_json()["total"] == 1
    assert client.patch(f"/api/tasks/{task['id']}", headers=headers, json={"completed": True}).get_json()["task"]["completed"] is True
    assert client.delete(f"/api/tasks/{task['id']}", headers=headers).status_code == 204
