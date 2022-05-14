import json
import numpy as np
from similaritymeasures import frechet_dist

from kafka_messenger import KafkaProducer, KafkaConsumer

MOI_json = {}
MOIs = {}

for video_id in range(1, 26):
    video_id = 'cam_{:02d}'.format(video_id)
    MOI_json[video_id] = json.load(open('moi_config/{}.json'.format(video_id)))
    MOIs[video_id] = [(MOI['shape_attributes']['all_points_x'], MOI['shape_attributes']['all_points_y'])
                for MOI in MOI_json[video_id]]
    MOIs[video_id] = [list(zip(MOI[0],MOI[1])) for MOI in MOIs[video_id]]
 

if __name__ == '__main__':
    consumer = KafkaConsumer('track_results')
    producer = KafkaProducer('count_results')
    while True:
        msg = consumer.consume()

        if msg is None:
            continue

        video_id = msg.key()
        value = msg.value()

        track_id = value['track_id']
        bbox = value['bbox']
        classes = value['class']
        frame_id = value['frame_id']

        track = [((bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2) for bb in bbox]

        try:
            moi_id = np.argmin([frechet_dist(track, MOI) for MOI in MOIs[video_id]])
        except:
            pass 
        
        if len(frame_id) <= 25:
            continue
        else:
            value = {            
                'track_id': track_id,
                'frame_id': frame_id,
                'bbox': bbox,
                'class' : classes,
                'moi_id': moi_id
            }
            producer.produce(
                key=video_id, 
                value=value
            )

        
