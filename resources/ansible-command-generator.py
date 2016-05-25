import pyperclip

from questionnaire import Questionnaire


def generate(env="development", kind="deploy", playbooks=[],
        tags=[], branch="", action="restarted", services=[]):
    """Generate Ansible command."""
    VAULT_PASS_FILE = "~/.ansible-vault-pass"

    _env = {
        "development": "-u vagrant -i inventories/development"
            " --private-key=.vagrant/machines/default/virtualbox/private_key",
        "staging": "-u root -i inventories/staging",
        "production": "-u root -i inventories/production",
    }

    if kind in playbooks or "all" in playbooks:
        # ignore other playbooks if base playbook was run
        playbooks = "playbooks/{}.yml".format(kind)
    else:
        playbooks = " ".join("playbooks/{}/{}.yml".format(kind, playbook)
            for playbook in playbooks)
    command = "ansible-playbook {0} --vault-password-file {1}" \
        " {2}".format(_env[env], VAULT_PASS_FILE, playbooks)

    if tags and "all" not in tags:
        command += " --tags=\"{}\"".format(",".join(tags))
    extra_vars = {}
    if kind == "deploy":
        extra_vars['git_branch'] = branch or "master"
    elif kind == "service":
        extra_vars['action'] = action
        if services and "all" not in services:
            extra_vars['services'] = services
    if extra_vars:
        command += " --extra-vars=\"{}\"".format(extra_vars)
    return command


if __name__ == '__main__':

    SERVICES_INITD = ['redis_6379', 'postgresql', 'nginx', 'firewall']
    SERVICES_UPSTART = ['gunicorn', 'celery-worker', 'celery-beat', 'celery-flower', 'django']
    SERVICES_DEV = SERVICES_INITD + [s + "-development" for s in SERVICES_UPSTART]
    SERVICES_STG = SERVICES_INITD + [s + "-staging" for s in SERVICES_UPSTART]
    SERVICES_PRD = SERVICES_INITD + [s + "-production" for s in SERVICES_UPSTART]

    q = Questionnaire()

    # ENV
    q.add_question('env', options=['development', 'staging', 'production'])

    # KIND
    q.add_question('kind', options=['deploy', 'service'])

    # PLAYBOOKS
    q.add_question('playbooks', prompter="multiple",
        options=['deploy', 'webserver', 'database', 'backend', 'webapp', 'api', 'message', 'staticfiles', 'create_user',]).\
        add_condition(keys=['kind'], vals=['deploy'])

    q.add_question('playbooks', prompter="multiple",
        options=['service', 'webserver', 'database', 'webapp', 'api', 'message',]).\
        add_condition(keys=['kind'], vals=['service'])

    # TAGS
    q.add_question('tags', prompter="multiple",
        options=['aws_cli', 'bower', 'clone_repo', 'collectstatic', 'createsuperuser', 'cron', 'django', 'env_vars', 'fixtures', 'iptables', 'logrotate', 'migrate', 'nginx', 'node', 'postgresql', 'redis', 'staticfiles', 'upstart', 'vagrant', 'virtualenv']).\
        add_condition(keys=['kind'], vals=['deploy'])

    # BRANCH
    q.add_question('branch', prompter="raw").add_condition(keys=['kind'], vals=['deploy'])

    # ACTION
    q.add_question('action', options=['started', 'stopped', 'restarted', 'reloaded']).\
        add_condition(keys=['kind'], vals=['service'])

    # SERVICES
    q.add_question('services', prompter="multiple", options=SERVICES_DEV).\
        add_condition(keys=['kind', 'env'], vals=['service', 'development'])
    q.add_question('services', prompter="multiple", options=SERVICES_STG).\
        add_condition(keys=['kind', 'env'], vals=['service', 'staging'])
    q.add_question('services', prompter="multiple", options=SERVICES_PRD).\
        add_condition(keys=['kind', 'env'], vals=['service', 'production'])

    answers = q.run()
    command = generate(**answers)

    print("\nTHE FOLLOWING COMMAND HAS BEEN COPIED TO YOUR CLIPBOARD:\n\n{}\n".format(command))
    pyperclip.copy(command)
