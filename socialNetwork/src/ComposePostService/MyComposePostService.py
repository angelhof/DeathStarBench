# import glob
import sys
sys.path.append('gen-py')
# print("hi", glob.glob('../../thrift-0.14.1/lib/py/build/lib*'))
# sys.path.insert(0, glob.glob('../../thrift-0.14.1/lib/py/build/lib*')[0])

from social_network import ComposePostService, TextService
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
            'local_agent': {
                'reporting_host': 'jaeger-agent',
                'reporting_port': '6831',
            },
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
        ## Initialize the tracer and set the global opentracing tracer
        # opentracing.set_global_tracer(tracer)
        config.initialize_tracer()
    except:
        log("WTF")
        exit(1)

class ComposePostHandler:
    def __init__(self, text_service_client):
        self.log = {}
        self.text_service_client = text_service_client

    ## TODO: Regenerate the thrift files so that carrier is there
    def ComposePost(self, req_id, username, user_id,    
                    text, media_ids, media_types, post_type, carrier):
        log("Received request:", req_id, "from:", user_id)
        log("Carrier:", carrier)
        tracer = opentracing.global_tracer()
        # log("Tracer:", tracer)
        ## Get the parent span
        parent_span_context = tracer.extract(format=Format.TEXT_MAP,
                                             carrier=carrier)
        # log("ParentContext:", parent_span_context)
        with tracer.start_span(operation_name='compose_post_server', 
                               child_of=parent_span_context) as span:
            ## This was here just for debugging.
            # span.log_kv({'event': 'test message', 'life': 42})

            ## TODO: I am not sure what I need to do with this
            writer_text_map = {}

            ## TODO: Make a call to another service properly.
            self._ComposeTextHelper(req_id, text, span, writer_text_map)
        return

    def _ComposeTextHelper(self, req_id, text, span, carrier):
        client = self.text_service_client

        ## TODO: Do correct logging, tracing!

        ## TODO: Create a new span here.
        opentracing.global_tracer().inject(
            span_context=span.context,
            format=Format.TEXT_MAP,
            carrier=carrier
        )

        ## TODO: Do we maybe need to connect to the transport here?

        ## TODO: What kind of errors to we need to catch here?
        return_text = client.ComposeText(req_id, text, carrier)

        return return_text





## TODO: Before making the tracer work we can do with logging, no problem.


def TextServiceClient():
    ## TODO: Get those from the config file
    text_service_port = 9090
    text_service_addr = "text-service"
    ## Setup the socket
    transport = TSocket.TSocket(host=text_service_addr,
                                port=text_service_port)
    ## Configure the transport layer to correspond to the expected transport
    transport = TTransport.TFramedTransport(transport)

    ## Configure the protocol to be binary as expected from the service
    protocol = TBinaryProtocol.TBinaryProtocol(transport)

    ## Create the client
    client = TextService.Client(protocol)

    ## Connect to the client
    ## TODO: Understand what this does
    ## TODO: Where do we need to catch errors?
    transport.open()

    return client

if __name__ == '__main__':
    ## TODO: Sigint handler
    ## TODO: Logger (probably not necessary)
    
    ## Setup Tracer
    set_up_tracer("TODO", 'compose-post-service')

    ## TODO: Load the config file
    service_port = 9090

    text_service_client = TextServiceClient()

    handler = ComposePostHandler(text_service_client)
    processor = ComposePostService.Processor(handler)
    transport = TSocket.TServerSocket(host='0.0.0.0', port=service_port)
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
