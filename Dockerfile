FROM fedora:24
RUN dnf install -y git python-pip gcc python-devel postgresql-devel redhat-rpm-config

RUN mkdir -p /opt/app
WORKDIR /opt/app

COPY . /opt/app

RUN pip install -r ./requirements.txt

# database needs to be set up before web can start serving requests
CMD sleep 7 && exec python /opt/app/manage.py runserver --noworker -v3 0.0.0.0:8000
