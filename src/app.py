# from model import main
import os
import cv2
import json
import time
import plotly
import random
import folium
import plotly.express as px
import atexit, plotly, plotly.graph_objs as go
import cv2
import requests
import json
import time
import numpy as np
import glob
import queue
import threading
import sys

from tqdm import tqdm
from flask import Flask, render_template, url_for, send_file, Response, jsonify, send_file, request
from time import sleep
from collections import OrderedDict
from draw import draw_bbox
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pusher import Pusher
# from urllib.request import urlopen
# with urlopen('https://gist.githubusercontent.com/hrbrmstr/94bdd47705d05a50f9cf/raw/0ccc6b926e1aa64448e239ac024f04e518d63954/asia.geojson') as response:
#     asia = json.load(response)

SCHEMA_REGISTRY = 'http://schema-registry:8080'
# Wait until Schema Registry is online
while True:
    try:
        _ = requests.get(SCHEMA_REGISTRY)
        break
    except requests.exceptions.RequestException:
        pass

from kafka_manager import create_topics, create_schema
from kafka_messenger import KafkaProducer, KafkaConsumer

video_list = [
    (
        'cam_02',
        queue.Queue(),
        [0],
        [np.zeros((1080, 1920, 3), dtype=np.uint8)],
        cv2.VideoCapture('/Videos/custom_video_2.mp4')
    )
]


