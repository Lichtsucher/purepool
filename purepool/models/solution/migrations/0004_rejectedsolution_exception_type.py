# Generated by Django 2.0.1 on 2018-04-22 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solution', '0003_auto_20180310_1020'),
    ]

    operations = [
        migrations.AddField(
            model_name='rejectedsolution',
            name='exception_type',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]
