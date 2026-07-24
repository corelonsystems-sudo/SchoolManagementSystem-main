# Remove old fields after finance data migration has run
# Note: These fields may have already been removed by a previous version
# of migration 0010. We handle both cases.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0010_create_studyyear_and_migrate_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='academicyear',
            name='year',
        ),
        migrations.RemoveField(
            model_name='enrollment',
            name='academic_year',
        ),
    ]
