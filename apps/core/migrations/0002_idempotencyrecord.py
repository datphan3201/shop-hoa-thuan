from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="IdempotencyRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("operation", models.CharField(max_length=64)),
                ("key", models.CharField(max_length=128)),
                ("fingerprint", models.CharField(max_length=64)),
                ("response_location", models.CharField(blank=True, max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                # This was an account foreign key in the first internal build.
                # Keep only its database column shape so 0004 can safely convert
                # already-installed replay records without loading an account app.
                ("legacy_user_id", models.BigIntegerField(db_column="user_id")),
            ],
        ),
        migrations.AddConstraint(model_name="idempotencyrecord", constraint=models.UniqueConstraint(fields=("legacy_user_id", "operation", "key"), name="idempotency_user_op_key")),
    ]
