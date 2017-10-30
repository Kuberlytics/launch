
# coding: utf-8
# ## Kuberutils
#
# When using the docker container, this will automatically save to a .py file. Otherwise. #jupyter nbconvert --to script kuberutils.ipynb
#
# This is a great place to put functions you develop and want to reuse. These programs can then be imported into each notebook using:
# ```
# import sys
# sys.path.append('/kuberlytics/kuberutils')
# import kuberutils as ku
#
# ```


#Let's import some common packages here
import importlib
import subprocess
import ruamel.yaml
import sys
import os.path
import collections
import csv, codecs
from dateutil import parser
docker_prefix="sudo docker run --rm -i --volumes-from gcloud-config kuberlytics/gcloud-sdk "

def gcloud_commands(cf_g):
    """This functions creates a variety of commands to augment the configuration.

    """
    cf_g['create_service_account']="gcloud iam service-accounts create "+cf_g['service_account_name']+ " --display-name "+ cf_g['service_account_name']
    cf_g['create_key']="gcloud iam service-accounts keys create "+cf_g['path']+"/config/gcloud/"+cf_g['authorization_file'] +" --iam-account "+cf_g['service_account_name']+"@"+cf_g['project']+".iam.gserviceaccount.com"
    cf_g['get_policy']="gcloud iam service-accounts get-iam-policy "+cf_g['service_account_name']+"@"+cf_g['project']+".iam.gserviceaccount.com --format json > "+cf_g['path']+"/config/gcloud/policy.json"
    cf_g['set_policy']="gcloud iam service-accounts set-iam-policy "+cf_g['service_account_name']+"@"+cf_g['project']+".iam.gserviceaccount.com "+cf_g['path']+"/config/gcloud/policy.json"
    cf_g['login']="gcloud auth activate-service-account  --key-file "+cf_g['path']+"/config/gcloud/"+ cf_g['authorization_file']
    cf_g['set_project']="gcloud config set project "+cf_g['project']
    cf_g['set_zone']="gcloud config set compute/zone "+cf_g['zone']
    cf_g['create_cluster']="gcloud container clusters create "+cf_g['cluster_name']+" --num-nodes="+str(cf_g['num_nodes'])+" --machine-type="+cf_g['machine_type']+" --zone="+cf_g['zone']
    cf_g['get_credentials']="gcloud container clusters get-credentials "+cf_g['cluster_name']
    cf_g['stop_cluster']="gcloud container clusters resize "+cf_g['cluster_name']+" --size=0 --quiet"
    cf_g['normal_size_cluster']="gcloud container clusters resize "+cf_g['cluster_name']+" --size="+str(cf_g['num_nodes'])+" --quiet"
    cf_g['class_size_cluster']="gcloud container clusters resize "+cf_g['cluster_name']+" --size="+str(cf_g['num_nodes_class'])+" --quiet"
    cf_g['delete_cluster']="gcloud container clusters delete "+cf_g['cluster_name']+" --zone="+cf_g['zone']+" --quiet"
    cf_g['autoscale']="gcloud alpha container clusters update "+cf_g['cluster_name']+" --enable-autoscaling --min-nodes="+str(cf_g['num_nodes'])+" --max-nodes="+str(cf_g['max_nodes'])+" --zone="+cf_g['zone']+" --node-pool=default-pool"
    cf_g['create_fixedip']="gcloud compute addresses create "+cf_g['fixedip_namespace']+" --region="+cf_g['region']
    cf_g['describe_fixedip']="gcloud compute addresses describe "+cf_g['fixedip_namespace']+" --region="+cf_g['region']
    cf_g['delete_forwarding_rule']="gcloud compute forwarding-rules delete forwarding_rule --quiet"
    cf_g['delete_fixedip']="gcloud compute addresses delete "+cf_g['fixedip_namespace']+" --region="+cf_g['region']+" --quiet"
    cf_g['describe_cluster']="gcloud container clusters describe "+cf_g['cluster_name']
    return cf_g

