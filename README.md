# trello-reporter

Reports and charts for your trello boards!


## Usage

### API key

This tool is interacting with trello via API. Every request sent to trello needs two values:

 1. API key
 2. token

You can obtain API key from [https://trello.com/app-key](https://trello.com/app-key).

The token is retrieved automatically from trello with the first request sent to the tool. The token is *NOT* saved to database. It's set as a cookie.


### Running the tool

Please make sure you have `docker-compose` installed.

Before starting the tool, you have to provide the API key. The easiest way is to set as an environment variable:

```
$ export API_KEY="mykey"
```

Then just bring the whole environment up:

```
$ docker-compose up
```

It may happen that database is not ready to accept conncetions when `migrator` container wants to create schema. Just restart it then:

```
$ docker-compose restart migrator
```

At this point, you should be able to [access](http://localhost:8000/) the tool in browser.


## Development

Everything is running in docker containers.


### Using django


#### Initializing project

Create new project using django installed in `web` image, the process will run
as your current used so the files and directories are not owned by root:

```
$ docker-compose run -u $(id -u) web django-admin startproject trello_reporter /opt/app
```
