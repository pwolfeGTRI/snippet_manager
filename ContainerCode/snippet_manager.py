#!/usr/bin/env python3

import moviepy.editor as mpe
import os
import datetime
import logging

class SnippetManager:

    dateformat='%Y-%m-%dT%H-%M-%SZ'
    mp4_dateformat = f'{dateformat}.mp4'
    logger = logging.getLogger(__name__)

    @staticmethod
    def join_mp4_file_list(file_list, output_file) -> None:
        """test function for joining mp4 file list together into single mp4
        Args:
            file_list (str): list of strings pointing to files on filepath to join
            output_file (str): name of output file 
        """
        video_clips = [mpe.VideoFileClip(f) for f in file_list]
        final_clip = mpe.concatenate_videoclips(video_clips)
        final_clip.write_videofile(output_file)

    @staticmethod
    def extract_clip(input_file, start_time, end_time, output_file):
        video = mpe.VideoFileClip(input_file)
        snippet = video.subclip(start_time, end_time)
        snippet.write_videofile(output_file)

        # # Example usage
        # extract_clip("input.mp4", 10, 20, "output.mp4")

    @classmethod
    def get_mp4_start_times(cls, cam_folder) -> list:
        """gets mp4 start times from camera folder assuming dateformat='%Y-%m-%dT%H-%M-%SZ.mp4'
        
        Args:
            cam_folder (str): the camera folder in videomanager path with videos of dateformat mentioned above.
        
        Returns:
            mp4_start_times (list): returns a list of the video start times in that folder as datetime.datetime objects
        
        Raises:
            FileNotFoundError: if cam_folder doesn't exist on local path
            Exception: if cam_folder contains no valid mp4 files
        """
        # verify mp4 files in directory
        all_files = os.listdir(cam_folder)
        mp4_files = [f for f in all_files if f.endswith('.mp4')]
        if len(mp4_files) == 0:
            raise Exception(f'there are no mp4 files in directory: {cam_folder}')
        
        # get 10 min video start times from mp4 file names sorted in time order
        cls.logger.debug(f'loading mp4 start times from folder {cam_folder}...')
        mp4_start_times = []
        for f in mp4_files:
            dt_object = datetime.datetime.strptime(f, cls.mp4_dateformat)
            mp4_start_times.append(dt_object)
        mp4_start_times = sorted(mp4_start_times)
        cls.logger.debug('got these sorted mp4 start times: ')
        [cls.logger.debug(f'    {f.strftime(cls.dateformat)}') for f in mp4_start_times]
        return mp4_start_times

    @classmethod
    def get_relevant_video_files(cls, mp4_start_times, start_time, end_time) -> list:
        """assemble list of mp4 files that overlap the start/end time range
        """

        # formatted date strings for printing
        t1_str = start_time.strftime(cls.dateformat)
        t2_str = end_time.strftime(cls.dateformat)

        # init vars
        relevant_files = []
        found_start = False
        found_end = False
        ten_min = datetime.timedelta(minutes=10)
        cls.logger.debug(f'looking for start time file for {t1_str}...')
        for t in mp4_start_times:
            filename = f'{t.strftime(cls.dateformat)}.mp4'
            if not found_start:
                if start_time - t < ten_min:
                    found_start = True
                    relevant_files.append(filename)
                    cls.logger.debug(f'found start time in file: {filename}')
                    cls.logger.debug(f'looking for end time file for {t2_str}...')
                else:
                    cls.logger.debug(f'skipping file {filename}')
            elif not found_end:
                relevant_files.append(filename)
                if end_time - t < ten_min:
                    cls.logger.debug(f'found end time in file: {filename}')
                    found_end = True
                    break
            else:
                break

        return relevant_files

    @classmethod
    def assemble_video_snippet(cls, cam_folder, relevant_files, start_time, end_time):
        """assembles video snippet from start to end time using the relevant files in cam folder
        
        Args:
            cam_folder (str): camera folder path
            relevant_files (list): list of mp4 files (without camera folder path) ordered in time
            start_time (datetime): snippet start time
            start_time (datetime): snippet end time

        Return:
            video_snippet (mpe.VideoFileClip): final assembled moviepy.editor.VideoFileClip snippet

        """
        t1_str = start_time.strftime(cls.dateformat)
        t2_str = end_time.strftime(cls.dateformat)
        duration = end_time - start_time
        
        cls.logger.debug(f'now assembling from {t1_str} to {t2_str}')
        cls.logger.debug(f'  duration: {duration}')
        cls.logger.debug(f'  using files:')
        [ cls.logger.debug(f'    {f}') for f in relevant_files]
        
        if len(relevant_files) == 1:
            #### just do a subclip of first & only video
            first_file = relevant_files[0]
            file_start_time = datetime.datetime.strptime(first_file, cls.mp4_dateformat)
            
            video = mpe.VideoFileClip(f'{cam_folder}/{first_file}')
            clip_start_t_sec = (start_time - file_start_time).total_seconds()
            clip_end_t_sec = (end_time - file_start_time).total_seconds()

            # return snippet
            return video.subclip(clip_start_t_sec, clip_end_t_sec)
        
        else:
            # get first and last video file names & start times
            first_file, last_file = relevant_files[0], relevant_files[-1]

            # get video start time from file name
            first_file_time = datetime.datetime.strptime(first_file, f'{cls.dateformat}.mp4')
            last_file_time = datetime.datetime.strptime(last_file, f'{cls.dateformat}.mp4')
            
            # make first video to clip from start_time until end
            first_video = mpe.VideoFileClip(f'{cam_folder}/{first_file}')
            clip_start_t_sec = (start_time - first_file_time).total_seconds()
            ten_min_sec = 10 * 60
            first_clip = first_video.subclip(clip_start_t_sec, ten_min_sec)

            # make last clip from beginning to end_time
            last_video = mpe.VideoFileClip(f'{cam_folder}/{last_file}')
            clip_end_t_sec = (end_time - last_file_time).total_seconds()
            last_clip = last_video.subclip(0, clip_end_t_sec)

            # concatenate together for final snippet using any files inbetween
            # middle_videos will be empty list if len(releveant_files) == 2
            middle_videos = [mpe.VideoFileClip(f'{cam_folder}/{f}').subclip(0, ten_min_sec) for f in relevant_files[1:-1]]
            clip_list = [first_clip, *middle_videos, last_clip]
            logger.debug('clip_list durations:')
            [logger.debug(f'  {v.duration} sec') for v in clip_list]
            return mpe.concatenate_videoclips(clip_list)

    @classmethod
    def generate_snippet_for_cam(cls, cam_folder, start_time, end_time) -> str:
        # take in datetime objects
        t1_str = start_time.strftime(cls.dateformat)
        t2_str = end_time.strftime(cls.dateformat)
        cls.logger.info(f'creating snippet for cam folder {cam_folder}')
        cls.logger.info(f'  from {t1_str} to {t2_str}')
        cls.logger.info(f'  duration {end_time - start_time}')

        # verify end time is greater than start time
        if end_time < start_time:
            raise Exception(f'start time {t1_str} is not less than end time {t2_str}. check your function inputs')

        # get start times list in datetime format from cam folder
        mp4_start_times = cls.get_mp4_start_times(cam_folder)

        # assemble list of mp4 files that overlap the start/end time range
        relevant_files = cls.get_relevant_video_files(mp4_start_times, start_time, end_time)
        cls.logger.info(f'relevant file list for {t1_str} to {t2_str}:')
        [cls.logger.info(f'  {f}') for f in relevant_files]

        # now assemble video snippet
        final_snippet = cls.assemble_video_snippet(cam_folder, relevant_files, start_time, end_time)
        cls.logger.info(f'final snippet duration: {final_snippet.duration} sec')

        # write final video snippet to file
        output_file = 'final_snippet_out.mp4'
        cls.logger.info(f'now writing final snippet out to: {output_file}')
        final_snippet.write_videofile(output_file)
        cls.logger.info('==== finished video snippet generation ====')

