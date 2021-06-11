# import glob
import sys
sys.path.append('gen-py')
# print("hi", glob.glob('../../thrift-0.14.1/lib/py/build/lib*'))
# sys.path.insert(0, glob.glob('../../thrift-0.14.1/lib/py/build/lib*')[0])

from social_network import ComposePostService
# from ComposePostService import *

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

## For Jaeger
from jaeger_client import Config
import opentracing
from opentracing.propagation import Format

def log(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def set_up_tracer(config_file_path, service):
    ## TODO: Properly read YAML config
    config = Config(
        config={
            # 'disabled': False,
            ## For some reason, the yaml looks different for C++ and python...
            # 'reporter': {
                # 'logSpans': False,
                # 'localAgentHostPort': "jaeger-agent:6831",
                # 'queueSize': 1000000,
                # 'bufferFlushInterval': 10              
            # },
            'reporter_queue_size': 1000000,
            'reporter_flush_interval': 10,
            'sampler': {
                'type': "probabilistic",
                'param': 0.01
            },
            'enabled': True,
            ## TODO: Do we need this?
            # 'logging': True
        },
        service_name=service,
        validate=True
    )
    try:
        tracer = config.initialize_tracer()
        # return tracer
        ## TODO: Check if this is indeed done by the jaeger library
        # opentracing.set_global_tracer(tracer)
    except:
        log("WTF")
        exit(1)

class ComposePostHandler:
    def __init__(self):
        self.log = {}

    ## TODO: Regenerate the thrift files so that carrier is there
    def ComposePost(self, req_id, username, user_id,    
                    text, media_ids, media_types, post_type, carrier):
        log("Received request:", req_id, "from:", user_id)
        log("Carrier:", carrier)
        tracer = opentracing.global_tracer()
        log("Tracer:", tracer)
        ## Get the parent span
        parent_span_context = tracer.extract(format=Format.TEXT_MAP,
                                             carrier=carrier)
        log("ParentContext:", parent_span_context)
        with tracer.start_span(operation_name='compose_post_server', 
                               child_of=parent_span_context
                            #    references=[opentracing.child_of(parent_span_context)]
                               ) as span:
            span.log_kv({'event': 'test message', 'life': 42})

            # with tracer.start_span('ChildSpan', child_of=span) as child_span:
            #     child_span.log_kv({'event': 'down below'})
        # tracer.close()
        return


## TODO: Before making the tracer work we can do with logging, no problem.


if __name__ == '__main__':
    ## TODO: Sigint handler
    ## TODO: Logger (probably not necessary)
    
    ## Setup Tracer
    ## TODO: Properly set up tracer to find the parent span yada yada
    set_up_tracer("TODO", 'compose-post-service')

    ## TODO: Load the config file
    port = 9090

    handler = ComposePostHandler()
    processor = ComposePostService.Processor(handler)
    transport = TSocket.TServerSocket(host='0.0.0.0', port=port)
    tfactory = TTransport.TFramedTransportFactory()
    pfactory = TBinaryProtocol.TBinaryProtocolFactory()

    server = TServer.TSimpleServer(processor, transport, tfactory, pfactory)

    # You could do one of these for a multithreaded server
    # server = TServer.TThreadedServer(
    #     processor, transport, tfactory, pfactory)
    # server = TServer.TThreadPoolServer(
    #     processor, transport, tfactory, pfactory)

    log('Starting the compose-post-service server...')
    server.serve()
    log('done.')
