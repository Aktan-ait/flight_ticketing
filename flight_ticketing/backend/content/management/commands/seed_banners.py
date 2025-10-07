from django.core.management.base import BaseCommand
from content.models import Banner

DEMO = [
    dict(
        title="🔥 Summer Sale −30%",
        image_url="https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?q=80&w=1200&auto=format",
        link_url="/flights",
        is_active=True,
        sort_order=1,
    ),
    dict(
        title="🛰️ New routes to Almaty",
        image_url="https://images.unsplash.com/photo-1518306727298-4c228dd06e51?q=80&w=1200&auto=format",
        link_url="/flights?destination=Almaty",
        is_active=True,
        sort_order=2,
    ),
]

class Command(BaseCommand):
    help = "Create demo banners"

    def handle(self, *args, **kwargs):
        created = 0
        for b in DEMO:
            obj, ok = Banner.objects.get_or_create(
                title=b["title"], defaults=b
            )
            if ok:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Banners created: {created}"))