def azure_commands(cf_a):
    """This functions creates a variety of commands to augment the configuration.

    """
    cf_a['web_login']="az login"
    cf_a['create_project']="az group create --name="+cf_a['resource_group']+ " --location="+ cf_a['location']
    cf_a['delete_project']="az group delete --name="+cf_a['resource_group']+" --yes --no-wait"
    cf_a['list-locations']="az account list-locations"
    cf_a['create_cluster_acs']="az acs create --orchestrator-type=kubernetes --resource-group="+cf_a['resource_group'] +" --name="+cf_a['cluster_name']+" --dns-prefix="+cf_a['dns_prefix']+" --agent-count="+str(cf_a['num_nodes'])+" --agent-vm-size="+cf_a['machine_type']+" --generate-ssh-keys --no-wait"
    cf_a['describe_cluster_acs']="az acs list  --resource-group="+cf_a['resource_group']
    cf_a['create_cluster_aks']="az acs create --orchestrator-type=kubernetes --resource-group="+cf_a['resource_group'] +" --name="+cf_a['cluster_name']+" --dns-prefix="+cf_a['dns_prefix']+" --agent-count="+str(cf_a['num_nodes'])+" --agent-vm-size="+cf_a['machine_type']+" --generate-ssh-keys --no-wait"
    cf_a['describe_cluster_aks']="az acs list  --resource-group="+cf_a['resource_group']

    cf_a['delete_cluster_acs']="az acs delete  --resource-group="+cf_a['resource_group']+" --name="+cf_a['cluster_name']+" --no-wait"
    cf_a['which cluster']="kubectl config current-context"
    cf_a['get_credentials_acs']="az acs kubernetes get-credentials --resource-group="+cf_a['resource_group']+" --name="+cf_a['cluster_name']

    # Can't size to 0 cf_g['stop_cluster']="az acs scale --resource-group="+cf_a['resource_group']+" --name="+cf_a['cluster_name']+" --new-agent-count 0"
    cf_a['normal_size_cluster']="az acs scale --resource-group="+cf_a['resource_group']+" --name="+cf_a['cluster_name']+" --new-agent-count "+str(cf_a['num_nodes'])
    cf_a['class_size_cluster']="az acs scale --resource-group="+cf_a['resource_group']+" --name="+cf_a['cluster_name']+" --new-agent-count "+str(cf_a['num_nodes_class'])
    return cf_a

def pachyderm_commands(cf_p):
    cf_p['install_pachyderm']= "az storage account create --resource-group="+cf_p['resource_group']+" --location="+cf_p['location']+" --sku=Standard_LRS  --name="+cf_p['storage_account']+" --kind=Storage"
    cf_p['get_storage_key']="az storage account keys list --account-name="+cf_p['storage_account']+" --resource-group="+cf_p['resource_group']+" --output=json | jq .[0].value -r"
    cf_p['clone']="git clone https://github.com/pachyderm/pachyderm /home/jovyan/work/pachyderm"
    cf_p['blob']= "az storage blob list --container=${CONTAINER_NAME}  --account-name="+cf_p['storage_account']"+" --account-key="+${STORAGE_KEY}
    return cf_p


