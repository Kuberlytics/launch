
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
import json
from dateutil import parser
docker_prefix="sudo docker run --rm -i --volumes-from gcloud-config kuberlytics/gcloud-sdk "

def initialize(config):
    """This functions creates a variety of commands to augment the configuration of Kubernetes.
       It returns the cf.
    """
    if config['restore_config']:
        restore_kube(config)
    #load the config file
    with open(config['path']+config['config_file'], 'r') as yaml:
         cf=ruamel.yaml.round_trip_load(yaml, preserve_quotes=True)
    #update passed variables
    cf['restore_config']=False
    cf['path']=config['path']
    cf['config_file']=config['config_file']
    cf['cloud_provider']=config['cloud_provider']      #azure of google
    cf['project_name']=config['project_name']  #Must be globally unique.
    cf['cluster_name']=config['cluster_name']         #Only use if restore_config==True
    cf['config_file']=config['config_file']  #The configuration will be overwritten if retreived.
    cf['path']=config['path']  #Path to admintools repository
    cf['ssh_dir']=config['ssh_dir']     #ssh directory
    cf['resource_group']=cf['project_name']
    #store any local changes
    ruamel.yaml.round_trip_dump(cf, open(config['path']+config['config_file'], 'w'))

    if cf['cloud_provider']=="azure":
        cf=azure_commands(cf)
    elif cf['cloud_provider']=="google":
        cf=google_commands(cf)
    cf=jupyterhub_commands(cf)
    cf['which_cluster']="kubectl config current-context"
    cf['clone_pachyderm']="git clone https://github.com/pachyderm/pachyderm /home/jovyan/work/pachyderm"
    return cf

def gcloud_commands(cf_g):
    """This functions creates a variety of commands to augment the configuration of Kubernetes on the Google cloud platform.
    """
    cf_g['cluster_name']=cf_g['cluster_name']
    cf_g['g_project']=cf_g['project_name']
    cf_g['create_service_account']="gcloud iam service-accounts create "+cf_g['g_service_account_name']+ " --display-name "+ cf_g['g_service_account_name']
    cf_g['create_key']="gcloud iam service-accounts keys create "+cf_g['g_path']+"/config/gcloud/"+cf_g['g_authorization_file'] +" --iam-account "+cf_g['g_service_account_name']+"@"+cf_g['g_project']+".iam.gserviceaccount.com"
    cf_g['get_policy']="gcloud iam service-accounts get-iam-policy "+cf_g['g_service_account_name']+"@"+cf_g['g_project']+".iam.gserviceaccount.com --format json > "+cf_g['g_path']+"/config/gcloud/policy.json"
    cf_g['set_policy']="gcloud iam service-accounts set-iam-policy "+cf_g['g_service_account_name']+"@"+cf_g['g_project']+".iam.gserviceaccount.com "+cf_g['g_path']+"/config/gcloud/policy.json"
    cf_g['web_login']="gcloud init"
    cf_g['login']="gcloud auth activate-service-account  --key-file "+cf_g['g_path']+"/config/gcloud/"+ cf_g['g_authorization_file']
    cf_g['create_project']="gcloud projects create "+cf_g['g_project']+"----set-as-default"
    cf_g['set_project']="gcloud config set project "+cf_g['g_project']
    cf_g['set_zone']="gcloud config set compute/zone "+cf_g['g_zone']
    cf_g['create_cluster']="gcloud container clusters create "+cf_g['cluster_name']+" --num-nodes="+str(cf_g['g_num_nodes'])+" --machine-type="+cf_g['g_machine_type']+" --zone="+cf_g['g_zone']
    cf_g['get_credentials']="gcloud container clusters get-credentials "+cf_g['cluster_name']
    cf_g['stop_cluster']="gcloud container clusters resize "+cf_g['cluster_name']+" --size=0 --quiet"
    cf_g['normal_size_cluster']="gcloud container clusters resize "+cf_g['cluster_name']+" --size="+str(cf_g['g_num_nodes'])+" --quiet"
    cf_g['class_size_cluster']="gcloud container clusters resize "+cf_g['cluster_name']+" --size="+str(cf_g['g_num_nodes_class'])+" --quiet"
    cf_g['delete_cluster']="gcloud container clusters delete "+cf_g['cluster_name']+" --zone="+cf_g['g_zone']+" --quiet"
    cf_g['autoscale']="gcloud alpha container clusters update "+cf_g['cluster_name']+" --enable-autoscaling --min-nodes="+str(cf_g['g_num_nodes'])+" --max-nodes="+str(cf_g['g_max_nodes'])+" --zone="+cf_g['g_zone']+" --node-pool=default-pool"
    cf_g['create_fixedip']="gcloud compute addresses create "+cf_g['g_fixedip_namespace']+" --region="+cf_g['g_region']
    cf_g['describe_fixedip']="gcloud compute addresses describe "+cf_g['g_fixedip_namespace']+" --region="+cf_g['g_region']
    cf_g['delete_forwarding_rule']="gcloud compute forwarding-rules delete forwarding_rule --quiet"
    cf_g['delete_fixedip']="gcloud compute addresses delete "+cf_g['g_fixedip_namespace']+" --region="+cf_g['g_region']+" --quiet"
    cf_g['describe_cluster']="gcloud container clusters describe "+cf_g['cluster_name']
    return cf_g

