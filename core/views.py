import datetime, json
from collections import Counter
from functools import wraps
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
from .models import *
from .services import adaptive, generators, ingest, llm, rag


def api_auth(fn):
    @wraps(fn)
    def inner(request, *a, **kw):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Please sign in."}, status=401)
        return fn(request, *a, **kw)
    return inner


def get_learner(request):
    u = request.user
    return Learner.objects.get_or_create(user=u, defaults={"session_key": f"user-{u.id}", "name": u.first_name or u.username})[0]


def get_course(request):
    """Only a course the signed-in user owns and has chosen. There is no default course."""
    cid = request.session.get("course_id")
    return Course.objects.filter(id=cid, owner=request.user).first() if cid else None


def mastery_map(learner, course):
    out = {}
    for t in course.topics.all():
        m, _ = Mastery.objects.get_or_create(learner=learner, topic=t)
        out[t.id] = m
    return out


@ensure_csrf_cookie
def index(request):
    if not request.user.is_authenticated:
        return redirect("login")
    u = request.user
    return render(request, "app.html", {"llm": llm.available(), "name": u.first_name or u.username, "email": u.email,
                                        "initial": (u.first_name or u.username)[:1].upper()})


@ensure_csrf_cookie
def login_page(request):
    if request.user.is_authenticated:
        return redirect("index")
    return render(request, "login.html")


def _streak(learner):
    days = {timezone.localtime(a).date() for a in learner.attempts.values_list("created", flat=True)}
    d, n = timezone.localdate(), 0
    if d not in days: d -= datetime.timedelta(days=1)
    while d in days: n += 1; d -= datetime.timedelta(days=1)
    return n


@api_auth
@require_GET
def dashboard(request):
    learner, course = get_learner(request), get_course(request)
    if not course:
        return JsonResponse({"empty": True})
    mm = mastery_map(learner, course)
    topics = []
    for t in course.topics.all():
        m = mm[t.id]
        topics.append({"id": t.id, "name": t.name, "p": round(m.p_known, 3), "level": adaptive.level(m.p_known),
                       "attempts": m.attempts, "correct": m.correct, "questions": t.questions.count(),
                       "chunks": t.chunks.count(), "prereqs": [p.id for p in t.prerequisites.all()]})
    atts = list(learner.attempts.select_related("question__topic").order_by("-created"))
    total, right = len(atts), sum(a.correct for a in atts)
    wrong = Counter((a.question.topic.name, a.question.answer, a.given) for a in atts if not a.correct and a.given)
    misconceptions = [{"topic": t, "expected": e, "chose": g, "times": n} for (t, e, g), n in wrong.most_common(4)]
    weak = sorted([t for t in topics if t["attempts"]], key=lambda t: t["p"])[:3]
    recs = []
    untouched = [t for t in topics if t["attempts"] == 0]
    if untouched:
        recs.append({"title": f"Start the diagnostic on {untouched[0]['name']}", "why": "No data yet, so EduAdapt can't tell what you already know.", "action": "quiz"})
    for t in weak:
        if t["p"] < 0.6:
            recs.append({"title": f"Revise {t['name']}", "why": f"Mastery is {round(t['p']*100)}%. Read the notes, then take a short quiz.", "action": "notes", "topic": t["id"]})
    if not recs:
        recs.append({"title": "Ask the tutor a hard question", "why": "Your mastery is strong. Test the edges of the material.", "action": "tutor"})
    return JsonResponse({
        "course": course.name, "learner": learner.name, "topics": topics,
        "overall": round(sum(t["p"] for t in topics) / max(1, len(topics)), 3),
        "accuracy": round(right / total, 3) if total else None, "answered": total, "streak": _streak(learner),
        "docs": course.documents.count(), "chunks": Chunk.objects.filter(document__course=course).count(),
        "questions": Question.objects.filter(topic__course=course).count(),
        "recent": [{"topic": a.question.topic.name, "correct": a.correct, "at": a.created.isoformat()} for a in atts[:8]],
        "misconceptions": misconceptions, "recommendations": recs[:4], "llm": llm.available(),
    })


