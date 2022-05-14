import json
import numpy as np
from sort import Sort

from kafka_messenger import KafkaProducer, KafkaConsumer

trackers = {}
active_tracks = {}

if __name__ == '__main__':
    consumer = KafkaConsumer('det_results')
    producer_tracks = KafkaProducer('track_results')
    producer_frames = KafkaProducer('track_frames')
    while True:
        msg = consumer.consume()

        if msg is None:
            continue

        video_id = msg.key()
        value = msg.value()

        frame_id = value['frame_id']

        if video_id not in trackers:
            # Create instance of the SORT tracker
            trackers[video_id] = Sort(
                max_age=5, 
                min_hits=1,
                iou_threshold=0.15
            )
            # Create tracks container
            active_tracks[video_id] = {}

        bbox    = np.array(value['bbox']).reshape(-1, 4)
        score   = np.array(value['score']).reshape(-1, 1)
        classes = np.array(value['class']).reshape(-1, 1)

        # bbox = [x1, y1, x2, y2, score, classes]
        tracks = trackers[video_id].update(np.hstack((bbox, score, classes))).astype(int).tolist() #List of trackid 
        track_list = active_tracks[video_id]
        for track in tracks:
            # track = [x1, y1, x2, y2, id, classes] 
            
            if track[-2] not in track_list:
                track_list[track[-2]] = {
                    'id': int(track[-2]),
                    'history': [],
                }
            track_list[track[-2]]['history'].append((track[:4], frame_id, track[-1]))   # append ([bbox], frame_id, class)

        # Produce result for each frame
        track_frames = [track[:4] for track in tracks]
        track_id = [track[4] for track in tracks]
        track_classes = [track[-1] for track in tracks]

        value = {
            'frame_id': frame_id,
            'bbox': track_frames,
            'track_id': track_id,
            'class': track_classes,
        }
        producer_frames.produce(
            key=video_id, 
            value=value
        )
        

        tracks = {track[-2] for track in tracks}    # This will return frame_id
        # tracks returns a dict of track_id

        for track_id in (set(track_list) - tracks):
            # set(track_list) - tracks -> history tracks that no longer actives
            track = track_list.pop(track_id)['history']

            bbox = [bb[0] for bb in track]
            frame_id = [bb[1] for bb in track]  
            classes = [bb[2] for bb in track]   # Class will get the first class that was detected !!need update a


        # Produce track results
            value = {
                'track_id': int(track_id),
                'bbox': bbox,
                'class': classes,
                'frame_id': frame_id,
            }

            producer_tracks.produce(
                key=video_id, 
                value=value
            )
