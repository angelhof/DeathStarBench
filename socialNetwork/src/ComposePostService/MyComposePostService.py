# import glob
import sys
sys.path.append('gen-py')
# print("hi", glob.glob('../../thrift-0.14.1/lib/py/build/lib*'))
# sys.path.insert(0, glob.glob('../../thrift-0.14.1/lib/py/build/lib*')[0])

from concurrent.futures import ThreadPoolExecutor
import time

from social_network import ComposePostService, MediaService, TextService, UniqueIdService, UserService, ttypes
# from ComposePostService import *

from thrift.transport import TSocket, THttpClient
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol, TJSONProtocol
from thrift.server import TServer

## For Jaeger
from jaeger_client import Config
import opentracing
from opentracing.propagation import Format

def log(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def try_n_times(fn, attempts):
    for i in range(attempts):
        try:
            log("Attempt: i...", end='')
            ret = fn()
            log("SUCCESS")
            return ret
        except:
            log("FAIL")
            time.sleep(1)

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
                 user_service_client,
                 media_service_client,
                 unique_id_service_client):
        self.log = {}
        self.text_service_client = text_service_client
        self.user_service_client = user_service_client
        self.media_service_client = media_service_client
        self.unique_id_service_client = unique_id_service_client

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
            serialized_span_context = {}
            tracer.inject(
                span_context=span.context,
                format=Format.TEXT_MAP,
                carrier=serialized_span_context
            )

            ## Setup the async futures executor
            ## TODO: Read that from some config file
            max_workers = 2
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                ## Call the ComposeTextHelper
                text_client_fn = self.text_service_client.ComposeText
                text_result_future = executor.submit(self.MakeRequestHelper,
                                                     'compose_text_client',
                                                     serialized_span_context,
                                                     text_client_fn,
                                                     req_id, text)

                ## Call the creator id service
                user_client_fn = self.user_service_client.ComposeCreatorWithUserId
                creator_future = executor.submit(self.MakeRequestHelper,
                                                 'compose_creator_client',
                                                 serialized_span_context,
                                                 user_client_fn,
                                                 req_id, user_id, username)

                ## Call the media service                
                media_client_fn = self.media_service_client.ComposeMedia
                media_future = executor.submit(self.MakeRequestHelper,
                                               'compose_media_client',
                                               serialized_span_context,
                                               media_client_fn,
                                               req_id, media_types, media_ids)

                ## Call the UniqueId service
                unique_id_client_fn = self.unique_id_service_client.ComposeUniqueId
                unique_id_future = executor.submit(self.MakeRequestHelper,
                                                   'compose_unique_id_client',
                                                   serialized_span_context,
                                                   unique_id_client_fn,
                                                   req_id, post_type)

                text_return = text_result_future.result()
                ## Old invocation without futures
                # text_return = self._ComposeTextHelper(req_id, text, serialized_span_context)
                # log("Text returned:", text_return)

                creator = creator_future.result()
                # log("Creator returned:", creator)

                media = media_future.result()
                # log("Media returned:", media)

                unique_id = unique_id_future.result()
                # log("Unique ID returned:", unique_id)

                ## TODO: How do we handle the timestamp nondeterminism 
                timestamp = int(round(time.time() * 1000))

                ## Create the post
                post = ttypes.Post(post_id=unique_id, 
                                   creator=creator, 
                                   req_id=req_id, 
                                   text=text_return.text, 
                                   user_mentions=text_return.user_mentions, 
                                   media=media, 
                                   urls=text_return.urls, 
                                   timestamp=timestamp, 
                                   post_type=post_type)
                log("Post:", post)

        return

    ## A helper that makes requests to downstream services and correctly sets up tracing in the process
    def MakeRequestHelper(self, tracer_name, carrier, client_fn, *args):
        tracer = opentracing.global_tracer()

        ## Create a new span here.
        parent_span_context = tracer.extract(format=Format.TEXT_MAP,
                                             carrier=carrier)
        
        with tracer.start_span(operation_name=tracer_name, 
                               child_of=parent_span_context) as span:

            writer_text_map = {}
            tracer.inject(
                span_context=span.context,
                format=Format.TEXT_MAP,
                carrier=writer_text_map
            )

            ## TODO: Do we maybe need to connect to the transport here?

            ## TODO: We assume that all client calls take the text_map as their final arg
            args_list = list(args)
            args_list.append(writer_text_map)
            new_args = tuple(args_list)

            ## TODO: What kind of errors to we need to catch here?
            return_value = client_fn(*new_args)

        return return_value


## TODO: Remove the extra injects and extracts.

## TODO: Before making the tracer work we can do with logging, no problem.

def SetupClient(service_client_class, service_addr, service_port):
    ## Setup the socket
    transport = TSocket.TSocket(host=service_addr,
                                port=service_port)
    ## Configure the transport layer to correspond to the expected transport
    transport = TTransport.TFramedTransport(transport)

    ## Configure the protocol to be binary as expected from the service
    protocol = TBinaryProtocol.TBinaryProtocol(transport)

    ## Create the client
    client = service_client_class.Client(protocol)

    ## Connect to the client
    ## TODO: Understand what this does
    ## TODO: Where do we need to catch errors?
    try_n_times(transport.open, 10)
    # transport.open()

    return client

def SetupHttpClient(service_client_class, service_url):
    ## An HTTP Client is necessary to interact with FaaS
    transport = THttpClient.THttpClient(service_url)

    ## TODO: Transport probably doesn't really matter
    transport = TTransport.TBufferedTransport(transport)

    ## The protocol also probably doesn't matter, but it is good to start with JSON for better observability.
    protocol = TJSONProtocol.TJSONProtocol(transport)
    client = service_client_class.Client(protocol)

    # TODO: Unclear if this is necessary. 
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
    time.sleep(5)
    ## TODO: Get address and port from config file
    user_service_client = SetupClient(UserService, "user-service", 9090) 
    media_service_client = SetupClient(MediaService, "media-service", 9090) 
    unique_id_service_client = SetupClient(UniqueIdService, "unique-id-service", 9090)
    # text_service_client = SetupClient(TextService, "text-service", 9090)

    ## Alternative for FaaS
    ## TODO: Get that from some documentation
    text_service_client = SetupHttpClient(TextService, "http://host.docker.internal:8090/function/compose-post")
     

    handler = ComposePostHandler(text_service_client,
                                 user_service_client,
                                 media_service_client,
                                 unique_id_service_client)
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
