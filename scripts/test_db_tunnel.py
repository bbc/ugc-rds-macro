#!/usr/bin/env python3
"""test_db_tunnel.

Usage:
  test_db_tunnel.py <env> <component> <port> <db>
  test_db_tunnel.py (-h | --help)


Commands:
   env               The environment
   component         The compoent eg. ugc-web-receier
   port              The postgress localhost port
   db                The address of the db to create the tunnel to.
"""
from docopt import docopt

import contextlib
import OpenSSL.crypto
from pathlib import Path
import ssl
from subprocess import Popen, PIPE, STDOUT
import os
import json
import io
from io import StringIO
import pycurl

def login(instance, component, env):
        
        cert_location = "/etc/pki/certificate.pem"
        e = io.BytesIO()
        buffer = StringIO()
        c = pycurl.Curl()
        c.setopt(c.URL, 'https://api.live.bbc.co.uk/cosmos/env/{0}/component/{1}/logins/create'.format(env,component))
        c.setopt(pycurl.HTTPHEADER, [ 'Content-Type: application/json' , 'Accept: application/json'])
        data = json.dumps({'instance_id': instance['id']})
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.POSTFIELDS, data)
        c.setopt(pycurl.SSL_VERIFYPEER, False)
        c.setopt(pycurl.SSL_VERIFYHOST, 2)
        c.setopt(c.WRITEFUNCTION, e.write)
        c.setopt(c.SSLCERT, cert_location)
        c.perform()
        c.close()

        print(str(e.getvalue()))


def get_instance(env, component):
        cert_location = "/etc/pki/certificate.pem"
        e = io.BytesIO()
        buffer = StringIO()
        c = pycurl.Curl()
        c.setopt(c.URL, 'https://api.live.bbc.co.uk/cosmos/env/{0}/component/{1}/instances'.format(env,component))
        c.setopt(pycurl.SSL_VERIFYPEER, False)
        c.setopt(pycurl.SSL_VERIFYHOST, 2)
        c.setopt(c.WRITEFUNCTION, e.write)
        c.setopt(c.SSLCERT, cert_location)
        c.perform()
        c.close()

        contents = json.loads(e.getvalue().decode('UTF-8'))
        return contents[0]

if __name__ == '__main__':
    arguments = docopt(__doc__, options_first=True)
    env  = arguments['<env>']
    component = arguments['<component>']
    port = arguments['<port>']
    db = arguments['<db>'] 
    
    i = get_instance(env, component)
    postgress_tunnel = "{0}:{1}:5432".format(port, db)
    remote_host = "{0},{1}".format(i['private_ip_address'],i['region'])

    login(i, component, env)
        
    tunnel_cmd = ['ssh', '-N', '-L', postgress_tunnel, remote_host]
    proc = Popen(tunnel_cmd)
    out, err = proc.communicate()
