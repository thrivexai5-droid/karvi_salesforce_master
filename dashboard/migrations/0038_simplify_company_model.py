# Generated migration for simplified Company model
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0037_userprofile_phone_number'),
    ]

    operations = [
        # Step 1: Remove the old unique constraint first
        migrations.AlterUniqueTogether(
            name='company',
            unique_together=set(),
        ),
        
        # Step 2: Add new simplified fields
        migrations.AddField(
            model_name='company',
            name='city',
            field=models.CharField(max_length=100, verbose_name='City', default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='company',
            name='address',
            field=models.TextField(verbose_name='Company Address', default=''),
            preserve_default=False,
        ),
        
        # Step 3: Copy data from old fields to new fields
        migrations.RunSQL(
            "UPDATE dashboard_company SET city = city_1 WHERE city_1 IS NOT NULL;",
            reverse_sql="UPDATE dashboard_company SET city_1 = city WHERE city IS NOT NULL;"
        ),
        migrations.RunSQL(
            "UPDATE dashboard_company SET address = COALESCE(address_1, address_2, address_3, '') WHERE address_1 IS NOT NULL OR address_2 IS NOT NULL OR address_3 IS NOT NULL;",
            reverse_sql="UPDATE dashboard_company SET address_1 = address WHERE address IS NOT NULL;"
        ),
        
        # Step 4: Remove old fields
        migrations.RemoveField(
            model_name='company',
            name='city_1',
        ),
        migrations.RemoveField(
            model_name='company',
            name='city_2',
        ),
        migrations.RemoveField(
            model_name='company',
            name='address_1',
        ),
        migrations.RemoveField(
            model_name='company',
            name='address_2',
        ),
        migrations.RemoveField(
            model_name='company',
            name='address_3',
        ),
        
        # Step 5: Add new unique constraint
        migrations.AlterUniqueTogether(
            name='company',
            unique_together={('company_name', 'city')},
        ),
    ]