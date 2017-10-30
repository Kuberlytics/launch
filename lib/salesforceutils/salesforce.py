
"""
These are a variety of shared functions
used in interfacting with salesforce   
"""
import configparser
import pandas as pd
pd.set_option("display.max_rows",999)
pd.set_option("display.max_columns",999)
import datetime
import logging
import psycopg2
#This connects to the mongoDB
import pymongo
import cgi
import requests
from simple_salesforce import Salesforce
from sqlalchemy import create_engine
from os import listdir
from os.path import isfile, join
import boto3
import ast
import shutil



#This is a fixed type translation between Salesforce and Posgress
translatePosgres={'ANYTYPE':'TEXT','BASE64':'TEXT','BOOLEAN':'BOOLEAN','COMBOBOX':'VARCHAR','CURRENCY':'NUMERIC','DATACATEGORYGROUPREFERENCE':'CHAR','DATE':'DATE','DATETIME':'TIMESTAMP','DOUBLE':'NUMERIC','EMAIL':'VARCHAR','ENCRYPTEDSTRING':'VARCHAR','ID':'CHAR','INT':'INTEGER','MULTIPICKLIST':'VARCHAR','PERCENT':'NUMERIC','PHONE':'VARCHAR','PICKLIST':'VARCHAR','REFERENCE':'CHAR','STRING':'VARCHAR','TEXTAREA':'VARCHAR','TIME':'TIME','URL':'VARCHAR'}

fileIgnore=['readme.md','.DS_Store']

def getConfig(file):
    """Return a configuration object cf.  cf should note be added to and then uses with anything outside.
    Arguments:
    * file -- the full path of the file. Don't use relative paths. 
    """
    cf={}
    cfg = configparser.ConfigParser()
    cfg.read(file)
    cf['today']=datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    cf['on_docker']= cfg.get('Default', 'on_docker')
    cf['login_type']= cfg.get('Default', 'login_type')
    cf['home']= cfg.get('Default', 'home')
    cf['data_path']= cfg.get('Default', 'data_path')

    cf['mongouri']=cfg.get('Mongo', 'mongouri')
    cf['mongodb']=cfg.get('Mongo', 'mongodb')

    cf['aws_redshift_database']= cfg.get('Aws', 'aws_redshift_database')
    cf['aws_redshift_host']= cfg.get('Aws', 'aws_redshift_host')
    cf['aws_redshift_username']= cfg.get('Aws', 'aws_redshift_username')
    cf['aws_redshift_password']= cfg.get('Aws', 'aws_redshift_password')
    cf['aws_redshift_port']= cfg.get('Aws', 'aws_redshift_port')
    cf['aws_redshift_tag']=cfg.get('Aws', 'aws_redshift_tag')

    cf['aws_access_key_id']= cfg.get('Aws', 'aws_access_key_id')
    cf['aws_secret_access_key']= cfg.get('Aws', 'aws_secret_access_key')
    cf['aws_region']= cfg.get('Aws', 'aws_region')
    cf['aws_bucket']=cfg.get('Aws', 'aws_bucket')
    cf['aws_move_to_s3']=ast.literal_eval(cfg.get('Aws', 'aws_move_to_s3'))

    cf['salesforce_email']= cfg.get('Salesforce', 'salesforce_email')
    cf['salesforce_password']= cfg.get('Salesforce', 'salesforce_password')
    cf['salesforce_token']= cfg.get('Salesforce', 'salesforce_token')
    cf['salesforce_id']= cfg.get('Salesforce', 'salesforce_id')
    cf['salesforce_secret']= cfg.get('Salesforce', 'salesforce_secret')
    cf['sandbox']=cfg.get('Salesforce', 'sandbox')
    cf['request_token_url'] = cfg.get('Salesforce', 'request_token_url')
    cf['access_token_url'] = cfg.get('Salesforce', 'access_token_url')
    cf['redirect_uri'] = cfg.get('Salesforce', 'redirect_uri')
    cf['authorize_url'] = cfg.get('Salesforce', 'authorize_url')
    cf['pardot_email']= cfg.get('Salesforce', 'pardot_email')
    cf['pardot_password']= cfg.get('Salesforce', 'pardot_password')
    cf['pardot_user_key']= cfg.get('Salesforce', 'pardot_user_key')
    cf['pardot_api_base']= cfg.get('Salesforce', 'pardot_api_base')

    return cf

def salesforceLogin(cf, userRecord=None):
    #Simple Login via username and password.
    if cf['login_type']=='password':
         return Salesforce(username=cf['salesforce_email'], password=cf['salesforce_password'], security_token=cf['salesforce_token'])
    else:
        #More complex login via mongodb. 
        cf=refreshUserToken(cf, userRecord)
        return Salesforce(instance_url=cf['response']['instance_url'], session_id=cf['response']['access_token'], sandbox=cf['sandbox'])

def soqlWhere(base,where=None): 
    if where==None:
        query=base
    else:
        query=base+where
    return query

def moveToS3(dataPath, cf):
    session = boto3.Session(
    aws_access_key_id=cf['aws_access_key_id'],
    aws_secret_access_key=cf['aws_secret_access_key'],
    region_name=cf['aws_region']
    )
    s3=session.resource('s3')
    
    #This lists the files
    dataFiles = [f for f in listdir(dataPath) if f not in fileIgnore and isfile(join(dataPath, f))]
    
    for dataFile in dataFiles:
        data = open(dataPath+'/'+dataFile, 'rb')
        if cf['aws_move_to_s3']:
            try: 
                #output3=s3.Bucket(cf['aws_bucket']).put_object(Key=dataFile, Body=data)
                print("Uploaded "+dataFile+" to S3.")
                data.close()  
                shutil.move(dataPath+'/'+dataFile, dataPath+'/archive/'+dataFile)
            
            except:
                print("Upload to S3 failed.")
        else:
            print("Config set to don't upload "+dataFile+" to S3.") 
         
    return 