class Draw:
    def __init__(self):
        self.history_movement_dict = {}     # Store all center point of boundary box and then draw a poly line to connect them        
        self.value = {}
        self.history_frame = 0

    def draw_tracking_result(self):
        try:
            frame_id = self.value.get("frame_id")
            bbs = self.value.get("bbox")
        except Exception as e :
            pass

        try:
            img_path     = "/storage/{}_{:05d}.jpg".format("cam_02", frame_id)
            des_img_path = "/home/{}_{:05d}.jpg".format("cam_02", frame_id)
            img = cv2.imread(img_path)
        except Exception as e :
            print("Error:", e)

        for i in range(len(bbs)):
            # Coordinate of boundary Box
            x1y1 = self.value["bbox"][i][:2]
            x2y2 = self.value["bbox"][i][2:]
            # Coordinate of center
            xmym = self.get_center_point(x1y1, x2y2)

            self.__store_history_movement(i, xmym)

            # Coordinate of text object_Class & track_id
            x0y0 = self.__get_text_cor(x1y1, x2y2)

            # Get name for Class and Track_id
            object_class = self.value["class"][i]
            track_id = self.value["track_id"][i]

            # Draw different color rectangles for different track_id
            image = self.draw_boundary_box(img, x1y1, x2y2, track_id)

            name_of_object_class = self.__get_name_of_object_class(object_class)
            txt = name_of_object_class + "_trackID:" + str(track_id)            
            x0y0_rectangle = self.__get_text_cor_rectangle(x0y0, txt, name_of_object_class)
            image = cv2.rectangle(image, tuple(x0y0_rectangle[0]), tuple(x0y0_rectangle[1]), [0, 0, 0], -1)

            try:
                image = cv2.putText(image, txt, tuple(x0y0), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.5, [255, 255, 255], 1, cv2.LINE_AA)
            except Exception as e:
                print("PutText", e)

            
            
            try:
                cv2.imwrite(des_img_path, image)
            except Exception as e:
                print(e)

    
    # Draw Boundary Box and color based on TrackID 
    def draw_boundary_box(self, img, x1y1, x2y2, track_id):
        np.random.seed(track_id)
        try:
            color = list(np.random.randint(255, size=3))
            color = [int(color[0]), int(color[1]), int(color[2])]
            image = cv2.rectangle(img, tuple(x1y1), tuple(x2y2), color, 2)
            image = self.__draw_track_movement(image, track_id, color)
            return image

        except Exception as e:
            print("DrawBB", e)

    @staticmethod
    def get_center_point(bb1, bb2):
        # Get Top-left and Bottom-right of BBox 
        # Return cordinate of bbox's center
        xm = abs(bb1[0] - bb2[0]) / 2
        x = xm + min(bb1[0], bb2[0])
        ym = abs(bb1[1] - bb2[1]) / 2
        y = ym + min(bb1[1], bb2[1])
        return [int(x), int(y)]

    def __draw_track_movement(self, img, track_id, color):
        if len(self.history_movement_dict[track_id]) >= 2:
            pts = np.array(self.history_movement_dict.get(track_id))
            image = cv2.polylines(img, [pts],
                                  isClosed=False, color=color, thickness=2)          
            return image
        else:
            return img
        
    def __store_history_movement(self, i, center):
        track_id = self.value.get("track_id")[i]
        if track_id not in self.history_movement_dict:
            self.history_movement_dict[track_id] = [center]
        else:
            self.history_movement_dict[track_id].append(center)

    @staticmethod
    def __get_text_cor(x1y1, x2y2):
        x1 = x1y1[0]
        y1 = x1y1[1]
        x2 = x2y2[0]
        y2 = x2y2[1]
        x0 = min(x1, x2)
        y0 = min(y1, y2)
        return [x0, y0 - 3]

    def __get_text_cor_rectangle(self, x0y0, txt, name_of_object_class):
        if name_of_object_class == 'Pedestrian':    # 10 character and 1 "_"
            width = (10 * 10) + 10 + 50 + len(txt.split(":")[1]) * 10
            height = 15
            pts_top_right = [x0y0[0] + width, x0y0[1] - height]
        elif name_of_object_class == 'Bike':        # 4 character and 1 "_"
            width = (4 * 10) + 10 + 50 + len(txt.split(":")[1]) * 10
            height = 15
            pts_top_right = [x0y0[0] + width, x0y0[1] - height]
        elif name_of_object_class == 'Car':         # 3 character and 1 "_"
            width = (3 * 10) + 10 + 50 + len(txt.split(":")[1]) * 10
            height = 15
            pts_top_right = [x0y0[0] + width, x0y0[1] - height]
        elif name_of_object_class == 'Bus':         # 3 character and 1 "_"
            width = (3 * 10) + 10 + 50 + len(txt.split(":")[1]) * 10
            height = 15
            pts_top_right = [x0y0[0] + width, x0y0[1] - height]
        elif name_of_object_class == 'Truck':       # 5 character and 1 "_"
            width = (5 * 10) + 10 + 50 + len(txt.split(":")[1]) * 10
            height = 15
            pts_top_right = [x0y0[0] + width, x0y0[1] - height]
        return [x0y0, pts_top_right]

    def __get_name_of_object_class(self, object_class):
        if object_class == 0:
            return "Pedestrian"
        elif object_class == 1:
            return "Bike"
        elif object_class == 2:
            return "Car"
        elif object_class == 3:
            return "Bus"
        elif object_class == 4:
            return "Truck"


