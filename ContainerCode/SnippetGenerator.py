#!/usr/bin/env python3

import os
# # set audio driver before loading tracker cuz it uses pygame
# os.environ['SDL_AUDIODRIVER'] = 'dsp'
# from moviepy.video.tools.tracking import autoTrack

from moviepy.editor import VideoFileClip, concatenate_videoclips

import datetime
import logging
from dataclasses import dataclass

from pathlib import Path

import cv2


class SnippetGenerator:

    logger = logging.getLogger(__name__)
    error_logger = logging.getLogger(f'{__name__}_errors')
    dateformat = '%Y-%m-%dT%H-%M-%SZ'
    mp4_dateformat = f'{dateformat}.mp4'
    video_file_duration_sec = 5 * 60  # duration of the video files in the cam_folder
    video_file_duration = datetime.timedelta(seconds=video_file_duration_sec)
    convert2utc = datetime.timedelta(hours=5)

    @dataclass
    class Task:
        """Class for storing Snippet Generator task data"""
        cam_folder: str  # pathway on filesystem to camera mp4s
        start_time: datetime.datetime  # start time
        end_time: datetime.datetime  # end time
        output_file: str  # name of output file
        bboxes: list  # list of TimeRangeBBoxes to draw/interpolate

        def __str__(self):
            return self.output_file

    @classmethod
    def process_task(cls, task):
        """processes task data to make snippet, draw bboxes, etc
        Args:
            task: a SnippetGenerator.Task for storing task data
        """
        snippet = cls.generate_snippet_for_cam(cam_folder=task.cam_folder,
                                               start_time=task.start_time,
                                               end_time=task.end_time,
                                               output_file=task.output_file)

        # draw bboxes on it final clip before writing out if list is not empty
        bbox_output_file = f"{task.output_file.strip('.mp4')}_boxes.mp4"
        generate_bbox_video = True
        if generate_bbox_video:
            cls.draw_bboxes(task.output_file, task, bbox_output_file)

    @classmethod
    def create_tracker(cls, tracker_type=None):
        tracker_types = ['BOOSTING', 'MIL', 'KCF', 'TLD', 'MEDIANFLOW', 'GOTURN', 'MOSSE', 'CSRT']
        if tracker_type is None:
            tracker_type = 'BOOSTING'  # 'KCF'
        elif tracker_type not in tracker_types:
            printmsg = f'{tracker_type} not in tracker types {tracker_types}'
            cls.logger.error(printmsg)
            cls.error_logger.error(printmsg)

        if tracker_type == 'BOOSTING':
            return cv2.legacy.TrackerBoosting_create()
        elif tracker_type == 'MIL':
            return cv2.TrackerMIL_create()
        elif tracker_type == 'KCF':
            return cv2.TrackerKCF_create()
        elif tracker_type == 'TLD':
            return cv2.legacy.TrackerTLD_create()
        elif tracker_type == 'MEDIANFLOW':
            return cv2.legacy.TrackerMedianFlow_create()
        elif tracker_type == 'GOTURN':
            return cv2.TrackerGOTURN_create()
        elif tracker_type == 'MOSSE':
            return cv2.legacy.TrackerMOSSE_create()
        elif tracker_type == "CSRT":
            return cv2.TrackerCSRT_create()

    @classmethod
    def draw_bboxes(cls, input_file, task, output_file, interpolate=True, flip_bbox_xy=True) -> None:
        """
        """
        test_draw = False

        # verify boxes present
        if len(task.bboxes) == 0:
            cls.logger.warning('bboxes len is 0. not drawing')
            return

        # verify bboxes  within start / end time
        boxes_to_draw = []
        for bbox in task.bboxes:
            # report bbox timestamps outside start / end time range for the clip
            ts = cls.convert_protobuf_ts_to_utc_datetime(bbox.timestamp)
            if ts < task.start_time:
                printmsg = f'bbox ts {ts} < start time {task.start_time} not drawing...'
                cls.logger.warning(printmsg)
                continue
            if ts > task.end_time:
                printmsg = f'bbox ts {ts} > end time {task.end_time}. (start time is {task.start_time}) not drawing...'
                cls.logger.warning(printmsg)
                continue

            # otherwise save box as box to be drawn
            boxes_to_draw.append((ts, bbox.bboxes))

        # if no boxes to draw, then report and return original snippet
        if len(boxes_to_draw) == 0:
            printmsg = f'no boxes in time range to draw. returning original snippet'
            cls.logger.warning(printmsg)
            return

        # verify input file exists
        cap = cv2.VideoCapture(input_file)
        if not cap.isOpened():
            cls.logger.error(f'draw_bboxes input file {input_file} didn\'t open')
            return

        # get width/height/fps by reading first frame
        read_success, frame = cap.read()
        if not read_success:
            cls.logger.error(f'couldn\'t read frame for input file {input_file}')
            return
        frame_h, frame_w, frame_channels = frame.shape
        fps = cap.get(cv2.CAP_PROP_FPS)

        # verify can open output file for writing
        fourcc = cv2.VideoWriter_fourcc(*'avc1')  # avc1 is for h264
        out = cv2.VideoWriter(output_file, fourcc, fps, (frame_w, frame_h))
        cls.logger.info(f'opened video for bbox drawing: fps: {fps}, resolution: {frame_w} x {frame_h}')

        #### drawing process ####

        # rectangle settings
        primary_object_color = (0, 255, 0)  # bgr. draw in green
        associated_objects_colors = {}  # bgr
        thickness = 1

        tracked_boxes = {}
        mp4_name_spl = Path(input_file).name.split('_')
        date_str = '_'.join(mp4_name_spl[1:3])  # join date + start time to string with underscore inbetween
        vid_start_time = datetime.datetime.strptime(date_str, '%Y-%m-%d_T%H-%M-%S')  # get datetime from string

        read_fail_count = 0
        sequential_read_fail_limit = 4
        drew_new_box = False
        while cap.isOpened():
            # check previous read success, and read next frame
            if not read_success:
                read_fail_count += 1
                cls.logger.error(f'mp4 read fail. count={read_fail_count}')

                # if sequential fail limit exceeded then break
                if read_fail_count >= sequential_read_fail_limit:
                    break
                # otherwise read another frame and see if read_success at top of loop
                else:
                    read_success, frame = cap.read()
                    continue
            else:
                # on read success reset fail counter
                read_fail_count = 0

            #### alternative check. not needed
            # if cap.get(cv2.CV_CAP_PROP_POS_FRAMES) == cap.get(cv2.CV_CAP_PROP_FRAME_COUNT):
            # If the number of captured frames is equal to the total number of frames,
            # we stop
            # break

            if test_draw:
                #### drawing test fixed bbox and frame flip ####
                # flip frame as test and draw static bbox
                frame = cv2.flip(frame, 0)
                top = 200
                bottom = 400
                left = 500
                right = 600
                cv2.rectangle(frame, (left, top), (right, bottom), primary_object_color, thickness)
            else:
                # get time stamp based on milliseconds past start of video from opencv
                ms_elapsed = cap.get(cv2.CAP_PROP_POS_MSEC)
                frame_ts = vid_start_time + datetime.timedelta(milliseconds=ms_elapsed)
                # cls.logger.debug(f'got ms_elapsed: {ms_elapsed} and frame ts: {frame_ts}')

                # frame is hxwxn numpy array

                # get first boxes list to draw
                #   ts is datetime timestamp in utc
                #   bboxes is list of skaiproto.interaction.GlobalBBox
                ts, bboxes = boxes_to_draw[0]

                #### check if first bboxes ts  <= frame_ts to draw protobuf boxes ####
                if ts <= frame_ts:

                    # delete that first entry now
                    del boxes_to_draw[0]

                    # draw bboxes for this timestamp
                    for box in bboxes:
                        # draw bbox on frame
                        if flip_bbox_xy:
                            left = int(box.top * frame_w)
                            right = int(box.bottom * frame_w)
                            top = int(box.left * frame_h)
                            bottom = int(box.right * frame_h)
                            
                        else:
                            top, bottom = int(box.top * frame_h), int(box.bottom * frame_h)
                            left, right = int(box.left * frame_w), int(box.right * frame_w)

                        cls.logger.debug(f'rectangles ms_elapsed: {ms_elapsed} and frame ts: {frame_ts}')
                        cls.logger.debug(
                            f'drawing rectangle(tlbr pixels): {top}, {left}, {bottom}, {right} on frame...')
                        cv2.rectangle(frame, (left, top), (right, bottom), primary_object_color, thickness)
                        cls.logger.debug('rectangle draw success!')
                        drew_new_box = True

                        # init tracker on bbox if interpolating
                        if interpolate:
                            # init tracker with bbox pixels
                            x, y = left, top
                            w, h = right - left, bottom - top
                            tracked_boxes[box.global_id] = cls.create_tracker()
                            init_bbox = [x, y, w, h]
                            cls.logger.debug(f'init-ing tracker with bbox(x,y,w,h): {init_bbox}')
                            tracked_boxes[box.global_id].init(frame, init_bbox)

                #### otherwise use template matching to interpolate bboxes ####
                elif interpolate:
                    for global_id in tracked_boxes:
                        success, bbox = tracked_boxes[global_id].update(frame)
                        if success:
                            (x, y, w, h) = [int(v) for v in bbox]
                            tracker_bbox = [x, y, w, h]
                            # cls.logger.debug(f'drawing interpolated tracker bbox(x,y,w,h): {tracker_bbox}')
                            cv2.rectangle(frame, (x, y), (x + w, y + h), primary_object_color, thickness)
                        else:
                            printmsg = f'error in tracker'
                            cls.logger.error(printmsg)
                            cls.error_logger.error(printmsg)

            # save frame to output (only write bbox frames if not interpolating)
            if not interpolate:
                if drew_new_box:
                    drew_new_box = False
                    out.write(frame)
            else:
                out.write(frame)

            # read next frame
            read_success, frame = cap.read()

        # close out readers/writers
        cap.release()
        out.release()

        cls.logger.info('==== bbox writing done ====')

    @classmethod
    def draw_on_frame(frame, t):
        pass

    @classmethod
    def convert_protobuf_ts_to_utc_datetime(cls, protobuf_ts):
        return datetime.datetime.fromtimestamp(protobuf_ts / 1e9) + cls.convert2utc

    @classmethod
    def get_current_utc_datetime(cls):
        return datetime.datetime.now() + cls.convert2utc

    @staticmethod
    def join_mp4_file_list(file_list, output_file) -> None:
        """test function for joining mp4 file list together into single mp4
        Args:
            file_list (str): list of strings pointing to files on filepath to join
            output_file (str): name of output file 
        """
        video_clips = [VideoFileClip(f) for f in file_list]
        final_clip = concatenate_videoclips(video_clips)
        final_clip.write_videofile(output_file)

    @classmethod
    def get_mp4_start_time(cls, mp4_filename):
        """gets start time as datetime object based on mp4 file name"""
        return datetime.datetime.strptime(mp4_filename, cls.mp4_dateformat)

    @classmethod
    def get_video_file_duration(cls, cam_folder, start_time):
        """ get video file duration from cam folder and start time
        """
        filename = f'{start_time.strftime(cls.dateformat)}.mp4'
        filepath = f'{cam_folder}/{filename}'
        return datetime.timedelta(seconds=VideoFileClip(filepath).duration)

    @classmethod
    def get_mp4_start_times_and_durations(cls, cam_folder) -> list:
        """gets mp4 start times and druations from camera folder assuming dateformat='%Y-%m-%dT%H-%M-%SZ.mp4'
        
        Args:
            cam_folder (str): the camera folder in videomanager path with videos of dateformat mentioned above.
        
        Returns:
            mp4_start_times (list): returns a list of 
                                    tuples of (video_start_time, duration) 
                                    which are type (datetime.datetime, datetime.timedelta)
                                    representing the start time and duration of each mp4 video in the camera folder
        
        Raises:
            FileNotFoundError: if cam_folder doesn't exist on local path
            Exception: if cam_folder contains no valid mp4 files
        """
        # verify mp4 files in directory and spaced apart by video_file_duration_sec
        all_files = os.listdir(cam_folder)
        mp4_files = [f for f in all_files if f.endswith('.mp4')]
        if len(mp4_files) == 0:
            exception_msg = f'there are no mp4 files in directory: {cam_folder}'
            cls.error_logger.exception(exception_msg)
            raise Exception(exception_msg)

        # get 10 min video start times from mp4 file names
        cls.logger.debug(f'loading mp4 start times from folder {cam_folder}...')
        mp4_start_times = []
        for f in mp4_files:
            dt_object = cls.get_mp4_start_time(f)
            mp4_start_times.append(dt_object)

        # sort in chronological order
        mp4_start_times = sorted(mp4_start_times)

        # calc durations using time between start times
        mp4_start_times_and_durations = []
        if len(mp4_start_times) == 1:
            t = mp4_start_times[0]
        else:
            last_t = mp4_start_times[0]
            for t in mp4_start_times[1:]:
                duration = t - last_t
                mp4_start_times_and_durations.append((last_t, duration))
                last_t = t

        # last file duration based on min expected file duration vs reported
        vidfile_duration = cls.get_video_file_duration(cam_folder, t)
        current_dt_utc = datetime.datetime.now() + cls.convert2utc
        # duration = min(current_dt_utc - t, vidfile_duration)
        duration = current_dt_utc - t - datetime.timedelta(seconds=3)  #, vidfile_duration)
        mp4_start_times_and_durations.append((t, duration))

        # debug print and return
        cls.logger.debug('got these sorted mp4 start times & durations: ')
        [cls.logger.debug(f'    {t.strftime(cls.dateformat)} ({d})') for t, d in mp4_start_times_and_durations]

        return mp4_start_times_and_durations

    @classmethod
    def get_relevant_times_and_durations(cls, mp4_start_times_and_durations, start_time, end_time) -> list:
        """assemble list of mp4 file time/durations that overlap the start/end time range
        Args:
        Return:
        Raises:
        """

        # init vars
        relevant_tds = []
        found_start = False
        found_end = False
        cls.logger.debug(f'looking for start time {start_time}...')
        for t, d in mp4_start_times_and_durations:
            file_end_time = t + d
            t_range_info = f'{t} - {file_end_time} ({d})'
            if not found_start:
                if (start_time - t) < d:
                    found_start = True
                    cls.logger.debug(f'  found mp4 start time in: {t_range_info}')
                    cls.logger.debug(f'looking for end time {end_time}...')
                else:
                    cls.logger.debug(f'  start_time not found in: {t_range_info}')
                    continue

            if found_start and (not found_end):
                relevant_tds.append((t, d))
                if (end_time - t) < d:
                    cls.logger.debug(f'  found mp4 end time in: {t_range_info}')
                    found_end = True
                    break
                else:
                    cls.logger.debug(f'  end_time not found in: {t_range_info}')
            else:
                break

        return relevant_tds

    @classmethod
    def assemble_video_snippet(cls, cam_folder, relevant_tds, start_time, end_time):
        """assembles video snippet from start to end time using the relevant files in cam folder
        
        Args:
            cam_folder (str): camera folder path
            relevant_tds (list): list of tuples of (time, duration) of type (datetime.datetime, datetime.timedelta)
                representing start time of mp4 video file and duration based on next file start time
            start_time (datetime): snippet start time
            start_time (datetime): snippet end time

        Return:
            video_snippet (VideoFileClip): final assembled moviepy.editor.VideoFileClip snippet

        """
        t1_str = start_time.strftime(cls.dateformat)
        t2_str = end_time.strftime(cls.dateformat)
        duration = end_time - start_time

        cls.logger.debug(f'now assembling from {t1_str} to {t2_str} ({duration})')
        cls.logger.debug(f'  using:')
        [cls.logger.debug(f'    {t} - {t+d} ({d})') for t, d in relevant_tds]

        if len(relevant_tds) == 0:
            printmsg = f'wait why are you sending me empty list relevant time date ranges?!?!?!'
            cls.logger.error(printmsg)
            cls.error_logger.error(printmsg)
            return None
        elif len(relevant_tds) == 1:
            #### just do a subclip of first & only video
            first_file_time, first_duration = relevant_tds[0]
            first_file = f'{first_file_time.strftime(cls.dateformat)}.mp4'
            video = VideoFileClip(f'{cam_folder}/{first_file}')
            clip_start_t_sec = (start_time - first_file_time).total_seconds()
            clip_end_t_sec = (end_time - first_file_time).total_seconds()

            # return snippet
            return video.subclip(clip_start_t_sec, clip_end_t_sec)

        else:
            # get first and last video file names & start times
            first_file_time, first_duration = relevant_tds[0]
            last_file_time, last_duration = relevant_tds[-1]
            first_file = f'{first_file_time.strftime(cls.dateformat)}.mp4'
            last_file = f'{last_file_time.strftime(cls.dateformat)}.mp4'

            # make first video to clip from start_time until end
            first_video = VideoFileClip(f'{cam_folder}/{first_file}')
            clip_start_t_sec = (start_time - first_file_time).total_seconds()
            clip_end_t_sec = first_duration.total_seconds()
            first_clip = first_video.subclip(clip_start_t_sec, clip_end_t_sec)

            # make last clip from beginning to end_time
            last_video = VideoFileClip(f'{cam_folder}/{last_file}')
            clip_start_t_sec = 0
            clip_end_t_sec = (end_time - last_file_time).total_seconds()
            last_clip = last_video.subclip(clip_start_t_sec, clip_end_t_sec)

            # concatenate together for final snippet using any files inbetween
            # middle_videos will be empty list if len(releveant_files) == 2
            middle_videos = []
            for t, d in relevant_tds[1:-1]:
                filename = f'{t.strftime(cls.dateformat)}.mp4'
                filepath = f'{cam_folder}/{filename}'
                clip_start_t_sec = 0
                clip_end_t_sec = d.total_seconds()
                middle_videos.append(VideoFileClip(filepath).subclip(clip_start_t_sec, clip_end_t_sec))

            clip_list = [first_clip, *middle_videos, last_clip]
            cls.logger.debug('clip_list durations:')
            [cls.logger.debug(f'  {v.duration} sec') for v in clip_list]
            return concatenate_videoclips(clip_list)

    @classmethod
    def generate_snippet_for_cam(cls, cam_folder, start_time, end_time, output_file=None) -> str:
        # take in datetime objects
        t1_str = start_time.strftime(cls.dateformat)
        t2_str = end_time.strftime(cls.dateformat)
        cls.logger.info(f'creating snippet for cam folder {cam_folder}')
        cls.logger.info(f'  from {t1_str} to {t2_str}')
        cls.logger.info(f'  duration {end_time - start_time}')

        # verify end time is greater than start time
        if end_time < start_time:
            printmsg = f'start time {t1_str} is not less than end time {t2_str}. check your function inputs'
            cls.error_logger.exception(printmsg)
            raise Exception(printmsg)

        # get start times list in datetime format from cam folder
        mp4_start_times_and_durations = cls.get_mp4_start_times_and_durations(cam_folder)

        # verify start_time is not before first start time
        mp4_list_first_time = mp4_start_times_and_durations[0][0]
        if start_time < mp4_list_first_time:
            printmsg = f'start time {start_time} is less than mp4 list first time {mp4_list_first_time}'
            cls.error_logger.exception(printmsg)
            raise Exception(printmsg)

        last_start_t, last_dur = mp4_start_times_and_durations[-1]
        mp4_list_last_time = last_start_t + last_dur
        if end_time > mp4_list_last_time:
            printmsg = f'end time {end_time} is greater than mp4 list last time {mp4_list_last_time}'
            cls.error_logger.exception(printmsg)
            raise Exception(printmsg)

        # assemble list of mp4 file (start_time, duration) tuples that
        # overlap the start_time to end_time range
        relevant_tds = cls.get_relevant_times_and_durations(mp4_start_times_and_durations, start_time, end_time)
        cls.logger.info(f'relevant start times for {t1_str} to {t2_str}:')
        [cls.logger.info(f'  {t} ({d})') for (t, d) in relevant_tds]
        if len(relevant_tds) == 0:
            printmsg = f'no relevant video files found for time range!'
            cls.logger.error(printmsg)
            raise Exception(printmsg)

        # now assemble video snippet
        final_snippet = cls.assemble_video_snippet(cam_folder, relevant_tds, start_time, end_time)
        if final_snippet is None:
            printmsg = f'video snippet could not be assembled!'
            cls.logger.error(printmsg)
            cls.error_logger.error(printmsg)

        cls.logger.info(f'final snippet duration: {final_snippet.duration} sec')

        # write final video snippet to file if desired
        if output_file:
            cls.logger.info(f'now writing final snippet out to: {output_file}')
            final_snippet.write_videofile(output_file)
            cls.logger.info('==== finished video snippet writing ====')

        # return final snippet
        return final_snippet


