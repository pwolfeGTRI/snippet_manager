#!/usr/bin/env python3

import moviepy.editor as mpe
import os
import datetime
import logging

class SnippetManager:

    dateformat='%Y-%m-%dT%H-%M-%SZ'
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
            dt_object = datetime.datetime.strptime(f, f'{cls.dateformat}.mp4')
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
        


        pass

    @classmethod
    def generate_snippet_for_cam(cls, cam_folder, start_time, end_time) -> str:
        # take in datetime objects
        t1_str = start_time.strftime(cls.dateformat)
        t2_str = end_time.strftime(cls.dateformat)
        cls.logger.info(f'\ncreating snippet for cam folder {cam_folder}\n  from {t1_str} to {t2_str}\n')

        # verify end time is greater than start time
        if end_time < start_time:
            raise Exception(f'start time {t1_str} is not less than end time {t2_str}. check your function inputs')

        # get start times list in datetime format from cam folder
        mp4_start_times = cls.get_mp4_start_times(cam_folder)

        # assemble list of mp4 files that overlap the start/end time range
        relevant_files = cls.get_relevant_video_files(mp4_start_times, start_time, end_time)
        cls.logger.info(f'relevant file list for {t1_str} to {t2_str}:')
        [cls.logger.info(f'  {f}') for f in relevant_files]
        cls.logger.info()

        # now assemble video snippet



if __name__=='__main__':
    # main logger
    logger = logging.getLogger(__name__)
    
    #### config loggers ####
    # setup same format and file handler for both main and SnippetManager loggers
    log_format=logging.Formatter('%(asctime)s [%(levelname)8s] %(message)s')
    fh = logging.FileHandler('/skailogs/snpm.log')
    fh.setLevel(logging.INFO)

    logger.setLevel(logging.INFO)
    SnippetManager.logger.setLevel(logging.DEBUG)
    


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
        end_time = start_time + datetime.timedelta(minutes=20)
        snpm.generate_snippet_for_cam(
            cam_folder=testfolder,
            start_time=start_time,
            end_time=end_time
        )