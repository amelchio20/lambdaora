# Zabbix Lambda Scripts

[[_TOC_]]

## Description
This repo aims at explaining how can one deploy in AWS a Lambda function which will query an on-prem Database and put the result back into a S3 Bucket. This is based on a deployment for the **dev** account (*621046659448*)<br/>
This is explanation is targeted for a **manual** deployment. A correct CI/CD pipeline should be implemented when the time is available. <br/>
The `package` folder is here **only for reference**. It should not be used directly, but should be built following the process explained below.

## Package the dependencies
Since this function will query an Oracle Database, we need to be able to use `cx_Oracle` and other binairies, with correct version number. <br/>
The first step of this process is to
* Create a folder that will hold all what we need (for example: `mkdir dependencies`).

### Oracle Instant Client
- Go to the Oracle Instant Client [page](https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html) and scroll down to the `Version 18.5.0.0.0`.
- Download `Basic Light Package (ZIP)` into the `dependencies` folder you created before ([direct download](https://download.oracle.com/otn_software/linux/instantclient/185000/instantclient-basiclite-linux.x64-18.5.0.0.0dbru.zip)).
- Unzip the content, which will create a directory called `instantclient_18_5`.
- Leave that here for now.

### cx_Oracle
- Go to the `pip` installation page for the `cx_Oracle` package [here](https://pypi.org/project/cx-Oracle/7.3.0/#files)
- Download `cx_Oracle-7.3.0-cp38-cp38-manylinux1_x86_64.whl`into `dependencies` folder you created before ([direct download](https://files.pythonhosted.org/packages/a3/b1/abcd4b736f568b5a58accbf72dd16754daee059c4556f564f0d1f78e462e/cx_Oracle-7.3.0-cp38-cp38-manylinux1_x86_64.whl)).
- Pull the [Amazon Linux Docker image](https://hub.docker.com/_/amazonlinux): `docker pull amazonlinux:latest`
- `cd` into the `dependencies` folder you created before.
- Execute a shell session on the Amazon Linux docker container by mounting your current folder:
    - `docker run --rm -it -v $PWD:/tmp -w /tmp  amazonlinux:latest /bin/bash`
- Once **inside** the container, install the latest `Python` and `pip3` version:
    - `amazon-linux-extras enable python3.8`
    - `yum install -y python3.8`
    - `yum install python3-pip`
- Still **inside** the container, install the `cx_Oracle` package:
    - `pip3 install cx_Oracle-7.3.0-cp38-cp38-manylinux1_x86_64.whl --target ./cx_Oracle`
- This will create two new entries we need: `dependencies/cx_Oracle/cx_Oracle-7.3.0.dist-info` and `dependencies/cx_Oracle/cpython-38-x86_64-linux-gnu.so`
- Leave those files here for now.

### libaio
- Go to the liabio download [page](https://pkgs.org/download/libaio) and search for the `PCLinuxOS`.
- Download it into the `dependencies` folder you created before:
    - `wget https://ftp.nluug.nl/pub/os/Linux/distr/pclinuxos/pclinuxos/apt/pclinuxos/64bit/RPMS.x86_64/lib64aio1-0.3.111-2pclos2020.x86_64.rpm`
- Pull the [Amazon Linux Docker image](https://hub.docker.com/_/amazonlinux): `docker pull amazonlinux:latest`
- `cd` into the `dependencies` folder you created before.
- Execute a shell session on the Amazon Linux docker container by mounting your current folder:
    - `docker run --rm -it -v $PWD:/tmp -w /tmp  amazonlinux:latest /bin/bash`
- Once **inside** the container, execute the following command:
    - `rpm2cpio lib64aio1-0.3.111-2pclos2020.x86_64.rpm | cpio -idmv`
- This will create several files in `dependencies/usr/lib64/` which we need.
- Leave those files here for now.

### Package everything
- Where you want, create a folder called `lambda_function` (the name does not matter): `mkdir lambda_function`.
- Inside this `lambda_function` folder, create another folder called `package`: `mkdir package`.
- In `package`:
    - Copy all the files from `dependencies/instantclient_18_5`.
    - Copy the folder (*the entire folder, not just the content*) `dependencies/cx_Oracle/cx_Oracle-7.3.0.dist-info` and the file `dependencies/cx_Oracle/cpython-38-x86_64-linux-gnu.so`
    - Copy all the files (*only the files, not the fodler*) from `dependencies/usr/lib64/`
- In the `lambda_function` folder, create a file called `lambda_function.py` (the name does not matter). This will be the function executed by the Lambda.
- An example of content could be the following:
```python
import json
import boto3
import cx_Oracle

def main(event, context):
    dsn_tns = cx_Oracle.makedsn('10.171.204.4', '1521', service_name='pMONDB')
    conn = cx_Oracle.connect(user='patroldb', password='<password>', dsn='(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=10.171.204.4)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=pMONDB)))' )
    c = conn.cursor()
    c.execute('select * from v$instance')
    with open("/tmp/output.txt", "w") as text_file:
        for row in c:
            print(row[0], '-', row[1])
            print(row)
            text_file.write(str(row[0]) + " - " + str(row[1]))
    conn.close()
    s3 = boto3.resource('s3')
    s3.meta.client.upload_file('/tmp/output.txt', 'lambda-test-bucket', 'results/output.txt')
```
- `cd` into the package directory, and zip everything:
    - `zip -r ../my-deployment-package.zip .`
- `cd` into the parent directory (`cd ..` from `package`) and add your function to the zip file:
    - `zip -g my-deployment-package.zip lambda_function.py`
- Your function is now packaged and ready to be up uploaded.

## Deploy the Lambda function
### Create a S3 bucket
- Go ahead and create a S3 Bucket.
- Leave all the default settings (make sure the `Block All Public Access` is ticked).
- *Modify the Bucket default encryption if you want.* **Note - If you use KMS, the policy attached to the IAM Role of the Lambda function will need to be adapted to use the KMS Key.**
- Uploads the deployment package to the root of this bucket.

### Create an IAM Role for the Lambda function
- On the [IAM Role Creation Page](https://console.aws.amazon.com/iam/home#/roles$new?step=type), create an `AWS Service` Role for `Lambda`.
- Create a new policy and put the following content in it (make sure to replace the `<bucket_name>` value by the name of the S3 Bucket you previously created)
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:eu-central-1:621046659448:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:eu-central-1:621046659448:log-group:/aws/lambda/*:*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateNetworkInterface",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DeleteNetworkInterface",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeSubnets",
                "ec2:DescribeVpcs"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:GetObject",
                "s3:GetObjectAcl",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::<bucket_name>",
                "arn:aws:s3:::<bucket_name>/*"
            ]
        }
    ]
}
```
- Continue the role Creation, attach the policy whihc has been created and give the role a name.
- Create a `Security Group` for the Lambda function and create the `inbound` or `outbounds` rules you want.

### Deploy the Lambda function
- Deploy the Lambda function in the right subnets. Those subnets **must** have access to `CNDTAG` if you want to query `on-prem` resources (*replace the values by the entities yoiu created before*)
```bash
aws lambda create-function \
            --function-name <function_name> \
            --runtime python3.8 \
            --role <role_arn> \
            --handler lambda_function.main \
            --code S3Bucket=<bucket_name>,S3Key=<bucket_string> \
            --vpc-config SubnetIds=<subnet_1>,<subnet_2>,SecurityGroupIds=<sg_id_1>,<sg_id_2>
            --timeout <timeout> \
            --memory-size <mem_size>
```

An example for the `dev` account would be:
```bash
aws lambda create-function \
            --function-name LambdaTest \
            --runtime python3.8 \
            --role arn:aws:iam::621046659448:role/Lambda_Demo \
            --handler lambda_function.main \
            --code S3Bucket=lambda-test-bucket,S3Key=my-deployment-package.zip \
            --vpc-config SubnetIds=subnet-00b48792fc4747851,subnet-069d83e46d1b6926d,SecurityGroupIds=sg-0e41019941cddeb20 \
            --timeout 180 \
            --memory-size 1024
```


## Resources
- [Create a Lambda deployment package](https://docs.aws.amazon.com/lambda/latest/dg/python-package-create.html)
- [High-level Overview on how to install `cx_Oracle`](https://stackoverflow.com/questions/55053472/accessing-oracle-from-aws-lambda-in-python)