if __name__=='__main__':
    
    #### logger config ####
    
    # lowest_log_level = logging.INFO
    lowest_log_level = logging.DEBUG

    # setup logger for command line output and file output
    logger = logging.getLogger(__name__)
    logger.setLevel(lowest_log_level)
    
    # setup same format and file handler for both main and SnippetManager loggers
    log_format=logging.Formatter('%(asctime)s [%(levelname)8s] %(message)s')
    
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
    
    # test msg
    logger.debug('debug msg!')
    logger.info('info msg!')

    # in future maybe actually use instance stuff for em listener. for now static methods
    snpm = SnippetManager()

    # test video join
    testfolder = '/skaivideos/2023-01-19/B8A44F3C4792/'
    # testfolder = '/skaivideos/2023-01-19/'
    allfiles = os.listdir(testfolder)
    
    test_join_files = False
    if test_join_files:
        # try joining first 2 mp4 files
        mp4_files = [ f'{testfolder}/{fname}' for fname in allfiles if fname.endswith('.mp4')]
        file_list = mp4_files[0:2] 
        
        # test join    
        snpm.join_mp4_file_list(file_list, "./test_snippet.mp4")

    test_join_with_timestamps = True
    if test_join_with_timestamps:
        start_time = datetime.datetime(2023, 1, 19, 17, 9, 30)
        end_time = start_time + datetime.timedelta(seconds=610)
        snpm.generate_snippet_for_cam(
            cam_folder=testfolder,
            start_time=start_time,
            end_time=end_time
        )