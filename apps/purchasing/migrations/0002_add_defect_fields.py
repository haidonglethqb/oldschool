import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchasing', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='phieunhapkho',
            name='trang_thai',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Bản nháp'),
                    ('PENDING_APPROVAL', 'Chờ duyệt'),
                    ('RETURNED', 'Trả lại chỉnh sửa'),
                    ('APPROVED', 'Đã duyệt'),
                    ('RETURN_PROPOSED', 'Chờ chủ duyệt trả NCC (Hàng lỗi)'),
                    ('RETURNED_TO_SUPPLIER', 'Đã trả hàng cho NCC'),
                ],
                db_index=True,
                default='PENDING_APPROVAL',
                max_length=25,
                verbose_name='Trạng thái',
            ),
        ),
        migrations.AddField(
            model_name='phieunhapkho',
            name='ly_do_loi_ncc',
            field=models.TextField(blank=True, default='', verbose_name='Lý do hàng lỗi / không đạt yêu cầu'),
        ),
        migrations.AddField(
            model_name='phieunhapkho',
            name='nguoi_bao_loi',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='phieu_nhap_bao_loi',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Người báo hàng lỗi',
            ),
        ),
        migrations.AddField(
            model_name='phieunhapkho',
            name='thoi_gian_bao_loi',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Thời gian báo lỗi'),
        ),
    ]
