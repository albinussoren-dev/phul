import json
def test_model_config():
 data=json.load(open("models/models.json"));assert data["models"][0]["name"]=="Kimi-K3"