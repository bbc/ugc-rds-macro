#!/bin/bash
make build

aws s3 cp rdsmacroinstance.zip s3://rds-snapshot-id-lambda
aws lambda update-function-code --function-name int-ugc-rds-macro --s3-bucket rds-snapshot-id-lambda  --s3-key rdsmacroinstance.zip  --region eu-west-2
