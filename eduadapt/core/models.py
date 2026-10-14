from django.contrib.auth.models import User
from django.db import models


class Learner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name="learner")
    session_key = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=80, default="Learner")
    created = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name


class Course(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="courses")
    name = models.CharField(max_length=200)
    created = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name


class Topic(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="topics")
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    prerequisites = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="unlocks")
    class Meta: ordering = ["order", "id"]
    def __str__(self): return self.name


class Document(models.Model):
    KINDS = [("pdf", "PDF"), ("pptx", "Slides"), ("docx", "Word"), ("video", "Video transcript"), ("text", "Notes"), ("image", "Image")]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=250)
    kind = models.CharField(max_length=10, choices=KINDS)
    file = models.FileField(upload_to="uploads/", blank=True)
    created = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title


class Chunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name="chunks")
    text = models.TextField()
    location = models.CharField(max_length=60)  # "Page 4", "Slide 7", "12:30"
    def __str__(self): return f"{self.document.title} · {self.location}"


class Question(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="questions")
    kind = models.CharField(max_length=10, default="mcq")  # mcq | short | numeric
    prompt = models.TextField()
    options = models.JSONField(default=list, blank=True)
    answer = models.CharField(max_length=300)
    explanation = models.TextField(blank=True)
    difficulty = models.PositiveSmallIntegerField(default=2)  # 1 easy .. 3 hard
    source = models.CharField(max_length=300, blank=True)
    fingerprint = models.CharField(max_length=64, db_index=True)


class Attempt(models.Model):
    learner = models.ForeignKey(Learner, on_delete=models.CASCADE, related_name="attempts")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    given = models.CharField(max_length=300, blank=True)
    correct = models.BooleanField()
    created = models.DateTimeField(auto_now_add=True)


class Mastery(models.Model):
    learner = models.ForeignKey(Learner, on_delete=models.CASCADE, related_name="mastery")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    p_known = models.FloatField(default=0.2)
    attempts = models.PositiveIntegerField(default=0)
    correct = models.PositiveIntegerField(default=0)
    class Meta: unique_together = ("learner", "topic")
