""" 
    - This is a document for service.py in the detection module
    - Line 13 to line 21 that import necessary library and tools
    - Line 23 to line 39 is coordinates of ROI, 4 points
    - consumer variable takes frame is processed
    - producer variable saves detection results
    - Nextly, read the result from Kafka: key, value
    - Function inference is taken from det_api.py which is responsible for getting the image path and detection results
    - Line 71 to line 74: Remove object outside ROI
    - Finally, save result detection in the producer variable
"""

import cv2
import json
import requests

from detect_api import *

from kafka_messenger import KafkaProducer, KafkaConsumer

import os

ROI =  np.array([[
              29.329889112903174,
              610.9149634576612
            ],
            [
              763,
              258
            ],
            [
              1472,
              320
            ],
            [
              1458,
              840
            ] 
            ], np.int32)


if __name__ == '__main__':
    consumer = KafkaConsumer('processed_frames')
    producer = KafkaProducer('det_results')
    while True:
        msg = consumer.consume()

        if msg is None:
            continue

        key = msg.key()
        value = msg.value()

        #giữ nguyên
        frame_id = value['frame_id']
        img_path = value['url']
        img = cv2.imread(img_path)
        
        
        # if os.path.exists(img_path):
        #     os.remove(img_path)
        # else:
        #     continue
        
        img, detection = inference(img)
        #return bboxes
        # detection = [[x1, y1, x2, y2, score, class], ...]
        
        new_detection = []
        
        for detect in detection:
          if cv2.pointPolygonTest(ROI, (detect[0],detect[1]),False)>=0 or cv2.pointPolygonTest(ROI, (detect[2],detect[3]),False)>=0 \
          or cv2.pointPolygonTest(ROI, (detect[0],detect[3]),False)>=0 or cv2.pointPolygonTest(ROI, (detect[2],detect[1]),False)>=0:
            new_detection.append(detect)
        

        bbox = [bb[:4] for bb in new_detection]
        score = [bb[4] for bb in new_detection]
        classes = [bb[5] for bb in new_detection]
        
        value={
                'frame_id': frame_id,
                'score': score,
                'class': classes,
                'bbox': bbox,
            }
        producer.produce(
            key=key, 
            value=value
        )
