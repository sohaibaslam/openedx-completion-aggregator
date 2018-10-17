# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-10-17 21:49
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('completion_aggregator', '0003_stalecompletion'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='stalecompletion',
            index_together=set([('username', 'course_key', 'created', 'resolved')]),
        ),
    ]