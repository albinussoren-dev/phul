# Phul V3

Phul is a mobile-first multi-model AI PWA using FastAPI on Vercel and the Hugging Face Router.

## V3 features
- Multi-model discovery from Hugging Face Router `/v1/models`
- Kimi-K3 default model
- Streaming chat responses
- Deep Think mode (instruction-level reasoning mode; model-dependent)
- Image upload as a data URL for vision-capable models
- Text/code file attachments
- Markdown rendering
- Code blocks with copy
- Copy + regenerate
- Local chat history and chat search
- Dark/light mode
- Android PWA install prompt
- Mobile responsive ChatGPT-style UI

## Deploy
1. Upload `main.py`, `requirements.txt`, and `README.md` to GitHub.
2. Import the repository into Vercel.
3. Add `HF_TOKEN` as a Vercel environment variable for Production.
4. Redeploy.

Do not put the HF token in frontend code or GitHub.

Hugging Face Inference Providers support OpenAI-compatible chat completions, streaming, model listing, provider selection, and VLM chat for supported models.
