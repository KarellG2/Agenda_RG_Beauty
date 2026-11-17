from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('agenda', '0006_personal_password'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE registros_auditoria '
                        'MODIFY id_personal INT NULL'
                    ),
                    reverse_sql=(
                        'ALTER TABLE registros_auditoria '
                        'MODIFY id_personal INT NOT NULL'
                    ),
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='registrosauditoria',
                    name='id_personal',
                    field=models.ForeignKey(
                        blank=True,
                        db_column='id_personal',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='registros_auditoria',
                        to='agenda.personal',
                    ),
                ),
            ],
        ),
    ]
