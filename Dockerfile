FROM fedora:24
# TODO: install server deps from RPM
# TODO: move devel tools to a separate container
RUN dnf install -y git python-pip gcc python-devel postgresql-devel redhat-rpm-config python2-pytest
# python-psycopg2 python-twisted python-six python-redis python-dateutil python-zope-interface

RUN mkdir -p /opt/app
WORKDIR /opt/app

COPY ./requirements.txt /opt/app/
RUN pip install --user -r ./requirements.txt
COPY ./requirements-devel.txt /opt/app/
RUN  pip install --user -r ./requirements-devel.txt

# XXX: development version of dockerfile, we're mounting sources inside
# COPY . /opt/app/

# database needs to be set up before web can start serving requests
# --noworker
CMD sleep 7 && exec python /opt/app/manage.py runserver -v3 0.0.0.0:8000
