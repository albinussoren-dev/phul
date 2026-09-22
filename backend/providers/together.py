from backend.providers.huggingface import client
def chat(**kwargs): return client().chat.completions.create(**kwargs)