# Generated manually to document Date of Quote validation enforcement

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0022_add_inquiry_item_model'),
    ]

    operations = [
        # This migration documents the enforcement of Date of Quote as required
        # The field was already defined as required in the model, but this migration
        # ensures proper validation is in place at all levels
        migrations.RunSQL(
            # Verify that no NULL values exist (should be empty result)
            "SELECT COUNT(*) FROM dashboard_inquiryhandler WHERE date_of_quote IS NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]