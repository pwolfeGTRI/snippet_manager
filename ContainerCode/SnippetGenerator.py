#!/usr/bin/env python3
import os
# set audio driver before loading tracker cuz it uses pygame
os.environ['SDL_AUDIODRIVER'] = 'dsp'
from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.video.tools.tracking import autoTrack

import datetime
import logging
from dataclasses import dataclass


class SnippetGenerator:

    logger = logging.getLogger(__name__)
    error_logger = logging.getLogger(f'{__name__}_errors')
    dateformat = '%Y-%m-%dT%H-%M-%SZ'
    mp4_dateformat = f'{dateformat}.mp4'
    video_file_duration_sec = 10 * 60  # duration of the video files in the cam_folder
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
        pass
        final_snippet = cls.generate_snippet_for_cam(cam_folder=task.cam_folder,
                                                     start_time=task.start_time,
                                                     end_time=task.end_time,
                                                     output_file=None)

        # draw bboxes on it final clip before writing out if list is not empty
        cls.draw_bboxes(final_snippet, task)

        # write final video snippet to file
        cls.logger.info(f'now writing final snippet out to: {task.output_file}')
        final_snippet.write_videofile(task.output_file)
        cls.logger.info('==== finished video snippet generation ====')

    @classmethod
    def draw_bboxes(cls, snippet, task):
        """
        """
        if len(task.bboxes) == 0:
            cls.logger.warning('bboxes len is 0. returning original snippet')
            return snippet

        boxes_to_draw = []
        for bbox in task.bboxes:
            # report bbox timestamps outside start / end time range for the clip
            ts = cls.convert_protobuf_ts_to_utc_datetime(bbox.timestamp)
            if ts < task.start_time:
                printmsg = f'bbox ts {ts} < start time {task.start_time} not drawing...'
                cls.logger.warning(printmsg)
                continue
            if ts > task.end_time:
                printmsg = f'bbox ts {ts} > end time {task.end_time}. not drawing...'
                cls.logger.warning(printmsg)
                continue

            # otherwise save box as box to be drawn
            boxes_to_draw.append(bbox)
        
        # if no boxes to draw, then report and return original snippet
        if len(boxes_to_draw) == 0:
            printmsg = f'no boxes in time range to draw. returning original snippet'
            cls.logger.warning(printmsg)
            return snippet
        
        # otherwise continue to drawing process
        # TODO use autoTrack(clipl, pattern)
        # iterate through frame from 
        for frame in snippet.iter_frames():
            # frame is hxwxn numpy array 
            pass
        

        # return snippet with bboxes
        return snippet

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
        # vidfile_duration = cls.get_video_file_duration(cam_folder, t)
        #vidfile_duration  #min(vidfile_duration, cls.video_file_duration)
        current_dt_utc = datetime.datetime.now() + cls.convert2utc
        duration = current_dt_utc - t 
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
        if len(relevant_tds) == 1:
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
        # last_start_t, last_dur = mp4_start_times_and_durations[-1]
        # mp4_list_last_time = last_start_t + last_dur
        # if end_time > mp4_list_last_time:
        #     printmsg = f'end time {end_time} is greater than mp4 list last time {mp4_list_last_time}'
        #     cls.error_logger.exception(printmsg)
        #     raise Exception(printmsg)

        # assemble list of mp4 file (start_time, duration) tuples that
        # overlap the start_time to end_time range
        relevant_tds = cls.get_relevant_times_and_durations(mp4_start_times_and_durations, start_time, end_time)
        cls.logger.info(f'relevant start times for {t1_str} to {t2_str}:')
        [cls.logger.info(f'  {t} ({d})') for (t, d) in relevant_tds]

        # now assemble video snippet
        final_snippet = cls.assemble_video_snippet(cam_folder, relevant_tds, start_time, end_time)
        cls.logger.info(f'final snippet duration: {final_snippet.duration} sec')

        # write final video snippet to file if desired
        if output_file:
            cls.logger.info(f'now writing final snippet out to: {output_file}')
            final_snippet.write_videofile(output_file)
            cls.logger.info('==== finished video snippet generation ====')

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

    test_join_with_timestamps = True
    if test_join_with_timestamps:
        start_time = datetime.datetime(2023, 1, 19, 17, 9, 30)
        # start_time = datetime.datetime(2023, 1, 19, 16, 49, 20)
        end_time = start_time + datetime.timedelta(minutes=10, seconds=10)
        SnippetGenerator.generate_snippet_for_cam(
            cam_folder=testfolder,
            start_time=start_time,
            end_time=end_time,
            output_file=None  # 'final_snippet.mp4'
        )