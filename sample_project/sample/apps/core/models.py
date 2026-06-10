from django.db import models


class Player(models.Model):
    """Demo model for the Model / QuerySet serialization E2E.

    ``scouting_notes`` is deliberately absent from ``InertiaMeta.fields`` —
    the serialization spec proves it never reaches the page JSON.
    """

    name = models.CharField(max_length=50)
    position = models.CharField(max_length=30)
    number = models.IntegerField()
    salary = models.DecimalField(max_digits=8, decimal_places=2)
    joined_at = models.DateTimeField()
    scouting_notes = models.TextField(blank=True, default="")

    class InertiaMeta:
        fields = ("name", "position", "number", "salary", "joined_at")
