ARG FROM_IMG
FROM ${FROM_IMG}

# upgrade pip to latest
RUN pip3 install --upgrade pip

# install skaimsginterface as a python package
COPY msg_interface/package /root/skaimsginterface_package
RUN cd /root/skaimsginterface_package && ./install_skaimsginterface.sh

# install requirements.txt
COPY requirements.txt /root/requirements.txt
RUN cd /root &&  pip3 install -r requirements.txt && rm requirements.txt
