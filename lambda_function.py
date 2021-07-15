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
    s3.meta.client.upload_file('/tmp/output.txt', 'celien-lambda-test', 'results/output.txt')