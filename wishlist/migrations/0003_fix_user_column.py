from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wishlist', '0002_fix_user_field'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL: No changes needed as the column already exists
            sql='',
            # Reverse SQL: No changes needed
            reverse_sql='',
            # Tell Django this is a no-op migration
            state_operations=[
                migrations.AlterField(
                    model_name='wishlist',
                    name='user',
                    field=models.ForeignKey(
                        db_column='userId_id',
                        on_delete=django.db.models.deletion.CASCADE,
                        to='auth.user'
                    ),
                ),
            ]
        ),
    ] 