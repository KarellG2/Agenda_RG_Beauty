from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('agenda', '0007_registrosauditoria_personal_nullable'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='personal',
            name='password',
        ),
    ]
