def test_app_import():
 from backend.main import app
 assert app.title.startswith("Phul")