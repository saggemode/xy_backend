from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wishlist', '0003_fix_user_column'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL: No changes needed as the columns already exist
            sql='',
            # Reverse SQL: No changes needed
            reverse_sql='',
            # Tell Django this is a no-op migration
            state_operations=[
                migrations.AlterModelOptions(
                    name='wishlist',
                    options={
                        'verbose_name': 'Wishlist',
                        'verbose_name_plural': 'Wishlists',
                        'unique_together': {('user', 'product')},
                    },
                ),
                migrations.AlterField(
                    model_name='wishlist',
                    name='product',
                    field=models.ForeignKey(
                        db_column='productId_id',
                        on_delete=django.db.models.deletion.CASCADE,
                        to='product.product'
                    ),
                ),
                migrations.AlterModelTable(
                    name='wishlist',
                    table='wishlist_wishlist',
                ),
            ]
        ),
    ] 