def azure_commands(cf_a):
    """This functions creates a variety of commands to augment the configuration of Kubernetes on the Google cloud platform.
    """

    cf_a['web_login']="az login"
    cf_a['login']="echo 'Service account login not yet available for Azure'"
    cf_a['create_project']="az group create --name="+cf_a['project_name']+ " --location="+ cf_a['a_location']
    cf_a['set_project']="echo 'No need to set project in Azure.'"
    cf_a['set_zone']="echo 'No need to set project in Azure.'"
    cf_a['delete_project']="az group delete --name="+cf_a['project_name']+" --yes --no-wait"
    cf_a['list-locations']="az account list-locations"
    cf_a['autoscale']="echo 'Autoscaling currently not possible.'"
    if cf_a['a_service_type']=="aks":
        cf_a['create_cluster']="az aks create --resource-group="+cf_a['project_name'] +" --name="+cf_a['cluster_name']+" --agent-count="+str(cf_a['a_num_nodes'])+" --agent-vm-size="+cf_a['a_machine_type']+" --generate-ssh-keys --no-wait"
        cf_a['describe_cluster']="az aks list --resource-group="+cf_a['project_name']
        cf_a['delete_cluster']="az aks delete --name="+cf_a['cluster_name']+" --resource-group="+cf_a['project_name']+" --no-wait"
        cf_a['get_credentials']="az aks get-credentials --resource-group="+cf_a['project_name']+" --name="+cf_a['cluster_name']
        cf_a['normal_size_cluster']="az aks scale  --agent-count "+str(cf_a['a_num_nodes']) +" --name="+cf_a['cluster_name']+" --resource-group="+cf_a['project_name']
        cf_a['class_size_cluster']="az aks scale --agent-count "+ str(cf_a['a_num_nodes_class'])+" --name="+cf_a['cluster_name']+" --resource-group="+cf_a['project_name']
    elif cf_a['a_service_type']=="acs":
        cf_a['create_cluster']="az acs create --orchestrator-type=kubernetes --resource-group="+cf_a['project_name'] +" --name="+cf_a['cluster_name']+" --dns-prefix="+cf_a['a_dns_prefix']+" --agent-count="+str(cf_a['a_num_nodes'])+" --agent-vm-size="+cf_a['a_machine_type']+" --generate-ssh-keys --no-wait"
        cf_a['describe_cluster']="az acs list  --resource-group="+cf_a['project_name']
        cf_a['delete_cluster']="az acs delete  --resource-group="+cf_a['project_name']+" --name="+cf_a['cluster_name']+" --no-wait"
        cf_a['get_credentials']="az acs kubernetes get-credentials --resource-group="+cf_a['project_name']+" --name="+cf_a['cluster_name']+" --ssh-key-file=~/.ssh/id_rsa_"+cf_a['cluster_name']
        cf_a['normal_size_cluster']="az acs scale --resource-group="+cf_a['project_name']+" --name="+cf_a['cluster_name']+" --new-agent-count "+str(cf_a['a_num_nodes'])
        cf_a['class_size_cluster']="az acs scale --resource-group="+cf_a['project_name']+" --name="+cf_a['cluster_name']+" --new-agent-count "+str(cf_a['a_num_nodes_class'])
    cf_a['install_helm']='helm init --client-only'
    # Can't size to 0 cf_g['a_stop_cluster']="az acs scale --resource-group="+cf_a['project_name']+" --name="+cf_a['cluster_name']+" --new-agent-count 0"
    cf_a['create_storage']= "az storage account create --resource-group="+cf_a['project_name']+" --location="+cf_a['a_location']+" --sku=Standard_LRS  --name="+cf_a['a_storage_account']+" --kind=Storage"
    cf_a['get_storage_key']="az storage account keys list --account-name="+cf_a['a_storage_account']+" --resource-group="+cf_a['project_name']+" --output=json | jq .[0].value -r"
    cf_a['create_keyvault']="az keyvault create --name="+cf_a['cluster_name']+" --resource-group="+ cf_a['project_name']+" --location="+cf_a['a_location']+" --enabled-for-template-deployment true"
    cf_a['backup_private_key']="az keyvault secret set --vault-name="+ cf_a['cluster_name']+ " --name=id-rsa-"+cf_a['cluster_name']+" --file=~/.ssh/id_rsa_"+cf_a['cluster_name']
    cf_a['backup_public_key']="az keyvault secret set --vault-name="+ cf_a['cluster_name']+ " --name=id-rsa"+cf_a['cluster_name']+"-pub --file=~/.ssh/id_rsa_"+cf_a['cluster_name']+".pub"
    cf_a['get_private_key']="az keyvault secret show --vault-name="+ cf_a['cluster_name']+ " --name=id-rsa-"+cf_a['cluster_name']
    cf_a['get_public_key']="az keyvault secret show --vault-name="+ cf_a['cluster_name']+ " --name=id-rsa"+cf_a['cluster_name']+"-pub"
    return cf_a

