# trello-reporter


## Development

Everything is in docker containers.


### Using django


#### Initializing project

Create new project using django installed in `web` image, the process will run
as your current used so the files and directories are not owned by root:

```
$ docker-compose run -u $(id -u) web django-admin startproject trello_reporter /opt/app
```
