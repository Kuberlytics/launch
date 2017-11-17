FROM jupyter/base-notebook:ae885c0a6226
ARG JUPYTERHUB_VERSION=0.8
ARG HELM_VERSION=2.6.2
ARG TERRAFORM_VERSION=0.10.8
ARG JUPYTER_USER=jovyan
ARG JUPYTER_GROUP=100
ARG GOVERSION=1.8
ARG AZURE_VERSION=0.8.0
ARG PACHYDERM_VERSION=1.6.3
ARG KISMATIC_VERSION=1.6.0
ENV DEBIAN_FRONTEND noninteractive
ENV INITRD No
ENV LANG en_US.UTF-8
ENV GOROOT /opt/go
ENV GOPATH /home/${JUPYTER_USER}/go
ENV PATH $GOPATH/bin:$GOROOT/bin:/${PATH}
ENV CLOUD_SDK_REPO "cloud-sdk-xenial"

#jq and qemu-utils used for Pachyderm
USER root
RUN apt-get update
RUN apt-get install -yq apt-transport-https curl apt-utils keychain git jq qemu-utils nano unzip
RUN echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ wheezy main" | tee /etc/apt/sources.list.d/azure-cli.list
RUN apt-key adv --keyserver packages.microsoft.com --recv-keys 52E16F86FEE04B979B07E28DB02C46DF417A0893
RUN apt-get update && apt-get install -yq azure-cli

### Install Go
RUN cd /opt && wget https://storage.googleapis.com/golang/go${GOVERSION}.linux-amd64.tar.gz && \
    tar zxf go${GOVERSION}.linux-amd64.tar.gz && rm go${GOVERSION}.linux-amd64.tar.gz && \
    ln -s /opt/go/bin/go /usr/bin/ && \
    mkdir $GOPATH
RUN go get github.com/docopt/docopt-go
RUN go get github.com/Microsoft/azure-vhd-utils
RUN go install github.com/Microsoft/azure-vhd-utils
RUN go get github.com/Azure/azure-sdk-for-go/storage
RUN chown ${JUPYTER_USER}:${JUPYTER_GROUP} $GOPATH && \
    fix-permissions $GOPATH

#KUBECTRL
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
RUN chmod +x ./kubectl
RUN mv ./kubectl /usr/local/bin/kubectl

#HELM
RUN curl https://raw.githubusercontent.com/kubernetes/helm/master/scripts/get > /tmp/get_helm.sh
RUN chmod 700 /tmp/get_helm.sh
RUN ls /tmp
RUN /tmp/get_helm.sh --version v${HELM_VERSION}

#AZURE
ARG ACS_URL=https://github.com/Azure/acs-engine/releases/download/v${AZURE_VERSION}/acs-engine-v${AZURE_VERSION}-linux-amd64.tar.gz
RUN curl -OL $ACS_URL
RUN tar -zxvf acs-engine-*.tar.gz && rm acs-engine-*.tar.gz
RUN chmod +x ./acs-engine*/acs-engine
RUN mv ./acs-engine*/acs-engine /usr/local/bin/acs-engine
RUN rm -rf ./acs-engine*

#PACHYDERM
RUN curl -o /tmp/pachctl.deb -L https://github.com/pachyderm/pachyderm/releases/download/v${PACHYDERM_VERSION}/pachctl_${PACHYDERM_VERSION}_amd64.deb && dpkg -i /tmp/pachctl.deb

#GOOGLE CLI

# Add the Cloud SDK distribution URI as a package source
RUN echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

# Import the Google Cloud Platform public key
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -

# Update the package list and install the Cloud SDK
RUN apt-get update && apt-get install -yq google-cloud-sdk

#TERRAFORM
RUN cd /tmp && \
   wget https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
   unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip -d /usr/bin && \
   rm -rf /tmp/* && \
   rm -rf /var/tmp/*


#KET
RUN mkdir /home/${JUPYTER_USER}/ket && \
    cd /home/${JUPYTER_USER}/ket && \
    wget https://github.com/apprenda/kismatic/releases/download/v${KISMATIC_VERSION}/kismatic-v${KISMATIC_VERSION}-linux-amd64.tar.gz && \
    tar -xzf kismatic-v${KISMATIC_VERSION}-linux-amd64.tar.gz -C /home/jovyan/ket && \
    rm kismatic-v${KISMATIC_VERSION}-linux-amd64.tar.gz

#COPY over files
COPY . /home/${JUPYTER_USER}/launch
COPY ./README.md /home/${JUPYTER_USER}/README.md
COPY ./config/config.sample /home/${JUPYTER_USER}/launch/config/config.yaml
RUN chown -R ${JUPYTER_USER}:$JUPYTER_GROUP /home/${JUPYTER_USER}/launch && chown ${JUPYTER_USER}:$JUPYTER_GROUP /home/${JUPYTER_USER}/README.md &&mkdir /home/${JUPYTER_USER}/.ssh &&chown ${JUPYTER_USER}:$JUPYTER_GROUP /home/${JUPYTER_USER}/.ssh


USER ${JUPYTER_USER}
RUN conda install -c conda-forge --quiet --yes \
    'ruamel.yaml=0.15*'
RUN pip install --no-cache jupyterhub==$JUPYTERHUB_VERSION
