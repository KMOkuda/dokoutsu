from django.db import models


class Ping(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
