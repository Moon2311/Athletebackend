from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status



from .serializers import UserSerializer, AthleteSerializer, AttendanceSerializer, TrainingVideoSerializer
from .models import User, Role, Team, UserTeam, Athlete, Attendence, TrainingVideo, AthletePerformance
from core.response import Response, Error

from rest_framework_simplejwt.tokens import RefreshToken
from django.core.paginator import Paginator
from django.conf import settings
from datetime import datetime
import os
from django.shortcuts import get_object_or_404
import cv2
from PIL import Image
import numpy as np
import math
from django.contrib.auth.hashers import make_password
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
from torchvision.models import resnet50, ResNet50_Weights

import mediapipe as mp
from collections import Counter


# Load the .pth file
checkpoint = torch.load("/home/talha/code/AthleteEdge-backend/AthleteEdge/cnn_prediction_full.pth", map_location="cpu")

# Print top few layer names
for key in list(checkpoint.keys())[:30]:
    print(key)

class SignUpView(APIView):
    def post(self, request):
        try:
            username = request.data.get('username')
            email = request.data.get('email')
            password = request.data.get('password')
            confirm_password = request.data.get('confirmPassword')

            if password != confirm_password:
                return Response(
                    message="password do not match",
                    status=status.HTTP_400_BAD_REQUEST,
                )

            management_role = Role.objects.filter(name="Management").first()
            if not management_role:
                return Response(
                    message="Management role not found.",
                    status=status.HTTP_400_BAD_REQUEST,
                )

            data_ = {
                'username': username,
                'email': email,
                'password': password,
                'role_id': management_role.id,
            }

            serializer = UserSerializer(data=data_)
            if serializer.is_valid():
                user = serializer.save()

                team = Team.objects.create(
                    username=username,
                    email=email,
                    password=password
                )

                UserTeam.objects.create(
                    user=user,
                    team=team
                )

                return Response(
                    success=True,
                    data=data_,
                    message="User Created Successfully.",
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    success=False,
                    message="User Creation failed.",
                    data=serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(
                success=False,
                message=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ForgetPasswordView(APIView):
    def post(self, request):
        try:
            email = request.data.get('email')
            password = request.data.get('password')
            confirm_password = request.data.get('confirmPassword')

            if not email or not password or not confirm_password:
                return Response(
                    {
                        "success": False,
                        "message": "All fields are required.",
                        "data": {}
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if password != confirm_password:
                return Response(
                    {
                        "success": False,
                        "message": "password do not match",
                        "data": {}
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.filter(email=email).first()
            if not user:
                return Response(
                    {
                        "success": False,
                        "message": "User with this email does not exist.",
                        "data": {}
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            user.password = make_password(password)
            user.save()

            return Response(
                {
                    "success": True,
                    "message": "Password updated successfully.",
                    "data": {
                        "email": email
                    }
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": str(e),
                    "data": {}
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class LoginView(APIView):
    def post(self, request):
        try:
            email = request.data.get("email")
            password = request.data.get("password")

            if not email or not password:
                return Response(
                    success=False,
                    message="Email and password are required.",
                    data=None,
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(
                    success=False,
                    message="Invalid email or password.",
                    data=None,
                    status=status.HTTP_401_UNAUTHORIZED
                )

            user = authenticate(username=user.username, password=password)
            if user is None:
                return Response(
                    success=False,
                    message="Invalid email or password.",
                    data=None,
                    status=status.HTTP_401_UNAUTHORIZED
                )

            team_id = None
            user_team = UserTeam.objects.filter(user=user).first()
            if user_team:
                team_id = user_team.team.id

            athlete_id = None
            # athlete = Athlete.objects.filter(user=user).first()
            # if athlete:
            #     athlete_id = athlete.id

            refresh = RefreshToken.for_user(user)
            refresh['team_id'] = team_id
            refresh['athlete_id'] = athlete_id
            message=""

            return Response(
                {
                    "success": True,
                    "message": "Login successful.",
                    "data": {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                    }
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response( 
                success=False,
                message=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateListAthlete(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            team_id = request.auth.payload.get("team_id")

            if not team_id:
                return Response({
                    "meta_data": {
                        "success": False,
                        "status_code": 400,
                        "message": "Team ID not found in token."
                    },
                    "data": {}
                }, status=status.HTTP_400_BAD_REQUEST)

            athletes = Athlete.objects.filter(team_id=team_id).order_by('id')
            total_athletes = athletes.count()

            # Pagination setup
            page = int(request.query_params.get("page", 1))
            limit = int(request.query_params.get("limit", 10))
            paginator = Paginator(athletes, limit)
            current_page = paginator.get_page(page)

            athlete_data = []
            total_percentages = []

            for athlete in current_page.object_list:
                total_attendance = Attendence.objects.filter(athlete=athlete).count()
                present_attendance = Attendence.objects.filter(athlete=athlete, attendence='present').count()

                attendance_percentage = 0
                if total_attendance > 0:
                    attendance_percentage = (present_attendance / total_attendance) * 100

                total_percentages.append(attendance_percentage)

                athlete_data.append({
                    "id": athlete.id,
                    "name": f"{athlete.first_name} {athlete.last_name}",
                    "attendance_percentage": round(attendance_percentage, 1)
                })

            average_attendance = round(sum(total_percentages) / len(total_percentages), 1) if total_percentages else 0

            return Response({
                "meta_data": {
                    "success": True,
                    "status_code": 200,
                    "message": "Athletes fetched successfully."
                },
                "data": {
                    "athletes": athlete_data,
                    "total_athletes": total_athletes,
                    "average_attendance": average_attendance,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total_pages": paginator.num_pages,
                        "has_next": current_page.has_next(),
                        "has_previous": current_page.has_previous()
                    }
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "meta_data": {
                    "success": False,
                    "status_code": 500,
                    "message": str(e)
                },
                "data": {}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def post(self, request, *args, **kwargs):
        try:
            team_id = request.auth.payload.get("team_id")

            if not team_id:
                return Response(
                    success=False,
                    message="Team ID not found in token.",
                    status=status.HTTP_400_BAD_REQUEST
                )

            team = Team.objects.filter(id=team_id).first()
            if not team:
                return Response(
                    success=False,
                    message="Team not found.",
                    status=status.HTTP_404_NOT_FOUND
                )

            data = request.data.copy()
            data['team'] = team.id

            serializer = AthleteSerializer(data=data)
            if serializer.is_valid():
                athlete = serializer.save()

                return Response(
                    success=True,
                    message="Athlete created successfully.",
                    data=serializer.data,
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    success=False,
                    message="Invalid data",
                    data=serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response(
                success=False,
                message=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

class AthleteAttendence(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            team_id = request.auth.payload.get("team_id")
            if not team_id:
                return Response(
                    success=False,
                    message="Team ID not found in token.",
                    data={},
                    status=status.HTTP_400_BAD_REQUEST
                )

            athletes = Athlete.objects.filter(team_id=team_id)
            if not athletes.exists():
                return Response(
                    success=False,
                    message="No athletes found for this team.",
                    data={},
                    status=status.HTTP_404_NOT_FOUND
                )

            attendances = Attendence.objects.filter(athlete__in=athletes).select_related('athlete')

            data = []
            for att in attendances:
                data.append({
                    "athlete_id": att.athlete.id,
                    "athlete_name": f"{att.athlete.first_name} {att.athlete.last_name}",
                    "date": att.date.strftime("%Y-%m-%d") if att.date else None,
                    "attendence": att.attendence
                })

            return Response(
                success=True,
                message="Attendance data retrieved successfully.",
                data=data,
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                success=False,
                message=str(e),
                data={},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        try:
            serializer = AttendanceSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(
                    success=True,
                    message="Attendance recorded successfully.",
                    data=serializer.data,
                    status=status.HTTP_201_CREATED
                )
            return Response(
                success=False,
                message="Invalid data",
                data=serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            return Response(
                success=False,
                message=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetAthleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            athlete_id = request.query_params.get("athlete_id")

            if not athlete_id:
                return Response({
                    "success": False,
                    "message": "athlete_id query parameter is required."
                }, status=status.HTTP_400_BAD_REQUEST)

            athlete = get_object_or_404(Athlete, id=athlete_id)
            full_name = f"{athlete.first_name} {athlete.last_name}"

            # Count attendance records with 'present'
            total_present = Attendence.objects.filter(athlete=athlete, attendence='present').count()

            # Get latest performance record if exists
            latest_performance = AthletePerformance.objects.filter(athlete=athlete).order_by('-created_at').first()

            performance_data = {
                "posture_score": latest_performance.posture_score if latest_performance else None,
                "form_quality": latest_performance.form_quality if latest_performance else None,
                "final_wrist_angle": latest_performance.final_wrist_angle if latest_performance else None,
            }

            return Response({
                "success": True,
                "message": "Athlete data fetched successfully.",
                "data": {
                    "name": full_name,
                    "total_present_attendance": total_present,
                    **performance_data
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class   TrainingVideoUploadAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = TrainingVideoSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    success=True,
                    message="Video uploaded successfully.",
                    data=serializer.data,
                    status=status.HTTP_201_CREATED
                )
            return Response(
                success=False,
                message="Invalid video data.",
                data=serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                success=False,
                message=str(e),
                data={},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = resnet50(weights=ResNet50_Weights.DEFAULT)
model.fc = nn.Linear(model.fc.in_features, 4)


model.load_state_dict(torch.load('/home/talha/code/AthleteEdge-backend/AthleteEdge/cnn_prediction_full.pth', map_location=device))
model.to(device)
model.eval()

class_names = ['Drive', 'Pull', 'Sweep', 'Cut']


class PredictFromVideo(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            video_url = request.data.get("video_url")
            athlete_id = request.data.get("athlete_id")

            if not video_url:
                return Response({"error": "Video URL not provided"}, status=400)
            if not athlete_id:
                return Response({"error": "Athlete ID not provided"}, status=400)

            athlete = Athlete.objects.filter(id=athlete_id).first()
            if not athlete:
                return Response({"error": "Invalid athlete ID"}, status=404)
            

            video_path = os.path.join(settings.BASE_DIR, video_url)
            print("Video path:", video_path)
            
            cap = cv2.VideoCapture(video_path)
            ret, frame = cap.read()
            if not cap.isOpened():
                return Response({"error": "Cannot open video. Check path or codec."}, status=400)
            if not ret:
                return Response({"error": "Video opened but cannot read frames. Check codec or corruption."}, status=400)


            transform = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((128, 128)),
                transforms.ToTensor(),
            ])

            mp_pose = mp.solutions.pose

            # Step 2: Create an instance of the Pose detector
            pose = mp_pose.Pose(
                static_image_mode=False,
                min_detection_confidence=0.5
            )
            all_predictions = []
            wrist_angles = []
            speeds = []
            posture_scores = []

            frames_with_wrist_data = 0
            frame_count = 0
            last_wrist_pos = None

            while cap.isOpened():
                
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % 10 == 0:
                    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, _ = frame.shape

                    results = pose.process(img_rgb)

                    if results.pose_landmarks:
                        lm = results.pose_landmarks.landmark
                        def get_point(p): return np.array([p.x * w, p.y * h, p.z * 1000])
                        shoulder = get_point(lm[mp_pose.PoseLandmark.RIGHT_SHOULDER])
                        elbow = get_point(lm[mp_pose.PoseLandmark.RIGHT_ELBOW])
                        wrist = get_point(lm[mp_pose.PoseLandmark.RIGHT_WRIST])

                        v1 = shoulder - elbow
                        v2 = wrist - elbow
                        dot_product = np.dot(v1, v2)
                        mag_v1 = np.linalg.norm(v1)
                        mag_v2 = np.linalg.norm(v2)
                        angle_rad = np.arccos(dot_product / (mag_v1 * mag_v2 + 1e-6))
                        angle_deg = np.degrees(angle_rad)
                        wrist_angles.append(angle_deg)
                        frames_with_wrist_data += 1

                        elbow_angle = angle_deg
                        if 160 <= elbow_angle <= 180:
                            posture_scores.append(1.0)
                        elif 140 <= elbow_angle < 160:
                            posture_scores.append(0.8)
                        elif 120 <= elbow_angle < 140:
                            posture_scores.append(0.5)
                        else:
                            posture_scores.append(0.2)

                        wrist_pos_2d = np.array([wrist[0], wrist[1]])
                        if last_wrist_pos is not None:
                            displacement = np.linalg.norm(wrist_pos_2d - last_wrist_pos)
                            speed = displacement * 3
                            speeds.append(speed)
                        last_wrist_pos = wrist_pos_2d

                    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img_tensor = transform(img).unsqueeze(0).to(device)
                    with torch.no_grad():
                        output = model(img_tensor)
                        _, pred = torch.max(output, 1)
                        all_predictions.append(class_names[pred.item()])

                frame_count += 1

            cap.release()

            if not all_predictions:
                return Response({"error": "No predictions made"}, status=400)

            most_common = Counter(all_predictions).most_common(1)[0]
            final_wrist_angle = wrist_angles[-1] if wrist_angles else None
            avg_wrist_angle = sum(wrist_angles) / len(wrist_angles) if wrist_angles else None
            avg_speed = sum(speeds) / len(speeds) if speeds else None
            posture_score = sum(posture_scores) / len(posture_scores) * 100 if posture_scores else None
            form_quality = max(0, 100 - np.std(wrist_angles) * 2) if len(wrist_angles) >= 2 else None

            performance = AthletePerformance.objects.create(
                athlete=athlete,
                final_prediction=most_common[0],
                confidence=round(most_common[1] / len(all_predictions), 2),
                total_frames_processed=frame_count,
                frames_with_wrist_data=frames_with_wrist_data,
                final_wrist_angle=round(final_wrist_angle, 1) if final_wrist_angle else None,
                average_wrist_angle=round(avg_wrist_angle, 1) if avg_wrist_angle else None,
                average_speed=round(avg_speed, 2) if avg_speed else None,
                posture_score=round(posture_score, 1) if posture_score else None,
                form_quality=round(form_quality, 1) if form_quality else None
            )

            return Response({
                "message": "Prediction saved successfully",
                "data": {
                    "final_prediction": performance.final_prediction,
                    "confidence": performance.confidence,
                    "total_frames_processed": performance.total_frames_processed,
                    "frames_with_wrist_data": performance.frames_with_wrist_data,
                    "final_wrist_angle": performance.final_wrist_angle,
                    "average_wrist_angle": performance.average_wrist_angle,
                    "average_speed": performance.average_speed,
                    "posture_score": performance.posture_score,
                    "form_quality": performance.form_quality
                }
            }, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)
        
from ultralytics import YOLO

model2 = YOLO("cricket_ball_detection/train/weights/best.pt")


from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from pathlib import Path
from PIL import Image
import tempfile


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
import tempfile
from pathlib import Path
import os
import cv2
from django.conf import settings

class DetectAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Check if file is in request
        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"error": "No image uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(image_file.name).suffix) as temp_file:
            for chunk in image_file.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name

        # Run YOLO prediction
        results = model2.predict(
            source=temp_path,
            conf=0.25
        )

        # Load image with OpenCV
        img = cv2.imread(temp_path)

        # Prepare detections and draw boxes
        detections = []
        for r in results:
            for box in r.boxes:
                x_min, y_min, x_max, y_max = map(int, box.xyxy[0].tolist())
                confidence = float(box.conf[0])

                # Draw white rectangle
                cv2.rectangle(img, (x_min, y_min), (x_max, y_max), color=(255, 255, 255), thickness=2)

                # Put label
                label = f"cricket_ball {confidence:.2f}"
                cv2.putText(img, label, (x_min, y_min - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                detections.append({
                    "class": "cricket_ball",
                    "confidence": confidence,
                    "bbox": [x_min, y_min, x_max, y_max]
                })

        # Save the image in MEDIA_ROOT/bowl
        bowl_folder = os.path.join(settings.MEDIA_ROOT, "bowl")
        os.makedirs(bowl_folder, exist_ok=True)

        output_filename = f"{Path(image_file.name).stem}_output.jpg"
        output_path = os.path.join(bowl_folder, output_filename)
        cv2.imwrite(output_path, img)

        # Remove temp file
        Path(temp_path).unlink(missing_ok=True)

        # Build URL to access the image
        output_url = request.build_absolute_uri(f"{settings.MEDIA_URL}bowl/{output_filename}")

        return Response({
            "detections": detections,
            "output_image_url": output_url
        }, status=status.HTTP_200_OK)
    

import cv2
import os
import tempfile
from pathlib import Path
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

class DetectVideoAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        video_file = request.FILES.get("video")
        if not video_file:
            return Response({"error": "No video uploaded"}, status=400)

        # 1️⃣ Save video temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(video_file.name).suffix) as temp_file:
            for chunk in video_file.chunks():
                temp_file.write(chunk)
            video_path = temp_file.name

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            return Response({"error": "Cannot open video"}, status=400)

        fps = int(cap.get(cv2.CAP_PROP_FPS))  # original video fps
        frames_per_second = 28
        frame_interval = max(1, fps // frames_per_second)

        output_folder = os.path.join(settings.MEDIA_ROOT, "video_frames")
        os.makedirs(output_folder, exist_ok=True)

        frame_index = 0
        saved_frames = []
        detections_output = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 2️⃣ Take 28 frames per second
            if frame_index % frame_interval == 0:
                results = model2.predict(source=frame, conf=0.25)

                frame_detections = []

                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        confidence = float(box.conf[0])

                        # Draw box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)
                        cv2.putText(
                            frame,
                            f"cricket_ball {confidence:.2f}",
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (255, 255, 255),
                            2
                        )

                        frame_detections.append({
                            "class": "cricket_ball",
                            "confidence": confidence,
                            "bbox": [x1, y1, x2, y2]
                        })

                # 3️⃣ Save frame ONLY if detection exists
                if frame_detections:
                    frame_name = f"{Path(video_file.name).stem}_frame_{frame_index}.jpg"
                    frame_path = os.path.join(output_folder, frame_name)
                    cv2.imwrite(frame_path, frame)

                    saved_frames.append(
                        request.build_absolute_uri(
                            f"{settings.MEDIA_URL}video_frames/{frame_name}"
                        )
                    )

                    detections_output.append({
                        "frame": frame_index,
                        "detections": frame_detections
                    })

            frame_index += 1

        cap.release()
        # Path(video_path).unlink(missing_ok=True)
        # images_to_video(images_folder=saved_frames,output_video_path,fps=28)

        return Response(
            {
                "total_detected_frames": len(saved_frames),
                "frames": saved_frames,
                "detections": detections_output
            },
            status=status.HTTP_200_OK
        )
