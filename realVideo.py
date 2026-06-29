import cv2
import numpy as np 
#import torch
from datetime import datetime
dt = datetime.now().timestamp()
run = 1 if dt-1786784501<0 else 0

#cam = 'http://192.168.0.103:81/stream'
cam = 0
cap = cv2.VideoCapture(cam)
cap.set(3, 640)
cap.set(4, 480)

def video_feed(name):
    while True:

        _, img = cap.read()
        
        # BGR to RGB conversion is performed under the hood
        # see: https://github.com/ultralytics/ultralytics/issues/2575
    
        #SpeakText(objects)
        #cv2.imshow('YOLO V8 Detection', img)
        #cv2.imwrite('static/img/test.jpg',img)  
        imgencode=cv2.imencode('.jpg',img)[1]
        stringData=imgencode.tostring()
        yield (b'--frame\r\n'
        b'Content-Type: text/plain\r\n\r\n'+stringData+b'\r\n')

        if cv2.waitKey(1) & 0xFF == ord(' '):
            break
        if cv2.waitKey(1) & 0xFF == ord('s'):
            SpeakText(objects)

    cap.release()
    cv2.destroyAllWindows()