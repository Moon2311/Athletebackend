from sqlite3.dbapi2 import Timestamp

from django.contrib.auth.models import AbstractUser
from django.db import models
from core.models import TimestampedModel


class Role(TimestampedModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "Role"


class User(AbstractUser):
    email = models.EmailField(unique=True, null=False, blank=False)
    username = models.CharField(
        max_length=150, null=False, blank=False, unique=True
    )  # max_length added
    role = models.ForeignKey("Role", on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.username

    class Meta:
        db_table = "User"


class Team(TimestampedModel):
    username = models.CharField(max_length=150, null=False, blank=False, unique=True)
    email = models.CharField(max_length=150, null=False, blank=False, unique=True)
    password = models.CharField(max_length=100, null=False, blank=False, unique=True)

    class Meta:
        db_table = "Team"


class UserTeam(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = "UserTeam"


class Athlete(TimestampedModel):
    first_name = models.CharField(max_length=100, null=False, blank=False)
    last_name = models.CharField(max_length=100, null=False, blank=False)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(null=False, blank=False)
    role = models.CharField(null=False, blank=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)

    class Meta:
        db_table = "Athlete"


class Attendence(models.Model):
    athlete = models.ForeignKey(Athlete, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)
    attendence = models.CharField(
        max_length=20, null=True, blank=True, default="present"
    )

    def __str__(self):
        return f"{self.athlete} - {self.date} - {self.attendence}"

    class Meta:
        db_table = "Attendence"


class TrainingVideo(models.Model):
    video = models.FileField(upload_to="videos/")
    athlete = models.ForeignKey(
        Athlete, on_delete=models.CASCADE, null=True, blank=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Video {self.pk}"


class AthletePerformance(TimestampedModel):
    athlete = models.ForeignKey(
        Athlete, on_delete=models.CASCADE, related_name="performances"
    )

    final_prediction = models.CharField(max_length=50)
    confidence = models.FloatField()
    total_frames_processed = models.IntegerField()
    frames_with_wrist_data = models.IntegerField()
    final_wrist_angle = models.FloatField(null=True, blank=True)
    average_wrist_angle = models.FloatField(null=True, blank=True)
    average_speed = models.FloatField(null=True, blank=True)
    posture_score = models.FloatField(null=True, blank=True)
    form_quality = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "AthletePerformance"
