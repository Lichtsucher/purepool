# Purepool - Biblepay Pool Software

Purepool is an alternative biblepay pool software written in Python.

## Basics

**Purepool requires an experienced administrator for setup, run and maintenance.**
Basic knowledge of system administration is required for this document, as it isn't a step-by-step guide. You already need to know how to setup and configue apache and mysql, must be able to learn and understand RabbitMQ (https://www.rabbitmq.com/configure.html) and Django (https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/modwsgi/).

## Server Layout

Purepool was designed to run on a 3 server layout:

* **Frontend:** The Webserver that handles the pool interface for the client and the website. Has only minimal write access to the database
* **Data:** Holds the database and the message/task queue
* **Backend:** Executes the tasks and runs the biblepay client/wallet

In this setup, the frontend has only minimal write access to the database, plus push-only rights to the message queue. It can only insert content into three tables of the database (work, miner, worker), but can not alter any entries (including work, miner, worker).

The base idea is that the frontend has no conneciton to the backend or even any knowledge about it. All communication is done via the data server, that grants only limited rights to the frontend.

## Workflow

At first, the miner is asking the pool for work. If the miner is unknown, the frontend will insert the miner and the worker into the database, then create a new work entry for the miner and returns that.
When the miner founds a solution, the frontend accepts it, puts it into the message queue and is done.
The backend will take the solution from the message queue, validates it and insert it to the database, if everything is ok.

At the same time, the backend will periodicly check for new blocks.
If a block is found, other tasks will share the bbp when the block is ready, and later send out the bbp to the users.

## Details

### Frontend

**Software:**

* Purepool source code
* Apache or any other Webserver that can run a django/wsgi project
* Memcache
* Let's encrypt

**Setup:**

* Install and configure apache, memcache and let's encrypt as you like it.
* Increase the maximum allowed header size in apache (LimitRequestFieldSize, LimitRequestLine, LimitRequestFields)
* Install purepool by putting the sourcecode to /srv/purepool
* Copy the settings/local.py.example as settings.local.py and edit it.
* Install the packages in ubuntu_packages.txt
* Create a virtualenv (http://docs.python-guide.org/en/latest/dev/virtualenvs/) and install the packages given in requirements.txt
* Configure apache for purepool wsgi. The django project explains it quite well: https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/modwsgi/
* Apache and Memcache should be started at system boot

**Security:**

It is highly adviced to use a firewall to block every access to any port except Port 80 and 443 (SSL).
You should only allow SSH connection from your own fixed ip address, and configure ssh to only accept logins with keys.

### Data

**Software:**

* MySQL (tested) or PostgreSQL (untested)
* RabbitMQ (message queue)

**Setup:**

* MySQL must listen on the public ip address, not only on localhost
* Same for RabbitMQ

**Security:**

Configure your server to use SSL for RabbitMQ and MySQL, or use a VPN connection between your servers. Block every other connection, and use the same ssh setup as for the frontend. Ensure that nobody except the two other servers can access mysql and rabbitmq!

MySQL should have two users: one for the frontend, one for the backend. Create a purepool database and give the frontend user read-only rights, with insert-rights to miner_miner, miner_worker nad solution_work. Do NOT grant update rights to any table!
The backend can have full right for the purepool database.

Create users for RabbitMQ, two. The user for the frontend should not be able to fetch messages from RabbitMQ, only push messages to the message queue.

### Backend

**Software:**

* Purepool Sourcecode
* Biblepay Client
* Celery
* Memcache

**Setup:**

* You do NOT need Apache here! This is a headless server that process tasks and handles the biblepay client!
* Install purepool, biblepay, celery and memcache
* Configure biblepay with an rpc connection (Point 5 of http://wiki.biblepay.org/Create_Sanctuary_2 gives you an example)
* Install the packages in ubuntu_packages.txt
* Create a virtualenv (http://docs.python-guide.org/en/latest/dev/virtualenvs/) and install the packages given in requirements.txt
* Copy the settings/local.py.example as settings.local.py and edit it.
* Follow the Celery Systemd guide: http://docs.celeryproject.org/en/latest/userguide/daemonizing.html
* Create the databasse with "manage.py migrate" (with your virtualenv) to create the database.
* Use the example celeryd file
* Use the example cron file to run the tasks
* Configure celery and biblepay to start at boot time. Look at the Dash project for an example who to make systemd and biblepay work together (https://github.com/dashpay/dash/blob/master/doc/init.md), as biblepay is based on dash


**Security:**

Configure the firewall, do not allow any connection from the frontend.
You should run biblepay as a unprivileged user.

