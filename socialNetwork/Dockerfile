FROM yg397/thrift-microservice-deps:xenial

ARG NUM_CPUS=1

## For python version of microservice
RUN apt install -y python3 python3-pip
RUN python3 -m pip install thrift


COPY ./ /social-network-microservices
# RUN cd /social-network-microservices \
#     && mkdir -p build \
#     && cd build \
#     && cmake -DCMAKE_BUILD_TYPE=Debug .. \
#     && make -j${NUM_CPUS} \
#     && make install


WORKDIR /social-network-microservices