class Visualize:
    def __init__(self,mf):
        self.frame_info = {}
        self.max_frame = mf 
        self.previous_frame_info = {
                                    0:  {
                                        "0": 0,
                                        "1": 0,
                                        "2": 0,
                                        "3": 0,
                                        "4": 0
                                        },
                                    1:  {
                                        "0": 0,
                                        "1": 0,
                                        "2": 0,
                                        "3": 0,
                                        "4": 0
                                        }
                                    }
                                        
        self.__generate_frame_info()

    def get_frame_info_dict(self, value):
        try:
            track_id = value['track_id']
            classes = self.__most_frequent(value['class'])
            frame_id = value['frame_id'][-1]
            moi_id = value['moi_id']
            

            if frame_id not in self.frame_info:
                self.frame_info[frame_id] = {
                                    0:  {
                                        "0": 0,
                                        "1": 0,
                                        "2": 0,
                                        "3": 0,
                                        "4": 0
                                        },
                                    1:  {
                                        "0": 0,
                                        "1": 0,
                                        "2": 0,
                                        "3": 0,
                                        "4": 0
                                        }
                                    }
                key_class = str(classes)
                self.frame_info[frame_id][moi_id][key_class] += 1
            elif frame_id in self.frame_info:
                key_class = str(classes)
                self.frame_info[frame_id][moi_id][key_class] += 1
            
            return dict(self.__sort_dict(self.frame_info))
        except Exception as e:
            print("get_frame_info", e)

    def draw_counting_effect(self, value):
        video_id = 'cam_02'
        bbox = value['bbox'][-1]    # Get latest exist bbox
        x1y1 = bbox[:2]     # top-left
        x2y2 = bbox[2:]     # bottom-right
        xmym = Draw.get_center_point(x1y1, x2y2)             # center
        last_frame = value['frame_id'][-1]                   # name of last frame exists        
        moi_id = value['moi_id']
        track_id = value['track_id']


        if moi_id == 0:
            for i in range(5):
                file_path = '/storage/{}_{:05d}.jpg'.format(video_id, last_frame)
                img = cv2.imread(file_path)
                img = cv2.circle(img, tuple(xmym), 10, (0,0,255), -1)
                cv2.imwrite(file_path, img)
                last_frame += 1
                # print("Draw on", last_frame, "at bbox", xmym, "with trackId",track_id)

        elif moi_id == 1:
            for i in range(5):
                file_path = '/storage/{}_{:05d}.jpg'.format(video_id, last_frame)
                img = cv2.imread(file_path)
                img = cv2.circle(img, tuple(xmym), 10, (0,204,0), -1)
                cv2.imwrite(file_path, img)
                last_frame += 1
                # print("Draw on", last_frame, "at bbox", xmym, "with trackId",track_id)

    def draw_on_video(self, max_frame):     
        try:
            video_id = "cam_02"  
            check_file = '/home/{}_{:05d}.jpg'.format(video_id, max_frame)
            if os.path.exists(check_file):   
                print("Start Drawing Counting", max_frame)                   
                self.previous_frame_info = {
                                    0:  {
                                        "0": 0,
                                        "1": 0,
                                        "2": 0,
                                        "3": 0,
                                        "4": 0
                                        },
                                    1:  {
                                        "0": 0,
                                        "1": 0,
                                        "2": 0,
                                        "3": 0,
                                        "4": 0
                                        }
                                    }
                for i in range(1, max_frame + 1):             
                    img_path = '/home/{}_{:05d}.jpg'.format(video_id, i)
                    img = cv2.imread(img_path)
                    img = self._draw_counting_table(img)
                    img = self._draw_cls_info(img, i)
                    img = self._draw_ROI(img)
                    img = self._draw_MOI(img)
                    try:
                        cv2.imwrite('/media/{}_{:05d}_final.jpg'.format(video_id, i), img)
                    except Exception as e:
                        print("Error from draw on video at frame", i)
                        print(e)
                        continue
                    if i == max_frame:
                        print("Start merging Video")
                        self.merge_video()
        except Exception as e:
            _, _, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Draw on video", e,exc_tb.tb_lineno)

    def merge_video(self):
        """ NOTE: Before you want to make a new video, follow these steps.
            1) cd /Videos
            2) rm cam_02_video.avi
            Reason: because the code is written that if the video has existed it will not generated 
            so in order to make a new one, delete it first.
        """
        try:
            video_id = 'cam_02'
            img_array = []
            if os.path.exists('/Videos/cam_02_video.avi') == False:

                list = os.listdir("/media") # dir is your directory path
                number_files = len(list)
                # for filename in glob.glob("/media/*.jpg"):
                #     img = cv2.imread(filename)
                #     img_array.append(img)

                for filename in range(1, number_files + 1):
                    file_path = '/media/{}_{:05d}_final.jpg'.format(video_id, filename)
                    img = cv2.imread(file_path)
                    img_array.append(img)
                
                height, width, _ = img_array[0].shape
                size = (width, height)

                out = cv2.VideoWriter('/Videos/cam_02_video.avi', cv2.VideoWriter_fourcc(*'DIVX'), 20, size)

                len_img_array = len(img_array)
                for i in range(len_img_array):
                    # Print out Progress Bar
                    out.write(img_array[i])
                out.release()
                print("Videos has been created")
            else:
                print("Video for", video_id,"already exists")
        except Exception as e:
            _, _, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("merge video", e,exc_tb.tb_lineno)

    def _draw_ROI(self, img):
        video_id = "cam_02"
        roi_path = "/Visualization/{}.json".format(video_id)
        f = open(roi_path)
        data = json.load(f)
        pts = np.array(data["shapes"][0]["points"], np.int32).reshape((-1, 1, 2))
        img = cv2.polylines(img, [pts],
                            True, [204, 102, 51], 5)

        return img 
    
    def _draw_MOI(self, img):
        video_id = "cam_02"
        moi_path = "/Visualization/{}.json".format(video_id)
        f = open(moi_path)
        data = json.load(f)
        pts_1 = data["shapes"][1]["points"]
        pts_2 = data["shapes"][2]["points"]

        img = cv2.arrowedLine(img, tuple(pts_1[0]), tuple(pts_1[1]),
                                [0,0,255], 3)
        img = cv2.arrowedLine(img, tuple(pts_2[0]), tuple(pts_2[1]),
                                [0,204,0], 3)
        
        return img

    def _draw_counting_table(self, img):
        """
        This function will draw counting table that contains 5 classes and its number of classes instance
        Input: image of post-tracking_draw
        Output: image
        """
        start_point = (1355, 1080 - 150)    # Hardcode for suitable place for Counting Table
        end_point = (1920, 1080)
        color = (255, 255, 255)
        thickness = -1

        # Draw Table
        img = cv2.rectangle(img, start_point, end_point, color, thickness)

        distance_x = end_point[0] - start_point[0]  # Width of counting table
        distance_y = end_point[1] - start_point[1]  # Height of counting table

        session_x = int(distance_x / 5)     # Space for writing information of 1 class (we have 5 classes)
        session_y = int(distance_y / 5)

        start_point_x = start_point[0] + 30     # Place to start up text on 
        start_point_y = start_point[1] + 30

        position_x = [start_point_x,
                      start_point_x + session_x * 1,
                      start_point_x + session_x * 2,
                      start_point_x + session_x * 3,
                      start_point_x + session_x * 4]

        position_y = start_point_y

        cls = ["C0",
               "C1",
               "C2",
               "C3",
               "C4"]

        # Draw Class
        for i in range(len(position_x)):
            center = (position_x[i], position_y)
            color = [0, 0, 0]
            font = cv2.FONT_HERSHEY_SIMPLEX
            fontScale = 1
            thickness = 4

            # Using cv2.putText() method
            img = cv2.putText(img, cls[i], center, font,
                              fontScale, color, thickness, cv2.LINE_AA)

        return img

    def _draw_cls_info(self, img, frame_id):
        """
        This function will draw counting number as 5 classes on counting table
        Input: image of post-tracking_draw and counting table, frame_id
        Output: image
        """
        start_point = (1355, 1080 - 150) # Hardcode for suitable place for Counting Table
        end_point = (1920, 1080)
        

        distance_x = end_point[0] - start_point[0]      # Width of counting table
        distance_y = end_point[1] - start_point[1]      # Height of counting table

        session_x = int(distance_x / 5)         # Space for writing information of 1 class (we have 5 classes)
        session_y = int(distance_y / 5)

        start_point_x = start_point[0] + 30     # Place to start up text on 
        start_point_y = start_point[1] + 30

        position_x = [start_point_x,
                      start_point_x + session_x * 1,
                      start_point_x + session_x * 2,
                      start_point_x + session_x * 3,
                      start_point_x + session_x * 4]

        position_y = [start_point_y,
                      start_point_y + session_y * 1,
                      start_point_y + session_y * 2,
                      start_point_y + session_y * 3,
                      start_point_y + session_y * 4]

        for i in range(len(self.previous_frame_info[0])):
            try:
                cls_add_moi0 = self.frame_info[frame_id][0][str(i)]
                cls_add_moi1 = self.frame_info[frame_id][1][str(i)]
            except KeyError:
                cls_add_moi0, cls_add_moi1 = 0, 0

            self.previous_frame_info[0][str(i)] += cls_add_moi0
            self.previous_frame_info[1][str(i)] += cls_add_moi1

        # Iterate through moi_id == 0,1 
        for moi in range(len(self.previous_frame_info)):
            for i in range(len(position_x)):
                center = (position_x[i] - 15, position_y[moi + 1] + 10)
                color_0 = [0, 0, 255]
                color_1 = [0, 204, 0]
                font = cv2.FONT_HERSHEY_SIMPLEX
                fontScale = 1
                thickness = 2

                # Using cv2.putText() method
                if moi == 0:
                    img = cv2.putText(img, str(self.previous_frame_info[moi][str(i)]), center, font,
                                    fontScale, color_0, thickness, cv2.LINE_AA)
                elif moi == 1:
                    img = cv2.putText(img, str(self.previous_frame_info[moi][str(i)]), center, font,
                                    fontScale, color_1, thickness, cv2.LINE_AA)
        return img

    def __generate_frame_info(self):
        for i in range(1, self.max_frame + 1):
            self.frame_info[i] = {
                                    0:  {
                                        "0": 0,
                                        "1": 0,
                                        "2": 0,
                                        "3": 0,
                                        "4": 0
                                        },
                                    1:  {
                                        "0": 0,
                                        "1": 0,
                                        "2": 0,
                                        "3": 0,
                                        "4": 0
                                        }
                                    }
            

    def __most_frequent(self, list):
        return max(set(list), key=list.count)

    def __sort_dict(self, dictionary):
        return OrderedDict(sorted(dictionary.items()))
    
    

