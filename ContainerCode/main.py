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

    def __init__(self, print_q) -> None:
        self.stop_event = mp.Event()
        self.print_q = print_q
        self.msg_q = mp.Queue()

        # start handler process
        self.start_handler()

        # start listener process
        self.ports = [7200]
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
        while not stop_event.is_set():
            if not msg_q.empty():
                msg = msg_q.get_nowait()
                
                # TODO actually parse and feed into snippet generator
                # cam_folder, start_time, end_time, output_file = SnippetManager.parse_em_msg(msg)
                # snpg.generate_snippet_for_cam(cam_folder, start_time,end_time,output_file)

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