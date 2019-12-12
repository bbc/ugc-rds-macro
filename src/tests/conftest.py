import pytest
from botocore.stub import Stubber
import botocore.session
import datetime
from lambdas.ugc_rds_macro import client, cf_client, lambda_client
import os
import py

@pytest.yield_fixture(autouse=True)
def rds_stub():
    with Stubber(client) as stubber:
        stubber.activate()
        yield stubber
        stubber.assert_no_pending_responses()

@pytest.yield_fixture(autouse=True)
def cloudformation_stub():
    with Stubber(cf_client) as stubber:
        stubber.activate()
        yield stubber
        stubber.assert_no_pending_responses()

@pytest.yield_fixture(autouse=True)
def lambda_stub():
    with Stubber(lambda_client) as stubber:
        stubber.activate()
        yield stubber
        stubber.assert_no_pending_responses()