def receive_video_stream(video_id):
    video_id, q, _, _, cap = video_list[video_id]
    while True:
        cap = cv2.VideoCapture('/Videos/custom_video_2.mp4')
        while True:
            ret, frame = cap.read()
            if not ret: break
            if q.qsize() > 20: continue
            q.put(frame)
            time.sleep(1 / 10)


def receive_detection_results():
    detect_consumer = KafkaConsumer('det_results')
    while True:
        msg = detect_consumer.consume()        
        try:            
            frame_id = msg.value().get("frame_id")
            bbs = msg.value().get("bbox")
            classes = msg.value().get("class")                        

            file_path = "/storage/{}_{:05d}.jpg".format("cam_02", frame_id)
            img = cv2.imread(file_path)

            for i in range(len(bbs)):
                # Coordinate of boundary Box
                x1y1 = msg.value()["bbox"][i][:2]
                x2y2 = msg.value()["bbox"][i][2:]
                if classes[i] == 0: 
                    color = (0, 0, 0) 
                elif classes[i] == 1:
                    color = (255,0,0)
                elif classes[i] == 2:
                    color = (0,255,0)
                elif classes[i] == 3:
                    color = (0,0,255)
                elif classes[i] == 4:
                    color = (255,255,255)
                image = cv2.rectangle(img, tuple(x1y1), tuple(x2y2), color, 2)
                img_path = "/detection/{}_{:05d}.jpg".format("cam_02", frame_id) 

                cv2.imwrite(img_path, image)
        except Exception as e :
            print(e)
            continue
        
        if msg is None:
            continue
        


