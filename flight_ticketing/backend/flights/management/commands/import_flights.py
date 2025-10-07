import csv
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from flights.models import Flight
from companies.models import Company

# Ожидаемый CSV (заголовки):
# flight_number,origin,destination,departure_time,arrival_time,price,total_seats,available_seats,company_id|company_name
# Пример даты: 2025-10-10 09:00

def parse_dt(s):
    # поддержка "YYYY-MM-DD HH:MM" и ISO "YYYY-MM-DDTHH:MM"
    s = s.strip().replace("T", " ")
    return datetime.strptime(s, "%Y-%m-%d %H:%M")

class Command(BaseCommand):
    help = "Импорт рейсов из CSV"

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Путь к CSV")
        parser.add_argument("--company", help="ID или имя компании (если нет столбца company_*)", default=None)
        parser.add_argument("--dry", action="store_true", help="Только проверить, без сохранения")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["file"]
        default_company = opts["company"]
        dry = opts["dry"]

        if default_company:
            company = Company.objects.filter(id=default_company).first() or Company.objects.filter(name=default_company).first()
            if not company:
                raise CommandError(f"Компания '{default_company}' не найдена")
        else:
            company = None

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                c = company
                # company в CSV имеет приоритет
                cid = (row.get("company_id") or "").strip()
                cname = (row.get("company_name") or "").strip()

                if cid or cname:
                    c = None
                    if cid.isdigit():
                        c = Company.objects.filter(id=int(cid)).first()
                    elif cname:
                        c = Company.objects.filter(name=cname).first()
                    if not c:
                        raise CommandError(f"Компания по CSV не найдена: id={cid} name={cname}")

                flight = Flight(
                    company=c,
                    flight_number=row["flight_number"].strip(),
                    origin=row["origin"].strip(),
                    destination=row["destination"].strip(),
                    departure_time=parse_dt(row["departure_time"]),
                    arrival_time=parse_dt(row["arrival_time"]),
                    price=Decimal(str(row["price"]).strip()),
                    total_seats=int(row["total_seats"]),
                    available_seats=int(row.get("available_seats") or row["total_seats"]),
                )

                # Валидация (кинет исключение, если что-то не так)
                flight.full_clean()

                if not dry:
                    flight.save()
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Импортировано рейсов: {count} (dry={dry})"))
