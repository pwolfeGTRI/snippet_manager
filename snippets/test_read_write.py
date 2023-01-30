#!/usr/bin/env python3

import argparse
import numpy as np
import cv2


def test_read_write(input_file):
    
    output_file = 'test_out.mp4'
    # output_file = 'test_out.avi'

    # verify input file exists
    cap = cv2.VideoCapture(input_file)
    if not cap.isOpened():
        print(f'draw_bboxes input file {input_file} didn\'t open')
        return

    # get width/height/fps by reading first frame
    read_success, frame = cap.read()
    if not read_success:
        print('read first frame fail')
    frame_h, frame_w, frame_channels = frame.shape
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Define the codec and create VideoWriter object
    # fourcc = cv2.VideoWriter_fourcc(*'H264')
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    # fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_file, fourcc, fps, (frame_w,frame_h))
    print(f'opened output video {output_file} for bbox drawing: fps: {fps}, resolution: {frame_w} x {frame_h}')
    # out = cv2.VideoWriter('output.avi',fourcc, 20.0, (640,480))

    primary_object_color = (0, 255, 0) # bgr
    thickness = 2
    top = 200
    bottom = 400
    left = 500
    right = 600


    while(cap.isOpened()):
        if read_success:
            # frame = cv2.flip(frame,0)
            cv2.rectangle(frame, (left, top), (right, bottom), primary_object_color, thickness)

            # write the flipped frame
            out.write(frame)

            # cv2.imshow('frame',frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break
        else:
            break
        read_success, frame = cap.read()

    # Release everything if job is finished
    cap.release()
    out.release()
    # cv2.destroyAllWindows()



if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filepath')
    args = parser.parse_args()
    test_read_write(args.filepath)
    