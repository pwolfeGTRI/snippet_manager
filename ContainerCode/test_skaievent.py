#!/usr/bin/python3
import time
from pathlib import Path
from argparse import ArgumentParser

from skaimsginterface.skaimessages import *
from skaimsginterface.tcp import TcpSender
from skaimsginterface.udp import UdpSender


def create_example_skaievent(num_cams=3):
    msg = SkaiEventMsg.new_msg()

    fake_primary_global_id = [42]
    fake_assoc_global_id = [69]
    fake_veh_assoc_global_id = [10]
    all_ids = [*fake_primary_global_id, *fake_assoc_global_id, *fake_veh_assoc_global_id]
    num_ids = 3

    event_length = 120 # seconds
    video_clip_length = 30 #seconds
    num_frames_in_clip = 5

    timestamp = int(time.time() * 1e9)  # integer version of double * 1e9
    initial_event_timestamp = timestamp - int(event_length * 1e9)

    initial_clip_timestamp = timestamp - int(video_clip_length * 1e9)
    clip_timestamps = np.linspace(initial_clip_timestamp, timestamp, num_frames_in_clip)

    example_location_tags = ['showroom', 'front_desk']
    example_employee_tags = ['elite_janitor_vp', 'associate_to_the_regional_manager']
    example_customer_tags = ['vip_customer']
    example_vehicle_tags = ['1234567', 'blue sedan']
    
    camera_mac = '00:10:FA:66:42:11'
    camera_id = SkaiMsg.convert_mac_addr_to_camera_identifier_number(camera_mac)
    fake_camera_ids = list(range(num_cams))
    for cam_count in range(num_cams):
        fake_camera_ids[cam_count] = (camera_id + cam_count)
    example_event_confidence = 0.80
    fake_tlbr_box = [0.2, 0.2, 0.2, 0.2]

    msg.event = 3 #customer greeting
    msg.confidence = example_event_confidence
    msg.event_starttime = initial_event_timestamp
    msg.event_endtime = timestamp
    msg.location_tags.extend(example_location_tags)

    msg.primary_obj.global_id = fake_primary_global_id[0]
    msg.primary_obj.classification = SkaiMsg.CLASSIFICATION.CUSTOMER
    msg.primary_obj.confidence = example_event_confidence # is this needed?
    msg.primary_obj.object_tags.extend(example_customer_tags)

    associated_obj = msg.associated_objs.add()
    associated_obj.global_id = fake_assoc_global_id[0]
    associated_obj.classification = SkaiMsg.CLASSIFICATION.EMPLOYEE
    associated_obj.confidence = example_event_confidence
    associated_obj.object_tags.extend(example_employee_tags)

    associated_obj = msg.associated_objs.add()
    associated_obj.global_id = fake_veh_assoc_global_id[0]
    associated_obj.classification = SkaiMsg.CLASSIFICATION.VEHICLE
    associated_obj.confidence = example_event_confidence
    associated_obj.object_tags.extend(example_vehicle_tags)

    for cam_count in range(num_cams):
        camera_time_range = msg.camera_time_ranges.add()
        camera_time_range.camera_id = fake_camera_ids[cam_count]
        camera_time_range.start_timestamp = initial_clip_timestamp
        camera_time_range.end_timestamp = timestamp

        for clip_timestamp in clip_timestamps:
            tr_bbox = camera_time_range.tr_boxes.add()
            tr_bbox.timestamp = int(clip_timestamp)
            for id_count in range(num_ids):
                global_bbox = tr_bbox.bboxes.add()
                global_bbox.global_id = all_ids[id_count]
                global_bbox.camera_id = fake_camera_ids[cam_count]
                global_bbox.top = fake_tlbr_box[0]
                global_bbox.left = fake_tlbr_box[1]
                global_bbox.bottom = fake_tlbr_box[2]
                global_bbox.right = fake_tlbr_box[3]

    return msg


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('udp_or_tcp', type=str,
                        help='protocol to listen on', choices=('tcp', 'udp'))
    parser.add_argument('--exampleout', help='dump an example message text file under a folder example_msg_prints',
                        nargs='?', type=bool, const=True, default=False)
    parser.add_argument(
        '--camgroup', help='camera group number (default 0)', nargs='?', type=int, default=0)
    args = parser.parse_args()

    msg = create_example_skaievent()
    # print(msg)

    # write example message to file for viewing
    if args.exampleout:
        filename = 'example_msg_prints/skaievent.txt'
        print(f'wrote example message to {filename}')
        p = Path(filename)
        p.parent.mkdir(exist_ok=True, parents=True)
        p.write_text(f'{msg}')

    msg_bytes = SkaiEventMsg.pack(msg, verbose=True)
    cam_group_idx = args.camgroup
    if args.udp_or_tcp == 'udp':
        sender = UdpSender(
            '127.0.0.1', SkaiEventMsg.ports[cam_group_idx], verbose=True)
    else:
        sender = TcpSender(
            '127.0.0.1', SkaiEventMsg.ports[cam_group_idx], verbose=True)
    sender.send(msg_bytes)