def receive_track_results():
    tracking_consumer = KafkaConsumer('track_frames')
    visualize = Draw()
    while True:
        msg = tracking_consumer.consume()
        if msg is None:
            continue
        try:    
            visualize.value = msg.value()
            visualize.draw_tracking_result()
        except Exception as e:
            continue

def receive_count_results():
    counting_consumer = KafkaConsumer('count_results')

    MAX_FRAME = 100

    visualize = Visualize(MAX_FRAME)                        
    while True:
        msg = counting_consumer.consume()          
        if msg is None:
            try:
                visualize.draw_on_video(MAX_FRAME)              # Change value according to Max_Frame at line 524 and 528 
                continue
            except Exception as e:
                print(e)
        
        try:
            visualize.draw_counting_effect(msg.value())
            visualize.get_frame_info_dict(msg.value())
            visualize.draw_on_video(MAX_FRAME)                  # Change value according to Max_Frame at line 524 and 528 
        except Exception as e:
            print(e)
            continue

def process(video_id):
    global video_list

    start_time = time.time()

    producer = KafkaProducer('raw_frames')

    global MAX_FRAME 
    MAX_FRAME = 100

    video_id, q, frame_id, current_frame, _ = video_list[video_id]
    while frame_id[0] < MAX_FRAME:
        if q.empty(): continue
        frame = q.get()

        frame_id[0] += 1

        detect = frame_id[0] % 1 == 0

        current_frame[0] = frame

        if detect:
            image_path = '/storage/{}_{:05d}.jpg'.format(video_id, frame_id[0])
            PNAT = '/home/{}_{:05d}.jpg'.format(video_id, frame_id[0])
            cv2.imwrite(image_path, frame)
            # cv2.imwrite(PNAT, frame)
            value = {"frame_id": frame_id[0], "url": image_path}

            producer.produce(key=video_id, value=value)
            # producer.flush()

    producer.flush()
    print("io time:", time.time() - start_time, flush=True)
    print("Processed {} frames".format(sum([x[2][0] for x in video_list])))
    print("Processing time:", time.time() - start_time)


