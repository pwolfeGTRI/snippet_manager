from SnippetGenerator import SnippetGenerator as snpg
import datetime
import logging
import argparse
import multiprocessing as mp
from skaimsginterface.skaimessages import *
from skaimsginterface.tcp import MultiportTcpListenerMP, TcpSenderMP
from pathlib import Path



class SnippetManager:
    logger = logging.getLogger(__name__)
    error_logger = logging.getLogger(f'{__name__}_errors')
    dateformat = '%Y-%m-%dT%H-%M-%SZ'
    mp4_dateformat = f'{dateformat}.mp4'
    camfolder_day_format = '%Y-%m-%d'
    current_day = datetime.datetime.now().strftime(camfolder_day_format)
    cam_folder_path = f'/var/skai/videos/{current_day}'

    def __init__(self, print_q) -> None:
        self.stop_event = mp.Event()
        self.print_q = print_q
        self.msg_q = mp.Queue()

        # start handler process
        self.start_handler()

        # start listener process
        self.ports = [7201]
        self.listener = MultiportTcpListenerMP(
            portlist=self.ports,
            multiport_callback_func=self.multiport_callback,
            print_q=self.print_q,
            recordfile=None,
            verbose=True
        )

    def start_handler(self):
        self.handle_proc = mp.Process(
            name=f'snip_mgr_em_msg_handler',
            target=self.handle_em_msgs,
            args=(
                self.stop_event,
                self.print_q,
                self.msg_q,
            )
        )
        self.handle_proc.daemon = True
        self.handle_proc.start()

    def stop(self):
        self.stop_event.set()
        self.listener.stop()

    @staticmethod
    def handle_em_msgs(stop_event, print_q, msg_q):
        ten_sec = datetime.timedelta(seconds=10)
        while not stop_event.is_set():
            if not msg_q.empty():
                msg = msg_q.get_nowait()
                

                #### tasks = SnippetManager.parse_em_msg(msg) ####
                # each entry is: [cam_folder, start_time, end_time, output_file]
                # event type, primary global id, event start time, event end time
                tasks = []

                # output folder naming (event primary_obj.global_id event_starttime event_endtime)
                event_start_time_dt = datetime.fromtimestamp(msg.event_starttime / 1e9)
                event_end_time_dt = datetime.fromtimestamp(msg.event_starttime / 1e9)
                event_start_time_str = event_start_time_dt.strftime(SnippetManager.dateformat)
                event_end_time_str = event_end_time_dt.strftime(SnippetManager.dateformat)
                output_folder = f"/snippets/{msg.primary_obj.global_id}_{event_start_time_str}_{event_end_time_str}"
                
                # create output folder exist ok
                Path(output_folder).mkdir(parents=True, exist_ok=True)
                
                camera_mac_strings = []
                for ctr in msg.camera_time_ranges:
                    mac_hex_str = SkaiMsg.convert_camera_id_to_mac_addr_string(ctr.camera_id).upper()
                    camera_mac_strings.append(mac_hex_str)
                    
                    start_time_dt = datetime.fromtimestamp(msg.event_starttime / 1e9)
                    end_time_dt = datetime.fromtimestamp(msg.event_starttime / 1e9)
                    start_time_str = start_time_dt.strftime(SnippetManager.dateformat)
                    end_time_str = end_time_dt.strftime(SnippetManager.dateformat)

                    duration = (end_time_dt - start_time_dt)
                    if duration < ten_sec:
                        end_time_dt = start_time_dt + ten_sec
                    
                    cam_folder = f"{SnippetManager.cam_folder_path}/{mac_hex_str}"
                    if Path(cam_folder).is_dir():
                        output_file = f"{output_folder}/{mac_hex_str}_{start_time_str}_{end_time_str}.mp4"
                        tasks.append([cam_folder, start_time_dt, end_time_dt, output_file])
                    else:
                        error_logger.exception(f'Not able to find folder {cam_folder}!!! not generating snippet for that cam')

                logger.info(f'got msg event: {msg.event} for cameras {camera_mac_strings} from {event_start_time_dt} to {event_end_time_dt}')
                

                for cam_folder, start_time, end_time, output_file in tasks:
                    snpg.generate_snippet_for_cam(cam_folder, start_time, end_time, output_file)

    def multiport_callback(self, data, server_address):
        try:
            msg_type, msg = SkaiMsg.unpack(data)
            if msg_type == SkaiMsg.MsgType.SKAI_EVENT:
                self.msg_q.put_nowait(msg)
        except Exception as e:
            logger.exception(e)

    def parse_em_msg(msg):
        return None, None, None, None


if __name__=='__main__':  
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
    
    # setup same format and file handler for both main and SnippetManager loggers
    log_format=logging.Formatter('%(asctime)s [%(levelname)8s] %(message)s')
    
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