def jupyterhub_commands(cf_j):
    cf_j['jupyterhub_instance']=cf_j['path']+"/config/jupyterhub/"+cf_j['namespace']
    cf_j['jupyterhub_config']=cf_j['path']+"/config/jupyterhub/"+cf_j['namespace']+"/config.yaml"
    cf_j['jupyter_base']=cf_j['path']+"/config/jupyterhub/"+cf_j['namespace']+"/values.yaml"
    cf_j['install_ssl']="helm install --name=letsencrypt --namespace=kube-system stable/kube-lego --set config.LEGO_EMAIL="+cf_j['email']+" --set config.LEGO_URL=https://acme-v01.api.letsencrypt.org/directory"
    cf_j['repo_jupyterhub']="helm repo add jupyterhub "+cf_j['jupyterhub_helm_repo']+" && helm repo update"
    cf_j['install_jupyterhub']="helm install jupyterhub/jupyterhub --version="+cf_j['jupyterhub_version']+" --name="+cf_j['releasename']+" --namespace="+cf_j['namespace']+" -f "+cf_j['jupyterhub_config']
    cf_j['upgrade_jupyterhub']="helm upgrade "+cf_j['namespace']+" jupyterhub/jupyterhub --version="+cf_j['jupyterhub_version']+" -f "+cf_j['jupyterhub_config']
    cf_j['describe_jupyterhub']="kubectl --namespace="+cf_j['namespace']+" get pod"
    cf_j['ip_jupyterhub']="kubectl --namespace="+ cf_j['namespace']+" get svc proxy-public"
    cf_j['delete_jupyterhub']="helm delete "+cf_j['releasename']+" --purge"
    cf_j['delete_namespace']="kubectl delete namespace "+cf_j['namespace']
    if cf_j['ssl']:
        cf_j['callback_url']= "https://"
    else:
        cf_j['callback_url']= "http://"
    cf_j['callback_url']=cf_j['callback_url']+cf_j['url']+"/hub/oauth_callback"
    cf_j['get_logs']="kubectl --namespace="+cf_j['namespace']+" logs <insert_podname>"
    return cf_j

def import_config(file):
    kube_yaml='../../config/kubernetes.yaml'
    with open(kube_yaml, 'r') as yaml:
        cf=ruamel.yaml.round_trip_load(yaml, preserve_quotes=True)
    return cf

def bash_command_simple(command):
    try:
        print("executing the Bash command:\n", command)
        result=subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        result=result.decode("utf-8")
        return result
    except subprocess.CalledProcessError as e:
        return(e.output.decode("utf-8"))

def bash_command(command, config={}):

    if command in config:
        syntax=config[command]
    else:
        syntax=command

    try:
        print("Executing "+command+":\n", syntax)
        result=subprocess.check_output(syntax, stderr=subprocess.STDOUT, shell=True)
        result=result.decode("utf-8")
        return result
    except subprocess.CalledProcessError as e:
        return(e.output.decode("utf-8"))

def gcloud_command(command,config):
    if command in config:
        syntax=config['google'][command]
    else:
        syntax=command

    if config['general']['docker']:
        env= " on docker"
        syntax=docker_prefix+syntax
    else:
        env= " on localhost"

    try:
        print("Executing "+command+ env+":\n", syntax)
        result=subprocess.check_output(syntax, stderr=subprocess.STDOUT, shell=True)
        result=result.decode("utf-8")
        return result
    except subprocess.CalledProcessError as e:
        return(e.output.decode("utf-8"))



# In[ ]:

def update_config(configkey, kubekey, cf_j):
    config = ruamel.yaml.round_trip_load(open(cf_j['jupyterhub_config']), preserve_quotes=True)
#        singleuser['singleuser']=cf_j['singleuser']
    if configkey in config:
        config[configkey]=cf_j[kubekey]
    else:
        config.insert(len(config), configkey, cf_j[kubekey])
    ruamel.yaml.round_trip_dump(config, open(cf_j['jupyterhub_config'], 'w'))
    return


# In[ ]:

#jupyter nbconvert --to script kuberutils.ipynb


# In[ ]:

