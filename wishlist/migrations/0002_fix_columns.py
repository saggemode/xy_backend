from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wishlist', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL: Rename the column if it exists
            sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'wishlist_wishlist' 
                    AND column_name = 'product_id'
                ) THEN
                    ALTER TABLE wishlist_wishlist RENAME COLUMN product_id TO "productId_id";
                END IF;
            END $$;
            """,
            # Reverse SQL: Rename back if needed
            reverse_sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'wishlist_wishlist' 
                    AND column_name = 'productId_id'
                ) THEN
                    ALTER TABLE wishlist_wishlist RENAME COLUMN "productId_id" TO product_id;
                END IF;
            END $$;
            """
        ),
    ] 