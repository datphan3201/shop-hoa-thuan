from django.db import migrations, models
import django.db.models.deletion


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
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="auth.user")),
            ],
        ),
        migrations.AddConstraint(model_name="idempotencyrecord", constraint=models.UniqueConstraint(fields=("user", "operation", "key"), name="idempotency_user_op_key")),
    ]