##Socket graph
pusher = Pusher(
    app_id="1307595",
    key="5fcda7fc431248b78bb1",
    secret="e410fc2100dc881873dd",
    cluster="ap1",
    ssl=True
)
app = Flask(__name__)

times, moto, car, bus, truck = [], [], [], [], []
times2, moto2, car2, bus2, truck2 = [], [], [], [], []
choice_graph = "cam_02"
start = time.time()

count_result = {x[0]: 0 for x in video_list}
count_result_ema = {x[0]: 0 for x in video_list}
graph = {x[0]: ([], [], [], [], [], [go.Figure()]) for x in video_list}

graph_update = 0


def retrieve_data():
    global graph_update, graph
    graph_update += 1
    if graph_update % 5 == 1:
        for x in video_list:
            graph_ = graph[x[0]]
            graph_[0].append(time.strftime('%H:%M:%S'))
            # graph_[1].append(random.randint(20,50))
            # graph_[2].append(random.randint(10,20))
            # graph_[3].append(random.randint(5,15))
            # graph_[4].append(random.randint(5,15))
            # count_result[x[0]] = count_result[x[0]] * 1.15
            if count_result_ema[x[0]] == 0:
                count_result_ema[x[0]] = count_result[x[0]]
            else:
                count_result_ema[x[0]] = count_result_ema[x[0]] * 0.9 + 0.1 * count_result[x[0]]
            graph_[1].append(int(np.random.normal(0.6, 0.1) * count_result[x[0]]))
            graph_[2].append(int(np.random.normal(0.2, 0.05) * count_result[x[0]]))
            graph_[3].append(int(np.random.normal(0.1, 0.02) * count_result[x[0]]))
            graph_[4].append(int(np.random.normal(0.1, 0.02) * count_result[x[0]]))
            count_result[x[0]] = 0
            if len(graph_[0]) > 8:
                graph_[0].pop(0)
                graph_[1].pop(0)
                graph_[2].pop(0)
                graph_[3].pop(0)
                graph_[4].pop(0)
            fig = graph_[5][0] = go.Figure()
            fig.add_trace(go.Scatter(x=graph_[0], y=graph_[4], stackgroup='one', name='truck'))  # fill down to xaxis
            fig.add_trace(go.Scatter(x=graph_[0], y=graph_[3], stackgroup='one', name='bus'))  # fill to trace0 y
            fig.add_trace(go.Scatter(x=graph_[0], y=graph_[2], stackgroup='one', name='car'))  # fill down to xaxis
            fig.add_trace(
                go.Scatter(x=graph_[0], y=graph_[1], stackgroup='one', name='motorbike'))  # fill down to xaxis
            fig.update_yaxes(range=[0, 110])

    print(choice_graph, flush=True)
    graphJSON = json.dumps(graph[choice_graph][5][0], cls=plotly.utils.PlotlyJSONEncoder)

    data = {
        'graph': graphJSON,
    }

    pusher.trigger("crypto", "data-updated", data)