def jupyterhub_commands(cf_j):
    cf_j['jup_instance']=cf_j['path']+"config/jupyterhub/"+cf_j['jup_namespace']
    cf_j['jup_config']=cf_j['path']+"config/jupyterhub/"+cf_j['jup_namespace']+"/config.yaml"
    cf_j['jup_base']=cf_j['path']+"config/jupyterhub/"+cf_j['jup_namespace']+"/values.yaml"
    cf_j['jup_install_ssl']="helm install --name=letsencrypt --namespace=kube-system stable/kube-lego --set config.LEGO_EMAIL="+cf_j['jup_email']+" --set config.LEGO_URL=https://acme-v01.api.letsencrypt.org/directory"
    cf_j['jup_repo']="helm repo add jupyterhub "+cf_j['jup_helm_repo']+" && helm repo update"
    cf_j['jup_install']="helm install jupyterhub/jupyterhub --version="+cf_j['jup_version']+" --name="+cf_j['jup_releasename']+" --namespace="+cf_j['jup_namespace']+" -f "+cf_j['jup_config']
    cf_j['jup_upgrade']="helm upgrade "+cf_j['jup_namespace']+" jupyterhub/jupyterhub --version="+cf_j['jup_version']+" -f "+cf_j['jup_config']
    cf_j['jup_describe']="kubectl --namespace="+cf_j['jup_namespace']+" get pod"
    cf_j['jup_get_ip']="kubectl --namespace="+ cf_j['jup_namespace']+" get svc proxy-public"
    cf_j['jup_delete_instance']="helm delete "+cf_j['jup_releasename']+" --purge"
    cf_j['jup_delete_namespace']="kubectl delete namespace "+cf_j['jup_namespace']
    if cf_j['jup_ssl']:
        cf_j['jup_callback_url']= "https://"
    else:
        cf_j['jup_callback_url']= "http://"
    cf_j['jup_callback_url']=cf_j['jup_callback_url']+cf_j['jup_url']+"/hub/oauth_callback"
    cf_j['jup_get_logs']="kubectl --namespace="+cf_j['jup_namespace']+" logs <insert_podname>"
    return cf_j

def restore_kube(cf):
    restore_file_az(cf['cluster_name']+"-public-key", cf['ssh_dir']+"id_rsa_"+cf['cluster_name']+".pub", cf)
    restore_file_az(cf['cluster_name']+"-private-key", cf['ssh_dir']+"id_rsa_"+cf['cluster_name'], cf)
    restore_file_az(cf['cluster_name']+"-config-file", cf['path']+cf['config_file'], cf)
    return

def restore_file_az(secret, file, cf):
    result=bash_command("az keyvault secret show --vault-name="+ cf['cluster_name']+ " --name="+secret)
    result=json.loads(result)
    with open(file, "w+") as text_file:
          text_file.write(result['value'])
    return result

def backup_kube(cf):
    bash_command('create_keyvault', cf)
    if cf['cloud_provider']=='azure':
        backup_file_az(cf['cluster_name']+"-public-key", cf['ssh_dir']+"id_rsa_"+cf['cluster_name']+".pub", cf)
        backup_file_az(cf['cluster_name']+"-private-key", cf['ssh_dir']+"id_rsa_"+cf['cluster_name'], cf)
        backup_file_az(cf['cluster_name']+"-config-file", cf['path']+cf['config_file'], cf)
    else:
        print('Backup not available for your cloud provider.')
    return

def backup_file_az(secret, file, cf):
    result=bash_command("az keyvault secret set --vault-name="+ cf['cluster_name']+ " --name="+secret+" --file="+file)
    return result

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

