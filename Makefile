.PHONY=default build run clean test

default: all

build:
	docker build --build-arg USER_ID=$(shell id -u) --tag=trelloreporter_web .
	docker tag -f trelloreporter_web trelloreporter_migrator

run:
	docker-compose up -d

all: build run
# build and run, this is the default; we don't want to build every time we run

clean:
	docker-compose down -v

test:
	docker exec -ti $(shell docker-compose ps -q web | head -n 1) py.test trello_reporter/

shell:
	docker exec -ti $(shell docker-compose ps -q web | head -n 1) bash

root-shell:
	docker exec -ti -u root $(shell docker-compose ps -q web | head -n 1) bash
