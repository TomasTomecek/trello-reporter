FROM fedora:24
# TODO: install server deps from RPM
# TODO: move devel tools to a separate container
RUN dnf install -y git python-pip gcc python-devel postgresql-devel redhat-rpm-config python2-pytest npm && \
    npm install -g bower
# python-psycopg2 python-twisted python-six python-redis python-dateutil python-zope-interface

ARG USER_ID=1000
RUN useradd -o -u ${USER_ID} reporter && \
    mkdir -p /opt/app && \
    chown reporter:reporter /opt/app
USER reporter

WORKDIR /opt/app
COPY ./install_static_data.sh /opt/app
RUN ./install_static_data.sh

COPY ./requirements.txt /opt/app/
RUN pip install --user -r ./requirements.txt
COPY ./requirements-devel.txt /opt/app/
RUN  pip install --user -r ./requirements-devel.txt

# the actual sources will be replaced by bind mount
COPY . /opt/app/
USER root
RUN chown -R reporter:reporter .
USER reporter

# database needs to be set up before web can start serving requests
# --noworker
CMD sleep 7 && exec python /opt/app/manage.py runserver -v3 0.0.0.0:8000