if __name__ == '__main__':

    #### logger config ####

    # lowest_log_level = logging.INFO
    lowest_log_level = logging.DEBUG

    # setup logger for command line output and file output
    logger = logging.getLogger(__name__)
    logger.setLevel(lowest_log_level)

    # setup same format and file handler for both main and SnippetGenerator loggers
    log_format = logging.Formatter('%(asctime)s [%(levelname)8s] %(message)s')

    # file logging config
    fh = logging.FileHandler('/skailogs/snpm.log', mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(log_format)

    # stdout logging config
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(log_format)

    # attach handlers
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info('SnippetGeneration main test running...')

    # test video join
    testfolder = '/skaivideos/2023-01-19/B8A44F3C4792/'
    # testfolder = '/skaivideos/2023-01-19/'
    allfiles = os.listdir(testfolder)

    test_join_files = False
    if test_join_files:
        # try joining first 2 mp4 files
        mp4_files = [f'{testfolder}/{fname}' for fname in allfiles if fname.endswith('.mp4')]
        file_list = mp4_files[0:2]

        # test join
        SnippetGenerator.join_mp4_file_list(file_list, "./test_snippet.mp4")

    test_join_with_timestamps = False
    if test_join_with_timestamps:
        start_time = datetime.datetime(2023, 1, 19, 17, 9, 30)
        # start_time = datetime.datetime(2023, 1, 19, 16, 49, 20)
        # end_time = start_time + datetime.timedelta(minutes=10, seconds=10)
        end_time = start_time + datetime.timedelta(minutes=0, seconds=59)
        SnippetGenerator.generate_snippet_for_cam(
            cam_folder=testfolder,
            start_time=start_time,
            end_time=end_time,
            output_file=None  # 'final_snippet.mp4'
        )

    test_bbox_drawing = True
    if test_bbox_drawing:
        mp4_files = [f'{testfolder}/{fname}' for fname in allfiles if fname.endswith('.mp4')]
        test_file = mp4_files[2]

        logger.info(f'opening file {test_file}')
        cap = cv2.VideoCapture(test_file)

        frame_no = 0
        while (cap.isOpened()):
            frame_exists, curr_frame = cap.read()
            if frame_exists:
                ts_str = cap.get(cv2.CAP_PROP_POS_MSEC)
                logger.info(f'frame [{frame_no}]:  {ts_str}')
            else:
                break
            frame_no += 1

        cap.release()
