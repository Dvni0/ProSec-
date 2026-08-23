from ultralytics import YOLO

model = YOLO("yolo26n-pose.pt")


results  = model("person-bicycle-car-detection.mp4", stream=True, show=True)

for result in results:
    pass

    