#!/usr/bin/env python3
from SnippetGenerator import SnippetGenerator as snpg
import SnippetGenerator
# import datetime
from datetime import timedelta, datetime
import logging
import argparse
import multiprocessing as mp
from skaimsginterface.skaimessages import *
from skaimsginterface.tcp import MultiportTcpListenerMP, TcpSenderMP
from pathlib import Path


class SnippetManager:
    logger = logging.getLogger(__name__)
    error_logger = logging.getLogger(f'{__name__}_errors')
    camfolder_day_format = '%Y-%m-%d'

    def __init__(self, print_q) -> None:
        self.stop_event = mp.Event()
        self.print_q = print_q
        self.msg_q = mp.Queue()

        # start handler process
        self.start_handler()

        # start listener process
        self.ports = [7201]
        self.listener = MultiportTcpListenerMP(portlist=self.ports,
                                               multiport_callback_func=self.multiport_callback,
                                               print_q=self.print_q,
                                               recordfile=None,
                                               verbose=True)

    def start_handler(self):
        self.handle_proc = mp.Process(name=f'snip_mgr_em_msg_handler',
                                      target=self.handle_em_msgs,
                                      args=(
                                          self.stop_event,
                                          self.print_q,
                                          self.msg_q,
                                      ))
        self.handle_proc.daemon = True
        self.handle_proc.start()

    def stop(self):
        self.stop_event.set()
        self.listener.stop()

    @staticmethod
    def handle_em_msgs(stop_event, print_q, msg_q):
        ten_sec = timedelta(seconds=10)
        five_sec = timedelta(seconds=10)
        logger = SnippetManager.logger
        error_logger = SnippetManager.error_logger
        while not stop_event.is_set():
            try:
                if not msg_q.empty():
                    msg = msg_q.get_nowait()

                    # continue if no camera time ranges in msg
                    if len(msg.camera_time_ranges) == 0:
                        printmsg = f'got msg type {msg.event} with cam time ranges list empty! not processing...'
                        logger.debug(printmsg)
                        error_logger.debug(printmsg)
                        continue

                    # output folder naming (event primary_obj.global_id event_starttime event_endtime)
                    event_start_time_dt = snpg.convert_protobuf_ts_to_utc_datetime(msg.event_starttime)
                    event_end_time_dt = snpg.convert_protobuf_ts_to_utc_datetime(msg.event_starttime)
                    date_str = event_start_time_dt.strftime('%Y-%m-%d')
                    event_start_time_str = event_start_time_dt.strftime('%H-%M-%S')
                    event_end_time_str = event_end_time_dt.strftime('%H-%M-%S')
                    output_folder = f"/snippets/{date_str}/E{msg.event}/ID{msg.primary_obj.global_id}/T{event_start_time_str}_T{event_end_time_str}_UTC"

                    # create output folder exist ok
                    Path(output_folder).mkdir(parents=True, exist_ok=True)

                    # input folder path based on day from event_start_time_dt (UTC time)
                    day_folder = event_start_time_dt.strftime(SnippetManager.camfolder_day_format)
                    cam_folder_path = f'/skaivideos/{day_folder}'

                    # each task is SnippetGenerator.Task(cam_folder, start_time, end_time, output_file, TimeRangeBBoxes)
                    tasks = []
                    camera_mac_strings = []
                    for ctr in msg.camera_time_ranges:
                        if ctr.camera_id is None:
                            printmsg = f'got missing camera id!'
                            logger.exception(printmsg)
                            error_logger.exception(printmsg)
                            continue
                        mac_hex_str = SkaiMsg.convert_camera_id_to_mac_addr_string(ctr.camera_id).upper()
                        mac_hex_str_no_colon = mac_hex_str.replace(':', '')
                        camera_mac_strings.append(mac_hex_str)

                        # convert ctr times to utc datetime objects
                        start_time_dt = snpg.convert_protobuf_ts_to_utc_datetime(ctr.start_timestamp)
                        end_time_dt = snpg.convert_protobuf_ts_to_utc_datetime(ctr.end_timestamp)
                        
                        # TODO: compare bbox timestamps to see if they're in range?

                        # check if duration is < 10 sec. if so move the start time back 5 sec
                        duration = (end_time_dt - start_time_dt)
                        if duration < ten_sec:
                            start_time_dt = start_time_dt - five_sec

                        # check if end time N sec of current time. if so delay N sec
                        N = 15
                        X = 10
                        current_dt_utc = snpg.get_current_utc_datetime()
                        cur_minus_X = current_dt_utc - timedelta(seconds=X)
                        if end_time_dt > cur_minus_X:
                            logger.info(f'got msg with end time {end_time_dt} > cur_t - 3 ({cur_minus_X}). delaying {N} seconds')
                            time.sleep(N)

                        # form strings for output file
                        date_str = start_time_dt.strftime('%Y-%m-%d')
                        start_time_str = start_time_dt.strftime('%H-%M-%S')
                        end_time_str = end_time_dt.strftime('%H-%M-%S')

                        cam_folder = f"{cam_folder_path}/{mac_hex_str_no_colon}"
                        if Path(cam_folder).is_dir():
                            output_file = f"{output_folder}/{mac_hex_str_no_colon}_{date_str}_T{start_time_str}_T{end_time_str}_UTC.mp4"
                            # tasks.append([cam_folder, start_time_dt, end_time_dt, output_file])
                            tasks.append(
                                snpg.Task(cam_folder, start_time_dt, end_time_dt, output_file, ctr.tr_boxes))
                        else:
                            error_logger.exception(
                                f'Not able to find folder {cam_folder}!!! not generating snippet for that cam')

                    logger.info(
                        f'got msg event: {msg.event} for cameras {camera_mac_strings} from {event_start_time_dt} to {event_end_time_dt}'
                    )
                    logger.info(f'tasks: {len(tasks)}')

                    # for cam_folder, start_time, end_time, output_file in tasks:
                    #     logger.info(f'generating snippet for {cam_folder} {start_time} {end_time} {output_file}')
                    #     snpg.generate_snippet_for_cam(cam_folder, start_time, end_time, output_file)
                    #     logger.info('done')
                    for t in tasks:
                        logger.info(f'generating snippet for {t}')
                        snpg.process_task(t)
                        logger.info('done')
            except Exception as e:
                logger.exception(e)
                error_logger.exception(e)

    def multiport_callback(self, data, server_address):
        try:
            msg_type, msg = SkaiMsg.unpack(data)
            if msg_type == SkaiMsg.MsgType.SKAI_EVENT:
                self.msg_q.put_nowait(msg)
        except Exception as e:
            logger.exception(e)


