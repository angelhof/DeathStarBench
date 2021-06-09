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

def log(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def set_up_tracer(config_file_path, service):
    ## TODO: Properly read YAML config
    config = Config(
        config={
            'disabled': False,
            'reporter': {
                'logSpans': False,
                'localAgentHostPort': "jaeger-agent:6831",
                'queueSize': 1000000,
                'bufferFlushInterval': 10              
            },
            'sampler': {
                'type': "probabilistic",
                'param': 0.01
            }
        },
        service_name=service
    )
    try:
        tracer = config.initialize_tracer()
        return tracer
    except:
        log("WTF")
        exit(1)

class ComposePostHandler:
    def __init__(self, tracer):
        self.log = {}
        self.tracer = tracer

    ## TODO: Regenerate the thrift files so that carrier is there
    def ComposePost(self, req_id, username, user_id,    
                    text, media_ids, media_types, post_type):
        tracer = self.tracer
        with tracer.start_span('TestSpan') as span:
            span.log_kv({'event': 'test message', 'life': 42})

            with tracer.start_span('ChildSpan', child_of=span) as child_span:
                child_span.log_kv({'event': 'down below'})
        tracer.close()
        return


if __name__ == '__main__':
    ## TODO: Sigint handler
    ## TODO: Logger (probably not necessary)
    
    ## Setup Tracer
    ## TODO: Properly set up tracer to find the parent span yada yada
    tracer = set_up_tracer("TODO", 'compose-post-service')

    ## TODO: Load the config file
    port = 9090

    handler = ComposePostHandler(tracer)
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