@api_auth
@require_GET
def library(request):
    course = get_course(request)
    if not course: return JsonResponse({"docs": []})
    return JsonResponse({"docs": [{"id": d.id, "title": d.title, "kind": d.kind, "chunks": d.chunks.count(),
                                   "added": d.created.strftime("%d %b %Y")} for d in course.documents.order_by("-id")]})


@api_auth
@require_POST
def upload(request):
    course = get_course(request)
    if not course: return JsonResponse({"error": "Choose or create a course first, then add material."}, status=400)
    files = request.FILES.getlist("files")
    if not files: return JsonResponse({"error": "Choose at least one file."}, status=400)
    done, errors = [], []
    for f in files:
        try:
            doc, n = ingest.ingest_document(course, f); done.append({"title": doc.title, "chunks": n, "topics": course.topics.count()})
        except Exception as e:
            errors.append({"file": f.name, "error": str(e) or e.__class__.__name__})
    return JsonResponse({"added": done, "errors": errors})


@api_auth
@require_POST
def ask(request):
    q = (json.loads(request.body or "{}").get("question") or "").strip()
    course = get_course(request)
    if not q or not course: return JsonResponse({"error": "Ask a question after adding course material."}, status=400)
    chunks = [{"id": c.id, "text": c.text, "doc": c.document.title, "kind": c.document.kind, "location": c.location,
               "topic": c.topic.name if c.topic else ""} for c in Chunk.objects.filter(document__course=course).select_related("document", "topic")]
    return JsonResponse(rag.answer(q, chunks, llm.chat if llm.available() else None))


def _q_json(q):
    return {"id": q.id, "prompt": q.prompt, "options": q.options, "topic": q.topic.name, "difficulty": q.difficulty}


@api_auth
@require_GET
def quiz_next(request):
    learner, course = get_learner(request), get_course(request)
    if not course: return JsonResponse({"error": "No course yet."}, status=400)
    mm = mastery_map(learner, course)
    mode = request.GET.get("mode", "adaptive")
    topics = list(course.topics.all())
    has_q = {t.id: t.questions.exists() for t in topics}
    if mode == "diagnostic":
        fresh = [t for t in topics if mm[t.id].attempts == 0 and has_q[t.id]]
        if not fresh: return JsonResponse({"done": True, "message": "Diagnostic complete. Your learner profile is ready."})
        tid, p = fresh[0].id, 0.5
    else:
        tid = adaptive.choose_topic({k: m.p_known for k, m in mm.items()}, {t.id: [p.id for p in t.prerequisites.all()] for t in topics}, has_q)
        if tid is None: return JsonResponse({"error": "No questions yet. Upload material first."}, status=400)
        p = mm[tid].p_known
    seen = set(Attempt.objects.filter(learner=learner).order_by("-id").values_list("question_id", flat=True)[:12])
    pool = list(Question.objects.filter(topic_id=tid).values("id", "difficulty"))
    pick = adaptive.choose_question(pool, p, seen)
    q = Question.objects.select_related("topic").get(id=pick["id"])
    return JsonResponse({"question": _q_json(q), "mastery": round(mm[tid].p_known, 3), "mode": mode})


@api_auth
@require_POST
def quiz_answer(request):
    learner = get_learner(request)
    body = json.loads(request.body or "{}")
    q = get_object_or_404(Question.objects.select_related("topic"), id=body.get("question"), topic__course__owner=request.user)
    given = str(body.get("answer", ""))
    ok = given.strip().lower() == q.answer.strip().lower()
    Attempt.objects.create(learner=learner, question=q, given=given, correct=ok)
    m, _ = Mastery.objects.get_or_create(learner=learner, topic=q.topic)
    before = m.p_known
    m.p_known = adaptive.bkt_update(before, ok); m.attempts += 1; m.correct += int(ok); m.save()
    return JsonResponse({"correct": ok, "answer": q.answer, "explanation": q.explanation, "source": q.source,
                         "topic": q.topic.name, "before": round(before, 3), "after": round(m.p_known, 3)})


