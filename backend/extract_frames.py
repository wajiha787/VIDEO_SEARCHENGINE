import cv2
import os

video_path = "videos/marathon.mp4"
output_folder = "frames"

os.makedirs(output_folder, exist_ok=True)

cap = cv2.VideoCapture(video_path)

frame_count = 0
saved_count = 0

while True:
    ret, frame = cap.read()
    
    if not ret:
        break

    # save 1 frame every second (assuming ~30fps)
    if frame_count % 30 == 0:
        filename = f"{output_folder}/frame_{saved_count}.jpg"
        cv2.imwrite(filename, frame)
        saved_count += 1

    frame_count += 1

cap.release()

print("Frames extracted:", saved_count)