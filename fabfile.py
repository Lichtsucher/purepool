from fabric.api import local

def devel_celery():
    local("./env/bin/celery -A purepool worker -Q celery,find_new_blocks,send_autopayments,important,standard -l INFO")
    
def devel_server():
    local("./env/bin/python manage.py runserver 0.0.0.0:8080")

def devel_tasks():
    # runn all basic tasks in devel at once
    local("./env/bin/python manage.py find_new_blocks --network test")
    local("./env/bin/python manage.py process_next_block --network test")
    local("./env/bin/python manage.py shareout_next_block --network test")
    local("./env/bin/python manage.py send_autopayments --network test")
    local("./env/bin/python manage.py cleanup_solutions")
