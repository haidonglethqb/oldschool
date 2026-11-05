from decimal import Decimal
from django.db import migrations, models


def clean_existing_discounts(apps, schema_editor):
    ChiTietPhieuNhapKho = apps.get_model('purchasing', 'ChiTietPhieuNhapKho')
    for item in ChiTietPhieuNhapKho.objects.all():
        if item.chiet_khau is not None and item.chiet_khau > 100:
            if item.chiet_khau == Decimal("100000"):
                item.chiet_khau = Decimal("10")
            else:
                gross = Decimal(item.so_luong or 0) * (item.don_gia or Decimal("0"))
                if gross > 0:
                    pct = (item.chiet_khau / gross) * Decimal("100")
                    item.chiet_khau = min(Decimal("100"), round(pct, 2))
                else:
                    item.chiet_khau = Decimal("0")
            gross = Decimal(item.so_luong or 0) * (item.don_gia or Decimal("0"))
            discount_amount = (gross * item.chiet_khau / Decimal("100")).quantize(Decimal("1"))
            item.thanh_tien = gross - discount_amount
            item.save()

    PhieuNhapKho = apps.get_model('purchasing', 'PhieuNhapKho')
    for pnk in PhieuNhapKho.objects.all():
        total = sum(line.thanh_tien for line in pnk.lines.all())
        if pnk.tong_tien != total:
            pnk.tong_tien = total
            pnk.save()


class Migration(migrations.Migration):

    dependencies = [
        ('purchasing', '0002_add_defect_fields'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='chitietphieunhapkho',
            name='ct_nhap_kho_nonnegative_amounts',
        ),
        migrations.RunPython(clean_existing_discounts, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='chitietphieunhapkho',
            name='chiet_khau',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                max_digits=5,
                verbose_name='Chiết khấu (%)',
            ),
        ),
        migrations.AddConstraint(
            model_name='chitietphieunhapkho',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ('don_gia__gte', 0),
                    ('chiet_khau__gte', 0),
                    ('chiet_khau__lte', 100),
                    ('thanh_tien__gte', 0),
                ),
                name='ct_nhap_kho_nonnegative_amounts',
            ),
        ),
    ]
