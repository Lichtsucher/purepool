# Generated by Django 2.0.1 on 2018-02-04 12:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('miner', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Block',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('height', models.IntegerField()),
                ('network', models.CharField(max_length=20)),
                ('pool_block', models.BooleanField(default=False)),
                ('subsidy', models.IntegerField()),
                ('recipient', models.CharField(max_length=100)),
                ('block_version', models.CharField(blank=True, max_length=100)),
                ('block_version2', models.CharField(blank=True, max_length=100)),
                ('processed', models.BooleanField(default=False)),
                ('inserted_at', models.DateTimeField(auto_now_add=True)),
                ('miner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='miner.Miner')),
            ],
        ),
    ]
