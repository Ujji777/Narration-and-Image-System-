from django.db import models

class PoemProject(models.Model):
    text = models.TextField()
    mood = models.CharField(max_length=50)
    voice_tld = models.CharField(max_length=20)
    poster = models.ImageField(upload_to="posters/")
    narration = models.FileField(upload_to="audio/")
    final_audio = models.FileField(upload_to="audio/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mood} @ {self.created_at:%Y-%m-%d %H:%M}"
