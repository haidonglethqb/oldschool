"""
Management command `seed_oldschool_3b`.
Tương đương `python manage.py seed_oldschool --branches 3`.
Khởi tạo dữ liệu mẫu bản mở rộng 3 cơ sở (CS1 Kho tổng, CS2 Thanh Khê, CS3 Ngũ Hành Sơn) và 7 tài khoản.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Khởi tạo dữ liệu mẫu Old School mở rộng với 3 cơ sở (CS1, CS2, CS3) và 7 tài khoản."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.MIGRATE_HEADING("=== Chạy lệnh khởi tạo dữ liệu mẫu 3 cơ sở (seed_oldschool_3b) ===")
        )
        call_command("seed_oldschool", branches=3)
