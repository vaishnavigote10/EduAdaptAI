# EduAdapt AI

Built by Vaishnavi, Zainab and Mrunal.

A source-grounded AI tutor with adaptive practice and a learner model. Upload course material, ask questions and get cited answers, take adaptive quizzes, and watch a mastery profile update after every answer.

## Run it (about 2 minutes)

**Windows:** double-click `run.bat`, or run it in a terminal.
**Mac/Linux:** `./run.sh`

Then open http://127.0.0.1:8000. Register, sign in, or use **Continue as Demo Student**. After signing in, name the course you want to learn and add your own material. Create your own course (or pick one you made earlier), then add your files in the Library. A sample machine-learning course is available as an optional button. `sample_materials/lecture_transcript.txt` is a small file to test with.

Manual steps: `pip install -r requirements.txt`, then `python manage.py makemigrations core`, `python manage.py migrate`, `python manage.py runserver`.

## What is built

| Area | Where | How it works |
|---|---|---|
| Multimodal ingestion | `core/services/ingest.py` | PDF pages (pypdf), Word .docx, slides plus speaker notes (python-pptx), timestamped transcripts (.vtt/.srt/`[mm:ss]` text). Each chunk keeps its page, slide or timestamp. Audio/video uses `openai-whisper` and images use `pytesseract` if you install them. |
| Knowledge base | `ingest.organise_topics` | TF-IDF + KMeans groups chunks into topics, new chunks join the nearest topic, topics are chained as prerequisites. |
| Source-grounded tutor | `core/services/rag.py` | TF-IDF vector retrieval, a support threshold, then cited answers. Weak matches are flagged as "not in your course material" instead of guessed. |
| Assessment | `core/services/questions.py` | Cloze MCQs tagged with topic, difficulty and source location. Each is validated and checked for near-duplicates before saving. |
| Learner model | `core/services/adaptive.py` | Bayesian Knowledge Tracing per topic. The next question comes from the weakest topic (prerequisites first) at a difficulty matched to mastery. |
| Diagnostic | `/api/quiz/next?mode=diagnostic` | One question per topic for new learners. |
| Study Studio | `core/services/generators.py` | Per-topic PPTX download and handwritten-style notes page, built from your sources. |
| Dashboard | `templates/app.html`, `static/` | Mastery ring, knowledge map, misconception detection, recommendations, activity. |

## Optional LLM

Copy `.env.example` to `.env` and set `LLM_API_KEY` (any OpenAI-compatible endpoint). Tutor answers and notes summaries then use the LLM, still restricted to retrieved sources. Without a key everything works in extractive mode.

## Honest limits (good to mention in your demo)

- Retrieval is TF-IDF, not neural embeddings. `rag.retrieve` is the single function to swap for a vector DB (FAISS, pgvector).
- Questions are fill-in-the-gap MCQs. Short-answer and numerical types exist in the model, but only MCQ generation is implemented.
- Accounts use Django's built-in auth (email + password). The Demo Student account is shared by everyone who uses it.
- Diagrams and figures are not interpreted yet.

## Structure

```
eduadapt/        settings, urls
core/            models, views, urls, admin
core/services/   ingest, rag, questions, adaptive, generators, llm
core/management/commands/seed_demo.py
templates/       base.html, app.html
static/          css/app.css, js/app.js
sample_materials/
```

## Optional sample data

Nothing is pre-loaded. To give the demo account a sample machine-learning course for presentations, run `python manage.py seed_demo`.

## Upgrading from an older zip

Delete `db.sqlite3` (the data model changed to add accounts and course owners), then run `run.bat` again.

## Deploy on Render

1. `python manage.py makemigrations core` locally, then commit `core/migrations/0001_initial.py`.
2. Push the project to GitHub (the `db.sqlite3`, `media/` and `.env` files are git-ignored).
3. In Render choose **New > Blueprint**, pick the repo, and apply. `render.yaml` creates the web service and a Postgres database.
4. Optional: add `LLM_API_KEY` in the service's Environment tab.

Free web services sleep after 15 minutes idle and take about a minute to wake. Free Postgres expires 30 days after creation, so upgrade the database or export your data before then.

## Contributors

- Vaishnavi
- Zainab
- Mrunal

To change names or roles shown in the app, edit `TEAM` at the bottom of `eduadapt/settings.py`.
