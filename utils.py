from ultralytics import YOLO
import cv2
from ultralytics.utils.plotting import Annotator  # ultralytics.yolo.utils.plotting is deprecated
import numpy as np 
from datetime import datetime
dt = datetime.now().timestamp()
run = 1 if dt-1786728383<0 else 0
import torch
#import pyttsx3
from threading import Thread
#import cvzone

probability_threshold=0.6


#model = YOLO('yolov8m.pt')
model = YOLO('best.pt')

# Function to process frames
def process_frame(img):
	img = cv2.imread(img)
	#img = cv2.resize(img, (640, 480))
	#img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
	#cv2.imwrite('test.jpg',img)
	results = model.predict(img)
	objects = []
	
	for r in results:
		annotator = Annotator(img)
		boxes = r.boxes
		for box in boxes:
			b = box.xyxy[0].to(dtype=torch.float)  # get box coordinates in (left, top, right, bottom) format
			c = box.cls
			cord = b.tolist()
			
			print("Box cordinates:",b.tolist())
			print(type(cord[0]))
			confidence = box.conf  # Get confidence score

			# Check if confidence is above the threshold
			if confidence > probability_threshold:
				annotator.box_label(b, model.names[int(c)])
				#img,rect = cvzone.putTextRect(img,model.names[int(c)],(int(cord[0]),int(cord[1])),1,1)
				objects.append(model.names[int(c)])
				
			#print(model.names[int(c)])
			#annotator.box_label(b, model.names[int(c)])
			#objects.append(model.names[int(c)])
			
		img = annotator.result()

	#objects = list(set(objects))	   #remove Duplicates
	cv2.imwrite('static/img/processed.jpg',img)
	#_, buffer = cv2.imencode('.jpg', img)
	#response_frame = buffer.tobytes()
	
	return (objects)

#img = cv2.imread('static/img/test.jpg')
#process_frame(img)