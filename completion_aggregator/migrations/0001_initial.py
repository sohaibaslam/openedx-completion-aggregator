# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-01-17 05:19
from __future__ import unicode_literals

import completion_aggregator.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import opaque_keys.edx.django.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Aggregator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('course_key', opaque_keys.edx.django.models.CourseKeyField(max_length=255)),
                ('aggregation_name', models.CharField(max_length=255)),
                ('block_key', opaque_keys.edx.django.models.UsageKeyField(max_length=255)),
                ('earned', models.FloatField(validators=[completion_aggregator.models.validate_positive_float])),
                ('possible', models.FloatField(validators=[completion_aggregator.models.validate_positive_float])),
                ('percent', models.FloatField(validators=[completion_aggregator.models.validate_percent])),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='aggregator',
            unique_together=set([('course_key', 'block_key', 'user', 'aggregation_name')]),
        ),
        migrations.AlterIndexTogether(
            name='aggregator',
            index_together=set([('course_key', 'aggregation_name', 'block_key', 'percent'), ('user', 'aggregation_name', 'course_key')]),
        ),
    ]
