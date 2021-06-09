FROM yg397/thrift-microservice-deps:xenial

ARG NUM_CPUS=1

## Download python and the latest pip (downloading with sudo apt doesn't work)
RUN apt update
RUN apt install curl
RUN apt install -y python3
RUN curl https://bootstrap.pypa.io/pip/3.5/get-pip.py -o get-pip.py
RUN python3 get-pip.py 
RUN python3 -m pip install --upgrade pip

## For the thrift python bindings
RUN python3 -m pip install thrift
## For the jaeger python bindings
RUN python3 -m pip install jaeger-client


COPY ./ /social-network-microservices
# RUN cd /social-network-microservices \
#     && mkdir -p build \
#     && cd build \
#     && cmake -DCMAKE_BUILD_TYPE=Debug .. \
#     && make -j${NUM_CPUS} \
#     && make install


WORKDIR /social-network-microservices