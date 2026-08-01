from django.db import migrations, models


def copy_legacy_owner_to_client_key(apps, schema_editor):
    record_model = apps.get_model("core", "IdempotencyRecord")
    for record in record_model.objects.all().iterator():
        record.client_key = f"legacy-{record.legacy_user_id}"
        record.save(update_fields=["client_key"])


class Migration(migrations.Migration):
    dependencies = [("core", "0003_shopsecuritysettings_revision")]

    operations = [
        migrations.RemoveConstraint(
            model_name="idempotencyrecord",
            name="idempotency_user_op_key",
        ),
        migrations.AddField(
            model_name="idempotencyrecord",
            name="client_key",
            field=models.CharField(default="", max_length=64),
            preserve_default=False,
        ),
        migrations.RunPython(copy_legacy_owner_to_client_key, migrations.RunPython.noop),
        migrations.RemoveField(model_name="idempotencyrecord", name="legacy_user_id"),
        migrations.AddConstraint(
            model_name="idempotencyrecord",
            constraint=models.UniqueConstraint(
                fields=("client_key", "operation", "key"),
                name="idempotency_client_op_key",
            ),
        ),
    ]
