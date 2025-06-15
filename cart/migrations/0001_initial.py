from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('product', '0001_initial'),
        ('store', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(db_column='productId_id', on_delete=django.db.models.deletion.CASCADE, to='product.product')),
                ('store', models.ForeignKey(db_column='storeId_id', on_delete=django.db.models.deletion.CASCADE, to='store.store')),
                ('user', models.ForeignKey(db_column='userId_id', on_delete=django.db.models.deletion.CASCADE, to='auth.user')),
            ],
            options={
                'verbose_name': 'Cart',
                'verbose_name_plural': 'Carts',
                'db_table': 'cart_cart',
                'managed': True,
                'unique_together': {('user', 'store', 'product')},
            },
        ),
    ] 