from django.db import models

class Banner(models.Model):
    title = models.CharField(max_length=120)
    image_url = models.URLField()
    link_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    def __str__(self):
        return self.title
