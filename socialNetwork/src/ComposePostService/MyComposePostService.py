# import glob
import sys
sys.path.append('gen-py')
# print("hi", glob.glob('../../thrift-0.14.1/lib/py/build/lib*'))
# sys.path.insert(0, glob.glob('../../thrift-0.14.1/lib/py/build/lib*')[0])

from concurrent.futures import ThreadPoolExecutor

from social_network import ComposePostService, TextService, UserService
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
    def __init__(self, 
                 text_service_client,
                 user_service_client):
        self.log = {}
        self.text_service_client = text_service_client
        self.user_service_client = user_service_client

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

            ## Inject a new span to the global tracer so that it
            ## can be extracted and found from the helper functions.
            ## 
            ## TODO: Is my understanding correct here?
            writer_text_map = {}
            tracer.inject(
                span_context=span.context,
                format=Format.TEXT_MAP,
                carrier=writer_text_map
            )

            ## Setup the async futures executor
            ## TODO: Read that from some config file
            max_workers = 2
            with ThreadPoolExecutor(max_workers=2) as executor:
                ## Call the ComposeTextHelper
                text_result_future = executor.submit(self._ComposeTextHelper, req_id, text, writer_text_map)

                ## Call the creator id service
                creator_future = executor.submit(self._ComposeCreaterHelper, req_id, user_id, username, carrier)

                text = text_result_future.result()
                ## Old invocation without futures
                # text = self._ComposeTextHelper(req_id, text, writer_text_map)
                # log("Text returned:", text)

                creator = creator_future.result()
                # log("Creator returned:", creator)


        return

    def _ComposeTextHelper(self, req_id, text, carrier):
        tracer = opentracing.global_tracer()

        ## Create a new span here.
        parent_span_context = tracer.extract(format=Format.TEXT_MAP,
                                             carrier=carrier)
        
        with tracer.start_span(operation_name='compose_text_client', 
                               child_of=parent_span_context) as span:

            writer_text_map = {}
            tracer.inject(
                span_context=span.context,
                format=Format.TEXT_MAP,
                carrier=writer_text_map
            )

            ## TODO: Do we maybe need to connect to the transport here?

            ## TODO: What kind of errors to we need to catch here?
            client = self.text_service_client
            return_text = client.ComposeText(req_id, text, writer_text_map)

        return return_text

    def _ComposeCreaterHelper(self, req_id, user_id, username, carrier):
        tracer = opentracing.global_tracer()

        ## Create a new span here.
        parent_span_context = tracer.extract(format=Format.TEXT_MAP,
                                             carrier=carrier)
        
        with tracer.start_span(operation_name='compose_creator_client', 
                               child_of=parent_span_context) as span:

            writer_text_map = {}
            tracer.inject(
                span_context=span.context,
                format=Format.TEXT_MAP,
                carrier=writer_text_map
            )

            ## TODO: Do we maybe need to connect to the transport here?

            ## TODO: What kind of errors to we need to catch here?
            client = self.user_service_client
            return_creator = client.ComposeCreatorWithUserId(req_id, user_id, username, writer_text_map)

        return return_creator




## TODO: Before making the tracer work we can do with logging, no problem.


## TODO: Refactor both this and the helper
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

def UserServiceClient():
    ## TODO: Get those from the config file
    user_service_port = 9090
    user_service_addr = "user-service"
    ## Setup the socket
    transport = TSocket.TSocket(host=user_service_addr,
                                port=user_service_port)
    ## Configure the transport layer to correspond to the expected transport
    transport = TTransport.TFramedTransport(transport)

    ## Configure the protocol to be binary as expected from the service
    protocol = TBinaryProtocol.TBinaryProtocol(transport)

    ## Create the client
    client = UserService.Client(protocol)

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

    ## Set up clients
    text_service_client = TextServiceClient()
    user_service_client = UserServiceClient()

    handler = ComposePostHandler(text_service_client,
                                 user_service_client)
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
