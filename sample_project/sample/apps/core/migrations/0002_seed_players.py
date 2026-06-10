from datetime import datetime, timezone
from decimal import Decimal

from django.db import migrations

# Fixed values on purpose: the serialization E2E asserts the exact JSON the
# page shell carries (ISO-8601 datetimes, Decimal-as-string, field filtering).
PLAYERS = [
    {
        "name": "Brian",
        "position": "Center",
        "number": 9,
        "salary": Decimal("980.00"),
        "joined_at": datetime(2026, 3, 2, 18, 0, tzinfo=timezone.utc),
        "scouting_notes": "TOP SECRET: fades after 40-second shifts",
    },
    {
        "name": "Brandon",
        "position": "Goalie",
        "number": 30,
        "salary": Decimal("1250.50"),
        "joined_at": datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc),
        "scouting_notes": "TOP SECRET: glove-side weakness",
    },
]


def seed_players(apps, schema_editor):
    player_model = apps.get_model("core", "Player")
    player_model.objects.bulk_create(player_model(**fields) for fields in PLAYERS)


def unseed_players(apps, schema_editor):
    player_model = apps.get_model("core", "Player")
    player_model.objects.filter(
        name__in=[fields["name"] for fields in PLAYERS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_players, unseed_players),
    ]
