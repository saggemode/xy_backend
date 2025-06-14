from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('wishlist', '0001_initial'),
    ]

    operations = [
        # Drop the existing table
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS wishlist_wishlist;",
            reverse_sql=""  # No reverse SQL needed as we'll recreate the table
        ),
        # Create the table with Django's default naming
        migrations.CreateModel(
            name='Wishlist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product.product')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.user')),
            ],
            options={
                'verbose_name': 'Wishlist',
                'verbose_name_plural': 'Wishlists',
                'db_table': 'wishlist_wishlist',
                'managed': True,
                'unique_together': {('user', 'product')},
            },
        ),
    ] 