@api_auth
@require_GET
def topic_ppt(request, tid):
    t = get_object_or_404(Topic, id=tid, course__owner=request.user)
    return FileResponse(generators.build_ppt(t), as_attachment=True, filename=f"{t.name}.pptx")


@api_auth
@require_GET
def topic_notes(request, tid):
    return HttpResponse(generators.notes_html(get_object_or_404(Topic, id=tid, course__owner=request.user)))


@api_auth
@require_POST
def reset_progress(request):
    learner = get_learner(request)
    learner.attempts.all().delete(); learner.mastery.all().delete()
    return JsonResponse({"ok": True})


def _body(request):
    try: return json.loads(request.body or "{}")
    except ValueError: return {}


@api_auth
@require_GET
def courses(request):
    cur = get_course(request)
    return JsonResponse({"current": cur.id if cur else None, "learner": get_learner(request).name,
        "courses": [{"id": c.id, "name": c.name, "docs": c.documents.count(), "topics": c.topics.count()} for c in Course.objects.filter(owner=request.user).order_by("-id")]})


@api_auth
@require_POST
def course_create(request):
    b = _body(request); name = (b.get("name") or "").strip()[:120]
    if not name: return JsonResponse({"error": "Give your course a name."}, status=400)
    c = Course.objects.create(name=name, owner=request.user); request.session["course_id"] = c.id
    return JsonResponse({"id": c.id})


@api_auth
@require_POST
def course_select(request):
    c = get_object_or_404(Course, id=_body(request).get("id"), owner=request.user); request.session["course_id"] = c.id
    return JsonResponse({"ok": True})


@api_auth
@require_POST
def course_delete(request):
    get_object_or_404(Course, id=_body(request).get("id"), owner=request.user).delete(); request.session.pop("course_id", None)
    return JsonResponse({"ok": True})


@api_auth
@require_POST
def paste(request):
    b = _body(request); text = (b.get("text") or "").strip(); title = (b.get("title") or "Pasted notes").strip()[:200]
    if len(text) < 80: return JsonResponse({"error": "Paste at least a few sentences of notes."}, status=400)
    course = get_course(request)
    if not course: return JsonResponse({"error": "Choose or create a course first, then add material."}, status=400)
    from django.core.files.base import ContentFile
    doc, n = ingest.ingest_document(course, ContentFile(text.encode(), name=title + ".txt"))
    return JsonResponse({"title": doc.title, "chunks": n, "topics": course.topics.count()})


def _start_session(request, user):
    login(request, user)
    request.session.pop("course_id", None)  # every sign-in starts at "choose your course"


@require_POST
def auth_register(request):
    b = _body(request)
    name = (b.get("name") or "").strip()[:60]; email = (b.get("email") or "").strip().lower(); pw = b.get("password") or ""
    if not name: return JsonResponse({"error": "Enter your name."}, status=400)
    if "@" not in email or "." not in email.split("@")[-1]: return JsonResponse({"error": "Enter a valid email address."}, status=400)
    if len(pw) < 6: return JsonResponse({"error": "Use a password with at least 6 characters."}, status=400)
    if User.objects.filter(username=email).exists(): return JsonResponse({"error": "An account with this email already exists. Sign in instead."}, status=400)
    _start_session(request, User.objects.create_user(username=email, email=email, password=pw, first_name=name))
    return JsonResponse({"ok": True})


@require_POST
def auth_login(request):
    b = _body(request)
    u = authenticate(request, username=(b.get("email") or "").strip().lower(), password=b.get("password") or "")
    if not u: return JsonResponse({"error": "Email or password is incorrect."}, status=400)
    _start_session(request, u)
    return JsonResponse({"ok": True})


@require_POST
def auth_demo(request):
    u, made = User.objects.get_or_create(username="demo@eduadapt.ai", defaults={"first_name": "Demo Student", "email": "demo@eduadapt.ai"})
    if made: u.set_unusable_password(); u.save()
    _start_session(request, u)
    return JsonResponse({"ok": True})


@require_POST
def auth_logout(request):
    logout(request)
    return JsonResponse({"ok": True})
