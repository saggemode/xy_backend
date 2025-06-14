from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wishlist', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL: No changes needed as the column already exists
            sql='',
            # Reverse SQL: No changes needed
            reverse_sql='',
        ),
        migrations.AlterModelOptions(
            name='wishlist',
            options={
                'verbose_name': 'Wishlist',
                'verbose_name_plural': 'Wishlists',
                'unique_together': {('user', 'product')},
            },
        ),
    ] 