def set_jupyterhub_config(cf):
    #This makes a specific directory for configuration
    if cf['jup_rebuild_config']:
        bash_command('rm -rf '+cf['jup_instance'])
        bash_command('mkdir '+cf['jup_instance'])
        #Random variable that will be added to the config file.
        bash_command("openssl rand -hex 32 > "+ cf['jup_instance']+"/cookie_secret.txt")
        #Random variable that will be added to the config file.
        bash_command("openssl rand -hex 32 > "+ cf['jup_instance']+"/secret_token.txt")
        #download reference config
        bash_command("wget -P "+ cf['jup_instance']+" "+cf['jup_config_init'])
        bash_command("mv "+ cf['jup_instance']+"/values.yaml " +cf['jup_instance']+"/reference.yaml")
        #init_jupyterhub_config(cf)
        if cf['jup_set_fixed_ip']:
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
        with open(cf['jup_instance']+'/cookie_secret.txt', 'r') as f:
                  cookie_secret = f.read().rstrip()
        with open(cf['jup_instance']+'/secret_token.txt', 'r') as f:
                  secret_token = f.read().rstrip()

        config = ruamel.yaml.load(inp, ruamel.yaml.RoundTripLoader)

        config['hub']['cookieSecret']=cookie_secret
        config['proxy']['secretToken']=secret_token
        if cf['jup_set_fixed_ip']:
            config['proxy']['service']['loadBalancerIP']=cf['jup_fixed_ip']
        if cf['cloud_provider']=='azure':
            config['prePuller']=cf['jup_prePuller']
        ruamel.yaml.round_trip_dump(config, open(cf['jup_config'], 'w'))
        cf['jup_rebuild_config']=False
        ruamel.yaml.round_trip_dump(cf, open(cf['path']+cf['config_file'], 'w'))
    else:
        print("Currently the jup_rebuild_config parameter in the configuration file is set to false. Not rebuilding config.")
    return cf

def bash_command2(command):
    import subprocess
    import shlex
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print (output.strip())
    rc = process.poll()
    return rc

def update_config(configkey, kubekey, cf_j):
    config = ruamel.yaml.round_trip_load(open(cf_j['jup_config']), preserve_quotes=True)
#        singleuser['singleuser']=cf_j['singleuser']
    if configkey in config:
        config[configkey]=cf_j[kubekey]
    else:
        config.insert(len(config), configkey, cf_j[kubekey])
    ruamel.yaml.round_trip_dump(config, open(cf_j['jup_config'], 'w'))
    return

def set_jupyterhub_auth(auth_type, cf_j):
    if auth_type=='dummy':
        #Optional Dummy Authorization
        inp_auth = """        type: dummy
        dummy:
        """
        auth = ruamel.yaml.round_trip_load(inp_auth, preserve_quotes=True)
        config = ruamel.yaml.round_trip_load(open(cf_j['jup_config']), preserve_quotes=True)
        auth['dummy']=cf_j['dummy_auth']

    elif auth_type=='github':
        #Optional Github Authorization
        inp_auth = """        type: github
        github:
        """
        auth = ruamel.yaml.round_trip_load(inp_auth, preserve_quotes=True)
        config = ruamel.yaml.round_trip_load(open(cf_j['jup_config']), preserve_quotes=True)
        auth['github']=cf_j['github_auth']


        ruamel.yaml.round_trip_dump(config, open(cf_j['jup_config'], 'w'))
    elif auth_type=='google':
        #Optional Google Authorization
        inp_auth = """        type: google
        google:
        """
        auth = ruamel.yaml.round_trip_load(inp_auth, preserve_quotes=True)
        config = ruamel.yaml.round_trip_load(open(cf_j['jup_config']), preserve_quotes=True)
        auth['google']=cf_j['google_auth']

    if 'auth' in config:
        config['auth']=auth
    else:
        config.insert(len(config), 'auth', auth)
    ruamel.yaml.round_trip_dump(config, open(cf_j['jup_config'], 'w'))
    print(ruamel.yaml.dump(config, sys.stdout, Dumper=ruamel.yaml.RoundTripDumper))
    return

def isipv4(s):
    sp = s.split('.')
    if len(sp) != 4: return False
    try: return all(0<=int(p)<256 for p in sp)
    except ValueError: return False

def get_jupyterhub_ip(cf_j):
    result=bash_command('jup_get_ip',cf_j)
    result=result.split(" ")
    cf_j['public_ip']=[x for x in result if isipv4(x)][1]
    print("JupyterHub is live at the following address:")
    print("http://"+cf_j['public_ip']+"/hub/login")


def get_fixed_ip(cf_g):
    result=bash_command(cf_g['describe_fixedip']).split('\n')
    public_ip= [x for x in result if "address:" in x][0].split(' ').pop()
    return public_ip
