FROM jupyter/base-notebook:ae885c0a6226
ARG JUPYTERHUB_VERSION=0.8
ARG HELM_VERSION=2.6.2
RUN pip install --no-cache jupyterhub==$JUPYTERHUB_VERSION

#jq and qemu-utils used for Pachyderm
USER root
RUN apt-get update
RUN apt-get install -yq apt-transport-https curl apt-utils keychain git jq qemu-utils nano
RUN echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ wheezy main" | tee /etc/apt/sources.list.d/azure-cli.list
RUN apt-key adv --keyserver packages.microsoft.com --recv-keys 52E16F86FEE04B979B07E28DB02C46DF417A0893
RUN apt-get update && apt-get install -yq azure-cli

#RUN add-apt-repository ppa:gophers/archive && apt update && apt-get install golang-1.8-go
### Install Go
ENV DEBIAN_FRONTEND noninteractive
ENV INITRD No
ENV LANG en_US.UTF-8
ENV GOVERSION 1.8
ENV GOROOT /opt/go
ENV GOPATH /home/jovyan/go
RUN cd /opt && wget https://storage.googleapis.com/golang/go${GOVERSION}.linux-amd64.tar.gz && \
    tar zxf go${GOVERSION}.linux-amd64.tar.gz && rm go${GOVERSION}.linux-amd64.tar.gz && \
    ln -s /opt/go/bin/go /usr/bin/ && \
    mkdir $GOPATH
RUN go get github.com/docopt/docopt-go
RUN go get github.com/Microsoft/azure-vhd-utils
RUN go install github.com/Microsoft/azure-vhd-utils
RUN go get github.com/Azure/azure-sdk-for-go/storage
ENV PATH $GOPATH/bin:$GOROOT/bin:/${PATH}

#Kubectrl
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
RUN chmod +x ./kubectl
RUN mv ./kubectl /usr/local/bin/kubectl

#HELM
RUN curl https://raw.githubusercontent.com/kubernetes/helm/master/scripts/get > /tmp/get_helm.sh
RUN chmod 700 /tmp/get_helm.sh
RUN ls /tmp
RUN /tmp/get_helm.sh --version v2.6.2

ARG ACS_URL=https://github.com/Azure/acs-engine/releases/download/v0.8.0/acs-engine-v0.8.0-linux-amd64.tar.gz
RUN curl -OL $ACS_URL
RUN tar -zxvf acs-engine-*.tar.gz && rm acs-engine-*.tar.gz
RUN chmod +x ./acs-engine*/acs-engine
RUN mv ./acs-engine*/acs-engine /usr/local/bin/acs-engine
RUN rm -rf ./acs-engine*

#Install Pachyderm
RUN curl -o /tmp/pachctl.deb -L https://github.com/pachyderm/pachyderm/releases/download/v1.6.3/pachctl_1.6.3_amd64.deb && dpkg -i /tmp/pachctl.deb


#Install Google Command Line
# Install the Google Cloud SDK.
# Create an environment variable for the correct distribution
ENV CLOUD_SDK_REPO "cloud-sdk-xenial"

# Add the Cloud SDK distribution URI as a package source
RUN echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

# Import the Google Cloud Platform public key
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -

# Update the package list and install the Cloud SDK
RUN apt-get update && apt-get install -yq google-cloud-sdk

USER jovyan
#Jason Added
RUN conda install -c conda-forge --quiet --yes \
    'fastparquet=0.1*' \
    'nbpresent=3.0*' \
    'ipython_unittest=0.2*' \
    'ruamel.yaml=0.15*'
RUN conda install --quiet --yes  \
    'pandas-datareader=0.5*' \
    'beautifulsoup4=4.6*'

RUN /opt/conda/bin/pip install twitter==1.17.1
RUN conda install -c conda-forge --quiet --yes \
    'plotly=2.0*'

COPY . /home/jovyan/work
