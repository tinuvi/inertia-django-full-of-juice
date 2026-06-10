from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Player",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50)),
                ("position", models.CharField(max_length=30)),
                ("number", models.IntegerField()),
                ("salary", models.DecimalField(decimal_places=2, max_digits=8)),
                ("joined_at", models.DateTimeField()),
                ("scouting_notes", models.TextField(blank=True, default="")),
            ],
        ),
    ]
