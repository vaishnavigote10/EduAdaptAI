from django.contrib import admin
from .models import *
for m in (Learner, Course, Topic, Document, Chunk, Question, Attempt, Mastery):
    admin.site.register(m)