def executeSOQLCSV(row, salesforce, cf):
    query_result = salesforce.query(generateSelect(row))
    counter=1
    records = query_result['records'] #Records In Current
    df = pd.DataFrame(records)
    records_received=len(records)
    print('Retreived: '+str(records_received)+' of '+str(query_result['totalSize'])+'\n')
    if records_received>0:   
        file=cf['data_path']+'/'+cf['salesforce_email']+"_"+row[0]+cf['today']+".csv" 
        out = open ( file , 'w')
        df.to_csv(out, header=False)
        if ('nextRecordsUrl' in query_result):
            while query_result['done'] is False:
                if cf['max_calls']!=None:
                    if counter>=maxCalls:
                        break
                next_record_url= query_result['nextRecordsUrl']
                query_result = salesforce.query_more(next_record_url, True)
                counter+=1
                records = query_result['records'] #Records In Current
                df = pd.DataFrame(records)
                df.to_csv(out, header=False)
                records_received +=len(records) #Records In Current
                print( 'Retreived: '+str(records_received)+' of '+str(query_result['totalSize'])+'\n')
        print("Finished Query \n")
        out.close()
    #Add something to keep track of most recent. 
    return 

def connectMongo(cf):
    try:
        conn=pymongo.MongoClient(cf['mongouri'])
        return conn[cf['mongodb']]
        print("Connection to MongoDB was successful.")
    except:
        print("Connection to MongoDB failed.")
        return 

def connectRedshift(cf,commands):
    conn = None
    try:
        # read the connection parameters
        # connect to the PostgreSQL server
        conn = psycopg2.connect(
        host=cf['aws_redshift_host'],
        user=cf['aws_redshift_username'],
        port=cf['aws_redshift_port'],
        password=cf['aws_redshift_password'],
        dbname=cf['aws_redshift_database'])
        cur = conn.cursor()
        # create table one by one
        for command in commands:
            #print("Executing: ",command)
            cur.execute(command)
        # close communication with the PostgreSQL database server
        cur.close()
        # commit the changes
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return

def get_tables(cf):
    """ query data from the vendors table """
    conn = None
    try:
        conn = psycopg2.connect(
        host=cf['aws_redshift_host'],
        user=cf['aws_redshift_username'],
        port=cf['aws_redshift_port'],
        password=cf['aws_redshift_password'],
        dbname=cf['aws_redshift_database'])
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        cur.execute("SELECT * FROM pg_catalog.pg_tables")
        print("The number of parts: ", cur.rowcount)
        row = cur.fetchone()
 
        while row is not None:
            print(row)
            row = cur.fetchone()
 
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()





# This manually hits the Salesforce API
def refreshUserToken(cf, userRecord ):
    query = cgi.FieldStorage()
    req = None
    data = {
	   'grant_type': 'refresh_token',
	   'redirect_uri': cf['redirect_uri'],
	   'refresh_token': userRecord['tokens'][0]['refreshToken'],
	   'client_id' : cf['salesforce_id'],
	   'client_secret' : cf['salesforce_secret']
    } 
    headers = {
	   'content-type': 'application/x-www-form-urlencoded'
    }
    try:
        print('Retrieved updated token from refresh token.')
        cf['response']=requests.post(cf['access_token_url'],data=data,headers=headers).json()
        return cf 
        
    except:
        print( 'Error renewing token.', cf['response'])
        return cf



def generateSelect(row): 
    fieldsObject=[x['name'] for x in row[1]['fields']]
    sql =  'SELECT '+', '.join(map(str, fieldsObject))+ ' FROM '+ row[0]
    return sql

def generateCreate(row,tag=''): 
    table=tag+row[0]
    sql =  'DROP TABLE IF EXISTS '+ table+'; CREATE TABLE '+ table+ ' ('
    for x in row[1]['fields']:
        sql=sql+x['name']+' '+ translatePosgres[x['type'].upper()]
        if x['length']!=0:   
            sql=sql+'('+str(x['length'])+')'
        if (x !=row[1]['fields'][-1]):
            sql=sql+', '
    sql =  sql+');'
    return sql

def generateValues(sfObject, descriptionObject): 
    values=[]
    for x in descriptionObject['fields']:
        print(x)
        #values.append([x['name'],x['type'],x['length']].upper()]+'('+str(x['length'])+')'
      
    return values

def countObject(salesforce, sfObject, cf, where = None):
    soql =  'SELECT COUNT() FROM '+ sfObject
    if where!=None:
        soql=soql+where
  
    try:
        countSQL=salesforce.query(soql)
        return countSQL['totalSize']
    except: 
        print("Retrieved"+sfObject+ "Object not successful.")
        return 0
    
def updateUser(mongo, cf, name, sf_object):
    try:
        mongo.users.update_one({'email': cf['salesforce_email']}, {'$set': {name:sf_object}})
        print( "Updated the user Record.")
        return
    except:
        print("Unable to update user record.")
        return

def retreiveUser(mongo,cf):
    try:
        user = mongo.users.find_one({'email':cf['salesforce_email']})
        print("Retrieved user details." )
        return user
    except: 
        print("User retreival not successful.")
        return None