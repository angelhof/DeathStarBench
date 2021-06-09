import glob
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



class ComposePostHandler:
    def __init__(self):
        self.log = {}

    ## TODO: Regenerate the thrift files so that carrier is there
    def ComposePost(self, req_id, username, user_id,    
                    text, media_ids, media_types, post_type):
        return


if __name__ == '__main__':
    ## TODO: Sigint handler
    ## TODO: Logger
    ## TODO: Tracer???

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

    print('Starting the compose-post-service server...')
    server.serve()
    print('done.')
