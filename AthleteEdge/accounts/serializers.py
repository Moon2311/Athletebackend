from rest_framework import serializers
import subprocess
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.core.exceptions import ValidationError
from accounts.models import User,Role,Athlete, Attendence, TrainingVideo
import tempfile
import cv2


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source='role',   # Model ke 'role' field ko bind karna
        required=False,
        allow_null=True
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role_id']

    def create(self, validated_data):
        role = validated_data.pop('role', None)
        user = User(
            username=validated_data['username'],
            email=validated_data['email']
        )
        if role:
            user.role = role
        user.set_password(validated_data['password'])  
        user.save()
        return user

    def update(self, instance, validated_data):
        role = validated_data.pop('role', None)
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if role is not None:
            instance.role = role

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class AthleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Athlete
        fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'role', 'team']
        extra_kwargs = {
            'team': {'write_only': True, 'required': False},
            'date_of_birth': {
                'input_formats': ["%Y-%m-%d"],
                'error_messages': {
                    'invalid': 'Date of birth must be in format YYYY-MM-DD.',
                    'required': 'Date of birth is required.'
                }
            }
        }

    def create(self, validated_data):
        return Athlete.objects.create(**validated_data)


class AttendanceSerializer(serializers.ModelSerializer):
    athlete_id = serializers.IntegerField(write_only=True)
    date = serializers.DateField(input_formats=["%Y-%m-%d"])

    class Meta:
        model = Attendence
        fields = ['athlete_id', 'date', 'attendence']

    def validate(self, attrs):
        request = self.context.get("request")
        team_id = request.auth.payload.get("team_id")
        athlete_id = attrs.get("athlete_id")

        athlete = Athlete.objects.filter(id=athlete_id, team_id=team_id).first()
        if not athlete:
            raise serializers.ValidationError("Athlete not found in your team.")

        attrs['athlete'] = athlete
        return attrs

    def create(self, validated_data):
        validated_data.pop('athlete_id', None) 
        return Attendence.objects.create(**validated_data)


class TrainingVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingVideo
        fields = ['id', 'video', 'athlete', 'uploaded_at']

    def validate_video(self, value):
        try:
            if isinstance(value, InMemoryUploadedFile):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                    for chunk in value.chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name
            elif isinstance(value, TemporaryUploadedFile):
                temp_file_path = value.temporary_file_path()
            else:
                raise serializers.ValidationError("Invalid file type.")

            cap = cv2.VideoCapture(temp_file_path)
            if not cap.isOpened():
                raise serializers.ValidationError("Could not read video file.")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            duration = frame_count / fps if fps > 0 else 0
            cap.release()

            if duration > 120:
                raise serializers.ValidationError("Maximum allowed video duration is 2 minutes.")
        except Exception as e:
            raise serializers.ValidationError("Invalid video file or could not read duration.")
        return value