from troposphere import Retain, Template, Sub, Ref, Parameter, GetAtt, Join, Output, Export, GenericHelperFn
from troposphere.awslambda import Function, Code, Alias, Environment
from troposphere import iam
from troposphere.cloudformation import Macro
from troposphere.logs import LogGroup, Destination
from awacs.aws import Action, Allow, Policy, PolicyDocument, Principal, Statement, AWSPrincipal, StringEquals, Condition, Null
from awacs.sts import AssumeRole
from troposphere.iam import Role

t = Template(
    Description="Create Macro For DBInstance manipulator and also the function")
t.add_version("2010-09-09")

ugc_rds_macro_function_name = "ugc-rds-macro"

t.add_description("Used manipulate the DbInstance Template")

rds_macro_handler = t.add_parameter(Parameter(
    "LambdaHandler",
    Type="String",
    Default="ugc_rds_macro.handler",
    Description="The name of the function (within your source code) "
                "that Lambda calls to start running your code."
))

memory_size = t.add_parameter(Parameter(
    "LambdaMemorySize",
    Type="Number",
    Default="1024",
    Description="The amount of memory, in MB, that is allocated to "
                "your Lambda function.",
    MinValue="128"
))

env = t.add_parameter(Parameter(
    "LambdaEnv",
    AllowedValues=["int", "test", "live"],
    Description="The environment the lambda is being deployed to",
    Type="String",
))

lambda_execution_time = t.add_parameter(Parameter(
    "LambdaExectionTime",
    Type="Number",
    Default="300",
    Description="Lambda Execution time"
))

function_role = t.add_resource(
    Role(
        "FunctionRole",
        Policies=[iam.Policy(
            PolicyName="UgcMoniorFunctionRolePolicy",
            PolicyDocument=Policy(
                Statement=[Statement(
                    Effect=Allow,
                    Action=[Action("logs", "CreateLogGroup"),
                            Action("logs", "CreateLogStream"),
                            Action("logs", "PutLogEvents")
                            ],
                    Resource=["arn:aws:logs:*:*:*"]
                ), Statement(
                    Effect=Allow,
                    Action=[
                        Action("rds", "DescribeDBSnapshots")],
                    Resource=["arn:aws:rds:*:*:*"]
                ), Statement(
                    Effect=Allow,
                    Action=[
                        Action("rds", "DescribeDBInstances")],
                    Resource=["*"]
                ), Statement(
                    Effect=Allow,
                    Action=[
                        Action("rds", "RestoreDBInstanceToPointInTime")],
                    Resource=["*"]
                ), Statement(
                    Effect=Allow,
                    Action=[
                        Action("rds", "CreateDBSnapshot")],
                    Resource=["*"]
                ), Statement(
                    Effect=Allow,
                    Action=[
                        Action("cloudformation", "GetTemplate")],
                    Resource=["*"]
                ), Statement(
                    Effect=Allow,
                    Action=[
                        Action("lambda", "TagResource")],
                    Resource=["*"]
                ), Statement(
                    Effect=Allow,
                    Action=[
                        Action("lambda", "UntagResource")],
                    Resource=["*"]
                ), Statement(
                    Effect=Allow,
                    Action=[
                        Action("lambda", "GetFunction")],
                    Resource=["arn:aws:lambda:*:*:function:*"]
                ), Statement(
                    Effect=Allow,
                    Action=[Action("lambda", "ListTags")],
                    Resource=["*"]
                ), Statement(
                    Effect=Allow,
                    Action=[
                        Action("rds", "DeleteDBInstance")],
                    Resource=["*"]
                )])
        )],
        AssumeRolePolicyDocument=Policy(
            Statement=[
                Statement(
                    Effect=Allow,
                    Action=[AssumeRole],
                    Principal=Principal(
                        "Service", ["lambda.amazonaws.com"]
                    )
                )
            ]
        )
    )
)

rds_macro_lambda = t.add_resource(
    Function(
        "RdsSnapShotLambdaFunction",
        Code=Code(
            S3Bucket="rds-snapshot-id-lambda",
            S3Key="rdsmacroinstance.zip"
        ),
        Environment=Environment(Variables={
            'log_level': 'info',
            'rds_snapshot_stack_name': 'mv-rds-db-stack',
            'replace_with_snapshot': 'false',
            'snapshot_type': '',
            'snapshot_id': '',
            'restore_time': '2019-09-07T23:45:00Z',
            'restore_point_in_time': 'false',
            'properties_to_remove': '',
            'properties_to_add': '',
        }
        ),
        Description="Function used to manipulate the dbinstance template",
        Handler=Ref(rds_macro_handler),
        MemorySize=Ref(memory_size),
        FunctionName=Sub("${LambdaEnv}-%s" % ugc_rds_macro_function_name),
        Role=GetAtt(function_role, "Arn"),
        Runtime="python3.7",
        Timeout=900
    )
)

role = Role(
    "RdsMacroLogRole",
    AssumeRolePolicyDocument=Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Action=[AssumeRole],
                Principal=Principal(
                    "Service", ["cloudformation.amazonaws.com"]
                )
            )
        ]
    ),
    Policies=[iam.Policy(
        PolicyName="FunctionRolePolicy",
        PolicyDocument=Policy(
            Statement=[
                Statement(
                    Effect=Allow,
                    Action=[Action("logs", "*")],
                    Resource=["arn:aws:logs:*:*:*"]
                ), Statement(
                    Effect=Allow,
                    Action=[Action("rds", "DescribeDBInstances")],
                    Resource=["*"]
                ),
                Statement(
                    Effect=Allow,
                    Action=[Action("rds", "DescribeDBSnapshots")],
                    Resource=["arn:aws:rds:*:*:*"]
                ), Statement(
                    Effect=Allow,
                    Action=[
                        Action("rds", "RestoreDBInstanceToPointInTime")],
                    Resource=["*"]
                ), Statement(
                    Effect=Allow,
                    Action=[Action("rds", "CreateDBSnapshot")],
                    Resource=["*"]
                )]
        ))]
)


lg = LogGroup(
    "LogGroupForRDSMacro",
    DeletionPolicy=Retain
)

t.add_resource(lg)
t.add_resource(role)

log_destination = Destination(
    'MyLogDestination',
    DestinationName='destination-name',
    RoleArn='role-arn',
    TargetArn='target-arn',
    DestinationPolicy='destination-policy'
)


dbInstanceMacro = Macro(title="DBInstanceManipulator",
                        template=t, validation=False,
                        Description="This is use to invoke the function that modifies the db instance template",
                        FunctionName=GetAtt(rds_macro_lambda, "Arn"),
                        LogGroupName=Ref(lg),
                        LogRoleARN=GetAtt(role, "Arn"),
                        Name="UgcRdsMacro")

print(t.to_json())
