# Kuberlytics Administrative Tools
Jupyter is an amazing interactive tool for analytics, but did you know that you an use it to launch your own cloud based data science stack on the Google Cloud platform, Azure (coming soon), or Amazon Web Services (coming soon)? We have put together a few powerful tools here including:

- Kubernetes: You probably have heard of containers and might even know the Docker whale. Kubernetes is a container orchestration platform that makes a great place to run containers and can be used on a variety of cloud platforms. In an era of "deep learning", you really need access to GPUs don't you? Well, the cloud is a great place to find them.

- Jupyterhub: Jupyter notebooks are a powerful way of combining content and code. They can also be great to do everything from control Kubernetes clusters to train models.

- Airflow: To build any type of ETL pipeline  or AI application you are likely to need some way of easily managing complex tasks.

- TBD:  I believe there are a number of different

This series of Jupyter Notebooks helps to augment the great work from [Helm](https://helm.sh), [Zero to Jupyterhub](https://zero-to-jupyterhub-with-kubernetes.readthedocs.io/en/latest/), [Pipeline.io](http://pipeline.io), [Pachyderm.io](pachyderm.io), and the emerging series of projects making it easier to do analytics on Kubernetes.

### Getting Started
1. Clone the repository.
2. Create a directory /config
2. Copy the Kubernetes.yaml file to /config and fill in with your with your data.
3. If you have conda installed, launch Jupyter from within the repostiory root directory
   `jupyter notebook`
4. Use notebooks to first create your Kubernetes cluster and then launch Jupyterhub.

This is an emerging project. Would love your comments, issues, or pull requests.

## Docker Image

This is a Jupyter Singleuser container with Azure CLI installed.
Build locally:
```
docker build -t kuberlytics/jupyter-singleuser-controller:latest -t kuberlytics/jupyter-singleuser-controller:v0.1 .
```
### To use Locally for example.
```
docker run -it --rm -p 8888:8888  -v /Users/jasonkuruzovich/githubdesktop/0_class:/home/jovyan/work --user root -e GRANT_SUDO=yes kuberlytics/jupyter-singleuser-controller:latest
```

#Please set to push to 2 repositories.

git remote set-url --add --push origin git@github.com:Kuberlytics/admin-tools.git
git remote set-url --add --push origin git@gitlab.com:Kuberlytics/admin-tools.git