# @app.route('/check', methods=['GET', 'POST'])
# def check():
#     id = request.form['username']
#     print(id)
#     return "OK"

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/ajax', methods=['GET'])
def ajax_request():
    cam_id = request.args.get("cam_id")
    global choice_graph
    choice_graph = cam_id
    return 'OK'


def listen(ip):
    while True:
        cap = cv2.VideoCapture(f'/Videos/{ip}.mp4')
        count = 0
        while True:
            ret, frame = cap.read()
            if not ret: break
            count += 1
            # if count % 3 != 0:
            #     continue
            ###Back-end
            # draw_bbox(frame,bbox)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/stream/<ip>', methods=['GET'])
def stream(ip):
    return Response(listen(ip), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/thumbnail/<ip>/frame.jpg')
def thumbnail(ip):
    # cap = cv2.VideoCapture(f'./Videos/{ip}.mp4')
    # sleep(0.5)
    # ret,frame = cap.read()
    # cv2.imwrite(f'./feed/{ip}.jpg',frame)
    return send_file("feed/" + str(ip) + ".jpg", mimetype='image/jpg')


@app.route('/map')
def map():
    return send_file("feed/map/map.png", mimetype='image/jpg')


@app.route('/map_2')
def well_map():
    start_coords = [10.872989, 106.765281]
    folium_map = folium.Map(location=start_coords, zoom_start=20)
    return folium_map._repr_html_()


if __name__ == '__main__':
    create_topics()
    create_schema()

    # time.sleep(20)

    # Receive()

    thread_receive_stream = []
    # print(video_list)
    for i, _ in enumerate(video_list):
        thread_receive_stream.append(threading.Thread(target=receive_video_stream, args=[i]))

    # p2 = threading.Thread(target=receive_tracking)
    # p3 = threading.Thread(target=receive_counting)

    thread_process = []
    for i, _ in enumerate(video_list):
        thread_process.append(threading.Thread(target=process, args=[i]))

    for thread in thread_receive_stream:
        thread.start()

    for thread in thread_process:
        thread.start()


    # thread = threading.Thread(target=receive_detection_results)
    # thread.start()

    thread = threading.Thread(target=receive_track_results)
    thread.start()

    thread = threading.Thread(target=receive_count_results)
    thread.start()

    # retrieve_data()

    # print('ready', flush=True)

    # create schedule for retrieving prices
    scheduler = BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(
        func=retrieve_data,
        trigger=IntervalTrigger(seconds=2),
        id='prices_retrieval_job',
        name='Retrieve prices every 10 seconds',
        replace_existing=False)
    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
    app.run(host='0.0.0.0', port=8000)

    for thread in thread_receive_stream:
        thread.join()