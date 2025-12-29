import cv2
import os
from pathlib import Path
def images_to_video(
    images_folder,
    output_video_path,
    fps=28
):
    images_folder = Path(images_folder)
    output_path = Path(output_video_path)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get all images (sorted) - supports jpg, jpeg, png
    image_paths = sorted(images_folder.glob("*.[jp][pn]g"))
    image_paths = [p for p in image_paths if p.is_file()]

    if not image_paths:
        raise ValueError("No images found in folder")

    # Read first image to get size
    first_image = cv2.imread(str(image_paths[0]))
    if first_image is None:
        raise ValueError(f"Cannot read image {image_paths[0]}")

    height, width, _ = first_image.shape

    # Use mp4v codec and ensure .mp4 extension
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video_writer = cv2.VideoWriter(
        str(output_path),  # Ensure it's string
        fourcc,
        fps,
        (width, height)
    )

    if not video_writer.isOpened():
        raise RuntimeError("Could not open VideoWriter. Check codec and path.")

    for image_path in image_paths:
        img = cv2.imread(str(image_path))
        if img is None:
            print(f"Warning: Could not read {image_path}, skipping.")
            continue

        img = cv2.resize(img, (width, height))
        video_writer.write(img)

    video_writer.release()
    print(f"✅ Video saved at: {output_path}")

output_video = "/home/talha/code/AthleteEdge-backend/AthleteEdge/media/output"


images_to_video(
    images_folder="/home/talha/code/AthleteEdge-backend/AthleteEdge/media/video_frames",
    output_video_path=output_video,
    fps=28
)

