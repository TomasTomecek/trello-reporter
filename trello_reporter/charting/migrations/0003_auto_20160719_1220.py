# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-07-19 12:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('charting', '0002_auto_20160719_0932'),
    ]

    operations = [
        migrations.CreateModel(
            name='List',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trello_id', models.CharField(db_index=True, max_length=32)),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='cardstate',
            name='list_name',
        ),
        migrations.AddField(
            model_name='cardaction',
            name='list',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='card_actions', to='charting.List'),
        ),
    ]
