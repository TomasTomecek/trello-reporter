# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-07-15 13:22
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Board',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trello_id', models.CharField(max_length=32)),
                ('name', models.CharField(max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Card',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trello_id', models.CharField(max_length=32)),
            ],
        ),
        migrations.CreateModel(
            name='CardAction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trello_id', models.CharField(db_index=True, max_length=32)),
                ('date', models.DateTimeField(db_index=True)),
                ('action_type', models.CharField(max_length=32)),
                ('data', django.contrib.postgres.fields.jsonb.JSONField()),
                ('board', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='card_actions', to='charting.Board')),
                ('card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='actions', to='charting.Card')),
            ],
        ),
    ]
