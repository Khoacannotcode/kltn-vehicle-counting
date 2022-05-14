
# - This is a document for docker file in the detection module
# - If you want to build a docker image for module detection, you can run the command line:
# 	cd detection
# 		docker build -t <image_name> .
# - After that, you can run docker image into container. If you want to mount a folder into a docker container, 
# 	you must cd to that folder first and run the following command:
# 	docker run -it --name <container_name> -v $(pwd):/src <image_name> /bin/bash


# YOLOv5 🚀 by Ultralytics, GPL-3.0 license

# Start FROM Nvidia PyTorch image https://ngc.nvidia.com/catalog/containers/nvidia:pytorch
FROM nvcr.io/nvidia/pytorch:21.10-py3
#(old Pytorch version)
#FROM nvcr.io/nvidia/pytorch:19.05-py3

# Install linux packages
RUN apt update && apt install -y zip htop screen libgl1-mesa-glx

# Install python dependencies
RUN python -m pip install --upgrade pip
RUN pip uninstall -y nvidia-tensorboard nvidia-tensorboard-plugin-dlprof
RUN pip install --no-cache -U numpy
COPY requirements.txt .
RUN apt-get install -y libglib2.0-0 libsm6 libxext6 libxrender-dev
RUN pip install --no-cache -r requirements.txt coremltools onnx gsutil notebook gdown
RUN pip install --no-cache torch==1.10.0+cu113 torchvision==0.11.1+cu113 torchaudio===0.10.0+cu113 -f https://download.pytorch.org/whl/cu113/torch_stable.html


# Create working directory
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN mkdir -p ./runs/train/day_5s/weights/ && \
    # curl -L -o './runs/train/day_5s/weights/best.pt' 'https://drive.google.com/u/0/uc?id=1-p35IWvT-U_zY9hhkKe09MA2f8AdjcMQ&export=download&confirm=t'
    #curl -L -o './runs/train/day_5s/weights/best.pt' 'https://drive.google.com/u/0/uc?id=1OsAxLpIvQxqa268Vmg3ZJ_g2Ow6LGt8w&export=download&confirm=t'
    gdown --id 1Y3kIOED-3ornSRZeLUj1rnIyFcKem0qE -O ./runs/train/day_5s/weights/best.pt
RUN mkdir -p ./runs/train/night_5s/weights/ && \
    gdown --id 1bxNyhKXoVTlfbWYWIAWEpj25rUV0Rgzw -O ./runs/train/night_5s/weights/best.pt
    
    
    

# Copy contents
COPY . /usr/src/app

# Set environment variables
ENV HOME=/usr/src/app


CMD python3 service.py


# Usage Examples -------------------------------------------------------------------------------------------------------

# Build and Push
# t=ultralytics/yolov5:latest && sudo docker build -t $t . && sudo docker push $t

# Pull and Run
# t=ultralytics/yolov5:latest && sudo docker pull $t && sudo docker run -it --ipc=host --gpus all $t

# Pull and Run with local directory access
# t=ultralytics/yolov5:latest && sudo docker pull $t && sudo docker run -it --ipc=host --gpus all -v "$(pwd)"/datasets:/usr/src/datasets $t

# Kill all
# sudo docker kill $(sudo docker ps -q)

# Kill all image-based
# sudo docker kill $(sudo docker ps -qa --filter ancestor=ultralytics/yolov5:latest)

# Bash into running container
# sudo docker exec -it 5a9b5863d93d bash

# Bash into stopped container
# id=$(sudo docker ps -qa) && sudo docker start $id && sudo docker exec -it $id bash

# Clean up
# docker system prune -a --volumes
