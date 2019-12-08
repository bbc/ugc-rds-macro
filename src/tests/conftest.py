import pytest
from botocore.stub import Stubber
import botocore.session
import datetime
from lambdas.ugc_rds_macro import client
import os
import py

@pytest.yield_fixture(autouse=True)
def s3_stub():
    with Stubber(client) as stubber:
        stubber.activate()
        yield stubber
        stubber.assert_no_pending_responses()