if __name__ == '__main__':
    #### argparse config ####
    parser = argparse.ArgumentParser()
    # parser.add_argument()
    args = parser.parse_args()

    #### logger config ####
    # lowest_log_level = logging.INFO
    lowest_log_level = logging.DEBUG

    # setup loggers for command line output and file output
    logger = logging.getLogger(__name__)
    logger.setLevel(lowest_log_level)

    error_logger = logging.getLogger(f'{__name__}_errors')
    error_logger.setLevel(logging.DEBUG)

    sg_logger = logging.getLogger(SnippetGenerator.__name__)
    sg_logger.setLevel(lowest_log_level)

    sg_error_logger = logging.getLogger(f'{SnippetGenerator.__name__}_errors')
    sg_error_logger.setLevel(lowest_log_level)

    # setup same format and file handler for both main and SnippetManager loggers
    log_format = logging.Formatter('%(asctime)s [%(levelname)8s] %(message)s')

    # file logging config
    fh = logging.FileHandler('/skailogs/snpm.log', mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(log_format)

    error_fh = logging.FileHandler('/skailogs/snpm_errors.log', mode='w')
    error_fh.setLevel(logging.DEBUG)
    error_fh.setFormatter(log_format)

    # stdout logging config
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(log_format)

    # attach handlers
    logger.addHandler(fh)
    logger.addHandler(ch)
    error_logger.addHandler(error_fh)
    error_logger.addHandler(ch)
    sg_logger.addHandler(fh)
    sg_logger.addHandler(ch)
    sg_error_logger.addHandler(error_fh)
    sg_error_logger.addHandler(ch)

    # init messages
    logger.info('==== Snippet Manager Logger Started ====')
    error_logger.info('==== Snippet Manager Error Logger Started ====')
    sg_logger.info('==== Snippet Generator Logger Started ====')

    #### Snippet Manager setup ####
    print_q = mp.Queue()
    snp_mgr = SnippetManager(print_q)
    logger.info('Snippet Manager started!')

    #### stay active until ctrl+c input ####
    try:
        while True:
            if not print_q.empty():
                logger.info(print_q.get_nowait())
            time.sleep(0.0000001)
    except KeyboardInterrupt:
        logger.info('snippet manager got keyboard interrupt!')
    finally:
        logger.info('stopping snippet manager...')
        snp_mgr.stop()