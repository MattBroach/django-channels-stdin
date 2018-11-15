from django.db import models
from django.utils import timezone


class Thought(models.Model):
    content = models.CharField(max_length=140)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.content