def set_jupyterhub_auth(auth_type, cf_j):
    if auth_type=='dummy':
        #Optional Dummy Authorization
        inp_auth = """        type: dummy
        dummy:
        """
        auth = ruamel.yaml.round_trip_load(inp_auth, preserve_quotes=True)
        config = ruamel.yaml.round_trip_load(open(cf_j['jupyterhub_config']), preserve_quotes=True)
        auth['dummy']=cf_j['dummy_auth']

    elif auth_type=='github':
        #Optional Github Authorization
        inp_auth = """        type: github
        github:
        """
        auth = ruamel.yaml.round_trip_load(inp_auth, preserve_quotes=True)
        config = ruamel.yaml.round_trip_load(open(cf_j['jupyterhub_config']), preserve_quotes=True)
        auth['github']=cf_j['github_auth']


        ruamel.yaml.round_trip_dump(config, open(cf_j['jupyterhub_config'], 'w'))
    elif auth_type=='google':
        #Optional Google Authorization
        inp_auth = """        type: google
        google:
        """
        auth = ruamel.yaml.round_trip_load(inp_auth, preserve_quotes=True)
        config = ruamel.yaml.round_trip_load(open(cf_j['jupyterhub_config']), preserve_quotes=True)
        auth['google']=cf_j['google_auth']

    if 'auth' in config:
        config['auth']=auth
    else:
        config.insert(len(config), 'auth', auth)
    ruamel.yaml.round_trip_dump(config, open(cf_j['jupyterhub_config'], 'w'))
    print(ruamel.yaml.dump(config, sys.stdout, Dumper=ruamel.yaml.RoundTripDumper))
    return


# In[ ]:

def init_jupyterhub_config(cf_j):
    if cf_j['set_fixed_ip']:
        inp = """    #These are the only two required fields we need to launch
        proxy:
          secretToken: null
          service:
            loadBalancerIP: null
        hub:
          cookieSecret: null
        """
    else:
        inp = """    #These are the only two required fields we need to launch
        proxy:
          secretToken: null
        hub:
          cookieSecret: null
        """
    #This will write out a basic .YAML file.
    with open(cf_j['jupyterhub_instance']+'/cookie_secret.txt', 'r') as f:
          cookie_secret = f.read().rstrip()
    with open(cf_j['jupyterhub_instance']+'/secret_token.txt', 'r') as f:
          secret_token = f.read().rstrip()

    #if os.path.exists(cf_j['jupyterhub_config']):
    #    config = ruamel.yaml.round_trip_load(open(cf_j['jupyterhub_config']), preserve_quotes=True)
    #else:
    #currently overwrites.
    config = ruamel.yaml.load(inp, ruamel.yaml.RoundTripLoader)

    config['hub']['cookieSecret']=cookie_secret
    config['proxy']['secretToken']=secret_token
    if cf_j['set_fixed_ip']:
        config['proxy']['service']['loadBalancerIP']=cf_j['fixed_ip']
    ruamel.yaml.round_trip_dump(config, open(cf_j['jupyterhub_config'], 'w'))

    return

def isipv4(s):
    sp = s.split('.')
    if len(sp) != 4: return False
    try: return all(0<=int(p)<256 for p in sp)
    except ValueError: return False

def get_jupyterhub_ip(cf_j):
    result=bash_command('ip_jupyterhub',cf_j)
    result=result.split(" ")
    cf_j['public_ip']=[x for x in result if isipv4(x)][1]
    print("JupyterHub is live at the following address:")
    print("http://"+cf_j['public_ip']+"/hub/login")
    return cf_j

def get_fixed_ip(cf_g):
    result=bash_command(cf_g['describe_fixedip']).split('\n')
    public_ip= [x for x in result if "address:" in x][0].split(' ').pop()
    return public_ip

def set_fixed_ip(cf_j):
    inp = """    #These are the only two required fields we need to launch
    proxy:
      secretToken: null
    hub:
      cookieSecret: null
    """

    if os.path.exists(cf_j['jupyterhub_config']):
        config = ruamel.yaml.round_trip_load(open(cf_j['jupyterhub_config']), preserve_quotes=True)
    else:
        config = ruamel.yaml.load(inp, ruamel.yaml.RoundTripLoader)


    config['proxy']['service']['loadBalancerIP']=cf_j['fixed_ip']
    ruamel.yaml.round_trip_dump(config, open(cf_j['jupyterhub_config'], 'w'))
    return
