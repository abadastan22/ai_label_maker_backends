from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("labels", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE labels_label DROP COLUMN IF EXISTS batch_text;
            ALTER TABLE labels_label DROP COLUMN IF EXISTS prepared_text;
            """,
            reverse_sql="""
            ALTER TABLE labels_label ADD COLUMN IF NOT EXISTS batch_text VARCHAR(255) DEFAULT '';
            ALTER TABLE labels_label ADD COLUMN IF NOT EXISTS prepared_text VARCHAR(255) DEFAULT '';
            """,
        ),
    ]