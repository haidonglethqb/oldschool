from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchasing', '0002_add_defect_fields'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='chitietphieunhapkho',
            name='ct_nhap_kho_nonnegative_amounts',
        ),
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
            name='ct_nhap_kho_nonnegative_amounts',
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
