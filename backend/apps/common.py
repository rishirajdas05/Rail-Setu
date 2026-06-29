"""Choices shared across apps."""

from django.db import models


class TravelClass(models.TextChoices):
    FIRST_AC = "1A", "AC First Class"
    SECOND_AC = "2A", "AC 2 Tier"
    THIRD_AC = "3A", "AC 3 Tier"
    SLEEPER = "SL", "Sleeper"
    CHAIR_CAR = "CC", "AC Chair Car"
    SECOND_SITTING = "2S", "Second Sitting"


class Quota(models.TextChoices):
    GENERAL = "GN", "General"
    TATKAL = "TQ", "Tatkal"
    LADIES = "LD", "Ladies"
    SENIOR = "SS", "Senior Citizen"


class Gender(models.TextChoices):
    MALE = "M", "Male"
    FEMALE = "F", "Female"
    OTHER = "O", "Other"
