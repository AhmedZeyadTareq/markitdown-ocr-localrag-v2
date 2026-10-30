# MarkItDown OCR LocalRAG (web app)

The Next.js front end of MarkItDown OCR LocalRAG. It talks to the Python API in `../backend/api.py`.

```bash
npm install
npm run dev        # http://localhost:3000 (start the API first: python -m backend.api from the repo root)
```

The API address defaults to `http://127.0.0.1:8000`; set `NEXT_PUBLIC_API_URL` to change it.

- `components/Workspace.tsx`: app state, uploads, streaming jobs and answers
- `components/Library.tsx`: document list and model status
- `components/DocumentSheet.tsx`: the document page, reading progress, passage highlights
- `components/ChatPanel.tsx`: questions and answers
- `lib/api.ts`: API client, including Server-Sent Events parsing
- `lib/blocks.ts`: splits text into paragraphs and maps answer passages onto them
